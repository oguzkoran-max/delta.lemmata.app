# P004 Metadata UX and Visual Review Decisions

**Status:** Human-approved product baseline

**Decision:** `HD-20260711-0009`

**Ticket:** `P004`

**Date:** 2026-07-11

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

## 2. P004 Visual Baseline

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

## 3. Deferred Scientific Graphics

MDS/PCA maps, dendrograms, distance heatmaps, parameter-stability heatmaps,
leave-one-work-out plots, and result trajectories are prohibited in P004. They enter
only after the canonical `stylo` engine, benchmark, parameter, and interpretation
Tickets supply real evidence. Placeholder charts must never resemble computed results.

## 4. Responsive and Accessibility Contract

- Desktop may show timeline and matrices at full width; narrow screens use horizontal
  scrolling inside the visualization or a text-equivalent list without page overflow.
- Every chart has a title, concise interpretation boundary, text/table equivalent,
  keyboard-readable details, and category labels that do not rely on color.
- Visuals use the existing restrained workbench language. They are not decorative
  cards, marketing illustrations, or a substitute for the editable corpus inventory.
