# Runtime

![Docker Compose](https://img.shields.io/badge/runtime-Docker%20Compose-2496ED?logo=docker&logoColor=white)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Database](https://img.shields.io/badge/database-PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Cache](https://img.shields.io/badge/cache-Redis-DC382D?logo=redis&logoColor=white)
![Proxy](https://img.shields.io/badge/proxy-nginx-009639?logo=nginx&logoColor=white)

Операторская памятка для локального запуска, проверки готовности и основных runtime-настроек Jefferson Cipher Service.

| Раздел | Для чего |
| --- | --- |
| Быстрый запуск | поднять локальный контур |
| Адреса | открыть backend, nginx и Web UI |
| Smoke | проверить готовность окружения |
| Runtime-настройки | Redis limiter, HTTPS, CORS, proxy headers |
| Миграции | понять запуск через compose и host |

## Быстрый запуск

```bash
docker compose up -d
curl -s http://localhost:8000/api/v1/health
curl -s http://localhost:8000/api/v1/ready
docker compose down
```

## Адреса

| Назначение | URL |
| --- | --- |
| Backend HTTP | `http://localhost:8000` |
| Nginx HTTP | `http://localhost:8080` |
| Nginx HTTPS | `https://localhost:8443` |
| Health | `http://localhost:8000/api/v1/health` |
| Ready | `http://localhost:8000/api/v1/ready` |
| OpenAPI | `http://localhost:8000/openapi.json` |

## Web UI

Web UI обслуживается `backend`-приложением. Статика отдаётся из `/static`, отдельный frontend-сервис не требуется. Формы Web UI используют CSRF.

> [!TIP]
> Для обычной локальной проверки достаточно открыть `https://localhost:8443/` или `http://localhost:8000/`.

## Runtime smoke

Команда:

```bash
bash scripts/smoke/compose_runtime_smoke.sh
```

| Проверяет |
| --- |
| Postgres health |
| `backend-init` (миграции + seed) |
| `backend` (health/ready) |
| Redis limiter |
| Web UI (CSRF flow) |
| Nginx (HTTP/HTTPS) |
| CORS preflight |
| Security headers |
| OpenAPI |
| Rate limit 429 |
| Отсутствие случайных изменений в `.env` и cert/key |

## Сервисы

| Сервис | Назначение |
| --- | --- |
| `postgres` | база данных |
| `redis` | хранилище rate limiter |
| `backend-init` | миграции и начальная инициализация |
| `backend` | API и Web UI |
| `nginx` | HTTP/HTTPS reverse proxy |

## Порты

| Порт | Сервис | Назначение |
| --- | --- | --- |
| 8000 | `backend` | direct backend HTTP |
| 8080 | `nginx` | HTTP proxy |
| 8443 | `nginx` | HTTPS proxy |
| 5432 | `postgres` | база данных |

## Основные проверки

```bash
docker compose ps
docker compose logs backend
curl -s http://localhost:8000/api/v1/health
curl -s http://localhost:8000/api/v1/ready
curl -s http://localhost:8000/openapi.json
curl -k -s https://localhost:8443/api/v1/health
```

CORS:

```bash
curl -i -X OPTIONS http://localhost:8000/api/v1/health \
  -H 'Origin: http://localhost:5173' \
  -H 'Access-Control-Request-Method: GET'
```

## HTTPS

### Local self-signed

* self-signed сертификаты генерируются автоматически;
* для `curl` используйте `-k`;
* cert/key лежат в `nginx/certs`;
* cert/key не должны случайно попадать в коммит.

### Свои сертификаты

1. `NGINX_GENERATE_SELF_SIGNED=false`
2. `NGINX_HOST_CERT_DIR=/путь/к/папке`
3. В папке должны быть `fullchain.pem` и `privkey.pem`.

> [!IMPORTANT]
> HSTS включайте только с валидным доверенным HTTPS-сертификатом. Для self-signed localhost оставляйте HSTS выключенным.

## Redis rate limiter

| Настройка | Поведение |
| --- | --- |
| `RATE_LIMIT_STORAGE=auto` + `REDIS_URL` задан | используется Redis |
| `RATE_LIMIT_STORAGE=auto` + `REDIS_URL` пустой | используется memory fallback |
| `RATE_LIMIT_STORAGE=memory` | используется память |
| `RATE_LIMIT_STORAGE=redis` | Redis обязателен |

* `RATE_LIMIT_FAIL_OPEN=true` с Redis-режимом запрещён.
* Если Redis недоступен в `redis`-режиме, `/ready` возвращает 503, а защищённые запросы получают 503 `RATE_LIMITER_UNAVAILABLE`.

## Proxy headers

| Переменная | Назначение |
| --- | --- |
| `TRUST_PROXY_HEADERS` | включает доверие proxy-заголовкам |
| `TRUSTED_PROXY_IPS` | задаёт доверенные proxy IP |

`*` допустим только как явный local/dev escape hatch.

## CORS

* `BACKEND_CORS_ORIGINS` задаётся через `.env`.
* Wildcard `*` запрещён.

## Миграции

Docker Compose:
`backend-init` выполняет миграции автоматически и использует `DATABASE_URL`.

Host-запуск:

```bash
ALEMBIC_DATABASE_URL="$DATABASE_URL_LOCAL" ../.venv/bin/python -m alembic upgrade head
```

> [!CAUTION]
> Не подменяйте контейнерный `DATABASE_URL` локальным host-URL внутри compose-сервисов.

## Полный тестовый прогон

```bash
cd backend
../.venv/bin/python -m pytest
```
