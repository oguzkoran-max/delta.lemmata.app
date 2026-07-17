# P014 Live-Host Integration Correction Checkpoint

Date: 2026-07-18
Status: correction locally verified; review and CI pending; no new live-host execution allowed

## Canonical State

- application source commit:
  `25fc2cadbba2147db6c7767e802088706a305f28`
- immutable private image:
  `ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:eb0c13a77dc39af8cf4dbfdadc811dd3bbe1f0b3d0381b15e140f5367ce9a54d`
- failed attempt operations commit:
  `748d3fdc688302d9b373557e030cf06bb39d78a1`
- failed attempt operations archive SHA-256:
  `00f3e78936a77511ede0120b54150bb2cf129629d90421201f101e7018cc5c75`
- correction branch: `codex/p014-live-host-fixes`
- correction worktree: `/tmp/delta-p014-live-host-fixes`

## Live Outcome

The accepted pre-Docker and installer-owned pre-mutation gates passed. Docker
was installed from the fixed official package set, but the post-Docker gate
looked outside the installer's private APT list directory and returned the false
failure `P014_DOCKER_PACKAGE_ORIGIN_INVALID`.

The automatic rollback removed Docker but could not prove the originally empty
firewall because restoring an empty iptables file does not delete Docker's
nftables tables. After preserving the Docker-only residual and rechecking the
three byte-empty baseline captures, the ruleset was flushed and the guarded
rollback was rerun. The final post-rollback gate passed.

Current target-host state:

- Docker absent;
- Delta absent;
- Caddy and Lemmata active;
- Lemmata 20/20 healthy, zero restarts, unchanged start identity;
- original listeners, forwarding, Caddyfile, and empty firewall restored;
- no public route or DNS change.

## Implemented Correction

- pass the root-only APT list directory into post-Docker and Delta-idle host
  gates;
- use that directory in isolated `apt-cache policy` calls;
- preserve firewall residuals before rollback restoration;
- explicitly flush nftables only when all validated baseline captures are
  exactly empty;
- retain captured restore behavior for non-empty baselines;
- enforce both changes in the runbook and deployment validator;
- add regression coverage for isolated APT policy, CLI path validation,
  empty-baseline flush, non-empty restore, and immutable residual evidence.

## Verification

- Bash syntax: passed for installer and rollback scripts.
- Ruff formatting and lint on changed Python/test files: passed.
- Focused host-gate and transaction tests: 46 passed.
- P014 deployment package validator: passed.
- A wider restricted test attempt passed 67 tests; two unchanged socket tests
  were blocked by the local sandbox before the complete authorized run.
- The first complete canonical-Python run passed all 1,732 applicable tests
  with one declared canonical-Linux-only skip and 100% measured coverage, then
  retained an R-library-path stop at the final lock check.
- The final explicit canonical Python and `renv` library run emitted
  `verify-ok`: 1,732 tests passed, one canonical-Linux-only test was skipped as
  designed on macOS, all 11,692 statements and 3,050 branches reached 100%
  measured coverage, 119 provenance records passed, and the metadata,
  repository, schema, R parse, R lock, and deployment-package gates passed.

## Next Steps

1. commit, push, open a pull request, and retain all CI outcomes;
2. merge only after all checks pass, then require green main CI;
3. stage a new exact operations archive and perform one fresh Phase 3 attempt;
4. do not pull Delta, alter Caddy/DNS, or activate publicly until every earlier
   gate passes and separate authorization is recorded.
