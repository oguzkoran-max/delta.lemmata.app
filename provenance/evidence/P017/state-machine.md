# P017 Scroll State Machine (The Living Corpus)

One protagonist (SVG `<symbol id="mono">`: 8 strata + measurement line + matrix
+ secondary views + run record + motif) is driven by a single normalized input
and six derived envelopes. All motion is CSS transform/opacity computed from
custom properties; JavaScript only writes numbers.

## Input
`P` = clamped `-scene.top / (scene.height - viewportHeight)` over the single
pinned chapter (`.scene`, 720vh). Recomputed on passive scroll/resize via rAF.
Reversible by construction: same P → same frame, forward or backward; fast
jumps and mid-scroll refresh land on the exact frame (verified in every
iteration's `report.json`).

## Envelopes (narrative verbs)
| Var | Window(s) over P | Meaning |
|---|---|---|
| `--settle` | 0 → .13 | Gather: jitter/rotation noise dies, the corpus assembles |
| `--sep` | up .11-.24, down .37-.45 | Act II: strata physically separate; label rail + copper RIGHTS climax |
| `--col` | up .39-.51, down .55-.65 | Act III: strata regroup into four equal MFW lens columns |
| `--mat` | up .55-.67 | Act IV: sweep into the distance matrix; secondary views arrive |
| `--dial` | .72-.86 | Act V: lens dial moves; dot-set crossfade (md0..md3) shows relations shifting |
| `--fold` | .88-.985 | Act VI: matrix recedes; labeled run record draws (dash-offset frame, staggered rows, seal) |

Per-stratum constants (inline `--d --jx --jy --jr --cx --cy --mx --my`) define
separation distance, initial noise, column target, and matrix-row target; the
CSS transform chain sums `sep·d + col·(cx,cy) + mat·(mx,my)` with scale terms,
so overlapping envelopes morph continuously instead of jump-cutting.

Copy blocks `.b1-.b6` and overlays (rail, lenses, matlabel/secondary, dial) use
trapezoid opacity windows in pure CSS over `--p`. Links inside visually hidden
blocks get `tabIndex=-1` + `pointer-events:none` from JS (no invisible tab
stops); `:focus-within` forces a block visible.

## Modes
- **cine**: `.js` root + `min-width:961px` + `prefers-reduced-motion:no-preference`
  → pinned chapter (above).
- **stacked**: everything else (mobile, no-JS, reduced motion, print) → six
  composed static sections; each `<use href="#mono">` instance carries preset
  envelope values inline (e.g. Act IV: `--mat:1`) and an act-specific viewBox
  crop, so every static state is an intentionally composed frame, not a frozen
  animation.

Modes are mutually exclusive via `display:none`, so assistive tech reads
exactly one copy of the narrative in either mode.

## Typographic x-ray (B graft)
`.xr` words use `background-clip:text` frequency bands whose
`background-position` slides with `--p`; heading `font-variation-settings`
weight eases 560→470 with P (JS-set, inherited); reduced-motion path never
runs any of it.
