# P014 Pre-Execution Host-Change Review

**Observed at:** 2026-07-15T20:12:44Z
**Last updated:** 2026-07-16
**Branch:** `codex/p014-live-host-acceptance`
**Scope:** host-preparation commands and content-free operational gates
**Live-host mutations:** none

## Authority Boundary

Oğuz Koran accepted ADR-0018's existing-VPS, official-Docker, no-new-swap
profile for ordered host preparation and measurement in `HD-20260715-0002` and
`PE-20260715-0005`. That decision does not authorize Caddy, DNS, public routing,
or final activation. No command described in this record was executed against
the live VPS.

## Independent No-Go Findings

Two focused read-only reviews independently returned `NO-GO` before full CI.
They are advisory checks, not owner acceptance. Together they identified:

1. fixture JSON could be relabelled and accepted as operational host evidence;
2. Delta phases could miss additional public listeners;
3. a snapshot named `under-load` did not prove a duration-based load condition;
4. baseline freshness, host/boot identity, sample parity, OOM telemetry, firewall
   contents, exact Docker packages, repository hashes, OS/CPU profile, and closed
   evidence shape were not fail-closed;
5. failed or partial APT transactions could evade package cleanup;
6. rollback mutated before validating its inputs, was not safely retryable, and
   remained destructively callable after successful installation;
7. key/source creation had an untracked ownership window;
8. first-release rollback did not disable the systemd unit or guarantee Compose
   cleanup;
9. registry authentication used root's normal Docker configuration rather than
   an isolated temporary directory;
10. multi-line runbook commands were not uniformly fail-fast or anchored to the
    immutable release directory.
11. the first corrected host gate still checked package names and arbitrary
    repository hashes rather than proving installed-equals-candidate versions,
    official Docker package origin, the expected signing-key fingerprint, and
    the exact repository source profile. A fresh focused review returned
    `NO-GO`; schema `1.2.0` and an adversarial wrong-version/origin/key/source test
    closed that finding.
12. a later independent transaction review found that Python `assert` statements
    disappeared under optimized execution, the accepted preflight was not
    recaptured immediately before mutation, rollback could mask Docker CLI and
    service-stop failures, first-release cleanup was incomplete, and the pulled
    image revision was not proved before service startup;
13. a separate host/load review found that the candidate-origin check was not
    bound to the isolated official source, the load evidence lacked a closed
    finite-number schema and current host/boot binding, listener comparison was
    not symmetric, CPU limits were measured but not enforced, and the workload
    exercised only the health endpoint rather than the analysis worker.
14. integration review found that the first-release cleanup trap was armed only
    after the systemd unit had already been staged and installed, so an earlier
    shell failure could leave a partial unit behind;
15. a fresh focused load review found that one real R/`stylo` handoff could
    finish early while the nominal load window continued with health requests
    only, so the gate did not prove sustained analysis coexistence;
16. parent review found that an interrupted APT transaction could install
    `containerd.io` before the Docker CLI existed, while rollback incorrectly
    required that CLI before cleaning transaction-owned runtime state;
17. exact-head PR CI later exposed an intermittent browser-harness race: after
    the result display selector triggered a Streamlit rerun, the second canonical
    result download could be clicked before the rerun was stably idle and ended
    as `Download.path: canceled`. The same source's push run passed, and source,
    unit, and hardened-container gates remained green.

A later 30,000-token implementation worker exhausted its budget after review and
made no edit. That failed delegation did not contribute code or approval.

Both later reviews returned `NO-GO`. Their findings were accepted as blockers;
no live-host command was run. One follow-up host-gate worker also exhausted its
explicit budget before reading the implementation and made no edit. The parent
agent resumed that bounded file scope directly.

## Corrections Applied

- `scripts/p014_host_gate.py` now collects live state only. The production CLI
  has no snapshot/fixture input. It uses a closed schema, rejects non-finite JSON,
  hashes complete firewall command outputs, fails closed on telemetry errors,
  binds comparisons to the same machine and boot, enforces a two-hour baseline
  freshness window, and requires the exact accepted Ubuntu/CPU/swap/Docker
  package/repository/listener profile.
- Host schema `1.3.0` adds a live `pre-mutation` phase. The guarded installer must
  recapture it immediately before any key, source, package, service, firewall, or
  runtime-root mutation. It binds the current state to the accepted baseline and
  fails on host/boot age, Lemmata process or latency, Caddy hash, exact listener,
  firewall, forwarding, memory, disk, Docker, or port drift.
- Docker candidate evidence now derives the candidate from an APT policy view
  isolated to the exact Docker source file and requires its exact
  `resolute/stable amd64 Packages` origin. The system candidate must equal that
  isolated official candidate. Repository evidence records all primary signing
  fingerprints and accepts exactly the expected Docker primary fingerprint.
- `scripts/p014_install_docker_ubuntu.sh` validates the accepted preflight and
  exact firewall inputs, rejects Docker's documented conflicting Ubuntu
  packages, stages repository files under installer ownership, pins signed
  package candidates, arms rollback only for the unfinished transaction, and
  permanently disarms destructive rollback after the post-Docker gate passes.
- `scripts/p014_rollback_docker_ubuntu.sh` validates every destructive input
  before mutation, handles non-final dpkg states, rejects images/containers and
  completed installs, distinguishes an active inspected Docker daemon from an
  unfinished CLI-less or inactive transaction, removes only installer-owned
  paths, restores captured iptables/ip6tables and forwarding inputs, and requires
  a complete post-rollback host gate.
- `scripts/p014_load_gate.py` replaces the false single-snapshot load label with
  a bounded live workload. Schema `1.2.0` repeats the real isolated P006
  R/`stylo` handoff without an idle gap for at least the requested window while
  sampling both services, host memory pressure, listeners, OOM markers,
  container CPU/RAM/PIDs, restarts, and service-error counts. The gate remains a
  bounded coexistence test, not an analysis-throughput benchmark, maximum-
  capacity validation, or scientific validation.
- `deploy/public-alpha/README.md` now uses fail-fast command blocks, immutable
  release anchoring, isolated temporary `DOCKER_CONFIG`, explicit runtime
  inspection, atomic Caddy staging, a first-release cleanup trap armed before
  unit staging, separate pre-Caddy owner authorization, and the duration-based
  coexistence gate.
- `scripts/browser_audit_p008.py` now requires Streamlit's app root to report
  `CONNECTED` and `notRunning` twice across a 250 ms settle window before JSON
  downloads and after selectbox reruns. A canceled download remains a hard error;
  the harness does not retry and conceal a persistent user-visible failure.

## Targeted Verification

The corrected working tree passed:

- Ruff for the host gate, load gate, validator, and tests;
- `bash -n` for both guarded host-change scripts;
- 42 targeted P014 host, load, deployment, and adversarial tests;
- `git diff --check`.

After the later adversarial reviews, the remediation package added current-state,
origin, key, transaction, partial-install rollback, image identity, closed load
schema, sustained real-worker load, listener, resource, early-cleanup, and
runbook ordering cases. The current focused P014 package passes 109 tests plus
Ruff and both Docker shell syntax checks.

The first full `scripts/verify.sh` attempt stopped before tests because Ruff
reported four files requiring project formatting. No gate was bypassed. After
applying the formatter, the second full run passed at `2026-07-15T20:40:57Z`:

- 1,583 tests passed and the one canonical Linux R-worker integration test was
  skipped on macOS as designed;
- 11,382 statements and 2,964 branches reached 100% measured coverage;
- schema, frozen-oracle, retained-worker, P014 deployment, metadata, provenance,
  repository, supply-chain, secret, and R-lock checks passed;
- final result: `verify-ok`.

Two first re-review continuations with 25,000-token caps consumed their budgets
on mandatory repository context and issued no verdict. They are not counted as
review evidence. Subsequent focused continuations, including fresh 60,000- and
100,000-token attempts, also exhausted their explicit budgets while processing
the mandatory repository and wiki context and issued no verdict. None is counted
as approval. Oğuz Koran selected Claude Code for the final independent review of
the completed pull-request candidate.

After findings 14-16 were corrected, the current combined working tree passed a
new full `scripts/verify.sh` run on 2026-07-16:

- 1,651 tests passed and the one canonical Linux R-worker integration test was
  skipped on macOS as designed;
- all 11,382 statements and 2,964 branches reached 100% measured coverage;
- 109 focused P014 tests, Ruff, both Docker shell syntax checks, schema,
  frozen-oracle, retained-worker, deployment, metadata, provenance, repository,
  supply-chain, secret, and R-lock checks passed;
- final results: `verify-ok` and `records-ok count=109`.

The first GitHub push run `29483237852` and pull-request run `29483279276` for
commit `8faef460d34b461100edad11310dc7ed542efd8b` then exposed one Linux-only
test-isolation defect. Both verify jobs reached 100% measured
coverage but failed
`test_partial_install_without_docker_cli_can_continue_owned_cleanup`: the test
used `PATH=/usr/bin:/bin` to represent an absent Docker CLI, while GitHub's Ubuntu
runner legitimately provides Docker in `/usr/bin` and retained CI images. The
production rollback guard was not weakened. The correction gives that test a
hermetic command directory containing only the required `bash` and `dirname`
commands, so the absent-CLI branch is independent of the host runner. The failed
runs remain evidence. After the correction, all 109 focused P014 tests and the
full local gate passed again with 1,651 tests, one documented macOS skip, and
100% measured coverage. Replacement push run `29484009945` and pull-request run
`29484013488` for correction commit
`11a440bf1f1cfafd025a05582e4b16e98a3f261b` then passed. Their verify jobs
`87574066735` and `87574078192` and hardened-container jobs `87574066685` and
`87574078145` were all green. This clears the replacement PR CI gate for the
correction commit; Claude Code final review, normal merge/main CI, and a new
exact-main immutable image remain pending.

Evidence-only commit `5c1b0839af4684296b582ebedad2732605ea651e` then produced
green push run `29484671596`. Its parallel pull-request run `29484673782` passed
the source/test step and hardened-container job `87576200609`, but verify job
`87576200574` stopped in the P009 browser gate when the second canonical result
download returned `Download.path: canceled`. The failed run remains retained.
The correction waits for two connected/idle Streamlit observations instead of
adding a blind sleep or download retry. Three focused helper tests passed; the
combined related suite passed 119 tests. A fresh full local `scripts/verify.sh`
run then passed with 1,654 tests, one documented canonical-Linux skip on macOS,
11,382 statements, 2,964 branches, 100% measured coverage, `records-ok count=109`,
and `verify-ok`. Replacement exact-head CI remains required before independent
Claude Code review.

These are working-tree checks. They do not replace an independent focused
re-review, normal pull-request CI, green main CI, or an immutable image rebuilt
from the resulting main commit.

## Remaining No-Go Conditions

Host modification remains prohibited until:

1. Claude Code final independent review passes and any findings are corrected;
2. the change reaches main through normal review and green CI;
3. a new immutable image is published from that exact main source commit;
4. the accepted pre-Docker gate is captured immediately before installation.

Caddy/DNS/public activation additionally requires the separate Phase 5 owner
decision after localhost-only Delta, runtime inspection, external-port denial,
coexistence load, cleanup, and rollback evidence are presented.

## Sources

- `decisions/ADR-0018-shared-vps-runtime-capacity.md`
- `provenance/human-decision-ledger.jsonl` (`HD-20260715-0002`)
- `provenance/prompt-events.jsonl` (`PE-20260715-0005`)
- `provenance/evidence/P014/target-host-read-only-preflight.md`
- `provenance/evidence/P014/target-host-runtime-capacity-observation.md`
- Docker Engine Ubuntu installation documentation
- Docker packet-filtering and firewall documentation
