"""Vector store: embed chunks e insere no PostgreSQL com pgvector."""
import logging
import os
import uuid
from typing import Optional

import google.generativeai as genai
import psycopg2
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
EMBEDDING_MODEL = "models/text-embedding-004"


def _normalize_db_url(url: str) -> str:
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg2://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


def get_db_connection():
    db_url = _normalize_db_url(os.environ["DATABASE_URL"])
    return psycopg2.connect(db_url)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def embed_chunk(text: str) -> list[float]:
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document",
    )
    return result["embedding"]


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


def insert_chunks(conn, concurso_id: str, chunks: list[str]) -> int:
    inserted = 0
    with conn.cursor() as cur:
        for i, chunk_text in enumerate(chunks):
            try:
                embedding = embed_chunk(chunk_text)
                embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
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
                logger.error(f"Erro embedding chunk {i}: {e}")
    conn.commit()
    return inserted
