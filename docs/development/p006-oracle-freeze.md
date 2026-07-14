# P006 Direct-stylo Oracle Freeze

## Purpose

P006 compares the future fixed R worker with an independent reference that calls
the locked `stylo` 0.7.71 distance functions directly. The reference is limited
to the declared whole-text synthetic fixture suite. It is not evidence of general
`stylo` parity, preprocessing parity, authorship accuracy, or production readiness.

## Fixture Boundary

- Suite: `tests/fixtures/stylo/p006-whole-text-v1/`
- Origin: project-authored synthetic integer counts
- Literary text: none
- License: CC0-1.0
- Inputs: complete base, changed-unknown canary, and culling boundaries
- Contract MFW range: 2 through 1,000
- Frozen v1 fixture MFW values: 3 through 6 only

Regenerate or verify the checked-in bytes with:

```bash
uv run python scripts/generate_p006_fixtures.py
uv run python scripts/generate_p006_fixtures.py --check
```

## Independence Rules

The oracle in `scripts/oracles/p006-direct-stylo-v1.R` must not source or import
the worker, the Python application, or a shared Delta calculation helper. It
independently implements known-only feature ranking, culling, relative
frequencies, means, sample standard deviations, and unknown projection. It then
calls only:

```r
stylo::dist.delta(z_scores, scale = FALSE)
stylo::dist.eder(z_scores, scale = FALSE)
stylo::dist.cosine(z_scores)
```

`perform.delta()` and `dist.wurzburg()` are forbidden for this protocol.

## Freeze Order

1. Commit the fixture, license, manifest, schema, generator, and independent R
   oracle before a worker implementation is compared.
2. Build the digest-pinned canonical Linux amd64 image.
3. Run the oracle twice with no network, a read-only root filesystem, fixed
   locale and timezone, and one BLAS thread.
4. Validate both runs against the input SHA-256 values and the scientific
   contract.
5. Require byte-identical run directories.
6. Commit the direct outputs, session record, environment identity, and checksum
   manifest as a separate descendant commit.
7. Remove the temporary write-enabled capture workflow after the freeze commit
   lands. This was completed after evidence commit `b5a842f`.
8. Only then implement and compare the worker.

The historical temporary workflow is available at source commit `7df1fdf`. It was
removed from the active branch after GitHub Actions run `29295419981` created
`provenance/evidence/P006/oracle-v1/`. Restoring a content-write workflow requires
a new explicit capture decision; normal CI is read-only.

## Acceptance Checks

`scripts/validate_p006_oracle_outputs.py` requires:

- every direct output to bind the exact canonical input hash;
- every result to pass the same fitting, cell, matrix, and outcome invariants as
  worker output;
- base and changed-unknown fixtures to have identical fitting artifacts;
- every known-known distance to remain exactly identical;
- at least one unknown-known distance to change;
- `canary_only` to remain outside ranking and selected features;
- the boundary fixture to retain four complete and three explicit
  not-enough-features fits.

The final checksum gate is:

```bash
cd provenance/evidence/P006/oracle-v1
sha256sum --check oracle-freeze.sha256
```

The durable repository gate additionally verifies the exact file set, canonical
metadata, historical source hashes, two-run snapshots, session record, input
binding, and scientific invariants:

```bash
uv run python scripts/validate_p006_frozen_oracle.py
```

The local macOS environment can parse and statically inspect the oracle but
cannot load `stylo` without XQuartz. Canonical numerical evidence therefore comes
only from the locked Linux capture.

The full passing identity and the three safely stopped capture attempts are retained
in `provenance/evidence/P006/oracle-freeze-validation.md` and
`provenance/runs/RUN-20260714-0001.json`.

## Post-freeze Method Audit

The first freeze remains immutable and inspectable, but it is not sufficient for
future worker acceptance. Every v1 document has `token_total=100`, so a worker that
incorrectly compares raw counts could escape this fixture. The only unknown document
is also the final row, which cannot detect an implementation that assumes position
instead of reading each document role. A strengthened v2 suite must vary document
lengths, place multiple unknown documents between known rows, and prove that the
raw-count counterfactual differs before any worker parity claim is evaluated.
The concrete strengthened design and read-only capture protocol are specified in
`docs/development/p006-oracle-v2.md`.
