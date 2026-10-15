#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export APP_IMAGE="${1:?Pass the immutable application image reference}"
command -v docker >/dev/null
command -v python3 >/dev/null
command -v openssl >/dev/null
docker compose version >/dev/null
umask 077
if [ ! -f .env ]; then
  {
    printf 'POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 32)"
    printf 'REDIS_PASSWORD=%s\n' "$(openssl rand -hex 32)"
    printf 'JWT_SECRET=%s\n' "$(openssl rand -hex 32)"
    printf 'TOTP_ENCRYPTION_KEY=%s\n' "$(openssl rand -hex 32)"
    printf 'ADMIN_EMAIL=admin@warp.local\n'
    printf 'ADMIN_PASSWORD=WarpGate-%s\n' "$(openssl rand -hex 16)"
    printf 'BIND_HOST=127.0.0.1\nSERVER_PORT=8080\n'
  } > .env
fi
set -a
source .env
set +a
export SMOKE_BASE_URL="http://127.0.0.1:${SERVER_PORT:-8080}"
project=(docker compose -p warpgate --env-file .env -f compose.server.yaml)
previous_image=""
if [ -f deployed-image.txt ]; then previous_image="$(cat deployed-image.txt)"; fi
if ! "${project[@]}" up -d --wait --wait-timeout 240; then
  if [ -n "$previous_image" ]; then
    echo 'Startup failed; restoring the previous application image.'
    APP_IMAGE="$previous_image" "${project[@]}" up -d --wait --wait-timeout 240 || true
  fi
  exit 1
fi
if [ ! -f .brand-initialized ]; then export INITIALIZE_BRAND=true; fi
python3 smoke.py
touch .brand-initialized
printf '%s\n' "$APP_IMAGE" > deployed-image.txt
echo 'WarpGate deployment verified. Initial administrator credentials are in the server .env file.'
