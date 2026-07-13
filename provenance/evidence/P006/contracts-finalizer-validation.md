# P006 Contracts and Scientific Finalizer Validation

**Date:** 2026-07-14

**Branch:** `codex/p006-stylo-worker`

**Decision:** `HD-20260713-0002`

**ADR:** `decisions/ADR-0013-stylo-worker-parity.md`

## Scope

This checkpoint implements and validates the closed Python-side scientific
contract before any R calculation or parity claim. It does not connect a public
analysis action, run an R worker, generate a direct-stylo oracle, or persist a
scientific result as lifecycle success.

## Implemented Boundary

- Closed Pydantic models and deterministic Draft 2020-12 schemas for worker input,
  result, and content-free fatal errors.
- Strict UTF-8 and JSON handling with duplicate-key, non-finite, out-of-range,
  invalid-Unicode, schema, and semantic rejection codes.
- A single JSON tree parse followed by strict scalar validation. Only JSON array to
  tuple and string to declared enum conversion are allowed; numeric strings remain
  invalid.
- A composable v1 profile: 20,000 features, 50 documents, 64 fits, 192 cells,
  1,000 MFW, 64-byte NFC features, 3,000,000 document-local counts, 150,000,000
  aggregate counts, and finite IEEE-754 double values.
- Conservative canonical-JSON input and result upper-bound calculations below the
  respective 32 MiB transport caps; serialization also enforces the cap.
- Known-only aggregate ranking, culling, relative-frequency means, sample standard
  deviations, selected feature order, and fitting-basis validation.
- Complete, partial, and failed outcome derivation from an exact requested fit/cell
  graph; explicit insufficient-feature and bounded calculation failures.
- Matrix label, shape, cardinality, finite-number, non-negative, symmetry, and zero
  diagonal validation.
- A pure fail-closed finalizer that separates process completion from scientific
  acceptance. Exit zero only permits output validation to begin.
- Bounded private workspace reads with exact opaque names, pre-open regular-file
  checks, no-follow and nonblocking open, owner/mode/link validation, before/after
  identity fingerprints, mutation and replacement detection, current-path area
  rebinding, bounded byte accumulation, and content-free errors.

## Method Regression Coverage

- Aggregate known counts can correctly exceed one document's count limit.
- A known or unknown document may have zero candidate-feature overlap.
- An unknown-only feature is excluded from ranking even when its unknown count is
  positive.
- Changing the unknown canary leaves ranking, culling eligibility, means, and
  standard deviations unchanged.
- Culling uses exact integer threshold arithmetic, including equality at 50%.
- Relative frequencies divide by whole-text `token_total`, not the sum of candidate
  counts.
- Equal-frequency NFC features use the locked UTF-8 byte order rather than incoming
  candidate order.

## Independent Adversarial Review

Three independent read-only agents reviewed the initial checkpoint through
scientific, security, and architecture/provenance lenses.

| Severity | Finding | Resolution |
|---|---|---|
| Blocker | Aggregate known count reused the document-local 3,000,000 cap and could raise an uncaught Pydantic error. | Added a separate 150,000,000 aggregate type and boundary regression. |
| Blocker | A JSON integer such as `10**400` could escape finite-number validation as `OverflowError`. | Added bounded tree validation, schema bounds, and finalizer regression. |
| Blocker | The first finite-number ceiling of `1e12` rejected a scientifically reachable Classic Delta above `6e12`. | Replaced the arbitrary ceiling with the finite IEEE-754 double domain and added a reachable `>1e12` regression. |
| High | FIFO output could block before file-type inspection. | Added pre-open `lstat`-equivalent checks, `O_NONBLOCK`, a direct flag assertion, and regular-file-to-FIFO race regressions. |
| High | A 64 MiB payload was parsed twice and workspace reads retained a chunk list plus joined bytes. | Reduced the closed result cap to 32 MiB, changed to one JSON parse, and accumulated into one bytearray. |
| High | Caller-supplied outcome/presence could masquerade as validated lifecycle success; generic P005 ACK remained usable. | Removed the entire premature lifecycle/ACK integration. AC-03 remains pending. |
| Critical | Terminal database commit followed by app death before ACK could leave `SUCCEEDED` with a deleted workspace result. | No false fix claimed. A future protocol must bind digest and size and be crash-recoverable before AC-03 can pass. |
| Medium | Zero candidate overlap was unnecessarily rejected. | Zero overlap is accepted; empty known support yields explicit insufficient-feature behavior. |
| Medium | Culling equality, unknown-only leakage, denominator, reversed candidate order, and Unicode tie cases were not discriminating tests. | Added focused method regressions for every case. |
| Medium | Canonical startup and handoff files still said that the HumanDecision was pending. | Synchronized `PROJECT_MEMORY.md`, `SESSION_HANDOFF.md`, `START_HERE.md`, and `AGENTS.md`. |
| Follow-up | P005 uses `C`; P006 records require `C.UTF-8`. | The future adapter must use a separate trusted P006 execution profile; the P005 global environment is unchanged. |

The read-only audits did not find a leaked claim of R execution, general stylo
parity, authorship accuracy, preprocessing parity, deployment, or public analysis.
After the numeric-ceiling and FIFO-race corrections, the final narrow scientific
review returned PASS with no new scientific or contract defect. The security and
architecture re-audits likewise reported no checkpoint-blocking defect; lifecycle
AC-03 remains intentionally open rather than being papered over.

## Retained Verification History

### Initial focused correction

The first post-audit focused run exposed six contract failures after replacing the
double parse. The cause was strict Python-mode handling of JSON arrays and enum
strings. A temporary global non-strict validation attempt then failed a new
numeric-string regression because it could coerce `"4"` to `4`. The final design
uses field-local conversion for arrays and declared enums while retaining strict
numeric scalars. The corrected focused suite passed 147 tests.

### First full gate, retained failure

`./scripts/verify.sh` passed all 1,072 behavior tests but exited 1 at 99.89%
coverage. Seven newly added defensive lines and three partial branches had no
direct adversarial test. The run covered 7,215 statements and 1,898 branches and is
retained as a failed quality gate rather than replaced by the later pass.

### Corrected full local gate

After adding explicit pre-open stat/open/fingerprint, serializer-cap, UTF-8
byte-bound, reachable large-distance, and FIFO-race regressions,
`./scripts/verify.sh` exited 0:

- 1,075 tests passed;
- all 7,216 measured statements and 1,898 branches reached 100%;
- Ruff format and lint passed;
- strict mypy passed across 36 source files;
- metadata passed;
- 80 provenance records passed;
- repository scanning passed;
- the synchronized R 4.5.2, renv 1.2.3, stylo 0.7.71, and jsonlite 2.0.0 lock
  check passed.

The local macOS gate deliberately reports `stylo-namespace-load-deferred` because
XQuartz is absent. It is a dependency-lock check, not R worker execution or parity
evidence.

## Exact Contract-Checkpoint CI

GitHub Actions run `29291282495` passed for exact implementation commit
`3c6ebe539b6c0a7f28c295cdcd74bc7e58135f6f`:

- verify job `86955214522` restored the pinned Python and R environments, passed
  source, metadata, schema, provenance, measured-coverage, SBOM, and dependency
  audit gates;
- container job `86955214531` built the canonical Linux amd64 image successfully.

This CI run establishes only the closed contracts, pure finalizer, and bounded
workspace-read checkpoint. It did not run an R worker, generate an oracle, compare
distances, or establish public analysis or production isolation.

## Explicit Nonclaims and Open Gates

- No R worker or fixed Python-to-R adapter exists yet.
- No synthetic fixture oracle output has been generated or frozen.
- No feature or distance parity has been measured.
- No durable scientific result, artifact digest, or crash-safe guardian handoff has
  been implemented; P006-AC-03 remains pending.
- No preprocessing, segmentation, corpus-health, accuracy, threshold, FAIR run
  package, Pinocchio, production isolation, deployment, or public analysis claim is
  established.
- Fixed R worker execution, independent direct-stylo oracle generation, and parity
  comparison remain the next P006 gates.
