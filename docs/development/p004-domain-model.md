# P004 Domain Model and Determinism Contract

**Status:** Implemented foundation; P004 remains in progress

**Ticket:** `P004`

**Date:** 2026-07-12

## 1. Boundary

P004 describes the scholarly identity and documented rights of inputs that already
passed P003 secure intake. It does not retain source text, run `stylo`, make a legal
determination, or unlock Parameters.

P003 and P004 deliberately use different identifiers:

- P003 `IntakeReceipt.asset_id` is a random, transient storage-safety identifier.
- P004 `AssetRecord.asset_id` is a stable, human-reviewable scholarly asset identifier.
- A P003 identifier must never enter the canonical P004 inventory hash.

P004 retains only a stable P003 catalog projection: exact file label, content SHA-256,
intake-limit profile, and `validated-for-intake` status. An asset must match that
catalog by exact label and hash before a separate human mapping confirmation matters.

## 2. Relationship Chain

The versioned inventory records this explicit chain:

```text
Author --contributes to--> Work --has--> Edition --documented by--> Source
                                ^                                ^
                                |                                |
                         analyzed Asset -------------------------+
                                |
                    Rights dependency chain
```

One analyzed TXT maps to one independent work in v0.1. The file label match is exact
and must be confirmed. Chapters, segments, and duplicate files do not increase the
independent-work count.

Each analyzed asset declares `rights_asset_ids`. The chain includes the analyzed
asset itself and can include underlying work, edition, scan, transcription, markup,
annotation, normalized text, or derived-output layers. Analysis and public
redistribution fail closed if any declared layer is missing or does not permit the
required action. A separate `rights_chain_confirmed` decision records that the
researcher reviewed which layers apply; public redistribution remains closed without
that confirmation even when every listed permission appears open.

## 3. Dates and Chronology Points

Work first-publication chronology and analyzed-edition date are separate assertions.
Each date is `exact`, `approximate`, `range`, or `unknown`; an unknown date cannot
carry hidden year bounds.

For the P004 minimum-design counter, chronology intervals are sorted and overlapping
intervals are conservatively merged. Certainty is retained in the record but does not
manufacture a second point: exact 1883 and approximate 1883 share one threshold point,
and overlapping uncertain ranges do not pretend to establish separate temporal
positions. This rule is only a workflow counter, not a claim that uncertain dates are
analytically equivalent.

Style Over Time requires at least six independent works and three chronology points
to remove the forced `exploratory` label, and no blocker may remain. The report contains the literal field
`threshold_is_sufficiency_claim: false`; passing the counter does not establish
scientific sufficiency or remove genre, audience, edition, or corpus confounds.

## 4. Rights Version 2

The original `asset-rights.schema.json` remains immutable as the boolean-based v1
draft. The active P004 model is published separately as
`asset-rights-v2.schema.json` with `schema_version: 2.0.0`:

- hyphenated status wire values become stable snake-case values;
- boolean permissions become `permitted`, `prohibited`, or `unknown`;
- upload, analysis, export, and public redistribution remain independent;
- any permitted action requires recorded evidence;
- public redistribution requires `verified_open`, permitted export, and a license;
- `analysis_only` and `excluded` use closed, internally coherent profiles.
- `verified_open` always requires a license and evidence, even when public export is
  not requested.

The record is a human-confirmed documentation state. Delta does not infer copyright,
jurisdiction, public-domain status, or permission from a date or source URL.
There is no automatic v1-to-v2 conversion: boolean v1 cannot recover explicit
uncertainty, and its identifier vocabulary differs. Any legacy v1 record must be
reviewed and reconfirmed under v2 rather than silently rewritten.

## 5. Canonical Inventory Identity

`inventory_sha256()` hashes a canonical semantic projection rather than UI state.

Included:

- schema and vocabulary versions, purpose, stable identities, relationships, titles,
  language, chronology, classifications, source evidence, file label and content hash,
  stable P003 file-catalog projection, normalization, rights dependency chain, rights
  state, action permissions, evidence, assessor, and notes;
- deterministic sorting of top-level records and set-like contributor, authority, and
  rights-evidence collections.

Excluded:

- upload order and UI order;
- the volatile rights assessment timestamp;
- P003 random storage identifiers, validation messages, and review timestamps.

Changing semantic metadata, source mapping, text hash, normalization, or documented
rights changes the inventory hash. `InventoryBinding` gives downstream runs a simple
machine-readable stale/current check.

## 6. Validation Output

Cross-record validation returns stable error codes with:

- severity: blocker, warning, or information;
- entity type and stable entity identifier;
- field path and an optional future CSV row number;
- concise English text stating what is wrong, why it matters, and how to correct it.

Identity, missing relationships, unconfirmed mappings, contradictory chronology,
P003 label/hash mismatch, incomplete rights dependencies, unknown normalization, and
unresolved upload or analysis permission block progression.
Unknown confound metadata and unresolved overall rights status remain visible warnings.

The generated Draft 2020-12 schema is the portable structural layer. It enforces
required fields, types, supported date modes, web-only URL syntax, and local
single-record conditions. Relationships that standard JSON Schema cannot compare,
such as `range.start_year <= range.end_year` or references across inventory arrays,
are accepted structurally and then rejected with actionable blocker codes by
`validate_inventory()`. Tests lock both layers explicitly; Delta does not claim they
are interchangeable.

## 7. Current Evidence and Deferred Work

The checked-in foundation includes immutable Pydantic models, generated Draft 2020-12
schemas, versioned vocabularies, valid and invalid JSON fixtures, purpose-aware
validation, canonical hashing, invalidation binding, and statement/branch tests.

Still deferred inside P004:

1. versioned CSV template, field dictionary, parser, and round-trip fixtures;
2. rights questionnaire mapping;
3. P003-to-P004 browser state integration;
4. Corpus Review UI and non-scientific corpus-description graphics;
5. responsive and accessibility evidence plus Oğuz Koran's human acceptance.
