# P006 Fixed-Worker Retained Evidence Validation

## Result

The fixed R `stylo` worker evidence package is retained, checksum-bound, and
offline revalidated from its exact outputs and exact source commit. P006-AC-07 and
P006-AC-08 are satisfied for the named synthetic whole-text fixtures and the
recorded environments. P006 is complete within that boundary. This does not
establish raw-text preprocessing parity, benchmark accuracy, literary-corpus
validity, public workflow behavior, production isolation, or a general `stylo`
parity claim.

## Immutable Chain

- Exact capture source: `79cb268a348a35c9622efe52cd3a09a829a09b1f`
- Normal source CI: run `29339965417`; verify job `87108811962`; container job
  `87108811961`
- Read-only capture: run `29340236382`; capture job `87110647201`; verify job
  `87109759192`; container job `87109759084`
- Built image ID:
  `sha256:ecc14f1b5f89228f5d3e14fc00b011ca6899199a521750b7fe8b29d34efbd75e`
- Raw capture-job log SHA-256:
  `1390711bf9db38e38ef888b192c58d7870567d58cb41ed20c3b2edbf6d45fab5`
- Transport envelope SHA-256:
  `99a114ca1f02fde0ac2bf4d9dd9dd4d4cc9d1ee6d64a15759fb5c13f23f27af9`
- Evidence-only commit: `7359cbe305743623db45777c3f4be059c847a74c`
- Publication CI: run `29347937295`; verify job `87136433154`; container job
  `87136433144`
- Native Run: `RUN-20260714-0004`
- Durable audit commit: `d676d90aa1bebea6197f2f18b5f988c8e6d11794`
- Audit CI: run `29350106890`; verify job `87143854938`; container job
  `87143854913`
- Exact-commit clean-clone Run: `RUN-20260714-0005`

The evidence commit has the exact capture source as its sole parent. It adds the
18-file package under `provenance/evidence/P006/worker-v1/` and one external
transport receipt. It changes no source code, workflow, ticket, or narrative
documentation.

## Captured Environment and Boundary

- Linux amd64; R 4.5.2; `stylo` 0.7.71; `jsonlite` 2.0.0
- `C.UTF-8` character and collation locale; `LC_NUMERIC=C`; UTC
- Mersenne-Twister / Inversion / Rejection RNG profile; seed 20260713
- No network, read-only root filesystem, all capabilities dropped, and
  `no-new-privileges`
- Two GiB outer capture-container memory and the separately retained worker
  profile: 30 CPU seconds, 60 wall seconds, one GiB memory, eight processes, and
  two seconds termination grace
- Read-only source mount and exact byte comparison between the repository worker
  script and the worker script inside the built image

The two-GiB outer container limit is capture orchestration headroom. It does not
replace or weaken the worker's separately enforced one-GiB scientific-process
limit.

## Recomputed Checks

The versioned offline validator re-read the persisted package rather than trusting
the reports produced during capture. It confirmed:

- exactly 18 expected package files and their internal checksum manifest;
- four named fixture executions across the retained v1 boundary suite and v2
  parity suite;
- exact direct-reference bytes from the checksum-frozen oracles;
- exact feature inventories, distance matrices within `1e-6`, and tie-aware
  nearest-neighbor groups for the declared v2 fixtures;
- changed-unknown invariance for known fitting artifacts and known-known
  distances, plus active unknown-distance changes;
- document-order permutation equivariance by opaque document ID;
- three expected `not_enough_features` cells retained as non-complete cells;
- twelve deliberately induced literal `failed` cells retained as failed, rather
  than rewritten as successful or insufficient-feature results;
- a fixed-adapter injection probe with no observed shell or code channel; and
- complete session, source, image, fixture, worker, lockfile, locale, timezone,
  RNG, package, and limit-profile bindings.

The checksum-bound GitHub job-log transport is an integrity-binding transport. It
is not described as a cryptographic GitHub attestation.

## Diagnostic Failures Retained

Two manual dispatches failed before evidence publication and produced no accepted
package:

1. Run `29333474110` at `d57431b` stopped during the first worker execution with a
   generic execution rejection. The next change separated outer capture headroom
   from the worker limit and preserved valid scientific `failed` envelopes instead
   of treating them as successful analysis.
2. Run `29335197916` at `bb9f05e` exposed the narrower diagnostic
   `limit_exceeded_cpu`. The cause was `renv` attempting lock, sandbox, or
   synchronized-state work in a read-only runtime. Source `79cb268` disabled those
   runtime mutations while retaining the same R, `stylo`, locale, seed, methods,
   fixtures, tolerances, and worker limits.

These failures are part of the development record. They are not scientific result
cells and are not counted as successful captures.

## Verification Commands

```text
./scripts/verify.sh
gh run watch 29339965417 --exit-status
gh run watch 29340236382 --exit-status
gh run view 29340236382 --job 87110647201 --log
python scripts/p006_log_transport.py extract p006-worker-job.log p006-worker-extracted --checksum-manifest worker-evidence.sha256
python scripts/validate_p006_worker_evidence.py p006-worker-extracted --source-commit 79cb268a348a35c9622efe52cd3a09a829a09b1f --image-id sha256:ecc14f1b5f89228f5d3e14fc00b011ca6899199a521750b7fe8b29d34efbd75e --github-run-id 29340236382 --github-run-attempt 1
gh run watch 29347937295 --exit-status
python scripts/validate_p006_worker_evidence.py
set -eu
clean_root=$(mktemp -d "${TMPDIR:-/tmp}/delta-p006-clean.XXXXXX")
git clone --no-hardlinks --no-checkout https://github.com/oguzkoran-max/delta.lemmata.app.git "$clean_root/repository"
cd "$clean_root/repository"
git checkout --detach d676d90aa1bebea6197f2f18b5f988c8e6d11794
./scripts/bootstrap.sh
./scripts/verify.sh
test -z "$(git status --porcelain --untracked-files=all)"
gh run watch 29350106890 --exit-status
```

The final audit tree passed 1,246 local tests with one canonical-Linux-only skip,
100% of 7,768 measured statements and 2,080 measured branches, metadata and 84
record checks, repository scanning, all frozen-evidence validators, R parsing, and
the locked R environment gate. The same exact commit passed all 1,247 tests,
worker parity, scientific handoff, 100% measured coverage, SBOM/dependency/secret
checks, and canonical Linux amd64 image construction in GitHub-hosted Ubuntu CI.
It was then fetched from the GitHub origin into a fresh remote no-hardlinks clone,
restored from committed Python and R lockfiles, reverified, and left a clean
post-run worktree.

## Closure Boundary

The one-time `p006-worker-capture` job is removed after evidence publication and a
regression test requires it to remain absent. The retained package remains
replayable from source commit `79cb268`. Public upload-to-analysis, preprocessing,
benchmark calibration, stability labels, FAIR run export, Pinocchio, and production
deployment remain locked to P007-P015. CE-04 remains fixture-local until P007, and
CE-07 remains limited to worker-level changed-unknown fitting invariance until
P010 and P011.
