# P006 Independent Direct-stylo Oracle Freeze Validation

## Scope

This checkpoint freezes an independent `stylo` reference before the fixed P006
worker exists. It covers only the named CC0 whole-text synthetic fixture suite and
the locked Linux amd64 environment. It does not establish worker parity, raw-text
preprocessing parity, authorship accuracy, benchmark validity, public analysis,
production isolation, or general reproducibility.

## Bound Identities

- Method decision: `HD-20260713-0002`
- Source commit: `7df1fdf754ecfb3a0b84835dc7f368c481f333f1`
- Capture run: GitHub Actions `29295419981`, job `86967691791`
- Normal source CI: GitHub Actions `29295419945`
- Evidence commit: `b5a842fdee5456c7f5f9d0397c0f5a2f7d7a336f`
- Native Run record: `RUN-20260714-0001`
- Built image: `sha256:77e703d85465eecb0c58958a037e7f0f4e3e64189499204e2dbed3af4cefdd07`
- Base image: digest-pinned `rocker/r-ver:4.5.2`
- Scientific environment: R 4.5.2, `stylo` 0.7.71, `jsonlite` 2.0.0,
  `C.UTF-8`, UTC, seed 20260713, Linux x86_64

## Transparent Failure Sequence

No failed attempt committed reference evidence.

1. Run `29294170144` stopped at the environment gate because the first oracle
   error was too broad to identify the unavailable namespace safely.
2. Run `29294530963` identified `ORACLE_JSONLITE_NAMESPACE_INVALID`. The locked
   `renv` library linked into a root-owned cache that the unprivileged runtime
   user could not traverse. The image now exposes that cache read-only to the
   runtime user and proves both locked namespaces during image construction.
3. Run `29294900147` completed both calculations but stopped before freeze because
   public synthetic outputs were written as private `0600` files and the separate
   host verifier could not read them. Oracle evidence now uses `0644`; private
   research workspace policy is unchanged.
4. Run `29295419981` passed source verification, image construction, two no-network
   oracle executions, semantic validation, byte comparison, checksum generation,
   repository scanning, and the evidence commit.

These failures are infrastructure and evidence-transfer findings. They are not
failed scientific comparisons because the fixed worker had not yet been built or
compared.

## Passing Invariants

- Three canonical fixture inputs bind exact SHA-256 values and a CC0-1.0 license.
- Two independent oracle directories contain the same four filenames, byte counts,
  and SHA-256 values.
- The changed unknown row leaves feature ranking, selected features, fitting means,
  standard deviations, and every known-known distance exactly unchanged.
- The unknown change affects at least one unknown-known distance and the
  `canary_only` feature never enters known-derived fitting.
- Classic Delta, Eder's Delta, and Cosine Delta call the locked `stylo` functions
  directly without a worker or shared distance helper.
- The boundary fixture retains exactly four complete cells and three explicit
  `not_enough_features` cells.
- The retained package records observed package versions, the `renv` lockfile hash,
  locale, timezone, RNG, BLAS, LAPACK, base image, built image ID, source commit,
  source hashes, input hashes, and output hashes. It does not retain the built image,
  CRAN archives, or a fully pinned APT package set.

## Durable Verification

`scripts/validate_p006_frozen_oracle.py` rejects an altered file set, checksum,
canonical metadata, historical source binding, environment identity, run snapshot,
input binding, session record, or scientific invariant. It also requires evidence
commit `b5a842f` to have source commit `7df1fdf` as its sole parent, add exactly the
six declared evidence files, and contain bytes identical to the retained working
tree. It is part of the normal `scripts/verify.sh` gate. The temporary content-write
workflow was manually disabled on GitHub immediately after independent review and
removed from the active branch after the bot-authored evidence commit.

## Acceptance Boundary

Post-freeze independent method review found that every v1 document has
`token_total=100` and that the sole unknown document is always the final row. The
retained v1 output therefore cannot detect a worker that skips relative-frequency
normalization or infers role from position. V1 remains a valid record of its declared
calculation, but it is not the final parity oracle. A v2 suite must vary document
length, interleave multiple unknown rows, and prove separation from a raw-count
counterfactual before worker implementation is accepted.

P006-AC-01 and P006-AC-05 remain the only passed ticket criteria. P006-AC-02 through
AC-04 and AC-06 through AC-08 remain pending until the strengthened oracle, fixed
worker, adapter, parity/leakage reports, crash-safe scientific artifact handoff,
exact replay, and final audits pass.
