"""Extrator inteligente via OpenRouter.

Modelos recomendados (gratuitos no OpenRouter):
  - Extração: google/gemini-2.0-flash-lite  (30 RPM)
  - Chat:     google/gemini-2.0-flash

Requer OPENROUTER_API_KEY no ambiente.
"""
from __future__ import annotations

import json
import logging
import os
import re
import textwrap

from bs4 import BeautifulSoup

from automacao.llm_client import generate

logger = logging.getLogger(__name__)


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


def extract_concursos_from_html(html: str, base_url: str, fonte: str, max_chars: int = 12000) -> list[dict]:
    text = _html_to_clean_text(html, max_chars)
    if len(text.strip()) < 100:
        logger.warning(f"[{fonte}] Texto muito curto, pulando extração")
        return []

    prompt = EXTRACT_PROMPT.format(scope=SCOPE_DESCRIPTION, base_url=base_url, text=text)

    model = os.environ.get("OPENROUTER_EXTRACTION_MODEL", "google/gemini-2.0-flash-lite")

    try:
        raw = generate(prompt, model=model)
    except Exception as e:
        logger.error(f"[{fonte}] LLM API error: {e}")
        return []

    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())

    try:
        data = json.loads(raw)
        concursos = data.get("concursos", [])
        if not isinstance(concursos, list):
            logger.error(f"[{fonte}] LLM retornou 'concursos' como {type(concursos).__name__}, esperado list. Resposta: {raw[:300]}")
            return []
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

    logger.info(f"[{fonte}] LLM extraiu {len(result)} concursos no escopo")
    return result


def extract_concursos_from_text(text: str, base_url: str, fonte: str) -> list[dict]:
    return extract_concursos_from_html(f"<pre>{text}</pre>", base_url=base_url, fonte=fonte)
