# P007 Preprocessing and Corpus Health Contract

**Status:** Accepted by `HD-20260714-0001`. Implementation is authorized within
the evidence and claim boundaries in this document.

**Ticket:** P007

**Date:** 2026-07-14

## 1. Purpose

P007 turns P003-validated text into a deterministic, inspectable input for the
P006 `stylo` worker and decides whether corpus defects must stop analysis. Its job
is not to improve the literary text, choose the best parameters, or certify the
corpus. It makes transformations and risks visible before calculation.

The user-facing sequence is:

1. **Upload:** validate bytes and file structure.
2. **Describe:** document works, editions, sources, rights, and research purpose.
3. **Prepare:** apply one versioned text profile without editing the uploaded
   source.
4. **Health review:** inspect blockers, strong warnings, notes, and feature
   capacity before analysis can be admitted.

## 2. Ownership Boundaries

| Layer | Owns | Must not own |
|---|---|---|
| P003 | Untrusted-byte validation, UTF-8/NFC gate, archive safety, raw digest | Scholarly metadata, preprocessing, analysis |
| P004 | Payload-free work/edition/source/rights inventory | Raw or prepared text, corpus-health judgment |
| P005 | Private ephemeral workspace, capability ownership, lifecycle, cleanup | Text semantics, scientific readiness |
| P006 | Closed count-table calculation and validated `stylo` result | Raw-text preparation, corpus-health policy |
| P007 | Deterministic preparation, work independence, health findings, admission receipt | Public run workflow, results interpretation, benchmark calibration |
| P008+ | Public analysis workflow and later outputs | Bypassing a P007 readiness receipt |

P004 v1 public schemas remain unchanged. New OCR, paratext, text-unit, parent-work,
and analysis-role assertions live in a separate versioned P007 overlay. This avoids
rewriting already accepted P004 evidence while making the additional method claims
explicit.

## 3. Private Materialization Boundary

### Accepted Architecture

- After P003 accepts an upload, validated TXT bytes or validated ZIP member bytes
  are copied directly into a P005-owned `prepare-only` workspace.
- The workspace uses the existing opaque 64-character hexadecimal component names,
  mode `0700` directories, mode `0600` files, no-follow access, and capability
  ownership.
- Raw bytes and prepared text never enter Streamlit session state, SQLite control
  rows, logs, exceptions, PromptEvents, Tickets, Runs, or browser HTML.
- P004 continues to receive only immutable receipts and payload-free catalogs.
- The materialization lease expires no later than one hour and is cleaned
  immediately on rejection, cancellation, blocker-only completion, or failed
  preparation. P014 still owns production storage, snapshot, swap, backup, and
  secure-erasure claims.
- Each source is rebound to raw SHA-256, asset ID, work ID, edition ID, source ID,
  rights decision, intake profile, and inventory SHA-256 before preparation.
- A missing byte source, digest mismatch, identity mismatch, rights denial, or
  workspace-integrity failure produces a blocker and fail-closed cleanup.

The P005 job state machine is not extended. P007 has an orthogonal preparation
state:

```text
MATERIALIZED -> PREPROCESSED -> HEALTH_CHECKED -> READY
                                             \-> BLOCKED
```

Only `READY` can issue an analysis-admission receipt. `BLOCKED` can issue a
content-free audit package but cannot enqueue P006.

## 4. Accepted Canonical Profile

Profile identifier: `delta-surface-words-v1`

### 4.1 Deterministic Transformation

For each validated source:

1. Preserve original upload bytes unchanged and retain their P003 SHA-256.
2. Decode by the already accepted P003 UTF-8 rule. An initial UTF-8 BOM is removed
   by decoding and recorded; an embedded BOM remains invalid at intake.
3. Convert CRLF and CR newlines to LF.
4. Apply Unicode `str.lower()`, not `casefold()`.
5. Apply NFC again because lowercase expansion can introduce combining marks.
6. Scan Unicode code points from left to right:
   - category `L*` starts or continues a token;
   - category `M*` continues a token only when a letter token is already open;
   - every other category, including punctuation `P*`, number `N*`, symbol `S*`,
     whitespace, and a standalone mark, is one separator.
7. Preserve diacritics. Do not transliterate.
8. Join tokens with one U+0020 ASCII space and append one final LF.

Consequences are deliberate:

- `L'amore` becomes `l amore`.
- `co-operare` becomes `co operare`.
- `perche` and `perché` remain different tokens.
- `2026`, page numbers, punctuation, and emoji do not become tokens.
- Italian function words remain because stopword removal is off.

### 4.2 Explicitly Disabled Transformations

The following are forbidden in v1: NFKC/NFKD, accent stripping, transliteration,
OCR correction, spelling correction, historical modernization, contraction
expansion, translation, POS tagging, named-entity removal, stopword removal,
lemmatization, stemming, automatic page-number deletion, automatic header/footer
deletion, automatic paratext deletion, or result-dependent text editing.

Paratext and OCR are documented as corpus conditions. The tool does not pretend to
repair them.

### 4.3 Custom Exclusions

`custom_exclusions.txt` is absent by default. When supplied:

- it is UTF-8 and NFC;
- each non-empty line must already be exactly one valid profile token;
- duplicates are collapsed deterministically;
- regex, glob, comments, multi-token lines, and invisible transformations are not
  supported;
- exclusions filter only the candidate feature inventory;
- prepared text, prepared SHA-256, token totals, unique-token totals, and full
  frequency counts remain unchanged;
- the exact exclusion-file digest and accepted tokens are represented in the
  private configuration; public default export retains the digest and count, not
  a user-authored token list unless the owner explicitly selects that later.

### 4.4 Candidate Features and Unknown Isolation

- Aggregate counts from known independent works determine the ranked candidate
  feature list.
- Stable ordering follows the accepted P006 collation contract.
- Custom exclusions are applied to that ranked candidate list.
- Unknown documents are counted only after the known-derived inventory is frozen.
- Changing unknown content must not change any known prepared hash, known count,
  candidate order, culling eligibility, or P006 fitting input.
- P007 supplies at most the P006 20,000-feature transport ceiling. It never silently
  lowers a requested MFW value.

## 5. Versioned Annotation Overlay

The accepted `corpus-analysis-annotations-v1` overlay binds to the immutable P004
inventory digest and adds only fields P007 needs:

| Field | Values | Purpose |
|---|---|---|
| `analysis_role` | `known`, `unknown` | Keep unknown outside fitted inventory |
| `text_unit` | `independent_work`, `segment`, `excerpt` | Define the unit of independence |
| `parent_work_id` | P004 work ID or null | Prevent segments/excerpts increasing independent n |
| `ocr_status` | `not_ocr`, `reviewed`, `unreviewed`, `unknown` | Surface OCR confounding |
| `paratext_status` | `absent`, `retained`, `manually_removed_before_upload`, `unknown` | Record, never auto-delete, paratext |
| `preupload_curation_note` | optional bounded text | Disclose owner-side preparation without changing source bytes |

An `independent_work` has no parent. A segment or excerpt must point to one parent
work. Multiple assets with the same P004 `work_id`, or multiple declared units with
one parent, count as one independent work for minimum-data and balance checks.

P007 is whole-text only: it detects and documents non-independent units but does
not create segments. P008 owns any later approved segmentation workflow.

## 6. Corpus-Health Vocabulary

Severity is a closed, versioned enum:

- **Blocker:** analysis cannot start. A content-free audit can still be downloaded.
- **Strong warning:** analysis may start, but the condition remains visible in
  Review, results, and export.
- **Note:** descriptive method information; never proof of adequacy or quality.

The UI must not calculate a quality score or use `clean corpus`, `representative`,
`unbiased`, `reliable`, or `publication-ready` as an automated verdict.

### 6.1 Blockers

- Raw digest, inventory digest, identity chain, rights, or preparation binding
  mismatch.
- P004 readiness is blocked or analysis rights are not granted.
- Configuration/profile mismatch, malformed exclusion file, non-deterministic
  preparation, or prepared-hash verification failure.
- Empty prepared work.
- Fewer than two known independent works.
- A segment or excerpt is presented as an independent work.
- Exact prepared duplicate across nominally independent works.
- Mixed preprocessing profile or undisclosed mixed curation policy.
- Unknown-isolation canary failure.
- No requested analysis cell has the minimum two eligible known-derived features.

### 6.2 Strong Warnings

- Fewer than six independent works for general work-level exploration.
- Fewer than three distinct chronology points for Style Over Time.
- Near-duplicate pair.
- Shared passage above the accepted boundary.
- Unknown or mixed OCR status, edition family, paratext status, or pre-upload
  curation policy.
- Mixed genre, audience, source type, adaptation status, collection status, or
  uncertain chronology relevant to the selected purpose.
- Longest/shortest prepared-token ratio greater than `4.0`.
- Largest/smallest non-empty group count ratio greater than `3.0`.
- A requested higher MFW value is unavailable. The affected cell remains
  `not_enough_features`; the tool does not substitute a smaller MFW.

The six-work and three-chronology-point rules are project gates, not universal laws
of stylometry. They must be described as conservative Delta v0.1 policy.

### 6.3 Notes

- Raw/prepared byte counts, token counts, unique-token counts, and transformation
  totals.
- Which of 100, 300, 500, and 1,000 known-derived candidate features are available.
- Whether custom exclusions were absent or present, with digest and count.
- Descriptive group sizes and work-length distribution when no warning threshold is
  crossed.

## 7. Accepted Similarity Rules

These values were accepted by `HD-20260714-0001` as declared Delta v0.1 policy,
not as universal laws of stylometry:

| Check | Deterministic rule | Output boundary |
|---|---|---|
| Exact duplicate | Equal prepared SHA-256 | Pair IDs and equality flag only |
| Near duplicate | Jaccard similarity of unique SHA-256 token 5-shingles `>= 0.90` | Pair IDs and rounded score; no shingles or text |
| Shared passage | Exact contiguous run `>= 200` prepared tokens **or** `>= 20%` of the shorter work | Pair IDs, longest-run count, shorter-work percentage; no passage |
| Length imbalance | Longest/shortest non-empty prepared-token ratio `> 4.0` | Work IDs, counts, ratio |
| Group imbalance | Largest/smallest non-empty independent-work group ratio `> 3.0` | Group labels, counts, ratio |

Near-duplicate computation uses content-addressed shingle digests in the private
workspace and deterministic sorting, not Python's randomized `hash()`. Shared-run
candidates are cryptographically hashed and then byte-confirmed privately before a
finding is emitted. Resource ceilings and temporary files remain inside P005; P014
must still measure production cost.

Thresholds must not be changed after benchmark or Pinocchio results without a new
profile version and contamination record.

## 8. Mandatory Analysis Admission

The only public path to P006 is:

```text
P003 receipt + P004 inventory + P007 overlay
    -> private materialization
    -> preprocessing manifest
    -> health report
    -> READY receipt
    -> receipt-bound P006 input builder
    -> P005/P006 enqueue
```

The READY receipt binds:

- P003 raw digests;
- P004 inventory digest;
- P007 overlay, configuration, manifest, and health-report digests;
- exact asset/work/role ordering;
- known-derived candidate-inventory digest;
- blocker count `0`;
- expiry and one-time admission identity.

Lower-level enqueue and raw P006 input-building functions remain internal. They
must reject missing, expired, reused, mismatched, blocked, or mutated receipts.
P006 wire schemas and P005 lifecycle states remain frozen.

## 9. Beginner-First English UX

The public flow extends the existing workbench rather than adding a marketing page.

### Prepare Screen

Heading: `Prepare the texts for comparison`

Body: `Delta applies the same documented profile to every analysis copy. Your
uploaded source files are not edited.`

Primary command: `Prepare corpus`

After completion: `Review corpus health`

### Health Review

- Findings are grouped by `Must fix`, `Review carefully`, and `Method notes`, while
  exports retain canonical severity names.
- A blocker message reads: `Analysis cannot start until these blockers are
  resolved. You can still download the audit data.`
- Each finding states what was observed, why it matters, what the researcher can
  change, and what the finding does not establish.
- No raw text, token list, filename path, or overlapping passage is displayed.

### Visuals

The first version may include:

- prepared-token length bars by work;
- transformation-impact bars by work;
- confound matrix by work and factor;
- overlap matrix plus an accessible pair table;
- 100/300/500/1,000 MFW capacity indicators.

Every visual must share one immutable projection with its semantic table and CSV.
Color is never the only carrier. Mobile/reflow states keep labels readable. Every
panel includes `What this does not establish` and must not resemble a stylometric
result.

## 10. FAIR-Oriented, Content-Free Outputs

Downloadable records:

- `delta-preprocessing-config-v1.json`
- `delta-preparation-manifest-v1.json`
- `delta-work-preparation-v1.csv`
- `delta-corpus-health-v1.json`
- `delta-health-findings-v1.csv`
- `delta-confound-matrix-v1.csv`
- `delta-analysis-preparation-receipt-v1.json` only when READY

Default records contain opaque IDs, hashes, controlled terms, counts, thresholds,
software/profile versions, and finding codes. They contain no raw/prepared text,
snippets, token lists, readable server paths, workspace names, session capability,
or secret. P012 owns the complete FAIR-oriented run package and clean rerun claim;
P007 outputs are auditable ingredients, not a FAIR certificate.

## 11. Schemas and Modules

Schemas:

- `preprocessing-config-v1.schema.json`
- `corpus-analysis-annotations-v1.schema.json`
- `preprocessing-manifest-v1.schema.json`
- `corpus-health-report-v1.schema.json`
- `analysis-preparation-receipt-v1.schema.json`

Modules:

- `preprocessing_models.py`
- `preprocessing.py`
- `corpus_health_models.py`
- `corpus_health.py`
- `corpus_materialization.py`
- `stylo_input_builder.py`
- `analysis_admission.py`
- `prepared_stylo_runner.py`

Names may change only for an evidenced local architecture reason. Existing P003,
P004, P005, and P006 public contracts must not be silently rewritten.

## 12. Human Decision Package

`HD-20260714-0001` accepts:

1. `delta-surface-words-v1` transformation rules.
2. Exact-token custom-exclusion behavior.
3. Separate P007 annotation overlay and whole-text independence model.
4. Blocker, strong-warning, and note assignments.
5. `0.90` 5-shingle near-duplicate threshold.
6. `200 tokens or 20%` shared-passage threshold.
7. Six-work, three-chronology-point, `4:1` length, and `3:1` group gates.
8. P005 prepare-only materialization and one-hour maximum lease.
9. Mandatory READY receipt as the sole P006 admission path.
10. Beginner-first English wording and content-free output boundary.

The decision now exists. Implementation may proceed, but each accepted rule still
requires its own deterministic fixture and cannot be described as validated merely
because the owner accepted the protocol.

## 13. Primary Method References

- Eder, M., Rybicki, J., and Kestemont, M. (2016), `Stylometry with R: A Package
  for Computational Text Analysis`, *The R Journal*:
  https://journal.r-project.org/articles/RJ-2016-007/
- Schleimer, S., Wilkerson, D. S., and Aiken, A. (2003), `Winnowing: Local
  Algorithms for Document Fingerprinting`:
  https://www.cs.princeton.edu/courses/archive/spr05/cos598E/bib/p76-schleimer.pdf

These sources orient the implementation. They do not independently validate the
project-specific thresholds above; those remain declared, human-owned Delta policy
requiring fixture evidence before any result claim.
