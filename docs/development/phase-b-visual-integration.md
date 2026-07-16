# Phase B Visual Integration

**Date:** 2026-07-16
**Branch:** `codex/p014-visual-phase-b`
**Exact base:** `26947e1f6843b2b4dc1d1b0cc552c0af808be3fa`
**Design source:** Claude Code Phase A5.1 review package, manifest verified 24/24

## Scope

Phase B maps the approved A5.1 visual and accessibility contract onto the real
Streamlit application. It does not replace the P006 `stylo` worker, alter the
P007 corpus-health rules, add P011 stability claims, or invent a P012 FAIR run
package.

The integrated surfaces are:

- beginner-oriented Entry with upload before extended teaching content;
- purpose-aware Review with human-readable grouped issues and raw codes under
  `Technical details`;
- evidence-first Results with the complete Guided grid, accessible numerical
  tables, a matrix-local heatmap, and an equal-domain MDS view;
- a shared responsive design system for desktop, mobile, and 320 px reflow;
- self-hosted Inter with licence and SHA-256 provenance.

## Preserved Scientific Contract

- Guided Mode remains 100, 300, 500, and 1000 MFW, zero culling, whole text,
  Classic Delta, and fixed seed 20260713.
- 500 MFW remains a pre-registered display reference, not a best result.
- Every completed Guided comparison remains available; changing the result
  selector changes display only and never reruns or rewrites the canonical
  result record.
- The distance matrix remains the authoritative evidence. Heatmap colours are
  scaled within the selected matrix and must not be compared across cells.
- Distances are displayed to six decimals while the canonical download retains
  stored numerical values.
- Nearest-neighbour ties use the recorded `1e-12` structural tolerance and
  nearness is explicitly described as potentially non-mutual.
- MDS axes have no literary meaning and apparent clusters may be projection
  artefacts.
- MFW ranking and Classic Delta standardisation are fitted on known reference
  texts only; an unknown holdout is projected after that fitting basis is
  frozen.
- Authorship, authenticity, influence, intention, chronology, causation, and
  probability claims remain outside this result surface.

## A5.1 Constraints Resolved

1. Inter is vendored as `InterVariable.woff2`; OFL text and the exact SHA-256
   are retained beside it. No runtime font request is made.
2. Purpose, corpus-format, and MFW choices use native Streamlit radio inputs
   styled as stable cards. The MFW cards are one row on desktop and 2 x 2 on
   mobile.
3. Every view has one visible H1, a keyboard-activatable skip link, the real
   Streamlit application section promoted to a `main` landmark, a footer, and a
   single method boundary.
4. Persistent text is at least 12 px. User-operated controls, including Vega
   toolbar actions, have a minimum 44 x 44 px target.
5. Wide numerical tables have named scroll regions and a visible instruction
   above the table.
6. The A5.1 scientific wording was reviewed against the current P006-P009
   contracts. No future stability or FAIR-completeness language was imported.

## Verification

The final local source gate on macOS passed:

- `./scripts/verify.sh`
- 1,666 passed, one documented canonical-Linux-only skip;
- 11,507 statements and 3,002 branches at 100% measured coverage;
- formatting, Ruff, mypy, generated schemas, frozen P006 oracle records,
  metadata, 109 provenance records, repository scan, and locked R versions.

The production renderer was also inspected at 1440 x 1000, 390 x 844,
375 x 844, and 320 x 800. Observed checks included no document overflow, one H1,
one footer, loaded local Inter, 44 px result controls, one/two-row MFW layout,
four visibly rendered comparison-status cards, and two nonblank SVG
visualizations. Activating the skip link moved focus to the focusable content
start immediately after the header while the Streamlit application section
remained the single `main` landmark. Switching 500 to 1000 MFW changed the displayed distance matrix from
`3.000000` to `4.000000` without changing the canonical download contract. The
browser gate now requires both visual pixel evidence and changed matrix/MDS
table digests, so a repaint alone cannot satisfy the MFW-change check.

The MDS browser contract measures the actual Vega root plot frame rather than
the outer component. At 320, 375, 390, and 1440 px viewports, the absolute
width-height difference was respectively 0.33, 0.75, 1.50, and 1.80 px, within
the 2 px square tolerance, with no document overflow. The role legend remains
available as accessible HTML outside the chart so it does not distort the data
area.

A local wheel build also confirmed that `InterVariable.woff2`, its OFL licence,
and `VENDORED.md` are present in the distribution artifact. The font bytes in
the wheel retain SHA-256
`693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3`.

The full local production browser audit reached the real worker boundary and
failed closed with `P009_PREPARED_CORPUS_RESULT_NOT_AVAILABLE`. This is a
documented noncanonical-host limitation: the closed worker environment requires
`/opt/renv/cache`, which CI creates on Linux, while this macOS host does not have
that system path. No partial scientific result was shown. This local failure is
not a passing worker claim and must not be converted into one.

The authoritative upload-to-R/`stylo`-to-results browser gate therefore remains
the canonical Linux GitHub Actions run for the exact Phase B commit.

Independent scientific-method, accessibility, and release reviews returned GO
after their remediation checks. The exact branch must still pass canonical
Linux CI before merge or deployment.

## Deliberately Deferred

- Cross-parameter stability labels and sensitivity summaries require P011
  calculation and calibration; they are not inferred from completion status.
- A complete FAIR run package remains P012 work.
- MDS stress, residual, or eigenvalue diagnostics require a separately specified
  and tested scientific contract.
- Research Mode and the full three-purpose execution matrix remain outside this
  visual integration.
- General usability or teachability cannot be claimed from developer inspection.

## Release Gate

Phase B may be proposed for review after the exact commit passes both GitHub CI
jobs and an independent diff review. It must not be merged, deployed, or routed
publicly on the strength of this local record alone.
