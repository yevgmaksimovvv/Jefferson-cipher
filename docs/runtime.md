# Runtime

## Быстрый запуск
```bash
docker compose up -d
```
Для остановки:
```bash
docker compose down
```

## Operator runbook
- Health check: `curl -s http://localhost:8000/api/v1/health`
- Ready check: `curl -s http://localhost:8000/api/v1/ready`
- OpenAPI check: `curl -s http://localhost:8000/openapi.json`
- CORS preflight: `curl -i -X OPTIONS http://localhost:8000/api/v1/health -H 'Origin: http://localhost:5173' -H 'Access-Control-Request-Method: GET'`
- HTTPS health via 8443: `curl -k -s https://localhost:8443/api/v1/health`
- Rate limit smoke: повторите один и тот же auth/cipher запрос до `429 RATE_LIMIT_EXCEEDED`.
- Redis limiter unavailable behavior: при `RATE_LIMIT_STORAGE=redis` и недоступном Redis ожидается `503 RATE_LIMITER_UNAVAILABLE`, если fail-open не включен.
- Audit logs: logger `app.audit`, смотреть в `docker compose logs backend`.

## Сервисы
- `postgres`: база данных.
- `redis`: кэш для rate limiter.
- `backend-init`: миграции БД.
- `backend`: API приложение.
- `nginx`: обратный прокси.

## Порты
- 8000: direct backend HTTP.
- 8080: nginx HTTP proxy.
- 8443: nginx HTTPS proxy.
- 5432: postgres.

## HTTPS (local mode)
- Self-signed сертификаты генерируются автоматически при старте.
- Curl: используйте флаг `-k`.
- Cert/key лежат в `nginx/certs`.

## Custom certificates
Для использования своих сертификатов:
1. Выключите автогенерацию: `NGINX_GENERATE_SELF_SIGNED=false`.
2. Укажите host-директорию с сертификатами: `NGINX_HOST_CERT_DIR=/путь/к/папке`.
3. В этой папке должны быть файлы `fullchain.pem` и `privkey.pem`.

## Redis limiter
- `REDIS_URL` задан: используется Redis.
- `REDIS_URL` пустой: используется память (memory fallback).
- Redis недоступен: возвращается 503.

## Proxy headers
- `TRUST_PROXY_HEADERS=true`: доверять заголовкам за прокси.
- `TRUSTED_PROXY_IPS`: список доверенных IP. Для local/dev допустимо `*`. В продакшене используйте конкретные подсети.

## CORS
- `BACKEND_CORS_ORIGINS`: задаётся в `.env`. Не используйте wildcard.

## HSTS
- Выключен по умолчанию. Включать только при наличии валидного доверенного сертификата (не для self-signed).

## Проверки
- `docker compose config`
- `curl -s http://localhost:8080/api/v1/health`
- `curl -k https://localhost:8443/api/v1/health`
- `pytest` (в папке backend)

## Работа с миграциями
- Docker Compose/backend-init автоматически использует `DATABASE_URL`.
- Для запуска миграций с хоста используйте explicit override:
  `ALEMBIC_DATABASE_URL="$DATABASE_URL_LOCAL" ../.venv/bin/python -m alembic upgrade head`
