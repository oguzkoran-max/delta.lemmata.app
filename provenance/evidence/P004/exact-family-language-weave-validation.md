# P004 Exact Family Palette and Language Weave Validation

**Date:** 2026-07-12

**Ticket:** `P004`

**PromptEvent:** `PE-20260712-0008`

**Exact rerun:** `RUN-20260712-0004`

**Implementation brief:** `prompts/P004-exact-family-language-weave.md`

## Scope

This checkpoint replaces the earlier approximate family mapping with exact colors
read from the live `lemmata.app` CSS custom properties and computed styles, while
retaining the exact LDA Streamlit canvas and sidebar values. It also replaces a
faint decorative token string with a pedagogical Language Weave. No scientific
analysis, parameter control, runtime AI, storage, deployment, or parent-site
change is included.

## Comparative Inspection

On 2026-07-12 the live `https://lemmata.app/` document exposed the following CSS
properties: `--teal: #0F6E56`, `--teal-dark: #0a5443`, `--teal-50: #e8f5f0`,
`--teal-100: #c5e8dc`, `--teal-arrow: #5DCAA5`, `--bg-alt: #f8faf9`,
`--text: #1a1a1a`, `--text-secondary: #5c5c5c`, `--text-tertiary: #888`,
`--border: #e2e5e4`, and its coral, amber, blue, and purple accent pairs. The live
`https://lda.lemmata.app/` computed styles exposed `#f8f9fa` for the body,
`#f0f2f6` for the sidebar, `#31333f` for native control text, and `#0f6e56` for
the primary control color.

This is a dated comparative observation, not a permanent external token API or a
claim that the sibling sites will never change.

## Product Result

- Delta uses the exact sibling palette rather than screenshot-matched
  approximations.
- The entry is an unframed mint teaching band with Inter/system typography.
- The Language Weave shows two illustrative common-word rows and a labelled key
  for common words, punctuation, sentence rhythm, and vocabulary.
- The illustration contains no value, axis, distance, cluster, author, work, or
  computed-result claim. Its caption says `Illustration only · no corpus analysed`.
- Observe, Compare, and Interpret remain visible. Their longer explanations remain
  available to assistive technology while the visual surface stays compact.
- Guided, Research, and Current status parameter explanations use exact teal,
  purple, and amber surfaces rather than one dominant hue.
- The subtitle now identifies Delta as a Lemmata stylometry workbench.

## Iteration Record

All six machine-readable browser reports are retained. Screenshots for attempts
1-5 were deliberately not retained because they duplicated 115 binary images;
the final passing attempt keeps the complete screenshot set.

| Attempt | Result | Reason |
|---|---|---|
| 1 | failed | The first expanded weave pushed purpose controls below 640px and mobile viewports; the 1280px Upload hint also failed. |
| 2 | failed | Compacting the weave fixed 390px but left 640px, 360px, 320px, and the 1280px next-stage hint outside their gates. |
| 3 | failed | A two-column method caption narrowed its own explanatory text into a vertical stack and regressed desktop height. |
| 4 | failed | The method-caption repair passed all but the 320px first action and the 1280px next-stage hint. |
| 5 | failed | Two illustrative rows nearly passed; 320px missed by 2.2px, 360px used an outdated heading oracle, and 1280px remained too tall. |
| 6 | passed | Exact tokens, responsive geometry, full TXT/ZIP flows, and all regression gates passed. |

The five failed reports are under
`provenance/evidence/P004/exact-family-language-weave-attempt-1/` through
`attempt-5/`. Passing evidence and screenshots are under `attempt-6/`.

## Passing Browser Evidence

The fresh-process attempt 6 passed all six target viewports. Purpose-control top
positions were 613.20, 636.98, 637.73, 805.77, 754.39, and 797.34 pixels for the
six ordered targets. The 1280x800 corpus work-surface hint began at 875.86 pixels,
inside the explicit 80-pixel continuation allowance.

Computed values were identical at every target:

- app `rgb(248, 249, 250)`;
- sidebar `rgb(240, 242, 246)`;
- entry `rgb(232, 245, 240)`, with no background image;
- parameter items `rgb(232, 245, 240)`, `rgb(243, 238, 254)`, and
  `rgb(253, 246, 227)`;
- entry-title contrast 15.54:1, sidebar-title contrast 15.53:1, and parameter-copy
  contrast 6.69:1.

The audit also passed the two-row and four-label Language Weave oracle, heading
scale, keyboard targets, zero horizontal/control overflow, individual-TXT and
two-member ZIP Upload-Describe-Review workflows, Review tables and CSV parity,
payload absence, no external host, and a clean browser console.

## Repository Evidence

The first full gate stopped on three formatting differences. After applying the
repository formatter, the second full gate exposed one stale test that still
expected the superseded approximate border `#6f8f84`. The updated exact-border
test and third full gate passed:

- 468 tests;
- 3,174 measured statements and 880 measured branches at 100% coverage;
- Ruff format and lint;
- strict mypy;
- metadata, schema, provenance, repository, supply-chain, and R lock checks.

## Agent Disclosure

Two read-only reviews supplied useful design and methodological cautions. Their
declared 10,000-token budgets were exceeded at 21,587 and 25,767 tokens. They are
design inputs only and are not counted as independent approval.

## Current Verdict

The implementation candidate satisfies its scoped automated and Chromium visual
gates. It does not establish general learnability, scientific validity, Safari or
VoiceOver conformance, production behavior, or P004 human acceptance. P004 remains
in progress until Oğuz Koran completes the revised human walkthrough.

Exact implementation commit `374e2d0` was subsequently reconstructed in a fresh
`--no-hardlinks` detached clone. `RUN-20260712-0004` restored the committed Python
and R environments, passed the same 468-test full gate and six-viewport browser
audit, and left the clone clean. This establishes exact-commit reproducibility for
the scoped implementation, not human acceptance or scientific validity.

The additive provenance-link commit `9864db4` then passed GitHub Actions run
`29204391922`: Linux verification, SBOM/dependency audit, and the canonical amd64
container build all succeeded. Human acceptance remains open.
