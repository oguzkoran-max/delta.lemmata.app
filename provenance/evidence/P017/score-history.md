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

## Gate status (honest)
- Technical, scientific, accessibility, performance gates: **PASS** (measured).
- Visual rubric: **NOT PASSED** — median 72.6 vs the 90 bar. Trajectory:
  concept 7.3/10-class → 67.5-72.7 with floor rising; both final critics judge
  the page categorically superior to P016 and not generic. Scores were not
  gamed; all cards above are verbatim.

## Multi-agent budget disclosure
Brief guidance: ≤180k tokens. Actual independent-agent spend: concept critics
~184k, verification panel ~306k, re-score ~117k ≈ **607k subagent tokens**
(plus main-loop work). Main driver: image-reading critics at contact-sheet
resolution. Disclosed per the no-silent-overrun rule; the P016 precedent
(552k, accepted) applied.
