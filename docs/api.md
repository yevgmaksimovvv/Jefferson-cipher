# API Reference

Все эндпоинты имеют префикс `/api/v1`.

Базовый `openapi.json`: `http://localhost:8000/openapi.json`.

## Endpoints

### Health
- `GET /api/v1/health` - liveness probe.
  - `200`: сервис жив.
- `GET /api/v1/ready` - readiness probe.
  - `200`: `{"status":"ready", ...}`.
  - `503`: `{"status":"not_ready", ...}` если БД, миграции или seed не готовы.

### Auth
- `POST /api/v1/auth/register`
  - `201`: пользователь создан.
  - `409`: email уже зарегистрирован.
  - `429`: rate limit.
- `POST /api/v1/auth/login`
  - `200`: возвращает access/refresh token pair.
  - `401`: неверный email или пароль.
  - `429`: rate limit.
- `POST /api/v1/auth/refresh`
  - `200`: возвращает новый access/refresh token pair.
  - `401`: refresh token недействителен.
  - `429`: rate limit.
- `POST /api/v1/auth/logout`
  - `204`: без тела ответа.
  - `401`: refresh token недействителен.
  - `429`: rate limit.

### Users
- `GET /api/v1/users/me`
  - `200`: публичный профиль текущего пользователя.
  - `401`: bearer token отсутствует или недействителен.

### Cipher
- `POST /api/v1/cipher/encrypt`
- `POST /api/v1/cipher/decrypt`
  - `200`: результат шифрования/дешифрования.
  - `400`: service/domain error в формате `{"error":{"code","message"}}`.
  - `429`: rate limit.
- `POST /api/v1/cipher/encrypt/from-disk-set`
- `POST /api/v1/cipher/decrypt/from-disk-set`
  - `200`: результат шифрования/дешифрования.
  - `400`: service/domain error в формате `{"error":{"code","message"}}`.
  - `401`: bearer token недействителен.
  - `404`: чужой private disk set скрывается как not found.
  - `429`: rate limit.

### Disk sets
- `GET /api/v1/disk-sets`
  - `200`: list response без `total`/`meta`.
  - `401`: bearer token недействителен.
  - `limit`: default `50`, max `100`.
  - `offset`: default `0`.
- `GET /api/v1/disk-sets/{disk_set_id}`
  - `200`: disk set details.
  - `401`: bearer token недействителен.
  - `404`: чужой private disk set скрывается как not found.
- `POST /api/v1/disk-sets`
  - `201`: disk set создан.
  - `400`: validation/service error в формате `{"error":{"code","message"}}`.
  - `401`: bearer token недействителен.
  - `409`: duplicate slug.
  - `429`: rate limit.
- `PATCH /api/v1/disk-sets/{disk_set_id}`
  - `200`: disk set обновлён.
  - `400`: validation/service error в формате `{"error":{"code","message"}}`.
  - `401`: bearer token недействителен.
  - `404`: disk set не найден или не принадлежит пользователю.
  - `409`: duplicate slug.
  - `429`: rate limit.
- `DELETE /api/v1/disk-sets/{disk_set_id}`
  - `204`: без тела ответа.
  - `400`: service error в формате `{"error":{"code","message"}}`.
  - `401`: bearer token недействителен.
  - `404`: disk set не найден или не принадлежит пользователю.
  - `429`: rate limit.

## Contract Notes

- `owner_id` не принимается в request body. Он назначается сервером через текущего пользователя.
- `public/system` disk sets имеют `owner_id=NULL`.
- Anonymous видит только public/system disk sets.
- Authenticated видит public/system + свои private disk sets.
- Чужой private disk set возвращается как `404`, чтобы не раскрывать существование ресурса.
- `422` возвращает FastAPI schema validation.
- `429` возвращает `RATE_LIMIT_EXCEEDED`.
- `503` может прийти как `RATE_LIMITER_UNAVAILABLE` или как `ready: not_ready`.
- `204` не содержит body для `auth/logout` и `disk-sets/delete`.
- CORS и security headers выставляются на HTTP layer.
- `/ready` проверяет БД, миграции и seed default disk set.

## Curl Examples

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

### List disk sets
```bash
curl -s "http://localhost:8000/api/v1/disk-sets?limit=50&offset=0"
```
