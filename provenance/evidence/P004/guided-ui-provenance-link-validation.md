# P004 Guided UI Provenance-Link Validation

Date: 2026-07-12

Status: corrective record; P004 acceptance is not claimed.

## Retained Failure

The first `./scripts/verify.sh` run after adding `RUN-20260712-0001` stopped at the
record-integrity gate. The Run record's `command` and `replay.command` strings
described the same clean-clone procedure at different levels of detail, but the
repository contract requires exact equality.

```text
RUN-20260712-0001: command and replay.command differ
1 failed, 466 passed
3165 statements, 878 branches, 100% coverage
```

The run is not treated as passing evidence. No application or test code changed in
response. The two fields were aligned to the actual bootstrap, canonical verify,
and exact-commit browser sequence before the complete gate was rerun.

## Corrected Outcome

The corrected tree passed `./scripts/verify.sh` with 467 tests, 100% of 3,165
statements and 878 branches, and `records-ok count=55`. Ruff, strict typing,
schemas, metadata, repository, supply-chain, and R-lock gates also passed.

## Boundary

This was a provenance-schema failure, not a scientific, security, ingestion, or UI
failure. GitHub CI and Oğuz Koran's human acceptance remain separate open gates.
