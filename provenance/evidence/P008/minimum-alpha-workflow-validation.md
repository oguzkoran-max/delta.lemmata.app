# P008 Minimum-Alpha Workflow Validation

## Scope

This record validates the exposed four-cell Guided whole-text slice at exact
commit `7e9a28eafa4756b2cf82e6d6f3d8e0c43742edf5`. It does not close the full P008
ticket. The three-purpose workflow matrix, known/unknown scope variants, and the
human-accepted `research-grid-v1` remain later P008 work.

## Implemented Boundary

- Canonical `resolved-workflow-config-v1` parsing, serialization, and SHA-256
  binding.
- Exact Guided grid: 100, 300, 500, and 1000 MFW; 0% culling; whole text;
  Classic Delta; seed 20260713; fixed 500-MFW display reference.
- Review-before-run configuration table, beginner explanations, explicit method
  limits, and downloadable resolved configuration.
- One-time P007 READY admission bound to the immutable P008 configuration and
  existing P006 request.
- Real queued execution through the locked R 4.5.2 and `stylo` 0.7.71 boundary.
- Public Research Mode remains visibly locked; no arbitrary controls or silent
  parameter downgrade were introduced.

## Passing Evidence

### Local source gate

`./scripts/verify.sh` passed with 1,458 tests and one documented macOS-only skip
for the canonical Linux worker integration. All 10,624 measured statements and
2,764 branches were covered. Formatting, lint, strict typing, generated schemas,
metadata, 96 provenance records, repository scanning, frozen P006 evidence, and
the R lock gate passed.

### Exact remote clean clone

The private GitHub origin was cloned with `--no-hardlinks`, detached at the exact
commit, bootstrapped only from committed Python and R lockfiles, and verified.
The same 1,458 tests and one documented macOS skip passed at 100% measured
statement and branch coverage. `git status --porcelain=v1` was empty after the
run.

### Canonical Linux CI

GitHub Actions run `29388984019` passed on Ubuntu 24.04 x86_64:

- verify job `87268030351`: 1,459 tests passed, no skips, 100% of 10,624
  statements and 2,764 branches, 96 provenance records, SBOM, dependency,
  secret, schema, metadata, repository, and R-lock gates;
- container job `87268030358`: canonical Linux amd64 image built as
  `sha256:dad60c946d0409cdc5d678b4e96d54d71a0b693913609ac97b081300e14a4584`;
- browser gate: three synthetic whole texts, 1,100 shared varying features,
  upload, documentation, rights review, preparation, all four MFW capacities,
  parameter confirmation, and the real R/stylo execution passed;
- the resolved configuration download matched the exact four-cell profile;
- desktop 1280x900, mobile 390x844, and reflow 320x800 had no page or main
  horizontal overflow, overflowing controls, or misframed table-scroll regions;
- browser console errors/warnings and observed external hosts were empty;
- the synthetic payload canary was absent from rendered output;
- the UI stopped honestly at the successful P008 validated-result boundary and
  stated that evidence review and result visualizations belong to P009.

Run URL:
<https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29388984019>

## Retained Failed Attempts

The failures are preserved rather than rewritten as successful runs.

1. CI `29388187630`, commit `9c7497c`: the real calculation reached the P008
   validated-result boundary, but the browser harness waited for P009's future
   `Analysis complete` state and timed out. The product calculation was not the
   observed failure.
2. CI `29388674911`, commit `46daea2`: every preparation, parameter, viewport,
   real-worker, privacy, console, and network check passed. The gate failed only
   because it required an exact match for the second sentence inside a two-sentence
   P009 handoff notice.
3. CI `29388984019`, commit `7e9a28e`: the corrected, boundary-aware gate passed.

This history demonstrates that the gate was corrected to the declared ticket
boundary. No scientific threshold, corpus, Delta value, or worker output was
changed to obtain a pass.

## Claim Boundary

This evidence supports a functional minimum-alpha Guided upload-to-validated-P006
path without user-authored R, Python, or shell code. It does not establish general
usability, teachability, benchmark accuracy, authorship, confidence, parameter
optimality, literary interpretation, all-purpose P008 completion, P009 result
quality, FAIR certification, production isolation, or public-release readiness.
The integrated Oğuz Koran owner walkthrough remains pending before activation.

