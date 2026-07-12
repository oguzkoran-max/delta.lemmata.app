# P004 Beginner-First Entry Experience Validation

**Date:** 2026-07-12

**Ticket:** `P004`

**PromptEvent:** `PE-20260712-0006`

**Implementation prompt:** `prompts/P004-entry-experience-redesign.md`

## Scope

This checkpoint changes only the initial Purpose and Upload experience. It does not
connect scientific analysis, R, AI, accounts, storage, deployment, or the parent
`lemmata.app` site. P003 intake validation, payload clearing, P004 metadata and
rights behavior, and the existing Upload -> Describe -> Review flow remain in force.

## Product and Method Decisions

- The first semantic heading now states the research category rather than a setup
  task: `Discover patterns in writing style.`
- The opening defines stylometry as comparison of measurable language-use patterns
  and gives one concrete beginner-readable example: how often common words recur.
- The interface states that every comparison is relative to the submitted corpus.
- A semantic Observe -> Compare -> Interpret figure teaches the conceptual process.
  It is explicitly labelled `not an analysis result`.
- Three plain-language paths replace specialist-first labels: Compare Texts,
  Compare Groups, and Trace Style Over Time.
- The selected path always shows a research question, a suitable use, and a
  conclusion that the evidence cannot establish.
- No fake dendrogram, cluster, heatmap, distance value, or computed-result preview
  was added.

## Visual and Accessibility Decisions

- The entry surface is one dark ink/forest band, followed immediately by the real
  purpose control and Upload workflow. It is not a separate marketing page.
- Teal carries actions, sky separates explanatory structure, and coral marks
  interpretive boundaries. The page uses no gradient, decorative blob, nested
  card, or radius above 8px.
- Upload has one semantic H1, named regions, minimum 44px segmented controls,
  minimum 14px purpose labels, visible focus treatment, and reduced-motion rules.
- Desktop retains a compact three-column method sequence. At 760px and below the
  method becomes three readable rows. The decorative token field is removed on
  mobile so it cannot overlap copy.
- At 320px the H1 becomes 30px and the entry spacing contracts; words no longer
  fragment into narrow vertical columns, and the first purpose action enters the
  initial 800px viewport.
- Method boundary is an unframed coral rule below Upload rather than a second
  floating card.

## Automated Evidence

Focused AppTest coverage verifies the definition, R/Python threshold, conceptual
method map, single H1, three guidance labels, purpose switching, and absence of
fake-result language. Existing intake and full TXT/ZIP flow tests remain active.

The final fresh-process Playwright result is:

`provenance/evidence/P004/browser-audit-entry-redesign-passed-2026-07-12/browser-audit.json`

It passed:

- 1440x1000, 1280x800, 640x800, 390x844, 360x800, and 320x800;
- one entry region, three method steps, one visible purpose guide, and three
  readable purpose controls;
- one H1 with the intended responsive scale;
- first-action visibility and a desktop hint of the Upload work surface;
- no page or control overflow, no hidden mobile-sidebar focus target, minimum
  control sizes, and an unoccluded product header;
- keyboard purpose selection;
- individual-TXT and two-member ZIP Upload -> Describe -> Review regressions;
- no submitted-text echo, external host, browser console warning/error, or fake
  result phrase.

Desktop and mobile screenshots are retained beside the JSON result.

The final repository-wide gate passed 467 tests with 100% of 3,167 measured
statements and 880 branches, strict typing, metadata checks, 57 provenance records,
repository scanning, and the locked R 4.5.2 / `stylo` 0.7.71 boundary.

## Retained Failures and Superseded Runs

None of the following is counted as passing evidence:

1. A host-Python pytest invocation failed because it did not use the repository's
   locked `uv` environment.
2. The first locked focused run exposed three stale-widget failures after Upload
   was moved outside the stable Streamlit column tree. The structural tree was
   restored while retaining near-full-width Upload; 15 focused tests then passed.
3. Two in-app CDP screenshot attempts timed out. The tracked fresh-process
   Playwright harness produced the retained screenshots instead.
4. `browser-audit-entry-redesign-run-1-2026-07-12` failed because the uploader
   itself was below an overly strict threshold. Visual review showed the real
   Upload heading and mode in the desktop viewport; the strengthened oracle now
   requires the first purpose action and the next workflow-surface hint.
5. `browser-audit-entry-redesign-run-2-2026-07-12` passed an intermediate copy
   candidate but was superseded by the more precise stylometry definition.
6. `browser-audit-entry-redesign-2026-07-12` retained an obsolete copy oracle and
   exposed the 320px first-action miss.
7. `browser-audit-entry-redesign-final-2026-07-12` passed the corrected content and
   geometry but retained the old 32px mobile H1 expectation after the deliberate
   30px narrow-screen adjustment.
8. The first repository-wide gate stopped on a static `str | None` versus literal
   Streamlit gap type; the second stopped on the formatter after that type fix.
   Neither partial run is counted as passing. The third complete gate passed.

Three 12k-token read-only agents and one 30k-token retry exhausted their budgets
while processing mandatory context. A second 30k-token accessibility agent reached
preliminary findings, including focus coverage, mobile purpose layout, reduced
motion, and first-viewport checks, but did not complete an independent approval.
These attempts informed the implementation and are not represented as review.

## Current Verdict

The final entry candidate passes its focused, browser, and repository-wide gates.
Exact-commit, CI, Safari, keyboard, and VoiceOver evidence are separate gates. P004
must remain `in-progress` until Oğuz Koran completes the revised human walkthrough
and explicitly accepts or rejects it.
