# P017 Concept Sprint — Three Rendered Directions

All three are real HTML compositions (no mockups), self-hosted variable fonts
(Fraunces OFL + the workbench's vendored Inter), one shared cinematic world
(near-black forest, ivory/bone type, luminous emerald, restrained copper), and a
working scroll spike: a reversible, scroll-driven `--p` state machine
(0→1 across a pinned scene) that already transforms the signature visual — not
fade-up reveals. No-JS and reduced-motion render a composed mid-state
(`--p` preset), so the static story is intentional, not broken.

Shots: `shots/` · sheets: `contact-sheet-desktop.png`, `contact-sheet-mobile.png`.
Live preview paths: `prototypes/p017-delta-cinematic-narrative/concepts/{a,b,c}/index.html`.

Image generation inventory (measured, 2026-07-21): Higgsfield MCP is callable
but the account holds 8.35 credits on the free plan — insufficient for the
bounded styleframe workflow; no purchase was made (owner contract). No
Gemini/OpenAI image tool is connected in this session. The sprint is therefore
100% code-native (layered SVG, procedural feTurbulence paper/fibre textures,
typographic compositing). If the owner wants generated raster masters for the
chosen direction, that is a separate decision (top-up or connecting an image
MCP); the code-native path remains fully viable for production.

## A · LIVING CORPUS MONOLITH

A monumental stratified corpus slab (paper fibre, oversized glyph fragments,
punctuation runs, measured tick intervals, analytical grid, a copper rights
notch) floats in a dark editorial space, rim-lit from the left, one emerald
measurement line crossing it. On scroll the strata physically separate and each
layer takes a documentation label (GENRE … RIGHTS · UNKNOWN … OCR); the hero
copy hands over to "A corpus is already an argument."

- Rationale: strongest single protagonist; the object IS the product metaphor
  (language layers becoming documented, measurable material); scales naturally
  to the remaining acts (strata → four lenses → distance field → folded record).
- Risks: SVG text glyphs depend on loaded fonts (self-hosted, so controlled);
  strata separation needs careful per-act choreography so the object never
  dissolves into abstraction.
- Cost: HTML 20.1 KB + fonts ~501 KB (shared across site, cacheable); zero
  raster. 60fps transform-only motion. Estimated full-page build: +25-35 KB
  HTML/CSS/JS, no additional media required.

## B · TYPOGRAPHIC X-RAY

The mandated phrase itself is the protagonist: a viewport-filling Fraunces
cascade ("Every / text / leaves / a trace.") with the word "text" X-rayed —
frequency bands live inside the letterforms (CSS background-clip typographic
compositing). On scroll the phrase compresses and loses weight via the variable
wght axis (flesh→skeleton), bands slide, and an equal-weight 100/300/500/1,000
MFW axis emerges below.

- Rationale: most ownable typographic identity; cheapest payload; the variable
  font is itself the motion medium — a genuinely editorial mechanism.
- Risks: hardest to sustain for six acts without repeating the one trick;
  needs a second visual system (matrix/bands) from Act IV on; `background-clip:
  text` + variable-axis animation must be perf-tested on low-end hardware.
- Cost: HTML 13.3 KB + fonts; zero raster. Estimated full build +20-30 KB.

## C · ARCHIVE TO SIGNAL

A tactile philological world: dark, grained, edge-lit archival pages with
copper marginalia stacked left; their ruled baselines extend rightward and
straighten into measured signal (interval ticks, an emerald measurement line, a
faint matrix corner). On scroll a scan line sweeps the stack; above it the
archive re-renders as documented, analytical structure, and a rights ledger
(rows, not cards) settles in.

- Rationale: warmest disciplinary identity (philology-first); the
  archive→instrument transformation mirrors Delta's actual pipeline; the scan
  is a legible, ownable scroll mechanic.
- Risks: procedural paper in pure SVG reads "slate" under some lights — the
  material would benefit most from one generated texture master later;
  left/right split must be recomposed per act to avoid repetition.
- Cost: HTML 18.4 KB + fonts; zero raster now; optional 1 texture master
  (~150-300 KB AVIF) if generation is enabled later.

## Shared measurements

- Payload per concept page (uncompressed): 13-20 KB HTML+CSS+JS inline + fonts
  67.4 KB (Fraunces) + 81.7 KB (Fraunces Italic) + 352.2 KB (Inter, already the
  workbench font). All self-hosted, OFL/repo-licensed, no CDN.
- Motion: single passive scroll listener + rAF; transform/opacity only;
  reversible by construction; reduced-motion and no-JS get a composed still.
- All copy on the three pages reuses P016-audited sentences; the only new line
  is the owner-mandated act title "Every text leaves a trace." (narrative
  premise framing, boundary sentence kept in the footer).
