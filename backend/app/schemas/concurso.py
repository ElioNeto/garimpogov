import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CargoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    vagas: Optional[int] = None
    salario: Optional[float] = None
    requisitos: Optional[str] = None


class ConcursoBase(BaseModel):
    instituicao: str
    orgao: Optional[str] = None
    status: str = "aberto"
    link_edital: str
    pdf_url: Optional[str] = None
    salario_maximo: Optional[float] = None
    data_encerramento: Optional[datetime] = None


class ConcursoCreate(ConcursoBase):
    pass


class ConcursoSchema(ConcursoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    cargos: list[CargoSchema] = []


class ConcursoListSchema(ConcursoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class PaginatedConcursos(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ConcursoListSchema]


class ChatRequest(BaseModel):
    question: str


class ChatChunk(BaseModel):
    text: str
    done: bool = False
