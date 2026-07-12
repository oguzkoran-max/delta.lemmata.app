# P004 Automated Acceptance Rehearsal Validation

**Date:** 2026-07-12

**Ticket:** `P004`

**PromptEvents:** `PE-20260712-0009`, `PE-20260712-0010`

**HumanDecision:** `HD-20260712-0002`

## Scope

The owner asked Codex to run intermediate tests and reserve the shared manual
walkthrough for the product-ready stage. The P004 browser harness was therefore
extended with a fresh-context rights correction journey in addition to its
existing six-viewport, Guided TXT, Review, download, and ZIP journeys.

The new journey proves that a `permission_required` record visibly blocks upload
and analysis, disables final confirmation, routes the user back to the exact
`rights_status` field, restores payload-free guided values, accepts an explicit
`analysis_only` correction, reports two permitted and two prohibited actions,
and permits inventory-bound confirmation only after blockers are gone.

## Synthetic Inputs

Only synthetic in-memory text was used by the committed harness. A disposable
Desktop aid was separately validated with two synthetic TXT files and one strict
two-member ZIP. The Desktop folder is not repository evidence or research data.

## Iteration Record

The pre-extension harness passed. The extension then exposed harness and oracle
defects before reaching a stable final run. None of the failed attempts is treated
as a product failure or a passing result.

| Attempt | Result | Observed reason |
|---|---|---|
| 1 | failed | Exact accessible-name matching did not find the icon-bearing correction button. |
| 2 | failed | The selected correction label existed both in the control and open virtual menu, creating a strict-locator collision. |
| 3 | failed | Correction routing worked, but the rights option was queried before the Streamlit selectbox stabilized. |
| 4 | failed | A keyboard patch matched the earlier Guided rights field and selected the wrong state there. |
| 5 | failed | The same wrong-state regression correctly kept confirmation disabled. |
| 6 | failed | The corrected-field selectbox still used the unstable single-open helper. |
| 7 | failed | A mouse-based checkbox operation targeted Streamlit's hidden input and was intercepted by its visible label. |
| 8 | failed | All behavior completed; two oracles read HTML attributes instead of live values and counted ZIP forms before rendering settled. |
| 9 | failed | All existing flows passed; the post-correction keyboard selection did not change the custom selectbox value. |
| 10 | failed | All behavior gates passed; confirmation rerender invalidated five earlier download URLs and produced console 404 errors. |
| 11 | failed | A transient fresh-process run did not reach the first intake-ready state; no behavior result was claimed. |
| 12 | passed | Stable selectbox retry, live input values, render-count wait, confirmation-before-download ordering, and keyboard checkbox activation all passed. |

Attempts 1-11 were generated under disposable `/tmp` paths and were removed by
host cleanup before repository capture. Their failure stages were observed in the
live command output and are summarized here; no unavailable raw file is claimed.
Attempt 12 was rerun directly into the tracked evidence directory and retains its
machine-readable report and complete screenshot set.

## Final Browser Result

`provenance/evidence/P004/automated-acceptance-rehearsal-attempt-12/browser-audit.json`
reports `passed`:

- six responsive Upload and Review viewports passed;
- Guided TXT flow passed;
- fail-closed rights correction flow passed;
- strict two-member ZIP flow passed;
- all `_pass` fields are true;
- 25 screenshots were generated;
- observed external hosts: none;
- browser console messages: none;
- source-payload echo: none;
- horizontal or control overflow: none.

Manual inspection of the final desktop, mobile, blocked-rights, resolved-rights,
timeline, matrix, composition, and ZIP screenshots found no incoherent overlap,
clipping, blank primary surface, or result-like placeholder.

## Repository Result

After the harness change, `./scripts/verify.sh` passed:

- 468 tests;
- 3,174 measured statements and 880 measured branches at 100% coverage;
- Ruff format and lint;
- strict mypy;
- metadata and 63 provenance records;
- repository and supply-chain scans;
- locked R 4.5.2, renv 1.2.3, stylo 0.7.71, and jsonlite 2.0.0.

## Exact-Commit Result

Implementation commit `9f3124a65216fd1c0f6d459cfe6a3049f51baa07`
was detached in a fresh `--no-hardlinks` clone and rebuilt from committed Python
and R lockfiles. The clone passed 468 tests, 3,174 statements and 880 branches at
100% measured coverage, every repository gate, and the expanded six-viewport
Guided TXT, rights-correction, Review/download, and strict ZIP audit. It remained
clean after the run.

The machine-readable record is `RUN-20260712-0005`; the human-readable replay,
browser JSON, and checksum manifest are under
`provenance/evidence/P004/automated-acceptance-rehearsal-exact-commit/` and
`provenance/evidence/P004/automated-acceptance-rehearsal-exact-commit.sha256`.

## Provenance-Link Iterations

The first post-link full gate passed application tests but correctly rejected the
new Run because `command` and `replay.command` differed and the replay contained a
placeholder. The second passed all 468 tests but the repository scanner correctly
rejected three records containing a personal macOS absolute path. The Run was made
internally identical and placeholder-free; paths were then normalized to an
equivalent relative or `$HOME` form, and affected checksums were regenerated.

A preliminary direct call to nonexistent `scripts/verify_metadata.py` was also
discarded as an operator command mistake; the repository's canonical
`./scripts/verify.sh` remained the only full-gate authority. The corrected final
gate passed 468 tests, 3,174 statements, 880 branches, 67 provenance records,
repository and supply-chain scans, metadata, and the R lock boundary.

## Verdict

The candidate passes P004's repeatable working-tree and exact-commit technical
acceptance rehearsal. GitHub CI remains the final technical-closure gate. This
does not establish Safari, VoiceOver, scientific computation, general usability,
production behavior, or the final owner walkthrough. Those boundaries remain
explicit.
