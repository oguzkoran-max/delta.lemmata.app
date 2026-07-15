# P007 Architecture, Method, Provenance, and UX Audit

**Date:** 2026-07-14

**Base commit:** `5fab67cc1407fed196a9c3033619fa5288be3730`

**Branch:** `codex/p007-preprocessing`

## Bounded Review Process

Four read-only review lenses received an explicit combined ceiling of 120,000
tokens, 30,000 tokens each. They independently inspected the P003-P006 contracts,
roadmap, claims, threats, state boundaries, and UI. All four returned usable
reports. Their convergence informed the proposed contract; their output is not
human acceptance or independent scientific validation.

| Lens | Main conclusion |
|---|---|
| Stylometric method | Freeze one explicit surface-word profile; keep diacritics and stopwords; treat exclusions as feature filtering; preserve known-only fitting and work-level independence. |
| Architecture/security | P007 cannot operate on payload-free P004 state alone; validated bytes need a direct P003-to-P005 private prepare-only handoff and one mandatory READY admission facade. |
| FAIR/provenance | Bind raw/prepared/config/inventory digests and software versions, but keep text, snippets, token lists, paths, and capabilities out of default evidence. P012 still owns a complete FAIR-oriented run package. |
| Beginner UX/claims | Add Prepare and Health review as real workflow steps; pair visuals with accessible tables; use blocker/warning/note without a quality score or adequacy claim. |

## Critical Findings

### P0: P007 Has No Raw-Byte Handoff

P003 validates bytes, while P004 intentionally carries only payload-free receipts
and metadata. P005 can stage validated payloads, but the public P004 flow is not
connected to that workspace. P007 therefore cannot honestly normalize or compare
real text from current session state.

The proposed fix is a direct private handoff: accepted P003 bytes or validated ZIP
members are materialized into a capability-owned P005 prepare-only workspace. P004
continues to receive receipts only. Text never enters Streamlit session state,
SQLite control rows, logs, provenance, or browser HTML.

### P0: Corpus Health Can Be Bypassed

P005 and P006 expose lower-level staging and enqueue services. A future P008 caller
could build a count table and invoke them without proving P007 ran. P007 therefore
needs one mandatory admission facade. Only a blocker-free, hash-bound, expiring,
one-time READY receipt may build P006 input and enqueue execution.

### P0: P006 Cannot Prove Its Counts Came from Raw Text

P006 correctly freezes its wire schema at candidate features and document counts.
That boundary should remain unchanged, but the public builder must consume a P007
preparation receipt and bind every count to raw, prepared, configuration, inventory,
role, and feature-inventory digests. This closes CE-04's preprocessing half without
rewriting the fixture-local P006 calculation proof.

### P0: Intake Counts Are Not Stylometric Counts

P003's token count is a resource-safety count over non-whitespace spans. It is not
the surface-word profile needed for `stylo`. UI, reports, and tests must label P003
counts as intake statistics and P007 counts as prepared-token statistics.

### P1: Work Independence Needs an Additive Model

P004 maps text assets to works but does not express segment, excerpt, parent-work,
OCR, paratext, or known/unknown role in a P007-ready contract. Mutating accepted P004
v1 schemas would blur evidence history. A separate overlay can bind these assertions
to the immutable P004 inventory and keep segments from inflating independent n.

### P1: Severity and Thresholds Are Not Yet Human-Owned

The roadmap names duplicate, passage, imbalance, and severity checks but does not
define algorithms or numbers. Implementing thresholds silently would turn an agent
proposal into a scientific decision. Proposed ADR-0014 therefore remains Proposed
until Oğuz accepts or revises the complete method package.

### P1: Claim and Threat Links Drifted

- CE-04 already correctly requires P006 and P007, but the P007 roadmap row omitted
  CE-04.
- EPI-07 requires confound inventory and warning language, but its Ticket list
  omitted P007.
- P007 must link CE-02, CE-04, CE-09 and EPI-01, EPI-02, EPI-04, EPI-06, EPI-07,
  EPI-11.

### P1: Startup Files Contained Historical Active Wording

SESSION_HANDOFF and PROJECT_MEMORY retained valuable P004-P006 checkpoints, but
their top status still said no active Ticket and a lower `Before reading` section
looked like current P004 guidance. The opening package updates the current pointers
and labels the old instruction as historical rather than deleting evidence.

## Proposed Method Boundary

The audit recommends `delta-surface-words-v1`:

- P003 UTF-8/BOM and NFC admission;
- LF newline normalization;
- Unicode `str.lower`, followed by NFC;
- Unicode letter sequences with following combining marks;
- punctuation, numbers, symbols, whitespace, and standalone marks as separators;
- diacritics preserved;
- stopwords retained;
- lemmatization and stemming disabled;
- apostrophes and hyphens split tokens;
- tokens joined by one ASCII space plus one final LF.

Automatic OCR correction, modernization, transliteration, accent stripping,
paratext deletion, stopword removal, lemmatization, and stemming are prohibited.

The recommended similarity policies are exact prepared-hash equality, unique
SHA-256 token 5-shingle Jaccard `>=0.90`, and a byte-confirmed contiguous shared run
of at least 200 prepared tokens or 20% of the shorter work. The values are declared
project policies, not universal stylometric laws, and remain unaccepted.

## Proposed Health Boundary

Blockers include integrity/rights/configuration failure, empty preparation, fewer
than two known independent works, segment-as-work inflation, exact duplicate
independent works, mixed preparation policy, unknown-isolation failure, and no
runnable feature cell.

Strong warnings include fewer than six independent works, fewer than three
chronology points for Style Over Time, near duplicate, shared passage, OCR/edition/
paratext uncertainty, relevant metadata confounds, length ratio over 4:1, group
ratio over 3:1, and unavailable requested MFW values.

Notes include transformation counts, feature capacity, exclusion status, and
descriptive distributions. No severity proves quality, representativeness, or
fitness for publication.

## Proposed Evidence Boundary

P007 should retain content-free, versioned configuration, preparation manifest,
work-level counts, findings, confound matrix, and READY receipt. Raw text, prepared
text, snippets, passages, token lists, server paths, workspace names, session
capabilities, and secrets stay outside default evidence.

Every visual must derive from the same immutable projection as its accessible table
and CSV. Length, transformation, confound, overlap, and feature-capacity graphics
are method diagnostics, not stylometric results.

## Primary References Consulted

- Eder, Rybicki, and Kestemont's `stylo` description for the established R workflow
  and configurable feature preparation:
  https://journal.r-project.org/articles/RJ-2016-007/
- Schleimer, Wilkerson, and Aiken's winnowing paper for deterministic document
  fingerprinting concepts:
  https://www.cs.princeton.edu/courses/archive/spr05/cos598E/bib/p76-schleimer.pdf

Neither source validates Delta's proposed numeric health thresholds. Those values
must be owned explicitly and tested against declared fixtures.

## Claim Boundary

This audit and opening package establish design requirements only. They establish no
accepted preprocessing profile, prepared corpus, duplicate detection performance,
corpus adequacy, P006 preprocessing parity, public analysis, FAIR package, benchmark
validity, Pinocchio finding, production isolation, or complete CE-02/CE-04/CE-09
verification.
