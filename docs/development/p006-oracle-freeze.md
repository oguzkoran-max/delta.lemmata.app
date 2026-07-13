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
- MFW range: 2 through 1,000 under the closed v1 contract

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
   lands.
8. Only then implement and compare the worker.

The temporary workflow is `.github/workflows/p006-oracle-freeze.yml`. A bot run
creates `provenance/evidence/P006/oracle-v1/`; bot-authored follow-up pushes are
excluded from the capture job to prevent a loop.

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

The local macOS environment can parse and statically inspect the oracle but
cannot load `stylo` without XQuartz. Canonical numerical evidence therefore comes
only from the locked Linux capture.
