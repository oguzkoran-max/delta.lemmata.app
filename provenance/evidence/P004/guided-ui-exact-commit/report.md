# P004 Guided UI Exact-Commit Clean-Clone Verification

**Run:** `RUN-20260712-0001`

**Commit:** `c82740d9953a215b29edbe8d911de751c188b837`

**Verification started (UTC):** `2026-07-12T11:11:03Z`

**Verification ended (UTC):** `2026-07-12T11:12:05Z`

**Commands:**

```text
./scripts/bootstrap.sh
./scripts/verify.sh
.venv/bin/python scripts/browser_audit_p004.py \
  --output /tmp/delta-p004-exact-browser-c82740d
```

**Exit codes:** `0`, `0`, `0`

## Preconditions

- The repository was cloned locally with `--no-hardlinks` into a new temporary
  directory.
- The clone was detached at the exact commit above.
- `git status --porcelain=v1` was empty before bootstrap and verification.
- Python and R dependencies were restored from the committed lockfiles.
- The browser harness started its own fresh-process Streamlit server on a free
  loopback port.
- No research corpus was used. The browser harness generated synthetic TXT, ZIP,
  and metadata inputs in memory.

## Canonical Verification Result

```text
46 files already formatted
All checks passed!
Success: no issues found in 19 source files
467 passed in 15.37s
3165 statements, 878 branches, 100% coverage
metadata-ok version=0.0.0.dev0
records-ok count=54
repository-scan-ok
r-lock-ok stylo-namespace-load-deferred
verify-ok
```

The clone remained clean after the command. This verifies the committed
implementation tree rather than a later provenance-link commit.

## Browser Result

The exact commit also passed the fresh-process P004 browser harness. The retained
bundle is under `browser-audit/` and records:

- six Upload and six Review desktop, mobile, and reflow viewports;
- the complete individual-TXT Upload -> Describe -> Review regression;
- the two-member ZIP Upload -> Describe -> Review flow;
- deterministic member labels and digest prefixes;
- payload absence across Upload, Describe, Review, and review CSV values;
- timeline selection, composition and completeness parity, rights blocking, five
  documentation downloads, keyboard confirmation, and analysis lock;
- no observed external host, console warning, console error, or page overflow.

The raw JSON preserves the temporary absolute screenshot paths emitted by the
harness. The corresponding screenshots are copied beside it in this evidence
bundle.

## Covered Boundary

This run covers the committed P004 domain, metadata CSV, rights, payload-free
guided corpus workflow, Review projection, individual-TXT and validated-ZIP member
catalog paths, responsive Streamlit presentation, synthetic browser interactions,
and repository-wide quality gates.

It does not claim scientific stylometric computation, legal rights determination,
production isolation, retention enforcement, deployment readiness, Safari or
VoiceOver acceptance, or Oğuz Koran's human acceptance.

## Replay

From a clean checkout at the recorded commit:

```text
./scripts/bootstrap.sh
./scripts/verify.sh
.venv/bin/python scripts/browser_audit_p004.py --output /tmp/p004-browser-audit
```

The Python and R package caches on the same Mac may be reused, but package versions
and project environments are reconstructed from the committed lockfiles.
