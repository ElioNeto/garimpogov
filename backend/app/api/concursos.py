import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.concurso import Concurso
from app.schemas.concurso import ConcursoSchema, PaginatedConcursos, ConcursoListSchema

router = APIRouter(prefix="/concursos", tags=["concursos"])


@router.get("", response_model=PaginatedConcursos)
async def list_concursos(
    orgao: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    salario_min: Optional[float] = Query(None),
    salario_max: Optional[float] = Query(None),
    data_encerramento_antes: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Concurso)

    if orgao:
        stmt = stmt.where(Concurso.orgao.ilike(f"%{orgao}%"))
    if status:
        stmt = stmt.where(Concurso.status == status)
    if salario_min is not None:
        stmt = stmt.where(Concurso.salario_maximo >= salario_min)
    if salario_max is not None:
        stmt = stmt.where(Concurso.salario_maximo <= salario_max)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.order_by(Concurso.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    concursos = result.scalars().all()

    return PaginatedConcursos(
        total=total,
        page=page,
        page_size=page_size,
        items=[ConcursoListSchema.model_validate(c) for c in concursos],
    )


@router.get("/{concurso_id}", response_model=ConcursoSchema)
async def get_concurso(
    concurso_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Concurso)
        .options(selectinload(Concurso.cargos))
        .where(Concurso.id == concurso_id)
    )
    result = await db.execute(stmt)
    concurso = result.scalar_one_or_none()

    if not concurso:
        raise HTTPException(status_code=404, detail="Concurso nao encontrado")

    return ConcursoSchema.model_validate(concurso)
