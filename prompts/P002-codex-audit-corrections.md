# P002 Codex Audit Corrections

## Native Request

`önerilerinle devam edelim`

SHA-256 is recorded in `PE-20260711-0001`. The request accepted the findings in
Codex's immediately preceding independent review of Claude's P002 audit branch.

## Objective

Resolve the two merge-blocking provenance findings and the evidence-backed P002
accessibility, responsive, heading, and user-copy findings without implementing
P003 ingestion or stylometric computation.

## Non-Negotiable Constraints

- Work on a new `codex/` branch based on the unmerged Claude review branch.
- Do not merge to `main`.
- Preserve prior P002 and Claude evidence files byte-for-byte.
- Correct historical mistakes through explicit errata and superseding records.
- Use path-qualified configuration hashes in new Run records.
- Call 320px and 640px checks reflow tests, not real browser zoom.
- Do not claim full screen-reader, packet-capture, or WCAG conformance.
- Keep runtime AI, ingestion, `stylo`, login, analytics, and storage out of scope.

## Acceptance

1. P002 links the Claude and Codex PromptEvents, decisions, Runs, commits, agents,
   and supplemental evidence.
2. Run schema 1.1 makes configuration paths, replay scope, supersession, and
   evidence manifests machine-readable while preserving schema 1.0 records.
3. Disabled controls visibly explain why they are unavailable; disabled buttons
   include that state in their accessible names.
4. Mobile starts without the sidebar covering the primary workflow.
5. The heading outline is one `h1` followed by peer `h2` sections.
6. User-facing copy contains no P-ticket jargon.
7. A tracked browser harness verifies desktop, mobile, 320/640px reflow, keyboard
   selection, disabled states, heading order, and observed browser requests.
8. Full verification and a clean-clone replay pass against an existing commit.
