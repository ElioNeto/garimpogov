# GarimpoGov

> Plataforma de monitoramento de editais de concursos publicos com Inteligencia Artificial

GarimpoGov realiza scraping diario de sites de concursos, processa os PDFs dos editais em um pipeline RAG (Retrieval-Augmented Generation), armazena vetores no PostgreSQL com pgvector e oferece uma interface React com chat por IA para consultar os editais.

## Arquitetura

```
[GitHub Actions (cron diario)]
        |
        v
[Scraper (PCI Concursos + Gemini)]
        |
        v
[PDF Processor -> Cloudflare R2]
        |
        v
[Embeddings (text-embedding-004) -> PostgreSQL + pgvector]
        |
        v
[FastAPI Backend (RAG + SSE Chat)] <-- [React Frontend]
```

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI + Python 3.11 |
| Banco de dados | PostgreSQL 16 + pgvector |
| Embeddings / LLM | Google Gemini (text-embedding-004 + gemini-1.5-flash) |
| Armazenamento PDFs | Cloudflare R2 |
| Frontend | React 18 + TypeScript + Vite + TailwindCSS |
| Deploy | Railway |
| CI/CD | GitHub Actions |

## Pre-requisitos

- Python 3.11+
- Node.js 18+
- PostgreSQL 16 com extensao `pgvector` (ou Docker)
- Conta Google AI Studio (Gemini API Key)
- Conta Cloudflare R2 (opcional para armazenar PDFs)

## Rodando Localmente

### 1. Clone e configure o banco

```bash
git clone https://github.com/ElioNeto/garimpogov.git
cd garimpogov

# Subir PostgreSQL com pgvector via Docker
docker run -d \
  --name garimpogov_db \
  -e POSTGRES_USER=garimpogov \
  -e POSTGRES_PASSWORD=garimpogov \
  -e POSTGRES_DB=garimpogov \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Configurar variaveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais

# Rodar migrations
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload
# API disponivel em http://localhost:8000
# Docs em http://localhost:8000/docs
```

### 3. Frontend

```bash
cd frontend
cp .env.example .env
# Ajustar VITE_API_URL se necessario

npm install
npm run dev
# Frontend disponivel em http://localhost:5173
```

### 4. Docker Compose (alternativa)

```bash
# Na raiz do projeto
cp backend/.env.example backend/.env
# Editar backend/.env

docker compose up --build
```

## Rodando a Ingestao Manualmente

```bash
cd backend
source .venv/bin/activate

# Certifique-se que as variaveis de ambiente estao setadas
export DATABASE_URL=postgresql+asyncpg://garimpogov:garimpogov@localhost:5432/garimpogov
export GEMINI_API_KEY=sua_chave_aqui
export R2_ACCESS_KEY_ID=...
export R2_SECRET_ACCESS_KEY=...
export R2_ENDPOINT_URL=...
export R2_BUCKET_NAME=garimpogov-editais

python scripts/run_ingestion.py
```

## Configurando GitHub Secrets

Para o workflow de ingestao automatica funcionar, adicione os seguintes secrets no repositorio GitHub:

**Settings > Secrets and variables > Actions > New repository secret**

| Secret | Descricao |
|---|---|
| `DATABASE_URL` | URL de conexao PostgreSQL (ex: Railway) |
| `GEMINI_API_KEY` | Chave da API Gemini (Google AI Studio) |
| `R2_ACCESS_KEY_ID` | Access Key do Cloudflare R2 |
| `R2_SECRET_ACCESS_KEY` | Secret Key do Cloudflare R2 |
| `R2_ENDPOINT_URL` | Endpoint do bucket R2 |
| `R2_BUCKET_NAME` | Nome do bucket R2 |
| `RAILWAY_TOKEN` | Token do Railway (para deploy automatico) |
| `VITE_API_URL` | URL da API em producao |

## Deploy no Railway

### Backend

1. Crie um novo projeto no [Railway](https://railway.app)
2. Adicione um servico PostgreSQL
3. Adicione um servico a partir do repositorio GitHub (pasta `backend`)
4. Configure as variaveis de ambiente (copie do `.env.example`)
5. O Railway detecta automaticamente o `Dockerfile`

### Frontend

1. Adicione outro servico no mesmo projeto Railway
2. Aponte para a pasta `frontend`
3. Configure `VITE_API_URL` com a URL do backend

## Estrutura do Projeto

```
garimpogov/
├── backend/
│   ├── app/
│   │   ├── api/           # Endpoints FastAPI
│   │   ├── core/          # Config e database
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Logica RAG
│   │   └── main.py
│   ├── scripts/           # Pipeline de ingestao
│   ├── alembic/           # Migrations
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/    # React components
│       ├── pages/         # Paginas
│       ├── services/      # API client
│       └── hooks/         # Custom hooks
└── .github/
    └── workflows/         # GitHub Actions
```

## API Endpoints

| Metodo | Endpoint | Descricao |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/concursos` | Listar concursos (paginado, filtros) |
| GET | `/concursos/{id}` | Detalhes de um concurso |
| POST | `/chat/{concurso_id}` | Chat com edital via SSE |

### Filtros em GET /concursos

- `orgao` - Filtrar por orgao (busca parcial)
- `status` - `aberto` | `encerrado` | `suspenso`
- `salario_min` - Salario minimo
- `salario_max` - Salario maximo
- `page` - Numero da pagina (default: 1)
- `page_size` - Resultados por pagina (default: 20, max: 100)

## Licenca

MIT
