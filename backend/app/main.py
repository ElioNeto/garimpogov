import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.concursos import router as concursos_router
from app.api.chat import router as chat_router
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="GarimpoGov API",
    description="Plataforma de monitoramento de editais de concursos publicos com IA",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(concursos_router)
app.include_router(chat_router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "garimpogov-api"}
