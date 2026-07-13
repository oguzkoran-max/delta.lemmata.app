# P005 Final Exact-Commit Verification

**Run:** `RUN-20260713-0003`

**Commit:** `2a17ec60ed62695e1e47383ad930330bef52f134`

**Started:** 2026-07-13T02:57:39Z

**Ended:** 2026-07-13T03:01:07Z

## Procedure

1. Created fresh `--no-hardlinks` local clones at the final implementation
   commit after the Linux process-reap correction.
2. Restored the committed Python and R environments with
   `./scripts/bootstrap.sh`.
3. Ran `./scripts/verify.sh` without changing the verification clone.
4. Confirmed that clone remained clean after the complete repository gate.
5. Ran the tracked P004 browser-boundary harness from the same clean exact-commit
   state.
6. Ran the tracked P005 lifecycle-component harness in a separate clean clone so
   both browser records independently report `git_dirty: false`.

## Result

- bootstrap: passed with uv 0.11.28 and locked renv restore;
- Ruff format and lint: passed;
- strict mypy: passed for 34 source files;
- pytest: 950 passed;
- measured coverage: 6,551 statements and 1,732 branches at 100%;
- metadata: passed;
- provenance integrity: 71 records passed;
- repository scan: passed;
- R/stylo lock boundary: passed with namespace load deferred by policy;
- post-verification clone status: clean;
- P004 browser boundary: passed from the exact commit with no external host,
  console error, payload exposure, analysis activation, or responsive failure;
- P005 lifecycle component: all 16 projections passed Chromium semantics and
  overflow checks at 1280x900 and 320x800;
- both browser records identify the exact commit and report `git_dirty: false`.

## Limits

The clean clones used the same Mac and may reuse locked Python and R package
caches. Browser evidence is Chromium-only and does not substitute for Safari or
VoiceOver testing. Linux source verification and the canonical container passed
for this commit, but GitHub rejected the generated supply-chain artifact because
account storage recalculation remained pending after expired-artifact cleanup.
This run does not prove production resource values, cgroup or host isolation,
reboot recovery, secure erasure, real R/stylo computation, deployment, or
product-owner acceptance.
