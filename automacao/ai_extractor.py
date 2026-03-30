"""Extrator inteligente via Gemini (google-genai SDK)."""
import json
import logging
import os
import re
import textwrap

from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.0-flash"

SCOPE_DESCRIPTION = textwrap.dedent("""
    Perfis de interesse:
    1. Cargos de TI com nivel superior: analista de TI, analista de sistemas,
       desenvolvedor, engenheiro de software, seguranca da informacao,
       infraestrutura, banco de dados, redes, ciencia da computacao, etc.
    2. Professor de Ingles (qualquer nivel).

    Ignore concursos que exijam apenas ensino medio/fundamental para cargos de TI.
    Ignore concursos sem relacao com TI ou professor de ingles.
""")

EXTRACT_PROMPT = textwrap.dedent("""
    Voce e um extrator de dados de concursos publicos brasileiros.

    Analise o texto abaixo extraido de um portal oficial e retorne SOMENTE um
    JSON valido (sem markdown, sem explicacoes) com a seguinte estrutura:

    {{"concursos": [
      {{
        "instituicao": "Nome do orgao/prefeitura/estado",
        "orgao": "Sigla ou local (ex: RS, SC, Porto Alegre - RS)",
        "cargos": ["cargo 1", "cargo 2"],
        "salario_maximo": "R$ X.XXX,XX ou null",
        "link_edital": "URL completa do edital ou pagina do concurso",
        "data_encerramento": "DD/MM/YYYY ou null",
        "data_publicacao": "DD/MM/YYYY ou null",
        "status": "aberto"
      }}
    ]}}

    Regras:
    - Inclua APENAS concursos dentro deste escopo:
    {scope}
    - Se nao houver concursos no escopo, retorne {{"concursos": []}}.
    - Nao invente dados. Se um campo nao existir no texto, use null.
    - Links relativos: complete com a base_url fornecida.
    - Retorne no maximo 30 concursos por chamada.

    base_url: {base_url}

    TEXTO DO PORTAL:
    {text}
""").strip()


def _html_to_clean_text(html: str, max_chars: int = 12000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "head", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:max_chars]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
def _call_gemini(prompt: str) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=4096,
        ),
    )
    return response.text


def extract_concursos_from_html(html: str, base_url: str, fonte: str, max_chars: int = 12000) -> list[dict]:
    text = _html_to_clean_text(html, max_chars)
    if len(text.strip()) < 100:
        logger.warning(f"[{fonte}] Texto muito curto, pulando AI extraction")
        return []

    prompt = EXTRACT_PROMPT.format(scope=SCOPE_DESCRIPTION, base_url=base_url, text=text)

    try:
        raw = _call_gemini(prompt)
    except Exception as e:
        logger.error(f"[{fonte}] Gemini API error: {e}")
        return []

    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())

    try:
        data = json.loads(raw)
        concursos = data.get("concursos", [])
    except json.JSONDecodeError as e:
        logger.error(f"[{fonte}] JSON invalido do Gemini: {e}\nResposta: {raw[:300]}")
        return []

    result = []
    for c in concursos:
        if not c.get("instituicao") or not c.get("link_edital"):
            continue
        c["fonte"] = fonte
        c["status"] = c.get("status", "aberto")
        c["cargos"] = c.get("cargos") or []
        result.append(c)

    logger.info(f"[{fonte}] Gemini extraiu {len(result)} concursos no escopo")
    return result


def extract_concursos_from_text(text: str, base_url: str, fonte: str) -> list[dict]:
    return extract_concursos_from_html(f"<pre>{text}</pre>", base_url=base_url, fonte=fonte)
