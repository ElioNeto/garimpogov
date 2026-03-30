"""Extrator via Gemini 2.0 Flash-Lite.

Estrategia BATCH:
  - Todas as fontes coletam o HTML (scraping puro, sem IA)
  - Os textos sao concatenados em blocos de ~18k chars
  - O Gemini recebe 1 bloco por vez -> drasticamente menos chamadas
  - Com 24 fontes gerando ~400 chars de texto util cada = ~10k chars total
  - Resultado: 1-3 chamadas Gemini por execucao completa

Limite free tier gemini-2.0-flash-lite: 30 RPM / 1500 RPD
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

logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.0-flash-lite"

# Rate limiter conservador: 1 chamada a cada 4s = 15 RPM (metade do limite)
_rate_lock = threading.Lock()
_last_call: float = 0.0
MIN_INTERVAL = 4.0

# Tamanho maximo de texto por chamada Gemini (~18k chars = ~4500 tokens)
BATCH_CHARS = 18000


def _rate_limit():
    with _rate_lock:
        global _last_call
        elapsed = time.monotonic() - _last_call
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        _last_call = time.monotonic()


SCOPE_DESCRIPTION = textwrap.dedent("""
    Perfis de interesse:
    1. Cargos de TI nivel superior: analista de TI, analista de sistemas,
       desenvolvedor, engenheiro de software, seguranca da informacao,
       infraestrutura, banco de dados, redes, TI em geral.
    2. Professor de Ingles (qualquer nivel).
    Ignore cargos de TI com ensino medio/fundamental.
    Ignore concursos sem relacao com TI ou professor de ingles.
""")

EXTRACT_PROMPT = textwrap.dedent("""
    Voce e um extrator de concursos publicos brasileiros.
    Analise os textos abaixo (de multiplas fontes) e retorne SOMENTE JSON valido:

    {{"concursos": [
      {{
        "instituicao": "Nome do orgao",
        "orgao": "Estado/cidade (ex: RS, Porto Alegre - RS)",
        "cargos": ["cargo"],
        "salario_maximo": "R$ X.XXX,XX ou null",
        "link_edital": "URL completa ou null",
        "data_encerramento": "DD/MM/YYYY ou null",
        "fonte": "nome da banca/portal"
      }}
    ]}}

    Regras:
    - Inclua APENAS: {scope}
    - Se nenhum concurso no escopo: {{"concursos": []}}
    - Nao invente dados; campos ausentes = null
    - Retorne no maximo 50 concursos

    TEXTOS:
    {text}
""").strip()


def _html_to_text(html: str, fonte: str, max_chars: int = 3000) -> str:
    """Converte HTML em texto limpo com cabecalho de fonte."""
    try:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "head", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text[:max_chars]
    except Exception:
        text = html[:max_chars]
    return f"\n\n=== FONTE: {fonte} ===\n{text}"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=30, max=120))
def _call_gemini(prompt: str) -> str:
    _rate_limit()
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=8192,
        ),
    )
    return response.text


def _parse_response(raw: str) -> list[dict]:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    try:
        data = json.loads(raw)
        return data.get("concursos", [])
    except json.JSONDecodeError as e:
        logger.error(f"JSON invalido do Gemini: {e} | {raw[:200]}")
        return []


# --- API publica ---

def extract_concursos_from_html(html: str, base_url: str, fonte: str, max_chars: int = 3000) -> list[dict]:
    """Chamada individual (compatibilidade). Usa batch internamente se possivel."""
    text = _html_to_text(html, fonte, max_chars)
    prompt = EXTRACT_PROMPT.format(scope=SCOPE_DESCRIPTION, text=text)
    try:
        raw = _call_gemini(prompt)
        concursos = _parse_response(raw)
        result = [c for c in concursos if c.get("instituicao")]
        for c in result:
            c.setdefault("fonte", fonte)
            c.setdefault("status", "aberto")
            c.setdefault("cargos", [])
        logger.info(f"[{fonte}] {len(result)} concursos extraidos")
        return result
    except Exception as e:
        logger.error(f"[{fonte}] Gemini error: {e}")
        return []


def extract_batch(pages: list[tuple[str, str, str]]) -> list[dict]:
    """Processa multiplas paginas em lote - UMA chamada Gemini por batch.

    Args:
        pages: lista de (html, base_url, fonte)

    Returns:
        lista de concursos extraidos
    """
    # Converte todos os HTMLs em texto limpo
    texts: list[str] = []
    for html, base_url, fonte in pages:
        texts.append(_html_to_text(html, fonte, max_chars=2000))

    # Divide em blocos de BATCH_CHARS para nao exceder contexto
    all_results: list[dict] = []
    current_block = ""
    block_num = 0

    for t in texts:
        if len(current_block) + len(t) > BATCH_CHARS and current_block:
            # Processa bloco atual
            block_num += 1
            logger.info(f"Gemini batch {block_num}: {len(current_block)} chars")
            prompt = EXTRACT_PROMPT.format(scope=SCOPE_DESCRIPTION, text=current_block)
            try:
                raw = _call_gemini(prompt)
                concursos = _parse_response(raw)
                for c in concursos:
                    if c.get("instituicao"):
                        c.setdefault("status", "aberto")
                        c.setdefault("cargos", [])
                        all_results.append(c)
                logger.info(f"Batch {block_num}: {len(concursos)} concursos")
            except Exception as e:
                logger.error(f"Gemini batch {block_num} error: {e}")
            current_block = t
        else:
            current_block += t

    # Ultimo bloco
    if current_block.strip():
        block_num += 1
        logger.info(f"Gemini batch {block_num} (final): {len(current_block)} chars")
        prompt = EXTRACT_PROMPT.format(scope=SCOPE_DESCRIPTION, text=current_block)
        try:
            raw = _call_gemini(prompt)
            concursos = _parse_response(raw)
            for c in concursos:
                if c.get("instituicao"):
                    c.setdefault("status", "aberto")
                    c.setdefault("cargos", [])
                    all_results.append(c)
            logger.info(f"Batch {block_num}: {len(concursos)} concursos")
        except Exception as e:
            logger.error(f"Gemini batch final error: {e}")

    logger.info(f"Total Gemini: {block_num} chamadas, {len(all_results)} concursos")
    return all_results
