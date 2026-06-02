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


EXTRACT_PROMPT = textwrap.dedent("""
    Voce e um extrator de dados de concursos publicos brasileiros.
    Analise o texto abaixo e retorne SOMENTE JSON valido (sem markdown).

    REGRAS OBRIGATORIAS:
    1. Cada concurso deve ter link_edital UNICO e ESPECIFICO (extraido do href).
       NUNCA use null, a URL inicial ou a URL de listagem como link_edital.
    2. Extraia os CARGOS ESPECIFICOS de cada concurso.
       NUNCA use "Varios Cargos" ou "Vários Cargos" — liste todos os cargos
       individuais mencionados.
    3. NUNCA use "ex:" antes dos valores dos campos.
       Os valores abaixo com "ex:" sao APENAS ilustrativos.
       Preencha com dados REAIS extraidos do texto, sem prefixo "ex:".
    4. NUNCA copie os textos de exemplo para os valores.
       "Nome do orgao", "cargo 1", "R$ X.XXX,XX", "DD/MM/YYYY",
       "URL completa", "Local (ex: ...)" sao EXEMPLOS — nao os use.
       Se um dado nao for encontrado, use null (mas tente extrair de verdade).
    5. Links relativos (que comecam com /): prefixe com {base_url}

    Formato da resposta:
    {{"concursos": [
      {{
        "instituicao": "Prefeitura de Sao Paulo",
        "orgao": "SP, Sao Paulo - SP",
        "cargos": ["Analista de Sistemas", "Professor de Ingles"],
        "salario_maximo": "R$ 5.000,00",
        "link_edital": "https://www.exemplo.com/concurso/edital",
        "data_encerramento": "30/06/2026",
        "data_publicacao": "01/06/2026",
        "status": "aberto"
      }}
    ]}}

    Extraia TODOS os concursos publicos mencionados no texto. Max 40 concursos.

    TEXTO:
    {text}
""").strip()


def _html_to_clean_text(html: str, max_chars: int = 12000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "head", "iframe"]):
        tag.decompose()

    # Preserva href dos links: <a href="URL">texto</a> → "texto (URL)"
    for a in soup.find_all("a"):
        href = a.get("href", "").strip()
        if href and not href.startswith("#"):
            # Coloca a URL entre parenteses ao lado do texto
            a.insert_after(f" ({href})")

    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:max_chars]


PLACEHOLDER_PATTERNS = [
    r"^ex:\s*",                            # ex: Prefeitura de Sao Paulo
    r"nome\s+do\s+[oó]rg[aã]o",          # Nome do orgao / Órgão
    r"cargo\s*[0-9]",                      # cargo 1, cargo2
    r"r\$\s*x\.xxx,xx",                    # R$ X.XXX,XX ou null
    r"dd/mm/yyyy",                         # DD/MM/YYYY ou null
    r"url\s+completa",                     # URL completa
    r"local\s+\(ex:",                      # Local (ex: ...)
    r"v[áaã]rios\s+cargos",               # Vários / Varios / Vários Cargos
]


def _repair_truncated_json(raw: str) -> str:
    """Tenta reparar JSON truncado (unterminated string, falta de colchetes/chaves)."""
    # Se o JSON já é válido, retorna como está
    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        pass

    # Fecha strings não terminadas no final
    # Se a última aspa está aberta, adiciona aspas de fechamento
    in_string = False
    escape = False
    for ch in raw:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string

    if in_string:
        raw += '"'

    # Fecha colchetes e chaves pendentes
    # Conta quantos de cada abriram mas não fecharam
    stack = []
    in_str = False
    esc = False
    for ch in raw:
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in "[{":
            stack.append(ch)
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()

    # Fecha na ordem inversa
    closer = {"[": "]", "{": "}"}
    for opener in reversed(stack):
        raw += closer[opener]

    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        return raw  # Devolve original se não conseguiu reparar


def _is_placeholder(value: str) -> bool:
    """Verifica se um valor corresponde a padroes de placeholder."""
    if not value:
        return False
    return any(re.search(p, value, re.IGNORECASE) for p in PLACEHOLDER_PATTERNS)


def extract_concursos_from_html(html: str, base_url: str, fonte: str, max_chars: int = 8000) -> list[dict]:
    text = _html_to_clean_text(html, max_chars)
    if len(text.strip()) < 100:
        logger.warning(f"[{fonte}] Texto muito curto, pulando extração")
        return []

    prompt = EXTRACT_PROMPT.format(base_url=base_url, text=text)

    model = os.environ.get("OPENROUTER_EXTRACTION_MODEL", "openrouter/free")

    try:
        raw = generate(prompt, model=model, max_tokens=8192) or ""
    except Exception as e:
        logger.error(f"[{fonte}] LLM API error: {e}")
        return []

    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())

    raw_repaired = _repair_truncated_json(raw)
    if raw_repaired != raw:
        logger.info(f"[{fonte}] JSON truncado reparado ({len(raw)} → {len(raw_repaired)} chars)")
        raw = raw_repaired

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
    n_dropped_null = 0
    n_dropped_placeholder = 0
    n_dropped_cargos = 0
    for c in concursos:
        if not c.get("instituicao") or not c.get("link_edital"):
            n_dropped_null += 1
            continue

        # Rejeita entradas com valores placeholder
        if _is_placeholder(c.get("instituicao", "")):
            n_dropped_placeholder += 1
            continue
        if _is_placeholder(c.get("link_edital", "")):
            n_dropped_placeholder += 1
            continue

        c["fonte"] = fonte
        c["status"] = c.get("status", "aberto")
        c["cargos"] = c.get("cargos") or []

        # Filtra cargos placeholder
        cargos_ok = [cg for cg in c["cargos"] if not _is_placeholder(cg)]
        n_dropped_cargos += len(c["cargos"]) - len(cargos_ok)
        c["cargos"] = cargos_ok

        result.append(c)

    extra = f"(null={n_dropped_null}, placeholder={n_dropped_placeholder}, cargos_placeholder={n_dropped_cargos})"
    logger.info(f"[{fonte}] LLM retornou {len(concursos)} no JSON, {len(result)} apos validacao {extra}")
    return result


def extract_concursos_from_text(text: str, base_url: str, fonte: str) -> list[dict]:
    return extract_concursos_from_html(f"<pre>{text}</pre>", base_url=base_url, fonte=fonte)
