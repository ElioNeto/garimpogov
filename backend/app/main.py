import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.concursos import router as concursos_router
from app.api.chat import router as chat_router
from app.core.config import get_settings
from app.core.database import get_db
from fastapi import Depends

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="GarimpoGov API",
    description="Plataforma de monitoramento de editais de concursos publicos com IA",
    version="1.0.0",
)

# B24: suporta múltiplas origens (produção + dev + preview deployments)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(concursos_router)
app.include_router(chat_router)


@app.get("/health", tags=["health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check com verificação de conectividade do banco."""
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.warning(f"Health check - DB error: {e}")

    return {
        "status": "ok" if db_ok else "degraded",
        "service": "garimpogov-api",
        "database": "connected" if db_ok else "error",
    }
