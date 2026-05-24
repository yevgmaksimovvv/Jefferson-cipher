# Jefferson Cipher Service

Сервис для работы с шифром Джефферсона.

## Быстрый запуск

### Через Docker Compose
```bash
docker compose up -d
```

### Локальный backend (через .venv)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e "backend/.[dev]"
# Далее настроить .env и запустить миграции БД:
python -m alembic upgrade head
```

## Адреса
- Backend HTTP: http://localhost:8000
- Nginx HTTP proxy: http://localhost:8080
- Nginx HTTPS proxy: https://localhost:8443
- Health endpoint: /api/v1/health

## Web UI
- http://localhost:8000/
- https://localhost:8443/

## Документация
- [API](docs/api.md): HTTP contract, error codes и curl-примеры.
- [Runtime](docs/runtime.md): конфигурация и эксплуатация.
- [Security](docs/security.md): контракты безопасности.
- Runtime smoke: `bash scripts/smoke/compose_runtime_smoke.sh`.
