# P007 Web Preparation Integration Validation

**Ticket:** P007  
**Commit:** `9b5790f3c75170f9c4241fad11d51f2a26495857`  
**Date:** 2026-07-15

## Scope

This evidence covers the browser handoff from accepted P003 uploads through P005
private materialization, P004 corpus confirmation, P007 deterministic preparation,
and the content-free corpus-health review. It does not establish public analysis
execution, parameter suitability, benchmark accuracy, stability, a FAIR run
package, production readiness, or a literary conclusion.

## Implemented Boundary

- Browser corpus bytes are revalidated before a trusted callback copies them into
  a capability-owned private workspace.
- Streamlit session state retains only an opaque owner key and payload-free
  receipts, annotations, and outcomes. It does not retain raw or prepared text,
  capabilities, authority secrets, or readable server paths.
- Production runtime startup fails closed without a pre-created private root and
  two distinct 256-bit secrets. P005 state is reconciled at startup and before new
  admission; expired idle leases are reaped before they can permanently consume
  staged capacity.
- Confirmed corpora reach one fixed preparation profile, explicit work-role/OCR/
  paratext annotations, deterministic READY or BLOCKED health review, token-length
  visualization, MFW capacity indicators, findings, and content-free downloads.
- READY remains a computational-preflight statement. Public parameters and
  analysis execution remain unavailable.

## Local Validation

The exact source later committed as `9b5790f` passed on macOS arm64 with Python
3.13.9:

```text
ruff format --check: 127 files already formatted
ruff check: passed
mypy: 46 source files passed
pytest: 1,379 passed, 1 skipped
skip: canonical R worker integration requires Linux
coverage: 9,758 statements and 2,570 branches, 100.00%
metadata: passed
records: 92 valid records
repository scan: passed
P006 oracle parse and R lock: passed
```

Focused materialization/runtime/web tests also passed: 71 tests, 1,330 statements,
290 branches, and 100.00% coverage.

## Browser Validation

The local Streamlit application was inspected in the Codex in-app browser against
the exact working tree before commit:

- default desktop entry rendered without visible overlap;
- a 390 by 844 viewport had document and body scroll widths of 390 pixels;
- no visible element crossed the mobile viewport boundary;
- the H1 remained inside its 326-pixel content width;
- switching from Compare Texts to Compare Groups updated the selected state and
  purpose-specific guidance;
- browser console error and warning records were empty.

Real-service Streamlit workflow tests separately exercised TXT and ZIP upload,
metadata review and confirmation, P005 materialization, P007 preparation, READY and
BLOCKED outcomes, restart behavior, role restrictions, content-free errors, chart
data, and downloads. Browser file-dialog automation was not used, so this evidence
does not claim a complete human browser acceptance run through the Prepare screen.

## Canonical Linux Validation

GitHub Actions run
[`29378757244`](https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29378757244)
tested the exact commit on GitHub-hosted Linux amd64:

```text
verify job: 87237608831
container job: 87237608822
pytest: 1,380 passed
coverage: 9,758 statements and 2,570 branches, 100.00%
records: 92 valid records
metadata, repository scan, P006 oracle parse, R lock: passed
SBOM, dependency vulnerability, and secret gates: passed
canonical Linux amd64 image: built
```

## Acceptance Consequence

This closes the implementation and automated validation portion of the P007 web
preparation slice. P007 remains open for its remaining acceptance evidence and any
explicit human gate. P008 owns the parameter review and public analysis workflow;
neither may bypass the one-time P007 READY authority.

## Remaining Limits

- No public parameter selection or P006 execution is connected.
- No result visualization or interpretation view exists.
- No real literary corpus, benchmark, Pinocchio case study, or stability claim is
  validated by these synthetic and interface tests.
- Deployment, monitoring, backup, rollback, and production storage claims remain
  later-ticket work.
