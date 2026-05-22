# Jefferson Cipher Service

Минимальный backend scaffold на FastAPI.

## Требования

- Python 3.10.11

## Локальный запуск

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python --version
cd backend
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload
```

## База данных

- `DATABASE_URL` используется в контейнере и указывает на host `postgres`.
- `ALEMBIC_DATABASE_URL` или `DATABASE_URL_LOCAL` используются для локального Alembic и указывают на `localhost`.

```bash
test -f .env || cp .env.example .env
docker compose up -d postgres
cd backend && ../.venv/bin/python -m alembic upgrade head
cd backend && ../.venv/bin/python -m app.db.init_db
cd .. && docker compose up --build -d
```

## Pre-commit

```bash
cd backend
../.venv/bin/python -m pip install -e ".[dev]"
cd ..
.venv/bin/python -m pre_commit install
.venv/bin/python -m pre_commit run --all-files
```

## Проверка

```bash
.venv/bin/python --version
cd backend && ../.venv/bin/python -m pytest
docker compose up --build
curl http://localhost:8000/api/v1/health
```

## Health

`GET /api/v1/health`
