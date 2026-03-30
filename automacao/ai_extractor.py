"""Extrator inteligente via Gemini 2.0 Flash.

Recebe HTML de qualquer portal e retorna lista padronizada de concursos.
Implementa rate limiting para evitar 429.
"""
import json
import logging
import os
import re
import textwrap
import time
import threading

from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.0-flash"

# Rate limiter: max 8 chamadas/minuto (free tier = 15 RPM, usamos 8 para margem)
_rate_lock = threading.Lock()
_call_times: list[float] = []
MAX_CALLS_PER_MINUTE = 8
MIN_INTERVAL = 60.0 / MAX_CALLS_PER_MINUTE  # ~7.5s entre chamadas


def _rate_limit():
    with _rate_lock:
        now = time.monotonic()
        # Remove chamadas mais antigas que 60s
        while _call_times and now - _call_times[0] > 60.0:
            _call_times.pop(0)
        if len(_call_times) >= MAX_CALLS_PER_MINUTE:
            sleep_for = 60.0 - (now - _call_times[0]) + 1.0
            logger.info(f"Rate limit: aguardando {sleep_for:.1f}s")
            time.sleep(sleep_for)
        _call_times.append(time.monotonic())


SCOPE_DESCRIPTION = textwrap.dedent("""
    Perfis de interesse:
    1. Cargos de TI com nivel superior: analista de TI, analista de sistemas,
       desenvolvedor, engenheiro de software, seguranca da informacao,
       infraestrutura, banco de dados, redes, ciencia da computacao, etc.
    2. Professor de Ingles (qualquer nivel).

    Ignore: cargos de TI apenas com ensino medio/fundamental.
    Ignore: concursos sem relacao com TI ou professor de ingles.
""")

EXTRACT_PROMPT = textwrap.dedent("""
    Voce e um extrator de dados de concursos publicos brasileiros.
    Analise o texto abaixo e retorne SOMENTE JSON valido (sem markdown):

    {{"concursos": [
      {{
        "instituicao": "Nome do orgao",
        "orgao": "Local (ex: RS, Porto Alegre - RS)",
        "cargos": ["cargo 1"],
        "salario_maximo": "R$ X.XXX,XX ou null",
        "link_edital": "URL completa",
        "data_encerramento": "DD/MM/YYYY ou null",
        "data_publicacao": "DD/MM/YYYY ou null",
        "status": "aberto"
      }}
    ]}}

    Escopo (inclua APENAS):
    {scope}

    - Se nenhum concurso no escopo: {{"concursos": []}}
    - Nao invente dados ausentes: use null
    - Links relativos: prefixe com {base_url}
    - Max 30 concursos

    TEXTO:
    {text}
""").strip()


def _html_to_clean_text(html: str, max_chars: int = 12000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "head", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:max_chars]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=3, min=10, max=60))
def _call_gemini(prompt: str) -> str:
    _rate_limit()
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
        logger.error(f"[{fonte}] JSON invalido: {e} | Resposta: {raw[:300]}")
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
