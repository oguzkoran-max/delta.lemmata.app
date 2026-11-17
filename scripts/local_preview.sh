#!/usr/bin/env bash
# Small local preview using the pinned Linux runtime and RAM-backed source files.
# Existing application files and containers are never removed by this script.
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
docker_bin="/Applications/Docker.app/Contents/Resources/bin/docker"
app_name="delta-entry-preview-memory"
gateway_name="delta-entry-preview-gateway-memory"
private_network="delta-entry-preview-isolated"
edge_network="delta-entry-preview-edge"
app_image="sha256:14c0b3cfde2e059af9fedb6d29f3482a9aa7cad7296e864817be4536a7871dd7"
gateway_image="nginxinc/nginx-unprivileged:1.30.3-alpine-slim@sha256:3b24c4bfb2b9f60359b1475605ca1c8ed6e4963eb8369c6835be4d96bdb3ea81"

"$docker_bin" info --format '{{.ServerVersion}}' >/dev/null
"$docker_bin" image inspect "$app_image" "$gateway_image" >/dev/null
app_running="$("$docker_bin" inspect --format '{{.State.Running}}' "$app_name" 2>/dev/null || true)"
gateway_running="$("$docker_bin" inspect --format '{{.State.Running}}' "$gateway_name" 2>/dev/null || true)"
if [ "$app_running" = true ] || [ "$gateway_running" = true ]; then
    if [ "$app_running" = true ] && [ "$gateway_running" = true ] &&
        curl --fail --silent --max-time 3 http://127.0.0.1:8768/_stcore/health >/dev/null; then
        printf 'An existing preview is running at http://127.0.0.1:8768/\n'
        printf 'Its source snapshot is preserved. Stop both preview containers before refreshing it.\n'
        exit 0
    fi
    printf 'A preview component is running, but the pair is unhealthy. Check its logs before restarting.\n' >&2
    exit 1
fi

if ! "$docker_bin" network inspect "$private_network" >/dev/null 2>&1; then
    "$docker_bin" network create --internal "$private_network" >/dev/null
fi
test "$("$docker_bin" network inspect --format '{{.Internal}}' "$private_network")" = true
if ! "$docker_bin" network inspect "$edge_network" >/dev/null 2>&1; then
    "$docker_bin" network create "$edge_network" >/dev/null
fi

if ! "$docker_bin" container inspect "$app_name" >/dev/null 2>&1; then
    "$docker_bin" create --name "$app_name" --platform linux/amd64 \
        --network "$private_network" --read-only --user 10001:10001 --init \
        --cap-drop ALL --security-opt no-new-privileges:true --pids-limit 128 \
        --cpus 1.5 --memory 1536m --memory-swap 1536m \
        --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m,mode=1777,uid=10001,gid=10001 \
        --tmpfs /var/lib/delta/runtime:rw,nosuid,nodev,noexec,size=512m,mode=0700,uid=10001,gid=10001 \
        --env DELTA_ENV=development --env DELTA_RUNTIME_ROOT=/var/lib/delta/runtime \
        --env DELTA_EXTERNAL_NETWORK=disabled --env PYTHONPATH=/tmp/preview/src \
        --entrypoint /bin/sh "$app_image" -ec \
        'umask 077; mkdir -p /tmp/preview; while [ ! -f /tmp/preview.ready ]; do sleep 1; done; cd /tmp/preview; ln -s /opt/delta/renv/library renv/library; exec /opt/delta/.venv/bin/streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --server.fileWatcherType=none --browser.gatherUsageStats=false' >/dev/null
fi
test "$("$docker_bin" inspect --format '{{.Image}}' "$app_name")" = "$app_image"
"$docker_bin" start "$app_name" >/dev/null
tar -C "$project_dir" -cf - app.py .streamlit/config.toml src/delta_lemmata \
    scripts/workers renv/activate.R renv/settings.json renv.lock |
    "$docker_bin" exec -i "$app_name" tar -xf - -C /tmp/preview --no-same-owner
"$docker_bin" exec "$app_name" touch /tmp/preview.ready

if ! "$docker_bin" container inspect "$gateway_name" >/dev/null 2>&1; then
    "$docker_bin" create --name "$gateway_name" --platform linux/amd64 \
        --network "$edge_network" --network "$private_network" \
        --publish 127.0.0.1:8768:8080 --read-only --user 101:101 \
        --cap-drop ALL --security-opt no-new-privileges:true --pids-limit 64 \
        --cpus 0.25 --memory 128m --memory-swap 128m \
        --tmpfs /tmp:rw,nosuid,nodev,noexec,size=32m,mode=0700,uid=101,gid=101 \
        --entrypoint /bin/sh "$gateway_image" -ec \
        'mkdir -p /tmp/client_temp /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp; while [ ! -f /tmp/preview.ready ]; do sleep 1; done; exec nginx -c /tmp/preview-nginx.conf -g "daemon off;"' >/dev/null
fi
test "$("$docker_bin" inspect --format '{{.Image}}' "$gateway_name")" = \
    "$("$docker_bin" image inspect --format '{{.Id}}' "$gateway_image")"
"$docker_bin" start "$gateway_name" >/dev/null
git -C "$project_dir" show HEAD:deploy/public-alpha/nginx.conf |
    sed -e "s/server app:8501/server $app_name:8501/" \
        -e 's/server_name delta.lemmata.app;/server_name localhost 127.0.0.1;/' \
        -e 's/X-Forwarded-Proto https;/X-Forwarded-Proto http;/' |
    "$docker_bin" exec -i "$gateway_name" sh -ec \
        'cat > /tmp/preview-nginx.conf; touch /tmp/preview.ready'

for attempt in {1..20}; do
    if curl --fail --silent --max-time 2 http://127.0.0.1:8768/_stcore/health >/dev/null; then
        printf 'Local preview ready at http://127.0.0.1:8768/\n'
        exit 0
    fi
    sleep 1
done
printf 'Preview startup is incomplete. Check the two local container logs.\n' >&2
exit 1
