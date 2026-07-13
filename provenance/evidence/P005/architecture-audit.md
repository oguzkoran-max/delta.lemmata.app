# P005 Architecture Audit

**Date:** 2026-07-12

**Base commit:** `d13e63cef5c19f5042fd2c6488fd02d63a7f345c`

## Read-Only Lenses

Four independent Codex explorers inspected the completed P004 tree without editing
files:

| Agent | Lens | Main finding |
|---|---|---|
| Volta | Security architecture | Job ID possession is not authorization; ownership, workspace confinement, bounded admission, process-group kill, and non-enumerating errors are mandatory. |
| Hubble | Lifecycle and retention | Terminal outcome and artifact cleanup are orthogonal; startup-only cleanup cannot satisfy deadlines; state changes require CAS and idempotency. |
| Avicenna | Product and accessible UX | P005 must not activate scientific analysis before P006/P008; cancelling and deletion claims require verified intermediate states. |
| Wegener | FAIR and claim boundaries | P005 proves only application-managed local controls; CE-14 production language and all CE-15 host-isolation language remain P014/P015 gates. |

Each explorer received an 8,000-token analysis budget. One reported that repository
inspection consumed its budget before completing every roadmap line; its findings
are retained as a bounded preliminary security review, not independent approval.

## Accepted Engineering Baseline

1. **Ownership:** A server-generated session capability and a separate cryptographic
   job ID are required. The ephemeral control store retains only a keyed owner digest.
2. **Control store:** Standard-library SQLite supplies transactions, compare-and-swap
   versions, queue admission, restart recovery, and process-safe ownership. It stores
   no research payload and expires all tombstones, so it is not project history.
3. **Two state axes:** Execution outcome is preserved after cleanup. Artifact cleanup
   cannot overwrite whether a job succeeded, failed, was cancelled, timed out, or
   crashed.
4. **Staging:** P005 provides a session-owned staging API with one lease per session,
   four global leases, and an immutable one-hour absolute TTL. P004 remains
   payload-free; public upload-to-job connection waits for P008.
5. **Queue:** One running and at most three queued jobs. Admission and allocation are
   one transaction; rejected work creates no job, directory, process, or log.
6. **Deadlines:** Staged lease and result/export are at most one hour; queued work and
   failed/cancelled/timed-out/crashed/abandoned payloads are at most 15 minutes;
   content-free events and deletion tombstones are at most seven days.
7. **Success publication:** An export cannot become visible until raw and normalized
   material is confirmed absent. Cleanup failure is not success.
8. **Process control:** P005 requires a finite versioned worker limit profile and
   validates behavior with an internal synthetic worker. R/stylo and production
   limits remain P006/P014.
9. **Public UI:** P005 prepares an accessible presentation projection only. It does
   not unlock Parameters, Start analysis, scientific success, or result graphics.
10. **Claim boundary:** P005 may report tested application-managed deletion and
    intra-Delta session isolation. It may not report secure erasure, production
    retention, host isolation, CE-15, or complete CE-14 verification.

## Required Adversarial Evidence

- complete legal/illegal transition matrix and idempotency report;
- concurrent one-running/three-queued admission with zero-allocation rejection;
- cross-session status/cancel/result/export/cleanup denial without existence oracle;
- workspace symlink, hardlink, rename-swap, permission, and external-canary tests;
- parent/child/grandchild cancellation, timeout, crash, simulated OOM, and reap tests;
- startup recovery plus continuously running janitor tests;
- fake-clock checks immediately before and after every retention deadline;
- canary scan across DOM, session state, SQLite/WAL, event/deletion logs, errors,
  another session, result, and export;
- exact-commit clean-clone, Linux CI, SBOM/dependency audit, and container build.

## Open Platform Boundary

macOS development can verify POSIX process groups and filesystem behavior, but it
does not establish Linux production containment. cgroups, seccomp/AppArmor,
no-new-privileges, separate Unix identities, egress denial, proxy buffers, swap,
snapshots, backups, reboot behavior, Lemmata load isolation, and rollback are P014.
