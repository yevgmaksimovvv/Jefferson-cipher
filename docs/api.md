# API Reference

![API](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![Version](https://img.shields.io/badge/version-v1-2563EB)
![Auth](https://img.shields.io/badge/auth-Bearer%20JWT-7C3AED)
![OpenAPI](https://img.shields.io/badge/OpenAPI-available-85EA2D?logo=openapiinitiative&logoColor=black)
![Rate limit](https://img.shields.io/badge/rate%20limit-enabled-F59E0B)

Документ фиксирует фактический HTTP API Jefferson Cipher Service. Источник истины для машинной схемы — `/openapi.json`; этот файл нужен как человекочитаемая карта контрактов.

## Базовая информация

| Параметр | Значение |
| --- | --- |
| Префикс business API | `/api/v1` |
| OpenAPI schema | `/openapi.json` |
| Swagger UI | `/docs` |
| ReDoc | `/redoc` |
| Web UI | не входит в business API |

> [!IMPORTANT]
> `/docs`, `/redoc` и `/openapi.json` — инструментальные маршруты. Они не считаются business API.

## Формат ошибок

| Случай | HTTP status | Формат |
| --- | --- | --- |
| Ошибка домена/сервиса | `400` | `{"error":{"code","message"}}` |
| Ошибка валидации схемы | `422` | стандартный FastAPI `detail` |
| Не авторизован | `401` | `{"detail":"Not authenticated"}` |
| Ресурс не найден | `404` | `{"detail":"Not found"}` |
| Rate limit | `429` | `RATE_LIMIT_EXCEEDED` |
| Rate limiter недоступен | `503` | `RATE_LIMITER_UNAVAILABLE` |

## Аутентификация

* API требует `Bearer` token (JWT) для защищенных эндпоинтов.
* Web UI использует cookies/CSRF, которые не относятся к JSON API.
* `owner_id` назначается сервером автоматически, в запросах не принимается.

> [!WARNING]
> Чужие частные `disk sets` возвращаются с `404`, чтобы не раскрывать существование ресурса.

## Endpoints

### Health

| Метод | Путь | Auth | Успех | Назначение |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/health` | Нет | `200` | liveness probe |
| `GET` | `/api/v1/ready` | Нет | `200/503` | readiness probe |

* `/ready` проверяет БД, миграции, seed и rate limiter.

### Auth

| Метод | Путь | Auth | Успех | Назначение |
| --- | --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register` | Нет | `201` | регистрация |
| `POST` | `/api/v1/auth/login` | Нет | `200` | login |
| `POST` | `/api/v1/auth/refresh` | Да | `200` | обновление токена |
| `POST` | `/api/v1/auth/logout` | Да | `204` | logout |

* Ошибки: `401`, `409`, `429`, `422`.

### Users

| Метод | Путь | Auth | Успех | Назначение |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/users/me` | Да | `200` | текущий профиль |

### Cipher

| Метод | Путь | Auth | Успех | Назначение |
| --- | --- | --- | --- | --- |
| `POST` | `/api/v1/cipher/encrypt` | Нет | `200` | шифрование (config) |
| `POST` | `/api/v1/cipher/decrypt` | Нет | `200` | дешифрование (config) |
| `POST` | `/api/v1/cipher/encrypt/from-disk-set` | Да | `200` | шифрование (disk set) |
| `POST` | `/api/v1/cipher/decrypt/from-disk-set` | Да | `200` | дешифрование (disk set) |

### Disk sets

| Метод | Путь | Auth | Успех | Назначение |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/disk-sets` | Да | `200` | список |
| `GET` | `/api/v1/disk-sets/{id}` | Да | `200` | детали |
| `POST` | `/api/v1/disk-sets` | Да | `201` | создание |
| `PATCH` | `/api/v1/disk-sets/{id}` | Да | `200` | обновление |
| `DELETE` | `/api/v1/disk-sets/{id}` | Да | `204` | удаление |

* `list` (GET): default `limit=50`, max `limit=100`, default `offset=0`.
* `owner_id` назначается сервером (NULL для public/system).

## Контракт disk sets

* `public/system` имеют `owner_id=NULL`.
* Anonymous видит только `public/system`.
* Authenticated видит `public/system` + свои частные.

## Curl-примеры

### Health
```bash
curl -s http://localhost:8000/api/v1/health
```

### Readiness
```bash
curl -s http://localhost:8000/api/v1/ready
```

### Login
```bash
curl -s \
  -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"password123"}'
```

### Current user
```bash
curl -s \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  http://localhost:8000/api/v1/users/me
```

### List disk sets
```bash
curl -s "http://localhost:8000/api/v1/disk-sets?limit=50&offset=0"
```

## Что не входит в этот документ
* не описывает Web UI;
* не заменяет `/openapi.json`;
* не описывает runtime-настройки;
* не является security audit.

Runtime и локальный запуск: [`docs/runtime.md`](./runtime.md).
Архитектурные границы: [`docs/architecture.md`](./architecture.md).
