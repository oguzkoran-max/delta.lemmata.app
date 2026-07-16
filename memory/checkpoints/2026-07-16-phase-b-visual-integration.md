# 2026-07-16 Phase B Visual Integration

- Source: Claude Code Phase A5.1 export, manifest 24/24 verified.
- Branch/base: `codex/p014-visual-phase-b` from
  `26947e1f6843b2b4dc1d1b0cc552c0af808be3fa`.
- Integrated: Entry, Review, Results, shared responsive tokens, native radio
  cards, local Inter, semantic tables, evidence-first charts, accessibility
  landmarks, and 44 px target sizing.
- Scientific invariants: P006-P009 unchanged; 500 MFW is a display reference,
  not an optimum; P011/P012 language remains deferred.
- Local gate: 1,666 passed, one Linux-only skip, 11,507 statements and 3,002
  branches at 100% measured coverage,
  metadata/provenance/repository/R-lock checks passed.
- Browser/packaging: four comparison cards remain visibly exposed; the skip
  link focuses the content-start target while the app keeps one real main
  landmark; 320/375/390/1440 px have no horizontal overflow, the actual MDS
  plot frame is square within 2 px, and the built wheel contains the font, OFL
  licence, and provenance record with the expected SHA-256.
- Review: independent scientific-method, accessibility, and release reviewers
  returned GO; canonical Linux CI remains required.
- Local real-worker browser limit: closed worker requires canonical
  `/opt/renv/cache`; macOS run failed closed before a result and exposed no
  partial evidence. Canonical Linux CI must supply the authoritative browser
  result.
- Next: exact commit, push, green verify/container CI, independent diff review.
  No merge, image publication, VPS change, Caddy/DNS, or public activation.

Full record: `docs/development/phase-b-visual-integration.md`.
