"""Armazena concursos em JSON no repositório (substitui o PostgreSQL).

Estrutura do arquivo data/concursos.json:
{
  "meta": {
    "ultima_coleta": "2026-06-02T12:00:00",
    "total_concursos": 42
  },
  "concursos": [ ... ]
}

Cada concurso é deduplicado por link_edital.
Concursos com data_encerramento vencida são removidos automaticamente.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, date, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_MODULE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "concursos.json")


# ── Utilitários de data ──────────────────────────────────────────────

def _parse_br_date(date_str: str) -> Optional[date]:
    """Tenta converter string DD/MM/YYYY ou DD/MM/AA para date.
    Retorna None se não conseguir parsear.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    # Tenta DD/MM/YYYY
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _is_date_passed(date_str: str) -> bool:
    """Verifica se a data de encerramento já passou (hoje inclusive)."""
    parsed = _parse_br_date(date_str)
    if parsed is None:
        return False  # Não conseguiu parsear → assume que ainda está aberto
    return parsed <= date.today()


# ── Gerenciamento do arquivo ─────────────────────────────────────────

def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_all() -> list[dict]:
    """Carrega todos os concursos do arquivo JSON."""
    _ensure_data_dir()
    if not os.path.exists(DATA_FILE):
        logger.info("Arquivo JSON ainda não existe, retornando lista vazia")
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("concursos", [])
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Erro ao ler {DATA_FILE}: {e}. Começando do zero.")
        return []


def save_all(concursos: list[dict]) -> None:
    """Salva a lista completa de concursos no arquivo JSON."""
    _ensure_data_dir()
    meta = {
        "ultima_coleta": datetime.now(timezone.utc).isoformat(),
        "total_concursos": len(concursos),
    }
    data = {"meta": meta, "concursos": concursos}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Salvos {len(concursos)} concursos em {DATA_FILE}")


# ── Consulta / Busca ─────────────────────────────────────────────────

def concurso_exists(link_edital: str) -> bool:
    """Verifica se um concurso com o link já existe no JSON (busca exata por link_edital)."""
    concursos = load_all()
    return any(c.get("link_edital") == link_edital for c in concursos)


def get_by_dedup_key(c: dict) -> dict | None:
    """Busca concurso existente pela chave de dedup."""
    key = _dedup_key(c)
    for existing in load_all():
        if _dedup_key(existing) == key:
            return existing
    return None


def _dedup_key(c: dict) -> str:
    """Gera chave única para deduplicação.

    Usa link_edital se disponível, senão compõe (fonte + instituicao).
    """
    link = c.get("link_edital") or ""
    if link:
        return f"link:{link}"
    fonte = c.get("fonte") or ""
    inst = c.get("instituicao") or ""
    return f"fallback:{fonte}|{inst}"


def _is_stale(c: dict) -> bool:
    """Verifica se um concurso contém valores placeholder que deveriam ter sido rejeitados."""
    inst = c.get("instituicao", "") or ""
    link = c.get("link_edital", "") or ""
    cargos = c.get("cargos") or []

    # Rejeita se instituicao estiver vazia ou for placeholder
    if not inst.strip():
        return True
    if re.search(r"^ex:\s*", inst, re.IGNORECASE):
        return True
    if re.search(r"nome\s+do\s+[oó]rg[aã]o", inst, re.IGNORECASE):
        return True

    # Rejeita link vazio, placeholder ou exemplo
    if not link.strip():
        return True
    if re.search(r"^ex:\s*", link, re.IGNORECASE):
        return True
    if re.search(r"url\s+completa", link, re.IGNORECASE):
        return True
    if re.search(r"exemplo\.com", link, re.IGNORECASE):
        return True
    if re.search(r"^(null|none|n/a|nao\s+informado)$", link.strip(), re.IGNORECASE):
        return True

    # Rejeita cargos com placeholder
    for cg in cargos:
        if not isinstance(cg, str):
            return True
        if re.search(r"^ex:\s*", cg, re.IGNORECASE):
            return True
        if re.search(r"^cargo\s*[0-9]", cg, re.IGNORECASE):
            return True

    return False


def _is_closed(c: dict) -> bool:
    """Verifica se um concurso já está com inscrições encerradas.

    Considera encerrado se:
    - status for 'fechado' ou 'encerrado'
    - data_encerramento já passou (hoje inclusive)
    """
    status = (c.get("status") or "").strip().lower()
    if status in ("fechado", "encerrado", "closed"):
        return True

    data_enc = c.get("data_encerramento")
    if data_enc and _is_date_passed(data_enc):
        return True

    return False


def _is_valid_concurso(c: dict) -> bool:
    """Valida se um concurso tem dados mínimos para ser armazenado.

    Rejeita concursos:
    - Com placeholders (instituicao, link_edital, cargos)
    - Com link_edital de exemplo
    - Já encerrados (data_encerramento no passado)
    - Sem instituicao ou link_edital
    """
    if not c.get("instituicao") or not c.get("link_edital"):
        return False
    if _is_stale(c):
        return False
    if _is_closed(c):
        return False
    return True


# ── Limpeza ──────────────────────────────────────────────────────────

def purge_stale() -> int:
    """Remove entradas antigas com dados placeholder do JSON store."""
    existing = load_all()
    before = len(existing)
    existing = [c for c in existing if not _is_stale(c)]
    if len(existing) < before:
        save_all(existing)
        logger.info(f"Limpadas {before - len(existing)} entradas com placeholder")
    return before - len(existing)


def purge_closed() -> int:
    """Remove concursos cuja data_encerramento já passou (inscrições encerradas)."""
    existing = load_all()
    before = len(existing)
    existing = [c for c in existing if not _is_closed(c)]
    n_closed = before - len(existing)
    if n_closed > 0:
        save_all(existing)
        logger.info(f"Removidos {n_closed} concursos com inscrições encerradas")
    return n_closed


def purge_all() -> dict[str, int]:
    """Executa todas as rotinas de limpeza e retorna contagem de removidos.

    Returns:
        {"stale": N, "closed": M, "total": N+M}
    """
    n_stale = purge_stale()
    n_closed = purge_closed()
    return {"stale": n_stale, "closed": n_closed, "total": n_stale + n_closed}


# ── Merge ────────────────────────────────────────────────────────────

def merge_new(new_concursos: list[dict]) -> list[dict]:
    """Faz merge dos novos concursos com os existentes, deduplicando.

    Regras:
    - Concurso já existente (mesmo link_edital) → ignorado
    - Concurso com data_encerramento vencida → ignorado
    - Concurso com placeholder/stale → ignorado

    Args:
        new_concursos: Lista de concursos recem-coletados.

    Returns:
        Lista de concursos que foram realmente adicionados (não duplicatas).
    """
    existing = load_all()
    existing_keys = {_dedup_key(c) for c in existing}

    newly_added = []
    n_duplicates = 0
    n_closed = 0
    n_stale = 0

    for c in new_concursos:
        # Pula concursos inválidos (placeholder, fechados, sem dados mínimos)
        if not _is_valid_concurso(c):
            if _is_closed(c):
                n_closed += 1
            else:
                n_stale += 1
            continue

        key = _dedup_key(c)
        if key in existing_keys:
            n_duplicates += 1
            continue

        # Garante que tem ID e timestamp
        c["id"] = c.get("id") or str(uuid.uuid4())
        c["data_coleta"] = datetime.now(timezone.utc).isoformat()
        c["data_publicacao"] = c.get("data_publicacao") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        existing.append(c)
        existing_keys.add(key)
        newly_added.append(c)

    if newly_added:
        save_all(existing)
        logger.info(
            f"Merge: +{len(newly_added)} novos | "
            f"{n_duplicates} duplicatas ignoradas | "
            f"{n_closed} fechados ignorados | "
            f"{n_stale} placeholders ignorados"
        )
    else:
        logger.info(
            f"Merge: nenhum novo concurso "
            f"({n_duplicates} duplicatas, {n_closed} fechados, {n_stale} placeholders)"
        )

    return newly_added
