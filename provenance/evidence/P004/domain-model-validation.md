# P004 Domain Model, Rights, Validation, and Determinism Evidence

## Scope

This checkpoint implements the first three ordered P004 foundations:

1. versioned domain models, controlled vocabularies, and generated JSON Schemas;
2. actionable purpose-aware validation with stable error codes and deterministic
   valid/invalid fixtures;
3. canonical inventory ordering, semantic hashing, and dependent-run invalidation.

P004 remains in progress. CSV round trips, the rights questionnaire, browser-state
integration, Corpus Review graphics, accessibility evidence, and human acceptance are
not claimed by this checkpoint.

## Implemented Contracts

- Immutable Pydantic records distinguish P003-validated files, scholarly assets,
  independent works, authors/contributors, editions, sources, and rights layers.
- P003 transient random storage identifiers are excluded. Exact file label and
  SHA-256 must match a stable `validated-for-intake` catalog projection before human
  mapping confirmation can succeed.
- Work first-publication chronology remains separate from analyzed-edition date;
  exact, approximate, range, and unknown assertions retain uncertainty.
- Overlapping uncertain date intervals form one conservative chronology point.
- Style Over Time remains exploratory below six independent works or three chronology
  points, and cannot report its minimum as met while any blocker remains. The report
  states that the threshold is not a sufficiency claim.
- Rights v1 remains unchanged at `asset-rights.schema.json`. The tri-state v2 contract
  is published separately at `asset-rights-v2.schema.json`.
- Upload, analysis, export, and public redistribution are independent tri-state
  actions. `verified_open` requires a license and evidence. Public redistribution
  requires every declared underlying rights layer to permit it and a separate human
  confirmation that the applicable rights chain was reviewed for completeness.
- Canonical inventory hashing sorts top-level and nested set-like collections, uses
  full canonical JSON as a duplicate-ID tie-breaker, excludes the volatile rights
  assessment timestamp, and changes when semantic metadata or rights change.
- Every validation issue contains severity, stable code, entity, field path, optional
  future CSV row, message, methodological reason, and correction guidance.
- JSON Schema is explicitly structural. Cross-record and cross-field semantics that
  Draft 2020-12 cannot express, including reversed date bounds, are accepted by the
  schema and then blocked by the deterministic semantic validator with stable codes.

The detailed engineering contract is retained in
`docs/development/p004-domain-model.md`.

## Deterministic Fixtures

- `tests/fixtures/p004/inventory-valid-text-proximity.json`
- `tests/fixtures/p004/inventory-invalid-cross-record.json`

The invalid fixture is structurally parseable but deliberately contains cross-record
problems. This distinction verifies that JSON shape acceptance cannot substitute for
scholarly relationship validation.

## Adversarial Review

The first independent review identified eight concerns:

1. public export considered only one rights record;
2. mapping confirmation was not tied to P003 label and hash evidence;
3. blocker-bearing records could satisfy the chronology minimum;
4. runtime and generated-schema cross-field rules diverged;
5. rights v1 was being overwritten instead of versioned;
6. duplicate identifiers could preserve input order inside the hash;
7. `verified_open` could be recorded without license or evidence;
8. schema snapshot equality was a circular oracle without independent negative cases.

All eight were accepted and repaired. A second independent review then found two
remaining P1 defects: duplicate P003 catalog order could change the validation report,
and three URL/range examples exposed an overstated runtime/schema parity assumption.
The catalog and all ID maps now use canonical ordering; matching considers every hash
under a duplicate label. Web-only source and rights-evidence constraints now reject
the cited URL cases in both layers. Reversed ranges are explicitly structural-schema
valid but semantic-validator blocked, because standard Draft 2020-12 cannot compare
two sibling numeric fields.

A final narrow re-review found no remaining P0, P1, or P2 defect and passed nine
focused probes. It retained two bounded residual risks: the direct reverse-order test
samples the validated-file collection while other duplicate-ID collections rely on
the same shared canonical helper, and the URL tests establish the cited cases rather
than proving equality for every possible URL grammar.

## Retained Failed Attempts

### Host `uv` command unavailable

An early targeted command used `uv run ruff ...` and exited `127` because `uv` was not
on the host shell PATH. The repository's canonical `.venv/bin/...` commands and
`./scripts/verify.sh` were used instead. This was an invocation error, not a code pass.

### Formatting gate

The first full `./scripts/verify.sh` stopped because Ruff reported four files that
would be reformatted. Ruff formatting was applied and the complete gate was rerun.
A later post-review edit repeated the same stop for `inventory.py`; it was formatted
and the full gate was rerun rather than treating the partial execution as evidence.

### Runtime-boundary URI false positive

The next full verification passed 298 tests but failed the no-remote-endpoint source
scan because the JSON Schema Draft identifier contained a literal URL. The identifier
is non-executable metadata, but the safety test was not weakened. The source literal
was split so application code still contains no declared remote endpoint; the next
complete run passed.

### First reviewer budget exhaustion

One 30,000-token independent review exhausted its budget on mandatory parent-vault
startup reading and made no source finding. It was closed without treating silence as
approval. A 60,000-token focused reviewer then completed the adversarial audit above.

### Guessed record-check script did not exist

A post-verification convenience command attempted
`.venv/bin/python scripts/check_records.py` and exited `2`; that script is not part of
the repository. The actual record and schema gates were then run through their
canonical pytest targets and passed 31/31. The earlier complete verification had
already passed the repository's `records-ok` gate.

## Final Local Verification

Command:

```text
./scripts/verify.sh
```

Result on the stable pre-commit snapshot:

- 318 tests passed;
- 1,510 measured statements, 0 missed;
- 392 measured branches, 0 missed or partial;
- Ruff formatting and lint passed;
- strict mypy passed for 15 source files;
- software metadata, provenance records, repository scan, supply-chain checks, and
  deferred R namespace lock all passed;
- no scientific analysis or browser UI was executed by this checkpoint.

## Remaining Boundary

This evidence does not pass the full P004 Ticket. Parameters remain locked. No
scientific chart, stylometric result, legal determination, raw-text export, permanent
storage, runtime AI, or deployment claim is introduced.

Implementation checkpoint: `e5b269f1614938cbf2a7066fa322d6b55d4d47d6`.

## GitHub CI

The pushed linkage snapshot `45921e13ce1d64603ddd7d9619b7fb8056a22f20`
passed GitHub Actions run `29170767298`:

- `verify`: success in 2m05s, including full-history checkout, locked Python/R
  environments, source and record verification, SBOM generation, and dependency audit;
- `container`: success in 2m37s for the canonical Linux amd64 image.

Run URL: `https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29170767298`.
