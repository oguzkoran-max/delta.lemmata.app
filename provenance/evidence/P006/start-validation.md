# P006 Start Validation

**Date:** 2026-07-13

**Base main commit:** `9c61710e0fed774562410606c46615f36a84412c`

**Branch:** `codex/p006-stylo-worker`

## Pre-Edit Baseline

`./scripts/verify.sh` passed before the opening records were added:

- 970 tests passed;
- 6,551 measured statements and 1,732 measured branches reached 100% coverage;
- Ruff format and lint passed;
- strict mypy passed;
- metadata passed;
- 75 provenance records passed schema and reciprocal-link validation;
- repository scan passed;
- R 4.5.2, renv 1.2.3, stylo 0.7.71, and jsonlite 2.0.0 lock checks passed.

The local macOS check deliberately retained `stylo-namespace-load-deferred` because
XQuartz is not installed. P006 scientific execution and headless parity must pass in
the canonical Linux container; the local lock check is not parity evidence.

## Opening Review

Usable independent schema, FAIR, method, and security reviews were consolidated in
`architecture-audit.md`. Two first-round reviews exhausted their bounded budgets in
the parent wiki and produced no target-code verdict; they are disclosed and not
counted as approval. Replacement method and security reviews completed against the
target files.

Direct read-only inspection of stylo 0.7.71 confirmed the public frequency,
culling, Delta, Eder, Cosine, Wurzburg, and supervised Delta paths. It identified a
combined-rescaling hazard for Wurzburg/Cosine Delta with unknown data, now prohibited
by proposed ADR-0013.

## Opening-Package Gate

The complete opening package passed `./scripts/verify.sh` before the start commit:

- 970 tests passed;
- 6,551 measured statements and 1,732 measured branches reached 100% coverage;
- Ruff format and lint passed;
- strict mypy passed;
- metadata passed;
- 77 provenance records passed schema and reciprocal-link validation;
- repository scanning passed;
- the synchronized R 4.5.2, renv 1.2.3, stylo 0.7.71, and jsonlite 2.0.0 lock
  check passed.

The macOS run again retained `stylo-namespace-load-deferred`; it is a lock and
opening-record gate, not scientific execution or parity evidence.

## Repeatability Finding

A later full-gate repeat retained all 970 passing tests but exited 1 because
coverage reached 99.96% instead of 100%. The uncovered lines were the first
completion branch in `ProcessController._choose_winner`. Production behavior had
not changed: real-process timing had previously covered that branch incidentally,
while the deterministic unit test covered only completion after a usage sample.

A regression test now drives the pre-sample completion branch directly and proves
that process-group usage is not sampled after completion is already observable.
No production source was changed. The failed gate is retained in the Ticket rather
than being replaced by a later pass.

## Corrected Final Gate

After the deterministic regression test was added, the complete package passed
`./scripts/verify.sh` again:

- 971 tests passed;
- all 6,551 measured statements and 1,732 measured branches reached 100% coverage;
- Ruff format and lint, strict mypy, metadata, 77 provenance records, repository
  scanning, and the synchronized R lock checks passed;
- the local stylo namespace remained deliberately deferred pending canonical Linux
  execution.

This correction establishes a repeatable opening gate only. It is not worker,
scientific-output, parity, or Linux execution evidence.

## Verdict

P006 may proceed only to schema-first and scientific-finalizer implementation. No R
worker, frozen direct-stylo oracle, parity, leakage control, scientific result,
public analysis, production isolation, CE-04 verification, or complete CE-07
verification is established by this start package. The proposed fixture and
tolerance protocol requires a separate HumanDecision before reference outputs are
generated or frozen.
