# P003 Failures And Corrections

1. The opening Ticket said TXT, CSV, and ZIP would be identified from content.
   Independent review correctly noted that a valid CSV is also valid UTF-8 text,
   so automatic TXT-versus-CSV inference is not a defensible security boundary.
   P003 now requires an explicit intake role followed by extension, MIME, and
   role-specific content validation.
2. The opening cleanup criterion could be read as covering Streamlit internals or
   the whole host. It is narrowed to copies, state, logs, exceptions, temporary
   directories, and workspaces controlled by Delta. Lifecycle and infrastructure
   retention guarantees remain P005 and P014.
3. The first ZIP draft validated EOCD placement and used server-generated flat
   storage names, but it still delegated local-versus-central header consistency
   to Python `zipfile` and allowed archive/member extra fields. Independent review
   demonstrated that `zipfile` accepts prefixed/suffixed data and conflicting raw
   headers. The draft was not accepted. P003 ZIP v1 now raw-parses EOCD, central,
   and local headers before `ZipFile`, requires exact ranges and matching fields,
   rejects ZIP64, comments, extra fields, data descriptors, encryption, split
   archives, unsupported flags/methods, and verifies member hashes again while
   materializing server-generated names.
4. The first fixed-fixture run passed 100 of 108 cases and failed eight. Three
   exposed real boundary issues: `./name.txt` was canonicalized instead of rejected,
   raw NUL names reached `ZipInfo` before path validation, and an impossible central
   offset was reported as a resource limit rather than a malformed archive. These
   were corrected. Three display-label failures used the right rejection with a
   less precise code and were made explicit. Two cleanup tests had replaced the
   process-wide `os.open`, unintentionally breaking `shutil.rmtree`; the tests now
   fail only generated asset creation while leaving cleanup operational.
5. The corrected fixed-fixture suite passed all 108 cases but reached only 96%
   branch-aware coverage, so the new 100% gate rejected it. The missing paths
   exposed two redundant conditions: aggregate compression ratio cannot exceed
   the highest already-bounded member ratio, and the closed `IntakeRole` enum had
   an unreachable fallback after all three roles were handled. Those conditions
   were removed. Targeted tests were then added for truncated raw ZIP structures,
   local-header gaps, disagreement between raw headers and `ZipFile`, runtime
   expanded-byte rechecking, second-pass integrity failure, and cleanup failure.
   The resulting ingestion suite passes 117 tests at 100% statement and branch
   coverage.
6. The first deterministic fuzz run passed all malicious families but failed two
   valid-input assertions. The assertion treated the payload word `text` as leaked
   because it also occurs legitimately in the `corpus_text` role name. No payload
   was exposed. The property now inserts a case-unique marker and checks only that
   marker against the content-free receipt representation.
7. The first repository-wide verification stopped at the formatting gate before
   lint, type, test, metadata, provenance, or R checks ran. Ruff required one
   mechanical line-layout change in `tests/test_ingestion_zip.py`; the formatter
   was applied only to the two new ingestion test files before rerunning the full
   gate.
8. The first staging attempt exposed that the repository-wide `data/` ignore rule
   also hid the packaged ingestion-limit profile. The profile was not force-added.
   Instead, `.gitignore` now has a narrow exception for
   `src/delta_lemmata/data/ingestion-limits-v1.json`, preserving the prohibition on
   user corpus data while ensuring the security policy exists in clean clones and
   built distributions.
9. The first UI formatting check ran after all Streamlit interaction tests passed
   and requested mechanical wrapping changes in `catalog.py` and `webapp.py`.
   Ruff formatted only those files before the repository-wide gate was rerun.
10. The next repository-wide run passed formatting and stopped at import ordering
    in `intake_ui.py`. Ruff's formatter does not apply its import-sorting lint
    rule, so the safe lint autofix was run on that file before restarting the full
    gate.
11. The first static check of the new P003 browser harness found two screenshot
    calls four characters over the repository line-length limit. Ruff reformatted
    the script before any browser-audit result was collected.
12. The first P003 browser-harness execution started a fresh server but stopped
    before collecting a viewport result because the JavaScript geometry expression
    closed its returned object with one extra parenthesis. The expression was
    corrected and the incomplete run is not represented as browser evidence.
13. The first correction matched an earlier, similar closing sequence in the
    heading extractor rather than the geometry expression, so the second execution
    stopped at the same syntax error. Both expressions were then corrected with
    their full surrounding context before another run.
14. The next browser audit completed all viewport checks but returned `failed` in
    the ZIP interaction. The harness waited for an `Uploads: 1` string already
    present during a Streamlit rerun and inspected the page before ZIP validation
    finished. It also expected the input `accept` attribute to equal `.zip`, while
    Streamlit prepends its internal `application/streamlit` value. The harness now
    waits for the unique ZIP-member summary and checks `.zip` as one accepted item.
    The failed JSON and screenshots are retained under
    `provenance/evidence/P003/browser-audit-failed-run-1/`; none is presented as
    passing evidence.

No failed or corrected attempt is presented as passing evidence.
