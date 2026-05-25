# Jefferson Cipher Service

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![SSR Web UI](https://img.shields.io/badge/Web%20UI-Jinja%20SSR-F59E0B)
![No CDN](https://img.shields.io/badge/No-CDN-94A3B8)

Веб-сервис для работы с шифром Джефферсона, включающий RESTful API и серверный Web UI.

## Быстрый запуск

```bash
docker compose up -d
```

> [!WARNING]
> Не используйте `docker compose down -v`, если нужно сохранить локальные данные.

## Основные адреса

| Назначение | Адрес |
| --- | --- |
| Backend HTTP | `http://localhost:8000` |
| Nginx HTTP | `http://localhost:8080` |
| Nginx HTTPS | `https://localhost:8443` |
| Healthcheck | `http://localhost:8000/api/v1/health` |

## Web UI
* Интерфейс для работы с шифром через браузер.
* Реализован на `Jinja` SSR внутри `FastAPI`.
* Использует `CSRF` для защиты форм.

## Документация

| Раздел | Ссылка |
| --- | --- |
| API | [`docs/api.md`](docs/api.md) |
| Runtime | [`docs/runtime.md`](docs/runtime.md) |
| Security | [`docs/security.md`](docs/security.md) |
| Architecture | [`docs/architecture.md`](docs/architecture.md) |
| Testing | [`docs/testing.md`](docs/testing.md) |
