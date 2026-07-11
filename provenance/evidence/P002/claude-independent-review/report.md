# P002 Claude Independent Audit and Repair — Review Report

**Reviewer:** Claude Opus 4.8, independent second-model audit (the P002 shell was
implemented by OpenAI Codex).
**Branch:** `claude/p002-independent-audit` (from `main` / commit `bef9dcc`).
**Apply-fixes commit:** `0788a6e94a46df984c88f65be8841e0ef9d3bb24`.
**Date:** 2026-07-10. **Not merged to main.** Left for Codex review.

## Verdict

**Accepted — 91 / 100.** Zero open P0 or P1. The completed P002 acceptance suite,
the post-fix full verification, the four-viewport browser + zoom audit, and a
clean-clone rerun all pass. No runtime AI, analytics, login, permanent storage,
or external request. No unverified professional / accessible / reproducible /
easy claim. Deferred items are routed to their tickets or to the owner.

This is not a claim that the shell is "perfect." It is a shell: ingestion,
`stylo`, results, deployment, screen-reader conformance, and the parent-site
launch remain later tickets, and several real-but-lower-risk findings were
deliberately deferred (below).

### Score by rubric

| Dimension | Weight | Score | Note |
|---|---|---|---|
| Product / workflow | 20 | 18 | Honest disabled states, clear purposes; ticket-id jargon fixed; boundary-panel/duplicate-map redundancy deferred as IA. |
| Visual / responsive | 15 | 14 | Quiet workbench; verified at 4 viewports + zoom; dead accent tokens removed. |
| Accessibility | 15 | 13 | One real AA contrast failure fixed; disabled-button help added; heading-level and decorative-border items deferred with reason. |
| Python / Streamlit + tests | 20 | 18 | Clean escaping, deterministic state, 100% coverage, strict mypy; unused `pydantic` and brittle UI tests deferred. |
| Content / epistemic | 15 | 14 | Copy epistemically clean; jargon + tense fixed; minor wording deferred. |
| Security / privacy / FAIR | 15 | 14 | No runtime AI/analytics/endpoint; telemetry off; health safe; all IDs resolve; hashes match; minor prior-run provenance nits documented (cannot overwrite). |

## Method

Six independent read-only reviewer lenses were run in parallel, each with minimal
scoped context and no authority to accept another's output, then synthesized and
re-verified by the main agent against source, tests, rendered DOM, computed
contrast, and provenance hashes. Conflicts were resolved with evidence (see the
heading-level adjudication). Read-only phase produced findings; only then were
fixes applied on the branch. Total audit ran within the briefed budget.

## Most important findings (severity order)

1. **VIS-1 / A11Y-1 (P2, fixed).** The active experiment-map marker rendered
   teal `#116f63` at **2.50:1** on the dark sidebar `#1c2925` — a WCAG AA
   failure for 0.72rem text, and the least legible element in the nav. The
   original `accessibility-report.json` marked this area "passed." Fixed with a
   sidebar-scoped lighter teal `#63b6a6` (**6.30:1**); the white-panel instance
   is unchanged (6.04:1). Independently re-computed three ways.
2. **PROD-1 (P2, fixed).** The primary corpus copy leaked an internal ticket id
   ("until the P003 validation gate passes"). Rewritten in plain language; the
   live DOM scan confirms `p003` is gone.
3. **CON-1 (P2, fixed).** Guided/Research descriptions stated unbuilt function in
   present tense; made future-tense to match the honestly-disabled controls.
4. **VIS-2 (P2, fixed).** Three of four accent design tokens
   (`--delta-coral/amber/blue`) were dead code; removed and documented.
5. **PROD-2 (P2, fixed).** The experiment map was hardcoded twice; unified into a
   shared helper (drift removed, rendering unchanged).
6. **A11Y-5 (P3, fixed)** and **PY-2 (P3, fixed).** Help text added to two
   disabled buttons; the dev-only `runOnSave` watcher turned off.

## Deliberately deferred (real, but out of P002 low-risk scope)

- **PY-1 (P2):** `pydantic` is a declared runtime dependency never imported.
  Removing it touches the locked SBOM and clean-clone gate and may be staged for
  P003 validation — an owner/Codex dependency decision, not a shell fix.
- **PROD-3 (P2):** the selected purpose's boundary sentence appears under both
  "Interpretive boundary" and "Method boundary." Genuine redundancy, but the fix
  is an information-architecture decision reserved for the owner.
- **SEC-1 / SEC-3 / SEC-4 (P3, provenance):** the prior runs carry a top-level
  `config_sha256` (`7baa8295…`) that matches no file (the authoritative per-file
  input-artifact hash is correct), `RUN-0003.git_commit` is null, and the ticket
  flattens two "passed-with-disclosed-scope" gates to "passed." These live in
  existing P002 evidence, which this review must not overwrite. Documented for
  Codex; this review's own Run records use the real raw config hash.
- **SEC-2 (P2, P014):** the egress claim rests on a sandbox, not a packet
  capture, and the config pins no `server.address` — production isolation is
  P014.
- **A11Y-2, VIS-4/A11Y-3, and the P3 tail (CON-2/3/4, PROD-4/5, VIS-3/5/6/7,
  A11Y-4, PY-3/4):** taste, wording, live-render-dependent, framework-driven, or
  a reviewer-disagreed heading nuance where any edit trades one minor imperfection
  for another. See `findings.json`.

## Tests actually run (real results)

- `./scripts/verify.sh` (post-fix, commit `0788a6e`): **exit 0** — ruff
  format+lint, strict mypy (7 files), **40 pytest passed, 100% measured coverage**
  (224 stmts), metadata/records/repository/supply-chain/R-lock. → `RUN-20260710-0005`.
- Playwright headless-Chromium browser audit at 1440×1000, 1280×800, 390×844,
  360×800 + a 200%-zoom emulation: **passed** — 0 horizontal overflow, 0 external
  assets, 0 unnamed viewport-visible controls, 0 prohibited-copy hits. →
  `browser-audit.json`, `screenshots/`.
- Streamlit AppTest smoke: no exceptions; all four future controls disabled;
  deterministic purpose/mode switching. → `smoke.json`.
- External-request inspection: all loaded assets loopback; telemetry off. →
  `network-observations.json`.
- Provenance: both original screenshot SHA-256 match on disk; every ticket-
  referenced ID resolves; all 17 records validate against schema.
- Clean-clone rerun of `0788a6e`: bootstrap + verify pass, empty `git status`. →
  `RUN-20260710-0006`, `clean-clone-verification.md`.

## Not tested here (honest gaps)

- The macOS-sandbox egress-denied smoke test from the original evidence was not
  re-executed; this review changed only CSS, copy, and one config flag and added
  no network call, so the original `network-trace.json` remains the baseline.
- No screen-reader session and no full WCAG conformance assessment (P008/P009/P015).
- 200% zoom is emulated by halving the CSS layout viewport, not a real browser
  zoom control.
- Production proxy/TLS/CORS/Host/CSRF/shared-VPS isolation are P014.

## For Codex to re-examine

1. **PY-1 pydantic:** remove now, or confirm it is P003's and add a note?
2. **SEC-1 `config_sha256`:** define it in `run.schema.json` or reconcile the
   two prior runs' stale value.
3. **PROD-3 boundary panel:** keep the duplicate, repurpose it, or drop it — an
   IA call.
4. **VIS-4/A11Y-3 heading level:** confirm the deferral, or restructure section
   headings to `h2` so the purpose value can sit below them.
5. Whether to append the two audit commits to `provenance/tickets/P002.json`
   after accepting the branch (this review left the ticket unmodified).

## Provenance

- Native launch request: `PE-20260710-0004` (request hash
  `600466115f16061cd03de54a00b9e4a95df0eaa45ea4832fc924c2ce843edac0`).
- Anticipating human decision: `HD-20260710-0005`.
- Runs: `RUN-20260710-0005` (post-fix verify + browser), `RUN-20260710-0006`
  (clean-clone). The original P002 acceptance evidence is untouched.
