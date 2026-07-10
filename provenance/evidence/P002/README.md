# P002 Evidence Index

P002 establishes the English-only workbench shell. It does not establish secure
ingestion, scientific computation, production isolation, or general usability.

## Artifacts

- `report.md`: human-readable acceptance synthesis, failures, and limitations
- `clean-clone-verification.md`: restoration and verification of the committed snapshot
- `browser-audit.json`: desktop/mobile geometry, naming, copy, and asset audit
- `accessibility-report.json`: keyboard and visible-control evidence
- `network-trace.json`: egress-denied shell observations and negative controls
- `copy-snapshot.txt`: deterministic snapshot of all 90 English UI strings
- `desktop-1440x1000.png`: accepted desktop rendering
- `mobile-390x844.png`: accepted mobile rendering

Machine-readable execution metadata is in `provenance/runs/RUN-20260710-0003.json`
and `provenance/runs/RUN-20260710-0004.json`. The development request is
represented by its native-message hash in PromptEvent `PE-20260710-0002`; the
repository does not claim to store a complete response transcript.
