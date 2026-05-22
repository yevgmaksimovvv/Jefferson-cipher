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
