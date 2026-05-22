#!/usr/bin/env bash
set -euo pipefail

found=0

while IFS= read -r -d '' path; do
  [[ -z "$path" ]] && continue
  if [[ "$path" == "scripts/precommit/forbid_staged_pem_material.sh" ]]; then
    continue
  fi
  if git show ":$path" | grep -aEq -- '-----BEGIN CERTIFICATE-----|-----BEGIN .*PRIVATE KEY-----'; then
    echo "PEM material detected in staged file: $path"
    found=1
  fi
done < <(git diff --cached --name-only --diff-filter=ACMR -z)

exit "$found"
