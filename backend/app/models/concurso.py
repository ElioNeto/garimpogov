import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Concurso(Base):
    __tablename__ = "concursos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instituicao: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    orgao: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="aberto", index=True
    )  # aberto | encerrado | em_analise
    link_edital: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    link_pdf_r2: Mapped[str | None] = mapped_column(Text, nullable=True)
    salario_maximo: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salario_minimo: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    data_encerramento: Mapped[date | None] = mapped_column(Date, nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    cargos: Mapped[list["Cargo"]] = relationship(
        "Cargo", back_populates="concurso", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["EditalChunk"]] = relationship(  # type: ignore[name-defined]
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
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    vagas: Mapped[int | None] = mapped_column(nullable=True)
    salario: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    escolaridade: Mapped[str | None] = mapped_column(String(100), nullable=True)

    concurso: Mapped["Concurso"] = relationship("Concurso", back_populates="cargos")
