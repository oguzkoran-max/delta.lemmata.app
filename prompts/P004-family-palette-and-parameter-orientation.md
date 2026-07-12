# P004: Lemmata Family Palette and Parameter Orientation

## Role

Act as a senior product designer, accessibility specialist, digital-humanities
methodologist, and Streamlit engineer. Improve the accepted beginner-first Delta
entry without extending P004 into scientific analysis or P008 controls.

## User Request

Align Delta with the soft visual language of `lemmata.app` and
`lda.lemmata.app`, explain the purpose of the left block, and make clear how
stylometric parameters are determined and whether users will be able to select
them.

## Evidence Baseline

Inspect the live sibling products before choosing colors. Treat their current
rendered interfaces as a dated comparative source, not an immutable design token
specification. Preserve Delta's own epistemic and accessibility requirements.

Use the observed family palette as follows:

- primary action and focus: `#0f6e56`;
- application canvas: `#f8f9fa`;
- sidebar: `#f0f2f6`;
- entry teaching surface: `#e1f5ee`;
- parameter explanation surface: `#f0faf6`;
- primary text: `#31333f`;
- visible non-text boundary: `#6f8f84`.

Do not use gradients. Keep corners at 8px or less and preserve coral and sky as
secondary semantic accents so the interface does not become one-note green.

## Sidebar Decision

Replace the developer-facing `Current boundary` paragraph with a compact user
guide:

1. choose a research question;
2. upload and document the texts;
3. review parameters before analysis.

Explain why parameters appear after corpus review. Keep build version, engine
state, and readiness inside a collapsed `Technical status` disclosure. The
sidebar may be hidden on small screens, so no essential instruction may exist
only there.

## Parameter Decision

Do not copy the LDA page's free sliders into the current P004 build. Delta's
parameter values define an experiment grid, and allowing result-driven manual
selection before corpus-health review would encourage cherry-picking.

The visible explanation must distinguish:

- **Guided mode:** test 100, 300, 500, and 1,000 MFW. Use 500 MFW, 0% culling,
  whole text, and Classic Burrows Delta as a fixed reference, not a best setting.
- **Research mode:** later expose bounded MFW, culling, segmentation, and distance
  controls, with no more than 24 versioned and documented combinations in one
  public job.
- **Current build:** keep controls locked until corpus-health checks and the R
  `stylo` engine are connected. Do not imply that an analysis has run.

The final exact 24-cell `research-grid-v1`, permitted segment sizes, runtime
limits, and calibrated stability labels remain future evidence-gated decisions.

## Placement

- Keep the real Purpose and Upload workflow in the first viewport.
- Put the full parameter explanation after the Upload work surface, where it
  previews the next stage without delaying the first task.
- Keep only the short sequencing explanation in the desktop sidebar.
- On mobile, rely on the main-flow parameter section rather than hidden sidebar
  content.

## Verification

1. Add deterministic AppTest assertions for the sidebar replacement, fixed Guided
   values, bounded Research explanation, current locked state, and absence of the
   old boundary phrase.
2. Lock the family palette in configuration tests.
3. Extend the fresh-process browser audit to inspect computed RGB values, absence
   of gradients, WCAG AA text contrast, semantic parameter/sidebar regions,
   desktop and mobile geometry, and unchanged TXT/ZIP workflows.
4. Retain failed browser and repository attempts. Do not represent either review
   agent as independent approval if its declared budget is exceeded.

## Non-Goals

- No R execution, scientific result, slider, stability score, AI, account,
  storage, deployment, or parent-site edit.
- No claim that the chosen palette proves accessibility or usability.
- No exact `research-grid-v1` definition before benchmark and load evidence.
- No weakening of P003 intake, P004 metadata, rights, or confirmation behavior.
