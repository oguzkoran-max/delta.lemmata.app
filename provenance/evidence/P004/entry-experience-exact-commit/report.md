# P004 Entry Experience Exact-Commit Clean-Clone Verification

**Run:** `RUN-20260712-0002`

**Commit:** `b538807799b83cae718c0c7888e28741bed56f66`

**Verification started (UTC):** `2026-07-12T12:29:20Z`

**Verification ended (UTC):** `2026-07-12T12:31:08Z`

**Commands:**

```text
./scripts/bootstrap.sh
./scripts/verify.sh
.venv/bin/python scripts/browser_audit_p004.py \
  --output /tmp/delta-p004-entry-exact-browser-b538807
```

**Exit codes:** `0`, `0`, `0`

## Preconditions

- The repository was cloned with `--no-hardlinks` into a new temporary directory.
- The clone was detached at the exact commit above.
- `git status --short --branch` contained only `HEAD (no branch)` before bootstrap
  and after all verification commands.
- Python and R environments were reconstructed from committed lockfiles. Package
  caches on the same Mac may have been reused.
- The browser harness started a fresh Streamlit process on a free loopback port.
- Only synthetic in-memory TXT, ZIP, and metadata values were used.

## Canonical Verification Result

```text
46 files already formatted
All checks passed!
Success: no issues found in 19 source files
467 passed in 15.08s
3,167 statements, 880 branches, 100% coverage
metadata-ok version=0.0.0.dev0
records-ok count=57
repository-scan-ok
r-lock-ok stylo-namespace-load-deferred
verify-ok
```

The exact implementation commit remained clean after verification.

## Browser Result

The same detached commit passed the complete fresh-process P004 harness. The
retained `browser-audit/` bundle records:

- six entry and six Review desktop, mobile, and reflow viewports;
- one semantic beginner entry region and H1;
- the three-step conceptual method map and visible purpose guidance;
- first-action visibility, responsive heading scale, 44px controls, 14px purpose
  labels, no page/control overflow, and an unoccluded header;
- keyboard selection between Compare Texts and Compare Groups;
- individual-TXT and two-member ZIP Upload -> Describe -> Review regressions;
- Review projection parity, downloads, confirmation, and analysis lock;
- no fake result phrase, submitted-text echo, observed external host, console
  warning, or console error.

The JSON retains temporary absolute screenshot paths emitted by the harness. The
corresponding screenshots are copied beside it.

## Covered Boundary

This run covers the committed beginner entry content, responsive visual system,
AppTest/browser oracles, existing P003 intake behavior, P004 corpus documentation,
and repository-wide quality gates.

It does not claim general learnability, screen-reader conformance, scientific
stylometric computation, legal rights determination, production isolation,
retention enforcement, deployment readiness, Safari or VoiceOver acceptance, or
Oğuz Koran's P004 human acceptance.

## Replay

From a clean checkout at the recorded commit:

```text
./scripts/bootstrap.sh
./scripts/verify.sh
.venv/bin/python scripts/browser_audit_p004.py --output /tmp/p004-entry-browser-audit
```
