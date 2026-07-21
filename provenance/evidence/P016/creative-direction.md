# P016 Creative Direction: Living Text Observatory

**Status:** Local prototype only. Not merged, not deployed, not a routing decision.
**Owner brief:** `prompts/P016-living-text-observatory-prototype.md` (transcribed summary).
**Historical decision preserved:** P002/P004 chose a directly usable workbench over a
marketing landing page (roadmap §P002 Amaç; `prompts/P004-entry-experience-redesign.md`).
P016 is a reversible design exploration and an architecture proposal, not a silent
revocation of that decision.

## 1. Design thesis

Delta should read as a contemporary scholarly journal meeting a precise research
instrument. The drama comes from written language becoming measurable structure,
while the surface keeps repeating that measurements depend on corpus documentation,
parameters, and interpretive limits. Restrained, editorial, recognisably academic;
neither a white SaaS dashboard nor a neon AI laboratory.

The central metaphor is the pipeline itself:

text fragments → recurring measurable features → documented comparison →
distance matrix → interpretive limits → preserved run record.

Scroll is narrative sequencing (one message per section), never decoration and
never hijacked.

## 2. Selected direction: Living Text Observatory

- Warm paper narrative surface over a deep forest opening band; ink typography;
  teal as the single instrument accent; amber/coral reserved strictly for genuine
  warning/limitation semantics (A5.1 discipline). One named exception, shared
  with the live workbench: the `Experimental` status pill uses the amber status
  style (status pills are semantic state, not decoration).
- Code-native visuals only in this pass: inline SVG token fields, ledger cards,
  matrix schematics. No generated media, no photography, no 3D claims.
- Motion grammar limited to five conceptual verbs: Gather, Align, Compare,
  Qualify, Record. CSS transitions + IntersectionObserver reveals only;
  transform/opacity; UI 180-240 ms, narrative 500-700 ms; no parallax loops, no
  pinned scene over ~1.2 viewport heights, no scroll-linked frame scrubbing.
- All meaningful text lives in normal DOM order; motion is progressive
  enhancement; reduced-motion and no-JS render the complete story statically.

## 3. Alternatives documented, not implemented

1. **Night Research Instrument** — full dark technical instrument aesthetic.
   Strong first impression; rejected as the primary direction because sustained
   dark surfaces drift toward cyberpunk/HUD cliché, fatigue long reading, and
   collide with the light scientific workbench it must hand off to. A single deep
   forest opening band is retained as a controlled quotation of this direction.
2. **Critical Edition Atlas** — warm paper, serif marginalia, layered annotation.
   Strong philological identity; rejected because it visually suggests a
   TEI/critical-edition or variant-comparison platform, which Delta explicitly is
   not (PhiloEditor boundary, DEVELOPMENT_CONTRACT §8). Its warm paper tone and
   ledger-like records survive in a restrained form.

## 4. Anti-patterns (hard exclusions)

Purple neon; portrait/product orbits; custom cursors; cyberpunk HUD; glassmorphism;
frame-sequence video scrub; full-page autoplay video; fake matrices/values
presented as results; topic/LDA/embedding/neural metaphors; low-contrast
microtext; scroll hijack; award/valuation claims; "AI" imagery of any kind.

## 5. Typography and tokens

No new typeface in this pass. A display serif (Literata/Source Serif 4) was
considered and deferred: licence review, self-hosting, SBOM and font-budget cost
outweigh the benefit for a prototype; editorial contrast is achieved through
size, weight, and composition on the Inter / Source Sans 3 families. The
prototype itself ships NO font files and names these families with a system-
stack fallback (it renders in system UI fonts on machines without them);
production integration would reuse the workbench's self-hosted
`InterVariable.woff2` supply chain. This keeps the prototype dependency-free
and the claim honest.

Narrative additions use existing A5.1 tokens (see `design-tokens.md`); the only
new values are two narrative surfaces (deep forest `#0D1B17`, warm paper
`#F5F2EA` / surface `#FFFDF8`, structural line `#D9D8D0`, muted `#5C655F`) used
exclusively inside the isolated `.p016-` namespace, contrast-checked in the
verification report. Amber/coral appear only inside the Corpus and Uncertainty
sections as genuine limitation semantics.

## 6. Relationship to the live workbench

The prototype is a separate static page. It does not touch Streamlit, its DOM,
selectors, CSS, science pipeline, uploads, or deployment. "Open the workbench"
is configurable (`<meta name="delta-workbench-url">`), defaulting to the current
production root. Routing options and risks are analysed separately in
`adr-proposal-routing.md`; no production routing choice is made here.
