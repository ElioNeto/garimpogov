"""RAG pipeline: embedding local + vector search + OpenRouter streaming (free).

Embedding: sentence-transformers (multilingual, local, sem API, sem custo).
Chat:     OpenRouter com modelo gratuito (openrouter/free → auto-routing).
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Embedding local (sentence-transformers)
# ---------------------------------------------------------------------------
_EMBEDDING_MODEL = None
_EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = settings.RAG_TOP_K


def _get_embedder():
    """Lazy-load do modelo sentence-transformers."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        from sentence_transformers import SentenceTransformer

        logger.info(f"Carregando modelo de embedding: {_EMBEDDING_MODEL_NAME}")
        _EMBEDDING_MODEL = SentenceTransformer(_EMBEDDING_MODEL_NAME)
    return _EMBEDDING_MODEL


def _sanitize_embedding(embedding: list[float]) -> list[float]:
    """Replace NaN/Infinity with 0.0 to avoid SQL errors."""
    return [0.0 if math.isnan(v) or math.isinf(v) else v for v in embedding]


def _embedding_to_sql_vector(embedding: list[float]) -> str:
    """Convert a list of floats to a PostgreSQL vector literal safely."""
    cleaned = _sanitize_embedding(embedding)
    return "[" + ",".join(str(v) for v in cleaned) + "]"


def embed_text(text_input: str) -> list[float]:
    """Generate embedding using local sentence-transformers."""
    model = _get_embedder()
    vec = model.encode(text_input, normalize_embeddings=True)
    return vec.tolist()


# ---------------------------------------------------------------------------
# Similarity search (pgvector)
# ---------------------------------------------------------------------------


async def similarity_search(
    db: AsyncSession, concurso_id: str, query_embedding: list[float], top_k: int = TOP_K
) -> list[str]:
    """Find most similar chunks using cosine distance (<=>)."""
    embedding_str = _embedding_to_sql_vector(query_embedding)
    stmt = text(
        """
        SELECT content
        FROM edital_chunks
        WHERE concurso_id = :concurso_id
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
        """
    )
    result = await db.execute(
        stmt,
        {"concurso_id": concurso_id, "embedding": embedding_str, "top_k": top_k},
    )
    rows = result.fetchall()
    return [row[0] for row in rows]


# ---------------------------------------------------------------------------
# Chat streaming (OpenRouter)
# ---------------------------------------------------------------------------


async def stream_chat_response(
    db: AsyncSession, concurso_id: str, question: str
) -> AsyncIterator[str]:
    """RAG pipeline: embed question → retrieve chunks → stream OpenRouter answer."""
    try:
        query_embedding = embed_text(question)
    except Exception as e:
        logger.error(f"Erro ao gerar embedding: {e}")
        yield "Desculpe, ocorreu um erro ao processar sua pergunta. Tente novamente mais tarde."
        return

    try:
        chunks = await similarity_search(db, concurso_id, query_embedding)
    except Exception as e:
        logger.error(f"Erro na busca por similaridade: {e}")
        yield "Desculpe, ocorreu um erro ao buscar informacoes no edital. Tente novamente mais tarde."
        return

    if not chunks:
        context = "Nenhum trecho do edital encontrado."
    else:
        context = "\n\n---\n\n".join(chunks)

    prompt = f"""Voce e um assistente especialista em concursos publicos brasileiros.
Responda a pergunta do candidato com base apenas no contexto do edital fornecido abaixo.
Se a resposta nao estiver no contexto, diga que nao encontrou essa informacao no edital.

CONTEXTO DO EDITAL:
{context}

PERGUNTA DO CANDIDATO:
{question}

RESPOSTA:"""

    async for chunk in _stream_openrouter(prompt):
        yield chunk


# ---------------------------------------------------------------------------
# Cache de modelos gratuitos (backend)
# ---------------------------------------------------------------------------
_FREE_MODELS_CACHE: list[str] | None = None
_FREE_MODELS_CACHE_TIME: float = 0
_CACHE_TTL = 3600  # 1 hora

_FALLBACK_FREE_MODELS = [
    "openrouter/free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-4-26b-a4b-it:free",
    "qwen/qwen3-coder:free",
]


def _fetch_free_models() -> list[str]:
    """Consulta API do OpenRouter e retorna modelos gratuitos."""
    import httpx

    try:
        resp = httpx.get(
            "https://openrouter.ai/api/v1/models",
            headers={"User-Agent": "GarimpoGov/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        free = []
        for model in data.get("data", []):
            pricing = model.get("pricing", {})
            if pricing.get("prompt") == "0" and pricing.get("completion") == "0":
                free.append(model["id"])

        if free:
            def sort_key(m: str) -> tuple:
                low = m.lower()
                if "google" in low:
                    return (0, m)
                if "llama" in low or "mistral" in low or "phi" in low:
                    return (1, m)
                return (2, m)
            free.sort(key=sort_key)
            logger.info("Modelos free carregados pela API (%d)", len(free))
            return free

        logger.warning("API retornou lista vazia — usando fallback")
    except Exception as e:
        logger.warning("Falha ao buscar modelos free (%s) — usando fallback", e)

    return _FALLBACK_FREE_MODELS.copy()


def _get_free_models() -> list[str]:
    global _FREE_MODELS_CACHE, _FREE_MODELS_CACHE_TIME
    now = time.monotonic()
    if _FREE_MODELS_CACHE is None or (now - _FREE_MODELS_CACHE_TIME) > _CACHE_TTL:
        _FREE_MODELS_CACHE = _fetch_free_models()
        _FREE_MODELS_CACHE_TIME = time.monotonic()
    return _FREE_MODELS_CACHE


def _build_chat_model_list() -> list[str]:
    """Monta lista priorizada para chat."""
    configured = os.environ.get("OPENROUTER_CHAT_MODEL", "openrouter/free")
    all_free = _get_free_models()

    ordered: list[str] = []
    seen: set[str] = set()

    if configured not in seen:
        ordered.append(configured)
        seen.add(configured)

    for m in all_free:
        if m not in seen:
            ordered.append(m)
            seen.add(m)

    return ordered or _FALLBACK_FREE_MODELS.copy()


async def _stream_openrouter(prompt: str) -> AsyncIterator[str]:
    """Stream resposta do OpenRouter com fallback dinâmico entre modelos free."""
    import httpx
    import asyncio

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY não configurada")
        yield "Desculpe, o chat não está configurado. Defina OPENROUTER_API_KEY no ambiente."
        return

    models = _build_chat_model_list()
    headers = {
        "User-Agent": "GarimpoGov/1.0",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    last_error: Exception | None = None

    for i, model in enumerate(models):
        if i > 0:
            logger.warning("Fallback chat para modelo: %s", model)

        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 2048,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=body,
                ) as resp:
                    if resp.status_code == 200:
                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:].strip()
                            if not data_str or data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                        return

                    try:
                        err_body = await resp.aread()
                    except Exception:
                        err_body = b"(could not read)"
                    logger.error(
                        "OpenRouter HTTP %d no modelo %s: %.300s",
                        resp.status_code, model,
                        err_body[:500].decode(errors="replace"),
                    )

                    if resp.status_code == 429 or resp.status_code >= 500:
                        await asyncio.sleep(30)
                        continue

                    break

        except Exception as e:
            last_error = e
            logger.error("Exceção streaming com %s: %s", model, e)
            continue

    yield f"Desculpe, ocorreu um erro ao gerar a resposta. Último erro: {last_error}"
