# P016 Baseline Audit (read-only, before any prototype file)

Date: 2026-07-19 · Agent: Claude Code (P016 session) · Mode: inspection only.

## Git and worktree
- Branch at inspection: `main`; HEAD `38eafeb` ("P014: Canli deploy kaydi...");
  parent merge `31e0978` (PR #15, 21 commits). Working tree clean; no stash use.
- Remote: origin = github.com/oguzkoran-max/delta.lemmata.app (public since
  2026-07-19, owner instruction).
- Second worktree `delta-p014-gateway-real-ip` (branch `codex/p014-gateway-real-ip`,
  Codex-owned) — untouched.
- Prototype branch created after this audit: `claude/p016-living-text-observatory-prototype`.

## Live deployment evidence (immutable sources, not assumed)
- `https://delta.lemmata.app/_stcore/health` → `ok` at audit time.
- Live container env `DELTA_BUILD_ID=31e09782ba07e6709cbdcca48bc9db22e6c49723`;
  image `ghcr.io/...@sha256:80836f17...` (publication workflow run 29696211566).
- Deployment record: SESSION_HANDOFF entry in commit `38eafeb`; release dir
  `/opt/delta-public-alpha/releases/31e0978...` with env/unit/Caddy backups.
- Known gap: no canonical HumanDecision/Run record exists yet for this
  owner-approved deployment (flagged in `adr-proposal-routing.md` decisions).

## Baseline verification (clean HEAD, before prototype)
- `bash scripts/verify.sh` → PASS: 1751 passed / 1 skipped; 11,718 statements,
  3,056 branches, 100% measured coverage; ruff/mypy/schemas/records(119)/
  repo-scan/R-lock all green. Log retained locally (`p016-baseline-verify`).

## Current experience baseline (desktop/mobile, this session's evidence)
- Entry: hero + 3 purpose cards + tri-cell guide + centered 4-step stepper +
  upload card; sidebar Start-here + Preparation summary; footer boundary.
- Typography: body 16-17px; micro-label floor 12px; hero 2.55rem Inter.
- Journey: Purpose → Corpus (Upload→Describe→Review→Prepare) → Parameters →
  Evidence; states for empty/loading/warning/error/complete per catalog.
- Accessibility semantics: one H1, skip link, promoted `main`, named scroll
  regions, 44px targets (Phase B contract; CI-gated).
- Network: self-hosted fonts; no third-party origin (CI no-egress gates).
- Known visual defects (open, documented in P014 design-review README): MDS
  square overlap hides holdout point at wide layouts (deferred recalibration);
  worker RLIMIT_AS crash suspicion (intermittent CI); gateway
  worker_connections 128 capacity ceiling (production).
- Known contract pins that any new surface must not break: entry fold budget
  (mobile upload button y ≤ 780 at 375/390), purpose-guide mobile order, MDS
  square frame ±2px, semantic table parity, claim denylist.

## Conflicts identified (no silent resolution)
1. START_HERE/roadmap/phase-b say public route unchanged & pre-Caddy gate
   pending vs. actual 2026-07-19 owner-approved deployment (source: session
   handoff `38eafeb`). Consequence: stale onboarding docs; owner decision listed.
2. P002/P004 direct-workbench decision vs. P016 narrative exploration —
   resolved by scope: P016 is a reversible prototype + ADR proposal only.
3. Threat model lacks the measured gateway capacity constraint — recorded here
   and in the ADR proposal as a production prerequisite.

## Canonical commands (discovered, used for gating P016)
- Full gate: `bash scripts/verify.sh`
- Focused tests: `.venv/bin/python -m pytest …`
- Browser evidence pattern: Playwright scripts under `scripts/browser_audit*.py`
  (P016 uses a separate local harness; it does not modify these gates).
