# ADR-0013: Versioned stylo Worker and Parity Protocol

**Status:** Accepted by `HD-20260713-0002`; P006 closure complete within the
fixture-local whole-text worker boundary

**Date:** 2026-07-13

**Scope:** P006 whole-text frequency fitting, R worker boundary, scientific output finalization, and fixture-local parity

## Context

P005 can launch, limit, cancel, reap, and clean a generic process, but it maps a
normal process exit to a terminal success before any scientific output is parsed.
That is correct for its synthetic lifecycle fixture and insufficient for P006: an R
process can exit with code zero while producing missing, malformed, non-finite, or
scientifically inconsistent output.

P007 owns raw-text preprocessing and corpus health. P006 therefore needs a narrow
calculation boundary that can prove the R/stylo computation without silently taking
ownership of tokenization, segmentation, duplicate detection, or edition quality.
The claim matrix also assigns full CE-04 to P006 plus P007 and full CE-07 to later
benchmark tickets. P006 must not close those broader claims by itself.

Direct inspection of stylo 0.7.71 found an additional unknown-leakage hazard.
`perform.delta(..., distance="wurzburg", z.scores.both.sets=FALSE)` first creates
training-derived z-scores but then calls `dist.wurzburg`, which scales the combined
matrix again. P006 must not use that path for known/unknown Cosine Delta.

## Accepted Decision

- P006 input is a closed, versioned whole-text candidate-feature and raw-count
  table. P007 will later own how real raw text becomes that table.
- Documents carry opaque asset and work identifiers plus `known` or `unknown` role.
  User labels, filenames, metadata, and text never become code, argv, environment,
  or filesystem paths.
- Known documents alone determine aggregate MFW order, culling presence, relative
  frequencies, means, standard deviations, and selected feature inventory.
  Unknown rows are projected only after fitting.
- The order follows the inspected stylo 0.7.71 pipeline: build the ranked full
  feature table, apply culling, then take the requested MFW prefix. The collating
  environment is frozen before oracle generation.
- Classic Delta is primary. Eder's Delta and Cosine Delta are separate sensitivity
  distances; raw values are never averaged across families.
- Classic and Eder distances consume known-derived z-scores with their stylo
  functions in no-rescale mode. Cosine Delta consumes the same known-derived
  z-scores through `stylo::dist.cosine`; the leakage-prone combined re-scaling path
  is forbidden.
- Process outcome and validated analysis outcome are separate. The finalizer reads
  one bounded atomic output, applies strict JSON and semantic validation, persists
  the mapped result, and only then sends the guardian acknowledgement.
- P005's hexadecimal opaque filename policy remains unchanged. P006 uses fixed
  digest-like names and does not introduce human-readable worker paths.
- An independent base-R plus stylo reference harness runs before worker comparison
  and shares no Delta calculation helper. Its outputs are checksum-frozen.
- Fixtures are deterministic project-authored synthetic token corpora,
  not literary texts. Their publication license is CC0-1.0.
- Canonical settings are R 4.5.2, stylo 0.7.71, `C.UTF-8`, UTC, NFC input,
  seed 20260713, exact ordered feature equality, matrix parity `<=1e-6`, structural
  tolerance `<=1e-12`, and tie grouping threshold `1e-12`.
- Oğuz accepted the fixture, license, environment, tolerance, metric, known-only
  fitting, and claim settings in `HD-20260713-0002`. Reference outputs may be
  generated only under this protocol and must be checksum-frozen before worker
  comparison.

## Rejected Alternatives

### Treat Exit Code Zero as Analysis Success

Rejected. It would allow malformed or scientifically invalid JSON to become a
durable success and could acknowledge cleanup before evidence is accepted.

### Pass Parameters or Filenames on the Command Line

Rejected. The worker command is fixed. Validated structured input is the only
parameter channel, preventing shell and R-code interpolation.

### Let Unknown Participate in stylo Scaling

Rejected. It violates CE-07 and EPI-03 by allowing the target text to alter the
feature and z-score space used to compare it.

### Use perform.delta Wurzburg with Training-Only Scaling

Rejected for P006 known/unknown execution. In stylo 0.7.71 the inspected path
re-scales the combined matrix inside `dist.wurzburg`, reintroducing unknown data.

### Use Pinocchio or LiberLiber as the Parity Oracle

Rejected. P006 needs redistribution-safe deterministic development fixtures.
Pinocchio is a later worked example, not calibration or oracle data.

### Claim General stylo Parity at P006 Closure

Rejected. P006 can support only named whole-text fixtures and the locked
environment. Preprocessing and segmentation parity remain P007; broader validation
remains P010-P015.

## Consequences

- P006 begins schema-first and finalizer-first, not with an R analysis script.
- Guardian acknowledgement semantics need an explicit validated-output phase.
- Reference fixtures and outputs may now be generated under the accepted protocol,
  but only after the closed schemas and scientific finalizer are verified.
- The public analysis control remains locked through P007 and P008.
- P006 closure language must remain fixture-local and version-specific.

## Contract Checkpoint, 2026-07-14

- The accepted v1 transport profile is bounded to 20,000 candidate features, 50
  documents, 64 fitting configurations, 192 requested cells, and MFW values
  from 2 through 1,000.
  The lower bound is two because the locked `stylo` 0.7.71 distance functions
  reject one-column inputs; P006 does not replace that behavior with a local
  one-feature formula.
- Feature strings are NFC and at most 64 UTF-8 bytes. Document-local counts are
  bounded separately from the 150,000,000 corpus aggregate. Scientific numbers
  must be finite IEEE-754 doubles; no lower arbitrary distance ceiling is imposed.
- Input and result envelopes are each capped at 32 MiB. Conservative worst-case
  canonical-JSON bounds are computed in the contract module and tested below the
  transport caps.
- A document may have zero overlap with the candidate inventory. Unknown-only
  features remain excluded because ranking and culling use known rows alone.
- The pure finalizer now classifies process and validated worker output, but it is
  not connected to durable job success or guardian acknowledgement yet.
- Independent reference evidence uses the separate
  `direct-stylo-oracle-v1` envelope. It binds an exact canonical input SHA-256
  and reuses the scientific invariants without claiming to be worker output.
- An early ACK integration was removed after independent review showed that it did
  not bind an artifact digest/size and was not crash-recoverable between database
  commit and guardian acknowledgement. P006-AC-03 therefore remains open.

## Oracle v2 Strengthening, 2026-07-14

- The checksum-frozen v1 suite remains immutable evidence of its declared direct
  calculation, but it is not sufficient for final worker acceptance. Every v1
  document has `token_total=100`, and its only unknown row is last.
- The required v2 suite uses six distinct document totals, two unknown documents
  interleaved among known documents, a known final row, a changed-unknown canary,
  and an order-permutation request.
- V2 validation identifies roles and compares matrix values by opaque document ID.
  It may inspect fixture positions only to prove that the adversarial topology is
  present; it must never use position as the scientific role source.
- A separately implemented formula-level raw-count counterfactual must differ from
  the normalized reference by more than `1e-3` for every requested fit and each of
  the three distance families. This threshold checks fixture activation and does
  not replace the accepted parity tolerances.
- Capture and publication authority are separated. The manual-only capture job has
  read-only repository permission and emits a checksum-bound candidate through its
  immutable job log; a separately validated local publication commit retains the
  final evidence. The log transport is used because exact run `29298977429` passed
  both oracle executions and validation but artifact storage quota rejected upload.
- Fixed-worker implementation cannot begin until v2 is checksum-frozen and its
  source/capture/publication chain passes normal CI.

## Fixed Worker and Scientific Handoff Checkpoint, 2026-07-14

- The fixed adapter invokes only trusted `Rscript --vanilla` and worker paths under
  the dedicated `R_STYLO` environment profile. User-controlled values remain in
  the validated JSON contract and never enter argv, environment names, R code, or
  filesystem paths.
- Exact implementation commit
  `f0800c82d7033da2790abc69bc8adfe48570fcb1` passed the canonical Linux worker
  comparison against oracle-v2. Ordered features were exact, fitting values met
  the `1e-12` structural tolerance, matrices met the `1e-6` tolerance, and nearest
  tie groups were exact at `1e-12`.
- The two-unknown canary left fitting artifacts and known-known distances exactly
  unchanged while activating all three unknown distance families. Document-order
  permutation remained equivariant by opaque identity, and the injection fixture
  opened no observed shell or R-code channel.
- Scientific execution now has a durable one-time claim. Validated result bytes are
  published with an exact digest and size, committed as terminal, acknowledged by
  a signed guardian receipt, and then confirmed on the current SQLite row.
- Startup reconciliation is three-state: accepted evidence confirms the result,
  recovery-required evidence removes it, and unresolved evidence keeps export
  locked while normal input/work cleanup and the result deadline continue.
- Terminal proof is bound to the immutable terminal operation version rather than
  the mutable current row version. Janitor maintenance can therefore advance the
  row without invalidating a correct guardian acknowledgement.
- A RUNNING record without signed process or guardian proof remains the documented
  P005 unresolved-recovery boundary. P006 does not infer death from elapsed time.
- P006-AC-02, AC-03, AC-04, and AC-06 pass at this checkpoint. AC-07 and AC-08
  remain pending until worker outputs and reports are retained in a checksum-bound
  package and a separate exact-commit clean-clone replay is recorded.

## Retained Evidence and Closure, 2026-07-14

- Exact capture source `79cb268a348a35c9622efe52cd3a09a829a09b1f` passed
  normal Linux CI and read-only capture run `29340236382`.
- Evidence-only commit `7359cbe305743623db45777c3f4be059c847a74c`
  retains the exact 18-file worker package and external transport receipt without
  source-code or workflow changes. `RUN-20260714-0004` binds the source, image,
  transport, package, environment, reports, and declared claim boundary.
- The permanent offline validator verifies the evidence commit's exact parent and
  added-file set, freezes the complete native Run bytes, and replays source commit
  `79cb268` using that source's own validator and fixtures.
- Durable audit commit `d676d90aa1bebea6197f2f18b5f988c8e6d11794`
  removed the temporary capture job and passed GitHub Linux CI run `29350106890`:
  all 1,247 tests, worker parity, scientific handoff, 100% measured statement and
  branch coverage, SBOM/dependency/secret gates, and canonical Linux amd64 image
  construction passed.
- `RUN-20260714-0005` records a fail-closed exact-commit remote no-hardlinks clone,
  locked bootstrap, full local verify, explicit clean-worktree assertion, and the
  successful exact-commit Linux CI result.
- P006-AC-01 through P006-AC-08 pass only for the named synthetic whole-text
  fixtures, R 4.5.2, `stylo` 0.7.71, and the fixed worker contract. Full CE-04
  still requires P007; full CE-07 remains with P010/P011. P007-P015 product and
  publication claims remain locked.

## Evidence Links

- `provenance/evidence/P006/architecture-audit.md`
- `provenance/evidence/P006/start-validation.md`
- `provenance/evidence/P006/contracts-finalizer-validation.md`
- `provenance/evidence/P006/worker-handoff-ci.md`
- `provenance/evidence/P006/worker-evidence-validation.md`
- `provenance/runs/RUN-20260714-0004.json`
- `provenance/runs/RUN-20260714-0005.json`
- `memory/checkpoints/2026-07-14-p006-complete.md`
- `docs/development/p006-oracle-v2.md`
- `prompts/P006-start.md`
- `provenance/tickets/P006.json`
