# P003 Independent Adversarial Review

## Scope And Evidence Rule

Independent agents reviewed three different P003 surfaces: product/UI behavior,
FAIR and provenance integrity, and the ingestion security boundary. Reviewers did
not own acceptance and did not edit the reviewed files. A finding was closed only
after a code or record correction, a fixed regression where applicable, the full
repository gate, and a follow-up review.

Any candidate reviewer invocation that ended without a substantive report,
including execution-budget or tool-filter termination, is excluded from the
verdict. A missing report is not represented as a pass.

## Product And UI Review

**Reviewer:** Faraday (`019f5046-4bd3-7fb3-9512-64d943059c20`)

The initial review found that rejected bytes remained reachable through fixed
Streamlit uploader keys, the privacy audit searched exact elements rather than the
whole rendered body, metadata-only intake could appear corpus-ready, and uploader
and progress evidence lacked adequate accessible semantics.

Corrections rotated every uploader key through a payload-free rerun, retained only
one stable error code, changed the canary audit to the complete body and filtered
session state, made metadata-only status informational, labelled upload regions,
and added an explicitly named semantic progressbar. Follow-up review found each
item resolved. A reviewer environment with an older Streamlit version was not used
as execution evidence; the pinned Streamlit 1.59.1 browser harness passed.

## FAIR And Provenance Review

**Reviewer:** Bacon (`019f5044-e6a4-7b11-b289-38ddcbeb5911`)

The initial review found an ambiguous MIME-absence policy, an ASCII PDF signature
accepted as text, missing P003 closure artifacts, a ticket schema that allowed
dishonest completion, incomplete ticket/decision/run links, failed browser JSON
whose paths pointed at the passing directory, and stale threat, claim, and handoff
language.

Corrections made supplied MIME advisory but mandatory-to-match, kept content
validation mandatory when MIME is absent, added known document signatures, kept
P003 explicitly in progress, hardened schema 1.1 and semantic record validation,
added the MIME HumanDecision, preserved failed browser JSON while adding path
errata, and scoped every research and security claim. Exact-commit Runs, checksum
manifest, and human acceptance remain closure gates rather than retrospective
claims.

Closure re-review then found four additional record-quality gaps: Run-to-Ticket
links were not checked in reverse, a complete schema-1.1 Ticket could omit commit,
decision, or prompt links or retain blockers, three documents used present tense
for future closure evidence, and fixed tests sampled rather than exhausted the
binary signature table. Corrections added reciprocal schema-1.1 links with legacy
schema-1.0 compatibility, complete-ticket ownership requirements, explicitly
pending closure language, and a table-driven test for every configured signature.
Final follow-up marked all four resolved with no open P0, P1, or P2.

## Security Review

**Reviewer:** Bernoulli (`019f5055-31f1-7cb0-a37a-15aade5f39d0`)

The initial review found six issues:

1. decoder, archive, and operating-system exceptions remained reachable through
   Python's hidden exception context;
2. ZIP member labels permitted render-unsafe markup, control, and bidi characters;
3. local and central ZIP headers did not compare version-needed and DOS time/date;
4. secure extraction read each member three times and batch expansion was rejected
   only after unnecessary work;
5. leading whitespace and a single backslash could bypass CSV path checks;
6. the packaged limit regression locked only one field.

The first correction detached cause and context at every public API, translated
surrogate labels, introduced render-safe ZIP labels, compared every shared raw ZIP
field, reused one preflight inspection for a two-read/one-text-scan extraction,
applied remaining batch budget before decompression, normalized path inspection,
and locked all 20 numeric limits plus the profile version and frozen behavior.

Follow-up review confirmed those controls and then widened the Unicode threat
model. U+2028/U+2029 labels and Unicode-space-prefixed CSV paths were added to the
fixed regression set. A second follow-up showed that U+2028/U+2029 also had to be
rejected inside CSV cells because later logging or export code may treat them as
line boundaries. The parser now uses named Unicode line categories consistently
across labels and CSV cells. The last scoped review also required the performance
claim itself to be regression-locked; the extraction test now counts exactly two
member reads and one text scan. Final follow-up marked that item resolved and left
no open P0, P1, or P2 in the reviewed ingestion areas.

## Automated Corroboration

- `./scripts/verify.sh`: 232 tests, 100% statement coverage, 100% branch coverage,
  metadata validation, record validation, repository scan, and locked R/stylo
  environment all passed.
- `.venv/bin/python scripts/browser_audit_p003.py --output
  provenance/evidence/P003/browser-audit`: passed in a fresh server process.
- `/usr/bin/time -p .venv/bin/pytest -q tests/test_ingestion_fuzz.py`: 16 tests,
  1,536 generated malicious cases, and 1,152 generated positive controls passed.

## Remaining Closure Gates

This report does not close P003. The implementation commit has been replayed from
a clean clone, the evidence package is sealed by an external SHA-256 manifest, and
reciprocal Ticket/Run links are recorded in the closure metadata. Oğuz Koran must
still make the acceptance decision. P003 does not verify CE-14, production
retention, proxy buffering, scientific analysis, or FAIR certification.
