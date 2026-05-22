#!/usr/bin/env bash
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
cd "$root/backend"

tests=(
  tests/api/test_health.py
  tests/api/test_cors_and_security_headers.py
  tests/api/test_rate_limiting.py
  tests/db/test_runtime_contract.py
)

if [[ -f tests/core/test_config.py ]]; then
  tests+=(tests/core/test_config.py)
fi

"$root/.venv/bin/python" -m pytest "${tests[@]}"
