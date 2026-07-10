# P002 Clean-Clone Verification

**Observed at:** 2026-07-10T19:27:05Z

**Implementation commit:** `a888e7c81e5fdae12687903de29d0728f5c7cbd5`

## Procedure

1. Created a new temporary directory outside the source working tree.
2. Cloned the repository with `git clone --no-local`.
3. Ran `./scripts/bootstrap.sh` in the new clone.
4. Ran `./scripts/verify.sh` in the new clone.
5. Ran `git status --porcelain=v1` and confirmed an empty result.
6. Removed the temporary clone after recording the result.

## Result

- Frozen Python environment restored with uv 0.11.28 and Python 3.13.9.
- Frozen R environment restored with R 4.5.2 and a consistent `renv` state.
- Ruff format and lint passed.
- Strict mypy passed for 7 source files.
- All 40 tests passed.
- Measured Python source coverage was 100%.
- Metadata, provenance-record, repository, supply-chain, and R-lock checks passed.
- The clean clone contained no versionable changes after bootstrap and verification.

Lock hashes:

- `uv.lock`: `5d435ec968063c0f4c7120e8974f1e94aef4b421eac265d52e0d7d4ce8ce450e`
- `renv.lock`: `bb792d224470650053412194edc35f3fd866673bd78d30ca756fcec3ad86ea1d`

## Scope Boundary

This rerun validates restoration and automated P002 checks. It does not rerun the
recorded browser screenshots, establish production security, or execute `stylo`.
Those claims remain assigned to their later acceptance tickets.
