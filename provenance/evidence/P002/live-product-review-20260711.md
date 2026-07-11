# P002 Live Product Review

## Scope

- Reviewed commit: `60be80e155269d927c0c34d2685b62acaa18170c`
- Surface: local Streamlit app at `http://127.0.0.1:8501`
- Review type: read-only product, interaction, responsive, copy, and console check
- Targets: default 1280 x 720, 390 x 844, and 320 x 800

## Checks

1. The first screen opens directly into the workbench without a landing page.
2. Text Proximity, Group Comparison, and Style Over Time each select uniquely and
   replace the working question, use case, and interpretive boundary.
3. Research mode selects and remains selected after the Streamlit rerun.
4. Style Over Time presents the dated-corpus question and explicitly rejects
   chronology as proof of ageing, maturation, a turning point, or causation.
5. Disabled corpus and analysis actions remain disabled and retain visible reasons.
6. At 390 px and 320 px, document scroll width equals client width, the main region
   fills the viewport, and the sidebar is off-canvas rather than covering the task.
7. The browser console contains no warning or error entry.
8. The live DOM contains `Interface foundation` and no `P002 · Interface shell`
   user-facing label.

## Rejected Evidence

After repeated viewport overrides, the Codex in-app browser screenshot renderer
produced a partially black raster even though the live DOM, geometry, controls,
and console remained healthy. That raster is not retained or treated as product
evidence. Visual acceptance continues to rely on the tracked fresh-context
Playwright screenshots in `provenance/evidence/P002/codex-correction/screenshots/`.

## Limits

This review does not add a real browser-chrome 200% zoom session, manual screen
reader conformance, packet capture, production deployment, ingestion, or
stylometric computation evidence.

## Verdict

No new P0, P1, or P2 finding. P002 remains merge-ready.
