# P007 Start Validation

**Date:** 2026-07-14

**Base main commit:** `5fab67cc1407fed196a9c3033619fa5288be3730`

**Branch:** `codex/p007-preprocessing`

## Pre-Edit Baseline

`./scripts/verify.sh` passed before the P007 opening records were added:

- 1,246 tests passed and one canonical-R-worker integration test was deliberately
  skipped on macOS;
- 7,768 measured statements and 2,080 measured branches reached 100% coverage;
- Ruff format and lint passed;
- strict mypy passed;
- P006 frozen-oracle, worker-evidence, parity, and scientific-handoff validators
  passed;
- metadata passed;
- 85 provenance records passed schema and reciprocal-link validation;
- repository scanning passed;
- the synchronized R lock check passed with local namespace loading deliberately
  deferred to canonical Linux.

This proves the P006-merged starting tree is clean. It is not P007 method
acceptance, preprocessing evidence, corpus-health evidence, public analysis, or a
scientific result.

## Opening Review

Four bounded read-only lenses completed method, architecture/security,
FAIR/provenance, and beginner-UX reviews. Their convergent findings are consolidated
in `architecture-method-audit.md`. They are agent review, not human acceptance.

The review found two implementation-blocking architectural gaps: P007 needs a
private P003-to-P005 materialization handoff because P004 state is payload-free, and
P008 must not be able to bypass corpus health through lower-level P005/P006 calls.
Proposed ADR-0014 addresses both without changing accepted P004 v1 schemas, P005
lifecycle states, or P006 wire schemas.

## Opening-Package Gate

The complete proposed opening package passed `./scripts/verify.sh`:

- 1,246 tests passed and the one canonical-R-worker macOS skip remained explicit;
- all 7,768 measured statements and 2,080 measured branches reached 100% coverage;
- Ruff format and lint plus strict mypy passed;
- all frozen P006 oracle, worker-evidence, parity, and scientific-handoff validators
  passed within their already accepted boundaries;
- metadata passed;
- 87 provenance records passed schema and reciprocal-link validation;
- repository scanning passed;
- the synchronized R lock check passed with local namespace loading deferred to
  canonical Linux;
- the command ended with `verify-ok`.

No production source, public schema, scientific fixture, or analysis behavior was
changed. This gate establishes opening-record integrity only.

## Verdict

P007 source implementation remains blocked until Oğuz records a separate
HumanDecision accepting or revising the preprocessing profile, health severities,
quantitative thresholds, minimum-data gates, temporary materialization boundary,
mandatory admission receipt, and public wording. The opening package itself cannot
be cited as preprocessing parity, corpus adequacy, FAIR compliance, or acceptance.
