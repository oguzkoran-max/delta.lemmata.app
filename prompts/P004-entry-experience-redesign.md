# P004: Beginner-First Entry Experience Redesign

## Role

Act as a senior product designer, digital-humanities methodologist, accessibility
specialist, and Streamlit frontend engineer. Work inside the existing Delta design
system and repository contracts. Do not redesign later corpus, rights, Review, or
analysis boundaries unless an entry-page change requires a narrowly scoped update.

## Product Context

Delta is an English-only scholarly stylometry workbench. Its promise is not
automatic interpretation. It removes the requirement to learn R or Python for the
supported workflow while keeping corpus documentation, method selection, rights,
limitations, and interpretation visible.

The current build supports secure TXT/ZIP intake and the documented
Upload -> Describe -> Review corpus workflow. It does not yet run scientific
stylometric analysis. The entry experience must therefore teach the method and
orient the user without displaying fabricated result graphics or implying that the
analysis engine is connected.

## Primary Objective

Redesign the initial Purpose/Upload experience so that a person who has never heard
of stylometry can answer, within one screen:

1. What is stylometry?
2. What kinds of textual patterns does it compare?
3. Why might a literary or digital-humanities researcher use it?
4. Which of Delta's three research-question paths fits the present corpus?
5. What can and cannot be inferred from stylistic distance?
6. What will happen after files are selected?

The actual research workflow must remain visible and immediately actionable. This
is a workbench entry surface, not a marketing landing page.

## Audience

- Literary scholars with no programming background.
- Digital-humanities beginners who do not know R, Python, `stylo`, MFW, culling, or
  distance metrics.
- Experienced researchers who need a fast, versioned, transparent route into the
  corpus workflow.

## Required Content

### Opening proposition

- Use the literal product and category as the first signal: Delta, a stylometry
  workbench.
- State plainly that stylometry measures recurring language choices across texts.
- Name beginner-readable examples: frequent words, function words, and their
  distributions.
- Explain the benefit: compare texts, examine documented groups, and trace change
  across dated works without writing R or Python.
- State that every comparison is relative to the uploaded corpus.

### Conceptual method map

Show a compact, semantic three-part sequence:

1. Observe recurring language patterns.
2. Compare those patterns across documented texts.
3. Interpret relative evidence with dates, editions, genre, source, and rights.

Label it explicitly as a conceptual workflow, not a computed analysis result. Do
not use fake charts, distance values, dendrograms, clusters, heatmaps, or result
previews.

### Research-question choice

Present three plain-language choices:

- Compare Texts
- Compare Groups
- Trace Style Over Time

For the selected choice, keep the working question, appropriate use case, and
interpretive boundary visible without requiring an expander.

### Epistemic boundary

Stylometric distance may support comparison and hypothesis formation. By itself it
must never be presented as proof of authorship, authenticity, intention, influence,
ageing, maturation, a turning point, or causation. Metadata completeness is not
scientific sufficiency or legal permission.

## Information Architecture

1. Keep the compact Delta product header.
2. Add one full-width, unframed entry band with an H1, concise explanation, and
   conceptual pattern sequence.
3. Place the research-question control immediately after the entry band.
4. Display selected-purpose guidance as a stable three-column evidence strip on
   desktop and a readable stack on small screens.
5. Show the four-step documentation map next.
6. Preserve a visible hint of the Upload work surface in every supported first
   viewport.
7. Do not add a splash screen, modal onboarding, carousel, login, account, sample
   result, or extra navigation layer.

## Visual Direction

- Quiet, editorial, scholarly, and precise rather than promotional.
- Use a dark ink/forest entry band with paper-white type and restrained teal,
  coral, and blue accents. Avoid a one-hue interface.
- No gradients, decorative blobs, bokeh, floating section cards, or nested cards.
- Corners must remain at 8px or below.
- Use a serif display face only for the entry H1; retain the system sans-serif for
  controls and operational copy.
- Use the conceptual sequence and typographic pattern field as the visual asset.
  It must be code-native, responsive, non-interactive, and hidden from assistive
  technology where decorative.
- Keep body copy compact. Teaching should clarify decisions, not delay file upload.

## Accessibility

- One semantic H1 on the Upload entry surface.
- Logical heading order and named regions.
- Purpose guidance must update accessibly after selection.
- Minimum 44px interactive targets.
- Minimum 14px purpose labels on narrow screens; never force three compressed
  labels into one unreadable row.
- Visible 3px focus treatment for buttons, links, inputs, selects, comboboxes,
  summaries, upload targets, and focusable regions.
- Do not use color as the only carrier of meaning.
- Respect `prefers-reduced-motion`.
- Maintain WCAG AA contrast and zero page/control overflow at 1440x1000, 1280x800,
  640x800, 390x844, 360x800, and 320x800.

## Immutable Boundaries

- Preserve all P003 secure-intake validation and payload-clearing behavior.
- Preserve P004 canonical metadata, rights, hashing, correction, and confirmation
  contracts.
- Do not connect R, Python analysis, AI, external services, analytics, storage,
  login, deployment, or the parent lemmata.app site.
- Do not retain or echo uploaded text.
- Do not weaken unknown-rights blocking.
- Do not claim general usability, legal certainty, or scientific sufficiency.

## Implementation Deliverables

1. Centralized English catalog copy for the beginner entry experience.
2. Semantic Streamlit/HTML rendering integrated with the existing Upload stage.
3. Responsive CSS within the existing visual system.
4. Updated AppTest coverage for copy, hierarchy, purpose switching, and absence of
   prohibited claims or fake result visuals.
5. Expanded browser audit for first-viewport composition, readable purpose
   controls, semantic regions, focus coverage, responsive geometry, and unchanged
   individual-TXT/ZIP flows.
6. Desktop and mobile screenshots retained as FAIR evidence.
7. PromptEvent, Ticket, checkpoint, validation report, exact-commit, CI, and human
   acceptance updates under the existing P004 boundary.

## Completion Gate

The redesign is complete only when:

- a beginner can state what stylometry does and select a research question from the
  visible copy;
- the upload task remains visible or clearly begins within the first viewport;
- all existing P004 flows and security boundaries still pass;
- every automated source, schema, provenance, accessibility, and browser gate is
  green;
- failed intermediate attempts are retained and not described as passing;
- Oğuz Koran completes the revised Safari/keyboard/VoiceOver human walkthrough and
  explicitly accepts or rejects P004.
