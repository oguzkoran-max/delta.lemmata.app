#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEPLOYMENT=$ROOT/deploy/public-alpha
COMPOSE_FILE=$DEPLOYMENT/compose.yml

: "${DELTA_IMAGE:?DELTA_IMAGE is required}"
: "${DELTA_BUILD_ID:?DELTA_BUILD_ID is required}"
: "${DELTA_RUNTIME_ENV_FILE:?DELTA_RUNTIME_ENV_FILE is required}"

if [ -x "$ROOT/.tools/uv/bin/uv" ]; then
  UV_BIN=$ROOT/.tools/uv/bin/uv
elif command -v uv >/dev/null 2>&1; then
  UV_BIN=$(command -v uv)
else
  printf '%s\n' "p014-runtime-gate-uv-missing" >&2
  exit 1
fi

RATE_RESULTS=$(mktemp)
OVERSIZED_BODY=$(mktemp)
BROWSER_RECORD=$(mktemp)
STACK_STARTED=0

cleanup() {
  if [ "$STACK_STARTED" -eq 1 ]; then
    docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" down \
      --remove-orphans --timeout 75 >/dev/null 2>&1 || true
  fi
  rm -f "$RATE_RESULTS" "$OVERSIZED_BODY" "$BROWSER_RECORD"
}
trap cleanup EXIT HUP INT TERM

gateway_start_diagnostics() {
  docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" ps --all >&2 || true
  # No public request or corpus upload has occurred when this helper is called.
  docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" logs \
    --no-color --tail 100 gateway >&2 || true
}

cd "$DEPLOYMENT"
"$UV_BIN" run python "$ROOT/scripts/validate_p014_deployment.py"
docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" config --quiet
STACK_STARTED=1
if ! docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" up \
  --detach --remove-orphans --wait --wait-timeout 180; then
  gateway_start_diagnostics
  printf '%s\n' "p014-runtime-stack-start-failed" >&2
  exit 1
fi

APP_ID=$(docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" ps --quiet app)
GATEWAY_ID=$(docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" ps --quiet gateway)
if [ -z "$APP_ID" ] || [ -z "$GATEWAY_ID" ]; then
  printf '%s\n' "p014-runtime-gate-container-missing" >&2
  exit 1
fi

"$UV_BIN" run python "$ROOT/scripts/inspect_p014_runtime.py" \
  --app "$APP_ID" --gateway "$GATEWAY_ID"
if ! "$ROOT/scripts/smoke_p014_stack.sh"; then
  gateway_start_diagnostics
  printf '%s\n' "p014-runtime-published-gateway-failed" >&2
  exit 1
fi

if docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" exec -T app \
  /bin/sh -c 'touch /opt/delta/p014-write-probe' >/dev/null 2>&1; then
  printf '%s\n' "p014-runtime-root-write-succeeded" >&2
  exit 1
fi

docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" exec -T app \
  /opt/delta/.venv/bin/python -c \
  "import os, stat; p='/var/lib/delta/runtime'; s=os.stat(p); assert s.st_uid == 10001 and stat.S_IMODE(s.st_mode) == 0o700"

if docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" exec -T app \
  /opt/delta/.venv/bin/python -c \
  "import socket; socket.create_connection(('1.1.1.1', 443), timeout=2)" \
  >/dev/null 2>&1; then
  printf '%s\n' "p014-runtime-egress-succeeded" >&2
  exit 1
fi

if [ "${DELTA_P014_BROWSER_AUDIT:-0}" = "1" ]; then
  "$UV_BIN" run python "$ROOT/scripts/browser_audit_p014_gateway.py" \
    --output "$BROWSER_RECORD"
fi

dd if=/dev/zero of="$OVERSIZED_BODY" bs=1048576 count=27 2>/dev/null
BODY_STATUS=$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --header 'Host: delta.lemmata.app' \
  --header 'Content-Type: application/octet-stream' \
  --data-binary "@$OVERSIZED_BODY" \
  http://127.0.0.1:8502/)
if [ "$BODY_STATUS" != "413" ]; then
  printf '%s\n' "p014-runtime-request-size-failed" >&2
  exit 1
fi

: > "$RATE_RESULTS"
export RATE_RESULTS
seq 1 90 | xargs -P 20 -I '{}' /bin/sh -c \
  'curl --silent --output /dev/null --write-out "%{http_code}\n" --header "Host: delta.lemmata.app" http://127.0.0.1:8502/_stcore/health >> "$RATE_RESULTS"'
if ! grep -q '^429$' "$RATE_RESULTS"; then
  printf '%s\n' "p014-runtime-rate-limit-not-observed" >&2
  exit 1
fi
if grep -Eq '^(000|5[0-9][0-9])$' "$RATE_RESULTS"; then
  printf '%s\n' "p014-runtime-rate-limit-unstable" >&2
  exit 1
fi

docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" down \
  --remove-orphans --timeout 75
STACK_STARTED=0
if [ -n "$(docker compose --project-name delta-public-alpha --file "$COMPOSE_FILE" ps --quiet)" ]; then
  printf '%s\n' "p014-runtime-cleanup-failed" >&2
  exit 1
fi

printf '%s\n' "p014-runtime-gate-ok"
