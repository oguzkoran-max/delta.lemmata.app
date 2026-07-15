# ADR-0018: Shared-VPS Runtime and Capacity Candidate

**Status:** Proposed; explicit Oğuz Koran approval is required before any host
modification

**Date:** 2026-07-15

**Scope:** Container runtime, host memory policy, network side effects, and
fail-closed capacity gates for the minimum Delta public alpha

## Context

The exact green Delta image is available from private GHCR by immutable digest,
but the intended shared VPS has no container runtime. The read-only target-host
observations found Ubuntu 26.04 on x86_64, two CPUs, 3,814 MiB total memory,
2,357 MiB available memory, no swap, and 32,621 MiB free root disk. Lemmata was
healthy, used 1,118,232,576 bytes, had zero recorded restarts, and had no finite
CPU or memory cap. Port `8502` was free.

The frozen Delta profile permits 1,536 MiB for the application and 128 MiB for
the gateway. If both reached their limits at the observed instant, only about
693 MiB of the observed available memory would remain for host variation and
container-runtime overhead. Disk is not the limiting resource; memory headroom
and shared-host effects are.

Docker's official Ubuntu instructions list Ubuntu 26.04 LTS and x86_64 as
supported. Docker also documents that Linux bridge networking creates firewall
rules and may enable IP forwarding. The observed host currently has no nftables,
iptables, or ip6tables rules, UFW reports `inactive`, and both IPv4 and IPv6
forwarding are disabled. Runtime installation therefore changes observable host
network state even before Delta starts.

## Candidate Decision

Subject to explicit owner approval, use the current VPS for the bounded alpha
with the following profile:

1. Install the stable official Docker Engine and Compose plugin from Docker's
   signed Ubuntu apt repository. Record exact package versions, repository/key
   hashes, daemon version, Compose version, and service state.
2. Keep Lemmata's source, unit, environment, process, port, and Caddy block
   unchanged. Docker installation is followed immediately by Lemmata health,
   restart-count, latency, socket, and Caddy checks before any Delta artifact is
   installed.
3. Do not create disk-backed swap for the alpha. Keep Delta's
   `memswap_limit == mem_limit` controls, so neither Delta container can use
   host swap even if host policy changes later.
4. Pull only the private immutable Delta manifest with a dedicated classic
   GitHub token limited to `read:packages`. Supply it through standard input,
   log out after the pull, and retain no token value or Docker credential file
   in evidence.
5. Bind the Delta gateway only to `127.0.0.1:8502`. No Caddy or DNS change is
   allowed until local health, hostile-request, resource, egress, cleanup, and
   direct-external-port probes pass.
6. Apply the existing exact resource profile: one application replica, one
   running and three queued jobs, application `1.50` CPU and `1536 MiB`, gateway
   `0.25` CPU and `128 MiB`, and the existing worker limits.

This is an installation candidate, not an accepted capacity claim. The same VPS
is accepted only if every gate below passes on the exact image.

## Frozen Host Gates

### Before Docker Installation

- Lemmata and Caddy are active; Lemmata health is `ok` and port `8502` is free.
- Available memory is at least `2,048 MiB`; root disk has at least `10 GiB` free.
- Lemmata restart count, memory, start time, and the Caddyfile hash are captured.
- Firewall rules, forwarding sysctls, listening sockets, package inventory, and
  memory-pressure counters are captured without configuration contents.
- A paired Lemmata latency baseline is collected immediately before the change.

### Immediately After Docker Starts

- Lemmata restart count and start time are unchanged; health remains `ok` for
  every sample and Caddy remains active.
- The paired Lemmata p95 latency increase is no more than the frozen `20%`
  project limit from CE-15.
- No unexpected public listening socket exists. Docker's firewall and forwarding
  differences are recorded and direct external probes of unpublished and
  loopback-published ports fail closed.
- Available memory remains at least `1,800 MiB` before Delta is started.

### Delta Idle and Maximum Accepted Load

- After Delta reaches healthy idle state, available host memory remains at least
  `768 MiB`; during the accepted load it never falls below `512 MiB`.
- Host `memory` pressure `full avg10` remains below `1.00`; no kernel OOM event,
  container OOM event, or PID-limit breach occurs.
- Lemmata has zero restart, zero health failure, and zero observed service error.
- During the bounded maximum Delta load, Lemmata p95 latency increases by no
  more than `20%` against the paired pre-load baseline.
- Delta remains within its CPU, memory, PID, queue, request, and worker limits;
  both sites pass contemporaneous smoke checks.

Any failed gate stops Delta, leaves the public Delta route absent or removes it,
and preserves the failed evidence. A date or idle-memory snapshot cannot waive a
failed capacity gate.

## Why No New Swap

A plain disk swapfile could retain memory pages beyond an application request and
would expand the storage/erasure boundary for both services. Encrypted ephemeral
swap or compressed RAM swap would add another untested host subsystem during an
accelerated release. Delta is already hard-limited and explicitly denied swap.

The candidate therefore makes no new disk-backed retention surface. If the
measured no-swap gates fail, the response is not to weaken container limits or
silently add swap. Delta stops and the next option is a memory upgrade or a
separate VPS.

## Network Change Boundary

Docker is allowed to create the documented bridge-network firewall rules needed
by the tested Compose topology. Disabling Docker firewall management is rejected
because Docker documents that this commonly breaks bridge networking. Before and
after hashes/counts, forwarding values, listening sockets, and external probes
must be retained.

Only `127.0.0.1:8502` may be published. The application has no host bind and
remains on an internal network without a default route. The existing Caddy route
for Lemmata is not edited during runtime installation.

## Rollback Boundary

If Docker installation alone affects Lemmata, stop before pulling Delta. Record
the failure, stop Docker, restore the observed forwarding values when safe,
remove only the newly installed Docker packages/repository/key if required, and
prove Lemmata health and socket state again. Do not restart or edit Lemmata as a
workaround.

If Delta fails before public routing, stop and remove only the Delta Compose
project, service, networks, release, and private environment files. If public
routing has begun, use the existing Caddy backup-and-reload rollback first, then
remove Delta. Every rollback must show that Lemmata remained healthy.

## Alternatives

### Separate VPS

Operationally safest because the kernel and memory are not shared, but it adds
monthly cost and is not the owner's preferred first attempt. It becomes the
default fallback if any shared-host gate fails.

### Increase the Existing VPS Memory

Preferable to adding unencrypted swap if the provider can resize with an
accepted maintenance window and rollback. It still shares one kernel and must
repeat all host gates.

### Native systemd Delta Runtime

Rejected for the accelerated alpha because it would depart from the canonically
tested image, egress topology, filesystem boundary, and rollback package.

### Rootless Docker

Rejected for this release because the tested systemd, cgroup, network, and
resource-inspection evidence targets the rootful Engine profile. Changing the
runtime mode would require a separate implementation and acceptance cycle.

### Plain or Persistent Swap

Rejected for the initial alpha because it expands retention risk and does not
replace measured capacity evidence.

## Approval Boundary

This ADR remains `Proposed` until Oğuz Koran explicitly accepts or rejects the
same-VPS, official-Docker, no-new-swap candidate. Approval authorizes only the
ordered host-preparation and measurement gates. It does not authorize Caddy,
DNS, public activation, or a claim that the two services are completely
isolated.

## Sources

- `provenance/evidence/P014/target-host-read-only-preflight.md`
- `provenance/evidence/P014/target-host-runtime-capacity-observation.md`
- `provenance/evidence/P014/immutable-image-publication.md`
- `deploy/public-alpha/compose.yml`
- `docs/research/claim-evidence-matrix.md`
- <https://docs.docker.com/engine/install/ubuntu/>
- <https://docs.docker.com/engine/network/packet-filtering-firewalls/>
- <https://docs.docker.com/reference/compose-file/services/#memswap_limit>
- <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>
