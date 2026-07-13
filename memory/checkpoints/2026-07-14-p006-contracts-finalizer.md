# P006 Contracts and Finalizer Checkpoint

**Date:** 2026-07-14

## Decision

`HD-20260713-0002` accepted the project-authored CC0 fixture, locked environment,
tolerance, metric-role, known-only fitting, and fixture-local claim protocol in
ADR-0013.

## Completed Locally

- Closed v1 input, result, and fatal-error models plus checked-in schemas.
- Strict one-parse JSON boundary and input-dependent scientific semantics.
- Known-only ranking, culling, percentage frequencies, sample SD, exact cells, and
  matrix invariants.
- Pure process/output scientific finalizer.
- Bounded nonblocking private workspace output read with mutation and path-rebind
  checks.
- 1,075 tests; 7,216 statements and 1,898 branches at 100%; full local gate green.

## Independent Review Outcome

Three read-only reviews found aggregate-count, huge-number, FIFO, memory,
zero-overlap, method-test, provenance, and lifecycle issues. Contract and read
issues were corrected. The premature validated guardian ACK implementation was
removed because it did not bind a real artifact and was not crash-recoverable.
The scientific re-audit then found that an arbitrary `1e12` numeric ceiling could
reject a reachable Classic Delta value. The contract now accepts every finite
IEEE-754 double, has a reachable `>1e12` regression, and passed the final narrow
scientific review. The workspace suite also covers a regular-file-to-FIFO race and
directly proves use of nonblocking open.

## Open Boundary

This checkpoint is not an R worker, parity result, or lifecycle success path.
P006-AC-03 remains pending until a digest/size-bound, crash-safe durable result
handoff exists. Exact commit and Linux CI are the next gate; then fixed R worker and
independent direct-stylo oracle implementation may begin.
