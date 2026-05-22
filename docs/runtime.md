# Runtime Guide

## Переменные окружения
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `DATABASE_URL`: Используется бэкендом внутри контейнера (`postgresql+psycopg://user:pass@postgres:5432/db`).
- `DATABASE_URL_LOCAL`: Используется локально или Alembic (`postgresql+psycopg://user:pass@localhost:5432/db`).
- `ALEMBIC_DATABASE_URL`: Используется для миграций.
- `SECRET_KEY`: >= 32 байт.
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `RATE_LIMIT_AUTH_PER_MINUTE`
- `RATE_LIMIT_REFRESH_PER_MINUTE`
- `RATE_LIMIT_CIPHER_PER_MINUTE`
- `RATE_LIMIT_MUTATION_PER_MINUTE`
- Rate limiting сейчас in-memory и подходит только для single-process/dev runtime; для multi-worker/prod нужен shared store.

## Сервисы Docker
- `postgres`: База данных.
- `backend-init`: Выполняет миграции и наполнение БД, затем завершается.
- `backend`: Приложение FastAPI.

## Команды для проверки
```bash
docker compose config
docker compose up -d postgres
cd backend && ../.venv/bin/python -m alembic upgrade head
cd backend && ../.venv/bin/python -m app.db.init_db
docker compose up --build -d
curl -s http://localhost:8000/api/v1/health
docker compose down
```
