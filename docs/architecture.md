# Архитектура

![Architecture](https://img.shields.io/badge/architecture-layered-4F46E5)
![Domain](https://img.shields.io/badge/domain-framework--free-16A34A)
![API](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![Database](https://img.shields.io/badge/database-SQLAlchemy%20%2B%20Alembic-4169E1)
![Web UI](https://img.shields.io/badge/Web%20UI-SSR%20Jinja-F59E0B)

Документ фиксирует фактическую архитектуру Jefferson Cipher Service: слои приложения, допустимые зависимости и границы, которые нельзя ломать при доработках.

## Карта проекта

| Зона | Где находится | Ответственность |
| --- | --- | --- |
| Domain | `backend/app/domain/` | чистая бизнес-логика шифра |
| Schemas | `backend/app/schemas/` | Pydantic-контракты запросов и ответов |
| API | `backend/app/api/` | HTTP API FastAPI |
| Web UI | `backend/app/web/` | SSR-страницы, формы, CSRF, шаблоны и статика |
| Services | `backend/app/services/` | orchestration между API/Web, domain и repositories |
| Repositories | `backend/app/repositories/` | доступ к данным |
| DB Models | `backend/app/db/models/` | SQLAlchemy-модели |
| Alembic | `backend/alembic/` | миграции БД |
| Runtime | `docker-compose.yml`, `scripts/` | локальный запуск, init, smoke-проверки |

## Поток зависимостей

Web UI / API
    ↓
Services
    ↓        ↓
Domain   Repositories
             ↓
        SQLAlchemy Models

## Слои

### Domain
* содержит алгоритм шифрования и доменные модели;
* не зависит от `FastAPI`, `SQLAlchemy`, `Alembic`, `HTTP`, Pydantic-схем API;
* должен быть тестируемым без БД и web/runtime окружения.

### Schemas
* Pydantic-модели входа/выхода;
* не должны содержать бизнес-логику шифрования;
* используются слоями API, Web и Service.

### API
* роуты `FastAPI`;
* HTTP-валидация, status codes, auth dependencies;
* не содержит алгоритм шифрования.

### Web UI
* SSR через `Jinja2` и `FastAPI` templates;
* использует cookies/CSRF для web-форм;
* не является отдельным frontend-сервисом;
* не должен дублировать бизнес-логику domain.

### Services
* связывает API/Web с domain и repositories;
* содержит application-level сценарии;
* не должен принимать решения на основе FastAPI `Response`;
* не должен превращаться в слой HTTP.

### Repositories
* доступ к данным;
* не знает про HTTP, cookies, templates;
* работает с `SQLAlchemy` session.

### DB Models и Alembic
* SQLAlchemy-модели описывают хранение;
* Alembic отвечает за миграции;
* миграции не должны становиться местом бизнес-логики.

## Архитектурные запреты

> [!IMPORTANT]
> `backend/app/domain/` должен оставаться framework-free. В этот слой нельзя импортировать `FastAPI`, `SQLAlchemy`, `Alembic`, `app.api`, `app.web`, `app.db`, `app.repositories` или runtime-конфигурацию.

| Граница | Запрещено |
| --- | --- |
| Domain | импорт FastAPI, SQLAlchemy, Alembic, API/Web/DB слоёв |
| API | реализация алгоритма шифрования внутри роутов |
| Web UI | дублирование domain-логики в шаблонах |
| Repositories | HTTP, cookies, templates, FastAPI response/request |
| Services | зависимость от FastAPI `Response` и HTML-шаблонов |
| Alembic | бизнес-логика и runtime-side effects |

## Инициализация

1. `postgres` становится healthy.
2. `backend-init` запускает миграции и seed данных.
3. `backend` стартует после успешного завершения `backend-init`.
4. `nginx` проксирует HTTP/HTTPS к `backend`.

> [!WARNING]
> `backend-init` и `backend` должны использовать совместимый образ. Иначе возможен запуск приложения против схемы БД, подготовленной другой версией кода.

## Web UI и API
* JSON API и Web UI живут в одном `backend`-приложении;
* Web UI не меняет API-контракт;
* Web UI использует SSR/Jinja и локальную статику;
* API auth/token contract не должен утекать в HTML;
* HTML не должен рендерить access/refresh tokens.

## Проверки границ

```bash
cd backend
../.venv/bin/python -m pytest
../.venv/bin/python -m ruff check .
../.venv/bin/python -m ruff format --check .
```

## Как вносить изменения
1. Определить слой, где должно жить изменение.
2. Не тащить HTTP/DB зависимости в domain.
3. Для API/Web изменений проверять CSRF/auth/status-code контракты.
4. Для DB изменений добавлять Alembic migration.
5. Для runtime изменений сверять `docker-compose.yml` и `docs/runtime.md`.
