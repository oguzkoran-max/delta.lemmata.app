# P006 Adversarial Oracle v2 Freeze Validation

## Result

The adversarial whole-text direct-`stylo` oracle v2 is checksum-frozen and
independently revalidated. It is suitable as the fixed reference for the next P006
worker-comparison step. This result is not fixed-worker parity, P006 acceptance,
raw-text preprocessing parity, benchmark validity, or production validation.

## Immutable Chain

- Exact source: `c6a07e1b62440d56feabf76fd7c58e4b58b63477`
- Normal source CI: run `29299641848`; verify job `86980527225`; container job
  `86980527228`
- Read-only capture: run `29299793944`; capture job `86980971428`; verify job
  `86980971766`; container job `86980971385`
- Log transport: `p006-log-transport-v1`; 137 chunks; 78,355 envelope bytes;
  SHA-256 `c94f84b3eb341fc0b16e8bee134f32841080f24ac35d333c838950501db4216c`
- Evidence-only commit: `42fe09b690d953fbcf45fcf48fa6d8f462fb8251`
- Publication CI: run `29300077689`; verify job `86981809318`; container job
  `86981809317`
- Native Run: `RUN-20260714-0002`

The evidence commit has the source commit as its only parent and adds exactly six
files under `provenance/evidence/P006/oracle-v2/`. No code, documentation, or prior
evidence changed in that commit.

## Environment

- Linux amd64, R 4.5.2, `stylo` 0.7.71, `jsonlite` 2.0.0
- Digest-pinned `rocker/r-ver:4.5.2` base image
- Built image ID `sha256:73bbf04a2eacd059f1b1b9f319f3645c0a1d552aafb4ac0cbe4a0129d182eabc`
- `C.UTF-8` collation and character locale, `LC_NUMERIC=C`, UTC
- Mersenne-Twister / Inversion / Rejection RNG profile, seed 20260713
- Both scientific executions: no network, read-only root, dropped capabilities,
  no-new-privileges, bounded process/memory/CPU, and fixed single-thread variables

## Scientific Checks

The direct reference ran twice and all four files in each run were byte-identical.
The retained three outputs passed the suite-v2 validator, which checks:

- six unequal document totals and two explicitly interleaved unknown documents;
- a known final row, preventing last-row role inference;
- known-only MFW ranking, culling, means, standard deviations, and feature selection;
- unchanged known fitting artifacts and known-known distances when both unknowns
  change;
- active unknown-distance changes for Classic, Eder, and Cosine Delta;
- full matrix equivariance under a document-order permutation, reindexed by opaque
  document ID;
- exact agreement with independent Python formulas at `1e-10` for the named
  fixtures; and
- separation from a raw-count counterfactual by more than `1e-3` for every complete
  fit and distance family.

The `1e-3` value is a fixture-activation threshold, not the worker-parity tolerance.
ADR-0013 retains exact ordered features, `1e-6` matrix tolerance, `1e-12`
structural tolerance, and `1e-12` tie grouping for the coming worker comparison.

## Transport and Failure Record

Run `29298977429` previously completed both oracle executions and package validation,
but GitHub rejected only the final artifact upload because account artifact storage
was full. The ephemeral package was not retained and no evidence was published from
that run.

The successful capture used no artifact service and no repository write permission.
It emitted a canonical JSON envelope with per-file size/hash records as numbered
base64 chunks in the job log. Local extraction required one begin/end pair, every
numbered chunk, the envelope digest, canonical JSON, unique safe paths, per-file
digests, and the internal checksum before creating the destination.

The first local destination `/tmp/...` was rejected because `/tmp` is a symlink on
macOS. Repeating the same extraction under the real `/private/tmp` parent passed.
The path policy was not weakened.

## Verification Commands

```text
./scripts/verify.sh
gh run watch 29299641848 --exit-status
gh run watch 29299793944 --exit-status
gh run view 29299793944 --job 86980971428 --log
python scripts/p006_log_transport.py extract <job-log> <new-destination>
shasum -a 256 -c oracle-freeze.sha256
python scripts/validate_p006_frozen_oracle_v2.py
gh run watch 29300077689 --exit-status
```

The source checkpoint passed 1,103 tests, 7,247 measured statements, 1,902 measured
branches, and 100% coverage. After the durable v2 validator, Run link, and temporary
capture-job removal were included, the final local closure passed 1,104 tests, all
7,247 measured statements and 1,902 measured branches at 100% coverage, 82
provenance records, repository scanning, oracle parsing, and the locked R gate.

## Remaining Boundary

The temporary capture job is removed from current CI after publication and remains
replayable from source commit `c6a07e1`. The next P006 task is the fixed
`Rscript --vanilla` worker and Python adapter, followed by direct comparison against
this reference. Public analysis remains locked.
