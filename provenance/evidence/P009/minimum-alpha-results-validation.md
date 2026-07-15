# P009 Minimum-Alpha Results Validation

## Scope

This record validates the minimum-alpha result presentation at exact commit
`c5e39b07bb65a11613684a10269b186c987ef980`. It does not close the full P009
ticket and it is not public-activation evidence. Purpose-specific result
extensions, the integrated owner walkthrough, and the minimum P014 deployment
gates remain later work.

## Implemented Boundary

- Capability-authorized result readback bound to the durable receipt, exact raw
  byte count and SHA-256 digest, strict JSON and schema checks, the original
  request, successful outcome, retained artifact, and guardian confirmation.
- A strict `result-view-v1` projection that excludes raw or prepared text, token
  streams, feature words, fitting vectors, capabilities, secrets, server paths,
  and private ownership identifiers.
- Complete retention of the declared 100, 300, 500, and 1000 MFW cells, including
  explicit complete, not-enough-features, and failed states.
- A fixed 500-MFW reading reference and a display-only complete-cell selector
  that cannot rerun, optimize, rank, erase, or substitute analytical cells.
- An exact distance-matrix heatmap, exact-tie-preserving nearest-neighbour table,
  deterministic work-level classical MDS map, and keyboard-adjacent semantic
  tables derived from the same selected validated matrix.
- Beginner-first explanations, panel-specific shows and does-not-show limits,
  and claim lint that blocks authorship proof, confidence, probability, pure
  style, causal age or maturation, turning-point, and equivalent claims.
- A result-only JSON export created before cleanup and published only after
  verified input and work absence, allowing the public lifecycle to report
  `Analysis complete` without retaining source text in the export.

## Passing Evidence

### Local source gate

`./scripts/verify.sh` passed with 1,522 tests and one documented macOS-only skip
for the canonical Linux scientific worker. All 11,377 measured statements and
2,964 branches were covered. Formatting, lint, strict typing, generated schemas,
metadata, provenance records, repository scanning, frozen upstream evidence,
and the R lock gate passed.

### Exact remote clean clone

The private GitHub origin was cloned without local-object reuse, detached at the
exact commit, and bootstrapped only from committed lockfiles. The same 1,522
tests and one documented macOS skip passed at 100% measured statement and branch
coverage. `git status --porcelain=v1` was empty after verification.

### Canonical Linux CI

GitHub Actions run `29402396790` passed on Ubuntu 24.04 x86_64:

- verify job `87309788046`: 1,523 tests passed, no skips, 100% of 11,377
  statements and 2,964 branches, 100 provenance records, generated-schema,
  SBOM, dependency, secret, metadata, repository, and R-lock gates;
- container job `87309788088`: the canonical Linux amd64 image built as
  `sha256:be1a6a98322a5ce1694b2588ac51e1b756d7d821b9a5fbdf1cfe1b50c40a8800`;
- canonical worker: R 4.5.2 with `stylo` 0.7.71;
- browser gate: three synthetic whole texts, 1,100 shared varying features,
  secure upload, corpus documentation, rights review, preparation, parameter
  confirmation, real R/stylo execution, all four result cells, the fixed
  500-MFW reading reference, two nonblank charts, semantic tables, and two
  result downloads passed;
- the result export matched its schema, document grid, cell grid, reference
  cell, exact distance matrices, finite numeric requirement, and privacy
  boundary; its SHA-256 was
  `b06c419a266931fb3c1b0d57b225b8fe1560383bdc642dda7d5eb34237dbb93c`;
- desktop 1280x900, mobile 390x844, and reflow 320x800 had no page or main
  horizontal overflow, overflowing controls, or incoherent overlap;
- the synthetic payload canary was absent and no external host was observed;
- unexpected browser console messages were empty.

Vega emitted five transient warnings while Streamlit rerendered the charts: one
distance warning and two warnings each for the x and y fields, all with the exact
text `Infinite extent for field ...: [Infinity, -Infinity]`. The gate allows only
these three exact warning forms, with a bounded total count, after independently
proving finite exported matrices and nonblank rendered chart pixels. The five
messages remain recorded separately; any different warning or error still fails
the gate.

Run URL:
<https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29402396790>

## Retained Failed Attempts

The failures are preserved rather than rewritten as successful runs.

1. CI `29395359809`, commit `dd515a9`: the browser gate encountered a corpus-form
   selector race before it could reach the new result presentation.
2. CI `29396477319`, commit `1b71cd3`: form interaction progressed, but result
   publication failed without a sufficiently specific browser-side reference.
3. CI `29397270285`, commit `084e4bc`: the added failure record still reported a
   generic result-publication reference.
4. CI `29398205876`, commit `a0138fb`: content-free lifecycle diagnostics proved
   that the scientific calculation succeeded while the result view remained
   absent.
5. CI `29398868867`, commit `86ace5c`: the complete result view and export were
   reached, but the second browser download was cancelled by a Streamlit rerun.
6. CI `29400116570`, commit `42c8bcc`: the audit closed an already-open corpus
   documentation expander during a rerender and could not continue the form.
7. CI `29401399006`, commit `59c2ce1`: every substantive product, export,
   privacy, chart-pixel, network, and viewport assertion passed. The run failed
   only because the strict console gate had not yet classified the five exact
   transient Vega warnings described above.
8. CI `29402396790`, commit `c5e39b0`: the product checks and the narrowed,
   evidence-backed console policy passed.

No corpus, scientific threshold, Delta value, distance matrix, or worker result
was altered to obtain the passing run. One earlier exact-clone macOS run also had
a single chart AppTest exceed its generic 20-second limit; the isolated test
passed, and only the two chart-rendering tests received a 40-second limit before
the final exact-clone pass.

## Claim Boundary

This evidence supports a functional synthetic minimum-alpha result path without
user-authored R, Python, or shell code. It does not establish general usability,
teachability, benchmark accuracy, authorship, confidence, literary findings,
Pinocchio findings, full all-purpose P009 completion, FAIR certification,
production isolation, public deployment, or publication readiness. Human owner
acceptance and the P014 activation gates remain pending.
