# P006 Architecture and Method Audit

**Date:** 2026-07-13

**Base commit:** `9c61710e0fed774562410606c46615f36a84412c`

**Branch:** `codex/p006-stylo-worker`

## Bounded Review Process

The review used a declared ceiling of 160,000 tokens across the initial and
replacement attempts. Four distinct concerns were assigned: method, process
security, schema/provenance, and FAIR/claim boundaries.

Two initial reviewers consumed their 30,000-token ceilings while following the
large parent-wiki startup rule and did not reach the target source. Their outputs
are retained as disclosed failed reviews and are not counted as independent
approval. Two 20,000-token replacement reviewers inherited the completed startup
context and finished the method and security scopes. The schema and FAIR reviewers
completed useful bounded reports in the first round.

| Lens | Usable result | Main finding |
|---|---:|---|
| Method | Yes, replacement review | Freeze synthetic fixtures and an independent direct-stylo oracle before worker evaluation; known-only fitting and fixture-local claims are mandatory. |
| Security/lifecycle | Yes, replacement review | Process exit zero cannot be lifecycle success; secure output validation must precede durable terminal state and guardian acknowledgement. |
| Schema/provenance | Yes | JSON Schema needs a separate semantic validator for finite values, square symmetric matrices, labels, fitting IDs, cells, and session information. |
| FAIR/claim | Yes | P006 may support only named whole-text fixture parity and worker-level unknown invariance; CE-04, CE-07, reproducibility, FAIR package, and production claims remain later gates. |

## Critical Findings

### P0: Process Success Is Not Scientific Success

The P005 controller maps a normal process exit to `SUCCEEDED`, and the guardian
expects the durable terminal outcome to match that process mapping. P006 must insert
a bounded finalization phase:

1. process terminates;
2. one output is opened through the trusted workspace boundary;
3. strict JSON and semantic validation run;
4. the validated analysis outcome is durably persisted;
5. guardian acknowledgement is sent.

Exit zero with absent, malformed, non-finite, inconsistent, or mislabeled output is
not success. The guardian contract must support this distinction without weakening
P005 app-loss cleanup.

### P0: Combined Rescaling Can Leak Unknown Data

The parent audit loaded the installed stylo 0.7.71 lazy-load database without
loading the Tcl/Tk namespace and inspected `perform.delta`, `dist.delta`,
`dist.eder`, `dist.wurzburg`, `dist.cosine`, `perform.culling`, and the main
`stylo` pipeline.

`perform.delta(..., z.scores.both.sets=FALSE)` correctly creates training-derived
z-scores. For `distance="wurzburg"`, however, it passes the combined z-score table
to `dist.wurzburg`, which calls `scale()` again. This can let unknown rows alter the
Cosine Delta space. P006 therefore uses known-derived z-scores and
`stylo::dist.cosine` directly for Cosine Delta. The inspected combined rescaling
path is prohibited for known/unknown analysis.

### P0: Preserve the Opaque Workspace Boundary

P005 allows only 64-character lowercase hexadecimal artifact names. P006 must not
relax that policy for readable JSON filenames. Fixed digest-like names, private
creation, atomic replacement, no-follow reads, regular-file and single-link checks,
bounded size, and stable inode verification remain mandatory.

### P0: Fixed Command Means Fixed Command

The generic P005 process controller accepts a broader command sequence because it
also serves synthetic fixtures. The P006 adapter must emit only trusted absolute
`Rscript`, literal `--vanilla`, and trusted absolute `R/stylo_worker.R`. No user or
corpus value enters argv, environment, cwd, or R code.

## Proposed Method Protocol

- Whole-text candidate-feature counts are the P006 boundary. Raw-text
  preprocessing, segmentation, duplicates, and corpus health remain P007.
- Aggregate known counts define the MFW order under frozen C collation. Culling is
  applied to the ranked full table before the requested MFW prefix, matching the
  inspected stylo 0.7.71 order.
- Means, standard deviations, and every fitting artifact use known documents only.
  Unknown variants must leave fitting hashes and known-known distances unchanged.
- Classic Delta is primary. Eder's and Cosine Delta are separate sensitivity
  distances, not averaged scores.
- Proposed synthetic fixtures cover anchor, MFW grid, culling boundaries, distance
  families, unknown canaries, Unicode/locale ordering, ties, and insufficient
  features.
- Proposed settings are CC0-1.0 fixtures, `C.UTF-8`, UTC, NFC input, seed 20260713,
  exact feature equality, matrix parity `<=1e-6`, structural tolerance `<=1e-12`,
  and tie threshold `1e-12`.
- The settings above are not accepted human decisions. No oracle output may be
  frozen until Oğuz records a separate HumanDecision.

## Required Evidence

- three closed worker schemas plus strict parser and semantic-validator tests;
- injection, path, environment, permission, link, duplicate-key, malformed UTF-8,
  non-finite, ragged, asymmetric, negative, mislabeled, and cardinality fixtures;
- guardian finalization races for valid, invalid, partial, cancelled, timed-out,
  and app-loss paths;
- direct-stylo raw outputs, fixture hashes, worker outputs, parity matrix, and
  tie-aware ordering report;
- unknown-canary invariance report for features, culling, means, standard
  deviations, and known-known distances;
- complete R/platform/package/locale/timezone/RNG/BLAS/LAPACK/entrypoint session
  information;
- exact-commit clean-clone, Linux CI, canonical container, and retained checksum
  evidence.

## Claim Boundary

This audit establishes design requirements only. It establishes no R worker,
direct-stylo parity, leakage control, scientific result, public analysis,
preprocessing parity, benchmark validity, clean-room reproducibility, FAIR package,
production isolation, CE-04 verification, or complete CE-07 verification.
