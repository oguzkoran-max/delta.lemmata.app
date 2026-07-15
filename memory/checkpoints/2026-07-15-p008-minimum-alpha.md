# P008 Minimum-Alpha Checkpoint

## Verified Implementation

- Exact commit: `7e9a28eafa4756b2cf82e6d6f3d8e0c43742edf5`
- Run record: `RUN-20260715-0002`
- Evidence: `provenance/evidence/P008/minimum-alpha-workflow-validation.md`
- Canonical Linux CI: `29388984019`
- Linux verify: 1,459 tests, no skip, 100% of 10,624 statements and 2,764 branches
- Browser gate: real upload-to-P007 preparation-to-P006 R/stylo validated result
- Clean clone: remote no-hardlinks detached checkout, bootstrap and full verify passed,
  post-run tree clean

## Exposed Alpha Boundary

Guided Mode resolves exactly four whole-text Classic Delta cells: 100, 300, 500,
and 1000 MFW with zero-percent culling, seed 20260713, and a fixed 500-MFW
reference that is not described as optimal. Research Mode is visible but locked.
The reviewed configuration is canonical and hash-bound to one-time P007 READY
admission before the existing P006 worker runs it.

## Retained Limitations

- P008 remains `in-progress`; AC-09 still requires all three research purposes and
  relevant known/unknown browser scopes for full closure.
- `research-grid-v1` remains undefined until a separate human method decision.
- P008 stops at the validated result boundary. P009 owns export-backed completion,
  result graphics, explanations, and interpretive guardrails.
- The integrated P007 owner warning-language walkthrough remains deferred to the
  final pre-activation session under ADR-0016.

## Next Boundary

Open minimum P009 schema-first. Use only fields actually available in P006 output.
Deliver a distance-matrix heatmap, nearest-neighbor table, one work-level 2D map,
and all four parameter-cell states with accessible table parity and explicit
`What this shows` / `What this does not show` text. Do not introduce confidence,
authorship proof, pure-style, or causal age/maturity claims.
