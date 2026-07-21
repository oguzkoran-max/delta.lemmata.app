# P016 Storyboard: Living Text Observatory

One message per section. All copy below is the exact prototype copy; every factual
sentence is audited in `claim-evidence-map.md`. Motion column lists the single
conceptual verb; reduced-motion (RM) state renders the final composition
statically with the same text and order. No-JS renders everything visible.

Legend: D = desktop ≥1024, M = mobile ≤760.

## S0 Persistent header (all sections)
- Left: Delta mark · "Delta" · "A Lemmata stylometry workbench".
- Right nav: How Delta works · Method · Limits · Documentation · **Open the workbench**.
- D: single row. M: brand + CTA visible; secondary links collapse into a native
  `<details>` disclosure (keyboard accessible, no JS required).
- CTA always visible, min 44×44, first tab stop after skip link. Skip link jumps
  to `#main`. Sticky header; no motion besides a background fade at first scroll
  (opacity only; RM: static).

## S1 Hero (~78vh, not full-screen; CTA in first viewport)
- Eyebrow: "PUBLIC ALPHA · EXPERIMENTAL" (status badges, pill allowed).
- H1: "Discover patterns in writing style."
- Lede: "A scholar-led, uncertainty-aware stylometry workbench for literary and
  digital-humanities research."
- Support: "Run supported stylometric workflows without first learning or writing
  R or Python code. Delta keeps corpus choices, parameters, and limitations visible."
- Primary CTA: "Open the workbench" · Secondary: "See how Delta works" (anchor to S2).
- Visual (right field, D 7/12 cols; M below copy, reduced density): inline SVG —
  two faint columns of abstract glyph fragments and punctuation ticks drift and
  settle into an ordered feature field (Gather). No readable passage, no author
  name, no values. ~42% of the composition stays calm for the HTML copy.
- Deep forest band; paper type. RM/M: final ordered state, no drift.

## S2 Observe — "Style leaves traces."
- Copy: "Stylometry observes recurring, measurable patterns in language use, such
  as how often common words recur. It does not read meaning, topics, or intent."
- Visual: token chips (short synthetic tokens, punctuation marks, rhythm ticks)
  gather into aligned rows (Align). Caption: "Conceptual workflow · not an
  analysis result."
- D: 5/7 editorial split, copy left. M: copy, then a static 2-row chip field.

## S3 Corpus — "A corpus is already an argument."
- Copy: "Genre, date, edition, audience, source, rights, and OCR shape what a
  comparison can mean. Delta asks you to document texts before any analysis."
- Visual: three restrained document ledger cards (Work / Date / Genre / Audience /
  Edition / Source / Rights). One card shows "Rights: Unknown" in amber linked to
  a visible limitation line: "Unknown values stay visible and block public export."
- Motion: cards rise 12px + fade (Qualify). M: cards stack. Amber only here.

## S4 Parameters — "One setting is not evidence."
- Copy: "Guided comparisons run 100, 300, 500, and 1,000 most-frequent-word
  settings together. 500 MFW opens first as a pre-specified display reference —
  not a best or optimal setting."
- Visual: four equally weighted lens cards (100/300/500/1000 MFW), identical
  chrome; density of the token glyph field varies across them. No star, no badge,
  no winner. D: one row of four. M: 2×2 grid. Motion: simultaneous equal reveal
  (Compare).

## S5 Evidence — "Distance is a relation, not a verdict."
- Copy: "Nearer means more similar measured patterns inside this corpus and this
  setting. The numerical distance matrix is the primary evidence; the heatmap and
  the MDS projection are renderings of the same matrix."
- Visual sequence (three stacked schematics, revealed in order; RM: all visible):
  1. structural distance matrix (cells show "·", no numbers),
  2. heatmap schematic (greyscale-teal ramp, caption: colour scale is local to
     the selected matrix),
  3. MDS schematic (unlabeled axes; caption: "Axes have no literary meaning;
     apparent clusters can be projection artefacts.").
- Label on the group: "Structural schematic · no result values." No fixture data
  is used (rights/provenance simplest path; see asset manifest).

## S6 Uncertainty — "Keep what changes visible."
- Copy: "A persuasive picture can still be sensitive to corpus composition,
  parameters, and projection. Delta keeps all four comparisons and every corpus
  warning side by side — there is no winner-takes-all view and no confidence
  score."
- Visual: the four S4 lenses reappear smaller, side by side, each with its own
  tiny matrix; one coral boundary line beneath: "Do not conclude: nearer does not
  mean the same author, influence, intention, or authenticity." (Qualify)

## S7 Record — "Take the record, not just the picture."
- Copy: "Delta is designed to preserve the corpus description, method settings,
  numerical outputs, rights summary, and declared interpretation limits of every
  run as a FAIR-oriented record."
- Visual: a single ledger card listing Run reference · Corpus documentation ·
  Parameters · Matrix output · Rights summary · Interpretation boundary · Export
  record, each row settling with a subtle tick (Record).

## S8 Final CTA — "Bring your corpus. Keep the choices visible."
- Three research paths as plain cards (existing catalog copy): Compare Texts ·
  Compare Groups · Trace Style Over Time (one line each, no invented claims).
- Primary CTA: "Open the workbench". Below: "Public alpha · Experimental" and a
  quiet footer (method boundary sentence + documentation links).
- The narrative ends; the workbench itself is untouched by any of this motion.

## Motion & state matrix
| State | Behaviour |
|---|---|
| Forward scroll | Sections reveal once at ~20% visibility; transforms ≤24px |
| Backward / fast scroll | Revealed state persists; no re-trigger, no invalid states |
| Reduced motion | All reveals pre-applied; zero transform/opacity animation |
| Save-Data | Identical (no heavy media exists to skip) |
| No JS | All content visible; anchors and CTA work; header details element native |
| Keyboard | Skip link → header nav → CTA → in-order landmarks; visible focus |
