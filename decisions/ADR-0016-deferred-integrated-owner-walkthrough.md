# ADR-0016: Deferred Integrated Owner Walkthrough

**Status:** Accepted

**Date:** 2026-07-15

## Context

P007 source, clean-clone replay, Linux CI, supply-chain gates, canonical image,
desktop/mobile geometry, and automated copy/state checks passed. Its final
prepared-state warning-language walkthrough remains human-owned. Oğuz Koran
previously directed Codex to perform all automated testing and to conduct the
combined owner walkthrough only when the usable site is ready.

Strictly blocking all P008 engineering on that deferred walkthrough would
repeat the same partial flow for the owner and conflict with the accepted
public-alpha sequence. Treating the walkthrough as completed would fabricate
human evidence.

## Decision

P007 remains `in-progress` with AC-09 pending. P008 may become the sole active
implementation ticket while P007 is an acceptance-only hold. No P007 acceptance
claim, general usability claim, or public activation follows from technical
progress. The final owner session must include the P007 warning-language check
before public-alpha activation.

Only one implementation ticket may modify the runtime at a time. P009 and P014
do not begin until the required P008 minimum slice has its own evidence.

## Consequences

- Engineering can reach a coherent upload-to-result flow before asking Oğuz to
  repeat the browser walkthrough.
- P007 and P008 may both display `in-progress`, but their open responsibilities
  are disjoint: P007 human acceptance versus P008 implementation.
- The release checklist must carry the P007 AC-09 item forward explicitly.
- Automated browser checks remain evidence of tested behavior, not evidence of
  generalized ease, learning, or acceptance.

## Evidence Links

- `HD-20260715-0001`
- `provenance/tickets/P007.json`
- `provenance/tickets/P008.json`
- `provenance/evidence/P007/corpus-health-diagnostics-validation.md`
- `provenance/runs/RUN-20260715-0001.json`

