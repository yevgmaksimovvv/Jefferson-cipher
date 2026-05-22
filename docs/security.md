# Security

## Аутентификация
- Используется JWT (access tokens) и opaque refresh tokens.
- Пароли хэшируются через bcrypt.
- Эндпоинт `/users/me` требует валидный токен.

## Rate limiting
- Используется Redis для хранения счетчиков.
- При отсутствии Redis — memory fallback.
- При недоступности Redis — 503.
- Ключи не содержат токены или пароли.

## Доверенный прокси
- `X-Forwarded-For` доверяется только от доверенных прокси.
- `TRUSTED_PROXY_IPS` содержит список разрешенных IP.

## HTTPS
- TLS завершается на nginx.
- Backend внутри сети compose работает по HTTP.
- Self-signed сертификаты только для локальной разработки.
- Custom certificates через `NGINX_HOST_CERT_DIR`.
- HSTS выключен по умолчанию.

## CORS
- Настраивается через `BACKEND_CORS_ORIGINS`.
- Wildcard по умолчанию запрещен.
