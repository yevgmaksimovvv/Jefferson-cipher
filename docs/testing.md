# Тестирование

## Быстрый gate перед коммитом

```bash
cd backend
../.venv/bin/python -m pytest
../.venv/bin/python -m ruff check .
../.venv/bin/python -m ruff format --check .
cd ..
.venv/bin/python -m pre_commit run --all-files
```

## Быстрые срезы

| Область | Команда |
| --- | --- |
| Web UI | `cd backend && ../.venv/bin/python -m pytest tests/web` |
| API | `cd backend && ../.venv/bin/python -m pytest tests/api` |
| Domain | `cd backend && ../.venv/bin/python -m pytest tests/domain` |
| DB | `cd backend && ../.venv/bin/python -m pytest tests/db` |

## Область покрытия

| Группа | Что проверяем |
| --- | --- |
| API | статус-коды, ошибки, auth, rate limit, ownership, JSON-контракты |
| Web UI | SSR HTML, CSRF, cookies, отсутствие токенов в HTML |
| Domain | алгоритм шифрования, валидация, edge cases |
| DB/Repositories | ownership, persistence, seed |
| Security | JWT, CSRF, rate limiter |
| Runtime smoke | контур Docker Compose, nginx, Redis |

## Pre-commit

```bash
.venv/bin/python -m pre_commit run --all-files
```

* Если hooks изменили файлы (формат), проверьте `git diff` и повторите команду.
* Не используйте `--no-verify` без веской причины.

## Рекомендации для новых тестов

* Сначала тест на контрактный эффект, затем реализация.
* Используйте реальные модели и `fixtures`.
* Не мокайте объекты, являющиеся сутью проверяемого поведения.
* В `Security` тестах проверяйте отсутствие токенов и секретов в HTML и логах.

## Финальный чеклист

| Что изменилось | Действие |
| --- | --- |
| Логика `backend` | `pytest` |
| Шаблоны/static `web` | `pytest tests/web` + `ruff` |
| API contract | `pytest tests/api` + проверка `docs/api.md` |
| Runtime/compose | `smoke` + проверка `docs/runtime.md` |
| Перед коммитом | `pre-commit run --all-files` |
