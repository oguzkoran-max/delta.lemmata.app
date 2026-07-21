# P016: Delta Living Text Observatory — Cinematic Scroll Narrative Prototype

**Recording mode:** transcribed summary of the owner's 2026-07-19 chat brief
(full native text lives in the owner's session transcript; this file is the
repository record and is hashed in `provenance/evidence/P016/MANIFEST.sha256`).
It is not presented as a native/exact prompt capture.

## Mission
Design and implement a high-fidelity, **local-only** prototype of a more
memorable Delta entry experience named **Living Text Observatory**: scroll as
narrative (not decoration), "contemporary scholarly publication meets precise
research instrument". The metaphor is the pipeline: text fragments → recurring
measurable features → documented comparison → distance matrix → interpretive
limits → preserved run record. The scientific workbench itself must remain
unchanged, fast, readable, accessible, epistemically careful.

## Authority
Allowed: read-only inspection (repo + live), isolated branch/worktree, local
static prototype, code-native animation, local browser testing, screenshots,
evidence, local commits after verification.
Forbidden without separate explicit owner instruction: merge, push, DNS/Caddy/
nginx/container/systemd/TLS/production changes, moving the workbench URL,
roadmap changes, paid (Higgsfield) generation, deployment, weakening security/
tests/coverage/accessibility/scientific boundaries.

## Key constraints (enforced)
- P002/P004 direct-workbench decision acknowledged; P016 = reversible proposal.
- Multi-agent workflow ≤160k tokens; ≥5 independent review roles (visual
  director, architecture, scientific-claim, a11y+performance, adversarial
  final); reviewers report, primary agent adjudicates.
- Mandatory reading list (contract, memory, roadmap, P004 prompt, phase-B,
  P014 evidence, claim matrix, threat model, catalog/webapp/ui_theme, deploy
  configs) — completed; conflicts reported, not silently resolved.
- Scientific contracts: R stylo canonical; 100/300/500/1000 MFW together; 500 =
  pre-specified display reference (never "best"); matrix primary; heatmap local
  scale; MDS axes meaningless; unknown stays holdout; proximity ≠ authorship/
  causation; confounds remain; "Public alpha · Experimental" visible; claim
  denylist (accuracy/reliability/confidence/easy/award/$-value/…): applied via
  `provenance/evidence/P016/claim-evidence-map.md`.
- Video reference (Fable5+Higgsfield workflow) = production-method reference
  only; its palette/orbit/cursor/HUD/frame-scrub/claims are explicitly excluded.
- Creative direction fixed: Living Text Observatory; two alternatives (Night
  Research Instrument, Critical Edition Atlas) documented as limited/rejected.
- Storyboard S0–S8 fixed (header/hero/observe/corpus/parameters/evidence/
  uncertainty/record/final CTA) with exact copy rules per section.
- Motion grammar: Gather/Align/Compare/Qualify/Record; native scroll; no
  hijack/Lenis/GSAP-by-default; transform+opacity; UI 180-240ms, narrative
  500-700ms; no pinned scene >1.2vh; DOM-order text; off-screen animations stop;
  progressive enhancement; no-JS keeps proposition/limits/CTA.
- Routing ADR required (A: app subdomain; B: /workbench path; C: root workbench
  + /how-delta-works story) — recommendation + owner decisions; no production
  routing in this pass. Gateway worker_connections/keepalive constraint must be
  re-verified and treated as production prerequisite.
- Higgsfield: optional, design-time only, zero credits this pass; asset manifest
  with REUSE/CODE-NATIVE/GENERATED-OPTIONAL classes; verbatim concept prompt
  retained in the owner brief for a possible later approved run (restrained
  editorial motion study, forest/ivory/teal, no people/products/neon/HUD/fake
  interfaces, 16:9 ≤6s 24fps silent, ~42% calm area).
- Budgets: LCP poster 100-200KB (unused — code-native), first transfer <500KB,
  optional later motion ≤1.5MB lazy; LCP ≤2.5s, CLS ≤0.1, INP ≤200ms; measure,
  don't guess; WCAG 2.2 AA targets incl. 44px, 4.5:1, zoom 200%, 320px no
  overflow; manual VoiceOver explicitly reported as not completed if not done.
- Verification matrix: 1440/1280/1024/390/375/320; normal/reduced-motion/
  Save-Data/no-JS/keyboard; forward/backward/fast scroll; resize-after-scroll;
  refresh mid-scroll; CTA nav; zero console errors/failed requests/third-party
  origins/overflow/focus traps/hidden CTA.
- Repository gates must stay green (verify.sh, coverage, browser gates); no
  threshold weakening; baseline failures distinguished from P016 regressions.
- Deliverables 1-11 (baseline audit → adversarial review) live under
  `provenance/evidence/P016/`; prototype under
  `prototypes/p016-living-text-observatory/`.
- Final report format fixed (17 items); Deployment status must be
  `NOT DEPLOYED - local prototype only`.
- Prohibited final claims: one-prompt/from-scratch/real-3D/$10k/award/
  production-ready/fully-accessible/all-tests-passed(without runs)/no-AI/
  deployed/data-is-real/authorship-proof/best-parameter/reliable/easy.
- Stop conditions: user-change overlap, destructive git, paid generation,
  permission bypass, unclear licence, production access, unresolvable claim
  conflict, pipeline change, provenance cannot represent work.
