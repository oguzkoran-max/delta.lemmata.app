# P004 Automated Acceptance Rehearsal Exact-Commit Verification

**Run:** `RUN-20260712-0005`

**Commit:** `9f3124a65216fd1c0f6d459cfe6a3049f51baa07`

**Started:** 2026-07-12T20:11:46Z

**Ended:** 2026-07-12T20:14:24Z

## Procedure

1. Created `$HOME/Developer/delta-p004-auto-exact-9f3124a` with
   `git clone --no-hardlinks`.
2. Detached the clone at the exact implementation commit.
3. Restored the committed Python and R environments with
   `./scripts/bootstrap.sh`.
4. Ran `./scripts/verify.sh`.
5. Ran the expanded P004 browser harness against a fresh local Streamlit process,
   writing output outside the clone.
6. Confirmed every machine-readable browser pass field, empty external-host and
   console lists, and the 25 generated screenshots.
7. Confirmed the detached clone remained clean after all checks.

The replay command sequence was:

```bash
./scripts/bootstrap.sh
./scripts/verify.sh
.venv/bin/python scripts/browser_audit_p004.py --output <external-output>
```

## Result

- bootstrap: passed;
- Ruff format and lint: passed;
- strict mypy: passed;
- pytest: 468 passed;
- measured coverage: 3,174 statements and 880 branches at 100%;
- metadata, 66 provenance records, repository, supply-chain, and R lock gates:
  passed;
- six Upload and six Review viewport gates: passed;
- Guided individual-TXT flow: passed;
- fail-closed permission-required rights flow: passed;
- exact `rights_status` correction and payload-free value restoration: passed;
- analysis-only action matrix and inventory-bound confirmation: passed;
- five documentation downloads with clean console: passed;
- strict two-member ZIP flow: passed;
- observed external hosts: none;
- source-payload echo: none;
- post-run clone status: clean.

The machine-readable browser result is retained at
`browser-audit/browser-audit.json`. Duplicate screenshot-path fields were removed
after the run; the complete 25-image passing set is already retained under
`../automated-acceptance-rehearsal-attempt-12/screenshots/`. Measurements and
pass/fail values were not changed.

## Limits

The clean clone used the same Mac and may reuse locked Python and R package
caches. Chromium was used rather than Safari or VoiceOver. Inputs were synthetic.
The run does not execute `stylo`, establish scientific validity, general
learnability, production isolation, retention enforcement, deployment behavior,
or the final owner walkthrough.
