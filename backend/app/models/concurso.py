import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Concurso(Base):
    __tablename__ = "concursos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instituicao: Mapped[str] = mapped_column(String(500), nullable=False)
    orgao: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # aberto | encerrado | suspenso
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="aberto")
    link_edital: Mapped[str] = mapped_column(String(2000), unique=True, nullable=False)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    salario_maximo: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    data_encerramento: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    cargos: Mapped[list["Cargo"]] = relationship(
        "Cargo", back_populates="concurso", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["EditalChunk"]] = relationship(
        "EditalChunk", back_populates="concurso", cascade="all, delete-orphan"
    )


class Cargo(Base):
    __tablename__ = "cargos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    concurso_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concursos.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(500), nullable=False)
    vagas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salario: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    requisitos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    concurso: Mapped["Concurso"] = relationship("Concurso", back_populates="cargos")


class EditalChunk(Base):
    __tablename__ = "edital_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    concurso_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("concursos.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # 768 dimensions for text-embedding-004
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=True)

    concurso: Mapped["Concurso"] = relationship("Concurso", back_populates="chunks")
