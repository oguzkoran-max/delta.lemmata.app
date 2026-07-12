# P004 Exact Family Language Weave Exact-Commit Verification

**Run:** `RUN-20260712-0004`

**Commit:** `374e2d04a3c28029c69b9311fa0f3118f4bedbce`

**Started:** 2026-07-12T18:34:01Z

**Ended:** 2026-07-12T18:35:18Z

## Procedure

1. Created a new temporary clone with `git clone --no-hardlinks`.
2. Detached the clone at the exact implementation commit.
3. Confirmed the clone was clean before bootstrap.
4. Restored the committed Python and R environments with
   `./scripts/bootstrap.sh`.
5. Ran `./scripts/verify.sh`.
6. Ran the complete P004 browser harness against a fresh local Streamlit process.
7. Confirmed the detached clone remained clean after all checks.

The replay command was:

```bash
./scripts/bootstrap.sh
./scripts/verify.sh
.venv/bin/python scripts/browser_audit_p004.py --output <temporary>/browser-audit
```

## Result

- bootstrap: passed;
- Ruff format and lint: passed;
- strict mypy: passed;
- pytest: 468 passed;
- measured coverage: 3,174 statements and 880 branches at 100%;
- metadata, schema, provenance, repository, supply-chain, and R lock gates:
  passed;
- six-viewport browser audit: passed;
- individual-TXT and two-member ZIP workflows: passed;
- computed exact palette, Language Weave, contrast, keyboard, no-overflow,
  payload-absence, no-egress, and clean-console checks: passed;
- post-run clone status: clean.

The machine-readable browser result is retained at
`browser-audit/browser-audit.json`. Its duplicate screenshot paths were removed
after the run; the complete visual set already exists in
`../exact-family-language-weave-attempt-6/screenshots/`. Measurements and pass/fail
values were not changed.

## Limits

The clean clone used the same Mac and may reuse locked Python and R package caches.
Chromium was used rather than Safari or VoiceOver. Inputs were synthetic and
in-memory. This run does not establish general usability, scientific validity,
production isolation, retention enforcement, deployment behavior, or P004 human
acceptance.
