import logging
from typing import AsyncIterator

import google.generativeai as genai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)

EMBEDDING_MODEL = "models/text-embedding-004"
GENERATION_MODEL = "gemini-1.5-flash"
TOP_K = 5


def embed_text(text_input: str) -> list[float]:
    """Generate embedding using Google text-embedding-004 (768 dims)."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text_input,
        task_type="retrieval_query",
    )
    return result["embedding"]


async def similarity_search(
    db: AsyncSession, concurso_id: str, query_embedding: list[float], top_k: int = TOP_K
) -> list[str]:
    """Find most similar chunks using cosine distance (<=>)."""
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
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
    query_embedding = embed_text(question)
    chunks = await similarity_search(db, concurso_id, query_embedding)

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

    model = genai.GenerativeModel(GENERATION_MODEL)
    response = model.generate_content(prompt, stream=True)

    for chunk in response:
        if chunk.text:
            yield chunk.text
