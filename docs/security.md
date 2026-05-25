# Security

![Security](https://img.shields.io/badge/security-overview-2563EB)
![Auth](https://img.shields.io/badge/auth-JWT%20%2B%20refresh%20tokens-7C3AED)
![Passwords](https://img.shields.io/badge/passwords-bcrypt-16A34A)
![Rate limit](https://img.shields.io/badge/rate%20limit-Redis%20or%20memory-F59E0B)
![HTTPS](https://img.shields.io/badge/HTTPS-nginx-0EA5E9)

Документ фиксирует фактические security-механизмы Jefferson Cipher Service. Это не внешний аудит и не замена настройкам production-инфраструктуры.

| Область | Реализация | Где смотреть |
| --- | --- | --- |
| API auth | JWT access token + refresh token | `backend/app/services/auth.py` |
| Password hashing | bcrypt | `backend/app/core/security.py` |
| Rate limiting | Redis / memory fallback | `backend/app/core/rate_limit.py` |
| HTTPS | nginx terminates TLS | `nginx/`, `docs/runtime.md` |
| CORS | `BACKEND_CORS_ORIGINS` | `backend/app/core/config.py` |
| Audit logs | logger `app.audit` | `backend/app/core/audit.py` |

> [!IMPORTANT]
> Источник истины по маршрутам API — `/openapi.json` и код `backend/app/api`. Этот документ описывает security-поведение, а не полный API-контракт.

## API inventory

* business routes имеют префикс `/api/v1`;
* `/docs`, `/redoc`, `/openapi.json` — инструментальные маршруты;
* подробный контракт API — [`docs/api.md`](./api.md).

## Аутентификация API

* API использует JWT `access tokens` и opaque `refresh tokens`;
* пароли хэшируются через `bcrypt`;
* `/api/v1/users/me` требует валидный Bearer token.

| Эндпоинт | Auth | Security note |
| --- | --- | --- |
| `POST /api/v1/auth/register` | Нет | создание пользователя |
| `POST /api/v1/auth/login` | Нет | выдача token pair |
| `POST /api/v1/auth/refresh` | Да | обновление токена |
| `POST /api/v1/auth/logout` | Да | инвалидация refresh token |
| `GET /api/v1/users/me` | Да | профиль пользователя |

## Web UI: cookies и CSRF

* Web UI использует cookies для управления сессией;
* реализована защита через CSRF-токены для форм;
* HTML-шаблоны не должны рендерить `access_token` или `refresh_token`.

> [!WARNING]
> CSRF-защита Web UI не заменяет Bearer-auth контракт JSON API. Это разные поверхности.

## Rate limiting

| Режим | Условие | Поведение |
| --- | --- | --- |
| `RATE_LIMIT_STORAGE=auto` + `REDIS_URL` | Redis доступен | Redis counters |
| `RATE_LIMIT_STORAGE=auto` + Redis пуст | fallback | memory counters |
| `RATE_LIMIT_STORAGE=memory` | явно memory | memory counters |
| `RATE_LIMIT_STORAGE=redis` | strict Redis | Redis обязателен |

* При недоступности Redis в strict mode возвращается `503 RATE_LIMITER_UNAVAILABLE`;
* `RATE_LIMIT_FAIL_OPEN=true` с Redis-режимом запрещён;
* ключи счетчиков не содержат персональные токены.

## Доверенный прокси

| Переменная | Назначение |
| --- | --- |
| `TRUST_PROXY_HEADERS` | включает доверие proxy-заголовкам |
| `TRUSTED_PROXY_IPS` | список доверенных IP |

> [!CAUTION]
> `TRUSTED_PROXY_IPS=*` нельзя использовать для backend, который доступен напрямую извне. Такой режим допустим только как осознанный local/dev escape hatch.

## HTTPS, CORS и заголовки

* TLS завершается на `nginx`;
* backend внутри `docker-compose` работает по HTTP;
* `CORS` регулируется `BACKEND_CORS_ORIGINS`;
* wildcard `*` в `CORS` запрещён;
* security headers задаются через `backend/app/core/security_headers.py` и `nginx`.

## Audit logs

* события безопасности пишутся в logger `app.audit`;
* доступны через `docker compose logs backend`.

## Что не гарантируется

* документ не является внешним security audit;
* не описывает production hardening полностью;
* не гарантирует безопасность инфраструктуры вне `docker-compose`;
* не описывает процесс ротации секретов.

## Быстрые проверки

```bash
curl -s http://localhost:8000/api/v1/health
curl -s http://localhost:8000/api/v1/ready
curl -s http://localhost:8000/openapi.json
docker compose logs backend
```

## Связанные документы

- [`docs/api.md`](./api.md) — HTTP API contract.
- [`docs/runtime.md`](./runtime.md) — запуск, ready/smoke, Redis limiter, HTTPS local mode.
- [`docs/architecture.md`](./architecture.md) — архитектурные границы.
