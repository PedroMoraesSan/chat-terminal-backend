# pyback

Backend FastAPI (Clean Architecture) com PostgreSQL (Neon), usado pelo chat em produção.

Instruções gerais do monorepo: [README na raiz](../README.md).

## Configuração local

1. Copie `.env.example` para `.env` e preencha `DATABASE_URL`, `JWT_SECRET` e `ENCRYPTION_KEY`.
2. Migrações: `poetry run alembic upgrade head`
3. Servidor: `poetry run uvicorn pyback.presentation.main:app --reload --host 0.0.0.0 --port 8000`

## Railway

1. Serviço com **Root Directory** = `pyback`.
2. Arquivo [`railway.toml`](railway.toml):
   - instala dependências de produção com Poetry;
   - **`releaseCommand`**: `alembic upgrade head` antes de cada deploy;
   - **`startCommand`**: uvicorn em `--port $PORT` (obrigatório no Railway);
   - healthcheck em `/health`.
3. Variáveis: ver `.env.example` — em especial **`CORS_ORIGINS`** com a URL exata do frontend (Netlify ou domínio próprio).

Requisitos: host com **WebSockets** habilitados (Railway atende). Neon: prefira connection string do **pooler** quando disponível.

## Testes

```bash
poetry run pytest
```
