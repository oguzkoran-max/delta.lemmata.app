# P006 Oracle v2 Freeze Checkpoint

## State

- Source `c6a07e1` passed local and normal Linux CI gates.
- Capture run `29299793944` ran the direct oracle twice without network and emitted
  a checksum-bound job-log envelope.
- Envelope SHA-256 is `c94f84b3eb341fc0b16e8bee134f32841080f24ac35d333c838950501db4216c`.
- Evidence-only commit `42fe09b` adds six files and has `c6a07e1` as its sole parent.
- Publication CI `29300077689` passed.
- `RUN-20260714-0002` binds environment, source, capture, transport, evidence, and
  publication identifiers.
- Current verification includes `validate_p006_frozen_oracle_v2.py`; the temporary
  capture job is removed from current CI.
- Final local closure passed 1,104 tests, 100% of 7,247 measured statements and
  1,902 measured branches, and all 82 provenance records.

## Scientific Meaning

V2 closes the fixture-design weaknesses found in v1: unequal totals activate
normalization checks, two interleaved unknowns activate leakage checks, a known final
row defeats positional role inference, and a full permutation checks ID-based
equivariance. Formula-level checks cover Classic, Eder, and Cosine Delta across all
four complete fits.

This freezes the independent reference only. It does not show that a Delta worker
matches the reference and does not pass any additional P006 acceptance criterion by
itself.

## Next Step

Implement the fixed trusted `Rscript --vanilla` worker and Python adapter. Keep raw
text preprocessing in P007, public workflow activation in P008, and broader leakage
and benchmark claims in P010/P011.
