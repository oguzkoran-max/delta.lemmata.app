# ADR-0015: Accelerated Public Alpha Sequence

**Status:** Accepted by `HD-20260714-0002`

**Date:** 2026-07-14

**Scope:** Public availability sequence, minimum alpha gates, and August 2026
manuscript timing

## Context

The original roadmap placed public beta after the complete benchmark, calibration,
FAIR-package, Pinocchio, deployment, and expert-walkthrough sequence. The product
owner has now prioritized making a real, constrained tool available within two or
three days and preparing the manuscript during August 2026.

Activating the current P004 interface would not meet that request: it validates and
documents uploads but cannot yet prepare text, admit a healthy corpus, execute the
public workflow, or explain real results. Conversely, waiting for every scientific
release gate would prevent early use and feedback even after a bounded path becomes
safe.

## Decision

Target a clearly labeled **Public alpha** by 2026-07-17. Activation is permitted
only after all of the following minimum gates pass:

1. P007 prepares real text deterministically, presents corpus-health blockers and
   warnings, and admits analysis only through a valid one-time READY receipt.
2. A minimum P008 path takes one supported whole-text workflow from accepted upload
   to a validated P006 result without R, Python, or shell work by the user.
3. A minimum P009 surface presents at least the primary distance result and
   nearest-neighbour evidence with a semantic table, downloadable content-free
   record, and explicit `What this does not establish` guidance.
4. The alpha uses bounded Guided settings. Whole text, 0% culling, Classic Delta,
   and supported MFW cells remain explicit; unavailable cells are not silently
   replaced.
5. A minimum P014 safety slice provides a separate Delta service/container identity,
   port, environment, volumes and secrets; TLS and strict Host routing; request,
   rate, file, token, queue, CPU, RAM, PID, timeout and concurrency limits; worker
   egress policy; health checks; rollback; and a passing Lemmata smoke test.
6. The interface says `Public alpha` and `experimental`. It does not claim scientific
   validation, FAIR certification, authorship proof, demonstrated usability,
   publication readiness, or production-grade isolation beyond tested controls.

The full P010-P013 scientific sequence, complete P012 FAIR-oriented run package,
remaining P014 deployment evidence, and P015 expert/release gate continue after
alpha activation. They are not retroactively treated as alpha prerequisites, but
their claims remain locked until their own evidence passes.

The manuscript target moves to a full draft during August 2026. Drafting may begin
only after the required 20-question preparation round, and every empirical claim
must be limited to evidence completed by the drafting date. Missing benchmark,
calibration, Pinocchio, FAIR, or expert evidence is reported as pending or omitted,
not inferred from alpha availability.

## Public Alpha Scope

- English-only interface
- Whole-text analysis only
- No runtime AI, login, analytics, or permanent project storage
- Strict corpus and job limits
- Real P006 `stylo` results, never placeholder graphics
- Content-free default downloads
- Visible warnings and locked unsupported workflows
- No Pinocchio result required for initial activation

## Consequences

- P007 remains the only active ticket until it closes. P008, P009, and the minimum
  P014 slice follow in order under separate records.
- The roadmap distinguishes functional alpha availability from scientific release.
- A date never overrides a failed privacy, admission, calculation, explanation,
  isolation, or rollback gate. Scope shrinks or activation moves.
- Alpha feedback may identify product defects but is not a participant study and
  cannot support general usability or teachability claims.
- Full P014 still owns production measurements and isolation claims after the
  minimum alpha slice.

## Alternatives Rejected

### Activate the Existing Interface Immediately

Rejected because the current build does not run a real public stylometric analysis.

### Wait for the Original November Public-Beta Gate

Rejected because a carefully bounded alpha can provide earlier practical value and
feedback without making later scientific claims.

### Waive Benchmark or Security Evidence to Meet the Date

Rejected. Alpha may narrow its claims and features; it may not fabricate missing
evidence or expose an unbounded shared server.

## Evidence Links

- `HD-20260714-0002`
- `provenance/tickets/P007.json`
- `docs/development/roadmap-P001-P015.md`
- `docs/research/claim-evidence-matrix.md`
- `docs/security/threat-model.md`
- `decisions/ADR-0014-preprocessing-corpus-health.md`
