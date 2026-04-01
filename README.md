# pyback

Backend FastAPI (Clean Architecture) com PostgreSQL (Neon), substituindo o Encore para o Chat Terminal.

## Configuração

1. Copie `.env.example` para `.env` e preencha `DATABASE_URL` (Neon), `JWT_SECRET` e `ENCRYPTION_KEY`.
2. Migrações: `cd pyback && poetry run alembic upgrade head`
3. Servidor: `poetry run uvicorn pyback.presentation.main:app --reload --host 0.0.0.0 --port 8000`

## Deploy

- Use um host que suporte **WebSockets** (Railway, Fly.io, Render com WS habilitado, etc.).
- Defina as mesmas variáveis de ambiente do `.env.example`.
- Neon: prefira o endpoint **pooler** na connection string quando disponível.
- CORS: ajuste `CORS_ORIGINS` para o domínio do frontend (ex.: Netlify).

## Testes

`poetry run pytest`
