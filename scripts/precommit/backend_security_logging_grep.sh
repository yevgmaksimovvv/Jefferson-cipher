#!/usr/bin/env bash
set -euo pipefail

if rg -n -i -e '\b(logger|log)\b.*\bpassword\b|\bpassword\b.*\b(logger|log)\b' -e '\b(logger|log)\b.*\baccess_token\b|\baccess_token\b.*\b(logger|log)\b' -e '\b(logger|log)\b.*\brefresh_token\b|\brefresh_token\b.*\b(logger|log)\b' -e '\b(logger|log)\b.*\bauthorization\b|\bauthorization\b.*\b(logger|log)\b' backend/app; then
  exit 1
fi
