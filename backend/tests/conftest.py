"""Fixtures compartilhadas para testes do backend."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def client() -> AsyncClient:
    """Cliente HTTP assíncrono para testar a API."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")
