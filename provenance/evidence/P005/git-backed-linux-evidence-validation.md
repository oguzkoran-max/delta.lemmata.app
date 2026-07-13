# P005 Git-Backed Linux Evidence Validation

**Date:** 2026-07-13

**Status:** Passed for the bounded P005 Linux CI and retained supply-chain evidence
gate. Final Ticket closure still requires removal of the temporary write-capable
capture workflow and a green normal CI run for the closure commit.

**HumanDecision:** `HD-20260713-0001`

**Exact source commit:** `d3ca0f67a6a08f2e6a232b0b686b36842ef819e9`

**Evidence commit:** `2eff470e4e06a1b1586c4aec251ba99162770dbc`

## Evidence Channel Decision

Four earlier final-implementation attempts passed Linux verification, evidence
generation, and the canonical container but could not retain the generated package
because GitHub rejected `upload-artifact` at an account-level storage boundary.
P005-AC-08 requires inspectable Linux CI, SBOM, audit, and container evidence; it
does not require GitHub's transient artifact service.

Oğuz Koran accepted a one-time branch-scoped Ubuntu capture that writes a
path-neutral, checksum-bound package to Git. Job logs alone were not treated as
sufficient. The previous quota failures remain in `final-ci-validation.md` and are
not rewritten as successes.

## Exact Linux Runs

### Capture workflow

- Workflow: `P005 Linux evidence capture`
- Run: `29268150070`
- Job: `86878774447`
- Result: success
- Runner: Ubuntu 24.04, x86_64
- Exact checkout: `d3ca0f67a6a08f2e6a232b0b686b36842ef819e9`
- Locked restore: Python 3.13.9, uv 0.11.28, R 4.5.2, stylo 0.7.71
- Repository gate: 970 tests, 6,551 statements, 1,732 branches, 100% measured
  coverage, 73 provenance records, repository scan, and locked R boundary passed
- Evidence generation: Python CycloneDX, R CycloneDX, dependency audit,
  environment inventories, source checksums, and path-neutral package validation
  passed
- Bot commit: `2eff470e4e06a1b1586c4aec251ba99162770dbc`

### Normal CI

- Workflow: `CI`
- Run: `29268150409`
- Verify job: `86878775588`, success
- Container job: `86878775601`, success
- The verify job independently repeated the 970-test, full-coverage, record,
  repository, R-lock, SBOM, audit, and package-validation gates.
- The canonical Linux amd64 container build passed.

## Retained Package

Package directory:
`provenance/evidence/P005/ci-supply-chain-d3ca0f6/`

Outer manifest:
`provenance/evidence/P005/ci-supply-chain-d3ca0f6.sha256`

| File | SHA-256 |
|---|---|
| `ci-supply-chain-d3ca0f6.sha256` | `08cd96c7586938a6a8c08eb240e1f461ca64f4e096f6dda8a9e7ec3d282269f6` |
| `checksums.sha256` | `e426fae4e1a6e5bc4bf7ab0f34954b54aa5bb4a12a100343a931cb24dbe9bd57` |
| `detect-secrets.json` | `6b5ef8fde0255dd714358fdc67bc0dc2b9df7ec27e69aa55afa8bc4ed0137ce8` |
| `pip-audit.json` | `fae8c18f803f7347a548a3adbc3f6e1b9459935d595d671f7af9a7de6d77fe76` |
| `python-environment.txt` | `dbebf5b335b885171443ef785d4d1df6efdd629c8bdfb536220b18f7578aec05` |
| `python-sbom.cdx.json` | `62de7dc1ccc85d243b84a8c1db08d90f5722a3e8f074cafcf9cf41c60f54727a` |
| `r-sbom.cdx.json` | `2b19db27bb1d5ab5b7c7b0f3fddf4e2c5989e4a39fa8bd6904dd6fef60427872` |
| `r-session-info.txt` | `0a0a28694379170f142fb81856815047e45253c9395c6fafb9705cbb8b492ed9` |
| `runtime-requirements.txt` | `2110dae3b82c86dad240e70ab4b3c4e80db0e5265d2ce5075b3000b8980794d2` |

The package validator confirmed exactly eight regular, non-empty UTF-8 files; four
JSON object roots; the ordered seven-file source checksum inventory; and no
`file://`, macOS user, GitHub runner workspace, Google Drive, account email, or
Windows user-path marker. The outer manifest and all seven nested source checksums
were independently replayed in a detached worktree at the evidence commit.

The Python CycloneDX document contains 99 components and 100 dependency entries,
including the root dependency. The R CycloneDX document contains 18 components.
`pip-audit` reports 45 dependencies and zero known vulnerabilities.

`detect-secrets` retains 365 unverified candidates rather than silently deleting
them: 363 are expected high-entropy Git and SHA-256 records, one is the content-free
`OWNER_SECRET_TOO_SHORT` enum label, and one is a deterministic URL-safe identity
test fixture. This report records that manual classification; it does not convert
an unverified detector report into a universal no-secret claim.

## Independent Replay Commands

```text
python3 scripts/validate_generated_evidence.py \
  provenance/evidence/P005/ci-supply-chain-d3ca0f6 \
  --manifest provenance/evidence/P005/ci-supply-chain-d3ca0f6.sha256

shasum -a 256 -c provenance/evidence/P005/ci-supply-chain-d3ca0f6/checksums.sha256
```

The sibling outer manifest was also replayed from inside the package directory.
Every file returned `OK`.

## Boundary

This evidence verifies the exact P005 source on hosted Linux, the retained
supply-chain bytes, package integrity, and the canonical container build. It does
not verify real R/stylo computation, scientific results, production isolation,
secure erase, swap, snapshots, backup deletion, deployment, Safari, VoiceOver, or
final product-owner acceptance. Those claims remain in their later Tickets.
