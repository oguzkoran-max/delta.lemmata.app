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
7. Build readiness summary, timeline, composition bars, Rights Action Matrix, and
   Metadata Completeness Matrix from validated inventory data only.
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
