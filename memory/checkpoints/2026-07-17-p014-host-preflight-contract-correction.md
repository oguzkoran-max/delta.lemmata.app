# P014 Host Preflight Contract Correction

## State

- Fresh target-host `pre-docker` gate passed with healthy zero-restart Lemmata,
  active Caddy, 2,339 MiB available RAM, 32,449 MiB free root disk, no swap,
  Docker absent, and port `8502` closed.
- The first Docker installer dispatch stopped before mutation with
  `P014_DOCKER_INSTALL_GATE_PHASE_INVALID` because the runbook passed a
  `pre-mutation` record while the guarded installer correctly requires the
  accepted `pre-docker` baseline.
- Post-failure checks confirmed no Docker binary/package/key/source/data root or
  transaction directory, unchanged Caddy hash, healthy Lemmata, and closed
  `8502`.
- The failed event is retained as `RUN-20260717-0004`; raw content-free host
  evidence is under `provenance/evidence/P014/live-20260717/`.

## Correction

The installer remains unchanged. The Phase 3 runbook, deployment validator, and
regression tests now agree on `pre-docker` as `--preflight`. The installer owns
the fresh `pre-mutation` capture immediately before package mutation.

## Verification

- The focused runbook, deployment-validator, installer-transaction, and
  host-gate suite passed all 63 tests after the two pre-existing loopback tests
  received their required local-socket permission.
- Two full-gate attempts stopped before substantive tests: the disposable
  worktree first asked `uv` to fetch isolated build requirements while network
  access was intentionally unavailable, then the correctly pinned offline run
  found one test file requiring project formatting. No dependency, test, or
  security check was weakened.
- After project formatting, the explicit offline canonical-environment run
  emitted `verify-ok`: 1,726 tests passed, one canonical-Linux R-worker test was
  skipped as designed on macOS, all 11,692 statements and 3,050 branches reached
  100% measured coverage, 118 provenance records passed, and the repository,
  metadata, schema, R parse, and R lock gates passed. Pytest also surfaced one
  non-failing `ResourceWarning` from an existing SQLite corpus test.

## Next Ordered Step

1. Merge this correction only through normal review and green CI.
2. Transfer the exact corrected operations tree to a new root-only host staging
   directory.
3. Rerun the guarded installer with the retained accepted `pre-docker` baseline.
4. Require the post-Docker gate and an external denial probe for port `8502`.
5. Pull and verify the immutable application digest, then stage Delta only on
   `127.0.0.1:8502`.
6. Stop before Caddy and present all pre-Caddy evidence to Oğuz Koran for a new,
   explicit proceed-or-stop decision.

P014 remains `in-progress`; AC-08 through AC-10 and the full deployment-profile
AC-05 remain open.
