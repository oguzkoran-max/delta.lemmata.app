# P014 Minimum Public-Alpha Deployment Contract

## Purpose

This contract separates three different facts:

1. the deployment package is defined in version control;
2. its runtime controls pass canonical local and Linux CI tests;
3. the exact package passes measured shared-VPS deployment, coexistence, and
   rollback tests.

Only the third fact can authorize public activation. None of the three facts
alone closes full P014, CE-14, or CE-15.

## Service Topology

```text
Internet
  -> existing host Caddy (TLS; strict delta.lemmata.app route)
  -> 127.0.0.1:8502 (Delta-only unprivileged gateway)
  -> private Delta network
  -> Delta Streamlit application:8501
  -> local R stylo worker process under existing bounded worker controls
```

The deployment must not reference the Lemmata application path, systemd unit,
environment, volume, secret, network, or internal port. The only shared runtime
components are the VPS kernel, host resources, and existing public TLS proxy.

## Fixed Public-Alpha Limits

| Layer | Control | Candidate value |
|---|---|---|
| Gateway | Host | exact `delta.lemmata.app` only |
| Gateway | request body | `26 MiB` |
| Gateway | request rate | bounded per client with a small burst |
| Gateway | concurrent connections | bounded per client |
| Gateway | upstream connect/read/send | explicit finite timeouts |
| Application | public bind | none; private network only |
| Application | direct host bind | none |
| Application | replicas | `1` |
| Application | CPU | `1.50` |
| Application | RAM | `1536 MiB` |
| Application | PIDs | `128` |
| Application | running/queued jobs | `1 / 3` |
| Application | upload | application ceiling `25 MiB` |
| Worker | wall/CPU/RAM/process | `60 s / 30 s / 1 GiB / 8` |
| Storage | runtime/work/export | private size-bounded tmpfs only |
| Storage | root filesystem | read-only |
| Network | application egress | denied by deployment topology |

Candidate values become accepted limits only after exact CI and host evidence.

## Secret Contract

Production requires three independent 256-bit hexadecimal values:

- `DELTA_JOB_OWNER_SECRET_HEX`
- `DELTA_PREPARATION_AUTHORITY_SECRET_HEX`
- `DELTA_RECOVERY_RECEIPT_SECRET_HEX`

They are generated on the target host, stored in a root-readable Delta-only
environment file, and checked for syntax, length, uniqueness, ownership, and
mode before startup. Templates contain names and instructions only. A value must
never be committed, baked into an image, copied from Lemmata, or printed by a
test or runbook.

## Local Acceptance

- The deployment definition parses and contains the expected isolated services,
  networks, mounts, limits, labels, health checks, and loopback-only binding.
- The application image runs as numeric UID/GID `10001`, starts Streamlit rather
  than a diagnostic command, returns public-safe health, and has no embedded
  production secret.
- The gateway rejects an incorrect Host, enforces request/rate/timeout policy,
  supplies security headers, and preserves Streamlit WebSocket upgrade headers.
- The application cannot create files outside declared tmpfs paths and cannot
  reach an external canary endpoint in the production topology.
- CI starts the exact stack, waits for health, tests hostile and valid requests,
  inspects runtime controls, and stops the stack without retained corpus data.
- The English interface visibly and accessibly labels the product `Public alpha`
  and `experimental` on every stage.

## Real-Host Acceptance

- Read-only inventory confirms the documented current Lemmata service, port,
  directories, proxy route, resources, and baseline health before Delta install.
- Every Delta path, service, environment, secret, port, network, and runtime
  identity is distinct.
- TLS, strict Host, headers, request-size, rate, timeout, CORS/XSRF, WebSocket,
  egress, filesystem, health, cleanup and restart checks pass on the exact image.
- Maximum accepted Delta load causes zero Lemmata restart and zero Lemmata error;
  measured p95 latency change stays within the frozen project budget.
- Rollback removes or disables only Delta artifacts and restores the previous
  routing state without Lemmata interruption.
- The complete Oğuz owner walkthrough passes through the deployed gateway.

## Claim Boundary

Passing this minimum contract permits only:

> Delta is available as an experimental public alpha under the recorded bounded
> configuration.

It does not permit claims of complete isolation, production maturity, scientific
validation, benchmark accuracy, FAIR certification, general usability,
teachability, reproducibility, publication readiness, or a literary finding.
