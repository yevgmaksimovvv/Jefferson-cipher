#!/bin/sh

set -eu

cert_path="${1:-${NGINX_CERT_PATH:-/etc/nginx/certs/localhost.crt}}"
key_path="${2:-${NGINX_KEY_PATH:-/etc/nginx/certs/localhost.key}}"
cert_dir="$(dirname "$cert_path")"

if [ -f "$cert_path" ] && [ -f "$key_path" ]; then
    exit 0
fi

if [ -f "$cert_path" ] || [ -f "$key_path" ]; then
    echo "Both certificate and key must exist together: $cert_path, $key_path" >&2
    exit 1
fi

mkdir -p "$cert_dir"
umask 077

openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
    -keyout "$key_path" \
    -out "$cert_path" \
    -subj "/CN=localhost" \
    -addext "subjectAltName = DNS:localhost,IP:127.0.0.1"
