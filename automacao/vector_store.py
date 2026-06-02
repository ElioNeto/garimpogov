"""Vector store: embed chunks (local sentence-transformers) e insere no PostgreSQL com pgvector."""
from __future__ import annotations

import logging
import math
import os
import uuid
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import psycopg2

from automacao.embeddings import embed_chunks_batch, embed_text, get_embedding_dim

logger = logging.getLogger(__name__)

# B30: cache de conexão para evitar reconectar a cada chamada
_db_connection = None

EMBEDDING_DIM = get_embedding_dim()


def _normalize_db_url(url: str) -> str:
    """Converte URL async (postgresql+asyncpg://) para síncrona (postgresql://).

    Mantida local para evitar dependência de sqlalchemy no ambiente de ingestão.
    Adiciona sslmode=require se não especificado (Railway exige SSL).
    """
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql://", 1)

    # Garantir sslmode=require se não estiver especificado
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if "sslmode" not in qs:
        qs["sslmode"] = ["require"]
        new_query = urlencode(qs, doseq=True)
        url = urlunparse(parsed._replace(query=new_query))

    return url


def get_db_connection():
    global _db_connection
    if _db_connection is None or _db_connection.closed:
        db_url = _normalize_db_url(os.environ["DATABASE_URL"])
        # Log seguro (sem password)
        p = urlparse(db_url)
        masked_netloc = f"{p.username}:****@{p.hostname}"
        if p.port:
            masked_netloc += f":{p.port}"
        safe_url = urlunparse(p._replace(netloc=masked_netloc))
        logger.info(f"Conectando ao banco: {safe_url}")
        try:
            _db_connection = psycopg2.connect(db_url)
        except psycopg2.OperationalError as e:
            logger.error(f"Falha ao conectar no banco: {e}")
            logger.error(
                "Verifique se o banco está acessível e se DATABASE_URL está correta. "
                "Railway requer SSL — sslmode=require será adicionado automaticamente."
            )
            raise
    return _db_connection


def close_db_connection():
    global _db_connection
    if _db_connection is not None and not _db_connection.closed:
        _db_connection.close()
    _db_connection = None


def _sanitize_embedding(embedding: list[float]) -> list[float]:
    """Replace NaN/Infinity with 0.0 to avoid SQL errors."""
    return [0.0 if math.isnan(v) or math.isinf(v) else v for v in embedding]


def _embedding_to_sql_vector(embedding: list[float]) -> str:
    """Convert a list of floats to a PostgreSQL vector literal safely."""
    cleaned = _sanitize_embedding(embedding)
    return "[" + ",".join(str(v) for v in cleaned) + "]"


def embed_chunk(text: str) -> list[float]:
    return embed_text(text)


def concurso_exists(conn, link_edital: str) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM concursos WHERE link_edital = %s", (link_edital,))
        row = cur.fetchone()
        return str(row[0]) if row else None


def insert_concurso(conn, data: dict) -> str:
    concurso_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO concursos
                (id, instituicao, orgao, status, link_edital, pdf_url,
                 salario_maximo, data_encerramento, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """,
            (
                concurso_id,
                data.get("instituicao", "N/A"),
                data.get("orgao"),
                data.get("status", "aberto"),
                data["link_edital"],
                data.get("pdf_url"),
                data.get("salario_maximo_float"),
                data.get("data_encerramento_dt"),
            ),
        )
        for cargo_nome in data.get("cargos") or []:
            cur.execute(
                "INSERT INTO cargos (id, concurso_id, nome) VALUES (%s, %s, %s)",
                (str(uuid.uuid4()), concurso_id, cargo_nome),
            )
    conn.commit()
    return concurso_id


def embed_chunks_batch_wrapper(texts: list[str]) -> list[list[float]]:
    """Wrapper que usa sentence-transformers em lote."""
    if not texts:
        return []
    try:
        return embed_chunks_batch(texts)
    except Exception as e:
        logger.error(f"Erro no batch embedding: {e}")
        # Fallback: individual
        return [embed_text(t) for t in texts]


def insert_chunks(conn, concurso_id: str, chunks: list[str]) -> int:
    inserted = 0
    if not chunks:
        return 0

    logger.info(f"Gerando embeddings para {len(chunks)} chunks em lote...")
    embeddings = embed_chunks_batch_wrapper(chunks)

    with conn.cursor() as cur:
        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            try:
                embedding_str = _embedding_to_sql_vector(embedding)
                cur.execute(
                    """
                    INSERT INTO edital_chunks
                        (id, concurso_id, content, chunk_index, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector)
                    """,
                    (str(uuid.uuid4()), concurso_id, chunk_text, i, embedding_str),
                )
                inserted += 1
                if (i + 1) % 10 == 0:
                    conn.commit()
            except Exception as e:
                logger.error(f"Erro inserindo chunk {i}: {e}")
    conn.commit()
    return inserted
