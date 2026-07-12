# P005 Retention Janitor Validation

**Status:** Intermediate engineering evidence. P005 remains open because an
application-process crash can still outlive the current in-process worker monitor.

**Validated locally:** 2026-07-13, macOS, branch `codex/p005-job-lifecycle`

**Implementation commit:** `0e84b106b10ca979b0ebb7d5cd9b6ff5de73c2bb`

## Implemented Boundary

- SQLite schema v2 adds a content-free deletion ledger independent of job
  tombstones. It stores only the allowlisted deletion-event fields and migrates
  schema v1 without accepting future schema versions.
- Trusted maintenance reads and CAS still validate every successor through the
  immutable lifecycle helpers. A session capability is not retained for janitor
  work, and public owner-scoped APIs remain unchanged.
- `WorkspaceManager.load_optional` returns absence only for a genuinely missing
  owner or job below the pinned private root. Symlink, mode, identity, malformed
  component, incomplete layout, root replacement, and OS errors remain fail-closed.
- The continuously callable janitor enforces staged and queue boundaries at the
  exact absolute deadline, preserves terminal outcomes, retries failed cleanup,
  publishes a success export only after verified input/work absence, expires
  result/export at one hour, and purges events/tombstones only after verified whole
  workspace absence.
- Startup reconciliation refuses to change a running row without an injected
  recovery proof. This is intentionally unresolved until a guardian process proves
  the tested worker group stopped.

## Validation Results

First repository gate attempt stopped only at formatting:

```text
Would reformat: src/delta_lemmata/job_store.py
Would reformat: src/delta_lemmata/job_workspace.py
Would reformat: tests/test_job_store_retention.py
```

After applying the repository formatter, the complete gate passed:

```text
./scripts/verify.sh
72 files already formatted
All checks passed!
Success: no issues found in 31 source files
795 passed in 19.97s
5,262 measured statements; 1,404 measured branches; 100% coverage
metadata-ok version=0.0.0.dev0
records-ok count=69
repository-scan-ok
r-lock-ok stylo-namespace-load-deferred
verify-ok
```

Focused retention and workspace gates also passed:

```text
127 passed
1,370 measured statements; 352 measured branches; 100% coverage

44 passed
465 measured statements; 98 measured branches; 100% coverage
```

## Adversarial Cases Covered

- immediately before and exactly at staged, queue, result, export, event, and
  tombstone deadlines;
- successful raw/normalized cleanup before export publication;
- published and never-published export expiry;
- failed cleanup retry without overwriting the terminal outcome;
- malformed, duplicate, wrong-digest, wrong-policy, wrong-time, and corrupt
  deletion-ledger records;
- workspace symlink, incomplete layout, unsafe mode, missing owner/job, OS failure,
  and root revalidation;
- startup running rows with no recovery proof, a rejecting proof, a raising proof,
  and a positive injected proof;
- maintenance CAS races and tombstone purge blocked without verified workspace
  absence;
- continuous-loop stop and invalid configuration boundaries.

## Independent Process Finding

One 40k-budget workspace agent exhausted its budget before editing files. A second
40k-budget read-only process audit completed and reported a reproducible P0 design
gap: the current controller monitor is a daemon thread in the application process,
so application `SIGKILL` can leave the synthetic worker group alive. Persisting a
PID or PGID and calling `killpg` after restart is rejected because identifiers can
be reused.

The required next design is a separate per-job guardian with an app-liveness pipe,
an owned group anchor, content-free authenticated recovery evidence, and a real
macOS/Linux parent-loss harness. Until that evidence passes, P005-AC-06 and P005
closure remain pending.

## Claim Boundary

This checkpoint supports tested application-managed deadline and deletion controls
inside the local Delta namespace. It does not establish secure erase, unattended
app-crash cleanup, production retention, container/cgroup isolation, host isolation,
reboot behavior, or CE-14/CE-15 completion.
