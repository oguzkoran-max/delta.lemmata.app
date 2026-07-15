# P014 Canonical Public-Alpha Stack Validation

## Scope

This record validates the versioned minimum public-alpha deployment package at
exact source commit `7f26dbe82437e7f9757e7c35b10b7666a3078578`. It proves the
package and its runtime controls in canonical GitHub-hosted Linux CI. It does
not prove the shared VPS, the live TLS route, Delta-Lemmata coexistence under
load, host restart cleanup, rollback, or Oğuz Koran's owner acceptance.

The full P014 ticket therefore remains `in-progress`. Only P014-AC-01 through
P014-AC-07 are supported by this record. P014-AC-08 through P014-AC-10 remain
pending and public activation remains prohibited.

## Implemented Boundary

- A real Streamlit application image runs as numeric UID/GID `10001:10001`,
  exposes a public-safe health endpoint, uses a read-only root filesystem, and
  receives three independently generated runtime secrets only through a
  private environment file.
- The application has no host port and joins only a private internal Docker
  network. Its production topology has no default-route egress.
- A separate unprivileged Nginx gateway runs as UID/GID `101:101`, publishes
  only `127.0.0.1:8502`, and joins a distinct edge bridge plus the private
  backend network.
- Application and gateway writable paths are private, size-bounded `tmpfs`
  mounts. Both services drop all capabilities, enable `no-new-privileges`, use
  finite CPU, memory, PID, file-descriptor, timeout, restart, health, and log
  limits, and retain no permanent corpus volume.
- The gateway rejects an unrecognised Host, retains Streamlit WebSocket
  upgrades, preserves the validated public authority, pins the external scheme
  to HTTPS, limits request size and connections, applies separate bounded
  budgets to dynamic requests and static interface assets, and emits the
  declared security headers.
- The interface exposes `Public alpha` and `experimental` labels at desktop,
  mobile, and 320-pixel reflow without changing the existing scientific and
  interpretation boundaries.
- The deployment runbook separates read-only host inventory, immutable image
  publication, installation, Delta-only TLS routing, coexistence/load testing,
  rollback, and human activation acceptance.

## Passing Evidence

GitHub Actions run `29420509541` passed on Ubuntu 24.04 x86_64 at the exact
source commit. The verify job was `87369452370`; the container job was
`87369452318`.

### Source, scientific, and browser gate

- 1,564 Linux tests passed with no skips.
- All 11,382 measured statements and 2,964 branches were covered.
- Formatting, lint, strict typing, generated schemas, 103 provenance records,
  metadata, repository, R-lock, SBOM, dependency, and secret gates passed.
- R 4.5.2 and locked `stylo` 0.7.71 executed the real synthetic
  upload-to-public-result workflow.
- All four declared MFW cells completed; semantic result tables and two
  nonblank charts passed; the result-only export SHA-256 was
  `9a16b87e465e29b1f870d05f4ebf4d24336392c251a42e4b034b0448f7bf5320`.
- Desktop 1280x900, mobile 390x844, and reflow 320x800 had no page or main
  horizontal overflow, overflowing controls, or misframed table regions.
- No unexpected console message or external browser host was observed. The
  package audit reported no known Python dependency vulnerability at the time
  of the run.

### Hardened stack gate

- The canonical Linux amd64 application build produced content-addressed image
  ID `sha256:f96fbd196c1e71b86a3dde8254f70fca3c2ff3d69306a4f6e02be73cb69a9934`.
- The pinned gateway manifest was
  `nginxinc/nginx-unprivileged:1.30.3-alpine-slim@sha256:3b24c4bfb2b9f60359b1475605ca1c8ed6e4963eb8369c6835be4d96bdb3ea81`;
  its running Linux image ID was
  `sha256:acffd179eaca40d7d73dc928ed314730fc7110a2f34c03f295245c344c90d037`.
- Package validation, stack health, hostile-request smoke checks, runtime
  inspection, denied application egress, and cleanup produced
  `p014-deployment-package-ok`, `p014-runtime-inspection-ok`,
  `p014-stack-smoke-ok`, and `p014-runtime-gate-ok`.
- The TLS browser audit received 79 successful responses and no blocked or
  failed request. The page reached `complete`, rendered 3,460 text characters,
  opened exactly one successful WebSocket, and produced no console or page
  error.
- The public Host remained exactly `delta.lemmata.app` for HTTP and WebSocket
  traffic. Desktop 1280x900, mobile 390x844, and reflow 320x720 displayed both
  release labels without horizontal overflow, and the release label remained
  inside each viewport.
- Stack shutdown removed both containers and both temporary networks. No corpus
  volume existed. Runtime secret values and uploaded text were never printed to
  the retained log.

BuildKit emitted one non-fatal warning because the Dockerfile explicitly pins
the canonical `linux/amd64` base platform. The image built and all runtime gates
passed; this warning is retained rather than omitted.

Run URL:
<https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29420509541>

## Retained Attempts

The earlier CI outcomes remain part of the development record:

1. `29408010407`, commit `444a4f7`: source verification correctly rejected one
   unformatted Python file.
2. `29408987359`, commit `166c530`: cancelled by branch concurrency after a
   correcting commit superseded it.
3. `29410308415`, commit `c90de6d`: cancelled by branch concurrency after a
   correcting commit superseded it.
4. `29411048388`, commit `faaa5bd`: the application became healthy, but the
   read-only gateway could not create its Nginx temporary cache paths.
5. `29411625601`, commit `95bb878`: retained diagnostics identified the missing
   gateway cache mount; the parallel verify job also encountered a transient
   pandas/Arrow segmentation fault.
6. `29412290649`, commit `188d49b`: the gateway became healthy, but runtime
   inspection rejected an incomplete expected application mount set; the
   parallel verify job repeated the pandas/Arrow segmentation fault.
7. `29413333714`, commit `49001d8`: source verification passed and both services
   were healthy, but the configured loopback port was not published.
8. `29414242074`, commit `dacf38f`: diagnostics proved the Docker `PORTS` field
   was empty because the sole internal network suppressed publication.
9. `29415155636`, commit `10c4363`: runtime inspection and smoke checks passed;
   Chromium upgraded the `.app` audit URL to HTTPS while the test bridge still
   served plain HTTP, causing a TLS protocol failure.
10. `29417081945`, commit `c63bc3f`: ephemeral TLS worked, but the single request
    budget counted normal Streamlit static assets as attack traffic and returned
    HTTP 429 during application boot.
11. `29418542119`, commit `8f692f3`: content-free browser diagnostics confirmed
    a successful entry response and one static-asset HTTP 429, a blank body,
    and no WebSocket.
12. `29419546551`, commit `6f55609`: all assets returned HTTP 200, but the gateway
    removed the non-default test port and forwarded an incorrect external
    scheme, producing reconnecting WebSockets and a blank application.
13. `29420509541`, commit `7f26dbe`: preserving the validated public authority
    and pinning external HTTPS resolved the remaining origin/WebSocket mismatch;
    both CI jobs passed.

No corpus, scientific parameter, Delta calculation, distance matrix, chart
value, or interpretation threshold was altered to obtain the passing run.

## Acceptance Mapping

- P014-AC-01: supported by canonical image build, non-root runtime inspection,
  source/image labels, health, and secret scans.
- P014-AC-02: supported by static package validation and exact runtime topology
  inspection; real-host distinctness is separately reserved for P014-AC-08.
- P014-AC-03: supported by gateway configuration validation, hostile-request
  smoke checks, TLS browser audit, and one successful Streamlit WebSocket.
- P014-AC-04: supported by runtime inspection of filesystem, mounts,
  capabilities, security options, resources, and production network topology.
- P014-AC-05: supported by existing application limit, saturation, timeout,
  cancellation, janitor, cleanup, leakage, and deployment-profile test suites.
- P014-AC-06: supported by release-label assertions at all three gateway
  viewports and the existing claim-lint/browser gates.
- P014-AC-07: supported by the exact canonical Linux stack run and its retained
  content-free log.
- P014-AC-08, P014-AC-09, and P014-AC-10: not tested by this run and remain
  pending.

## Claim Boundary

This evidence supports a CI-validated candidate public-alpha deployment package.
It does not establish that Delta is publicly deployed, that the shared VPS has
sufficient headroom, that Lemmata is unaffected under concurrent load, that
rollback works on the host, or that the owner accepts activation. It also does
not establish complete isolation, production maturity, benchmark accuracy,
FAIR certification, general usability, teachability, reproducibility,
publication readiness, or a literary finding.
