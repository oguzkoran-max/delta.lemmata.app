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
15. Independent UI review found that rejected bytes remained reachable through
    Streamlit's fixed-key uploader widget even though Delta retained no payload in
    its own outcome object. It also found that exact-element canary checks could
    miss a substring leak and that metadata-only success conflicted with an
    awaiting-corpus evidence row. Rejection now rotates all uploader keys through a
    payload-free rerun, retains only one stable error code for display, checks the
    complete visible body for canary and filename substrings, and presents
    metadata-only validation as informational rather than corpus readiness.
16. The first post-review browser audit passed uploader reset, filename and payload
    absence, labelled uploader regions, all interactions, and every geometry check,
    but returned `failed` because Streamlit kept the progressbar accessible name as
    the generic `progress` even when text was supplied. The native widget was
    replaced with a simple semantic progress element carrying an explicit name and
    min, max, and current values. The failed package is retained under
    `browser-audit-failed-run-2/` with additive path errata.
17. Independent FAIR review showed that AC-01 said MIME must agree without stating
    what happens when a client supplies no MIME, and demonstrated that an ASCII PDF
    signature could pass the plain-text parser. P003 now treats client MIME as
    untrusted advisory metadata: when present it must match, while absence never
    replaces role-specific content validation. Known binary/document signatures,
    including BOM-prefixed PDF and RTF, now fail as type mismatches with fixed and
    generated regression cases.
18. The same review demonstrated that a schema-1.1 Ticket could be marked complete
    while Runs, changed files, commands, acceptance states, and acceptance evidence
    remained empty. Completed schema-1.1 Tickets now require populated closure
    arrays and passed/not-applicable acceptance entries with evidence. The semantic
    validator resolves every acceptance evidence path to a repository file and
    requires Ticket/Run links to be reciprocal.
19. The first full verification after review fixes stopped at lint because two
    uploader-state constants had been inserted between import groups in
    `webapp.py`. They were moved below the complete import block before restarting
    the gate; no behavioral result from that run is claimed.
20. Final independent security review found six additional hardening gaps: public
    rejections retained Python's hidden exception context; archive labels could
    contain markup, control, or bidi characters; three shared ZIP header fields
    were not compared; secure extraction decompressed each member three times and
    batch expansion was detected too late; whitespace-prefixed CSV paths could
    bypass checks; and the packaged limit test locked only one value. The boundary
    now detaches cause and context at every public API, maps surrogate labels to a
    stable error, restricts ZIP labels to render-safe characters, compares version
    needed and DOS time/date, reuses the preflight inspection for a two-read
    extraction, applies remaining batch budget before decompression, normalizes
    CSV path inspection after leading horizontal whitespace, and locks every field
    of the frozen versioned profile.
21. The first coverage run after those fixes passed all 209 tests but failed the
    mandatory 100% gate at 99.46%. Four lines represented three intentional
    defenses: surrogate archive-path translation, actual-versus-declared batch
    expansion rechecking, and the final aggregate batch guard. Direct regression
    tests were added for all three. The next repository-wide run passed 211 tests
    with 100% statement and branch coverage, followed by metadata, provenance,
    repository, and R lock checks.
22. Security re-review confirmed the six original findings except for two broader
    Unicode variants. U+2028/U+2029 are line and paragraph separators rather than
    `Cc`/`Cf`, and Unicode space separators are not removed by ASCII-only
    `lstrip(" \\t")`. Display and archive labels now share a category denylist that
    also rejects `Zl` and `Zp`; CSV path inspection now strips all Unicode
    whitespace before applying every path rule. Fixed tests cover U+2028, U+2029,
    NBSP, figure space, and narrow no-break space.
23. The first full verification after the Unicode corrections stopped at the
    formatting gate before lint or tests because Ruff required a mechanical wrap
    in `ingestion.py`. The formatter was applied to that file only. The rerun then
    passed 218 tests with 100% statement and branch coverage plus every remaining
    project gate.
24. A second security re-review confirmed both Unicode corrections but showed that
    U+2028/U+2029 could still occur inside a CSV cell. Although Python's CSV reader
    does not treat them as record delimiters, later `splitlines`, logging, or export
    code could. CSV cells now reject Unicode `Zl` and `Zp` anywhere, using the same
    named category policy as labels. Two fixed regressions raised the repository
    total to 220 tests; the complete gate remained at 100% statement and branch
    coverage.
25. Final scoped review found no implementation defect but noted that the
    two-read extraction regression counted reads without explicitly locking the
    promised single text scan. The test now counts `_read_member` and `_decode_text`
    independently and requires exactly two reads and one parse. Its first full-gate
    run stopped at a mechanical Ruff wrap in the modified test; after formatting
    that file, all 220 tests and every repository gate passed again.
26. FAIR closure re-review found that reciprocal Ticket/Run validation was still
    one-way, a schema-1.1 Ticket could be complete with empty commit, decision, or
    prompt links and active blockers, three documents described future closure
    evidence in the present tense, and only three of eleven configured document
    signatures were fixed-test inputs. The validator now checks both directions,
    completed schema-1.1 Tickets require every ownership and execution link plus
    zero blockers, the documents explicitly mark Run/manifest/acceptance as
    pending, and a table-driven regression executes every configured signature.
27. The first reciprocal-link test correctly rejected two legacy P001 Runs because
    their schema-1.0 Ticket predates `run_ids`. Rather than rewriting historical
    records, reverse-link enforcement was scoped to schema-1.1 Tickets while
    forward links remain checked whenever present. Synthetic tests cover missing,
    one-way, reverse-only, valid, and legacy links. The full gate then passed 232
    tests at 100% statement and branch coverage.
28. The first exact-commit clean-clone bootstrap called `uv` by name and exited 127
    because the host does not install uv on `PATH`. The replay did not fall back to
    an unlocked installer. It used the existing project bootstrap uv executable by
    explicit path and created a fresh clone-local `.venv` from `uv.lock`.
29. The first clean-clone `verify.sh` run passed formatting, lint, type, all 232
    tests, metadata, provenance, and repository checks, then failed at the R gate
    because clone-local packages from `renv.lock` had not yet been restored. After
    an explicit noninteractive `renv::restore`, the unchanged source commit passed
    the full gate, fresh-process browser audit, and wheel policy check.
30. The canonical replay was repeated from a second untouched clone using only
    `./scripts/bootstrap.sh` and documented project commands. Bootstrap, full
    verification, browser audit, and wheel build all passed without source edits.
    Two wheel builds from the same commit had different whole-file SHA-256 values,
    so P003 does not promote them to a bit-reproducible-package claim. Both embedded
    the exact tracked ingestion policy hash; release reproducibility remains a
    later gate.

No failed or corrected attempt is presented as passing evidence.
