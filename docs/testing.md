# Тестирование

Документ описывает локальные проверки: запуск `pytest`, использование `ruff` для линтинга, `pre-commit` как основной gate и smoke-проверки.

## Быстрый gate перед коммитом

Для выполнения полной проверки перед коммитом используйте следующую последовательность:

```bash
cd backend
../.venv/bin/python -m pytest
../.venv/bin/python -m ruff check .
../.venv/bin/python -m ruff format --check .
cd ..
.venv/bin/python -m pre_commit run --all-files
```

* `pytest`: проверка бизнес-логики и контрактов backend.
* `ruff check`: статический анализ кода (linting).
* `ruff format --check`: проверка соответствия стилю форматирования.
* `pre-commit run --all-files`: выполнение всех локальных hooks.

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
| Web UI | SSR HTML, CSRF, cookies, отсутствие токенов в HTML, базовые UI-контракты |
| Domain | алгоритм шифрования, валидация ключа/алфавита, edge cases |
| DB/Repositories | ownership, persistence, slug conflicts, seed default disk set |
| Security | JWT/refresh lifecycle, CSRF, rate limiter, запрет утечек токенов |
| Runtime smoke | контур Docker Compose, health/ready, nginx, Redis, security headers |

## Runtime smoke

```bash
bash scripts/smoke/compose_runtime_smoke.sh
```

* Проверяет готовность локального контура `docker-compose`.
* Не заменяет полный `pytest`.
* Подробности в [`docs/runtime.md`](./runtime.md).

## Pre-commit

```bash
.venv/bin/python -m pre_commit run --all-files
```

* Локальные hooks запускают обязательные проверки.
* Если hook изменил файлы (автоформат), проверьте изменения через `git diff`, затем повторите команду.
* Не обходите проверку через `--no-verify` без веской причины.

## Рекомендации для новых тестов

* Сначала тест на пользовательский или контрактный эффект, затем реализация.
* Используйте реальные модели и `fixtures` для повышения достоверности тестов.
* Не мокайте объекты, являющиеся сутью проверяемого поведения.
* В `Web UI` проверяйте семантические маркеры и наличие важных элементов, избегая привязки к верстке.
* В `Security` тестах проверяйте отсутствие токенов и секретов в HTML и логах.

## Финальный локальный чеклист

| Что изменилось | Действие |
| --- | --- |
| Логика `backend` | `pytest` |
| Шаблоны/static `web` | `pytest tests/web` + `ruff` |
| API contract | `pytest tests/api` + проверка `docs/api.md` |
| Runtime/compose/headers | `smoke` + проверка `docs/runtime.md`/`docs/security.md` |
| Перед коммитом | `pre-commit run --all-files` |
