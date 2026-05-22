#!/bin/sh

set -eu

cert_path="${NGINX_CERT_PATH:-/etc/nginx/certs/localhost.crt}"
key_path="${NGINX_KEY_PATH:-/etc/nginx/certs/localhost.key}"

if [ "${NGINX_GENERATE_SELF_SIGNED:-true}" = "true" ]; then
    /docker/scripts/generate_self_signed_cert.sh "$cert_path" "$key_path"
else
    host_cert_path="/mnt/nginx-host-certs/fullchain.pem"
    host_key_path="/mnt/nginx-host-certs/privkey.pem"

    if [ ! -f "$host_cert_path" ] || [ ! -f "$host_key_path" ]; then
        echo "Custom TLS certs are required but missing: $host_cert_path, $host_key_path" >&2
        exit 1
    fi

    mkdir -p "$(dirname "$cert_path")"
    cp "$host_cert_path" "$cert_path"
    cp "$host_key_path" "$key_path"
fi

exec nginx -g 'daemon off;'
