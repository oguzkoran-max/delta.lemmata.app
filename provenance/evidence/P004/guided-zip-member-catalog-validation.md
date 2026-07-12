# P004 Guided ZIP Member Catalog Validation

Date: 2026-07-12

Status: locally verified implementation checkpoint; P004 acceptance is not claimed.

## Scope

This checkpoint allows one P003-accepted ZIP archive to enter the same payload-free
Upload -> Describe -> Review workflow as individually uploaded TXT files.

The P003 parser already calculated each accepted TXT member's safe path, byte size,
SHA-256, line count, token count, and active limit profile while enforcing the
existing archive limits and path, type, compression, duplicate, nested-archive,
UTF-8, NFC, control-character, markup, line, and token checks. P004 now exposes only
those content-free values as immutable `ArchiveMemberReceipt` records nested under
the accepted archive receipt. It does not reparse or extract the ZIP, create a
workspace, retain archive bytes, or retain member text.

`project_corpus_receipts()` converts either individual TXT receipts or validated ZIP
members into the same `ValidatedCorpusUnit` contract. Ordering is deterministic by
normalized member label and content digest. Parent archive asset identifiers,
storage names, and archive SHA-256 do not enter the P004 catalog or its hash.

The Upload surface shows a separate validated member catalog with each member's
label, line count, token count, and abbreviated SHA-256. Continue stores only the
projected catalog and clears upload widgets before Describe. Nested safe member
paths also pass the unchanged P003 metadata-CSV policy and versioned template.

## Security and Interpretation Boundary

- The strict P003 ZIP parser and resource limits are unchanged.
- Member summaries are content-derived metadata, not source text or extraction
  handles.
- No archive member is written to disk in this P004 workflow.
- A ZIP member is treated as one candidate independent work only because the user
  explicitly selected the guided corpus contract; scholarly work, edition, source,
  chronology, and rights claims still require confirmation in Describe.
- Unknown rights remain blockers. ZIP acceptance is not permission to analyze,
  export, or redistribute any member.
- This checkpoint creates no analysis state and makes no retention, deployment, or
  scientific-result claim.

## Attempted Independent Review

Two read-only agents received separate security/domain and UX/browser assignments
with explicit 10,000-token budgets. Both consumed their budgets reading mandatory
parent-vault context before reaching the target source files. They changed no files
and produced no reliable code-level recommendation. Their attempts are disclosed as
incomplete and are not represented as independent approval.

## Automated Verification

Focused ingestion, intake-UI, corpus-workflow, Streamlit, and workflow suites passed
125 tests. The final canonical `./scripts/verify.sh` run passed:

- 467 tests;
- 3,165 statements and 878 branches at 100% measured coverage;
- Ruff format and lint;
- strict mypy across 19 source files;
- schema, metadata, provenance, repository, supply-chain, and R-lock gates.

The tracked fresh-process Playwright harness re-runs the complete individual-TXT
flow and adds a two-member ZIP flow. The passing audit verifies:

- the ZIP mode exposes exactly two member rows with expected labels and digest
  prefixes;
- Continue becomes available only after accepted member summaries exist;
- no member payload is visible in Upload, Describe, Review, or downloaded review
  CSV values;
- upload file inputs are gone after Continue;
- two ZIP members create two guided forms and two Review work rows;
- default unknown rights produce a visible blocker instead of an implicit pass;
- multi-work timeline, completeness, and rights tables contain two rows;
- mobile Describe and Review have no page or control overflow and retain an
  unoccluded brand header;
- the existing individual-TXT flow, five downloads, keyboard confirmation, all six
  base viewports, no-egress observation, and console-clean checks still pass.

Passing evidence:

- `browser-audit-guided-zip-2026-07-12/browser-audit.json`
- `browser-audit-guided-zip-2026-07-12/screenshots/zip-member-catalog.png`
- `browser-audit-guided-zip-2026-07-12/screenshots/zip-describe-mobile.png`
- `browser-audit-guided-zip-2026-07-12/screenshots/zip-review-mobile.png`

## Retained Failures and Corrections

1. `browser-audit-guided-zip-failed-expander-2026-07-12/` stopped because the
   harness treated Streamlit's native `details/summary` expander as an ARIA button.
   The final harness targets the summary element.
2. `browser-audit-guided-zip-failed-rights-select-2026-07-12/` stopped while
   redundantly selecting rights in the second collapsed form. Rights interaction is
   already exercised by the individual-TXT browser flow and two-work AppTest; the
   final ZIP flow instead verifies that default unknown rights fail visibly closed.
3. `browser-audit-guided-zip-failed-mobile-oracle-2026-07-12/` and
   `browser-audit-guided-zip-geometry-2026-07-12/` passed every functional ZIP check
   but failed the brand oracle while the page remained scrolled thousands of pixels
   below the offscreen header. Recorded widths showed no overflow. The final harness
   scrolls the main surface to the top before evaluating visible header occlusion.

These runs are not treated as passing evidence.

## Open Gates

- Exact-commit clean-clone verification and GitHub CI for the combined P004 UI
  candidate remain pending.
- Oğuz Koran's terminology, negative-rights, correction, timeline, confirmation,
  ZIP, Safari, and VoiceOver walkthrough remains pending.
- Scientific parameters, R/stylo execution, result graphics, runtime AI,
  deployment, retention, public release, and parent-site launch remain outside this
  checkpoint.

The functional local P004 implementation is now complete, but P004 remains
`in-progress` until exact-commit/CI evidence and human acceptance are recorded.
