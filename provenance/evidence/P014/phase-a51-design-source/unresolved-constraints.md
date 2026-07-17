# Phase A5.1 · Unresolved Constraints

1. **Type stand-ins.** Inter is not installed on this machine and no external
   font may be requested, so headings render in the system face as an explicit
   stand-in (noted in every page footer). Phase B vendors Inter (SIL OFL 1.1)
   with license text and SHA-256 recorded at the vendoring commit; the body
   face is the Source Sans that Streamlit already bundles offline. The
   provisioning table is in `system.html`.
2. **Streamlit mapping risk.** The prototypes use plain HTML controls. In
   Phase B, purpose cards, the mode pair, and the MFW selector map to
   Streamlit widgets whose internal DOM differs; the accessible contract
   (real radiogroup, labels, 44 px targets, visible focus) is the requirement,
   and exact pixel geometry may shift within the stated budgets. Any deviation
   will be reported with measurements.
3. **Results remain a design specimen.** All values come from the frozen P006
   oracle fixture (MFW 6/5/4/3, six documents); the production guided grid is
   100/300/500/1,000 with a fixed 500-MFW display reference. The specimen
   banner states this on the page. Live verification of the real results
   surface stays with the Linux CI browser gate in Phase B.
4. **Items needing independent scientific review (Codex).** Sequential
   heatmap ramp and its per-matrix scaling caption, the equal-aspect MDS with
   strengthened projection-artefact warning, the nearest-neighbour tie and
   non-reciprocity wording, rounding disclosure, and the reduced boundary
   repetition. No underlying value, ordering, calculation, projection,
   semantic table, or CSV contract was changed or prototyped differently.
5. **Fieldset computed-style artifact.** Chromium lays out `display: grid`
   on `<fieldset>` correctly but reports the unresolved template string via
   `getComputedStyle`; automated Phase B geometry oracles should assert on
   bounding boxes, as `measurements.md` does.
6. **Purpose-conditioned review copy.** The conditioned status band
   ("Ready for Compare Texts…", chronology note for Style Over Time) uses only
   validation facts that P004/P007 already compute; final copy keys belong in
   `catalog.py` and will need Oğuz's copy approval in Phase B.
7. **No P011/P012 features.** Stability labels, calibration language, and the
   complete FAIR package remain absent by design; the evidence list in the
   preparation rail names only artefacts that exist today.
