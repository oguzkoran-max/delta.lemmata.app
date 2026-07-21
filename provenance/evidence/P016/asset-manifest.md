# P016 Asset Manifest

Policy: this pass is 100% code-native. No Higgsfield or paid generation occurred;
no credits were spent; no runtime external request exists. Classification values:
REUSE / CODE-NATIVE / GENERATED-OPTIONAL.

| ID | Purpose | Location (repo-relative) | Class | Method | Dim/Dur | Format | Fallback | Role | Alt decision | Rights | SHA-256 | Transfer |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | Hero token field (gather→ordered) | prototypes/p016-living-text-observatory/index.html (inline SVG (`.p016-hero-field`)) | CODE-NATIVE | hand-authored SVG + CSS transforms | 560×380 viewBox | SVG inline | static final state (RM/no-JS) | decorative | `aria-hidden="true"` | project-original | n/a (inline; page hash in MANIFEST) | ~6 KB gzip est |
| A2 | Observe chip field | inline SVG (`.p016-observe-field`) | CODE-NATIVE | same | 640×240 | SVG | static | decorative w/ visible caption | aria-hidden; caption in DOM | project-original | n/a | ~2 KB |
| A3 | Corpus ledger cards | semantic HTML | CODE-NATIVE | HTML/CSS | — | HTML | n/a | informative | real text | project-original | page hash | — |
| A4 | Four MFW lenses | HTML + tiny inline SVG density fields | CODE-NATIVE | — | 4×(160×72) | SVG | static | informative labels + decorative fields | labels in DOM; fields aria-hidden | project-original | n/a | ~3 KB |
| A5 | Matrix schematic | inline SVG (`.p016-schematic`, matrix) | CODE-NATIVE | — | 200×150 | SVG | static | decorative-with-caption ("no result values") | aria-hidden + caption | project-original | n/a | ~2 KB |
| A6 | Heatmap schematic | inline SVG | CODE-NATIVE | greyscale-teal ramp, no values | 200×150 | SVG | static | same | same | project-original | n/a | ~1 KB |
| A7 | MDS schematic | inline SVG (unlabeled axes) | CODE-NATIVE | — | 200×150 | SVG | static | same | same | project-original | n/a | ~1 KB |
| A8 | Run-record ledger | HTML list | CODE-NATIVE | — | — | HTML | n/a | informative | real text | project-original | — | — |
| A9 | Delta mark | reuse of live glyph (Δ in rounded square, CSS) | REUSE (recreated in CSS, no binary copied) | CSS | 40×40 | HTML/CSS | text "Delta" | informative | text present | project brand | — | — |
| A10 | Optional hero motion study | not created | GENERATED-OPTIONAL | Higgsfield (design-time only) | 16:9 ≤6s 24fps no audio | AVIF/WebM later | A1 static | decorative | aria-hidden | would be project-commissioned | — | ≤1.5 MB budget |

Fixture decision (S5): no verified public result fixture is embedded. The P006/P009
fixtures are synthetic and rights-clean, but rendering their numbers on a marketing
surface invites misreading as research findings; the storyboard therefore uses
purely structural schematics labeled "Structural schematic · no result values."
This is the lower-risk choice and is reversible.

## Higgsfield status
- Not called. No credits spent. MCP tools not invoked for generation.
- Recommendation: NOT REQUIRED for this concept. The Living Text Observatory
  metaphor is geometric (glyphs, ticks, grids) and renders crisper as code-native
  SVG than as raster/video; motion needs are within CSS capability; the
  performance budget is easier met without media. Generated media would add
  licence/provenance surface for marginal gain. If the owner still wants one
  6-second ambient study for the hero, the ready-to-run concept prompt is stored
  verbatim in the owner brief (`prompts/P016-living-text-observatory-prototype.md`,
  "OPTIONAL HIGGSFIELD CONCEPT PROMPT") and requires: explicit owner approval →
  1 style frame → owner review → ≤1 bounded motion batch → optimized ≤1.5 MB,
  lazy-loaded post-LCP, static A1 fallback retained.

## Performance budget vs. actuals
Budgets: LCP visual 100-200 KB (we use none: text + inline SVG), first critical
transfer <500 KB excl. fonts, requests minimal, no third-party origin.
Actual measured sizes and request counts are in `verification-report.md`.
