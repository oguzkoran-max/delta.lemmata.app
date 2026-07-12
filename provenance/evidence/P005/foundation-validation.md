# P005 Lifecycle Foundation Validation

**Status:** Intermediate engineering evidence. P005 is not closed and no production
retention, isolation, secure-erasure, R/stylo, or scientific-result claim is made.

**Validated locally:** 2026-07-12, macOS, branch `codex/p005-job-lifecycle`

## Implemented Boundary

- Independent 256-bit session capability and public job identifier, keyed owner
  digest, non-authorizing job IDs, short support references, and opaque workspace
  components.
- Closed `job-policy-v1`: one running, three queued, four staged globally, one
  staged/active job per session, absolute queue/staging deadlines, and bounded
  event/tombstone retention.
- Immutable execution, outcome, cancellation, artifact-cleanup, operation-id, and
  optimistic-version models. Queued cancellation is supported; staged cancellation
  is rejected.
- Payload-free SQLite WAL control store with private database files, private and
  identity-pinned parent directory, atomic staged/queue admission, FIFO claim,
  one-running enforcement, content-free errors, owner checks, and validated CAS.
- Fixed private workspace layout, opaque file names, all-or-nothing materialization,
  hash/size revalidation, symlink/hardlink/rename-swap defenses, selective input/work
  cleanup, whole-job cleanup, and startup-safe layout loading.
- POSIX synthetic process controller with a dedicated `setrlimit + execve` launcher,
  clean environment, closed stdin, discarded stdout/stderr, fixed cwd, process group,
  wall/CPU/RSS/PID limits, TERM/KILL escalation, nested-child cancellation, and reap.
- Conservative English lifecycle projection. `Succeeded` is not shown until input
  and work cleanup is verified and the export is published; `Finalizing` and
  `Abandoned` are distinct states.
- Allowlisted deletion-event model containing only a stable code, reference digest,
  UTC timestamps, reason, counts, policy version, and expiry.

The public P004 Upload-Describe-Review flow remains payload-free and locked. These
components are not connected to public Start analysis before P006/P008.

## Validation Results

Checkpoint `eca535773a237d304b8c12397e1295df49295d3f`:

```text
./scripts/verify.sh
69 files already formatted
All checks passed!
Success: no issues found in 30 source files
769 passed in 20.01s
4,947 measured statements; 1,304 measured branches; 100% coverage
metadata-ok version=0.0.0.dev0
records-ok count=69
repository-scan-ok
r-lock-ok stylo-namespace-load-deferred
verify-ok
```

Focused combined P005 foundation run before workspace recovery:

```text
296 passed in 8.81s
1,699 measured statements; 406 measured branches; 100% coverage
```

Focused subsystem results:

- SQLite store: 20 passed, 343 statements, 74 branches, 100%.
- Process controller: 34 passed, 326 statements, 98 branches, 100%.
- Workspace after recovery controls: 41 passed, 445 statements, 92 branches, 100%.
- Validated-payload staging: 8 passed, 86 statements, 14 branches, 100%.
- Lifecycle UI, projection, and deletion events: 63 passed, 145 statements,
  34 branches, 100%.

## Failed Attempts and Corrections

1. Two early coding agents exhausted a 12k context budget before writing files.
2. A second SQLite/process pair exhausted a 40k budget while loading project context;
   neither changed files.
3. A 120k process attempt produced a partial controller, but macOS rejected resource
   setup inside `preexec_fn`; 15 of 24 tests failed. Resource setup was moved to a
   dedicated single-threaded Python launcher that applies limits and calls `execve`.
   macOS virtual-memory `RLIMIT_AS` cannot be lowered reliably beneath the running
   interpreter, so macOS uses process-group RSS sampling while Linux also inherits
   `RLIMIT_AS`. The boundary remains application-managed local POSIX evidence, not a
   cgroup/container claim.
4. The 120k SQLite attempt stopped with three failing tests, 97.47% coverage, Ruff
   failures, and unclosed-connection warnings. Deadline monotonicity, detached error
   context, explicit connection closure, WAL fail-closed tests, corruption paths,
   concurrency branches, and parent-directory identity checks were added.
5. The repository secret scanner initially mistook `icon_token="loader-circle"` for
   an assigned API token. Its regex now requires a complete identifier boundary and
   still detects real `token=`, `secret=`, and `api_key=` assignments.

## Residual Boundary

- Continuous janitor, startup running-job recovery, deletion-ledger persistence,
  result/export expiry, and tombstone/event purge are not yet implemented.
- Process-group identity is not yet persisted for post-crash orphan termination.
- Real R/stylo execution remains P006; public workflow integration remains P008.
- Linux exact-commit CI, adversarial clean-clone evidence, canonical container,
  SBOM, and P005 closure evidence remain pending.
- Production capacity, host isolation, Delta-LDA coexistence, proxy/TLS, swap,
  snapshots, backups, and secure/forensic erase remain P014/P015 boundaries.

## Commits

- `ae6720f7b107bdc611e00dd25226e7156b6334f9` lifecycle contract
- `bce5bb216ee9c133c31f458298ba778d41a80a50` lifecycle foundation
- `0da9a1b6a8a324aaa73c49437801c98b3013f3ac` honest lifecycle projections
- `5e1cbbaadd49215c03e6a2708927774f8a609caf` bounded job execution
- `eca535773a237d304b8c12397e1295df49295d3f` workspace recovery controls
