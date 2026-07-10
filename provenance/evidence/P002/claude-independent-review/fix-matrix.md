# P002 Independent-Review Fix Matrix

Applied only where the change rested on a concrete ground (acceptance violation,
usability/accessibility, code/security/maintenance risk, or wrong/unsafe content),
stayed inside the P002 shell scope, and carried low risk.

| Finding | Severity | Ground | Action | File | Test / evidence |
|---|---|---|---|---|---|
| VIS-1 / A11Y-1 sidebar active-row contrast | P2 | Accessibility (WCAG AA) | Sidebar-scoped `--delta-teal-on-dark` (#63b6a6, 6.3:1); base teal unchanged on the white panel | `src/delta_lemmata/ui_theme.py` | `contrast-proof.json` (2.5→6.3); `screenshots/desktop-1440x1000.png`; `browser-audit.json` |
| VIS-2 dead accent tokens | P2 | Maintenance | Removed unused `--delta-coral`/`--delta-amber`/`--delta-blue`; documented teal-as-primary | `src/delta_lemmata/ui_theme.py` | `verify.sh` (ruff/mypy/40 tests); grep shows no remaining `var(--delta-coral\|amber\|blue)` |
| PROD-1 internal ticket id in copy | P2 | Wrong/unclear content | `corpus.body` no longer names "P003"; plain-language phrasing | `src/delta_lemmata/catalog.py` | `browser-audit.json` prohibitedCopyHits=0 (incl. `p003`); `copy-snapshot.txt` |
| CON-1 present-tense unbuilt copy | P2 | Content honesty | Guided/Research bodies now "Will run …"; preserved "documented parameter grid" | `src/delta_lemmata/catalog.py` | `smoke.json` research_body_future_tense=true; `test_webapp.py` still green |
| PROD-2 duplicated experiment-map markup | P2 | Maintenance (drift) | Factored to one `_experiment_map_markup()` helper (byte-identical output) | `src/delta_lemmata/webapp.py` | `verify.sh`; browser audit unchanged rendering |
| A11Y-5 disabled buttons lack help | P3 | Accessibility | Added `help=` to the two disabled corpus buttons (+2 English registry keys) | `src/delta_lemmata/webapp.py`, `catalog.py` | source; `test_catalog.py` key count ≥70 (now 92) |
| PY-2 committed dev-watch flag | P3 | Config/deployment boundary | `runOnSave = true` → `false` | `.streamlit/config.toml` | `test_runtime_boundary.py` still green |

## Deliberately not changed (deferred, with reason)

| Finding | Severity | Why not fixed here |
|---|---|---|
| PY-1 unused `pydantic` dependency | P2 | Touches the locked SBOM/`uv.lock` and clean-clone gate; predates P002; plausibly staged for P003 ingestion validation. Owner/Codex decision. |
| PROD-3 boundary text under two labels | P2 | Removing/repurposing a panel is an information-architecture/product decision, not a defect fix. |
| SEC-1 / SEC-3 / SEC-4 prior-run + ticket provenance nits | P3 | Editing them would overwrite existing P002 evidence, which the brief forbids. Documented for Codex; this review's new Run records use the real raw config hash. |
| SEC-2 egress / `server.address` | P2 (deferred-feature) | P014 production-isolation responsibility. |
| A11Y-2 decorative border contrast | P3 | Not a hard AA text failure; darkening the global line token would shift the deliberately quiet aesthetic. |
| VIS-4 / A11Y-3 heading level | P3 | The two accessibility reviewers disagreed; the minimal edit trades one minor imperfection for another. |
| CON-2/3/4, PROD-4/5, VIS-3/5/6/7, A11Y-4, PY-3/4 | P3 | Taste, wording, live-render-dependent, or framework-driven; no P002 acceptance impact. |
