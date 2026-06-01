# Análise do Projeto GarimpoGov

> **Data:** Junho 2026
> **Objetivo:** Documentar funcionalidades existentes, problemas identificados e oportunidades de melhoria.

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Stack Tecnológica](#2-stack-tecnológica)
3. [Funcionalidades Existentes](#3-funcionalidades-existentes)
4. [Ajustes e Melhorias Necessários](#4-ajustes-e-melhorias-necessários)
   - 4.1 [Bugs Críticos](#41-bugs-críticos)
   - 4.2 [Bugs Funcionais](#42-bugs-funcionais)
   - 4.3 [Problemas de Error Handling](#43-problemas-de-error-handling)
   - 4.4 [Duplicação de Código](#44-duplicação-de-código)
   - 4.5 [Problemas de Type Safety](#45-problemas-de-type-safety)
   - 4.6 [Valores Hardcoded](#46-valores-hardcoded)
   - 4.7 [Problemas de Performance](#47-problemas-de-performance)
   - 4.8 [Problemas de Segurança](#48-problemas-de-segurança)
5. [Arquitetura: Problemas Estruturais](#5-arquitetura-problemas-estruturais)
6. [Funcionalidades Futuras (Roadmap)](#6-funcionalidades-futuras-roadmap)
7. [Recomendações Prioritárias](#7-recomendações-prioritárias)

---

## 1. Visão Geral

O **GarimpoGov** é uma plataforma de monitoramento de concursos públicos brasileiros com inteligência artificial. O sistema realiza scraping diário de múltiplas fontes, filtra automaticamente oportunidades nas áreas de **TI (nível superior)** e **professor de inglês**, processa editais em PDF com extração de texto e vetorização, e disponibiliza um chat RAG (Retrieval-Augmented Generation) para tirar dúvidas sobre cada concurso.

### Fontes de Dados

| Tipo | Fontes | Quantidade |
|------|--------|-----------|
| **Portais agregadores** | PCI Concursos, QConcursos, Estratégia Concursos | 3 |
| **Bancas organizadoras** | Fundatec, FEPESE, FGV, Cebraspe, FCC, Vunesp, Quadrix, Idecan, etc. | 22 |
| **Diários oficiais** | DOU (Federal), DOERS (RS), DOESC (SC) | 3 |
| **Municípios** | Porto Alegre, Florianópolis, Joinville, Caxias do Sul, Blumenau | 5 |
| **Total** | | **33 fontes** |

### Pipeline de Dados

```
Scrapers → Filtro (TI/Inglês) → Extração via Gemini AI → 
Banco (concursos + cargos) → PDF → R2 → Texto → Chunks → 
Embeddings → pgvector → API FastAPI → Chat RAG → Frontend React
```

---

## 2. Stack Tecnológica

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| **Backend** | Python + FastAPI + Uvicorn | 3.11 / FastAPI |
| **ORM** | SQLAlchemy 2.0 (assíncrono) | 2.0 |
| **Database** | PostgreSQL 16 + pgvector | 16 |
| **Driver Async** | asyncpg | — |
| **Migrations** | Alembic | — |
| **AI / LLM** | Google Gemini (text-embedding-004, gemini-1.5-flash, gemini-2.0-flash-lite) | — |
| **PDF** | PyMuPDF (fitz) + LangChain text splitters | — |
| **Storage** | Cloudflare R2 (S3-compatible via boto3) | — |
| **Scraping** | requests + BeautifulSoup4 + lxml | — |
| **Frontend** | React 18 + TypeScript + Vite 6 + TailwindCSS 3 | — |
| **UI** | Radix UI, lucide-react, React Router DOM | — |
| **Containerização** | Docker + Docker Compose | — |
| **Deploy** | Railway | — |
| **CI/CD** | GitHub Actions (cron diário) | — |

---

## 3. Funcionalidades Existentes

### 3.1 Ingestão de Dados (`automacao/`)
- [x] **Scraping multi-fonte**: 33 fontes diferentes distribuídas em scrapers dedicados
- [x] **Filtro inteligente**: Seleção automática de concursos de TI (nível superior) e Inglês
- [x] **Extração via IA**: Uso do Gemini 2.0 Flash-Lite para extrair dados estruturados de HTML
- [x] **Processamento de PDF**: Download → Upload R2 → Extração de texto → Chunking
- [x] **Vetorização**: Embeddings com `text-embedding-004` (768 dimensões) armazenados no pgvector
- [x] **Rate limiting**: Token-bucket para respeitar limites da API Gemini (free tier: 30 RPM)
- [x] **Idempotência**: Detecção de duplicatas por `link_edital` (UNIQUE)
- [x] **Relatórios diários**: Relatório markdown auto-gerado e commitado no git
- [x] **Automação CI/CD**: GitHub Actions com cron diário (08:00 UTC) e trigger manual

### 3.2 API Backend (`backend/`)
- [x] `GET /health` — Health check
- [x] `GET /concursos` — Lista paginada com filtros (órgão, status, faixa salarial)
- [x] `GET /concursos/{id}` — Detalhe do concurso com cargos
- [x] `POST /chat/{concurso_id}` — Chat RAG via Server-Sent Events (SSE)
- [x] **RAG Pipeline**: Embedding → busca por similaridade (cosine distance) → Gemini 1.5 Flash streaming

### 3.3 Frontend (`frontend/`)
- [x] Lista paginada de concursos com cards
- [x] Painel de filtros (busca textual, status, órgão, faixa salarial)
- [x] Modal de chat com streaming em tempo real (SSE)
- [x] Debounce no campo de busca
- [x] Design responsivo com TailwindCSS
- [x] Docker multi-stage com Nginx para produção

---

## 4. Ajustes e Melhorias Necessários

### 4.1 Bugs Críticos

#### 🔴 B1 — Scrapers QConcursos e Estratégia retornam vazio
**Arquivos:** `automacao/scraper_qconcursos.py`, `automacao/scraper_estrategia.py`  
**Problema:** Ambos os sites carregam conteúdo via JavaScript. O `requests.get()` captura apenas o HTML inicial vazio.  
**Impacto:** Esses scrapers estão efetivamente quebrados e sempre retornam `[]`.  
**Solução:** Usar `playwright` ou `selenium` para renderização JS, ou implementar chamadas às APIs internas dos sites.

#### 🔴 B2 — Filtro de nível superior aprova concursos indevidos
**Arquivo:** `automacao/filters.py` (linhas 30-35)  
**Problema:** A lógica `if nivel_match or not any(n in full_text for n in ["médio", "medio", "fundamental"])` retorna `True` se o texto não mencionar "médio"/"fundamental", mesmo sem confirmação de nível superior.  
**Impacto:** Concursos de nível médio entram no sistema se a palavra "médio" não aparecer no texto raspeado.  
**Solução:** Exigir confirmação explícita de nível superior (palavras como "superior", "graduação", "nível superior") em vez de fallback aberto.

#### 🔴 B3 — String interpolada para vetor no SQL
**Arquivos:** `backend/app/services/rag.py` (linha 34), `automacao/vector_store.py` (linha 84)  
**Problema:** `embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"` — montagem manual de string vetorial.  
**Impacto:** Valores como `NaN` ou `Infinity` quebram o SQL. Risco de parsing error no PostgreSQL.  
**Solução:** Usar parâmetro nativo do pgvector (`CAST(%s AS vector)` com binding correto).

#### 🔴 B4 — `data_encerramento_antes` aceito mas ignorado
**Arquivo:** `backend/app/api/concursos.py` (linha 22)  
**Problema:** O parâmetro é recebido mas nunca aplicado na cláusula WHERE.  
**Impacto:** Usuários podem filtrar por data de encerramento mas o filtro não funciona.  
**Solução:** Converter para `datetime` e adicionar ao filtro da query.

---

### 4.2 Bugs Funcionais

#### 🟠 B5 — Modelo `EditalChunk` duplicado com definições conflitantes
**Arquivos:** `backend/app/models/concurso.py` (linhas 59-73), `backend/app/models/edital_chunk.py`  
**Problema:** Duas definições para a mesma tabela: uma com `nullable=True` no embedding, outra com `nullable=False`, uma com `created_at`, outra sem.  
**Impacto:** Bugs de inserção dependendo de qual modelo é importado.  
**Solução:** Unificar em um único modelo, preferencialmente removendo `edital_chunk.py`.

#### 🟠 B6 — Dois SDKs diferentes do Gemini
**Arquivos:** `backend/app/services/rag.py` (SDK antigo `google-generativeai`), `automacao/` (SDK novo `google-genai`)  
**Problema:** APIs diferentes, rate limits diferentes, comportamentos potencialmente diferentes.  
**Impacto:** Manutenção duplicada, inconsistências.  
**Solução:** Migrar tudo para o SDK mais novo (`google-genai`).

#### 🟠 B7 — Modelos Gemini diferentes entre pipelines
**Arquivo:** `backend/` usa `gemini-1.5-flash`, `automacao/` usa `gemini-2.0-flash-lite`  
**Impacto:** Qualidade de resposta do chat vs extração usam modelos diferentes.  
**Solução:** Centralizar a escolha do modelo em configuração compartilhada.

#### 🟠 B8 — Schema `ChatRequest` duplicado
**Arquivos:** `backend/app/schemas/chat.py`, `backend/app/schemas/concurso.py` (linhas 55-61)  
**Problema:** Definição duplicada com estruturas diferentes. A versão em `concurso.py` é morta.  
**Solução:** Remover o schema duplicado em `concurso.py`.

#### 🟠 B9 — `updated_at` nunca atualizado via raw SQL
**Arquivo:** `backend/alembic/versions/0001_initial_schema.py`  
**Problema:** A migration não define `onupdate=sa.func.now()`. O `vector_store.py` faz inserções via SQL bruto, então a coluna nunca é atualizada.  
**Solução:** Adicionar `onupdate` na migration.

#### 🟠 B10 — Filtro salarial exclui concursos com salário NULL
**Arquivo:** `backend/app/api/concursos.py` (linhas 33-36)  
**Problema:** `salario_maximo >= salario_min` retorna NULL quando `salario_maximo` é NULL, excluindo concursos sem salário definido.  
**Solução:** Usar `COALESCE(salario_maximo, 0)` ou tratar NULLs com OR.

---

### 4.3 Problemas de Error Handling

#### 🟡 B11 — Sem tratamento de erro no streaming RAG
**Arquivo:** `backend/app/services/rag.py` (linhas 76-81)  
**Problema:** Exceções do Gemini (quota, conteúdo bloqueado) propagam sem traceback adequado.  
**Solução:** Adicionar try/except com logging e mensagem amigável para o usuário.

#### 🟡 B12 — Sem rollback em falha parcial na ingestão
**Arquivo:** `automacao/run_ingestion.py` (linhas 79-106)  
**Problema:** Cada `insert_concurso` commita independentemente. Falha no meio deixa dados inconsistentes.  
**Solução:** Usar transação única com commit no final e rollback em caso de erro.

#### 🟡 B13 — `conn.close()` não está em bloco `finally`
**Arquivo:** `automacao/run_ingestion.py` (linha 108)  
**Problema:** Se ocorrer exceção, a conexão com o banco vaza.  
**Solução:** Mover para bloco `finally` ou usar `with` statement.

#### 🟡 B14 — Falhas parciais no processamento de PDF não são logadas
**Arquivo:** `automacao/pdf_processor.py` (linhas 68-94)  
**Problema:** Se o download falha, concurso é inserido sem PDF. Se extração falha, sem chunks. Pouco logging.  
**Solução:** Log estruturado para cada etapa, com nível de severidade adequado.

---

### 4.4 Duplicação de Código

#### 🔴 B15 — Dois pipelines de ingestão paralelos
**Diretórios:** `automacao/` (avançado, multi-fonte) vs `backend/scripts/` (legado, regex-based)  
**Problema:** Dois pipelines que fazem a mesma coisa com tecnologias diferentes. Código divergente.  
**Impacto:** Se o schema muda, ambos precisam ser atualizados. Risco de inconsistência.  
**Solução:** Remover o pipeline legado de `backend/scripts/` após verificar que `automacao/` cobre todos os casos.

#### 🟠 B16 — Scrapers com estrutura idêntica
**Arquivos:** `scraper_pci.py`, `scraper_qconcursos.py`, `scraper_estrategia.py`, `scraper_rs.py`, `scraper_sc.py`  
**Problema:** ~50 linhas de boilerplate repetido em cada scraper (headers, loop, dedup, sleep).  
**Solução:** Criar classe base `BaseScraper` (similar a `municipios/base.py`) para reutilização.

#### 🟠 B17 — User-Agent duplicado em 8+ arquivos
**Problema:** O mesmo dicionário de headers aparece em 8 arquivos diferentes.  
**Solução:** Centralizar em `automacao/config.py` ou criar `automacao/utils/http.py`.

#### 🟠 B18 — `logging.basicConfig` chamado em 10 arquivos
**Problema:** `logging.basicConfig()` é chamado em múltiplos módulos. Apenas a primeira chamada tem efeito.  
**Solução:** Chamar `basicConfig` apenas uma vez (em `run_ingestion.py`) e usar `logging.getLogger(__name__)` nos demais.

#### 🟡 B19 — Rate limiting implementado duas vezes
**Arquivos:** `automacao/ai_extractor.py` (token-bucket 2.5s) + sleeps manuais nos scrapers (4-5s)  
**Problema:** Os sleeps redundantes praticamente dobram o tempo do pipeline.  
**Solução:** Remover sleeps dos scrapers; o rate limiter do extrator já controla a taxa.

#### 🟡 B20 — Conversão de URL do banco duplicada e inversa
**Arquivos:** `backend/app/core/database.py` (`_make_async_url`), `automacao/vector_store.py` (`_normalize_db_url`)  
**Problema:** Uma converte sync→async, a outra async→sync. Se uma mudar, a outra quebra.  
**Solução:** Centralizar em package compartilhado.

---

### 4.5 Problemas de Type Safety

#### 🟡 B21 — `Numeric` mapeado como `float`
**Arquivo:** `backend/app/models/concurso.py` (linha 25)  
**Problema:** `Numeric(12,2)` retorna `Decimal` do Python, mas o type hint diz `float`. Perda de precisão.  
**Solução:** Usar `Decimal` no type hint.

#### 🟡 B22 — Type assertion insegura no frontend
**Arquivo:** `frontend/src/services/api.ts` (linha 127)  
**Problema:** `(err as Error).name` assume que o erro é sempre uma instância de `Error`.  
**Solução:** Verificar com `err instanceof Error` antes de acessar `.name`.

#### 🟡 B23 — Sem validação de tipo no retorno do Gemini
**Arquivo:** `automacao/ai_extractor.py` (linha 133)  
**Problema:** `data.get("concursos", [])` retorna `Any`. Se Gemini retornar `null` ou string, o loop `for c in concursos` quebra.  
**Solução:** Validar runtime com `isinstance(concursos, list)`.

---

### 4.6 Valores Hardcoded

#### 🟡 B24 — `FRONTEND_ORIGIN` hardcoded para localhost
**Arquivo:** `backend/app/core/config.py` (linha 17)  
**Problema:** Default `http://localhost:5173` precisa ser sobrescrito em cada deploy.  
**Solução:** Tornar obrigatório em produção ou suportar múltiplas origens.

#### 🟡 B25 — Chunk size e overlap hardcoded
**Arquivo:** `automacao/pdf_processor.py` (linhas 18-19): `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`  
**Solução:** Mover para configuração.

#### 🟡 B26 — `TOP_K=5` hardcoded no RAG
**Arquivo:** `backend/app/services/rag.py` (linha 17)  
**Solução:** Parametrizar ou tornar configurável.

#### 🟡 B27 — Sleeps hardcoded (4-5s) em cada scraper
**Arquivo:** Múltiplos scrapers  
**Solução:** Usar variável configurável em `config.py`.

---

### 4.7 Problemas de Performance

#### 🟠 B28 — Embedding sequencial (1 chamada API por chunk)
**Arquivo:** `automacao/vector_store.py` (linhas 81-92)  
**Impacto:** Para 200 chunks → 200 chamadas API → ~100 segundos apenas para embedding.  
**Solução:** Usar batch embedding do SDK `google-genai` (suporta embeddings em lote).

#### 🟡 B29 — Nenhum teste no projeto
**Impacto:** Qualquer mudança pode quebrar funcionalidades sem detecção.  
**Solução:** Implementar testes conforme seção [5.3](#53-testes).

#### 🟡 B30 — Conexão nova ao banco a cada ingestão
**Arquivo:** `automacao/vector_store.py` (linha 28)  
**Solução:** Usar pool de conexões (já existe no backend via SQLAlchemy async).

---

### 4.8 Problemas de Segurança

#### 🔴 B31 — SSL verification desabilitado no scraper DOESC
**Arquivo:** `automacao/scraper_sc.py` (linha 40): `verify=False`  
**Problema:** Conexão vulnerável a MITM.  
**Solução:** Adicionar certificado ao trust store em vez de desabilitar verificação.

#### 🟠 B32 — Sem autenticação nos endpoints
**Arquivo:** Todos os endpoints da API são públicos.  
**Impacto:** Qualquer pessoa pode consumir a API e o chat RAG (custo Gemini).  
**Solução:** Implementar rate limiting e/ou autenticação básica.

#### 🟠 B33 — Sem rate limiting no chat
**Arquivo:** `backend/app/api/chat.py`  
**Impacto:** Um usuário pode exaurir a cota da API Gemini, gerando custos.  
**Solução:** Adicionar rate limiting por IP (ex: `slowapi` ou middleware customizado).

#### 🟡 B34 — Sem limite de tamanho no `question` do chat
**Arquivo:** `backend/app/schemas/chat.py` (linhas 4-6)  
**Problema:** `question: str` sem `max_length`. Atacante pode enviar 10MB.  
**Solução:** Adicionar `max_length=2000` com validação Pydantic.

#### 🟡 B35 — CORS muito restritivo ou permissivo
**Arquivo:** `backend/app/main.py` (linha 23)  
**Problema:** Única origem configurada. Em preview deployments ou multi-domínio, quebra.  
**Solução:** Usar middleware que valida origem contra lista configurável.

#### 🟡 B36 — Chave API configurada a nível de módulo
**Arquivos:** `rag.py` (linha 13), `ai_extractor.py` (linha 27)  
**Problema:** API key configurada no import do módulo. Rotação de chave requer restart.  
**Solução:** Configurar lazy ou via dependency injection.

---

## 5. Arquitetura: Problemas Estruturais

### 5.1 Duas Pipelines de Ingestão

O sistema possui **dois pipelines completamente separados** que interagem com o mesmo banco:

| Aspecto | Backend (`backend/scripts/`) | Automação (`automacao/`) |
|---------|------------------------------|--------------------------|
| Driver DB | `asyncpg` (assíncrono) | `psycopg2` (síncrono) |
| ORM | SQLAlchemy async | SQL puro |
| SDK Gemini | `google-generativeai` (legado) | `google-genai` (novo) |
| Embedding | `genai.embed_content()` | `client.models.embed_content()` |
| Modelo RAG | `gemini-1.5-flash` | `gemini-2.0-flash-lite` |
| Config | `pydantic-settings` | `os.environ` |

**Recomendação:** Extrair um pacote compartilhado (`garimpogov_shared/`) com:
- Helpers de conexão DB (sync e async)
- Funções de embedding (modelo único)
- Configuração centralizada
- Utilitários de data e salary parsing

### 5.2 Testes — Ausência Total

O projeto possui **zero testes automatizados**. Recomendação mínima:

| Camada | Ferramenta | O que testar |
|--------|-----------|-------------|
| API Backend | `pytest` + `httpx.AsyncClient` | Endpoints, paginação, filtros, erros |
| Services | `pytest` | `rag.py` com Gemini mockado, `config.py` |
| Automacao | `pytest` | `filters.py` (vários cenários de concurso) |
| Automacao | `pytest` | `ai_extractor.py` com resposta mockada |
| Frontend | `vitest` + `@testing-library/react` | Componentes, hooks |
| Integração | `pytest` | Pipeline completo com DB de teste |
| E2E | Playwright | Fluxos: busca, filtro, chat |

### 5.3 Monitoramento e Observabilidade

**Estado atual:** Apenas `GET /health` retornando `{"status": "ok"}` estático.

**Melhorias:**
- [ ] Health check com verificação de DB, Gemini API, R2
- [ ] Logging estruturado (JSON) com request IDs
- [ ] Métricas de latência das chamadas Gemini
- [ ] Rastreamento de custos por chamada de API (tokens)
- [ ] Alertas para falha do pipeline de ingestão

### 5.4 CI/CD e Deploy

- [ ] Migrations devem rodar como init container, não no CMD principal
- [ ] Adicionar `.dockerignore`
- [ ] Remover volume mounts em produção no `docker-compose.yml`
- [ ] Usar lockfile para dependências Python (`pip freeze`)
- [ ] Adicionar notificação de falha no GitHub Actions (Slack/Discord)
- [ ] Estratégia de backup do banco de dados

---

## 6. Funcionalidades Futuras (Roadmap)

### 6.1 Autenticação e Usuários
- [ ] **Cadastro/login** (email + senha ou OAuth Google/GitHub)
- [ ] **JWT ou session-based auth** para proteger endpoints
- [ ] **Perfil de usuário** com preferências de filtro
- [ ] **Roles** (admin, editor, viewer)

### 6.2 Favoritos e Salvos
- [ ] **Favoritar concursos** — salvar para acompanhamento
- [ ] **Histórico de visualizações**
- [ ] **Comparação de concursos** lado a lado
- [ ] **Acompanhamento de inscrições** (status: pretendo, inscrito, etc.)

### 6.3 Notificações
- [ ] **Notificações por email** — novos concursos matching filtros salvos
- [ ] **Webhooks** — para sistemas externos receberem alertas
- [ ] **Notificações in-app** (sino)
- [ ] **Push notifications** (browser/mobile)

### 6.4 Features da API
- [ ] `POST /concursos` — Criar concurso manualmente (admin)
- [ ] `PUT /concursos/{id}` — Editar (admin)
- [ ] `DELETE /concursos/{id}` — Remover (admin)
- [ ] `GET /concursos/stats` — Agregados (total por status, top órgãos)
- [ ] `GET /concursos/orgaos` — Lista de órgãos para dropdown
- [ ] `GET /concursos/export` — Exportar CSV/JSON
- [ ] `GET /subscriptions` — Gerenciar notificações

### 6.5 Features do Frontend
- [ ] **Página de detalhe do concurso** (rota `/concursos/:id`)
- [ ] **Skeletons de carregamento** (não apenas pulse simples)
- [ ] **Error boundaries** para evitar crash total
- [ ] **Empty states ilustrados**
- [ ] **Dark mode**
- [ ] **Ordenação** (por salário, data, instituição)
- [ ] **Visualização em tabela** (alternativa ao grid de cards)
- [ ] **Atalhos de teclado** (`/` para buscar, `Escape` para fechar)
- [ ] **SEO** (meta tags, SSR ou SSG)

### 6.6 Administração
- [ ] **Painel admin** com estatísticas do sistema
- [ ] **Gerenciamento de scrapers** (ativar/desativar via UI)
- [ ] **Logs de ingestão** visíveis no frontend
- [ ] **Gerenciamento de concursos** (CRUD via UI)

### 6.7 Aprimoramentos do Pipeline
- [ ] **Paralelização de scrapers** (atualmente sequenciais)
- [ ] **Atualização incremental** (não apenas inserção, mas update de status)
- [ ] **Detecção de concursos encerrados** (atualizar status automaticamente)
- [ ] **Batch embedding** para chunks de PDF (reduzir chamadas API)
- [ ] **Suporte a mais estados/municípios**

---

## 7. Recomendações Prioritárias

### 🚨 Imediatas (P0)
| # | Item | Esforço | Impacto |
|---|------|---------|---------|
| 1 | Corrigir filtro de nível superior (`filters.py`) | Baixo | Alto |
| 2 | Consertar scrapers QConcursos/Estratégia | Médio | Alto |
| 3 | Corrigir string interpolada de embeddings (SQL injection) | Baixo | Alto |
| 4 | Aplicar filtro `data_encerramento_antes` | Baixo | Alto |
| 5 | SSL verification no scraper SC | Baixo | Alto |

### ⚡ Curto Prazo (P1)
| # | Item | Esforço | Impacto |
|---|------|---------|---------|
| 6 | Unificar modelos `EditalChunk` | Baixo | Médio |
| 7 | Migrar para SDK único do Gemini | Médio | Médio |
| 8 | Adicionar rate limiting no chat | Médio | Alto |
| 9 | Implementar testes (começar por filters.py) | Médio | Alto |
| 10 | Remover pipeline legado `backend/scripts/` | Baixo | Médio |

### 📋 Médio Prazo (P2)
| # | Item | Esforço | Impacto |
|---|------|---------|---------|
| 11 | Refatorar scrapers com classe base | Médio | Médio |
| 12 | Batch embedding para PDFs | Baixo | Alto |
| 13 | Adicionar logging estruturado | Médio | Médio |
| 14 | Implementar health check real | Baixo | Médio |
| 15 | Remover sleeps redundantes | Baixo | Médio |

---

> **Documento gerado em:** 01/06/2026  
> **Última revisão:** Análise completa do código-fonte
