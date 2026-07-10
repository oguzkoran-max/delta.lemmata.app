# P001 Clean Clone Verification

**Commit:** `26131a88a04d1d79ffe50d9eb9ee676d41c2072b`
**Started:** 2026-07-10T12:42:51Z
**Ended:** 2026-07-10T12:43:08Z
**Host:** macOS arm64; Python 3.13.9; R 4.5.2
**Result:** Passed

## Procedure

1. Clone the committed repository into a newly created temporary directory with
   `git clone --no-local`.
2. Run `./scripts/bootstrap.sh` without copying either project environment.
3. Run `./scripts/verify.sh` in the clone.
4. Check `git status --porcelain` after verification.

## Observed Results

- The clone resolved exactly to the commit recorded above.
- The locked Python environment installed 95 packages.
- `renv` restored the 10 missing locked R packages and reported a consistent state.
- Ruff format and lint, strict mypy, metadata, schema, supply-chain, repository,
  and R lock checks passed.
- Pytest collected and passed 24 tests; measured Python source coverage was 100%.
- The clone ended with zero versionable working-tree changes.

## Deliberate Limitation

The local macOS R/Tcl-Tk build still requires XQuartz to load the full `stylo`
namespace. P001 verifies exact installation and lock restoration. P006 owns
scientific execution and parity in the pinned Linux container.
