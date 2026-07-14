# P006 Fixed Worker, Parity, and Scientific Handoff Evidence

**Date:** 2026-07-14

**Branch:** `codex/p006-stylo-worker`

**Implementation commit:** `f0800c82d7033da2790abc69bc8adfe48570fcb1`

**CI run:** `29308457480`

**Run URL:**
`https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29308457480`

## Scope

This checkpoint connects the fixed R/stylo worker to the P005 lifecycle, compares
the worker against the checksum-frozen adversarial oracle-v2 fixtures, and binds a
validated result to SQLite and the guardian protocol. It does not activate the
public analysis workflow or retain the complete P006 worker evidence package.

## Implemented Boundary

- `StyloWorkerAdapter` uses the fixed trusted `Rscript --vanilla` command, the
  `R_STYLO` environment profile, opaque workspace components, bounded private
  reads, and no user-controlled command, environment name, or filesystem path.
- The fixed worker consumes only the versioned whole-text contract. Scientific
  validation rejects absent, malformed, non-finite, structurally inconsistent,
  mislabeled, duplicate, or cardinality-invalid output before lifecycle success.
- `StyloJobRunner` first persists a single scientific execution claim. A stale
  RUNNING snapshot therefore loses its compare-and-swap before adapter, guardian,
  filesystem, or R side effects can repeat.
- A successful result is published byte-for-byte to the result area and committed
  with its schema, request digest, size, and SHA-256. The terminal transition is
  durable before the guardian receives the exact outcome and result commitment.
- The guardian writes a signed acceptance or recovery receipt. The application
  confirms the result only after validating that exact receipt. Startup recovery
  distinguishes accepted, recovery-required, and unresolved evidence.
- Terminal proof uses the immutable operation version that created the terminal
  state. Janitor cleanup may advance the current row without invalidating a valid
  guardian acknowledgement. Result confirmation reads and updates the current row
  in one SQLite immediate transaction.
- Pending unresolved scientific results never open export. Input and work areas
  are still cleaned, while the result remains locked until its one-hour deadline.

## Method and Security Validation

The Linux parity gate executes the three predeclared oracle-v2 requests plus an
injection canary through the fixed worker. It verifies:

- exact ordered feature inventories and fitting structure;
- means and standard deviations within the `1e-12` structural tolerance;
- all distance matrices within the accepted `1e-6` tolerance;
- exact nearest-neighbor tie groups at `1e-12`;
- exact fitting artifacts and known-known distances after both unknown documents
  change;
- document-order equivariance by opaque document identity;
- an active changed-unknown canary for Classic, Eder's, and Cosine Delta;
- no observed shell or R-code execution from the injection feature.

The real Linux handoff gate additionally executes the R worker through
`StyloJobRunner`, verifies the retained result bytes against the committed digest
and size, verifies the exact scientific terminal and confirmation operations, and
checks the signed guardian acceptance receipt.

## Independent Adversarial Review

Read-only review rounds challenged stale-snapshot replay, unsigned recovery input,
generic success after a scientific claim, unresolved-result retention, mutable
terminal versions, and janitor/guardian ordering. Each blocking finding received a
focused regression. The final review returned `PASS`, with no open P0 or P1.

The review also confirmed that a RUNNING record without signed process or guardian
proof remains the explicit P005 unresolved-recovery boundary. P006 does not infer
process death from elapsed time and does not weaken that fail-closed rule.

## Local Quality Gate

`./scripts/verify.sh` exited 0 on macOS before publication:

- 1,235 tests passed and the one canonical-Linux integration test was skipped;
- all 7,768 measured statements and 2,080 branches reached 100%;
- Ruff format and lint passed;
- strict mypy passed across 38 source files;
- metadata, 82 provenance records, repository scanning, both frozen-oracle
  validators, R parsing, and the locked R environment passed.

The local result is not worker-execution evidence because canonical R execution is
Linux-only.

## Exact-Commit Linux CI

GitHub Actions run `29308457480` passed on exact implementation commit
`f0800c82d7033da2790abc69bc8adfe48570fcb1`:

- verify job `87006903860` passed in 3 minutes 45 seconds;
- `p006-worker-parity-ok` was emitted at `2026-07-14T05:26:34Z`;
- `p006-scientific-handoff-ok` was emitted at `2026-07-14T05:26:38Z`;
- all 1,236 Linux tests passed;
- all 7,768 measured statements and 2,080 branches reached 100%;
- metadata, 82 records, repository scanning, R lock, SBOM, secret scan, and
  dependency audit passed;
- container job `87006903862` built the canonical Linux amd64 image in 2 minutes
  59 seconds as `sha256:b54eec2cd101ab8fbe834f99599a40e85e0b5c51365b3e73bbf0e4487b7e4eea`.

## Acceptance Mapping

| Criterion | Result | Evidence boundary |
|---|---|---|
| P006-AC-02 | Passed | Fixed adapter, environment, opaque paths, injection regressions, and Linux worker gate |
| P006-AC-03 | Passed | Ordered result validation, durable commitment, exact guardian receipt, startup reconciliation, and race regressions |
| P006-AC-04 | Passed | Linux changed-unknown canary proves exact fitting artifacts and known-known distances |
| P006-AC-06 | Passed | Linux fixture-local comparison against checksum-frozen oracle-v2 at accepted tolerances |
| P006-AC-07 | Pending | CI created worker outputs and reports only in a temporary directory; a checksum-bound retained package is still required |
| P006-AC-08 | Pending | Exact Linux CI passed, but a separate exact-commit clean-clone replay and final retained evidence package are still required |

## Explicit Nonclaims and Next Gate

- This is fixture-local worker parity, not general stylo parity, preprocessing
  parity, authorship accuracy, threshold calibration, or a literary result.
- No public Upload-to-Run action, interpretation card, visualization, Pinocchio
  case study, production isolation, egress denial, load result, or deployment claim
  is established.
- Simultaneous host/guardian abrupt-death guarantees beyond the documented P005
  proof boundary are not claimed.
- The next P006 gate must run the parity validator with `--output-directory` on the
  exact implementation, retain worker outputs, parity/leakage/security reports,
  session information, and checksums through the existing fail-closed log
  transport, then perform a separate exact-commit clean-clone replay.
