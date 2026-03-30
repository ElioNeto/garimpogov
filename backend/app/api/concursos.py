"""Endpoints for listing and retrieving concursos."""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.core.deps import DbSession
from app.models.concurso import Cargo, Concurso
from app.schemas.concurso import ConcursoDetail, ConcursoListResponse, ConcursoRead

router = APIRouter(prefix="/concursos", tags=["concursos"])


@router.get("", response_model=ConcursoListResponse)
async def list_concursos(
    db: DbSession,
    orgao: Optional[str] = Query(None, description="Filtrar por órgão"),
    status: Optional[str] = Query(None, description="Filtrar por status (aberto/encerrado)"),
    salario_min: Optional[float] = Query(None, description="Salário mínimo"),
    salario_max: Optional[float] = Query(None, description="Salário máximo"),
    data_encerramento_ate: Optional[str] = Query(None, description="Data de encerramento até (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ConcursoListResponse:
    stmt = select(Concurso)

    if orgao:
        stmt = stmt.where(Concurso.orgao.ilike(f"%{orgao}%"))
    if status:
        stmt = stmt.where(Concurso.status == status)
    if salario_min is not None:
        stmt = stmt.where(Concurso.salario_maximo >= salario_min)
    if salario_max is not None:
        stmt = stmt.where(Concurso.salario_maximo <= salario_max)
    if data_encerramento_ate:
        stmt = stmt.where(Concurso.data_encerramento <= data_encerramento_ate)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    stmt = stmt.order_by(Concurso.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    import math
    return ConcursoListResponse(
        items=[ConcursoRead.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if page_size > 0 else 0,
    )


@router.get("/{concurso_id}", response_model=ConcursoDetail)
async def get_concurso(concurso_id: uuid.UUID, db: DbSession) -> ConcursoDetail:
    stmt = select(Concurso).where(Concurso.id == concurso_id)
    result = await db.execute(stmt)
    concurso = result.scalar_one_or_none()

    if concurso is None:
        raise HTTPException(status_code=404, detail="Concurso não encontrado")

    # Load cargos
    cargos_stmt = select(Cargo).where(Cargo.concurso_id == concurso_id)
    cargos_result = await db.execute(cargos_stmt)
    concurso.cargos = list(cargos_result.scalars().all())

    return ConcursoDetail.model_validate(concurso)
