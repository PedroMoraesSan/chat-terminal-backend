# Retro Hacker Chat

Chat em tempo real com estética terminal/hacker (React + Vite). O fluxo principal usa o backend **pyback** (FastAPI, PostgreSQL/Neon, WebSocket).

A pasta **`backend/`** contém o projeto legado **Encore** (TypeScript), mantido para referência ou desenvolvimento paralelo; o app em produção descrito abaixo fala com o **pyback**.

## Funcionalidades

- Chat em tempo real (WebSocket)
- Múltiplas conversas, histórico e integração com Groq (LLM) no backend
- Interface React 19, TailwindCSS 4, tipagem TypeScript

## Stack (caminho principal)

| Camada | Tecnologia |
|--------|------------|
| Frontend | React 19, Vite 6, TailwindCSS 4, `frontend/lib/pybackClient.ts` (REST + WS) |
| API | **pyback**: FastAPI, SQLAlchemy async (asyncpg), Alembic, JWT, criptografia de chaves Groq |
| Banco | PostgreSQL (ex.: Neon) |

## Pré-requisitos locais

- **Bun** (frontend): `npm install -g bun`
- **Poetry** + Python 3.11+ (pyback)
- Conta e connection string no **Neon** (ou outro Postgres)

## Como executar (pyback + frontend)

### 1. Backend (pyback)

```bash
cd pyback
cp .env.example .env
# Edite .env: DATABASE_URL, JWT_SECRET, ENCRYPTION_KEY, CORS_ORIGINS

poetry install
poetry run alembic upgrade head
poetry run uvicorn pyback.presentation.main:app --reload --host 0.0.0.0 --port 8000
```

API em `http://127.0.0.1:8000`, healthcheck em `GET /health`.

### 2. Frontend

```bash
cd frontend
cp .env.development .env.development.local   # opcional
# Garanta VITE_PYBACK_URL=http://127.0.0.1:8000 (veja .env.development)

bun install
bun run dev
```

Abra `http://localhost:5173` (ou a porta indicada pelo Vite).

### Build de produção (local)

```bash
cd frontend
export VITE_PYBACK_URL=https://sua-api.exemplo.com
bun run build
bun run preview
```

## Estrutura do repositório

```
.
├── pyback/           # API FastAPI (deploy Railway)
├── frontend/         # SPA React (deploy Netlify)
├── backend/          # Encore (legado; opcional)
└── netlify.toml      # Build/publish do frontend na Netlify
```

## Deploy: Netlify (frontend)

1. Conecte o repositório na Netlify.
2. O arquivo [`netlify.toml`](netlify.toml) define `base = "frontend"`, build com Bun e redirect SPA para o `BrowserRouter`.
3. Em **Site configuration → Environment variables**, defina no momento do build:
   - **`VITE_PYBACK_URL`**: URL HTTPS pública do pyback no Railway (sem barra no final).

Consulte também [`frontend/.env.production.example`](frontend/.env.production.example).

## Deploy: Railway (pyback)

1. Crie um serviço e defina **Root Directory** como **`pyback`** (monorepo).
2. O arquivo [`pyback/railway.toml`](pyback/railway.toml) configura:
   - **build**: `poetry install --without dev`
   - **release**: `poetry run alembic upgrade head` (migrações a cada deploy)
   - **start**: `uvicorn` em `0.0.0.0:$PORT` (Railway injeta `PORT`)
   - healthcheck em `/health`
3. Variáveis de ambiente no **mesmo serviço** que executa o uvicorn (o deploy não usa `.env` do Git):
   - **`DATABASE_URL`** e **`JWT_SECRET`** são obrigatórios. Com Postgres plugin da Railway, use *Variable Reference* para expor `DATABASE_URL` do banco neste serviço.
   - `ENCRYPTION_KEY`, **`CORS_ORIGINS`** (origem exata do Netlify), `API_PUBLIC_BASE_URL`

**WebSocket:** com frontend em HTTPS, use `VITE_PYBACK_URL` em `https://…`; o cliente abre `wss://…/chat` automaticamente.

Detalhes extras: [`pyback/README.md`](pyback/README.md).

## Documentação para portfólio

Texto voltado a currículo e apresentação do projeto (stack, arquitetura, destaques técnicos): [`docs/DOCUMENTACAO-PORTFOLIO.md`](docs/DOCUMENTACAO-PORTFOLIO.md).

## Encore (`backend/`)

Fluxo opcional com Encore CLI e `encore run` está resumido em [`DEVELOPMENT.md`](DEVELOPMENT.md).

## Licença

MIT.
