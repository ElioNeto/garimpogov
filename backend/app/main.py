import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.concursos import router as concursos_router
from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API para monitoramento de editais de concursos públicos com IA.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(concursos_router)
app.include_router(chat_router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": settings.app_name}


@app.get("/", tags=["health"])
async def root():
    return {"message": "GarimpoGov API 🔍", "docs": "/docs"}
