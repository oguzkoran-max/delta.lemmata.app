# P004 Metadata CSV Exact-Commit Verification

**Run:** `RUN-20260711-0006`

**Commit:** `8dd85c1d3cd454c3b1a8227122ff73e136da87b0`

**Started (UTC):** `2026-07-11T23:53:04Z`

**Ended (UTC):** `2026-07-11T23:53:40Z`

**Command:** `./scripts/verify.sh`

**Exit code:** `0`

## Preconditions

- Branch: `codex/p004-metadata-rights`
- The working tree was clean before the command.
- `HEAD` resolved to the exact commit above.
- The command ran from the repository root.
- No evidence or Run-record file was created inside the repository until the command
  had finished and the clean status had been checked again.

## Result

```text
40 files already formatted
All checks passed!
Success: no issues found in 17 source files
390 passed in 6.70s
2097 statements, 542 branches, 100% coverage
metadata-ok version=0.0.0.dev0
records-ok count=49
repository-scan-ok
r-lock-ok stylo-namespace-load-deferred
verify-ok
```

The working tree remained clean after the command. The Run therefore verifies the
committed implementation tree, not a later documentation or provenance-link commit.

## Covered Boundary

This run covers the P004 domain and versioned metadata CSV implementation present at
the recorded commit, including secure import/export, generated schemas, rights
controls, deterministic fixtures, record integrity, repository scanning, and the
locked R/stylo environment.

It does not cover the deferred Streamlit metadata editor, rights questionnaire,
Corpus Review browser behavior, real research texts, scientific stylo computation,
production deployment, retention enforcement, or P004 human acceptance.

## Replay

From a clean checkout at the recorded commit:

```text
./scripts/bootstrap.sh
./scripts/verify.sh
```

The recorded run used the already bootstrapped canonical workspace. A clean-clone
replay and browser evidence remain future P004 gates.
