# P004 Versioned Metadata CSV Contract

**Status:** Exact-commit implementation and GitHub CI verified; browser integration and human acceptance remain pending

**Ticket:** `P004`

**Date:** 2026-07-12

## 1. Purpose and Boundary

`corpus-metadata-csv-v1` is the editable spreadsheet representation of a P004
corpus inventory. It is intended for bulk metadata entry and transparent exchange.
The guided on-screen editor remains the beginner path; both surfaces build the same
`corpus-inventory-v1` model.

The CSV never replaces P003. Import accepts untrusted bytes, runs the unchanged P003
CSV checks first, and only then parses scholarly metadata. File label, content hash,
intake profile, and intake status must match the separately supplied P003 catalog.
No source text is retained in the CSV result or its diagnostics.

## 2. Representation Decision

The contract uses one row per analyzed work and 58 fixed columns. This is below the
P003 limit of 64 columns. Normal identity, chronology, classification, edition,
source, normalization, confirmation, and intake values remain ordinary spreadsheet
columns.

Only four genuinely one-to-many structures use compact JSON arrays:

- `primary_author_authorities_json`
- `additional_contributors_json`
- `rights_sources_json`
- `rights_records_json`

An additional contributor object contains `author_id`, `display_name`, `kind`,
`role`, and `authority_identifiers`. The rights-source array preserves complete
`SourceRecord` objects when a license or permission source differs from the analyzed
text's acquisition source. The rights array contains complete `asset-rights-v2`
records. JSON is parsed with the standard JSON parser; Delta does not use custom
delimiters or split scholarly values on punctuation.

Two alternatives were rejected:

- A multi-table CSV bundle would model relationships cleanly, but P003 permits one
  optional metadata CSV and the accepted UI is a single-upload workflow.
- A long `record_type` table could represent every entity independently, but it
  would make ordinary spreadsheet editing depend on sparse polymorphic rows and
  would be harder to teach.

The selected hybrid preserves common-case readability while retaining multiple
contributors, roles, authority identifiers, rights layers, permissions, evidence,
and assessment provenance.

## 3. Version and Field Dictionary

Every row declares all four corpus-level values:

```text
csv_schema_version = corpus-metadata-csv-v1
inventory_schema_version = corpus-inventory-v1
vocabulary_profile = corpus-vocabularies-v1
purpose = text_proximity | group_comparison | style_over_time
```

Rows that disagree about these values are rejected. Header order may change during
spreadsheet editing, but names must match the versioned dictionary exactly. Export
always restores canonical column order.

The machine-readable field dictionary is:

`src/delta_lemmata/data/corpus-metadata-fields-v1.json`

Its generated Draft 2020-12 schema is:

`schemas/corpus-metadata-field-dictionary.schema.json`

Each entry records position, section, requirement level, value format, short
definition, methodological reason, example, and any finite allowed-value list. The
same loaded dictionary defines the parser's 58-column header. Its public JSON Schema
also fixes every v1 position and name with ordered `prefixItems`, preventing Python
and non-Python consumers from accepting different dictionary structures.

## 4. Template Behavior

`metadata_csv_template()` receives the stable P003 file catalog and creates one row
per validated TXT. It pre-fills only technical values that are already known:

- exact file label and SHA-256;
- intake profile and status;
- readable technical identifier proposals derived from the label plus hash prefix;
- explicit Unknown classification/date states;
- empty JSON arrays;
- `mapping_confirmed = false` and `rights_chain_confirmed = false`.

It does not guess title, language, author, edition, source, dates, rights, or legal
status. The checked-in example is `templates/corpus-metadata-v1.csv`.

## 5. Import and Validation

`import_metadata_csv()` has three ordered gates:

1. P003 validates bytes, UTF-8/NFC, size, row and column limits, formula prefixes,
   HTML, newlines, and path-like cells.
2. The P004 parser validates headers, required cells, fixed versions, exact file
   mapping, typed scalar values, JSON arrays, recursively decoded JSON strings, and
   repeated embedded identities. Unicode-escaped formulas, HTML, newlines, paths,
   controls, BOMs, and bidi overrides are checked against the same P003 cell policy
   after JSON decoding. Duplicate JSON keys, non-standard numeric constants, and
   excessive nesting fail closed.
3. `validate_inventory()` applies cross-record and purpose-aware domain rules.

Parser failures return `MetadataCsvImportResult` with no partial inventory. Each
`MetadataCsvIssue` contains a stable code, CSV row number, field name, what is wrong,
why it matters, and how to correct it. It never echoes the rejected cell value.

When parsing succeeds, the result retains the inventory even if the domain report is
blocked. Domain issues receive their originating CSV row where one exists. This is
how duplicate work identifiers, reversed date ranges, unknown controlled terms,
unconfirmed mappings, and other cross-record problems remain correctable rather than
becoming generic parse failures.

## 6. Canonical Export and Round Trip

`export_metadata_csv()` resolves all referenced authors, works, editions, sources,
validated files, rights dependency sources, and rights records, then writes
deterministic rows and compact JSON. Duplicate stable identifiers, unresolved
references, or inventory records that this one-row-per-work representation would
silently omit fail closed because selecting or dropping one record would change
scholarship.

Generated CSV is submitted to P003 again. Nested JSON strings are also checked before
serialization, because a JSON array prefix would otherwise hide a formula-like inner
value from a whole-cell prefix test. An unsafe title, citation, nested JSON value, or
other cell therefore cannot be exported by smuggling it around the intake policy.
There is no reversible escaping scheme that weakens the P003 injection boundary.

For a valid representable inventory, set-like contributor, authority, dependency,
and evidence order is canonicalized. The acceptance invariant is semantic rather
than UI-tuple order:

```text
canonical_inventory_payload(imported) == canonical_inventory_payload(original)
inventory_sha256(imported) == inventory_sha256(original)
export(imported) == export(original)
```

Top-level ordering and CSV row order are canonicalized. The full rights assessment
timestamp is retained even though that timestamp is intentionally excluded from the
semantic inventory hash. Canonically ordered fixtures also retain full model equality,
but arbitrary pre-export UI ordering is not a scholarly datum and is not promised.

## 7. Evidence

- `tests/test_metadata_csv.py`
- `tests/fixtures/p004/metadata-valid-v1.csv`
- `tests/fixtures/p004/metadata-invalid-domain-v1.csv`
- `templates/corpus-metadata-v1.csv`
- `src/delta_lemmata/data/corpus-metadata-fields-v1.json`
- `schemas/corpus-metadata-field-dictionary.schema.json`

The tests cover exact round trips, multiple contributors, authority identifiers,
multiple rights layers with distinct source records, canonical header and row
behavior, malformed JSON, missing values, version conflicts, unmatched labels, hash
mismatch, P003 injection rejection, statement-only public-rights rejection,
embedded-identity conflict, duplicate work IDs, reversed dates, unknown controlled
values, exact external dictionary-schema order, and content-free error output.

## 8. Deferred Work

The CSV contract does not yet connect to Streamlit session state. P004 still requires
the rights questionnaire mapping, Upload-Describe-Review integration, Corpus Review
graphics, accessible download controls, responsive browser evidence, and Oğuz
Koran's terminology and workflow acceptance.
