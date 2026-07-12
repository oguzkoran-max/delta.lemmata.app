# P004 Lemmata Family Palette and Parameter Orientation Validation

**Date:** 2026-07-12

**Ticket:** `P004`

**PromptEvent:** `PE-20260712-0007`

**HumanDecision:** `HD-20260712-0001`

**Implementation brief:**
`prompts/P004-family-palette-and-parameter-orientation.md`

## Scope

This checkpoint aligns the existing Delta entry and sidebar with the live Lemmata
product family and explains future parameter behavior. It does not implement
parameter controls, corpus-health calculation, R `stylo` execution, scientific
results, stability labels, storage, deployment, or the parent-site launch link.

The comparative sources inspected on 2026-07-12 were `https://lemmata.app/` and
`https://lda.lemmata.app/`. Live interfaces may change; the resulting local tokens
are therefore versioned Delta decisions rather than a claim about a permanent
external design specification.

## Product Decisions

- Delta now uses the observed Lemmata family green (`#0f6e56`), LDA-like working
  canvas (`#f8f9fa`), light sidebar (`#f0f2f6`), soft mint entry
  (`#e1f5ee`), mint parameter note (`#f0faf6`), and dark neutral text
  (`#31333f`).
- Coral and sky remain semantic secondary accents for inferential boundaries and
  explanation, preventing a one-hue interface.
- The dark technical sidebar was replaced with `Start here`, a three-step research
  path, and a short explanation of why parameters follow corpus review.
- Build, version, readiness, and engine state remain available inside collapsed
  `Technical status`; they are no longer the sidebar's primary message.
- The full parameter explanation is in the main flow after Upload because the
  sidebar is deliberately unavailable on small screens.

## Method Decision

Delta does not copy the LDA page's free parameter sliders into P004. In Delta,
MFW, culling, segment size, and distance define experiment cells. A user who sees
one result and then searches for the most attractive setting could hide parameter
sensitivity.

The visible plan is therefore:

- Guided mode tests 100, 300, 500, and 1,000 MFW.
- Its fixed reference is 500 MFW, 0% culling, whole text, and Classic Burrows
  Delta. The interface explicitly says this is not a best setting.
- Research mode will expose bounded MFW, culling, segmentation, and distance
  choices and compare at most 24 documented combinations per public job.
- Controls remain locked until P006/P007/P008 connect the R engine, corpus-health
  checks, and workflow review.

The exact 24-cell `research-grid-v1`, permitted segment sizes, file/token/CPU/RAM
and timeout limits, and qualitative stability thresholds remain open. Stability
must not be labelled confidence.

## Review Inputs

Two bounded read-only reviews were requested: a visual-family audit and a
stylometric parameter-governance audit. Both returned useful findings, including
the palette mapping, sidebar hierarchy, post-corpus sequencing, fixed Guided
values, and bounded Research controls. Both exceeded the stated 20k-token budget;
neither is represented as independent approval.

## Browser Evidence

The first fresh-process candidate is retained at:

`family-palette-parameter-orientation-attempt-1/browser-audit.json`

It passed the palette, computed contrast, semantic parameter region, TXT flow, ZIP
flow, no-egress, no-console, and no-overflow checks. It failed because the detailed
parameter block pushed the Upload hint below the 1280x800 viewport and because the
mobile oracle incorrectly required hidden sidebar guidance to be rendered. This
run is not passing evidence.

The corrected fresh-process candidate is retained at:

`family-palette-parameter-orientation-attempt-2/browser-audit.json`

It passed all six target viewports: 1440x1000, 1280x800, 640x800, 390x844,
360x800, and 320x800. Computed styles were identical at every target:

- canvas `rgb(248, 249, 250)`;
- sidebar `rgb(240, 242, 246)`;
- entry `rgb(225, 245, 238)` with `background-image: none`;
- parameter note `rgb(240, 250, 246)`.

Measured contrast was 15.33:1 for the entry title, 11.18:1 for the sidebar title,
and 5.21:1 for parameter copy. The audit also passed semantic sidebar and parameter
regions, three visible parameter explanations, first-action and next-stage hints,
zero page/control overflow, unchanged individual-TXT and two-member ZIP
Upload-Describe-Review flows, no submitted-text echo, no external host, and a
clean browser console.

Screenshots are retained beside both audit JSON files. Manual inspection rejected
the first content placement and accepted the corrected desktop/mobile composition
as an automated candidate. Safari, VoiceOver, and general usability remain human
acceptance work.

## Repository Evidence

The first `./scripts/verify.sh` attempt stopped on two Ruff formatting differences
before executing the full gate. It is retained as a failed attempt. After applying
the repository formatter, the complete gate passed:

- 468 tests;
- 3,171 measured statements and 880 measured branches at 100% coverage;
- strict mypy, metadata, schema, provenance, repository, supply-chain, and R lock
  checks;
- 58 provenance records at this pre-additive-record checkpoint.

## Current Verdict

The implementation candidate satisfies its scoped automated and visual gates. It
does not establish learnability, scientific validity, Safari or screen-reader
conformance, production behavior, or P004 human acceptance. Exact-commit replay,
CI, and the revised Oğuz Koran walkthrough remain separate gates.
