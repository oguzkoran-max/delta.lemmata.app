# P006 Adversarial Oracle v2

## Purpose

Oracle v2 strengthens the immutable v1 reference before any fixed worker is
implemented. V1 correctly records its declared `stylo` calculation, but equal
document totals and one final-position unknown row cannot expose two plausible
implementation defects: using raw counts instead of relative frequencies, or
inferring document role from row position.

V2 is project-authored CC0 synthetic data. It contains no literary text and does
not extend the claim beyond the named whole-text fixtures in the locked
environment.

## Document Topology

The base and canary requests use this exact order:

| Row | Role | Token total | Semantic fixture identity |
| --- | --- | ---: | --- |
| 1 | known | 80 | known-1 |
| 2 | unknown | 150 | unknown-a |
| 3 | known | 120 | known-2 |
| 4 | known | 200 | known-3 |
| 5 | unknown | 240 | unknown-b |
| 6 | known | 320 | known-4 |

The final row is deliberately known. A third request contains the same six
documents in a different order and preserves each explicit role, count vector,
token total, and opaque identity.

## Feature Design

The candidate inventory contains two unknown-only canaries and six known-derived
features. Known aggregate ranking is fixed as follows:

| Rank | Feature | Known count | Known-document presence |
| ---: | --- | ---: | ---: |
| 1 | beta | 146 | 4 |
| 2 | alpha | 114 | 4 |
| 3 | gamma | 86 | 4 |
| 4 | delta | 34 | 3 |
| 5 | epsilon | 16 | 3 |
| 6 | zeta | 8 | 2 |

`unknown_a_only` and `unknown_b_only` must never enter ranking, culling,
selection, means, or standard deviations. Four complete fits cover `(MFW,
culling)` values `(6,0)`, `(5,50)`, `(4,75)`, and `(3,100)` for Classic Delta,
Eder's Delta, and Cosine Delta.

## Adversarial Pairs

- `normalization-base`: unequal totals and two interleaved unknown rows.
- `normalization-canary`: known rows are byte-equivalent by opaque document ID;
  both unknown count vectors change while their identities and totals remain fixed.
- `order-permutation`: all base documents are unchanged but reordered. Numerical
  comparisons reindex matrices by document ID, never by row position.

For every fit and all three distance families, a local formula-level
counterfactual calculates the result that would arise if normalization were
skipped. The minimum known-known gap is safely above the `1e-3` design threshold:

| Distance | Minimum gap across four fits | Maximum gap |
| --- | ---: | ---: |
| Classic Delta | 0.522862167897 | 0.732170088485 |
| Eder's Delta | 2.359863334621 | 2.883020899143 |
| Cosine Delta | 0.799979768369 | 1.220034209071 |

These values are fixture-discrimination checks, not scientific tolerances. Worker
parity remains governed by ADR-0013: exact ordered features, matrix tolerance
`1e-6`, structural tolerance `1e-12`, and tie threshold `1e-12`.

## Capture Protocol

The temporary `p006-oracle-v2-capture` job in `.github/workflows/ci.yml` runs only
for `workflow_dispatch`; the workflow has `contents: read`. Reusing the CI workflow
is necessary because GitHub permits manual dispatch only for workflow files already
registered on the default branch. Checkout credentials are not persisted. The job
restores the locked environment, verifies the source, builds the digest-pinned Linux
amd64 image, runs the direct-`stylo` oracle twice with no network and a read-only
root filesystem, validates both directories, and uploads a seven-day candidate
artifact.

The workflow cannot commit or push. Publication is a separate local step:

1. Download the artifact for the exact source run.
2. Verify its artifact digest, internal checksum, source hashes, fixture design,
   output semantics, and two-run identity.
3. Copy only the validated package to `provenance/evidence/P006/oracle-v2/`.
4. Commit and push it through the normal branch and CI path.
5. Bind source commit, capture run, artifact identity, publication commit, input
   hashes, output hashes, package versions, image identity, and limitations in a
   native Run record.
6. Remove the temporary manual capture job from normal CI after publication; retain
   it in the exact source commit for replay.

## Acceptance Boundary

V2 can establish that the named reference is sensitive to normalization, explicit
roles, unknown leakage, and row permutation. It still does not establish fixed
worker parity, raw-text preprocessing parity, authorship accuracy, benchmark
validity, public workflow readiness, production isolation, or general
reproducibility. Those claims remain gated by the rest of P006 and later tickets.
