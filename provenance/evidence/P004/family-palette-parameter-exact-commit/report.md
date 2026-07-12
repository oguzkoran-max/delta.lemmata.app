# P004 Family Palette and Parameter Exact-Commit Verification

**Date:** 2026-07-12

**Ticket:** `P004`

**Run:** `RUN-20260712-0003`

**Exact commit:** `54e479d1075f3c73ee4a707090e3c43e10488085`

## Procedure

The repository was cloned locally with `git clone --no-hardlinks`, detached at the
exact implementation commit, and bootstrapped from its committed Python and R
lockfiles. The clone did not reuse the source repository's working tree, virtual
environment, or Git object hardlinks.

The canonical repository gate and complete P004 browser harness were run inside
that clone. The browser output was copied into this evidence directory only after
the detached run completed.

The first wrapper invocation was started from `/tmp` before obtaining the source
repository's SHA and stopped immediately with `not a git repository`. It created
no clone and is not counted as execution evidence. The corrected invocation began
from the canonical repository, then changed into the new clone before bootstrap.

## Result

The exact commit passed:

- locked Python 3.13.9 and `uv` 0.11.28 bootstrap;
- locked R 4.5.2 and `stylo` 0.7.71 restore;
- Ruff formatting and lint;
- strict mypy;
- 468 tests with 100% of 3,171 statements and 880 branches;
- metadata, schemas, 58 pre-additive provenance records, repository scan,
  supply-chain tests, and R-lock checks;
- the fresh-process P004 browser harness across six Upload and six Review
  viewports;
- computed family palette, no-gradient, text-contrast, semantic sidebar and
  parameter orientation, first-action, next-stage, and no-overflow checks;
- individual-TXT and two-member ZIP Upload-Describe-Review regressions;
- no submitted-text echo, external host, or browser console warning/error.

`git status --short` was empty after bootstrap, verification, and browser testing.

## Evidence

- `browser-audit/browser-audit.json`
- `browser-audit/screenshots/`
- `../family-palette-parameter-orientation-validation.md`
- `../family-palette-parameter-exact-commit.sha256`

## Limits

The clone used the same Mac and may have linked or reused package-cache objects
managed by `uv` and `renv`. Chromium was used rather than Safari or VoiceOver.
Inputs were synthetic. This run does not establish scientific validity, calibrated
stability, production isolation, retention enforcement, general usability, or
P004 human acceptance.
