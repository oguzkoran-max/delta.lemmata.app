# Generated Asset Provenance — styleframe-01 (hero key visual)

- Tool: Higgsfield MCP (owner-connected account, free plan)
- Model: nano_banana_2 (requested as nano_banana_pro; server resolved)
- Generation date: 2026-07-22
- Job/generation id: a21e161c-ae86-4d6b-ba03-cc8dc371ddc6
- Cost: 2.0 credits (preflighted with get_cost; balance 8.35 → 6.35)
- Dimensions: 1376×768 (16:9, 1k)
- Complete prompt: recorded verbatim in the job params (see id above); summary:
  monumental corpus sculpture of archival paper strata with fragmented serif
  letterforms, punctuation, interval ticks and fine analytical lines, deep
  forest-black museum space, ivory/bone fibre material, restrained emerald
  accents, one copper annotation edge, upper-left museum key light, European
  editorial art direction, calm left negative space.
- Exclusions (in-prompt): no readable words/sentences, no author names, no
  numbers, no dashboard/UI/charts, no neural network, no glowing orb, no
  purple neon, no cyberpunk, no glassmorphism, no human figure, no book
  mockup, no logo, no watermark.
- Content check (manual): letterform glyphs (A, g, M, ;, ,) only — no readable
  prose, no numerals, no results, no faces, no marks. PASS.
- Reference asset: none (canonical first frame).
- Editing history: downscale 1600w + JPEG q82 via sips; no retouching.
- Intended use: DECORATIVE Act I key visual ("the corpus, before analysis") in
  prototypes/p017-delta-cinematic-narrative/; fades out by scroll p=.125 as the
  schematic SVG twin takes over; mobile stacked s1 hero art. Page caption
  "Conceptual visualisation · not an analysis result" remains on stage.
- Usage-rights basis: generated on the owner's Higgsfield account under the
  service's user-content terms; owner-authorized session generation.
- SHA-256 original (PNG, 1,415,289 B):
  2e0a6f6ee71848cdb1154e5b038993fda61ec5b5f4dfde60c2683ea9038ef41d
- SHA-256 optimized derivative (keyvis-hero.jpg, 210,883 B, 1600×893):
  5118784cdefae4d76c3c52c1b4331dc18e748e2781448cd064d1ebff44fac58b
- Final output format: JPEG (WebP encode unavailable via sips on this host;
  within the ≤450 KB hero-poster budget).

---

# styleframe-02 (Act II · separated strata) — reference-guided edit
- Model: nano_banana_flash (reference edit of styleframe-01); date 2026-07-22
- Job id: adae4a8a-c6d9-4ae4-a41f-f499c60ad58a; reference: a21e161c-...ddc6
- Cost: 2 credits. Prompt: same sculpture, strata separated vertically with
  visible gaps, same material/light/camera; full text in job params.
- Content check: glyphs only (A, g, M, ;), no words/numbers/faces/marks. PASS.
- Use: DECORATIVE stacked-mode Act II art (mobile/no-JS/reduced-motion),
  radial-mask melt; cine mode remains SVG-driven.
- SHA-256 original: 9d7b05fdf5a1f2bf55c693c65abe944b6b2b5c366487ac6621513794a57b8e12
- SHA-256 derivative keyvis-02.jpg (215,665 B):
  409e4c28e6ab2af4888a6fbe810deec1dd37ec20e1f728db6cb3111ca674d8f4

# styleframe-03 (Act VI · sealed record volume) — reference-guided edit
- Model: nano_banana_flash (reference edit of styleframe-01); date 2026-07-22
- Job id: ab0aee25-9042-4e1c-a00a-0dc4f65174af; reference: a21e161c-...ddc6
- Cost: 2 credits (balance after the family: 2.35). Prompt: same sculpture
  bound into a sealed archival volume, one emerald band, copper spine, stone
  plinth, same room/light; full text in job params.
- Content check: glyphs + abstract erosion marks only. PASS.
- Use: DECORATIVE stacked-mode Act VI art, radial-mask melt.
- SHA-256 original: 087d6f833d077009c5c5d0c360851479f34f49c7390883eb1b733574ee8743d0
- SHA-256 derivative keyvis-03.jpg (213,378 B):
  564e3d72b690205f87dbec1ec306d065af78559f83167f3b67770fc3e6c6cb82

---

# motion-01 (Act I hero motion loop) — owner-generated on higgsfield.ai
- Tool: higgsfield.ai web UI (owner's account, site free-trial "Unlimited"
  tier), model Seedance 2.0, image-to-video, 8.06 s, 1280x720, silent.
- Take 1 REJECTED (recorded honestly): generated without the start image
  attached; the model read "corpus sculpture" literally and produced an
  inscribed human effigy — violates the no-human-figure and no-readable-text
  exclusions. File kept by the owner outside the repo; not used.
- Take 2 ACCEPTED: floating deckled paper stack in a dark archive room, warm
  upper-left key light, dust motes; no humans, no readable text, no logos.
  Same material family as the styleframes; edge-melt mask hides the differing
  background. Motion verified during playback (distinct frames at 1.0/2.6/
  4.2/5.9 s).
- Source file: hf_20260722_090949_2d28e9b9-98c8-46d0-a971-92ebf74a5ca8.mp4
- SHA-256 original (7,951,936 B):
  61b2091b87a7a4757d58bd96254d1e9bffecbee8f14589a3909018f9de4ebe60
  (archived as motion-01-original.mp4)
- Derivative: keyvis-hero.mp4 — avconvert Preset960x540, 3,859,596 B
  SHA-256: 3ae4e7928787c389d1b01d8280c938a2c4c524d7757ab8641dbf3b21de685ddd
- Integration: cine mode only; <video muted loop playsinline preload="none">
  with the styleframe JPEG as poster (poster stays the LCP); src attached by
  JS only when Save-Data is off; plays only while Act I is on stage (pauses
  past p=.16); stacked/mobile/no-JS/reduced-motion never load it.
