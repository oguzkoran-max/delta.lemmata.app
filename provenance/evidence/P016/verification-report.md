# P016 Verification Report (measured, not estimated)

Harness: local Playwright (Chromium), prototype served from a loopback
`http.server`; raw JSON in `browser-report.json`; screenshots in `screenshots/`.
Test date: 2026-07-20 (local machine; shared-runner numbers will differ).

## Performance (desktop 1440×1000, cold load, loopback)
| Metric | Measured | Budget | Status |
|---|---|---|---|
| LCP | 124 ms | ≤2500 ms | PASS |
| CLS | 0 | ≤0.1 | PASS |
| DOMContentLoaded | 122 ms | — | info |
| Requests | 3 (html+css+js) | minimal | PASS |
| Transfer (uncompressed) | 41,861 B total (html 18,634 / css 19,278 / js 3,949) | <500 KB | PASS (×12 headroom) |
| Third-party origins | 0 | 0 | PASS |
| Failed requests | 0 | 0 | PASS |
| Console errors/warnings | 0 | 0 | PASS |
INP: not measurable meaningfully on a static page without user interaction
instrumentation; no long tasks observed. Lighthouse not run locally; deterministic
size/request budgets used instead (as the brief prefers).

## Viewport matrix (after fixes; all measured)
| Viewport | overflow-x | H1 | CTA in first viewport | <44px targets |
|---|---|---|---|---|
| 1440×1000 | none | 1 | yes | 0 |
| 1280×900 | none | 1 | yes | 0 |
| 1024×768 | none | 1 | yes | 0 |
| 390×844 | none | 1 | yes | 0 |
| 375×844 | none | 1 | yes | 0 |
| 320×800 | none | 1 | yes | 0 |

## State matrix
| State | Result |
|---|---|
| Forward scroll 25/50/75/100% | sections reveal; content complete |
| Return to top after full scroll | 0 hidden reveals (one-way persistence) |
| Fast jump scrolling | valid (same mechanism; no re-trigger) |
| Resize after scroll (1440→1024) | no overflow, no invalid state |
| Refresh mid-scroll | load handler reveals everything above/at viewport |
| Reduced motion | 0 hidden reveals; body text parity 3,521 chars; no animation |
| No JS | full content visible (3,521 chars); CTA href = production workbench; nav details open |
| Save-Data | no conditional media exists; page identical (by construction) |
| Keyboard | tab order: skip link → brand → 4 nav links → CTAs; visible 3px focus |
| CTA navigation | href resolves to configured workbench URL (meta override verified) |

## Accessibility (code + measured)
- Landmarks: 1 header / 1 nav / 1 main / 1 footer; single H1; ordered H2s.
- Skip link targets `#main`; focus-visible styles on light+dark surfaces.
- Decorative SVGs `aria-hidden` + visible text captions; all copy in DOM order.
- Minimum text size 12px (labels); body 16-17px.
- Contrast (computed): ink/paper 14.76, ink/surface 16.24, muted/paper 5.39,
  paper/forest 15.82, mint-strong/forest 13.45, white/teal 6.20, teal/paper 5.55,
  amber-text/amber-soft 7.25, coral-text/surface 6.37, blue/paper 5.83,
  teal-dark/mint 7.94 — all ≥4.5:1.
- Explicitly NOT done: **manual VoiceOver + Safari verification not completed**;
  automated/semantic checks only. Lighthouse/axe not executed in this pass.

## Claim-denylist gate
`grep -iE` over the page for the denylist returned only two negative-form
boundary sentences ("does not read meaning, topics, or intent", "no
winner-takes-all view and no confidence score") — permitted negative claims per
`claim-evidence-map.md` (#7, #17). Zero positive violations.

## Workbench regression
Full `bash scripts/verify.sh` with all P016 files present: PASS —
1,751 passed / 1 skipped; 11,718 statements, 3,056 branches, 100% measured
coverage; schemas/records(119)/repo-scan/R-lock green. Identical totals to the
pre-P016 baseline run (`baseline-audit.md`), i.e. zero regression and zero
workbench change.

## Known capture artifact
Playwright full-page screenshots paint the sticky header at the capture scroll
offset (mid-page band in `p016-1440x1000.png`); in a real browser the header
stays at the top. Verified as a tooling artifact, not a page defect.

## Fix log during verification
1. Closed `<details>` hid desktop nav links (browser behavior) → `open` default
   + JS collapse ≤860px; nav links now in tab order.
2. Nav/footer links below 44×44 → inline-flex min sizes.
3. 320px horizontal overflow (header brand+menu+CTA) → ≤379px compact header,
   subtitle hidden; overflow 0 at all six widths.
4. Hero SVG max-height forcing width overflow at 320 → fluid width.
5. "Menu" summary <44px wide at ≤379px → min-width 44.
6. Full-page evidence screenshots captured pre-reveal → harness scrolls through
   the page before capture (page behavior itself was already correct).

### Post-panel fix log (adjudicated findings, all re-verified above)
7. No-JS hero final field invisible (hardcoded opacity=0) → attribute removed;
   `.p016-js` rule owns the animated start state.
8. Final-section CTA/status centering broken by 62ch max-width → max-width:none.
9. 390-560px sticky header wrapped into a multi-line pile → subtitle hidden
   ≤560px, nowrap CTA, tightened gaps; ≤379px brand text sr-only (accessible
   name preserved; no aria-label override) with 44px brand target.
10. Focus ring invisible on the dark final section → mint outline extended.
11. WCAG 2.5.3 Label-in-Name on "Menu" summary → aria-label removed.
12. Sticky header clipping anchor targets → [id]{scroll-margin-top:84px}.
13. Hero caption inside aria-hidden wrapper → aria-hidden moved to the SVG only.
14. S5 coral holdout diamond (palette semantics) → teal point like the others.
15. S6 placeholder wireframes → S4-echo dot-density minis; 2×2 grid ≤760px.
16. Motion grammar flattening → staggered schematic/ledger reveals (CSS delays),
    12px Qualify rise for Corpus, hero settle timed into the 500-700ms band;
    reduced-motion overrides extended to the new staggered children.
17. Backdrop blur (glassmorphism guard) → solid forest header.
18. Print styles added (white-on-white risk removed).
19. Reveal trigger tuned (threshold .08, rootMargin -8%) so tall stacked groups
    on small screens do not leave large blank bands at the fold.
20. Nav CTA nowrap regression caused 1-11px overflow at 390/320 → responsive
    header rework; final harness: zero overflow, zero <44px targets at all six
    widths.

### Owner polish round (2026-07-20, pre-activation)
21. Colors: hero drift marks raised to legible opacity; settled field accented
    with A5.1 `mint-accent #5dcaa5` dots; final path-card borders brightened.
22. Scroll feel: 2px teal reading-progress hairline (passive rAF, informational);
    header gains an accent rule after 8px scroll; stagger extended to corpus
    ledger cards, MFW lenses, mini-lenses, and path cards; reveal travel/time
    28px/620ms. Native scrolling untouched; reduced-motion disables all of it.
23. Embed resilience: rect-based reveal fallback in the rAF painter plus a
    self-terminating 400ms watcher so wrapper-scroll environments (some in-app
    browsers) still reveal the narrative; one-way persistence re-verified
    (hidden-after-full-scroll = 0).

## Adjudicated independent review findings
See `adversarial-review.md` (five-role panel verdicts, findings, and the
adjudication of each item).
