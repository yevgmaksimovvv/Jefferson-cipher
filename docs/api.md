# API Reference

Все эндпоинты имеют префикс `/api/v1`.

### Health & Readiness
- `GET /api/v1/health`: Базовый статус здоровья сервиса (200/503).
- `GET /api/v1/ready`: Статус готовности сервиса (200/503) на основе доступности БД, миграций и данных.

### Authentication
- `POST /api/v1/auth/register`: Регистрация нового пользователя.
- `POST /api/v1/auth/login`: Вход и получение access/refresh токенов.
- `POST /api/v1/auth/refresh`: Обновление access токена с помощью refresh токена.
- `POST /api/v1/auth/logout`: Отзыв refresh токена.

### Users
- `GET /api/v1/users/me`: Получение данных текущего пользователя (требуется Auth).

### Cipher
- `POST /api/v1/cipher/encrypt`: Шифрование текста с передачей ключей набора дисков.
- `POST /api/v1/cipher/decrypt`: Дешифрование текста с передачей ключей набора дисков.
- `POST /api/v1/cipher/encrypt/from-disk-set`: Шифрование с использованием предустановленного набора дисков.
- `POST /api/v1/cipher/decrypt/from-disk-set`: Дешифрование с использованием предустановленного набора дисков.

### Disk Sets
- `GET /api/v1/disk-sets`: Список всех наборов дисков (публичные + собственные).
- `GET /api/v1/disk-sets/{id}`: Получение набора дисков по ID.
- `POST /api/v1/disk-sets`: Создание нового приватного набора дисков (требуется Auth).
- `PATCH /api/v1/disk-sets/{id}`: Обновление собственного набора дисков (требуется Auth).
- `DELETE /api/v1/disk-sets/{id}`: Удаление собственного набора дисков (требуется Auth).
