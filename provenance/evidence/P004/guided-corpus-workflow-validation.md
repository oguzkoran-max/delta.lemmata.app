# P004 Guided Corpus Workflow Validation

## Scope

This checkpoint connects the P003 secure-intake boundary to a payload-free P004
Upload -> Describe -> Review workflow for individual TXT files. It also implements a
deterministic guided rights questionnaire, purpose-aware validation, a semantic work
timeline, a rights action matrix, readiness counters, and metadata/inventory/report
downloads.

This is an implementation checkpoint, not P004 acceptance. No scientific analysis,
legal determination, runtime AI, retention guarantee, deployment claim, or raw-text
export is introduced.

## Implemented Boundary

- Accepted individual TXT receipts are projected to a stable catalog containing only
  file labels, content hashes, intake profiles, and content-free counts.
- Uploaded bytes and transient storage identifiers are removed before Describe.
- Guided values build the existing immutable P004 inventory rather than a parallel UI
  model.
- Source evidence requires a URL plus access date or a bibliographic citation.
- Rights states map deterministically to separate upload, analysis, export, and public
  redistribution permissions. Unknown and permission-required states stay closed.
- Style Over Time additionally blocks mixed author sets and mixed languages so those
  differences cannot silently masquerade as chronology.
- Review shows warnings and blockers with what/why/fix guidance and produces canonical
  inventory JSON, validation-report JSON, and versioned metadata CSV without raw text.
- ZIP intake remains available but its transition to Describe is fail-closed until a
  member-level payload-free catalog is implemented.

## Comparative UX Baseline

The live `lda.lemmata.app` audit is retained in
`lemmata-live-comparative-audit-2026-07-12.md`. Delta preserves direct upload and
task-oriented output while placing corpus identity, uncertainty, rights, and review
before parameters. The guided editor is primary and the 58-column CSV is labelled as
an advanced path.

## Automated Verification

Final project gate:

```text
./scripts/verify.sh
```

Result:

- 418 tests passed;
- 2,519 measured statements, 0 missed;
- 644 measured branches, 0 missed or partial;
- Ruff formatting and lint passed;
- strict mypy passed for 18 source files;
- metadata, schema, provenance-record, repository, and R/stylo lock gates passed.

Final browser gate:

```text
.tools/uv/bin/uv run python scripts/browser_audit_p004.py \
  --output provenance/evidence/P004/browser-audit-guided-flow-2026-07-12
```

The fresh-process Playwright run passed at `1440x1000`, `1280x800`, `640x800`,
`390x844`, `360x800`, and `320x800`. It verified:

- no page or main-container horizontal overflow;
- exactly one semantic stepper and one active `aria-current="step"` item;
- first-uploader positions of 698.5 CSS px on desktop, 829.64 on the two mobile
  targets, and 898.53 on the 320 px reflow target;
- computed 32/28 px H1 and 20 px H2 sizes, 44+ px segmented controls, and 24 px help
  targets;
- no visible or focusable closed mobile-sidebar control;
- keyboard purpose selection;
- enabled Upload -> Describe transition after valid intake;
- no file input or uploaded text rendered in Describe or Review;
- successful guided rights documentation, semantic rights table, three documentation
  downloads, and an explicit analysis lock;
- no observed external browser host and no browser console warning or error.

Machine-readable details and screenshots are in
`browser-audit-guided-flow-2026-07-12/`.

## Retained Failed Browser Attempts

Four failed iterations are retained rather than overwritten:

1. `browser-audit-guided-flow-failed-run-1-2026-07-12/`: the first harness waited for
   explanatory copy inside a collapsed expander after keyboard selection and timed
   out. Six initial screenshots were produced; no result JSON was written.
2. `browser-audit-guided-flow-failed-run-2-2026-07-12/`: the harness exposed uploader
   placement, mobile-sidebar control, hidden file-input false positives, and stale
   active-step assertions.
3. `browser-audit-guided-flow-failed-run-3-2026-07-12/`: the guided flow passed, but a
   1440 px context was measured before Streamlit finished replacing its skeleton and
   the 320 px uploader remained below the gate.
4. `browser-audit-guided-flow-failed-run-4-2026-07-12/`: every functional gate passed;
   the 320 px uploader measured 900.53 CSS px against the 900 px threshold.

Each observed defect or harness error was corrected and rerun. No failed iteration is
presented as passing evidence.

## Remaining P004 Work

- composition bars and their text/CSV equivalent;
- metadata completeness matrix with field-level correction links;
- explicit mapping-and-rights review confirmation before future Parameters unlock;
- full guided ZIP member catalog and transition;
- human terminology, negative-rights, Safari, and VoiceOver walkthrough by the
  acceptance owner;
- exact-commit rerun, CI, clean-clone verification, and final P004 closure records.

The current timeline is an accessible ordered corpus chronology, not yet the complete
selectable horizontal visual specified by P004-AC-07. P004-AC-07 therefore remains
pending.
