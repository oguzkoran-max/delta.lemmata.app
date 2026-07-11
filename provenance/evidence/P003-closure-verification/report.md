# P003 Exact-Commit Closure Verification

## Result

- Status: passed
- Run: `RUN-20260711-0005`
- Tested commit: `d99aa7158caa8ba78ac8b2c1810eb61d9d21b8a2`
- Command: `./scripts/verify.sh`
- Started: 2026-07-11T19:16:21Z
- Ended: 2026-07-11T19:16:30Z
- Exit code: 0

The command was run only after the P003 human acceptance, decision-context,
adversarial review, Ticket closure, claim, threat, memory, and handoff records
were committed. The working tree was clean before execution and remained clean
after execution.

## Passed Gates

- Ruff format and lint
- strict mypy
- 232 tests
- 100 percent measured statement and branch coverage
- metadata validation
- JSON and JSONL schema validation
- reciprocal Ticket, Run, PromptEvent, HumanDecision, commit, artifact, and
  evidence-manifest integrity checks
- repository hygiene scan
- supply-chain policy checks
- locked R environment gate

## Boundary

This Run verifies the committed P003 closure tree and repository gates. It does
not repeat the human browser interactions, validate metadata semantics or rights,
execute `stylo`, establish production retention, or test deployment isolation.

The Run record and this evidence are added in the following documentation commit
and therefore do not claim to hash or test their own future Git objects.
