# Delta Public-Alpha Deployment Runbook

This runbook is executable only after the exact source commit passes canonical
CI. It must be followed in order. A failed step stops the rollout; the next step
is not used to work around it.

## What This Package Does

- Keeps the existing host Caddy service as the public TLS boundary.
- Binds the Delta-only gateway to `127.0.0.1:8502`.
- Runs Streamlit only on a private internal network with no default-route egress.
- Uses a separate gateway-only edge bridge to publish host loopback `8502`; the
  application never joins that bridge.
- Preserves the validated public Host authority for Streamlit WebSockets and
  pins the external scheme to HTTPS because the gateway is reachable only
  through the host TLS route.
- Keys request and connection budgets by Caddy's replaced `X-Forwarded-For`
  value, with a socket-address fallback for direct loopback health probes, so
  unrelated public visitors do not consume one shared Docker-bridge budget.
- Exempts Streamlit's parallel `/static/` JavaScript and CSS boot assets from
  the concurrent-connection cap while retaining their separate bounded request
  rate, preventing an accepted browser from receiving an incomplete white page.
- Gives Delta separate containers, environment files, secrets, runtime storage,
  labels, health checks, resource limits, and rollback controls.
- Leaves the existing Lemmata application, service, environment, volume, secret,
  data, and internal port unchanged.

The two applications still share one VPS kernel and host resources. This is
operational separation under tested controls, not complete isolation.

## Required Evidence Before Host Work

1. The exact source commit is clean and pushed.
2. The GitHub Actions `verify` and `container` jobs are green.
3. The container job reports `p014-runtime-gate-ok`.
4. The application image has an immutable `sha256` reference.
5. The source commit, image digest, gateway digest, CI run, and CI job are copied
   into the P014 run record without a secret or uploaded text.

## Phase 0: Publish the Exact Application Image

Do not build Delta on the shared VPS. After the exact source commit's normal CI
run is green, manually dispatch `.github/workflows/p014-publish-image.yml` with
that full commit as `source_sha`. The workflow checks that prerequisite run,
rebuilds the same Linux amd64 profile, repeats the hardened stack and browser
gates, and publishes only `sha-<commit>` to GHCR. It does not publish `latest`.

Record the workflow run, job, source commit, local image ID, and returned
`repository@sha256:...` reference. Deployment uses the digest reference, not the
commit tag. A publication failure stops the rollout and remains in the P014
history.

## Phase 1: Read-Only Host Inventory

Do not install, restart, reload, stop, or edit anything in this phase. Docker is
expected to be absent on the first run; absence is recorded rather than treated
as an inventory-command failure. Transfer the exact green operations tree to a
private root-only staging directory, then run:

```bash
set -Eeuo pipefail
install -d -o root -g root -m 0700 /root/p014-host-evidence
python3 scripts/p014_host_gate.py pre-docker \
  --output /root/p014-host-evidence/pre-docker.json \
  --samples 20
```

The tool records only OS/resource facts, selected service properties, Caddyfile
hash, listener addresses and ports, firewall-rule hashes and counts, forwarding values,
memory pressure, package/runtime versions, and aggregate health/latency metrics.
It does not print or retain environment values, process command lines, request
bodies, uploaded text, registry credentials, or Caddyfile contents.

For manual diagnosis, use commands that tolerate the expected absent runtime:

```bash
set -Eeuo pipefail
date -u +%Y-%m-%dT%H:%M:%SZ
uname -a
cat /etc/os-release
nproc
free -m
df -h /
command -v docker || printf '%s\n' docker-absent
systemctl is-active docker caddy lemmata || true
systemctl show lemmata --property=ActiveState,SubState,NRestarts,MemoryCurrent,ExecMainStartTimestampMonotonic
ss -H -ltn 'sport = :8501 or sport = :8502'
sha256sum /etc/caddy/Caddyfile
curl --fail --silent --show-error https://lda.lemmata.app/_stcore/health
```

Never run `systemctl show-environment`, print an environment file, dump a Docker
container environment, or capture a process command line that may contain a
secret. The inventory is rejected if Lemmata is not healthy, port `8502` is in
use, disk/memory headroom is insufficient, or the documented topology differs
from the observed host.

The accepted evidence contract for this rollout is `p014-host-gate/1.3.0`.
Evidence produced by an older schema is not reused or upgraded by hand.

## Phase 2: Accept Runtime and Capacity Policy

No package is installed until `ADR-0018` is explicitly accepted by Oğuz Koran.
The proposed accelerated profile uses the existing VPS, the stable official
Docker Engine and Compose plugin, and no new host swap. It does not modify or
apply a finite resource cap to Lemmata.

Immediately before installation, repeat the safe inventory and require:

- Lemmata and Caddy active, Lemmata health `ok`, and port `8502` free;
- at least `2,048 MiB` available memory and `10 GiB` available root disk;
- recorded Lemmata start time, restart count, memory, Caddyfile hash, sockets,
  forwarding values, firewall-rule counts, and memory-pressure values;
- a paired Lemmata latency baseline collected immediately before the change.

Install Docker only from its signed official Ubuntu repository and record exact
package versions plus repository/key hashes. Docker documents that bridge
networking creates firewall rules and may enable IP forwarding. Capture those
differences and immediately rerun Lemmata health, restart, latency, Caddy, socket,
and direct-external-port checks before pulling or installing Delta. Stop if
available memory is below `1,800 MiB`, Lemmata restarts or errors, an unexpected
public socket appears, or paired p95 latency increases by more than the frozen
CE-15 budget of `20%`.

Do not disable Docker firewall management as a shortcut. Do not create a plain
swapfile. Both Delta services retain `memswap_limit == mem_limit`, so they cannot
use swap. If the measured no-swap profile fails, stop and use a memory upgrade or
separate VPS rather than weakening the accepted limits.

## Phase 3: Install and Compare the Container Runtime

Use only the guarded installer from the exact green operations commit. It
refuses a pre-existing runtime, Docker repository, key, data root, conflicting
package, wrong OS/architecture, failed preflight, reused evidence path, or an
unscoped invocation. It pins every package to the current signed stable
candidate, verifies Docker's primary signing-key fingerprint, starts only
Docker, and immediately runs the post-Docker Lemmata comparison:

```bash
set -Eeuo pipefail
scripts/p014_install_docker_ubuntu.sh \
  --preflight /root/p014-host-evidence/pre-docker.json \
  --post-output /root/p014-host-evidence/post-docker.json \
  --rollback-output /root/p014-host-evidence/post-rollback.json \
  --state-dir /root/p014-host-evidence/docker-change \
  --apply
```

The installer accepts the Phase 1 `pre-docker` baseline, copies it into its
root-only transaction directory, then captures and validates a fresh
`pre-mutation` observation immediately before the first package change. Do not
generate or pass a standalone `pre-mutation` file to `--preflight`; that phase is
owned by the guarded transaction so the baseline and last-moment observation
cannot be interchanged.

Any failed command or post-Docker gate invokes the guarded rollback. Rollback
purges only the fixed Docker package allowlist introduced by this unfinished
transaction, removes only installer-owned repository/key paths whose hashes were
validated before mutation, removes only newly owned Docker runtime roots, restores
the captured iptables/ip6tables inputs and forwarding values, and requires the
original listeners, complete firewall hashes, Caddyfile hash, Lemmata process
identity, health, latency budget, and no-Docker state. A successful installation
disarms this destructive rollback before any Delta image is pulled.

If a completed installation must be removed solely to refresh an expired
pre-Docker measurement window, use the same exact operations commit with the
explicit `--completed-install-removal` mode. This maintenance path accepts only
the original completed/disarmed transaction, verifies that every installed
Docker package still has its recorded version, refuses any image or container,
preserves the original transaction markers, and writes separate
`completed-removal-started` and `completed-removal-complete` evidence. Remove
only rollout-owned images first; never use this mode on a shared or populated
Docker runtime. Its output is a newly captured, accepted `pre-docker` baseline
for the immediate reinstall; it does not compare against the expired baseline:

```bash
set -Eeuo pipefail
scripts/p014_rollback_docker_ubuntu.sh \
  --state-dir /root/p014-host-evidence/docker-change \
  --output /root/p014-host-evidence/pre-docker-after-completed-removal.json \
  --completed-install-removal \
  --apply
```

The post-install gate reuses the installer's private APT list directory rather
than consulting the host's unrelated default package index. If the accepted
pre-Docker firewall snapshots were all empty, rollback captures the residual
rules and flushes the Docker-created nftables ruleset before proving the exact
empty baseline. Non-empty baselines continue to use their captured iptables and
ip6tables restore inputs.

Do not continue unless `post-docker.json` has `gate.passed=true`, available
memory is at least `1,800 MiB`, and no public listener was added. Retain the
root-only state directory for the rollout evidence.

Before any image pull, pause and run this denial probe from a genuinely external
machine or network:

```bash
set -Eeuo pipefail
: "${DELTA_HOST:?Set DELTA_HOST to the server public IP or DNS name}"
if curl --fail --show-error --max-time 5 \
  "http://${DELTA_HOST}:8502/_stcore/health"; then
  echo "P014_POST_DOCKER_EXTERNAL_8502_REACHABLE" >&2
  exit 1
fi
```

This Phase 3 check proves only that installing Docker did not expose port
`8502`; Delta does not exist yet. The separate Phase 4 external check, after the
stack starts, is what proves Delta's published gateway remains loopback-only.

## Phase 4: Install an Immutable Release

Use a release directory named by the full source commit:

```text
/opt/delta-public-alpha/releases/<40-character-commit>/
/opt/delta-public-alpha/current -> releases/<40-character-commit>
/etc/delta-public-alpha/deployment.env
/etc/delta-public-alpha/runtime.env
/etc/systemd/system/delta-public-alpha.service
```

Transfer only the tracked tree from the exact green commit. Do not copy a dirty
working directory, `.git`, a local virtual environment, caches, uploads, or an
environment file. On the workstation, create the source stream with
`git archive <40-character-commit>`; on the host, extract it into a new,
root-owned release directory and verify that the archived source commit is the
same commit recorded in the CI evidence. Never overwrite an existing release.

Release source is root-owned and not writable by the containers. The application
image is pulled before systemd starts because the unit deliberately cannot read
root's Docker credential directory.

On the workstation, create and checksum one archive from the exact commit that
produced the immutable image, then transfer only that archive:

```bash
set -Eeuo pipefail
: "${SOURCE_SHA:?Set SOURCE_SHA to the exact 40-character green commit}"
: "${DELTA_HOST:?Set DELTA_HOST to the server public IP or DNS name}"
[[ $SOURCE_SHA =~ ^[0-9a-f]{40}$ ]]
git archive --format=tar --output /tmp/delta-release.tar "$SOURCE_SHA"
sha256sum /tmp/delta-release.tar
scp -i ~/.ssh/lemmata_oracle /tmp/delta-release.tar \
  root@"${DELTA_HOST}":/root/delta-release.tar
```

On the host, refuse an existing release, extract it as root, and switch
`current` only after the release files are in place:

```bash
set -Eeuo pipefail
: "${SOURCE_SHA:?Set SOURCE_SHA to the exact 40-character green commit}"
: "${ARCHIVE_SHA256:?Set ARCHIVE_SHA256 to the workstation checksum}"
[[ $SOURCE_SHA =~ ^[0-9a-f]{40}$ ]]
[[ $ARCHIVE_SHA256 =~ ^[0-9a-f]{64}$ ]]
RELEASE_ROOT="/opt/delta-public-alpha/releases/$SOURCE_SHA"
printf '%s  %s\n' "$ARCHIVE_SHA256" /root/delta-release.tar | sha256sum --check --strict
install -d -o root -g root -m 0755 /opt/delta-public-alpha/releases
test ! -e "$RELEASE_ROOT"
test ! -e /opt/delta-public-alpha/current.next
install -d -o root -g root -m 0755 "$RELEASE_ROOT"
tar --extract --file /root/delta-release.tar \
  --directory "$RELEASE_ROOT" \
  --no-same-owner --no-same-permissions
printf '%s\n' "$SOURCE_SHA" > "$RELEASE_ROOT/.p014-source-sha"
chown -R root:root "$RELEASE_ROOT"
chmod -R a-w "$RELEASE_ROOT"
ln -s "releases/$SOURCE_SHA" /opt/delta-public-alpha/current.next
mv -Tf /opt/delta-public-alpha/current.next /opt/delta-public-alpha/current
cd "$RELEASE_ROOT"
[[ $PWD == "$RELEASE_ROOT" ]]
[[ $(<.p014-source-sha) == "$SOURCE_SHA" ]]
[[ $(readlink -f /opt/delta-public-alpha/current) == "$RELEASE_ROOT" ]]
```

The real `deployment.env` must contain:

```text
DELTA_IMAGE=<registry/repository@sha256:immutable-manifest-digest>
DELTA_BUILD_ID=<the-same-40-character-source-commit>
DELTA_RUNTIME_ENV_FILE=/etc/delta-public-alpha/runtime.env
```

Create the file without shell-history interpolation or a text editor:

```bash
set -Eeuo pipefail
: "${DELTA_IMAGE:?Set DELTA_IMAGE to the immutable GHCR digest reference}"
: "${SOURCE_SHA:?Set SOURCE_SHA to the exact source commit}"
[[ $DELTA_IMAGE == *@sha256:* ]]
[[ $SOURCE_SHA =~ ^[0-9a-f]{40}$ ]]
RELEASE_ROOT="/opt/delta-public-alpha/releases/$SOURCE_SHA"
[[ $(<"$RELEASE_ROOT/.p014-source-sha") == "$SOURCE_SHA" ]]
install -d -o root -g root -m 0700 /etc/delta-public-alpha
test ! -e /etc/delta-public-alpha/deployment.env
printf 'DELTA_IMAGE=%s\nDELTA_BUILD_ID=%s\nDELTA_RUNTIME_ENV_FILE=%s\n' \
  "$DELTA_IMAGE" "$SOURCE_SHA" /etc/delta-public-alpha/runtime.env \
  > /etc/delta-public-alpha/deployment.env
chown root:root /etc/delta-public-alpha/deployment.env
chmod 0600 /etc/delta-public-alpha/deployment.env
```

Pull the exact digest before systemd starts. For the private registry, use a
dedicated classic personal access token with only `read:packages`, pass it through
standard input, then log out after the pull; never put registry credentials in
either Delta environment file:

```bash
set -Eeuo pipefail
set -a
. /etc/delta-public-alpha/deployment.env
set +a
: "${DELTA_BUILD_ID:?Missing DELTA_BUILD_ID}"
[[ $DELTA_BUILD_ID =~ ^[0-9a-f]{40}$ ]]
SOURCE_SHA=$DELTA_BUILD_ID
RELEASE_ROOT="/opt/delta-public-alpha/releases/$SOURCE_SHA"
[[ $(<"$RELEASE_ROOT/.p014-source-sha") == "$SOURCE_SHA" ]]
DOCKER_CONFIG=$(mktemp -d /root/p014-docker-config.XXXXXX)
export DOCKER_CONFIG
cleanup_registry_auth() {
  local status=$?
  local cleanup_status=0
  trap - EXIT
  unset GHCR_TOKEN
  if ! docker logout ghcr.io >/dev/null 2>&1; then
    cleanup_status=1
  fi
  if ! rm -rf -- "$DOCKER_CONFIG"; then
    cleanup_status=1
  fi
  if (( cleanup_status != 0 )); then
    echo "P014_REGISTRY_AUTH_CLEANUP_FAILED" >&2
    exit 97
  fi
  exit "$status"
}
trap cleanup_registry_auth EXIT
read -r -s -p 'GHCR read:packages token: ' GHCR_TOKEN
printf '\n'
printf '%s' "$GHCR_TOKEN" | \
  docker login ghcr.io --username oguzkoran-max --password-stdin
docker pull "$DELTA_IMAGE"
python3 "$RELEASE_ROOT/scripts/verify_p014_image.py" \
  --image-reference "$DELTA_IMAGE" \
  --source-sha "$SOURCE_SHA"
```

The verifier requires the exact digest reference in Docker's local
`RepoDigests` and an exact `org.opencontainers.image.revision` match before any
service is started. Record only the image reference and resulting image ID. Do not record the
credential, Docker config, or environment-file contents.

Create the private secret directory and file without printing the values:

```bash
set -Eeuo pipefail
set -a
. /etc/delta-public-alpha/deployment.env
set +a
RELEASE_ROOT="/opt/delta-public-alpha/releases/$DELTA_BUILD_ID"
[[ $(<"$RELEASE_ROOT/.p014-source-sha") == "$DELTA_BUILD_ID" ]]
cd "$RELEASE_ROOT"
install -d -o root -g root -m 0700 /etc/delta-public-alpha
python3 scripts/generate_p014_secrets.py --output /etc/delta-public-alpha/runtime.env
chown root:root /etc/delta-public-alpha/runtime.env
chmod 0600 /etc/delta-public-alpha/runtime.env
```

Validate the release and compose expansion before startup:

```bash
set -Eeuo pipefail
set -a
. /etc/delta-public-alpha/deployment.env
set +a
RELEASE_ROOT="/opt/delta-public-alpha/releases/$DELTA_BUILD_ID"
[[ $(<"$RELEASE_ROOT/.p014-source-sha") == "$DELTA_BUILD_ID" ]]
cd "$RELEASE_ROOT"
python3 scripts/validate_p014_deployment.py
docker compose --project-name delta-public-alpha \
  --env-file /etc/delta-public-alpha/deployment.env \
  --file deploy/public-alpha/compose.yml config --quiet
```

Materialize the unit with the exact release path. The tracked unit is a template;
the installed unit must not depend on the mutable `current` symlink. The same
shell arms a fail-closed cleanup before service start and keeps it armed through
stack smoke, runtime inspection, and the Delta-idle host gate. A failure stops
and disables Delta, removes the Compose project and first-release unit, and
requires both an empty project and a closed port `8502` before returning:

```bash
set -Eeuo pipefail
set -a
. /etc/delta-public-alpha/deployment.env
set +a
: "${DELTA_BUILD_ID:?Missing DELTA_BUILD_ID}"
[[ $DELTA_BUILD_ID =~ ^[0-9a-f]{40}$ ]]
SOURCE_SHA=$DELTA_BUILD_ID
RELEASE_ROOT="/opt/delta-public-alpha/releases/$SOURCE_SHA"
UNIT_PATH=/etc/systemd/system/delta-public-alpha.service
UNIT_STAGE="/etc/systemd/system/.delta-public-alpha.$SOURCE_SHA.service"
[[ $(<"$RELEASE_ROOT/.p014-source-sha") == "$SOURCE_SHA" ]]
[[ $(readlink -f /opt/delta-public-alpha/current) == "$RELEASE_ROOT" ]]
test ! -e "$UNIT_PATH"
test ! -e "$UNIT_STAGE"
cd "$RELEASE_ROOT"

COMPOSE=(
  docker compose --project-name delta-public-alpha
  --env-file /etc/delta-public-alpha/deployment.env
  --file "$RELEASE_ROOT/deploy/public-alpha/compose.yml"
)
PREEXISTING_CONTAINERS=$("${COMPOSE[@]}" ps --quiet)
[[ -z $PREEXISTING_CONTAINERS ]]
PREEXISTING_LISTENERS=$(ss -H -ltn 'sport = :8502')
[[ -z $PREEXISTING_LISTENERS ]]
PRE_CADDY_GATES_COMPLETE=0
cleanup_failed_first_release() {
  local status=$?
  local cleanup_status=0
  local remaining_containers
  local remaining_listeners
  trap - EXIT
  if (( PRE_CADDY_GATES_COMPLETE == 1 )); then
    exit "$status"
  fi
  if [[ -e $UNIT_PATH ]]; then
    if ! systemctl stop delta-public-alpha.service; then
      echo "P014_PRE_CADDY_STOP_FAILED" >&2
      cleanup_status=1
    fi
    if ! systemctl disable delta-public-alpha.service; then
      echo "P014_PRE_CADDY_DISABLE_FAILED" >&2
      cleanup_status=1
    fi
  fi
  if ! "${COMPOSE[@]}" down --remove-orphans --timeout 75; then
    echo "P014_PRE_CADDY_COMPOSE_DOWN_FAILED" >&2
    cleanup_status=1
  fi
  if ! remaining_containers=$("${COMPOSE[@]}" ps --quiet); then
    echo "P014_PRE_CADDY_PROJECT_INSPECTION_FAILED" >&2
    cleanup_status=1
  elif [[ -n $remaining_containers ]]; then
    echo "P014_PRE_CADDY_CONTAINERS_REMAIN" >&2
    cleanup_status=1
  fi
  if ! remaining_listeners=$(ss -H -ltn 'sport = :8502'); then
    echo "P014_PRE_CADDY_LISTENER_INSPECTION_FAILED" >&2
    cleanup_status=1
  elif [[ -n $remaining_listeners ]]; then
    echo "P014_PRE_CADDY_8502_REMAINS" >&2
    cleanup_status=1
  fi
  if ! rm -f -- "$UNIT_STAGE" "$UNIT_PATH"; then
    echo "P014_PRE_CADDY_UNIT_REMOVE_FAILED" >&2
    cleanup_status=1
  fi
  if ! systemctl daemon-reload; then
    echo "P014_PRE_CADDY_DAEMON_RELOAD_FAILED" >&2
    cleanup_status=1
  fi
  if (( cleanup_status != 0 )); then
    echo "P014_PRE_CADDY_CLEANUP_INCOMPLETE" >&2
    exit 96
  fi
  exit "$status"
}
trap cleanup_failed_first_release EXIT

TEMPLATE_WORKDIR='WorkingDirectory=/opt/delta-public-alpha/current/deploy/public-alpha'
RELEASE_WORKDIR="WorkingDirectory=$RELEASE_ROOT/deploy/public-alpha"
[[ $(grep -Fxc "$TEMPLATE_WORKDIR" deploy/public-alpha/delta-public-alpha.service) == 1 ]]
sed "s|^$TEMPLATE_WORKDIR$|$RELEASE_WORKDIR|" \
  deploy/public-alpha/delta-public-alpha.service > "$UNIT_STAGE"
[[ $(grep -Fxc "$RELEASE_WORKDIR" "$UNIT_STAGE") == 1 ]]
! grep -Fq '/opt/delta-public-alpha/current' "$UNIT_STAGE"
chown root:root "$UNIT_STAGE"
chmod 0644 "$UNIT_STAGE"
mv -f "$UNIT_STAGE" "$UNIT_PATH"
systemctl daemon-reload

systemctl enable --now delta-public-alpha.service
scripts/smoke_p014_stack.sh
"${COMPOSE[@]}" ps
APP_ID=$("${COMPOSE[@]}" ps --quiet app)
GATEWAY_ID=$("${COMPOSE[@]}" ps --quiet gateway)
[[ $APP_ID =~ ^[0-9a-f]{64}$ && $GATEWAY_ID =~ ^[0-9a-f]{64}$ ]]
python3 scripts/inspect_p014_runtime.py --app "$APP_ID" --gateway "$GATEWAY_ID"
python3 scripts/p014_host_gate.py delta-idle \
  --baseline /root/p014-host-evidence/pre-docker.json \
  --apt-lists-dir /root/p014-host-evidence/docker-change/apt-lists \
  --output /root/p014-host-evidence/delta-idle.json \
  --samples 20
PRE_CADDY_GATES_COMPLETE=1
trap - EXIT
```

From a different machine or external network, a direct connection to the host
port must fail because `8502` is loopback-only:

```bash
set -Eeuo pipefail
: "${DELTA_HOST:?Set DELTA_HOST to the server public IP or DNS name}"
if curl --fail --show-error --max-time 5 \
  "http://${DELTA_HOST}:8502/_stcore/health"; then
  echo "P014_EXTERNAL_8502_REACHABLE" >&2
  exit 1
fi
```

Success from that external command is a rollout failure and requires the
pre-Caddy rollback below. No Caddy or DNS change is allowed in Phases 1 through
4.

## Phase 5: Obtain Separate Pre-Caddy Owner Authorization

Present the pre-Docker, post-Docker, Delta-idle, external-port denial, runtime
inspection, and Lemmata comparison evidence to Oğuz Koran. Record an explicit
proceed or stop decision. The ADR-0018 acceptance does not authorize the Caddy
edit, DNS change, or public route test.

## Phase 6: Add the Delta-Only TLS Route

First save a timestamped root-only copy and hash of the complete active Caddyfile.
Merge `Caddyfile.delta.example` into the observed host structure; do not replace
the existing file blindly and do not change the Lemmata site block.

The gateway keys its per-client request-rate and connection limits on
`X-Forwarded-For`. Caddy already ignores client-supplied `X-Forwarded-*` by
default because its `trusted_proxies` list is empty, so those limits are not
spoofable out of the box. As defense-in-depth, keep the example's
`header_up X-Forwarded-For {http.request.remote.host}` line in the merged live
`delta.lemmata.app` block so the edge pins that header to the real client
address explicitly, and avoid configuring a broad `trusted_proxies` that would
trust a client-supplied value.

```bash
set -Eeuo pipefail
set -a
. /etc/delta-public-alpha/deployment.env
set +a
RELEASE_ROOT="/opt/delta-public-alpha/releases/$DELTA_BUILD_ID"
[[ $(<"$RELEASE_ROOT/.p014-source-sha") == "$DELTA_BUILD_ID" ]]
cd "$RELEASE_ROOT"
test ! -e /etc/caddy/Caddyfile.pre-delta
test ! -e /etc/caddy/.Caddyfile.delta.p014
install -o root -g root -m 0600 \
  /etc/caddy/Caddyfile /etc/caddy/Caddyfile.pre-delta
sha256sum /etc/caddy/Caddyfile.pre-delta
! grep -Fq 'delta.lemmata.app {' /etc/caddy/Caddyfile
install -o root -g root -m 0644 \
  /etc/caddy/Caddyfile /etc/caddy/.Caddyfile.delta.p014
cat deploy/public-alpha/Caddyfile.delta.example >> /etc/caddy/.Caddyfile.delta.p014
caddy validate --config /etc/caddy/.Caddyfile.delta.p014
mv -f /etc/caddy/.Caddyfile.delta.p014 /etc/caddy/Caddyfile
```

Before reload:

```bash
set -Eeuo pipefail
caddy validate --config /etc/caddy/Caddyfile
curl --fail --silent --show-error https://lda.lemmata.app/_stcore/health
```

Use `systemctl reload caddy`, not a restart. Then require:

```bash
set -Eeuo pipefail
curl --fail --silent --show-error https://delta.lemmata.app/_stcore/health
curl --fail --silent --show-error https://lda.lemmata.app/_stcore/health
```

Wrong Host, body-size, security-header, WebSocket, XSRF/CORS, and separate
bounded rate-limit checks for static interface assets and dynamic requests must
pass through the public URL. The complete owner walkthrough then runs through
this same route.

## Phase 7: Coexistence and Load Gate

Freeze a Lemmata health and latency baseline before Delta load. During bounded
Delta load, sample both sites and both systemd units. Activation fails if:

- Lemmata restarts or reports any error;
- Delta escapes its CPU, RAM, PID, queue, worker, request, or connection limits;
- either site's health fails;
- Lemmata's measured p95 latency increase exceeds the frozen `20%` CE-15 budget;
- host available memory falls below `512 MiB`, idle post-start memory falls below
  `768 MiB`, memory-pressure `full avg10` reaches `1.00`, or any host/container
  OOM event occurs;
- runtime, logs, or exported records contain uploaded text or secret material.

Load evidence must record the tool, command, request count, concurrency, start/end
times, status distribution, latency distribution, CPU/RAM/PID peaks, image
identity, and source commit. A one-off manual refresh or a snapshot merely named
`under-load` is not load evidence.

The live gate below first freezes a new 20-request Lemmata baseline. It then
repeats a bounded, isolated synthetic stylo handoff through the real analysis
worker inside the application container without an idle gap until at least the
60-second observation window has elapsed. A four-worker, rate-bounded gateway
workload runs concurrently. Throughout the interval it samples Lemmata,
host memory pressure, container CPU/RAM/PIDs, configured limits, restart state,
OOM state, service errors, and the complete listener set. The fixture checksum,
analysis outcome, admission-slot use, worker use, and content cleanup are part of
the closed evidence record. This is a coexistence gate, not an
analysis-throughput benchmark or scientific validation:

```bash
set -Eeuo pipefail
set -a
. /etc/delta-public-alpha/deployment.env
set +a
RELEASE_ROOT="/opt/delta-public-alpha/releases/$DELTA_BUILD_ID"
[[ $(<"$RELEASE_ROOT/.p014-source-sha") == "$DELTA_BUILD_ID" ]]
cd "$RELEASE_ROOT"
COMPOSE=(
  docker compose --project-name delta-public-alpha
  --env-file /etc/delta-public-alpha/deployment.env
  --file "$RELEASE_ROOT/deploy/public-alpha/compose.yml"
)
APP_ID=$("${COMPOSE[@]}" ps --quiet app)
GATEWAY_ID=$("${COMPOSE[@]}" ps --quiet gateway)
[[ $APP_ID =~ ^[0-9a-f]{64}$ && $GATEWAY_ID =~ ^[0-9a-f]{64}$ ]]
python3 scripts/p014_load_gate.py \
  --host-baseline /root/p014-host-evidence/pre-docker.json \
  --app "$APP_ID" \
  --gateway "$GATEWAY_ID" \
  --output /root/p014-host-evidence/coexistence-load.json \
  --duration-seconds 60 \
  --concurrency 4 \
  --request-interval-seconds 0.2
```

## Rollback

### Pre-Caddy rollback

If the Phase 4 external denial or owner review fails after the automatic startup
trap has been disarmed, use this first-release rollback. It neither reads nor
requires a Caddy backup because no public route has been changed:

```bash
set -Eeuo pipefail
set -a
. /etc/delta-public-alpha/deployment.env
set +a
RELEASE_ROOT="/opt/delta-public-alpha/releases/$DELTA_BUILD_ID"
[[ $(<"$RELEASE_ROOT/.p014-source-sha") == "$DELTA_BUILD_ID" ]]
COMPOSE=(
  docker compose --project-name delta-public-alpha
  --env-file /etc/delta-public-alpha/deployment.env
  --file "$RELEASE_ROOT/deploy/public-alpha/compose.yml"
)
systemctl stop delta-public-alpha.service
systemctl disable delta-public-alpha.service
"${COMPOSE[@]}" down --remove-orphans --timeout 75
REMAINING_CONTAINERS=$("${COMPOSE[@]}" ps --quiet)
[[ -z $REMAINING_CONTAINERS ]]
REMAINING_LISTENERS=$(ss -H -ltn 'sport = :8502')
[[ -z $REMAINING_LISTENERS ]]
rm -f -- /etc/systemd/system/delta-public-alpha.service
systemctl daemon-reload
curl --fail --silent --show-error https://lda.lemmata.app/_stcore/health
```

The failed release, immutable image, deployment evidence, and content-free logs
remain available for diagnosis. They are not executed again without a new gate.

### Post-Caddy rollback

Rollback is prepared before public routing changes:

1. Keep the pre-change Caddyfile backup and its checksum.
2. Keep the previous Delta release directory and immutable image when one exists.
3. To remove public exposure, restore only the prior Caddyfile and validate it.
4. Reload Caddy and immediately prove Lemmata health.
5. Stop `delta-public-alpha.service` and verify port `8502` is closed.
6. On the first deployment, application rollback means removing the public
   route first, stopping Delta, removing only the Delta Compose project, and
   leaving no `8502` listener. For later releases, repoint `current` to the
   previous exact release, restore its deployment image reference, render that
   exact release path into the installed unit, and start Delta again only after
   image-identity and Compose validation.
7. Retain the failed rollout record, container status, and content-free logs.

The route-first rollback is exact and never edits the Lemmata block:

```bash
set -Eeuo pipefail
set -a
. /etc/delta-public-alpha/deployment.env
set +a
RELEASE_ROOT="/opt/delta-public-alpha/releases/$DELTA_BUILD_ID"
[[ $(<"$RELEASE_ROOT/.p014-source-sha") == "$DELTA_BUILD_ID" ]]
cd "$RELEASE_ROOT"
COMPOSE=(
  docker compose --project-name delta-public-alpha
  --env-file /etc/delta-public-alpha/deployment.env
  --file "$RELEASE_ROOT/deploy/public-alpha/compose.yml"
)
install -o root -g root -m 0644 \
  /etc/caddy/Caddyfile.pre-delta /etc/caddy/.Caddyfile.rollback.p014
caddy validate --config /etc/caddy/.Caddyfile.rollback.p014
mv -f /etc/caddy/.Caddyfile.rollback.p014 /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
curl --fail --silent --show-error https://lda.lemmata.app/_stcore/health
systemctl stop delta-public-alpha.service
systemctl disable delta-public-alpha.service
"${COMPOSE[@]}" down --remove-orphans --timeout 75
REMAINING_CONTAINERS=$("${COMPOSE[@]}" ps --quiet)
[[ -z $REMAINING_CONTAINERS ]]
rm -f -- /etc/systemd/system/delta-public-alpha.service
systemctl daemon-reload
REMAINING_LISTENERS=$(ss -H -ltn 'sport = :8502')
[[ -z $REMAINING_LISTENERS ]]
```

If Docker installation itself fails before any Delta image is pulled, run the
same guarded rollback explicitly if automatic rollback did not complete. It
will refuse a successful/disarmed installation or any transaction containing an
image or container. Use a new output path for each retry:

```bash
set -Eeuo pipefail
scripts/p014_rollback_docker_ubuntu.sh \
  --state-dir /root/p014-host-evidence/docker-change \
  --output /root/p014-host-evidence/post-rollback-manual.json \
  --apply
```

Rollback succeeds only when Lemmata remains healthy throughout, Delta has no
orphan container/network, the intended route state is restored, and the evidence
record identifies every command and artifact digest.

## Activation Decision

The site is activated only after Oğuz Koran reviews:

- exact CI and image evidence;
- host inventory and pre-change baseline;
- isolation and runtime inspection;
- public TLS/Host/header/WebSocket checks;
- owner walkthrough;
- load and simultaneous Lemmata smoke results;
- restart/cleanup and rollback transcript;
- the visible `Public alpha` and `Experimental` claim boundary.

Acceptance authorizes the bounded public alpha only. Full P014, CE-14, CE-15,
scientific validation, FAIR certification, general usability, and publication
readiness remain open.
