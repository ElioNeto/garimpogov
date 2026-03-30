import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.concurso import Concurso
from app.schemas.concurso import ChatRequest
from app.services.rag import stream_chat_response

router = APIRouter(prefix="/chat", tags=["chat"])


async def event_generator(
    db: AsyncSession, concurso_id: str, question: str
) -> AsyncIterator[str]:
    try:
        async for text_chunk in stream_chat_response(db, concurso_id, question):
            data = json.dumps({"text": text_chunk, "done": False})
            yield f"data: {data}\n\n"
        yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"
    except Exception as e:
        error_data = json.dumps({"error": str(e), "done": True})
        yield f"data: {error_data}\n\n"


@router.post("/{concurso_id}")
async def chat_with_edital(
    concurso_id: uuid.UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Concurso).where(Concurso.id == concurso_id)
    result = await db.execute(stmt)
    concurso = result.scalar_one_or_none()

    if not concurso:
        raise HTTPException(status_code=404, detail="Concurso nao encontrado")

    return StreamingResponse(
        event_generator(db, str(concurso_id), request.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
