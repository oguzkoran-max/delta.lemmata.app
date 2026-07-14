# ADR-0014: Deterministic Preprocessing and Corpus-Health Admission

**Status:** Proposed; explicit HumanDecision required before implementation

**Date:** 2026-07-14

**Scope:** P007 raw-text preparation, work independence, corpus-health severity,
temporary materialization, and mandatory admission to the P006 worker

## Context

P003 validates untrusted bytes and intentionally returns a payload-free receipt.
P004 documents works, editions, sources, rights, and purpose without retaining text
in public/session state. P005 owns private ephemeral workspaces and lifecycle. P006
accepts a closed candidate-feature count table and proves fixture-local `stylo`
calculation, but it cannot prove how real uploaded text became that table.

Without one P007 boundary, three failures are possible:

1. preprocessing differs across works or runs without being visible;
2. duplicate works, shared passages, segments, OCR, paratext, or metadata confounds
   produce persuasive graphics from a weak corpus;
3. a lower-level enqueue path bypasses corpus-health review and sends caller-built
   counts directly to P006.

P007 must close those gaps without weakening the accepted P003-P006 contracts or
claiming that automated checks establish corpus quality.

## Proposed Decision

- Add a versioned profile named `delta-surface-words-v1` with UTF-8/BOM behavior
  inherited from P003, newline normalization, Unicode `str.lower`, NFC restoration,
  letter-plus-following-mark tokenization, punctuation/number/symbol separation,
  preserved diacritics, retained stopwords, no lemmatization, and one-space plus
  final-LF canonical output.
- Preserve raw bytes and raw SHA-256; record a separate prepared SHA-256 and
  transformation summary. Uploaded source files are never edited.
- Keep custom exclusions off by default. An optional exact-token list filters only
  candidate features and never changes prepared text, prepared hash, token totals,
  or full counts.
- Derive candidate feature order from known independent works only. Unknown content
  cannot affect known preparation, candidate order, culling eligibility, or fitting
  input.
- Keep P004 v1 schemas unchanged. Bind a separate versioned P007 overlay for
  known/unknown role, independent-work/segment/excerpt unit, parent work, OCR,
  paratext, and disclosed pre-upload curation.
- Treat multiple assets or segments from one work as one independence unit. P007
  does not create segments; it remains whole-text only.
- Stage P003-validated bytes directly in a P005-owned private prepare-only workspace
  for at most one hour. Text never enters Streamlit session state, SQLite control
  metadata, logs, provenance, or default exports.
- Use the closed severity vocabulary `blocker`, `strong_warning`, and `note`.
  Blockers stop analysis but not content-free audit export. Warnings remain visible
  through later results and exports. Notes are descriptive, not approval.
- Proposed quantitative rules are: prepared-hash equality for exact duplicates;
  token 5-shingle SHA-256 Jaccard `>=0.90` for near duplicates; exact contiguous
  overlap `>=200` tokens or `>=20%` of the shorter work for shared passage; work
  length ratio `>4.0`; group count ratio `>3.0`; fewer than six independent works
  and fewer than three chronology points as strong warnings.
- Fewer than two known independent works, empty prepared text, non-independent units
  presented as works, exact duplicates across nominally independent works,
  configuration/hash/rights mismatches, mixed preparation policy, unknown-isolation
  failure, or no runnable requested feature cell are blockers.
- Introduce one hash-bound, expiring, one-time READY receipt as the sole path to the
  P006 input builder and P005/P006 enqueue. Existing P006 wire schemas and P005
  lifecycle states remain unchanged.
- Present Upload -> Describe -> Prepare -> Health review in English. Pair each
  visual with one semantic table, CSV, and a statement of what it does not
  establish. Never produce a corpus-quality score.
- Export content-free configuration, preparation, findings, confound, and admission
  records. P012 remains owner of the complete FAIR-oriented run package.

The complete proposed profile, thresholds, fields, UI wording, and output boundary
are specified in
`docs/development/p007-preprocessing-corpus-health-contract.md`.

## Alternatives Rejected by the Proposal

### Reuse P003 Whitespace Token Counts

Rejected. P003 counts bounded non-whitespace strings for intake safety. Those
counts do not implement the accepted stylometric token profile and cannot establish
P006 feature parity.

### Put Uploaded Text in Streamlit Session State

Rejected. It would break the payload-free P004 boundary, complicate restart and
cleanup behavior, and create a browser/session leakage channel.

### Mutate the Accepted P004 v1 Schemas

Rejected. OCR, paratext, text-unit, parent-work, and analysis-role assertions can be
bound in an additive P007 overlay without invalidating P004 evidence.

### Let P006 Accept Arbitrary Caller-Built Counts

Rejected for the public path. P006's lower-level contract remains useful and
frozen, but analysis admission must prove that counts came from the accepted P007
profile and a blocker-free health report.

### Automatically Remove Paratext or Correct OCR

Rejected. Those are editorial interventions, language/edition dependent, and can
erase stylistically meaningful material. Delta documents them and leaves curation
to the researcher.

### Use a Single Corpus Quality Score

Rejected. It would collapse heterogeneous risks into a false ranking and encourage
users to treat an automated score as scientific adequacy.

### Silently Reduce MFW

Rejected. It changes the declared analysis. Unavailable cells remain
`not_enough_features`.

## Consequences if Accepted

- P003 intake must gain a private, direct materialization handoff while retaining
  its existing public payload-free receipt.
- P007 needs separate schema and semantic validation before transformation code.
- Corpus health becomes a mandatory gate rather than an optional report.
- P008 can activate public analysis only through a P007 READY receipt.
- UI and default exports remain useful without exposing text or claiming quality.
- Threshold changes after benchmark or Pinocchio results require a new profile
  version and contamination record.
- Production resource measurements, host isolation, swap/snapshot behavior, and
  secure erasure remain P014.

## Acceptance Boundary

This ADR is not accepted by the user's generic continuation request. No P007 source
implementation, fixture freeze, threshold claim, public analysis, or human-owned
method decision exists until a separate `HD-20260714-*` record explicitly accepts
or revises the ten-item package in the P007 contract.

## Evidence Links

- `docs/development/p007-preprocessing-corpus-health-contract.md`
- `provenance/evidence/P007/architecture-method-audit.md`
- `provenance/evidence/P007/start-validation.md`
- `prompts/P007-start.md`
- `provenance/tickets/P007.json`
