# P005 Guardian Exact-Commit Verification

**Run:** `RUN-20260713-0001`

**Commit:** `3c746d160769e50baddf2e6ec1c3c13db14fd019`

**Started:** 2026-07-13T00:09:23Z

**Ended:** 2026-07-13T00:11:40Z

## Procedure

1. Created `<fresh-clone>/delta-p005-guardian-exact-3c746d1` with
   `git clone --no-hardlinks` from the local repository.
2. Detached the clone at the exact implementation commit.
3. Restored the committed Python and R environments with
   `./scripts/bootstrap.sh`.
4. Ran `./scripts/verify.sh` without editing source or evidence in the clone.
5. Confirmed the detached clone remained clean after verification.

## Result

- bootstrap: passed with uv 0.11.28 and locked renv restore;
- Ruff format and lint: passed;
- strict mypy: passed for 33 source files;
- pytest: 878 passed;
- measured coverage: 6,060 statements and 1,602 branches at 100%;
- metadata: passed;
- provenance integrity: 69 records passed;
- repository scan: passed;
- R/stylo lock boundary: passed with namespace load deferred by policy;
- post-run clone status: clean.

## Limits

The clean clone used the same Mac and may reuse locked Python and R package caches.
It verifies the exact committed local implementation, not Linux behavior, canonical
container parity, SBOM/dependency audit, production host isolation, reboot recovery,
secure erasure, real R/stylo execution, deployment, or final P005 acceptance.
