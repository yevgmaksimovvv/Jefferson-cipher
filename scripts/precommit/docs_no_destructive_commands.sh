#!/usr/bin/env bash
set -euo pipefail

violations="$(
  rg -n -i -e 'cp \.env\.example \.env' -e 'docker compose down[[:space:]]+-v' README.md docs .env.example || true
)"

if [[ -z "$violations" ]]; then
  exit 0
fi

if printf '%s\n' "$violations" | rg -vi 'не выполнять|не используйте|не запускайте|do not|dont'; then
  printf '%s\n' "$violations"
  exit 1
fi
