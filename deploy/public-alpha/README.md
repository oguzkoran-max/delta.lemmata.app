# Delta Public-Alpha Deployment Runbook

This runbook is executable only after the exact source commit passes canonical
CI. It must be followed in order. A failed step stops the rollout; the next step
is not used to work around it.

## What This Package Does

- Keeps the existing host Caddy service as the public TLS boundary.
- Binds the Delta-only gateway to `127.0.0.1:8502`.
- Runs Streamlit only on a private container network.
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

## Phase 1: Read-Only Host Inventory

Do not install, restart, reload, stop, or edit anything in this phase. Record:

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
uname -a
cat /etc/os-release
nproc
free -m
df -h / /var/lib/docker
docker version
docker compose version
systemctl is-active docker caddy lemmata
systemctl show lemmata --property=ActiveState,SubState,MainPID,MemoryCurrent,CPUUsageNSec,ExecMainStartTimestamp
ss -H -ltn 'sport = :8501 or sport = :8502'
sha256sum /etc/caddy/Caddyfile
curl --fail --silent --show-error https://lda.lemmata.app/_stcore/health
```

Never run `systemctl show-environment`, print an environment file, dump a Docker
container environment, or capture a process command line that may contain a
secret. The inventory is rejected if Lemmata is not healthy, port `8502` is in
use, disk/memory headroom is insufficient, or the documented topology differs
from the observed host.

## Phase 1.5: Publish the Exact Application Image

Do not build Delta on the shared VPS. After the exact source commit's normal CI
run is green, manually dispatch `.github/workflows/p014-publish-image.yml` with
that full commit as `source_sha`. The workflow checks that prerequisite run,
rebuilds the same Linux amd64 profile, repeats the hardened stack and browser
gates, and publishes only `sha-<commit>` to GHCR. It does not publish `latest`.

Record the workflow run, job, source commit, local image ID, and returned
`repository@sha256:...` reference. Deployment uses the digest reference, not the
commit tag. A publication failure stops the rollout and remains in the P014
history.

## Phase 2: Install an Immutable Release

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

The real `deployment.env` must contain:

```text
DELTA_IMAGE=<registry/repository@sha256:immutable-manifest-digest>
DELTA_BUILD_ID=<the-same-40-character-source-commit>
DELTA_RUNTIME_ENV_FILE=/etc/delta-public-alpha/runtime.env
```

Pull the exact digest before systemd starts. For a private registry, use a
least-privilege, read-only package credential, then log out after the pull; never
put registry credentials in either Delta environment file:

```bash
set -a
. /etc/delta-public-alpha/deployment.env
set +a
docker pull "$DELTA_IMAGE"
docker image inspect "$DELTA_IMAGE" --format '{{.Id}}'
```

Record only the image reference and resulting image ID. Do not record the
credential, Docker config, or environment-file contents.

Create the private secret directory and file without printing the values:

```bash
install -d -o root -g root -m 0700 /etc/delta-public-alpha
python3 scripts/generate_p014_secrets.py --output /etc/delta-public-alpha/runtime.env
chown root:root /etc/delta-public-alpha/runtime.env
chmod 0600 /etc/delta-public-alpha/runtime.env
```

Validate the release and compose expansion before startup:

```bash
python3 scripts/validate_p014_deployment.py
docker compose --project-name delta-public-alpha \
  --env-file /etc/delta-public-alpha/deployment.env \
  --file deploy/public-alpha/compose.yml config --quiet
```

Install the versioned unit, reload systemd, and start only Delta:

```bash
install -o root -g root -m 0644 \
  deploy/public-alpha/delta-public-alpha.service \
  /etc/systemd/system/delta-public-alpha.service
systemctl daemon-reload
systemctl enable --now delta-public-alpha.service
```

At this point only `127.0.0.1:8502` may answer. Run the stack smoke and runtime
inspection before changing Caddy:

```bash
scripts/smoke_p014_stack.sh
docker compose --project-name delta-public-alpha \
  --env-file /etc/delta-public-alpha/deployment.env \
  --file deploy/public-alpha/compose.yml ps
```

## Phase 3: Add the Delta-Only TLS Route

First save a timestamped root-only copy and hash of the complete active Caddyfile.
Merge `Caddyfile.delta.example` into the observed host structure; do not replace
the existing file blindly and do not change the Lemmata site block.

Before reload:

```bash
caddy validate --config /etc/caddy/Caddyfile
curl --fail --silent --show-error https://lda.lemmata.app/_stcore/health
```

Use `systemctl reload caddy`, not a restart. Then require:

```bash
curl --fail --silent --show-error https://delta.lemmata.app/_stcore/health
curl --fail --silent --show-error https://lda.lemmata.app/_stcore/health
```

Wrong Host, body-size, security-header, WebSocket, XSRF/CORS, and rate-limit
checks must pass through the public URL. The complete owner walkthrough then runs
through this same route.

## Phase 4: Coexistence and Load Gate

Freeze a Lemmata health and latency baseline before Delta load. During bounded
Delta load, sample both sites and both systemd units. Activation fails if:

- Lemmata restarts or reports any error;
- Delta escapes its CPU, RAM, PID, queue, worker, request, or connection limits;
- either site's health fails;
- Lemmata's measured p95 latency change exceeds the frozen project budget;
- runtime, logs, or exported records contain uploaded text or secret material.

Load evidence must record the tool, command, request count, concurrency, start/end
times, status distribution, latency distribution, CPU/RAM/PID peaks, image
digest, and source commit. A one-off manual refresh is not load evidence.

## Rollback

Rollback is prepared before public routing changes:

1. Keep the pre-change Caddyfile backup and its checksum.
2. Keep the previous Delta release directory and immutable image.
3. To remove public exposure, restore only the prior Caddyfile and validate it.
4. Reload Caddy and immediately prove Lemmata health.
5. Stop `delta-public-alpha.service` and verify port `8502` is closed.
6. For an application-only rollback, repoint `current` to the previous exact
   release, restore its deployment image reference, and start Delta again only
   after compose validation.
7. Retain the failed rollout record, container status, and content-free logs.

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
