# P005 Acceptance Hardening Validation

**Status:** Final exact-commit candidate passed. Linux verification, evidence
generation, and the canonical container passed; retained supply-chain artifact
upload and product-owner acceptance remain open.

**Date:** 2026-07-13

## Why This Pass Was Required

The first closure audit rejected P005. It found five material gaps rather than
documentation polish:

1. model and store calls could accept deadlines beyond `job-policy-v1`;
2. result, export, and cleanup lacked one capability-first service boundary;
3. capacity rejection was not composed ahead of every allocation surface;
4. an expired job could claim server removal before cleanup was verified;
5. malformed deletion-event input could appear in validation errors.

The evidence audit also found an incomplete terminal-outcome retention matrix, no
fresh P005 browser-boundary artifact, no retained CI SBOM artifact, and stale
container/environment wording. P005 remained open while these findings were fixed.

## Implemented Corrections

- `JobRecord` now enforces the closed policy version and maximum staged, queue,
  running cleanup, unsuccessful payload, result, export, event, and tombstone
  deadlines. Legal transitions shorten earlier leases instead of extending them.
- `JobService` authorizes status, cancel, result, export, and cleanup before opening
  a workspace or reader. Unknown, malformed, and unauthorized requests share the
  same content-free response.
- SQLite admission now checks session and capacity limits before job-ID generation.
  The reservation includes workspace materialization; failure rolls the job and
  events back and removes the workspace. Concurrent rejection does not call the ID
  factory, materializer, or process gateway.
- A failed store finalization now also removes already materialized files. If store
  finalization and immediate filesystem cleanup both fail, startup reconciliation
  inventories the trusted root and removes verified workspaces that have no control
  row. This sweep runs only during startup, not beside live admission transactions.
- Unsuccessful terminal jobs with retained artifacts continue to consume both the
  owner and global admission budgets. Cleanup failure therefore cannot create an
  unbounded series of payload-bearing terminal workspaces.
- Queue claiming terminalizes cancellation-requested entries without launching
  them, then continues FIFO selection. Running cancellation delivery is idempotent
  and retryable; a launch error must be synchronously reaped before the row becomes
  `CRASHED`.
- Owner-requested cleanup can withdraw a published export before its scheduled
  expiry, then verify every artifact absent and record content-free deletion
  evidence.
- Non-success terminal outcomes project `Cleaning up` or `Cleanup needs attention`
  until all artifact states prove absence. `Expired` removal copy is reachable only
  after that proof.
- Deletion-event validation hides raw inputs and its factory exposes only
  `JOB_DELETION_EVENT_INVALID`.
- One injected canary lifecycle is scanned across SQLite/WAL, events, service state,
  owner and other-session errors, status projection, result/export rejection, and
  cleanup.
- Every running unsuccessful outcome (`failed`, `cancelled`, `timed_out`, `crashed`,
  and `abandoned`) has a deterministic fake-clock cleanup test.
- Lifecycle projections now have an escaped HTML renderer with `status` or `alert`,
  `aria-live`, and `aria-atomic` semantics. Public analysis remains locked.
- CI now preserves SBOM, audit, environment, and checksum output as a 90-day
  commit-named artifact using a commit-pinned upload action.
- Guardian completion now uses a reciprocal acknowledgement: the app sends durable
  terminal ACK and the guardian replies `A` only when that ACK arrived before its
  deadline. Timeout recovery replies `X`, so a late app ACK cannot be mistaken for
  a no-cleanup success.
- Guardian and worker launchers receive an inode-checked cwd descriptor and enter it
  with `fchdir`; pathname rename/symlink swaps between validation and spawn fail
  closed. Partial pipe setup errors close every allocated descriptor.
- SQLite WAL/SHM hardening accepts an already-open sidecar whose link count became
  zero because another connection removed it. Main database identity and hardlink
  rejection remain strict. The public concurrency test then passed 100 separate
  interpreter runs.

## Automated Result

The current candidate passed:

```text
./scripts/verify.sh
80 files already formatted
All checks passed!
Success: no issues found in 34 source files
950 passed in 30.98s
6,541 measured statements; 1,728 measured branches; 100% coverage
metadata-ok version=0.0.0.dev0
records-ok count=70
repository-scan-ok
r-lock-ok stylo-namespace-load-deferred
verify-ok
```

The concurrent admission test initially exposed an intermittent
`JOB_STORE_INVALID_DATABASE`. A diagnostic run traced it to an opened WAL/SHM
sidecar being unlinked between `open` and `fstat`, not to capacity arithmetic. The
sidecar race was fixed without relaxing main-database identity checks; the same
public test then passed 100 separate interpreter runs. The exact clean-clone
repetition is recorded below; Linux repetition remains required.

Independent re-audit reproduced five service/store P1 paths before repair: store
finalization orphaning, unbounded cleanup-failure workspaces, launch compensation,
queued cancellation launch, and lost running-cancel delivery. After repair, the
same probes reported no remaining P0/P1 and ten focused regression tests passed.

## Browser Evidence

`browser-boundary-run-1` passed every viewport and interaction assertion, observed
no external host, and found no browser-visible payload. It failed overall because
five Streamlit download-button requests emitted transient `404` console errors.

`browser-boundary-run-2` repeated the same tracked Chromium harness in a fresh
Streamlit process. Six upload and six review viewports, guided and ZIP flows, rights
correction, keyboard interaction, responsive geometry, analysis lock, no external
hosts, no console errors, and payload-absence checks all passed.

`lifecycle-component-run-1` rendered every P005 lifecycle state in Chromium at
1280x900 and 320x800. Region count, role, live-region semantics, heading presence,
escaping, forbidden markers, and horizontal overflow checks passed. This first
component run used the dirty candidate and is not exact-commit evidence.

## Exact-Commit Evidence

`RUN-20260713-0002` reconstructed commit
`4b8a2e819ee06203ba7241c2a0261b9ba685b0a2` in fresh `--no-hardlinks`
clones. Locked bootstrap, all repository gates, 950 tests, 6,541 measured
statements, 1,728 measured branches, and 100% coverage passed. The verification
clone remained clean.

The tracked P004 browser harness then passed from a clean exact-commit state. Its
record reports `git_dirty: false`, no external host, no console error, and no
browser-visible payload or analysis activation. The P005 component harness ran in
a separate clean clone and passed all 16 lifecycle projections at 1280x900 and
320x800 with correct live-region semantics and no horizontal overflow. It also
reports the exact commit and `git_dirty: false`.

The report, both machine-readable browser records, screenshots, and their external
SHA-256 manifest are retained under:

- `provenance/evidence/P005/acceptance-exact-commit/`
- `provenance/evidence/P005/browser-boundary-exact-4b8a2e8/`
- `provenance/evidence/P005/lifecycle-component-exact-4b8a2e8/`
- `provenance/evidence/P005/acceptance-exact-commit.sha256`

## Final-Commit Correction And Replay

The first Linux closure run exposed a real emergency-reap defect: when process
enumeration failed again after `SIGKILL`, the controller could publish an error
without collecting the killed leader. The fallback now collects the owned leader,
does not re-signal a potentially reusable process-group identifier, and still
returns `REAP_FAILED` because descendant absence was not proven.

The next Linux run passed all 950 tests but exposed one platform-dependent coverage
branch. A deterministic fake-clock case now executes that branch on both macOS and
Linux. `RUN-20260713-0003` then rebuilt final implementation commit
`2a17ec60ed62695e1e47383ad930330bef52f134`: 950 tests, 6,551 statements,
1,732 branches, 100% coverage, all repository gates, both tracked browser
harnesses, and clean exact-commit status passed.

Final exact-commit artifacts are retained under:

- `provenance/evidence/P005/final-exact-commit/`
- `provenance/evidence/P005/browser-boundary-exact-2a17ec6/`
- `provenance/evidence/P005/lifecycle-component-exact-2a17ec6/`
- `provenance/evidence/P005/final-exact-commit.sha256`

For final commit `2a17ec6`, GitHub run `29220278021` passed Linux verification,
100% coverage, SBOM/dependency-audit generation, and the canonical Linux amd64
container. Upload alone failed because GitHub reported an account artifact-storage
quota. Seven already-expired Windows build artifacts totaling about 2.5 GB were
removed; the immediate retry was still rejected because GitHub documents a 6-12
hour usage-recalculation delay. The upload remains a hard gate rather than a
`continue-on-error` step. Full sequence:
`provenance/evidence/P005/final-ci-validation.md`.

## Claim Boundary

These results cover the application-managed P005 mechanism and synthetic fixtures.
They do not establish scientific R/`stylo` correctness, production resource values,
container runtime parity, cgroup or host isolation, reboot recovery, secure erasure,
Safari, VoiceOver, deployment, or the final product-owner walkthrough.

The tested fixed worker tree does not establish containment of arbitrary
user-controlled code. In particular, preventing a deliberately spawned descendant
from creating a new POSIX session requires the P014 container/cgroup/process-
isolation boundary; P005 makes no such claim.
