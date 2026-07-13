# ADR-0013: Versioned stylo Worker and Parity Protocol

**Status:** Accepted by `HD-20260713-0002`; implementation and evidence remain pending

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
  documents, 64 fitting configurations, 192 requested cells, and 1,000 MFW.
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
- An early ACK integration was removed after independent review showed that it did
  not bind an artifact digest/size and was not crash-recoverable between database
  commit and guardian acknowledgement. P006-AC-03 therefore remains open.

## Evidence Links

- `provenance/evidence/P006/architecture-audit.md`
- `provenance/evidence/P006/start-validation.md`
- `provenance/evidence/P006/contracts-finalizer-validation.md`
- `prompts/P006-start.md`
- `provenance/tickets/P006.json`
