# Phase A5.1 · Before / After Measurements

Before = Phase A.5 owner-local export (absolute path redacted for repository hygiene).
After = this A5.1 export. Measured with headless Chromium at the acceptance
viewports. Raw data: `measurements.json` in the working directory; geometric
values below were read from live layout, not from source CSS.

| Measurement | Viewport | Before (A5) | After (A5.1) | Target |
|---|---|---|---|---|
| `Browse files` top offset | 375×844 | 1096 px | **740 px** | ≤ 780 px |
| `Browse files` top offset | 390×844 | 1096 px | **740 px** | ≤ 780 px |
| `Browse files` top offset | 1440×1000 | 771 px | **768 px** | inside initial viewport |
| Page H1 count (every page) | all | 1 (entry H1 was the upload panel) | **1 (entry H1 is the page headline; upload is H2)** | exactly one real H1 |
| Native radio inputs (entry) | all | 0 | **7** | native semantics |
| `<main>` / `<footer>` landmarks | all | absent | **present on every page** | present |
| Skip link | all | absent | **present, visible on focus** | present |
| Visible scroll-instruction height | 375×844 | 0 visible (chip clipped to ~4 px) | **19 px lines, 2 on review, 2 on results, 4 on system** | persistent, unclipped |
| MFW selector layout | 375×844 | 4 stacked rows | **2×2 grid, four 44 px options** (row/col positions: [14,661] [192,661] [14,713] [192,713]) | 2×2 |
| `system.html` document width | 375×844 | 716 px (overflow) | **375 px, no overflow** | no overflow |
| `system.html` document width | 390×844 | 716 px (overflow) | **390 px, no overflow** | no overflow |
| Page horizontal overflow (entry, review, results) | 375 / 390 / 1440 | none | **none** | none |
| Persistent smallest text | all | 10.5–11 px labels | **12 px minimum** | ≥ 12 px |
| Essential control minimum size | all | 34 px small buttons | **44 px for all buttons and choices** | ≥ 44 px |
| Text contrast pairs | n/a | 20/20 pass (one boundary row mis-scoped) | **17/17 text pairs ≥ 4.5:1** | 4.5:1 |
| Non-text contrast pairs (essential boundaries, state marks, focus ring) | n/a | not separately audited | **9/9 pairs ≥ 3:1** (control-line #6f7d78: 4.29:1 on paper) | 3:1 |

Notes.

1. The A5 "before" browse offset is identical at 375 and 390 because the same
   mobile breakpoint governs both. The mobile reordering, compact step
   indicator, and button-first dropzone produce the A5.1 value.
2. The MFW grid geometry was verified from bounding boxes because Chromium
   reports an unresolved `grid-template-columns` string on `<fieldset>`
   elements even while laying them out correctly.
3. Contrast is computed from the token values with the WCAG relative-luminance
   formula; the full tables, including the corrected non-text section and the
   decorative-border exemption note, are inside `design-system.png` and
   `system.html`.
