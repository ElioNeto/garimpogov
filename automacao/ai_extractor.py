"""Extrator inteligente via Gemini.

Recebe HTML bruto (ou texto) de qualquer portal e retorna uma lista
padronizada de concursos usando o modelo Gemini Flash.
Isso elimina a dependencia de seletores CSS frageis.
"""
import json
import logging
import os
import re
import textwrap
from typing import Optional

import google.generativeai as genai
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Gemini Flash: rapido e barato para extracao estruturada
MODEL = "gemini-1.5-flash"

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

    {{
      "concursos": [
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
      ]
    }}

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
    """Converte HTML para texto limpo e trunca para caber no contexto do modelo."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "head", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Remove linhas em branco multiplas
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:max_chars]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
def _call_gemini(prompt: str) -> str:
    model = genai.GenerativeModel(MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.0,  # determinístico para extracao
            max_output_tokens=4096,
        ),
    )
    return response.text


def extract_concursos_from_html(
    html: str,
    base_url: str,
    fonte: str,
    max_chars: int = 12000,
) -> list[dict]:
    """
    Dado o HTML de um portal, usa o Gemini para extrair concursos no escopo.
    Retorna lista de dicts padronizados.
    """
    text = _html_to_clean_text(html, max_chars)

    if len(text.strip()) < 100:
        logger.warning(f"[{fonte}] Texto muito curto apos limpeza, pulando AI extraction")
        return []

    prompt = EXTRACT_PROMPT.format(
        scope=SCOPE_DESCRIPTION,
        base_url=base_url,
        text=text,
    )

    try:
        raw = _call_gemini(prompt)
    except Exception as e:
        logger.error(f"[{fonte}] Gemini API error: {e}")
        return []

    # Remove possivel markdown ao redor do JSON
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())

    try:
        data = json.loads(raw)
        concursos = data.get("concursos", [])
    except json.JSONDecodeError as e:
        logger.error(f"[{fonte}] JSON invalido do Gemini: {e}\nResposta: {raw[:300]}")
        return []

    # Normaliza e adiciona fonte
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


def extract_concursos_from_text(
    text: str,
    base_url: str,
    fonte: str,
) -> list[dict]:
    """Versao que recebe texto limpo diretamente (ex: resposta de API JSON)."""
    return extract_concursos_from_html(
        f"<pre>{text}</pre>", base_url=base_url, fonte=fonte
    )
