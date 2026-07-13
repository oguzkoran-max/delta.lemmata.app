# P005 Guardian and Application-Loss Validation

**Status:** Historical guardian checkpoint. Its exact-commit clean-clone and Linux
CI/container/SBOM build gates later passed; subsequent P005 acceptance hardening is
recorded separately.

**Validated locally:** 2026-07-13, macOS, branch `codex/p005-job-lifecycle`

**Implementation commit:** `3c746d160769e50baddf2e6ec1c3c13db14fd019`

## Implemented Boundary

- A separate per-job guardian survives loss of the application process and owns the
  finite synthetic worker controller through an inherited liveness pipe.
- The original worker leader is observed with `waitid(..., WNOWAIT)` and is not
  reaped until group descendants are absent. This prevents PID/PGID reuse during
  normal TERM/KILL cleanup.
- Completion is a two-phase protocol. The guardian keeps ownership after sending a
  result and releases it only after the app proves the exact terminal SQLite row:
  job, running operation reference, terminal version, and mapped outcome must match.
- Missing, late, invalid, or failed acknowledgement triggers verified workspace
  cleanup and an HMAC-authenticated, content-free recovery receipt.
- Receipts bind `JobId` and the immutable `execution:running:none` operation
  reference, so another execution reference for the same job cannot replay proof.
- If ordinary cancellation and emergency reap both fail, the guardian does not
  exit. It retains the leader identity and retries safe group reaping until absence
  is proven.

## Validation Results

The first post-documentation repository gate failed only because `ADR-0012` had
been placed in Ticket `decision_ids`, whose integrity rule resolves HumanDecision
records rather than ADR files:

```text
P005: unresolved HumanDecision ADR-0012
```

The ADR remained linked through `supplemental_evidence`; the invalid decision entry
was removed and the complete gate was rerun.

The first gate after adding `RUN-20260713-0001` then passed provenance integrity but
stopped at repository scan because the human-readable report retained an absolute
local macOS user path. The path was replaced with the machine-independent
`<fresh-clone>` label and the report, manifest, and Run hashes were regenerated.

The final repository gate passed:

```text
./scripts/verify.sh
77 files already formatted
All checks passed!
Success: no issues found in 33 source files
878 passed in 26.50s
6,060 measured statements; 1,602 measured branches; 100% coverage
metadata-ok version=0.0.0.dev0
records-ok count=69
repository-scan-ok
r-lock-ok stylo-namespace-load-deferred
verify-ok
```

The four highest-risk real/fault-injection tests were repeated in three fresh pytest
runs after the final ownership change; all 12 executions passed. Earlier versions
also ran the two real app-loss races five times each before the later fixes.

`RUN-20260713-0001` then detached the exact implementation commit in a fresh local
`--no-hardlinks` clone, restored the committed Python and R locks, reran the same
878-test full gate with 100% measured coverage, and confirmed a clean post-run Git
status. Report and checksum manifest:
`provenance/evidence/P005/guardian-exact-commit/` and
`provenance/evidence/P005/guardian-exact-commit.sha256`.

The additive provenance-link commit `cfb503c` then passed GitHub Actions run
`29215163561`: Linux verification, SBOM generation/dependency audit, and the
canonical amd64 container build all succeeded. Details are recorded in
`provenance/evidence/P005/guardian-exact-commit-ci.md`.

## Real and Adversarial Cases

- app session receives `SIGKILL` while a nested three-process worker group runs;
- worker finishes before app loss, but durable terminal ACK is still absent;
- app group death does not kill the guardian because guardian and worker use
  separate POSIX sessions;
- malformed control byte, EOF, cancellation, wall timeout, crash, and normal result;
- protocol-monitor and worker-monitor thread start failures;
- process enumeration failure followed by a second normal-reap failure;
- persistent reap failure retains guardian ownership and retries instead of exiting;
- ACK before SQLite terminal transition, wrong version, wrong outcome, late ACK,
  broken ACK pipe, and store failure;
- forged signature, wrong execution reference, same-job replay attempt, expiry,
  unsafe receipt root/record, short read, malformed JSON, and write races;
- external workspace symlink canary, content canaries, receipt/SQLite/WAL absence,
  and startup recovery to one `ABANDONED` outcome.

## Independent Review Record

The first 40k read-only agent exhausted its budget before code review and produced
no finding; it was not counted as approval. An 80k adversarial review found the
completion/app-loss race, malformed-control orphan path, and guardian-reap gaps.
After repair, a 60k review found premature ACK, same-job receipt replay, two
thread-start failures, and a second-control-failure leak. A final narrow review
confirmed ACK, execution binding, and thread failures closed, then found one last
double-reap exit path. `reap_until_absent` closed it. The last 20k independent check
returned `CLOSED` with no new P0/P1.

## Claim Boundary

This checkpoint supports the tested local POSIX application-loss boundary on macOS.
The later Linux CI result is a separate source/test and image-build record, not a
production runtime claim. Neither record establishes secure erasure, reboot
recovery, production resource values, container/cgroup/host isolation, proxy
behavior, R/stylo execution, or CE-14/CE-15 completion. Those claims remain gated by
P006/P014/P015 work.
