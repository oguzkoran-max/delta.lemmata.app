# P016 Design Token Sheet

Base system: A5.1 (exact-HEAD `src/delta_lemmata/ui_theme.py`). The prototype is
namespaced `.p016-` and self-contained; it reuses A5.1 semantics and adds a
narrative layer. Existing workbench tokens are unchanged.

## Reused A5.1 tokens (verbatim values)
| Token | Value | Use in prototype |
|---|---|---|
| teal | #0f6e56 | instrument accent, links, CTA |
| teal-dark | #0a5443 | CTA hover, emphasis |
| mint | #e8f5f0 | active/selected wash |
| mint-strong | #c5e8dc | hairline accents on paper |
| mint-soft | #f4faf7 | quiet panel fill |
| ink | #1a1a1a | headings on paper |
| muted | #5c5c5c | secondary text on paper |
| line | #e2e5e4 | borders on light UI surfaces |
| coral | #d85a30 / text #a33d1c | boundary ("Do not conclude") only |
| amber | #b8860b / text #6b4d00 | genuine warning only (Rights: Unknown) |
| blue | #185fa5 | inline links only |
| canvas | #f8f9fa | handoff strip to workbench |

## Narrative additions (P016 namespace only)
| Token | Value | Contrast (on) | Use |
|---|---|---|---|
| p016-forest | #0D1B17 | — | hero band background |
| p016-paper | #F5F2EA | 14.76:1 vs ink #17211D | main narrative background |
| p016-surface | #FFFDF8 | 16.24:1 vs ink | cards/ledgers |
| p016-ink | #17211D | — | body text on paper |
| p016-paper-on-forest | #F5F2EA | 15.82:1 vs forest | hero text |
| p016-muted | #5C655F | 5.39:1 on paper | secondary on paper |
| p016-line | #D9D8D0 | non-text | structural rules |
Measured ratios recorded in `verification-report.md` (computed, not estimated).

## Typography (no new fonts; supply chain unchanged)
| Role | Face | Size | Notes |
|---|---|---|---|
| Hero H1 | Inter 700 | clamp(2.7rem, 6vw, 5.25rem) | tracking normal (A5.1: no negative LS) |
| Section H2 | Inter 700 | clamp(1.9rem, 3.6vw, 3.4rem) | |
| Body | Source Sans 3 | 17px/1.6 | narrative measure ~62ch |
| Support/caption | Source Sans 3 | 14-15px | ≥12px floor everywhere |
| Labels/eyebrow | Inter 700 | 12px uppercase | letter-spacing +0.06em |
| Numerals | Inter tabular-nums | — | ledger rows |

## Layout & spacing
- Max narrative width 1280px; 12-col grid, gutter 24px; editorial split 5/7.
- Section rhythm: 96-128px desktop, 64px mobile; hero ~78vh.
- Radius 8px max; borders 1px; shadows: none beyond a 1px line + subtle
  paper tint (Quiet Ledger discipline).
- Interactive targets ≥44×44; focus ring 3px teal on paper, 3px mint on forest.

## Motion tokens
- `--p016-ease: cubic-bezier(.22,.61,.36,1)`
- UI 200ms; narrative reveal 560ms; translate ≤24px; opacity 0→1.
- All animation gated by `.p016-js` root class + `prefers-reduced-motion` media.

## Semantic-state mapping
| State | Colour | Rule |
|---|---|---|
| Status badge (alpha/experimental) | mint / amber pill | pills allowed for status only |
| Warning (unknown rights) | amber-text on amber-soft | only genuine limitation |
| Boundary (do-not-conclude) | coral-text + coral left rule | only S6 boundary |
| Instrument accent | teal | never decorative amber/coral |
