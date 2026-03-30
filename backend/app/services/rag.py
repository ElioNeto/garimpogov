"""RAG service: embedding generation and vector similarity search."""

import logging
from typing import Any

import google.generativeai as genai
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "models/text-embedding-004"
CHAT_MODEL = "gemini-1.5-flash"
EMBEDDING_DIM = 768


def _configure_genai() -> None:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_embedding(text_input: str) -> list[float]:
    """Generate a 768-dimensional embedding using text-embedding-004."""
    _configure_genai()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text_input,
        task_type="RETRIEVAL_QUERY",
    )
    return result["embedding"]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_document_embedding(text_input: str) -> list[float]:
    """Generate embedding for document chunks (RETRIEVAL_DOCUMENT task)."""
    _configure_genai()
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text_input,
        task_type="RETRIEVAL_DOCUMENT",
    )
    return result["embedding"]


async def vector_search(
    db: AsyncSession,
    concurso_id: str,
    query_embedding: list[float],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Perform cosine similarity search on edital_chunks filtered by concurso_id."""
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
    query = text(
        """
        SELECT id, content, chunk_index,
               1 - (embedding <=> :embedding::vector) AS similarity
        FROM edital_chunks
        WHERE concurso_id = :concurso_id
        ORDER BY embedding <=> :embedding::vector
        LIMIT :limit
        """
    )
    result = await db.execute(
        query,
        {
            "embedding": embedding_str,
            "concurso_id": concurso_id,
            "limit": limit,
        },
    )
    rows = result.fetchall()
    return [
        {
            "id": str(row.id),
            "content": row.content,
            "chunk_index": row.chunk_index,
            "similarity": float(row.similarity),
        }
        for row in rows
    ]


def build_rag_prompt(question: str, context_chunks: list[dict[str, Any]]) -> str:
    """Build a RAG prompt from the question and retrieved context chunks."""
    context = "\n\n---\n\n".join(
        f"Trecho {i+1}:\n{chunk['content']}"
        for i, chunk in enumerate(context_chunks)
    )
    return f"""Você é um assistente especializado em concursos públicos brasileiros.
Responda à pergunta do usuário com base APENAS nos trechos do edital fornecidos abaixo.
Se a informação não estiver nos trechos, diga que não encontrou essa informação no edital.

TRECHOS DO EDITAL:
{context}

PERGUNTA DO USUÁRIO:
{question}

RESPOSTA:"""


async def stream_chat_response(
    db: AsyncSession,
    concurso_id: str,
    question: str,
):
    """Async generator that yields SSE-formatted text chunks from Gemini."""
    _configure_genai()

    # 1. Embed the question
    try:
        query_embedding = generate_embedding(question)
    except Exception as e:
        logger.error("Embedding generation failed: %s", e)
        yield f'data: {{"type": "error", "content": "Falha ao gerar embedding."}}\'\n\n'
        return

    # 2. Vector search
    try:
        chunks = await vector_search(db, concurso_id, query_embedding)
    except Exception as e:
        logger.error("Vector search failed: %s", e)
        yield 'data: {"type": "error", "content": "Falha na busca vetorial."}\n\n'
        return

    if not chunks:
        yield 'data: {"type": "text", "content": "N\\u00e3o encontrei trechos relevantes neste edital para responder sua pergunta."}\n\n'
        yield 'data: {"type": "done", "content": ""}\n\n'
        return

    # 3. Build prompt and stream Gemini response
    prompt = build_rag_prompt(question, chunks)
    model = genai.GenerativeModel(CHAT_MODEL)

    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                import json
                text_escaped = json.dumps(chunk.text)
                yield f'data: {{"type": "text", "content": {text_escaped}}}\n\n'
    except Exception as e:
        logger.error("Gemini streaming failed: %s", e)
        yield 'data: {"type": "error", "content": "Falha ao gerar resposta."}\n\n'
        return

    yield 'data: {"type": "done", "content": ""}\n\n'
