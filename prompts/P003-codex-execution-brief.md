# P003 Codex Execution Brief

## Native Request

`devam edelim`

The exact request hash and its context-bounded interpretation are recorded in
`PE-20260711-0002`. The native request follows a message that explicitly named
P002 live review, main integration, and P003 as the next sequence. This brief is
a durable implementation interpretation, not a second native prompt.

## Objective

Implement the P003 secure-ingestion boundary defined by `prompts/P003-start.md`,
the roadmap, CE-14, and SEC-01 through SEC-05.

## Boundary

- Accept only TXT, ZIP, and metadata CSV.
- Treat every byte, filename, archive entry, and CSV cell as untrusted.
- Validate the complete archive inventory before creating an extraction target.
- Allocate no analysis state for a rejected payload.
- Keep errors, logs, and evidence content-free.
- Keep limits centralized, versioned, deterministic, and explicit.
- Preserve the English-only workbench and expose only controls that are genuinely
  implemented and security-tested.

## Out Of Scope

P004 metadata meaning and rights, P005 lifecycle and retention guarantees, P006
stylo execution, scientific preprocessing, Pinocchio data, production deployment,
runtime AI, additional document formats, and parent-site integration.

## Completion Gate

P003 remains incomplete if any malicious fixture, property/fuzz bound, cleanup
canary, content-free error check, repository verification, or clean-clone replay
fails. Failed attempts remain in the evidence package.
