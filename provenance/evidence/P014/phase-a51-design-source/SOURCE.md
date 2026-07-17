# Claude Code Phase A5.1 Design Source

## Provenance

- Producer: Anthropic Claude Code
- Phase: A5.1 focused visual prototype revision
- Original export location: owner-local Desktop export; absolute path redacted
- Original export date: 2026-07-17
- Original manifest SHA-256: `9eb0f4466c65be202733920dfd9c8632eea4b29a409cbad66f2acc38cd8dd866`
- Original Claude report SHA-256 before path-only redaction: `030fa408755c1ecb0f691774b3ad799ce686d0f058f6fd4c3c39c6782008c93f`
- Phase B base commit: `26947e1f6843b2b4dc1d1b0cc552c0af808be3fa`

`ORIGINAL-MANIFEST.sha256` preserves the 24 hashes received with the export.
Repository hygiene required one path-only redaction in `measurements.md`; no
design, measurement, image, HTML, constraint, or scientific content changed.
`claude-phase-a51-report.txt` likewise replaces only its owner-local absolute
path. `MANIFEST.sha256` verifies the repository-safe derivative and includes the
redacted report. Run `shasum -a 256 -c MANIFEST.sha256` in this directory.

## Boundary

These files are design-source evidence, not application output and not a
scientific result. The HTML files are static specimens. Their result values are
identified in the source report as frozen synthetic fixture data. The real
Streamlit implementation, R/`stylo` execution, responsive behavior, privacy
lifecycle, and result export require their own tests and exact-commit evidence.

The owner-local origin is retained at the semantic level without publishing a
machine-specific path. This Git-backed copy is the durable, independently
retrievable source used for Phase B review.
