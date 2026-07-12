# P004 Timeline, Correction, and Confirmation Validation

Date: 2026-07-12

Status: locally verified implementation checkpoint; P004 acceptance is not claimed.

## Scope

This checkpoint completes three previously open Corpus Review interactions without
creating analysis state:

- a chronological, horizontally selectable work timeline backed by the same
  hash-bound, payload-free projection as the semantic timeline table;
- one correction shortcut per non-complete work/field pair, routed to the exact
  guided work and metadata section or, for CSV-origin inventories, to an explicit
  source-CSV field and `work_id` instruction;
- an explicit file-to-work mapping and rights-record confirmation bound to the
  canonical inventory SHA-256.

The confirmation is a documentation acknowledgement. It is not legal approval,
scientific sufficiency, authorship evidence, or permission to redistribute text.
Any guided rebuild clears the stored confirmation. A blocked validation report
disables the checkbox.

Guided editor values are retained as immutable, payload-free `GuidedWorkInput`
records so returning from Review does not silently erase the researcher's metadata.
Uploaded text bytes are not present in this state. CSV-origin inventories are not
silently converted into an empty guided form because the application does not
retain their original CSV bytes; the interface instead names the exact source field
that must be corrected and re-uploaded.

No sixth timeline CSV was added. The timeline is already represented in the
canonical inventory and its semantic table; adding a separate projection export
would duplicate evidence without a distinct research use.

## Bounded Independent Review

Two read-only agents were assigned explicit 10,000-token budgets before
implementation. The timeline reviewer completed its task and recommended a
chronological native single-selection control, visible selected-work details,
internal horizontal scrolling, and no proportional geometry or style score. The
correction/confirmation reviewer exhausted its budget while reading the mandatory
project context and produced no usable implementation recommendation. That
delegation is recorded as incomplete rather than represented as an independent
approval.

## Automated Verification

Focused domain and UI tests passed 84 tests after the interaction implementation.
The final canonical `./scripts/verify.sh` run passed:

- 464 tests;
- 3,132 statements and 868 branches at 100% measured coverage;
- Ruff format and lint;
- strict mypy across 19 source files;
- metadata, provenance, repository, supply-chain, schema, and R-lock gates.

The tracked Playwright harness starts a fresh local Streamlit process and verifies:

- one accessible timeline radiogroup and one timeline row per projected work;
- selected timeline detail and semantic table `data-row-key` parity;
- four named, keyboard-focusable data-table regions with visible outlines;
- keyboard activation of the final confirmation and its recorded state;
- five documentation downloads and no source-text echo in Review or review CSVs;
- no page-level horizontal overflow at 1440x1000, 1280x800, 640x800, 390x844,
  360x800, or 320x800;
- an unoccluded custom brand header at every viewport;
- no external host request or browser console warning/error.

Passing machine-readable evidence:

- `browser-audit-timeline-confirmation-2026-07-12/browser-audit.json`
- `browser-audit-timeline-confirmation-2026-07-12/screenshots/`

## Retained Failures and Corrections

The first expanded browser run stopped before report serialization because
Playwright's native-input `check()` action was intercepted by Streamlit's visible
checkbox label. Screenshots and a failure note are retained under
`browser-audit-timeline-confirmation-failed-interaction-2026-07-12/`. The final
harness uses focus plus Space and therefore tests the accessible keyboard control.

The next run passed every automated assertion, but manual screenshot inspection
found that Streamlit's translucent built-in header partially covered the custom
`Delta` wordmark on mobile. That run is retained under
`browser-audit-timeline-confirmation-passed-before-header-fix-2026-07-12/` and is
not treated as final visual evidence. The unused Streamlit header was removed and a
DOM hit-test now verifies that the brand remains unoccluded.

The first canonical verification attempt stopped at two Ruff formatting
differences. After formatting, the next full run passed all 462 tests but failed the
mandatory coverage threshold at 99.75%. Six newly added defensive branches received
explicit tests; the complete command was rerun from the beginning and passed all
464 tests at 100% statement and branch coverage.

## Open Gates

- Guided ZIP member documentation is not implemented; ZIP cannot advance to
  Describe without a member-level payload-free catalog.
- Manual Safari and VoiceOver acceptance by Oğuz Koran remains pending.
- Exact-commit clean-clone verification and GitHub CI for the combined P004 UI
  candidate remain pending.
- Human terminology, negative-rights, correction-routing, timeline, and
  confirmation walkthrough remains pending.
- Scientific parameters, R/stylo execution, result graphics, runtime AI,
  deployment, retention, public release, and parent-site launch remain outside this
  checkpoint.

These open gates are not hidden passes and P004 remains `in-progress`.
