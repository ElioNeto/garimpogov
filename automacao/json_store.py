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
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "concursos.json")


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
    # Checa "ex:" prefix
    if re.search(r"^ex:\s*", inst, re.IGNORECASE):
        return True
    if re.search(r"^ex:\s*", link, re.IGNORECASE):
        return True
    for cg in cargos:
        if re.search(r"^ex:\s*", str(cg), re.IGNORECASE):
            return True
    # Checa placeholders clássicos
    if re.search(r"nome\s+do\s+[oó]rg[aã]o", inst, re.IGNORECASE):
        return True
    if re.search(r"url\s+completa", link, re.IGNORECASE):
        return True
    return False


def purge_stale() -> int:
    """Remove entradas antigas com dados placeholder do JSON store."""
    existing = load_all()
    before = len(existing)
    existing = [c for c in existing if not _is_stale(c)]
    if len(existing) < before:
        save_all(existing)
        logger.info(f"Limpadas {before - len(existing)} entradas com placeholder")
    return before - len(existing)


def merge_new(new_concursos: list[dict]) -> list[dict]:
    """Faz merge dos novos concursos com os existentes, deduplicando.

    Args:
        new_concursos: Lista de concursos recem-coletados.

    Returns:
        Lista de concursos que foram realmente adicionados (não duplicatas).
    """
    existing = load_all()
    existing_keys = {_dedup_key(c) for c in existing}

    newly_added = []
    for c in new_concursos:
        key = _dedup_key(c)
        if key in existing_keys:
            logger.debug(f"Já existe: {key}")
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
        logger.info(f"Adicionados {len(newly_added)} novos concursos")
    else:
        logger.info("Nenhum concurso novo para adicionar")

    return newly_added
