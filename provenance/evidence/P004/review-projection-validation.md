# P004 Review Projection Validation

Date: 2026-07-12

Status: locally verified implementation checkpoint; P004 acceptance is not claimed.

## Scope

This checkpoint adds a payload-free, deterministic Review projection for two
documentation visuals:

- Corpus Composition Bars for genre, audience, adaptation, collection, and
  acquisition source type.
- Metadata Completeness Matrix for identity, chronology, edition, source,
  classification, rights, and normalization.

`build_review_projection()` accepts only one canonical `CorpusInventory` and its
hash-matching `ValidationReport`. A stale report fails closed. The projection does
not accept Streamlit state, upload bytes, raw text, storage identifiers, or
scientific results.

The decorative bars, semantic HTML table, completeness matrix, and two CSV files
are generated from the same immutable projection tuples. Each generated CSV is
revalidated through the unchanged P003 CSV policy before download. Unsafe formula,
markup, newline, bidi, control, non-NFC, or path-like cells therefore disable the
review CSV rather than being escaped into a reversible spreadsheet payload.

## Interpretation Boundary

The visible UI states that composition counts describe documented metadata and do
not measure style, representativeness, balance, or scholarly quality. Completeness
states describe documentation rather than research quality, scientific validity,
or permission to analyze or redistribute a text.

`analysis_only` and `excluded` may therefore be complete rights documentation even
when one or more actions are prohibited. Action permissions remain visible in the
separate Rights Action Matrix. No completeness score or aggregate quality grade is
calculated.

## Independent Read-Only Review

Two bounded read-only agents ran before implementation and changed no files:

1. A domain/validation reviewer mapped Work, Edition, Source, Asset, Rights, and
   ValidationIssue relationships; required one-work-per-dimension counting; and
   identified stale-report, duplicate-ID, orphan-source, and rights-chain tests.
2. A UX/accessibility reviewer required one shared projection, visible status
   words, a semantic table and CSV for each visual, named keyboard-focusable scroll
   regions, explicit interpretation boundaries, and browser key-parity assertions.

Both reviews rejected independent renderer calculations because they could permit
the visual, table, and CSV to drift.

## Automated Verification

The focused projection suite passed 37 tests with 100% coverage of 415 statements
and 178 branches. The current uncommitted candidate then passed the canonical
`./scripts/verify.sh` gate: 457 tests, 100% coverage of 2,984 statements and 830
branches, strict typing, metadata and provenance records, repository scanning, and
the locked R/stylo namespace boundary.

The tracked Playwright harness starts a fresh local Streamlit process and verifies:

- exactly one Corpus Composition data table, one Metadata Completeness Matrix, and
  one Rights Action Matrix;
- identical composition row keys in bars, table, and downloaded CSV;
- a complete per-dimension work-count denominator;
- identical `work:group` keys in the matrix and downloaded completeness CSV;
- exactly seven visible status cells per work, each using Complete, Missing,
  Warning, or Conflict text;
- three named, focusable horizontal table regions with a visible focus outline;
- exact review CSV filenames and no source-text payload in their cells;
- no page-level overflow at 1440x1000, 1280x800, 640x800, 390x844, 360x800, or
  320x800;
- no external host request, browser console warning/error, or uploaded text echo;
- the continuing statement that no stylometric analysis has run.

Passing machine-readable evidence:

- `browser-audit-review-projection-2026-07-12/browser-audit.json`
- `browser-audit-review-projection-2026-07-12/screenshots/`

## Retained Failures

The first expanded browser run failed only the focus-outline oracle. Its JSON is
retained at
`browser-audit-review-projection-failed-focus-2026-07-12/browser-audit.json`.
The CSS was corrected to expose the same high-contrast outline for both `:focus`
and `:focus-visible`.

A later automated run passed but manual screenshot inspection found that the
composition count column was clipped in the narrow main content rail. That run is
not treated as acceptance evidence. Its JSON and rejected screenshot are retained
under `browser-audit-review-projection-failed-visual-2026-07-12/`. Grid minimums
were reduced, long labels were allowed to wrap, and the harness now asserts that
every count remains visible inside a non-overflowing composition row.

The first canonical `./scripts/verify.sh` attempt stopped on two Ruff formatting
differences. It did not execute the remaining gates and is not treated as passing
evidence. After repository formatting, the complete command was rerun from the
beginning and passed.

## Open Gates

- Matrix cells identify exact field paths but do not yet provide truthful
  field-level correction links. Review still has one generic Edit metadata action.
- The work timeline is semantic but not yet horizontally selectable.
- The final explicit mapping/rights confirmation gate is not implemented.
- ZIP intake remains fail-closed before Describe because member-level catalog
  projection is not implemented.
- Manual Safari and VoiceOver acceptance by Oğuz Koran remains pending.
- Exact-commit clean-clone verification and GitHub CI for this checkpoint remain
  pending.
- Scientific parameters, R/stylo execution, result graphics, runtime AI,
  deployment, retention, and public release remain outside this checkpoint.

These open gates are not hidden passes and P004 remains `in-progress`.
