# P008 Start Prompt: Guided and Research Workflows

## Instruction

Continue Delta from the exact verified P007 baseline on branch
`codex/p008-workflows`. Build P008 schema-first and tests-first. The immediate
public-alpha objective is one honest whole-text Guided path from a P007 READY
receipt to a validated P006 result. Do not widen the result, benchmark,
stability, FAIR-release, case-study, or deployment claims owned by later
tickets.

## Accepted Method Boundary

- Guided Mode runs the declared 100, 300, 500, and 1,000 MFW cells with 0%
  culling, whole text, and Classic Burrows's Delta.
- The 500-MFW cell is a fixed reference, not a best setting.
- Every requested cell remains visible. An unavailable MFW cell is reported as
  `not enough features`; it is never replaced by a smaller value.
- Known works alone determine MFW order, culling eligibility, means, standard
  deviations, and fitting state. Unknown works are projection-only.
- All-known work is labelled `transductive_exploratory`; a declared unknown is
  labelled `unknown_holdout`. Neither label is a confidence or authorship claim.
- The public Research preset remains locked until its exact, versioned, hashed
  grid is accepted. Its hard ceiling is 24 cells. Do not invent the remaining
  culling or segmentation choices to meet the alpha date.
- P006 remains the only numerical engine boundary. Do not reproduce Delta
  calculations in the web layer.

## Architecture Boundary

- The P007 READY authority is one-time, expiring, and hash-bound.
- Resolve and hash the complete workflow configuration before admission.
- Persist exactly the resolved request that is reviewed. A changed corpus,
  receipt, role, parameter configuration, or request payload fails closed.
- READY consumption and queue transition remain one SQLite transaction.
- Public code must not bypass `PreparedCorpusService` to enqueue a P006 job.
- Streamlit state may retain content-free projections and opaque ownership
  material only; never raw/prepared text, tokens, features, server paths,
  capabilities, secrets, or result matrices.
- A process exit code is not scientific success. Show success only after P006
  schema validation, semantic validation, durable result persistence, and
  guardian acknowledgement.

## UX Boundary

- Keep the interface English-only for v0.1 and consistent with the Lemmata
  family palette.
- Explain MFW, culling, whole text, and Delta in plain language before Run.
- Show available and unavailable cells, estimated cell count, fixed reference,
  analysis scope, and a complete review-before-run summary.
- The minimum alpha may expose Guided Mode and visibly lock Research Mode.
- Preserve keyboard, mobile/reflow, semantic-table, and no-horizontal-overflow
  behavior.
- Never describe the workflow as easy, validated, objective, accurate,
  reproducible, FAIR-certified, or proof of authorship.

## Required Sequence

1. Open a native P008 Ticket, PromptEvent, decision/ADR links, contract, and
   checkpoint.
2. Add closed workflow-config models, strict parsing, canonical serialization,
   generated JSON Schema, and adversarial tests.
3. Bind the resolved config to private P006 input construction without changing
   the frozen P006 wire schema.
4. Add a server-side runner/orchestration service with content-free status,
   cancellation, retry, and partial-result semantics appropriate to the exposed
   alpha path.
5. Add Parameters, Review, Run, and progress surfaces.
6. Add real browser E2E and exact-commit Linux/clean-clone evidence.
7. Keep P009 result interpretation and P014 deployment work separate.

## Stop Conditions

Stop and record the blocker instead of improvising when:

- an exact Research grid or segmentation value requires a new human method
  decision;
- a requested path would weaken P007 admission or P006 validation;
- raw text or private identifiers would enter public state or provenance;
- a failed cell would be hidden or silently replaced;
- the public-alpha date would require bypassing a privacy, calculation,
  explanation, resource, isolation, rollback, or Lemmata smoke gate.

