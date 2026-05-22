#!/usr/bin/env bash
set -euo pipefail

if rg -n -i -e 'create_async_engine' -e 'AsyncSession' -e 'asyncpg' -e 'aiosqlite' backend/app; then
  exit 1
fi
