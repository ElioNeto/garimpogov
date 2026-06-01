"""Vector store: embed chunks e insere no PostgreSQL com pgvector."""
import logging
import math
import os
import uuid
from typing import Optional

from google import genai
from google.genai import types
import psycopg2
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# B36: lazy loading do cliente Gemini
_client_instance = None
EMBEDDING_MODEL = "text-embedding-004"


def _get_client():
    global _client_instance
    if _client_instance is None:
        _client_instance = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client_instance


# B20: usa função centralizada do backend para conversão de URL
# (evita duplicação de lógica entre os dois pipelines)
import sys
import os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "backend"))
from app.core.database import make_sync_url

# B30: cache de conexão para evitar reconectar a cada chamada
_db_connection = None


def get_db_connection():
    global _db_connection
    if _db_connection is None or _db_connection.closed:
        db_url = make_sync_url(os.environ["DATABASE_URL"])
        _db_connection = psycopg2.connect(db_url)
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


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def embed_chunk(text: str) -> list[float]:
    client = _get_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return result.embeddings[0].values


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


def embed_chunks_batch(texts: list[str], batch_size: int = 5) -> list[list[float]]:
    """
    B28: Gera embeddings em lote, reduzindo chamadas à API Gemini.
    O google.genai SDK aceita múltiplos contents em uma única chamada.
    """
    client = _get_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            # O retorno pode ser um único embedding ou lista
            if hasattr(result, "embeddings") and result.embeddings:
                for emb in result.embeddings:
                    all_embeddings.append(emb.values)
            else:
                # Fallback: chamada individual para cada texto
                for t in batch:
                    all_embeddings.append(embed_chunk(t))
        except Exception as e:
            logger.error(f"Erro no batch embedding lote {i//batch_size}: {e}")
            # Fallback: tenta cada chunk individualmente
            for t in batch:
                try:
                    all_embeddings.append(embed_chunk(t))
                except Exception as e2:
                    logger.error(f"Erro embedding chunk individual: {e2}")
                    all_embeddings.append([0.0] * 768)

    return all_embeddings


def insert_chunks(conn, concurso_id: str, chunks: list[str]) -> int:
    inserted = 0
    if not chunks:
        return 0

    # Gera embeddings em lote (B28)
    logger.info(f"Gerando embeddings para {len(chunks)} chunks em lote...")
    embeddings = embed_chunks_batch(chunks)

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
