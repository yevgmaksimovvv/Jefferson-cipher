# Jefferson Cipher Service

Продакшн-фрэймворк для шифра Джефферсона.

## Стек технологий

- Backend: Python 3.10.11, FastAPI, SQLAlchemy 2 (sync), Alembic, PostgreSQL.
- Тестирование и инструменты: pytest, ruff, pre-commit.

## Карта документации

- [Архитектура](docs/architecture.md): Обзор компонентов системы и границ слоев.
- [API Reference](docs/api.md): Эндпоинты и контракты.
- [Runtime Guide](docs/runtime.md): Настройка, конфигурация и управление через docker-compose.
- [Testing Guide](docs/testing.md): Запуск тестов и валидация.
- [Security Guide](docs/security.md): Аутентификация, владение ресурсами и контракты безопасности.

## Быстрый старт

1. **Установка зависимостей**:
   ```bash
   python3.10 -m venv .venv
   source .venv/bin/activate
   cd backend
   pip install -e ".[dev]"
   ```

2. **Настройка окружения**:
   - Создайте файл `.env` на основе `.env.example`.
   - Обновите переменные в `.env` (например, `SECRET_KEY`).

3. **Запуск локального окружения**:
   ```bash
   docker compose up -d postgres
   cd backend && ../.venv/bin/python -m alembic upgrade head
   cd backend && ../.venv/bin/python -m app.db.init_db
   cd .. && docker compose up --build -d
   ```

4. **Проверка**:
   ```bash
   curl -s http://localhost:8000/api/v1/health
   ```

5. **Остановка**:
   ```bash
   docker compose down
   ```

## Локальные проверки

```bash
cd backend && ../.venv/bin/python -m pytest
cd backend && ../.venv/bin/python -m ruff check .
cd backend && ../.venv/bin/python -m ruff format --check .
.venv/bin/python -m pre_commit run --all-files
```
