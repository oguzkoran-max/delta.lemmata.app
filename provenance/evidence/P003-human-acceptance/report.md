# P003 Human Acceptance Report

## Decision

- Acceptance owner: Oğuz Koran
- Decision: accepted
- Final decision record: `HD-20260711-0008`
- Initial contextual continuation: `HD-20260711-0007`
- Manual test record: `RUN-20260711-0004`
- Tested application commit: `568984e7a36d5d296a4c476ff5c20c5668487693`
- Test surface: Delta on loopback in the Codex in-app browser
- Test date: 2026-07-11

After the three guided manual checks below, Oğuz Koran first responded,
"tamam devam edelim". An independent reviewer requested a less ambiguous record.
Codex then presented the exact P003 acceptance choice and Oğuz replied,
"devam edelim". The scoped surrounding exchange is transcribed with capture
limitations in `provenance/evidence/P003-acceptance-context-20260711.md`.

## Test Inputs

Codex created a synthetic test folder on the local Desktop. The files contained
no research corpus, personal data, or unpublished material:

- `collodi_sample_early.txt`
- `collodi_sample_late.txt`
- `corpus_valid.zip`, containing the two synthetic TXT files
- `metadata_valid.csv`
- `metadata_invalid.csv`, containing a spreadsheet-formula injection fixture

The Desktop fixture folder is a disposable manual-test aid and is not a source
artifact for the Delta repository.

## Observed Checks

### Valid individual TXT files and metadata CSV

The user selected two individual TXT files and the valid metadata CSV. The
interface reported:

- `Intake checks passed`
- uploads: 3
- corpus texts: 2
- input bytes: 624
- metadata structure validated
- two named corpus receipts and one metadata receipt

Evidence: `valid-txt-metadata.png`.

### Valid strict ZIP archive

The user selected the ZIP input role and uploaded the prepared archive. The
interface reported:

- `Intake checks passed`
- uploads: 1
- corpus texts: 2
- input bytes: 579
- TXT members: 2
- expanded bytes: 472

Evidence: `valid-zip.png`.

### Unsafe metadata rejection and clearing

The user uploaded one valid TXT file with the intentionally unsafe metadata CSV.
The interface:

- rejected the complete submission;
- displayed `The submission was rejected and cleared before intake`;
- displayed the content-free code `INGEST_CSV_INJECTION`;
- cleared both browser upload widgets; and
- kept corpus parameters, evidence, and analysis unavailable.

Evidence: `rejected-csv-injection.png`.

## Acceptance Scope

Human acceptance confirms that the visible P003 TXT, ZIP, CSV, and rejection
flows were understandable and behaved as expected in the guided walkthrough.
It supplements, but does not replace, the automated parser, fuzz, cleanup,
browser, exact-commit clean-clone, and checksum evidence in the immutable P003
implementation package.

This acceptance does not establish metadata meaning, rights decisions,
successful-job retention, production deletion times, `stylo` computation,
scientific validity, deployment isolation, or upload-to-export completion. Those
remain assigned to later tickets.

## Outcome

All three manual checks passed. No manual acceptance blocker was reported. P003
may be marked complete and integrated into `main`; P004 may open as a separate
ticket and branch.
