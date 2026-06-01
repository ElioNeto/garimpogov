"""RAG pipeline: embedding, vector search, and Gemini streaming.

B6: Migrado de google.generativeai para google.genai (SDK unificado).
"""
import logging
import math
from typing import AsyncIterator

from google import genai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# B36: lazy loading da API key (não configura no import do módulo)
_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


# Usa valores do config centralizado (B26)
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
GENERATION_MODEL = settings.GENERATION_MODEL
TOP_K = settings.RAG_TOP_K


def _sanitize_embedding(embedding: list[float]) -> list[float]:
    """Replace NaN/Infinity with 0.0 to avoid SQL errors."""
    return [0.0 if math.isnan(v) or math.isinf(v) else v for v in embedding]


def _embedding_to_sql_vector(embedding: list[float]) -> str:
    """Convert a list of floats to a PostgreSQL vector literal safely."""
    cleaned = _sanitize_embedding(embedding)
    return "[" + ",".join(str(v) for v in cleaned) + "]"


def embed_text(text_input: str) -> list[float]:
    """Generate embedding using Google text-embedding-004 (768 dims)."""
    client = _get_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text_input,
        config={"task_type": "retrieval_query"},
    )
    return result.embeddings[0].values


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


async def stream_chat_response(
    db: AsyncSession, concurso_id: str, question: str
) -> AsyncIterator[str]:
    """RAG pipeline: embed question -> retrieve chunks -> stream Gemini answer."""
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

    try:
        client = _get_client()
        response = client.models.generate_content_stream(
            model=GENERATION_MODEL,
            contents=prompt,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        logger.error(f"Erro na geracao Gemini: {e}")
        yield "Desculpe, ocorreu um erro ao gerar a resposta. Verifique se a API Gemini esta configurada corretamente."
