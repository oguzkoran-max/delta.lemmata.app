# P007 Corpus Health Diagnostics Validation

**Ticket:** P007  
**Implementation commit:** `b42da99442f4c2a7f617da082c699f1f48942b62`  
**Date:** 2026-07-15

## Scope

This evidence covers the content-free corpus-health projection shared by the
Prepare-stage visuals, semantic tables, and CSV exports. It also covers the
purpose-aware metadata-confound warnings added to the deterministic P007 health
engine. It does not establish parameter suitability, literary interpretation,
benchmark accuracy, stability, general usability, production readiness, or a
complete FAIR run package.

## Implemented Boundary

- Ten explicit warning codes cover OCR, paratext, disclosed curation, edition,
  genre, audience, source type, adaptation, collection, and chronology. The
  chronology rule is purpose-aware: exact date variation is expected in a Style
  Over Time corpus, while uncertain dates remain visible.
- One immutable projection verifies the inventory, annotations, preparation
  manifest, candidate inventory, and health-report hashes before any visual,
  table, or CSV is rendered. A stale or incomplete binding fails closed.
- Work length, transformation counts, confound metadata, duplicate/overlap
  findings, and MFW capacity are projected from the same object used by their
  semantic tables and four versioned CSV exports.
- The CSV exports contain stable identifiers, hashes, controlled terms, counts,
  ratios, and states. They omit corpus text, snippets, titles, edition labels,
  curation notes, readable server paths, secrets, and capabilities, and are
  revalidated by the P003 CSV intake policy before download.
- Every diagnostic panel states what it does not establish. `Not flagged` is not
  presented as proof of no overlap; preprocessing counts are not presented as
  errors; MFW availability is not presented as a best setting; metadata
  variation is not presented as statistically controlled.

## Automated Validation

The implementation working tree passed the full repository gate before commit:

```text
ruff format and lint: passed
mypy: 47 source files passed
pytest: 1,402 passed, 1 documented macOS skip
coverage: 10,088 statements and 2,642 branches, 100.00%
P007 schemas: 5 generated schemas matched
metadata: passed
records: 92 valid records
repository scan and locked R boundary: passed
```

The focused tests additionally prove:

- expected warning codes for all ten metadata factors and no exported metadata
  values in the content-free health report;
- no false chronology warning for exact dated variation in Style Over Time;
- deterministic projection ordering and CSV bytes;
- rejection of stale hashes, missing relations, duplicate work rows, malformed
  overlap pairs, and CSV-policy violations;
- no corpus payload, title, edition label, or curation note in the four CSVs;
- eight expected downloads and five explicit interpretation boundaries in the
  real Streamlit workflow;
- fail-closed behavior when projection annotations or bindings are missing.

## Browser Validation

The exact pre-commit working tree was inspected in the Codex in-app browser at
`http://127.0.0.1:8501/`:

- 1,440 by 1,000 desktop: no horizontal overflow, clipped text, or visible
  overlap; the entry hierarchy and corpus action remained readable;
- 390 by 844 mobile: root width and scroll width were both 390 pixels, no text
  element was clipped, the H1 fit its 326-pixel content area, and the three
  research-purpose controls reflowed into two rows with 48-pixel control height;
- Compare Texts, Compare Groups, and Trace Style Over Time each selected correctly
  and displayed its own question, use case, and `Do not conclude` boundary;
- keyboard focus moved from Compare Groups to Trace Style Over Time in document
  order;
- browser error and warning logs were empty.

The native browser file chooser was not automated. Real-service Streamlit tests
separately exercised TXT and ZIP upload, documentation, rights confirmation,
private materialization, deterministic preparation, READY/BLOCKED outcomes,
diagnostic data, downloads, and restart behavior. Therefore this record is an
automated technical check, not the final owner walkthrough or a usability study.

## Exact Remote Clean Clone

The implementation commit was fetched from the private GitHub origin into a fresh
remote `--no-hardlinks` clone, checked out detached, and rebuilt only from committed
Python and R lockfiles:

```text
commit: b42da99442f4c2a7f617da082c699f1f48942b62
bootstrap: passed
pytest: 1,402 passed, 1 documented Linux-only macOS skip
coverage: 10,088 statements and 2,642 branches, 100.00%
metadata and 92 provenance records: passed
repository scan and R lock: passed
post-run git status: clean
```

The clean clone used the same macOS host and may reuse package-manager caches. It
is not an independent non-developer reproduction.

## Canonical Linux Validation

GitHub Actions run
[`29381188842`](https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29381188842)
tested the exact implementation commit on GitHub-hosted Ubuntu 24.04 amd64:

```text
verify job: 87244975281
container job: 87244975195
pytest: 1,403 passed
coverage: 10,088 statements and 2,642 branches, 100.00%
records: 92 valid records
schemas, metadata, repository scan, R lock: passed
SBOM, dependency-vulnerability, and secret gates: passed
canonical Linux amd64 image: sha256:16b67de0cc560e31cac7d123387f697f868a9ef6a1e9bacd4c325837506b78d4
```

## Acceptance Consequence

The technical evidence supports P007-AC-03 through P007-AC-08 and the automated
portion of P007-AC-09. Exact source, schema, privacy-canary, clean-clone, Linux,
supply-chain, and container gates support P007-AC-10 once this evidence record is
itself validated on the closure commit.

P007 remains open for Oğuz Koran's final review of the corpus-warning language
and prepared-state browser surface. That review must not be described as general
usability, ease, or teachability evidence. P008 continues to own parameter review
and public analysis execution.

## Remaining Limits

- No public parameter control or P006 execution is connected.
- No result graph, dendrogram, PCA/MDS view, or literary interpretation exists.
- No real literary corpus, Pinocchio example, benchmark, or calibrated stability
  claim was evaluated here.
- No production retention, host isolation, monitoring, backup, rollback, or public
  deployment claim follows from this evidence.
