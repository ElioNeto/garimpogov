import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CargoBase(BaseModel):
    nome: str
    vagas: Optional[int] = None
    salario: Optional[float] = None
    escolaridade: Optional[str] = None


class CargoRead(CargoBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    concurso_id: uuid.UUID


class ConcursoBase(BaseModel):
    instituicao: str
    orgao: Optional[str] = None
    status: str = "aberto"
    link_edital: str
    salario_maximo: Optional[float] = None
    salario_minimo: Optional[float] = None
    data_encerramento: Optional[date] = None
    descricao: Optional[str] = None


class ConcursoRead(ConcursoBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    link_pdf_r2: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConcursoDetail(ConcursoRead):
    cargos: list[CargoRead] = []


class ConcursoListResponse(BaseModel):
    items: list[ConcursoRead]
    total: int
    page: int
    page_size: int
    pages: int
