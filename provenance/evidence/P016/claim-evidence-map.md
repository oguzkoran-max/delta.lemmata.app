# P016 Claim-Evidence Map (prototype copy audit)

Rule: every factual/scientific sentence in the prototype is listed; anything not
supportable is not published. Sources: `src/delta_lemmata/catalog.py` (exact-HEAD
strings), `DEVELOPMENT_CONTRACT.md` (§2 product promise, §6 method),
`docs/research/claim-evidence-matrix.md` (CE rows + denylist),
`docs/development/phase-b-visual-integration.md` (result-surface contract).

| # | Proposed sentence | Source | Claim ID | Evidence status | Qualification applied | Decision |
|---|---|---|---|---|---|---|
| 1 | "Discover patterns in writing style." | catalog `setup.title` (verbatim) | — | live copy | none needed | PUBLISH |
| 2 | "A Lemmata stylometry workbench" | live header subtitle (verbatim on delta.lemmata.app) | — | live copy | none | PUBLISH |
| 2b | "Δ" brand mark + "Delta" | live product identity | — | live copy | none | PUBLISH |
| 3 | "A scholar-led, uncertainty-aware stylometry workbench for literary and digital-humanities research." | CONTRACT §2 product identity (Scholar-led, uncertainty-aware; hedef kullanıcı DBB) | — | design-intent claim | descriptive positioning, no capability claim | PUBLISH |
| 4 | "Run supported stylometric workflows without first learning or writing R or Python code." | CONTRACT §2 canonical promise; CE-01 fallback | CE-01 (implemented, not verified) | fallback wording exactly as licensed | second clause "Delta keeps corpus choices, parameters, and limitations visible" from same §2 sentence | PUBLISH (fallback form) |
| 5 | "Public alpha · Experimental" | catalog `header.release_*` (verbatim) | ADR-0015 | required visible | none | PUBLISH (required) |
| 6 | "Stylometry observes recurring, measurable patterns in language use, such as how often common words recur." | catalog `setup.intro` (paraphrase-tightened) | — | live teaching copy | adds "measurable"; no semantic/AI claim | PUBLISH |
| 7 | "It does not read meaning, topics, or intent." | boundary derived from CONTRACT §3/anti-scope | — | negative scope statement | phrased as design boundary | PUBLISH |
| 8 | "Genre, date, edition, audience, source, rights, and OCR shape what a comparison can mean." | CE-09 wording family; catalog corpus guidance | CE-09 (implemented) | confound visibility only | "shape what a comparison can mean" (no control claim) | PUBLISH |
| 9 | "Delta asks you to document texts before any analysis." | live flow (Upload→Describe→Review), catalog sidebar copy | CE-02 slice | live behaviour | none | PUBLISH |
| 10 | "Unknown values stay visible and block public export." | P004 rights model (fail-closed), CE-13 | CE-13 (implemented) | mechanism exists in app | limited to visibility+export gate; no legal claim | PUBLISH |
| 11 | "Guided comparisons run 100, 300, 500, and 1,000 most-frequent-word settings together." | CONTRACT §6.2; catalog parameters copy | CE-02 | live behaviour | none | PUBLISH |
| 12 | "500 MFW opens first as a pre-specified display reference — not a best or optimal setting." | catalog results reference-note family (near-verbatim; "500 MFW opens first...") | Phase-B contract | live copy | exact anchor framing kept | PUBLISH |
| 12b | "All four settings stay visible together · none is marked best" (caption) | phase-b result surface (all cells visible) | CE-02/CE-08 | live behaviour | caption form | PUBLISH |
| 13 | "Nearer means more similar measured patterns inside this corpus and this setting." | catalog results proximity language | — | live copy family | corpus+setting relativised | PUBLISH |
| 14 | "The numerical distance matrix is the primary evidence; the heatmap is a rendering of that matrix, and the MDS projection is derived from it." | catalog results matrix/heatmap/MDS bodies; phase-b contract | — | live copy family | MDS wording: "derived from", not "rendering" | PUBLISH |
| 15 | "Axes have no literary meaning; apparent clusters can be projection artefacts." | catalog `results.mds.body` (verbatim family) | — | live copy | none | PUBLISH |
| 16 | "Do not conclude: nearer does not mean the same author, influence, intention, or authenticity." | catalog purpose boundary copy (verbatim family: "Nearer does not mean the same author, influence, intention, or authenticity.") | claim-lint core | live copy | "Do not conclude:" prefix from live guide label | PUBLISH |
| 17 | "Delta keeps all four comparisons and every corpus warning side by side — there is no winner-takes-all view and no confidence score." | phase-b result surface + CE-08 stability-not-confidence | CE-08 | live behaviour + design rule | "no confidence score" is a *negative* claim (allowed) | PUBLISH |
| 17b | Run-ledger rows labeled "kept" | design-intent, qualified by visible caption "Run-record structure · design intent, illustrative" | CE-12 | design intent | caption qualifies tense | PUBLISH |
| 18 | "Delta is designed to preserve the corpus description, method settings, numerical outputs, rights summary, and declared interpretation limits of every run as a FAIR-oriented record." | CONTRACT §9 FAIR-oriented; catalog evidence.* strings | CE-12 (implemented, not verified) | "is designed to" + "FAIR-oriented" fallback | never "FAIR-compliant/complete reproducibility" | PUBLISH (design-intent form) |
| 19 | "R stylo is the canonical analysis engine." | CONTRACT §2; catalog `build.engine_value` | CE-04 boundary | architecture fact | listed under Method, no parity generalisation | PUBLISH |
| 20 | Three path cards: "Compare Texts / Recurring language patterns across individual texts." etc. | catalog `purpose.*.summary` (verbatim ×3) | — | live copy | none | PUBLISH |
| 21 | Footer boundary: "Designed to remove R and Python coding from supported workflows. Method knowledge and interpretation remain the researcher's responsibility." | catalog `footer.method` (verbatim) | CE-01/EPI-13 | live copy | none | PUBLISH |

Rejected candidates (not published): any accuracy/reliability/validated wording
(CE-05/06 not run); "reproducible" (CE-11/12 gate); "isolated/secure" absolutes;
"easy/intuitive/anyone"; monetary/award language; "stability" labels (CE-08 gate);
Pinocchio/benchmark references (P010-P013 open); "193-frame/3D/cinematic" method
claims. Denylist from claim-evidence-matrix §7 was applied to the full page and is
re-checked by the scientific-claim reviewer and a grep gate in the verification
report.
