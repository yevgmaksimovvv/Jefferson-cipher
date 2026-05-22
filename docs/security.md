# Security Guide

- **Пароли**: Хэшируются с использованием bcrypt (через `pwdlib`).
- **JWT**: Короткоживущие access токены, подписанные `SECRET_KEY` (минимум 32 байта).
- **Refresh Tokens**: Непрозрачные (opaque) случайные строки, хранящиеся в БД в виде хэшей. Поддерживается ротация при обновлении.
- **Владение (Ownership)**: Приватные ресурсы связаны с `owner_id`. Публичные ресурсы имеют `owner_id` равный `NULL`.
- **BOLA**: Попытки доступа к чужим приватным ресурсам возвращают 404.
- **BOPLA**: Поля владения защищены от модификации через тело запроса.
- **Rate limiting**: `memory` fallback подходит для local/test без `REDIS_URL`; `redis` нужен для docker/local/prod-like runtime. Ключи строятся только из bucket и safe client IP.
- **Proxy headers**: `X-Forwarded-For` игнорируется по умолчанию. При `TRUST_PROXY_HEADERS=true` доверие есть только для direct client, входящего в `TRUSTED_PROXY_IPS`. Малформленные или недоверенные значения откатываются к `request.client.host`.
- **Secret logging**: Не логируются `password`, `Authorization`, `access_token`, `refresh_token` и request body.
- **HSTS**: Заголовок `Strict-Transport-Security` включается только через `ENABLE_HSTS=true`; по умолчанию выключен.
- **Audit trail**: DB audit trail здесь не обещается и не является частью этого контракта.
