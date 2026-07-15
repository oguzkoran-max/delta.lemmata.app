# ADR-0017: Public-Alpha Deployment Profile

**Status:** Proposed; local implementation authorized by `HD-20260714-0002`,
real-host cutover requires the P014 owner gate

**Date:** 2026-07-15

**Scope:** Minimum P014 public-alpha deployment package on the shared Lemmata VPS

## Context

ADR-0015 permits a bounded public alpha before the complete P010-P015 scientific
release sequence, but only after a minimum P014 security slice passes. Delta and
`lda.lemmata.app` may share the same VPS while remaining separate services. They
still share a kernel and physical host, so this design cannot support a claim of
complete isolation.

The current canonical image verifies the scientific environment but exits after
printing the package version. It has no production command or health check. The
repository also lacks a target deployment definition, strict gateway policy,
secret-generation procedure, rollback package, and executable two-site smoke
gate. Those are prerequisites for a controlled cutover.

## Decision

The minimum public-alpha profile uses three layers:

1. Host Caddy continues to own public TLS. A future Delta route accepts only
   `delta.lemmata.app` and proxies to host loopback port `8502`.
2. A Delta-only unprivileged gateway binds `127.0.0.1:8502`, enforces strict Host,
   request/rate/connection/time limits and security headers, and proxies only to
   the private application network.
3. The Delta application runs the digest-identified canonical image as fixed UID
   and GID `10001`, with a read-only root filesystem, dropped capabilities,
   no-new-privileges, private tmpfs runtime, no host project bind mount, three
   distinct secrets, and explicit CPU/RAM/PID/concurrency limits.

The gateway and application use a Delta-only internal network. The application
has no default-route egress in the production profile. The gateway has only the
network access required to receive loopback traffic and reach the application.
No Lemmata directory, socket, environment, volume, network, secret, or service is
mounted or referenced.

The production application retains Streamlit XSRF and CORS protections. Public
traffic cannot bind directly to Streamlit. Runtime state is temporary and lives
only in size-bounded tmpfs paths; durable deployment files contain no uploaded
text. Application queue, token, file, timeout, and concurrency limits remain
enforced in addition to gateway and container limits.

## Resource Profile

The initial candidate profile is intentionally small and must be revised only
from measured evidence:

- one application replica;
- at most one running public analysis and three queued jobs;
- application CPU limit `1.50`, memory limit `1536 MiB`, PID limit `128`;
- gateway CPU limit `0.25`, memory limit `128 MiB`, PID limit `64`;
- request body ceiling `26 MiB`, slightly above the application's `25 MiB`
  single-upload ceiling to permit protocol overhead;
- bounded request, response, idle, and WebSocket connection behavior;
- worker wall-clock `60 s`, CPU `30 s`, memory `1 GiB`, process limit `8` as
  already enforced by the scientific boundary.

These are candidate deployment limits, not proven capacity. Real load evidence
must show that Delta stays inside them and that Lemmata does not restart, error,
or exceed the predeclared latency budget.

## Activation Sequence

1. Build and validate the exact image in CI.
2. Record an immutable image digest and source commit.
3. Run read-only host inventory and capture the existing Lemmata baseline.
4. Install Delta under separate paths and service identity without changing the
   active Lemmata unit or environment.
5. Start Delta behind loopback, run health and hostile Host/request checks, then
   run the complete owner walkthrough locally through the gateway.
6. Add and validate only the Delta Caddy route, obtain TLS, and run both-site
   smoke checks.
7. Apply bounded load while monitoring both services.
8. Exercise rollback and prove that Lemmata remains available.
9. Activate only after Oğuz accepts the recorded minimum gate.

## Consequences

- Local artifacts can be implemented and tested without touching the live host.
- Host Caddy remains a shared dependency, but the new route is narrow and
  independently removable.
- A Delta-only gateway adds one component but avoids changing the existing Caddy
  binary or weakening Lemmata's current service.
- Production secrets are generated on the host and never enter Git, images,
  logs, screenshots, or provenance records.
- Public-alpha activation does not close full P014 or establish CE-14/CE-15.
- If gateway image pinning, host resources, or coexistence evidence cannot be
  made deterministic, activation stops instead of degrading the boundary.

## Alternatives Rejected

### Run Streamlit Directly on a Public Port

Rejected because it cannot independently provide the required strict Host,
request-size, rate, connection, timeout, and security-header boundary.

### Reuse the Lemmata Service, Environment, or Port

Rejected because a shared process identity or runtime would make failure,
rollback, secrets, and resource accounting inseparable.

### Modify the Existing Caddy Build to Add Rate-Limit Plugins

Rejected for the minimum alpha because rebuilding the shared TLS proxy would add
unnecessary risk to `lda.lemmata.app`. Delta receives its own gateway instead.

### Claim Full Isolation from Containers Alone

Rejected because both applications still share one VPS kernel and host resources.

## Evidence Required Before Acceptance

- Local deployment validator and canonical CI runtime inspection
- Immutable image digest and SBOM link
- Read-only host inventory and Lemmata baseline
- Strict Host, TLS, headers, request-size, rate and WebSocket checks
- Egress denial, read-only filesystem and resource-limit checks
- Delta health, owner walkthrough and content-free runtime scan
- Delta load with contemporaneous Lemmata smoke/latency/error evidence
- Restart, cleanup and rollback transcript
- Oğuz's explicit P014 activation decision

## Related Records

- `decisions/ADR-0015-accelerated-public-alpha.md`
- `docs/development/p014-public-alpha-deployment-contract.md`
- `docs/security/threat-model.md`
- `docs/research/claim-evidence-matrix.md`
- `provenance/tickets/P014.json`
