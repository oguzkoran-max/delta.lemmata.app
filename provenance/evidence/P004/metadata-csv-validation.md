# P004 Metadata CSV Validation Evidence

**Status:** Local implementation candidate passed; exact-commit Run, GitHub CI,
browser integration, and human acceptance remain pending

**Date:** 2026-07-12

**Ticket:** `P004`

## Scope

This checkpoint implements and tests the versioned bulk-metadata representation for
`corpus-inventory-v1`. It does not implement the Streamlit Describe/Review workflow,
scientific analysis, runtime AI, production retention, or final P004 acceptance.

The candidate contains:

- a 58-column `corpus-metadata-csv-v1` contract below the unchanged P003 64-column
  limit;
- one analyzed work per row;
- compact standard JSON only for authority identifiers, additional contributors,
  distinct rights-source records, and rights records;
- an executable field dictionary and an exact ordered Draft 2020-12 schema;
- secure import, deterministic export, blank/valid/invalid fixtures, and actionable
  row-and-field diagnostics;
- canonical semantic payload, inventory-hash, and canonical re-export round trips;
- fail-closed public redistribution requiring verified-open status, export
  permission, license, jurisdiction, and URL evidence.

## Retained Attempts

The following attempts were not silently represented as passing evidence:

1. An initial independent architecture-agent request could not start because its
   external usage quota was exhausted. No result is attributed to that attempt.
2. The first full verification after the final security patch stopped because Ruff
   would reformat three files. The canonical formatter was applied.
3. The next full verification passed all 385 tests but correctly failed the project's
   100% coverage gate at 99.51%. Five focused branch tests were added.
4. The final local verification passed 390 tests and every project gate at 100%
   measured statement and branch coverage.

The GitHub failure email for commit prefix `93c9f50` referred to an earlier
shallow-history provenance failure. GitHub's authoritative run history showed that
the later pre-CSV snapshot `a520448` passed run `29170868695`. That historical green
run is not presented as verification of this uncommitted CSV candidate.

## Independent Review Findings and Resolutions

### Provenance overclaim

An adversarial provenance reviewer found that the threat matrix used verified-style
language before an exact-commit Run existed. The status was changed to
`implemented; verification pending`. It must not be raised until the implementation
is committed and rerun from the recorded tree.

### Nested JSON security

A security reviewer found that whole-cell P003 checks could miss unsafe strings after
JSON decoding. Import and generated export now recursively inspect decoded strings
and keys for formula prefixes, HTML, newlines, path-like text, Unicode normalization,
BOMs, bidi overrides, and control characters. Duplicate JSON keys, non-standard
constants, excessive nesting, ambiguous identifiers, and unsafe generated values
fail closed. Regression tests cover each route.

### Distinct rights-source loss

A FAIR/schema reviewer demonstrated a domain-valid rights dependency whose
`source_id` differed from the analyzed text's acquisition source. The original
57-column draft dropped that source during export/import. The contract now has the
58th `rights_sources_json` capability: complete dependency source records are
exported, identity-merged on import, and required to match the rights references.
A separate-source multi-layer inventory now round-trips with equal model, canonical
payload, and inventory hash.

### Statement-only public redistribution

The reviewer demonstrated that a statement-only `verified_open` record could open
the public-redistribution helper. Model validation and the generated JSON Schema now
require jurisdiction and at least one HTTP(S) URL evidence record whenever public
redistribution is permitted. A statement may document other rights decisions but
cannot by itself open the public gate.

### External schema drift

The Pydantic field-dictionary model enforced ordered consecutive positions and
unique names, while its first generated JSON Schema did not. The public schema now
uses exact ordered `prefixItems`, fixed item count, and per-position `const` values
for all v1 names and positions. Mutated duplicate-name and duplicate-position
dictionaries fail external JSON Schema validation.

### Wrong actionable field names

Broad model-validation catches previously attributed an invalid language to
`work_id` and an empty rights array to `asset_id`. Validation locations are now
mapped to the actual CSV column, and an empty required rights array fails directly at
`rights_records_json`. Focused tests cover date, term, author, work, source, asset,
and rights fields without echoing rejected values.

### Independent re-review

The same FAIR/schema reviewer reran each original reproduction against the corrected
working tree with a read-only 20k-token ceiling. All four findings were reported
fixed, the previous distinct-source case returned an unblocked equal inventory and
equal hash, statement-only public redistribution failed at both model and CSV layers,
the external schema rejected both mutations, and field diagnostics named the correct
columns. The reviewer passed 172 related tests and reported no new P0, P1, or P2
regression in this bounded follow-up. No files were changed by the reviewer.

## Local Verification

Final command:

```text
./scripts/verify.sh
```

Final result:

```text
390 passed
2097 statements, 542 branches, 100% coverage
metadata-ok version=0.0.0.dev0
records-ok count=49
repository-scan-ok
r-lock-ok stylo-namespace-load-deferred
verify-ok
```

The gate also passed Ruff formatting/linting, strict mypy, generated-schema checks,
metadata consistency, provenance-record integrity, repository scanning, supply-chain
tests, and the locked R 4.5.2 / stylo 0.7.71 environment.

## Evidence Paths

- `decisions/ADR-0011-versioned-metadata-csv.md`
- `docs/development/p004-metadata-csv.md`
- `docs/security/threat-model.md`
- `src/delta_lemmata/metadata_csv.py`
- `src/delta_lemmata/metadata_csv_models.py`
- `src/delta_lemmata/data/corpus-metadata-fields-v1.json`
- `schemas/corpus-metadata-field-dictionary.schema.json`
- `templates/corpus-metadata-v1.csv`
- `tests/fixtures/p004/metadata-valid-v1.csv`
- `tests/fixtures/p004/metadata-invalid-domain-v1.csv`
- `tests/test_metadata_csv.py`
- `tests/test_corpus.py`
- `tests/test_schemas.py`

## Remaining Gates

1. Commit the exact implementation tree and record its immutable Git SHA.
2. Rerun `./scripts/verify.sh` from that exact committed tree and create a reciprocal
   P004 Run record.
3. Push the branch and require green GitHub verify, audit/SBOM, and Linux container
   jobs.
4. Implement and browser-test the English-only rights questionnaire, guided
   metadata editor, and accessible Corpus Review visuals.
5. Obtain Oğuz Koran's terminology/workflow acceptance before closing any P004
   acceptance criterion.
