#!/usr/bin/env bash

set -euo pipefail

root="$(git rev-parse --show-toplevel)"
cd "$root"

tmpdir="$(mktemp -d)"
compose_started=0

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  local status=$?

  set +e

  if [[ "$compose_started" -eq 1 ]]; then
    docker compose down >/dev/null 2>&1 || true
  fi

  if [[ -d "$tmpdir" ]]; then
    rm -rf "$tmpdir"
  fi

  if [[ -d nginx/certs ]]; then
    while IFS= read -r cert_file; do
      [[ -n "$cert_file" ]] || continue
      rm -f "$cert_file"
    done < <(git ls-files --others --exclude-standard -- nginx/certs)
  fi

  exit "$status"
}

trap cleanup EXIT

http_request() {
  local body_file="$1"
  shift
  curl -sS -o "$body_file" -w '%{http_code}' "$@"
}

http_request_with_headers() {
  local body_file="$1"
  local headers_file="$2"
  shift 2
  curl -sS -D "$headers_file" -o "$body_file" -w '%{http_code}' "$@"
}

wait_for_status() {
  local expected="$1"
  local label="$2"
  shift 2

  local attempt=1
  local status=""
  while [[ $attempt -le 60 ]]; do
    status="$("$@" 2>/dev/null || true)"
    if [[ "$status" == "$expected" ]]; then
      return 0
    fi
    sleep 1
    attempt=$((attempt + 1))
  done

  fail "timeout waiting for $label (last status: $status, expected: $expected)"
}

assert_contains() {
  local haystack="$1"
  local needle="$2"
  local label="$3"
  if ! printf '%s' "$haystack" | grep -Fq "$needle"; then
    fail "missing $label: $needle"
  fi
}

assert_regex() {
  local haystack="$1"
  local regex="$2"
  local label="$3"
  if ! printf '%s\n' "$haystack" | grep -Eq "$regex"; then
    fail "missing $label matching regex: $regex"
  fi
}

assert_header_equals() {
  local headers_file="$1"
  local header_name="$2"
  local expected_value="$3"
  local actual

  actual="$(
    tr -d '\r' <"$headers_file" | awk -F': ' -v name="$header_name" '
      tolower($1) == tolower(name) { print $2; found=1; exit }
      END { if (!found) exit 1 }
    '
  )" || fail "missing header: $header_name"

  if [[ "$actual" != "$expected_value" ]]; then
    fail "unexpected value for $header_name: got '$actual', expected '$expected_value'"
  fi
}

assert_header_absent() {
  local headers_file="$1"
  local header_name="$2"
  if tr -d '\r' <"$headers_file" | awk -F': ' -v name="$header_name" '
    tolower($1) == tolower(name) { found=1 }
    END { exit found ? 0 : 1 }
  '; then
    fail "unexpected header present: $header_name"
  fi
}

assert_json_value() {
  local body_file="$1"
  local key_path="$2"
  local expected="$3"

  python3 - "$body_file" "$key_path" "$expected" <<'PY'
import json
import sys

body_path, key_path, expected = sys.argv[1:]
with open(body_path, encoding="utf-8") as fh:
    payload = json.load(fh)

value = payload
for key in key_path.split("."):
    value = value[key]

if str(value) != expected:
    raise SystemExit(
        f"unexpected value for {key_path}: got {value!r}, expected {expected!r}"
    )
PY
}

assert_openapi_paths() {
  local body_file="$1"
  shift

  python3 - "$body_file" "$@" <<'PY'
import json
import sys

body_path = sys.argv[1]
required_paths = sys.argv[2:]

with open(body_path, encoding="utf-8") as fh:
    payload = json.load(fh)

paths = payload.get("paths", {})
missing = [path for path in required_paths if path not in paths]
if missing:
    raise SystemExit(f"missing openapi paths: {', '.join(missing)}")
PY
}

wait_for_backend_health() {
  local body_file="$tmpdir/backend-health.json"
  wait_for_status 200 "backend /api/v1/health" http_request "$body_file" http://localhost:8000/api/v1/health >/dev/null
}

wait_for_backend_ready() {
  local body_file="$tmpdir/backend-ready.json"
  wait_for_status 200 "backend /api/v1/ready" http_request "$body_file" http://localhost:8000/api/v1/ready >/dev/null
}

compose_ps_snapshot() {
  docker compose ps -a
}

docker compose config >/dev/null
compose_started=1
docker compose up -d --build >/dev/null

wait_for_backend_health
wait_for_backend_ready

backend_init_logs="$(docker compose logs backend-init --tail=100 2>/dev/null || true)"
assert_contains "$backend_init_logs" "Seeded disk set:" "backend-init seed log"

ps_output="$(compose_ps_snapshot)"
assert_regex "$ps_output" 'postgres.*healthy' "postgres healthy state"
assert_regex "$ps_output" 'redis.*(healthy|Up)' "redis running state"
assert_regex "$ps_output" 'backend-init.*Exited \(0\)' "backend-init exit status"
assert_regex "$ps_output" 'backend.*Up' "backend running state"
assert_regex "$ps_output" 'nginx.*Up' "nginx running state"

backend_health_body="$tmpdir/backend-health.json"
backend_health_status="$(http_request "$backend_health_body" http://localhost:8000/api/v1/health)"
[[ "$backend_health_status" == "200" ]] || fail "backend direct health returned $backend_health_status"

backend_ready_body="$tmpdir/backend-ready.json"
backend_ready_status="$(http_request "$backend_ready_body" http://localhost:8000/api/v1/ready)"
[[ "$backend_ready_status" == "200" ]] || fail "backend ready returned $backend_ready_status"
assert_json_value "$backend_ready_body" "status" "ready"
assert_json_value "$backend_ready_body" "rate_limiter" "ok"

nginx_http_body="$tmpdir/nginx-http-health.json"
nginx_http_status="$(http_request "$nginx_http_body" http://localhost:8080/api/v1/health)"
[[ "$nginx_http_status" == "200" ]] || fail "nginx HTTP health returned $nginx_http_status"

nginx_https_body="$tmpdir/nginx-https-health.json"
nginx_https_headers="$tmpdir/nginx-https-health.headers"
nginx_https_status="$(http_request_with_headers "$nginx_https_body" "$nginx_https_headers" -k https://localhost:8443/api/v1/health)"
[[ "$nginx_https_status" == "200" ]] || fail "nginx HTTPS health returned $nginx_https_status"
assert_header_equals "$nginx_https_headers" "X-Content-Type-Options" "nosniff"
assert_header_equals "$nginx_https_headers" "X-Frame-Options" "DENY"
assert_header_equals "$nginx_https_headers" "Referrer-Policy" "no-referrer"
assert_header_absent "$nginx_https_headers" "Strict-Transport-Security"

cors_body="$tmpdir/cors-preflight.json"
cors_headers="$tmpdir/cors-preflight.headers"
cors_status="$(http_request_with_headers "$cors_body" "$cors_headers" \
  -X OPTIONS \
  -H "Origin: https://localhost:8443" \
  -H "Access-Control-Request-Method: GET" \
  http://localhost:8000/api/v1/health)"
[[ "$cors_status" == "200" || "$cors_status" == "204" ]] || fail "CORS preflight returned $cors_status"
assert_header_equals "$cors_headers" "Access-Control-Allow-Origin" "https://localhost:8443"

openapi_body="$tmpdir/openapi.json"
openapi_status="$(http_request "$openapi_body" http://localhost:8000/openapi.json)"
[[ "$openapi_status" == "200" ]] || fail "openapi.json returned $openapi_status"
assert_openapi_paths "$openapi_body" \
  /api/v1/health \
  /api/v1/ready \
  /api/v1/auth/login \
  /api/v1/disk-sets

rate_limit_found=0
for attempt in $(seq 1 15); do
  login_body="$tmpdir/login-$attempt.json"
  login_status="$(http_request "$login_body" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"email":"smoke-rate-limit@example.com","password":"wrong-password"}' \
    http://localhost:8000/api/v1/auth/login)"
  if [[ "$login_status" == "429" ]]; then
    assert_json_value "$login_body" "error.code" "RATE_LIMIT_EXCEEDED"
    rate_limit_found=1
    break
  fi
done

[[ "$rate_limit_found" -eq 1 ]] || fail "did not observe 429 RATE_LIMIT_EXCEEDED during burst"

tracked_secret_diff="$(git diff --name-only -- .env nginx/certs '*.pem' '*.key')"
if [[ -n "$tracked_secret_diff" ]]; then
  printf '%s\n' "$tracked_secret_diff" >&2
  fail "tracked secrets/certs changed"
fi

untracked_secret_status="$(git status --short --untracked-files=all -- .env nginx/certs '*.pem' '*.key')"
if [[ -n "$untracked_secret_status" ]]; then
  printf '%s\n' "$untracked_secret_status" >&2
  fail "secrets/certs left in working tree"
fi

printf 'compose runtime smoke passed\n'
