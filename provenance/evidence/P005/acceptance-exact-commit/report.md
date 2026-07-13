# P005 Acceptance Exact-Commit Verification

**Run:** `RUN-20260713-0002`

**Commit:** `4b8a2e819ee06203ba7241c2a0261b9ba685b0a2`

**Started:** 2026-07-13T02:16:41Z

**Ended:** 2026-07-13T02:25:58Z

## Procedure

1. Created fresh `--no-hardlinks` local clones at the exact implementation commit.
2. Restored the committed Python and R environments with
   `./scripts/bootstrap.sh`.
3. Ran `./scripts/verify.sh` without changing the verification clone.
4. Confirmed that clone remained clean after the complete repository gate.
5. Ran the tracked P004 browser-boundary harness from a clean exact-commit state.
6. Ran the tracked P005 lifecycle-component harness in a separate clean clone so
   both browser records could independently report `git_dirty: false`.

## Result

- bootstrap: passed with uv 0.11.28 and locked renv restore;
- Ruff format and lint: passed;
- strict mypy: passed for 34 source files;
- pytest: 950 passed;
- measured coverage: 6,541 statements and 1,728 branches at 100%;
- metadata: passed;
- provenance integrity: 70 records passed;
- repository scan: passed;
- R/stylo lock boundary: passed with namespace load deferred by policy;
- post-verification clone status: clean;
- P004 browser boundary: passed from exact commit with no external host, console
  error, payload exposure, analysis activation, or responsive-layout failure;
- P005 lifecycle component: all 16 projections passed Chromium semantics and
  overflow checks at 1280x900 and 320x800;
- both browser records identify the exact commit and report `git_dirty: false`.

## Limits

The clean clones used the same Mac and may reuse locked Python and R package
caches. Browser evidence is Chromium-only and does not substitute for Safari or
VoiceOver testing. This run does not prove Linux parity, canonical container
behavior, retained CI SBOM integrity, production resource values, cgroup or host
isolation, reboot recovery, secure erasure, real R/stylo computation, deployment,
or product-owner acceptance. Those claims remain separate gates.
