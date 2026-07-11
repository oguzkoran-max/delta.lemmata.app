# P002 Independent-Review Before / After

## 1. Sidebar active-step contrast (VIS-1 / A11Y-1) — the material change

- **Before:** the active experiment-map row's number and state (`01`, `ACTIVE`)
  rendered `--delta-teal #116f63` on the dark sidebar `#1c2925` = **2.50:1**,
  below WCAG AA (4.5:1) for that 0.72rem text. The original
  `accessibility-report.json` marked this region "passed"; the failure is a
  computed contrast ratio, not visible to an unaided glance.
- **After:** a sidebar-scoped `--delta-teal-on-dark #63b6a6` = **6.30:1**. The
  same rule on the white right-column panel is untouched at 6.04:1, so the
  "active = teal" language is preserved in both contexts.
- **Evidence:** `contrast-proof.json`; `screenshots/desktop-1440x1000.png`
  (light-teal `01 · ACTIVE` in the dark rail) vs the pre-fix baseline
  `../desktop-1440x1000.png` (darker teal). Both screenshots hashed in
  `screenshot-hashes.txt` and the original P002 record.

## 2. Copy: internal ticket id removed (PROD-1)

- **Before:** `corpus.body` = "Secure corpus intake is deliberately unavailable
  until **the P003 validation gate** passes."
- **After:** "Secure corpus intake is deliberately unavailable **until it has
  been implemented and security-tested**."
- **Evidence:** live DOM scan `prohibitedCopyHits` includes `p003` before,
  empty after (`browser-audit.json`); `copy-snapshot.txt`.

## 3. Copy: honest tense for unbuilt modes (CON-1)

- **Before:** "A constrained parameter sweep …" / "A documented parameter grid …"
- **After:** "**Will run** a constrained parameter sweep …" / "**Will run** a
  documented parameter grid …" (the test-asserted substring "documented
  parameter grid" is preserved).

## 4. Dead design tokens removed (VIS-2)

- **Before:** `:root` declared `--delta-coral`, `--delta-amber`, `--delta-blue`;
  none reached the rendered stylesheet (only `--delta-teal` was wired).
- **After:** the three unused tokens are gone; a comment documents that teal is
  the single applied accent, badge hues come from Streamlit's named palette, and
  the link colour lives in `config.toml`.

## 5. Smaller changes

- **A11Y-5:** the two disabled corpus buttons now carry `help=` text (was: none).
- **PROD-2:** the experiment-map markup is emitted by one shared helper instead
  of two hardcoded copies (rendered output unchanged).
- **PY-2:** `.streamlit/config.toml` `runOnSave` `true` → `false`.

## Verification of "no rendered regression"

Across 1440×1000, 1280×800, 390×844, 360×800 and a 200%-zoom emulation:
zero horizontal overflow, zero external assets, zero unnamed viewport-visible
controls, zero prohibited-copy hits, build marker present on desktop (and
intentionally hidden on mobile by the existing responsive CSS). See
`browser-audit.json`.
