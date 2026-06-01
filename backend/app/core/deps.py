import time
from collections import defaultdict
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]

# ── Autenticação via API Key (B32) ─────────────────────────────────────────

security_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
) -> None:
    """
    Valida a API Key enviada via header `Authorization: Bearer <key>`.
    Se API_KEY não estiver configurada nas settings, a autenticação é ignorada.
    """
    settings = get_settings()
    if not settings.API_KEY:
        # Autenticação desabilitada
        return

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Autenticação necessária. Envie Authorization: Bearer <api_key>",
        )
    if credentials.credentials != settings.API_KEY:
        raise HTTPException(
            status_code=403,
            detail="API Key inválida",
        )

# ── Rate Limiter simples (in-memory) ──────────────────────────────────────
# B33: Limita chamadas ao chat por IP para evitar abuso da API Gemini

_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # segundos
RATE_LIMIT_MAX_REQUESTS = 10  # máximo de requisições por window


async def chat_rate_limit(request: Request):
    """
    Rate limiter para o endpoint de chat.
    Permite no máximo RATE_LIMIT_MAX_REQUESTS chamadas por IP a cada RATE_LIMIT_WINDOW segundos.
    """
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW

    # Limpa entradas antigas e conta as recentes
    _rate_limit_store[client_ip] = [
        ts for ts in _rate_limit_store[client_ip] if ts > window_start
    ]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Limite de {RATE_LIMIT_MAX_REQUESTS} chamadas por {RATE_LIMIT_WINDOW}s atingido. Aguarde e tente novamente.",
        )

    _rate_limit_store[client_ip].append(now)
