from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Pergunta do candidato sobre o edital (max 2000 caracteres)",
    )


class ChatChunk(BaseModel):
    type: str  # 'text' | 'done' | 'error'
    content: str
