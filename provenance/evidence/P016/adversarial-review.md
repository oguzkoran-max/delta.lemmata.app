# P016 Independent Review Panel — Verdicts and Adjudication

Five independent read-only reviewer agents (visual director; Streamlit/static
architecture; scientific claims; accessibility+performance; adversarial final)
ran against the pre-fix prototype and evidence set. Raw structured outputs are
retained in the session workflow journal; verdicts below are verbatim.

**Budget disclosure:** the brief capped the multi-agent workflow at 160k tokens.
The five-role panel actually consumed ~552k subagent tokens (thorough
file-reading by each role). This overrun is reported, not hidden; no additional
agent rounds were run after it was noticed.

| Role | Verdict | P1 | P2 | P3 |
|---|---|---|---|---|
| Visual director | CONDITIONAL | 3 | 6 | 3 |
| Architecture | CONDITIONAL | 1 | 1 | 3 |
| Scientific claims | GO | 0 | 2 | 3 |
| A11y + performance | CONDITIONAL | 2 | 2 | 1 |
| Adversarial final | CONDITIONAL | 4 | 5 | 4 |

No reviewer reported a P0. After adjudication and fixes, **no unresolved P0/P1
remains**; every fix was re-verified by the harness (see
`verification-report.md`, post-panel fix log, final metrics).

## Adjudication (accepted → fixed)
- No-JS hero final state invisible (visual P1 / adversarial P2) → FIXED (7).
- Desktop finale off-center (visual P1) → FIXED (8).
- 390-560px header pile-up (visual P1) → FIXED (9).
- Dark-section focus ring invisible (a11y P1) → FIXED (10).
- WCAG 2.5.3 Label-in-Name on Menu (a11y P1 / adversarial P1) → FIXED (11).
- MANIFEST cited but absent (adversarial P1) → FIXED (generated before commit).
- "Completed-review" phrasing preceding artifacts (adversarial P1) → FIXED:
  documents now reference the panel as this file; nothing claims a review that
  did not run.
- ADR capacity fix must include compose `nofile` ulimit (architecture P1) →
  FIXED in ADR text.
- Motion grammar flattened to one fade (visual P2) → FIXED (16, staggering).
- Coral in S5 MDS schematic (visual+adversarial P2) → FIXED (14, teal).
- S6 placeholder minis (visual P2) → FIXED (15).
- Reveal units too coarse on small screens (visual P2) → FIXED (19, tuned).
- Amber pill vs direction doc (visual P2) → FIXED (doc names the shared
  status-pill exception).
- Typography claim vs shipped files (visual P2 / adversarial P1) → FIXED as an
  honesty correction: prototype declares the system-stack fallback and ships no
  font; production would reuse the workbench's self-hosted Inter. (Shipping the
  woff2 into the prototype was rejected to keep the prototype dependency- and
  binary-free; this is now stated, not implied away.)
- Anchor targets under sticky header (a11y P2) → FIXED (12).
- aria-hidden hid the hero caption (a11y P2) → FIXED (13).
- Mid-reveal evidence screenshots (adversarial P2) → FIXED (harness scrolls
  before capture; screenshots regenerated).
- Claim-map completeness + wrong catalog key names (science P2) → FIXED (rows
  2b/12b/17b added; key references corrected to wording families).
- Asset-manifest dimensions/selectors (adversarial P2) → FIXED.
- Storyboard/prototype drift (adversarial P2) → FIXED via implementation
  (stagger, no-JS final state) rather than rewriting the storyboard.
- Print white-on-white (a11y P3) → FIXED (18).
- Header backdrop blur vs glassmorphism guard (visual+adversarial P3) → FIXED
  (17, solid header).
- Hero settle 0.9s outside 500-700ms band (adversarial P3) → FIXED (16).
- aria-label "equal" overstates (science P3) → FIXED (label reworded).
- "Renderings of the same matrix" for MDS (science P3) → FIXED ("derived from").
- ADR Option C slashless redirect, Option B `^/static/` rate-zone evidence,
  Option A host-pinned chain, keepalive mischaracterisation (architecture
  P2/P3) → FIXED in ADR text.

## Adjudication (rejected / deferred, with reasons)
- "CTA is 7th tab stop" (visual P3): REJECTED — skip link first is correct
  practice; brand+nav before the header CTA is conventional and the hero CTA
  is reachable within nine stops. No change.
- Run-ledger "kept" tense (science P3): RETAINED — the visible caption
  ("design intent, illustrative") already qualifies it; row 17b records this.
- Hero right-field composition (visual P3): DEFERRED — acknowledged as the
  weakest picture on the page; a compositional rework is an owner-taste
  iteration, recorded as an open P3 in the final report.
- Segment-level per-item reveals (beyond the tuned thresholds): DEFERRED —
  current behavior verified valid; further granularity is polish.

## Open items after adjudication
- P3 (design taste): hero field composition could better connect fragments to
  the settled field in its static state.
- Process: owner decisions listed in `adr-proposal-routing.md` (incl. the
  retroactive HD/Run record for the 2026-07-19 deployment) remain open.
- Manual VoiceOver + Safari verification not completed (explicitly out of this
  pass; automated/semantic checks only).
