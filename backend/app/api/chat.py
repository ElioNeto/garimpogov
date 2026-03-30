"""Chat endpoint with Server-Sent Events streaming via Gemini RAG."""

import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.deps import DbSession
from app.models.concurso import Concurso
from app.schemas.chat import ChatRequest
from app.services.rag import stream_chat_response

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{concurso_id}")
async def chat(
    concurso_id: uuid.UUID,
    request: ChatRequest,
    db: DbSession,
) -> StreamingResponse:
    # Verify the concurso exists
    stmt = select(Concurso).where(Concurso.id == concurso_id)
    result = await db.execute(stmt)
    concurso = result.scalar_one_or_none()

    if concurso is None:
        raise HTTPException(status_code=404, detail="Concurso não encontrado")

    if not request.question.strip():
        raise HTTPException(status_code=422, detail="A pergunta não pode estar vazia")

    return StreamingResponse(
        stream_chat_response(db, str(concurso_id), request.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
