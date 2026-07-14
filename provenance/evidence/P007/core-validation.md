# P007 Closed Contracts and Pure Core Validation

**Ticket:** P007  
**Commit:** `83a6eca2036a40e79b7e49d6b2507e914e7adcc6`  
**Date:** 2026-07-14

## Scope

This evidence covers only the closed P007 configuration, annotation overlay,
preparation manifest, corpus-health report, and READY-receipt schemas and the pure
`delta-surface-words-v1` preparation and corpus-health core. It does not establish
private materialization, one-time analysis admission, public workflow behavior,
benchmark accuracy, stability, FAIR certification, a literary finding, or
production isolation.

## Implemented Boundary

- Five checked-in Draft 2020-12 schemas are generated from strict, immutable,
  closed Pydantic models and are checked for drift in `scripts/verify.sh`.
- Parsers reject wrong types, empty or oversized payloads, invalid UTF-8, invalid
  JSON, duplicate keys, non-finite and out-of-range numbers, surrogate code
  points, unknown fields, and inconsistent semantic combinations with
  content-free codes.
- Preparation implements the accepted Unicode surface-word profile, preserves
  source bytes by digest, and emits deterministic prepared bytes, counts, hashes,
  and a content-free manifest.
- Candidate ranking uses known independent works only. Exact custom exclusions do
  not alter prepared text or full counts, and over-width P006 transport features
  are disclosed rather than silently truncated.
- Corpus health implements the accepted exact-duplicate, five-shingle Jaccard,
  exact shared-run, independence, minimum-data, chronology, length, group, and MFW
  capacity policies without exporting source text, shingles, token lists, or
  shared passages.

## Local Validation

The exact source later committed as `83a6eca` passed on macOS arm64 with Python
3.13.9:

```text
ruff format --check: 117 files already formatted
ruff check: passed
mypy src: 41 source files passed
P007 schema drift check: p007-schemas-ok count=5
pytest: 1,294 passed, 1 skipped
skip: canonical R worker integration requires Linux
coverage: 8,496 statements and 2,286 branches, 100.00%
```

The four new P007 modules were also measured independently: 48 focused tests,
728 statements, 206 branches, and 100.00% coverage.

## Canonical Linux Validation

GitHub Actions run
[`29367142454`](https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29367142454)
tested the exact commit on GitHub-hosted Ubuntu 24.04, x86_64, Python 3.13.9,
R 4.5.2, UTC:

```text
verify job: 87201419824
container job: 87201419770
pytest: 1,295 passed
coverage: 8,496 statements and 2,286 branches, 100.00%
records: 91 valid records
repository scan: passed
P006 R boundary and locked environment: passed
SBOM, dependency vulnerability, and secret gates: passed
canonical Linux amd64 image: built
image id: sha256:e9e2f6beda8ab2b68086cc40df8bb9d17daca3b29bd424e3122d004313340240
```

## Acceptance Consequence

`P007-AC-02` passes for the named closed contracts and validators. The test matrix
also supplies substantial evidence toward `P007-AC-04`, `P007-AC-05`, and
`P007-AC-06`, but those criteria remain pending until their cross-layer P006,
boundary, and admission obligations are complete.

## Remaining Limits

- Uploaded bytes are not yet rebound into a capability-owned private preparation
  workspace.
- READY receipts are structurally validated but are not yet issued, claimed once,
  or enforced as the only P006 entry path.
- Confound-matrix coverage and beginner-facing Prepare/Health screens are pending.
- No benchmark, Pinocchio, or real literary-corpus claim follows from these
  synthetic contract and method fixtures.
