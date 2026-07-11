# P002 Codex Audit Correction Report

## Verdict

The two merge-blocking FAIR findings are resolved additively. The corrected P002
shell has no open P0 or P1. Automated responsive, reflow, keyboard, heading,
disabled-state, copy, record-integrity, clean-clone, and observed browser-request
checks pass. Full WCAG, real browser-chrome 200% zoom, manual screen-reader, packet
capture, and production egress conformance are not claimed.

## Code And Product Corrections

- Mobile sidebar state is `auto`; fresh 390px and 360px contexts do not cover the
  primary workflow.
- The document outline is one `h1` followed by peer native `h2` sections.
- Disabled button names include why the action is unavailable, with visible panel
  explanations. Their icons were removed after live accessibility snapshots showed
  that Streamlit included icon ligature text in their names.
- `P002` and `ticket` jargon was removed from the user-facing English catalog.
- The duplicated purpose boundary became a general method boundary while each
  purpose retains its specific interpretive limit.
- `pydantic` remains locked for the forthcoming P003 ingestion-validation decision;
  no runtime ingestion was added here.

## FAIR And Replay Corrections

- Run schema 1.1 replaces the ambiguous pathless configuration digest with explicit
  configuration artifacts, exact replay commands, scoped supersession, and optional
  evidence manifests.
- Run 1.1 validation recomputes each input hash from the named Git commit, each
  output hash from the retained artifact, and rejects non-canonical or escaping
  repository paths. Negative tests cover duplicated false hashes, changed outputs,
  and parent-directory traversal.
- Ticket schema 1.1 adds Run and supplemental-evidence links.
- A tracked replay script clones an exact 40-character commit, bootstraps both
  languages, runs every verification gate, verifies all 18 Claude review files, and
  requires an empty Git status.
- A tracked Playwright harness starts its own loopback Streamlit process and records
  six fresh browser contexts, accessibility snapshots, keyboard behavior, geometry,
  screenshots, and observed request hosts.
- Claude's original review files and Runs remain byte-for-byte unchanged. Their
  incorrect or overly broad fields are corrected in `provenance-errata.json` and
  superseded only within the fields named by the new Runs.
- `RUN-20260710-0005` ended 124 seconds before its named commit existed. Its
  `git_commit` and `tested_snapshot` claims are now explicitly superseded by the
  clean-clone Run against a pre-existing immutable commit.

## Remaining Disclosed Limits

Streamlit 1.59.1 offers no supported API to replace the native sidebar-toggle name
or the disabled file input's `Choose File` name. The interface therefore keeps an
explicit visible field label and does not claim those framework controls have a
product-specific accessible name. Real 200% browser-chrome zoom was attempted in
the available browser surface, but the measured zoom did not change; that attempt
was rejected rather than relabelled as success. The 640px and 320px results are
strictly reflow tests.

## Final Adversarial Re-review

The same fork-context reviewer that identified the two remaining P2 defects
re-examined their repairs without editing the working tree. It found no open P0,
P1, or P2, independently reported 18 targeted tests, 21 valid records, the exact
47-test clean-clone replay, a temporary six-target browser rerun, both manifest
checks, and a clean diff. Its final verdict is `MERGE-READY` after the closure
records are committed. The bounded result is retained in `adversarial-review.md`.

## Commits Under Review

- Claude repair: `0788a6e94a46df984c88f65be8841e0ef9d3bb24`
- Claude evidence closure: `1787ff4880ea92e32f217673cddfe92e8ed3491a`
- Codex corrections: `b53e3087f1f18529ce46023a95b11d4b24ad3119`
- Codex evidence-scope correction: `05e7b01cf7f454e0a6a6607c547246c8a85279cf`
- Codex Run-integrity correction: `cd7d7b1094dfed40a354a2c4ff2da46b662463d2`

The branch remains unmerged for the human owner's review and merge decision.
