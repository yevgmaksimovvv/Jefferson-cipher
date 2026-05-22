# Runtime Guide

## Переменные окружения
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `DATABASE_URL`: Используется бэкендом внутри контейнера (`postgresql+psycopg://user:pass@postgres:5432/db`).
- `DATABASE_URL_LOCAL`: Используется локально или Alembic (`postgresql+psycopg://user:pass@localhost:5432/db`).
- `ALEMBIC_DATABASE_URL`: Используется для миграций.
- `REDIS_URL`: Адрес Redis для rate limiter; если пустой, в local/test используется in-memory fallback.
- `SECRET_KEY`: >= 32 байт.
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `RATE_LIMIT_STORAGE`: `auto`, `memory` или `redis`.
- `RATE_LIMIT_FAIL_OPEN`: Поведение при недоступности Redis для limiter.
- `RATE_LIMIT_AUTH_PER_MINUTE`
- `RATE_LIMIT_REFRESH_PER_MINUTE`
- `RATE_LIMIT_CIPHER_PER_MINUTE`
- `RATE_LIMIT_MUTATION_PER_MINUTE`
- `TRUST_PROXY_HEADERS`: Включает доверие к `X-Forwarded-For` только за trusted proxy.
- `TRUSTED_PROXY_IPS`: Список trusted proxy IP через запятую; `*` только как опасный dev escape hatch.
- `ENABLE_HSTS`: Opt-in HSTS header.
- `HSTS_MAX_AGE_SECONDS`: Значение `max-age` для HSTS.
- `BACKEND_CORS_ORIGINS`: CORS origins из env; defaults включают localhost dev origins.

## Сервисы Docker
- `postgres`: База данных.
- `redis`: Хранилище counters для rate limiter.
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

`docker compose down -v` не используйте без отдельной причины: это удаляет volume с данными БД.
