#!/bin/sh
set -eu

BASE_URL=${DELTA_SMOKE_URL:-http://127.0.0.1:8502}
PUBLIC_HOST=${DELTA_PUBLIC_HOST:-delta.lemmata.app}
HEADERS=$(mktemp)
trap 'rm -f "$HEADERS"' EXIT HUP INT TERM

BODY=$(curl --fail --silent --show-error \
  --header "Host: $PUBLIC_HOST" \
  --dump-header "$HEADERS" \
  "$BASE_URL/_stcore/health")

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
