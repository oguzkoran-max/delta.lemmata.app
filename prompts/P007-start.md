# P007 Execution Brief

**Record type:** Agent-prepared, human-owned ticket execution brief

**Not a PromptEvent:** The user's native continuation request is retained separately
as a hash-bound PromptEvent. This file expands the accepted roadmap into an
engineering plan; it is not presented as the user's verbatim request.

```text
P007: Deterministic Preprocessing and Corpus Health

Read START_HERE.md, SESSION_HANDOFF.md, the P007 roadmap section, CE-02, CE-04,
CE-09, EPI-01, EPI-02, EPI-04, EPI-06, EPI-07, EPI-11, ADR-0002, ADR-0011,
ADR-0012, ADR-0013, proposed ADR-0014, and the P007 contract. Do not reopen
accepted product decisions. Do not treat the opening package as human method
acceptance, preprocessing parity, corpus adequacy, public analysis, FAIR
certification, or a literary result.

Do not write P007 implementation until Oğuz records a separate HumanDecision for
the proposed preprocessing profile, corpus-health severities, quantitative
thresholds, minimum-data gates, temporary materialization boundary, and public
wording.

After that decision, implement in this order:

1. Close versioned P007 configuration, annotation-overlay, preparation-manifest,
   corpus-health, and admission-receipt schemas before implementing text
   transformation. Reject duplicate JSON keys, unknown fields, non-finite values,
   malformed identifiers, unbounded strings or arrays, and semantic inconsistency.
2. Preserve P004's payload-free public/session state. Materialize P003-validated
   TXT bytes or validated ZIP members directly into a P005-owned private
   prepare-only workspace. Do not place text, snippets, readable paths, or prepared
   tokens in Streamlit session state, SQLite control rows, logs, exceptions, or
   provenance records.
3. Bind every materialized source to the P003 raw SHA-256, P004 asset/work/edition/
   source chain, rights decision, intake profile, and immutable inventory digest.
   A mismatch is a blocker and causes fail-closed cleanup.
4. Implement exactly the accepted `delta-surface-words-v1` profile. Keep raw bytes
   unchanged; decode with the P003 UTF-8/BOM rule; normalize newlines; lowercase
   with Unicode `str.lower`; restore NFC; tokenize letter sequences with following
   combining marks; treat all other characters as separators; preserve diacritics;
   retain stopwords; do not lemmatize or stem; join tokens by one ASCII space and
   one final LF.
5. Record raw and prepared SHA-256, profile/config digest, input and prepared byte
   sizes, token totals, unique-token totals, transformation counts, Python and
   Unicode database versions, and implementation version. Never export source or
   prepared text, snippets, token lists, or absolute paths by default.
6. Keep `custom_exclusions.txt` optional and exact-token only. It changes the
   candidate feature inventory after preparation; it does not rewrite prepared
   text, prepared hashes, token totals, or full frequency counts. Reject regex,
   wildcard, multi-token, non-NFC, or ambiguous entries.
7. Derive candidate feature order from known independent works only. Unknown rows
   are projected into the frozen known-derived inventory. Changing an unknown must
   leave prepared known artifacts, feature order, culling eligibility, and every
   known-only fitting input unchanged.
8. Model work independence explicitly in a versioned P007 overlay without changing
   P004 v1 schemas. Segments, excerpts, or multiple assets from one parent work do
   not increase the number of independent works. P007 remains whole-text only and
   does not create analytical segments.
9. Run deterministic exact-normalized duplicate, near-duplicate, shared-passage,
   edition, OCR, paratext, work-length, group-balance, genre, audience, source,
   adaptation, collection, and chronology checks using the accepted thresholds.
   Pair findings by opaque identity; never retain or render matching passages.
10. Use the versioned severity vocabulary `blocker`, `strong_warning`, and `note`.
    A blocker prevents analysis but still permits content-free audit export. A
    warning remains visible through Review, results, and export. A note is never
    presented as proof that the corpus is clean, representative, balanced, or fit
    for a general claim.
11. Introduce one mandatory admission facade. Only a hash-bound P007 `READY`
    receipt may build P006 input and enqueue execution. Lower-level P005/P006 paths
    remain internal and cannot bypass corpus health. Preserve the frozen P006 wire
    schemas and P005 lifecycle states.
12. Do not silently lower requested MFW. Capacity indicators may report whether
    100, 300, 500, or 1,000 known-derived features are available; an unavailable
    requested cell remains `not_enough_features`.
13. Build beginner-first English UI in the existing Lemmata family system:
    Upload -> Describe -> Prepare -> Health review. Explain that source files are
    not edited, show what changed as counts, and pair every visual with an
    accessible table, CSV, and `What this does not establish` statement.
14. Test deterministic reruns, Unicode and apostrophe/hyphen cases, BOM/newline
    equivalence, exclusions, duplicate and passage boundaries, confound matrices,
    role invariance, workspace cleanup, state/log leakage, admission bypass,
    malformed contracts, exact-commit clean clone, Linux CI, and canonical
    container execution. Preserve failed evidence honestly.

P007 may establish only the accepted preprocessing profile, named corpus-health
fixtures, and the P007 part of CE-02, CE-04, and CE-09. Do not claim that a corpus
is good, representative, unbiased, statistically controlled, publication-ready, or
FAIR-compliant. Do not activate the public analysis workflow, display stylometric
results, infer authorship or causality, calibrate benchmarks, analyze Pinocchio, or
claim production isolation.
```
