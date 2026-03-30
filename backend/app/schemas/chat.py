from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class ChatChunk(BaseModel):
    type: str  # 'text' | 'done' | 'error'
    content: str
