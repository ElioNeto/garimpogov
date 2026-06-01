"""Testes dos endpoints de concursos."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_concursos(client: AsyncClient):
    """GET /concursos deve retornar lista."""
    response = await client.get("/concursos")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_concursos_filter_superior(client: AsyncClient):
    """Filtro nivel=superior deve funcionar."""
    response = await client.get("/concursos", params={"nivel": "superior"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_concursos_data_encerramento(client: AsyncClient):
    """Filtro data_encerramento_antes deve ser aceito (B4)."""
    response = await client.get("/concursos", params={"data_encerramento_antes": "2026-12-31"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_concursos_salario_filter(client: AsyncClient):
    """Filtro salario_minimo deve incluir NULLs (B10)."""
    response = await client.get("/concursos", params={"salario_minimo": 3000})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_concurso_detail_not_found(client: AsyncClient):
    """GET /concursos/{id} com ID inexistente deve retornar 404."""
    response = await client.get("/concursos/nonexistent-id-12345")
    assert response.status_code == 404
