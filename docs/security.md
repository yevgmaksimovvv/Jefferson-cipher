# Security

## API inventory
- Source of truth for business routes is `app.openapi()`.
- `docs/api.md` documents the business API contract.
- `/docs`, `/redoc`, and `/openapi.json` are tooling endpoints, not business API.

## Аутентификация
- Используется JWT (access tokens) и opaque refresh tokens.
- Пароли хэшируются через bcrypt.
- Эндпоинт `/users/me` требует валидный токен.

## Rate limiting
- Используется Redis для хранения счетчиков.
- При отсутствии Redis — memory fallback.
- При недоступности Redis — 503.
- `RATE_LIMIT_STORAGE=redis` требует `REDIS_URL`.
- `RATE_LIMIT_FAIL_OPEN=true` с Redis-режимом запрещён.
- Ключи не содержат токены или пароли.

## Доверенный прокси
- `X-Forwarded-For` доверяется только от доверенных прокси.
- `TRUSTED_PROXY_IPS` содержит список разрешенных IP.
- `TRUSTED_PROXY_IPS=*` допустим только для local/dev escape hatch, когда backend стоит за доверенным локальным прокси и не торчит напрямую наружу.

## HTTPS
- TLS завершается на nginx.
- Backend внутри сети compose работает по HTTP.
- Self-signed сертификаты только для локальной разработки.
- Custom certificates через `NGINX_HOST_CERT_DIR`.
- HSTS выключен по умолчанию.
- HSTS не включают на self-signed localhost-стенде.

## CORS
- Настраивается через `BACKEND_CORS_ORIGINS`.
- Wildcard `*` запрещён.

## Audit logs
- Security audit events пишутся в logger `app.audit`.
- В контейнере backend они попадают в stdout/stderr и доступны через `docker compose logs backend`.
