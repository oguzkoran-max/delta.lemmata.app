#!/bin/sh
set -eu

BASE_URL=${DELTA_SMOKE_URL:-http://127.0.0.1:8502}
PUBLIC_HOST=${DELTA_PUBLIC_HOST:-delta.lemmata.app}
READINESS_ATTEMPTS=${DELTA_SMOKE_READINESS_ATTEMPTS:-20}
READINESS_DELAY=${DELTA_SMOKE_READINESS_DELAY:-0.5}
HEADERS=$(mktemp)
BODY_FILE=$(mktemp)
CURL_ERROR=$(mktemp)
trap 'rm -f "$HEADERS" "$BODY_FILE" "$CURL_ERROR"' EXIT HUP INT TERM

case "$READINESS_ATTEMPTS" in
  ''|*[!0-9]*|0)
    printf '%s\n' "p014-smoke-readiness-attempts-invalid" >&2
    exit 1
    ;;
esac

ATTEMPT=1
while :; do
  : > "$HEADERS"
  : > "$BODY_FILE"
  : > "$CURL_ERROR"
  if curl --fail --silent --show-error \
    --connect-timeout 1 \
    --max-time 3 \
    --header "Host: $PUBLIC_HOST" \
    --dump-header "$HEADERS" \
    --output "$BODY_FILE" \
    "$BASE_URL/_stcore/health" 2>"$CURL_ERROR"; then
    break
  fi
  if [ "$ATTEMPT" -ge "$READINESS_ATTEMPTS" ]; then
    cat "$CURL_ERROR" >&2
    printf '%s\n' "p014-smoke-published-gateway-unavailable" >&2
    exit 1
  fi
  ATTEMPT=$((ATTEMPT + 1))
  sleep "$READINESS_DELAY"
done

BODY=$(cat "$BODY_FILE")

if [ "$BODY" != "ok" ]; then
  printf '%s\n' "p014-smoke-health-body-invalid" >&2
  exit 1
fi

for HEADER in \
  'X-Content-Type-Options: nosniff' \
  'X-Frame-Options: DENY' \
  'Referrer-Policy: no-referrer' \
  'Cross-Origin-Opener-Policy: same-origin' \
  'Cross-Origin-Resource-Policy: same-origin'
do
  if ! grep -i -q "^${HEADER}$(printf '\r')\{0,1\}$" "$HEADERS"; then
    printf '%s\n' "p014-smoke-security-header-missing" >&2
    exit 1
  fi
done

INVALID_STATUS=$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --header 'Host: invalid.example' \
  "$BASE_URL/_stcore/health")
if [ "$INVALID_STATUS" != "421" ]; then
  printf '%s\n' "p014-smoke-strict-host-failed" >&2
  exit 1
fi

printf '%s\n' "p014-stack-smoke-ok"
