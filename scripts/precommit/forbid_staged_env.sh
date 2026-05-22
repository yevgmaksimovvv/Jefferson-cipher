#!/usr/bin/env bash
set -euo pipefail

if git diff --cached --name-only --diff-filter=ACMR | grep -Eq '(^|/)\.env$'; then
  echo ".env must not be committed"
  exit 1
fi
