# P017 Visual Score History (all scorecards preserved, including failures)

Rubric (owner brief): impact 15 · originality 15 · signature 15 · scroll
narrative 15 · typography 10 · composition 10 · mobile 10 · scientific 5 ·
finish 5 → /100. Pass bar: median ≥90, no major creative category <8.5/10, no
generic-SaaS verdict, no unresolved P0/P1.

## Concept sprint (3 blind critics, anonymous A/B/C contact sheets)
Overall medians: A 7.3 · B 6.4 · C 5.6. Ranking unanimous A>B>C; unanimous
greenlight Hybrid A+B. Full verbatim cards:
`concept-sprint/blind-critic-scorecards.md`. Owner selected **Hybrid A+B**
(2026-07-21, AskUserQuestion checkpoint).

## Implementation iterations (tracked harness `tests/p017/harness.py`)
| It | What changed (composition-level) | Technical gates |
|---|---|---|
| 1 | First full build: pinned chapter, envelopes, stacked mode | green except 1 sub-44px target; rail-opacity CSS bug found via sheet |
| 2 | Rail leak fixed; label↔strata alignment; hero text-shadow; minis moved | all green; matrix payoff judged too dim (self) |
| 3 | Matrix strengthened (frame/wash/index ticks/dots); windows widened; use-offset reverted | all green |
| 4 | Mobile: capnote flow fix, s2 recrop, methods padding | all green |
| 5 | Mobile matrix crops enlarged; review JPEGs for panel | all green |
| 6 | Craft push: header scrim, hero lighting, labeled record card + seal, motif reprise, dial visibility, italic-formula cut, a11y invisible-tab-stop fix, font preloads, meta copy fix, envelope tightening | all green |
| 7 | Ruled path rows (kills 3 bordered cards → 1 card group total), finale record-residue, earlier separation | all green: LCP 156ms, CLS 0, overflow 0, sub-44 0, console 0, denylist 0, RM/no-JS parity 2,843 chars |

Evidence: `iterations/it-N/` (contact sheets + report.json every iteration;
full 13-position shots and scroll walkthrough retained for it-1 baseline and
it-7 final; mid-iteration raw frames pruned for repo weight — sheets preserve
the visual record).

## Independent verification round (after it-5)
- Scientific reviewer: **PASS**, zero violations; 3 minor risks (meta
  description phrasing → fixed in it-6; two watch-items noted).
- A11y+perf verifier: perf PASS; a11y FAIL on one P1 (invisible focusable
  links in opacity-0 cine blocks) → fixed in it-6 (tabIndex/pointer-events +
  :focus-within); P2s (heatmap caveat only in aria-hidden node → moved into
  methods; font preload → added). Contrast table: all pairs ≥4.5:1.
- Blind visual critics (rubric): **72.7** and **67.5**; generic-SaaS: no/no;
  superior to P016: yes/yes. Convergent P0/P1: mobile presence, payoff
  weakness, hero lighting, header collisions.

## Re-score round (after it-6 craft push)
- Critic A: **72.5** · Critic B: **72.7**; generic: no/no; superior: yes/yes.
- Remaining convergent objections: (P0/P1) mobile is "subtitles, not a film
  edit" — object collapses to slivers on 390/320; (P1) final third after the
  record fold reads as generic furniture and the exit viewport is half empty;
  (P1/P2) mid-scroll morphs (d033/d050) read murky; value-range compression.
- It-7 addressed the finale furniture (ruled rows, record residue) and the
  opening dead hold after the re-score; mobile film-edit and transition
  lighting remain the two open P1 themes.

## Craft round 2 (owner-approved, it-8 → it-11)
| It | What changed | Result |
|---|---|---|
| 8 | Mobile film-edit attempt: full-bleed art + scrims + per-act crops + static dial | Harness green but sheets showed art vanished on mobile |
| 9 | ROOT CAUSE: `<symbol>` re-viewports `<use>` (scales scene into crop box) — replaced with plain `<g>`; crops became true crops | Mobile object finally present: full-width matrix, big strata stack |
| 10 | 320 hero art lowered; review JPEGs; final blind re-score | **74.4** and **70.2** (median 72.3); generic no/no; superior yes/yes; narrative continuity up to 8.6 |
| 11 | Critics' named finish bugs: header scrim solidified (nothing reads through chrome), 0-8% dead beat removed (separation starts at p=.06) | Harness green (LCP 508ms local, CLS 0, all zeros) |

Remaining convergent objections after round 2 (both critics): the object needs
**material depth** (light response, density, luminous matrix) beyond flat SVG —
the named path to ≥80 is a rendering-depth pass (canvas/WebGL lighting or one
generated texture master); closing acts could stay deeper inside the object's
world. These are recorded as the next-round scope, not hidden.

## Gate status (honest)
- Technical, scientific, accessibility, performance gates: **PASS** (measured).
- Visual rubric: **NOT PASSED** — final median 72.3 (74.4/70.2) vs the 90 bar. Trajectory:
  concept 7.3/10-class → 67.5-72.7 with floor rising; both final critics judge
  the page categorically superior to P016 and not generic. Scores were not
  gamed; all cards above are verbatim.

## Multi-agent budget disclosure
Brief guidance: ≤180k tokens. Actual independent-agent spend: concept critics
~184k, verification panel ~306k, re-score rounds ~235k ≈ **725k subagent tokens**
(plus main-loop work). Main driver: image-reading critics at contact-sheet
resolution. Disclosed per the no-silent-overrun rule; the P016 precedent
(552k, accepted) applied.

## Owner feedback round (2026-07-22, it-12 → it-14)
Owner review notes: page too dark; strata text should be meaningful (like the
real tables used on lemmata.app); the "100" lens label clipped; check
Higgsfield (campaign claim).
- it-12: global lighting lift (pin ambient, strata fills/strokes, text tones);
  strata glyphs replaced with REAL most-frequent words ("the of and a in to" /
  "it is was that he" — the actual material stylometry counts); MFW columns
  and labels pulled inboard so 100 and 1,000 always render in-frame.
- Higgsfield reality check: video NOT free on this account (kling3_0_turbo 5s
  = 7.5 credits, plan free, balance 8.35); image nano_banana 2 credits.
  One styleframe generated with owner authorization (job
  a21e161c-ae86-4d6b-ba03-cc8dc371ddc6, 2 credits, balance -> 6.35): the
  material corpus monolith master. Provenance: assets/styleframe-01.md.
- it-13: styleframe integrated as Act I key visual — first attempt read as a
  pasted rectangle (hard frame edges, double presence with the schematic).
- it-14: edge-melt integration: radial mask + multiply vignette dissolve the
  photo into the stage; object-crop composition; schematic twin waits at 14%
  opacity and takes over by p=.125 (photo -> diagram handoff); same treatment
  as the mobile s1 full-bleed hero. Harness green throughout (LCP 716 ms with
  the 211 KB poster, CLS 0).

## Motion round + final coherence review (2026-07-22, it-15 → it-16)
- Styleframe family (02 separated / 03 sealed record) integrated into stacked
  acts; hero motion loop (owner-generated Seedance 2.0 on site, take 1
  rejected for human figure, take 2 accepted) wired as cine-only
  poster-backed video (3.86 MB, Save-Data guarded, pauses past Act I).
- Fresh blind critic on it-16 (photo+video state): **81.4/100** — first score
  above 80. impact 8.5 · narrative 8.6 · originality 8.4 · scientific 9.5.
  generic: no; superior to P016: yes. Coherence verdict: photo-world and
  schematic-world read as ONE world via the literal material-to-diagram
  dissolve and the copper rights thread.
- Critic recommendation: **SHIP**, with fast-follows (not release blockers):
  (P1) Act III/IV mid-scroll panels dimmer/smaller than the hero's material
  world; (P1) mobile acts 2-6 read more schematic than the promised
  photo-film; (P2) copper caution crop at mobile act-4 seam, ghost-caption
  contrast, d008 dissolve word overlap.
- Rubric bar status: 90 still not met; trajectory 67.5 → 72.3 → **81.4**.
