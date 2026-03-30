# =============================================================================
# GarimpoGov Backend - Dockerfile para Railway
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# Dependencias do sistema (necessarias para psycopg2/asyncpg e PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o codigo
COPY . .

# Railway injeta a variavel $PORT automaticamente
EXPOSE 8000

# Roda migrations e sobe o servidor
# O script de startup garante que o DB esta pronto antes do servidor
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
