# Testing Guide

## Запуск тестов
Запустите полный набор тестов из корня:
```bash
cd backend && ../.venv/bin/python -m pytest
```

## Линтинг
```bash
cd backend && ../.venv/bin/python -m ruff check .
cd backend && ../.venv/bin/python -m ruff format --check .
```

## Pre-commit
```bash
.venv/bin/python -m pre_commit run --all-files
```

## Область тестирования (Test Scope)
- **API**: Валидация входных данных, контракты ошибок, статус-коды.
- **Domain**: Краевые случаи алгоритма шифрования, валидация.
- **DB/Runtime**: Миграции Alembic, наполнение данными (seeding), ограничения моделей, разделение URL для хоста и контейнера.
- **Security**: Валидация владения, жизненный цикл JWT, ротация refresh токенов.
