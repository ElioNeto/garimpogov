# GarimpoGov 🔍

Plataforma de monitoramento de editais de concursos públicos com IA.

Realiza ETL diário via web scraping, processa PDFs em um pipeline RAG, armazena dados no PostgreSQL com pgvector e oferece uma interface React com chat inteligente.

## Stack

- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL + pgvector
- **AI**: Google Gemini Flash (chat) + text-embedding-004 (embeddings)
- **Storage**: Cloudflare R2 (PDFs)
- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **CI/CD**: GitHub Actions (ingestion diária + deploy)

## Pré-requisitos

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ com extensão `pgvector`
- Conta Cloudflare R2 (ou compatível S3)
- Chave de API Google Gemini

## Configuração Local

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edite .env com suas credenciais
uvicorn app.main:app --reload
```

O backend estará disponível em: http://localhost:8000

Documentação interativa (Swagger): http://localhost:8000/docs

### Banco de Dados (Migrations)

```bash
cd backend
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# Edite .env.local com VITE_API_URL=http://localhost:8000
npm run dev
```

O frontend estará disponível em: http://localhost:5173

### Executar Ingestion Manualmente

```bash
cd backend
python scripts/scraper.py
python scripts/pdf_processor.py
python scripts/vector_store.py
```

## Variáveis de Ambiente

Veja `backend/.env.example` para a lista completa de variáveis necessárias.

## Deploy (Railway)

1. Faça push para `main`.
2. O GitHub Actions acionará o deploy automático no Railway (configure os secrets abaixo).

## Secrets do GitHub (obrigatórios)

Adicione os seguintes secrets em **Settings → Secrets and variables → Actions**:

| Secret | Descrição |
|---|---|
| `DATABASE_URL` | URL de conexão PostgreSQL |
| `GEMINI_API_KEY` | Chave de API Google Gemini |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 Access Key |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 Secret Key |
| `R2_ENDPOINT_URL` | Endpoint R2 (ex: https://xxx.r2.cloudflarestorage.com) |
| `R2_BUCKET_NAME` | Nome do bucket R2 |
| `FRONTEND_ORIGIN` | URL do frontend (ex: https://garimpogov.up.railway.app) |

## Arquitetura

```
[GitHub Actions (Cron)]
       |
       v
[Scraper] → [PDF Processor] → [Vector Store]
                  |                  |
                  v                  v
           [Cloudflare R2]    [PostgreSQL + pgvector]
                                     |
                              [FastAPI Backend]
                                     |
                              [React Frontend]
```
