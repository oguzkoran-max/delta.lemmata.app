# P004 Metadata UX and Visual Review Decisions

**Status:** Human-approved product baseline

**Decisions:** `HD-20260711-0009`, `HD-20260711-0010`

**Ticket:** `P004`

**Date:** 2026-07-12

## 1. Accepted Interaction Decisions

1. Delta supports both an on-screen guided editor and versioned CSV import/export.
2. Essential fields appear first; edition, source, adaptation, collection, rights
   evidence, and normalization details use progressive disclosure.
3. One analyzed TXT represents one independent work in v0.1. Chapters and segments
   do not increase the independent-work count.
4. Files and metadata rows match only by an exact controlled label. Delta can
   propose exact matches, but the user confirms the final mapping. No fuzzy match
   silently assigns scholarly metadata.
5. Chronology supports start, end, and certainty while keeping simple single-year
   entry easy.
6. First-publication date and the date of the analyzed edition remain separate.
7. A deterministic rights questionnaire helps the user document a state, but Delta
   never presents that state as an automatic legal judgment.
8. Upload, analysis, export, and public redistribution permissions remain separate
   and each supports explicit uncertainty.
9. Validation uses blocker, warning, and information levels. Identity, mapping,
   contradictory chronology, and required rights failures block progression;
   possible corpus confounds remain visible warnings.
10. A Corpus Review screen precedes Parameters. The user can inspect the inventory,
    correct problems, and download metadata plus the canonical manifest. Delta does
    not add permanent project storage.

## 2. Corpus Workflow and Layout

1. The four top-level workbench stages remain Purpose, Corpus, Parameters, and
   Evidence. Corpus contains three internal stages: Upload, Describe, and Review.
2. During Corpus, the right rail becomes a live readiness summary with work,
   chronology-point, blocker, warning, and rights-restriction counts.
3. Essential metadata uses a compact editable grid. Selecting a work opens its
   edition, source, adaptation, collection, normalization, and rights details.
4. Describe shows only a compact live summary. Complete corpus-description
   visualizations appear in Review, where partial data remains visibly `Unknown`.
5. The work timeline is horizontal and selectable. A selected mark reveals title,
   first publication, date certainty, edition, genre, audience, and source details.
6. Genre, audience, source, adaptation, and collection summaries use a stable
   segmented view with horizontal bars rather than pie or donut charts.
7. The Rights Action Matrix shows every asset, sorts blockers first, and offers a
   `Needs attention` filter without hiding clean records by default.
8. The existing dark-green workbench remains the base. Permitted, warning, blocked,
   and unknown states use restrained green, amber, red, and grey plus icon and text.
9. Parameters unlock only after one explicit confirmation that file-to-work mappings
   and rights records were reviewed. Per-work confirmation is not required.
10. Review can download versioned metadata CSV, canonical inventory JSON, and a
    validation report. Raw text is never added automatically.

## 3. Metadata Field and Teaching Contract

### Purpose-Aware Requirements

- Every purpose requires exact file mapping, stable work and author identities,
  original title, language, edition/source evidence, normalization profile, and
  explicit upload and analysis permissions.
- Group Comparison additionally requires a group label.
- Style Over Time additionally requires first-publication chronology and date
  certainty. Fewer than six independent works or three chronology points forces
  exploratory status.
- Missing genre, audience, adaptation, or collection information remains visible as
  a confound warning unless a more specific cross-field rule makes it a blocker.

### Stable Identities

- Delta proposes a readable `work_id`, such as `collodi_pinocchio_1883`; the user
  confirms it before Review.
- Confirmed identifiers do not silently change when a title or date is corrected.
- Authors use stable `author_id` plus display name. Anonymous, unknown, and multiple
  contributors with roles are supported; external authority IDs remain optional.

### Titles, Language, and Chronology

- The original title and text language are canonical. An English display title is
  optional and never replaces the original.
- Date entry begins with `exact`, `approximate`, `range`, or `unknown`; the interface
  opens only the fields needed by that mode.
- First-publication chronology and analyzed-edition date remain separate. An edition
  date never silently substitutes for a work date.

### Controlled Classifications

- Genre and audience use versioned suggested vocabularies plus `Other`.
- Custom labels preserve the user's wording and receive a separate normalized value
  so spelling or capitalization variants do not fragment charts.
- Unknown and not-applicable are explicit values; an empty cell is not treated as a
  scholarly assertion.

### Source and Rights Evidence

- Each analyzed asset requires either a source URL or a bibliographic citation;
  both are retained when available. Source type, edition date, and access date are
  separate fields.
- A deterministic questionnaire asks about upload, analysis, export, and public
  redistribution. It proposes a rights state and explains the mapping; the user
  confirms the record. Delta does not make a legal determination.
- Unknown permission closes only the affected action. Upload and analysis must be
  explicitly permitted before analysis; unknown public redistribution blocks public
  raw/normalized export without erasing the documented asset.

### Layered Teaching

- Field labels stay short and use `?` help for definitions and examples.
- Every validation item states what is wrong, why it matters, and how to correct it.
- `Why Delta asks` explanations and a versioned downloadable field dictionary carry
  deeper method guidance without turning the workbench into a tutorial page.

## 4. P004 Visual Baseline

P004 visualizations describe the corpus that the user assembled. They do not show
or imply a stylometric result.

### Work Timeline

- One mark per independent work on first-publication chronology.
- Date ranges and uncertainty are visible rather than collapsed into false precision.
- Tooltip and keyboard-readable details include title, date, certainty, edition,
  genre, and audience.
- The chart does not draw a stylistic trajectory because P004 has no style values.

### Corpus Composition Bars

- Horizontal small-multiple bars summarize genre, audience, adaptation, collection,
  and source counts.
- Bars are preferred to pie or donut charts because category comparison and small
  counts remain readable.
- Counts and category names remain available as text and in the inventory table.

### Rights Action Matrix

- Rows are works or assets; columns are upload, analysis, export, and public
  redistribution.
- Cells show permitted, prohibited, or unknown with icon, text, and color. Color is
  never the only carrier of meaning.
- Unknown and permission-required states remain visibly closed for public raw export.

### Metadata Completeness Matrix

- Rows are works; columns are identity, chronology, edition, source, classification,
  rights, and normalization groups.
- Complete, missing, warning, and conflict states link back to the exact editable field.
- The matrix is a validation overview, not a score of scholarly quality.

### Readiness Summary

- Stable counters show independent works, chronology points, unresolved blockers,
  warnings, and rights restrictions.
- Style Over Time explicitly shows progress toward six independent works and three
  chronology points.
- The component uses counts and a checklist, not a speedometer, quality score, or
  confidence gauge.

## 5. Deferred Scientific Graphics

MDS/PCA maps, dendrograms, distance heatmaps, parameter-stability heatmaps,
leave-one-work-out plots, and result trajectories are prohibited in P004. They enter
only after the canonical `stylo` engine, benchmark, parameter, and interpretation
Tickets supply real evidence. Placeholder charts must never resemble computed results.

## 6. Responsive and Accessibility Contract

- Desktop may show timeline and matrices at full width; narrow screens use horizontal
  scrolling inside the visualization or a text-equivalent list without page overflow.
- Every chart has a title, concise interpretation boundary, text/table equivalent,
  keyboard-readable details, and category labels that do not rely on color.
- Visuals use the existing restrained workbench language. They are not decorative
  cards, marketing illustrations, or a substitute for the editable corpus inventory.

## 7. Implementation Sequence

1. Define versioned domain models, controlled vocabularies, and JSON schemas for
   works, authors, editions, sources, rights actions, and inventory records.
2. Implement stable error codes, cross-field validators, blocker/warning/information
   severity, and valid/invalid deterministic fixtures.
3. Implement canonical ordering, inventory hashing, semantic-change invalidation,
   and upload-order invariance before UI state depends on them.
4. Add versioned CSV template, field dictionary, parser, form-to-CSV and CSV-to-form
   round trips, and exact file mapping with explicit confirmation.
5. Implement the deterministic rights questionnaire and action-specific fail-closed
   policy with no runtime AI or automatic legal claim.
6. Connect Upload, Describe, and Review state while preserving the P003 rejection,
   cleanup, and no-permanent-storage boundaries.
7. Build the readiness summary, Rights Action Matrix, and simple timeline first from
   validated inventory data only. Add composition bars and the Metadata Completeness
   Matrix only after the complete guided path passes browser and keyboard checks.
8. Add metadata CSV, inventory JSON, and validation-report downloads without raw text.
9. Run unit, property, determinism, accessibility, responsive-browser, clean-clone,
   and adversarial scope tests; retain failed attempts in P004 evidence.
10. Ask Oğuz Koran to review terminology, guidance, graphics, and negative rights
    flows before any P004 acceptance or main integration.

## 8. Design Boundary

These decisions authorize implementation, not P004 acceptance. No metadata field,
chart, threshold, or rights label counts as verified until its Ticket criterion has
test and browser evidence. Parameters and scientific analysis remain locked throughout
P004 implementation.

## 9. Comparative Baseline: Lemmata LDA v0.1.0

A live desktop and mobile audit of `https://lda.lemmata.app/` on 2026-07-12
established the sibling tool as a usability floor, not a visual template. The
[comparative evidence record](../../provenance/evidence/P004/lemmata-live-comparative-audit-2026-07-12.md)
retains the reproducible test conditions and observed failure/success paths. Delta
keeps Lemmata's directness while improving the order of scholarly decisions,
accessibility, error recovery, and reproducibility evidence.

### Patterns to Preserve

- The primary action is immediately visible and the three-step upload, configure,
  analyse explanation is concise.
- Advanced controls remain collapsed while common controls use familiar selects,
  sliders, and reset actions.
- Results use task-oriented tabs, preprocessing counts, plain-language warnings,
  interpretation prompts, and downloadable tables.
- Topic interpretation explicitly distinguishes statistical word clusters from
  humanistic themes and returns interpretive responsibility to the researcher.
- Export includes both a complete archive and separately downloadable result files.

### Improvements Required in Delta

- Delta is corpus-first rather than parameter-first. The user documents and reviews
  the corpus before any scientific parameter is shown.
- A rights-cleared worked example starts inside the application with one action;
  the beginner is not sent to a repository to locate fixture files.
- The default path is the guided editor. The 58-column CSV remains an advanced bulk
  import/export contract and is never presented as the beginner's starting surface.
- One experiment stepper and one readiness summary replace duplicate progress panels.
  Locked future panels do not occupy the primary task surface.
- Every error states what happened, why it matters, and the exact correction. Public
  UI never exposes a raw traceback, server path, or dependency internals.
- Closed mobile navigation is removed from keyboard and accessibility-tree order.
  Its toggle has a task name such as `Open experiment navigation`, not an icon-font
  token exposed as the accessible name.
- Every corpus or result visualization has a programmatically equivalent table and
  CSV. Tooltips, color, and a raster download are never the only evidence channel.
- Result presentation follows `health and limitations -> evidence table -> visual ->
  what this shows -> what this does not show -> FAIR export`, rather than leading
  with a gallery of plots.
- The FAIR package later includes resolved configuration, hashes, rights status,
  warnings and failed cells, limitations, environment, checksums, and rerun guidance;
  a collection of result CSV files alone is not treated as reproducibility evidence.
- All repository, citation, issue, and source links are generated from one canonical
  project identity and tested for HTTP success so stale account paths cannot ship.

### Measurable P004 UX Gates

1. The first uploader begins within the first 700 CSS pixels on `1440x1000` and the
   first 900 CSS pixels on `390x844` without hiding the method boundary.
2. The rendered interface contains one experiment navigation component and one
   readiness summary; no duplicate Experiment Map appears in the main rail.
3. Guided metadata entry is the visually primary action; CSV import is labelled
   `Advanced` and remains reachable without being required.
4. At `390x844`, `360x800`, `320x800`, and 400 percent reflow, closed navigation is
   not focusable and the document has no horizontal page overflow.
5. Mobile interactive targets are at least `44x44` CSS pixels. Normal text meets
   `4.5:1`; focus indicators, control boundaries, and non-text status marks meet
   `3:1` against adjacent colors.
6. Computed styles, not only source CSS, verify H1, H2, segmented-control, and focus
   dimensions. Letter spacing is `0` throughout the workbench.
7. Rejection moves focus to a live error summary or the affected field and preserves
   the safe state required by P003. The same test confirms that technical tracebacks
   and uploaded content are not echoed.
8. The stepper uses navigation/list semantics and exposes the current stage with
   `aria-current="step"`; matrices use table semantics rather than generic `div` rows.
9. Each Review visual is checked against its table and downloadable CSV from the same
   validated inventory object. Removing color leaves all categories distinguishable.
10. Automated desktop/mobile checks are followed by a manual Safari and VoiceOver
    pass covering headings, navigation, upload failure, guided editing, timeline,
    rights matrix, downloads, and focus restoration.

## 10. Implementation Checkpoint: Guided TXT Flow

The first UI slice passed its automated gate on 2026-07-12. Individual TXT files now
move from secure Upload to payload-free Describe and Review. The guided editor builds
the canonical P004 inventory; Review exposes readiness counters, an ordered semantic
timeline, the rights action matrix, actionable issues, and three documentation
downloads. Parameters and analysis remain locked.

The browser evidence is retained in
`../../provenance/evidence/P004/guided-corpus-workflow-validation.md`. The checkpoint
did not by itself satisfy the full visual baseline. Its remaining visual items are
addressed separately below rather than retroactively changing that evidence.

## 11. Implementation Checkpoint: Review Projection

The second UI slice passed its local automated gate on 2026-07-12. A pure,
hash-bound Review projection now produces composition counts and seven
documentation-completeness states from the exact same canonical inventory and
validation report used by the rest of Review.

The five composition dimensions count every work exactly once. Unknown,
not-applicable, missing source mapping, and conflicting source types remain visible
categories; orphan sources do not inflate a count. The decorative horizontal bars,
semantic table, and P003-validated CSV share identical row keys.

The completeness matrix presents one row per work and one cell each for identity,
chronology, edition, source, classification, rights, and normalization. Every cell
contains a visible Complete, Missing, Warning, or Conflict label, a short
explanation, and the relevant field paths. The matrix is a documentation overview,
not a corpus-quality score. Complete rights documentation does not imply permission;
action permissions remain a separate matrix.

Named table regions are keyboard-focusable and receive a visible outline. The
fresh-process browser audit confirms visual/table/CSV key parity, exact work-by-seven
matrix shape, five downloads, six responsive Review viewports, and absence of raw
payload echo or external hosts. The failed focus run and a manually rejected clipped
count screenshot are retained alongside the passing evidence:
`../../provenance/evidence/P004/review-projection-validation.md`.

P004 remains open. Guided ZIP-member documentation, exact-commit/CI verification,
and human Safari/VoiceOver acceptance are pending rather than represented as
completed behavior.

## 12. Implementation Checkpoint: Timeline, Correction, and Confirmation

The third UI slice passed its local automated gate on 2026-07-12. The ordered work
timeline is now a native single-selection control. Selecting a work changes a
plain-language detail list while the full semantic table remains available. Both
surfaces use the same hash-bound projection and stable row keys. Unknown dates sort
after documented dates; multiple edition or source relationships are labelled as
conflicts rather than collapsed into one apparently authoritative value. The
control does not encode distance, trajectory, quality, or a scientific result.

Every non-complete metadata field in the completeness matrix can now be selected as
a correction target. Guided inventories return to the exact work and metadata
section, with the target field path visible. Guided values are restored from an
immutable payload-free input record because Streamlit removes widget values while
their controls are absent from Review. CSV-origin inventories instead name the
exact `work_id` and source CSV field to edit; Delta does not pretend to edit CSV
bytes that it deliberately did not retain.

Final confirmation asks the researcher to acknowledge the documented file-to-work
mappings and rights records. The acknowledgement is bound to the canonical
inventory SHA-256, disabled when blockers exist, and invalidated by every guided
rebuild. It is explicitly not a legal determination, a corpus-quality score, or a
scientific sufficiency claim.

The final fresh-process browser audit verifies timeline selection/table parity,
keyboard confirmation, four named focusable data regions, five downloads, no page
overflow across six viewports, no payload echo, no external host, and an unoccluded
custom header. Manual screenshot inspection caught a mobile header overlap after an
otherwise passing run; that run, the earlier interaction failure, and the final
passing run are retained separately. Full verification passed 464 tests and 100%
of 3,132 statements and 868 branches. Evidence:
`../../provenance/evidence/P004/timeline-correction-confirmation-validation.md`.

P004 remains open for exact-commit/CI evidence and Oğuz Koran's terminology,
negative-rights, Safari, and VoiceOver walkthrough.

## 13. Implementation Checkpoint: Guided ZIP Member Catalog

The fourth UI slice passed its local automated gate on 2026-07-12. The strict P003
ZIP parser already calculated a safe member path, SHA-256, byte size, line count,
token count, and limit profile for every accepted TXT member. P004 now exposes only
those content-free values as immutable nested receipt records. It does not reparse
or extract the ZIP and does not retain archive or member bytes.

Individual TXT receipts and ZIP member receipts project into the same
`ValidatedCorpusUnit` model. Catalog order and hash do not depend on ZIP member
order. Parent archive asset IDs, storage names, and archive digests are deliberately
excluded from the documentation state. Safe nested member paths remain valid in
the unchanged versioned metadata CSV contract.

Upload shows a named member catalog before Continue. Each member displays its safe
label, line and token counts, and abbreviated content digest. After Continue, one
member opens one guided work form. The interface still asks the researcher to
confirm whether each member represents an independent work, which edition and
source it represents, and which actions the documented rights permit. Archive
acceptance itself grants none of those claims.

The final fresh-process browser audit re-runs the individual-TXT workflow and adds
a two-member ZIP. It verifies two catalog rows, two guided forms, two Review rows,
visible default-rights blockers, mobile Describe and Review without page overflow,
no payload echo, no egress, and a clean console. Four failed harness/oracle runs are
retained separately. Full verification passed 467 tests and 100% of 3,165
statements and 878 branches. Evidence:
`../../provenance/evidence/P004/guided-zip-member-catalog-validation.md`.

The local functional P004 implementation is complete. P004 remains open for an
exact-commit clean-clone and GitHub CI record plus Oğuz Koran's terminology,
negative-rights, correction, timeline, confirmation, ZIP, Safari, and VoiceOver
walkthrough.
