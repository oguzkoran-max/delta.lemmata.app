# P014 Phase B Visual Integration Validation

## Scope and Claim Boundary

This record validates the Phase B transfer of the approved Claude Code A5.1
visual and accessibility contract into the real Delta Streamlit application at
exact implementation commit
`3a554e0e76522672efaf547b1d03e12cb4f3531b`. It covers Entry, Review,
Parameters, and Results presentation, responsive geometry, local font
packaging, accessible controls and landmarks, semantic result tables, chart
pixel evidence, and the existing upload-to-R/`stylo`-to-export workflow.

This is a visual-integration and regression record. It does not validate P011
parameter stability, a complete P012 FAIR package, the Pinocchio case study,
general usability or teachability, screen-reader conformance, public
deployment, shared-VPS readiness, or a literary finding. P014 remains
`in-progress`; this record does not close P014-AC-08 through P014-AC-10.

## Design Source and Handoff Chain

The implementation follows the Claude Code Phase A5.1 review package:

- package: `~/Desktop/Delta-Phase-A51-Review/`;
- Claude report:
  `~/.codex/attachments/3c2c8d45-61bb-4c75-9230-f1546cddb382/pasted-text.txt`;
- package manifest SHA-256:
  `9eb0f4466c65be202733920dfd9c8632eea4b29a409cbad66f2acc38cd8dd866`;
- Claude report SHA-256:
  `030fa408755c1ecb0f691774b3ad799ce686d0f058f6fd4c3c39c6782008c93f`;
- manifest check: 24 listed files, 24 passed on 2026-07-17;
- Phase B base:
  `26947e1f6843b2b4dc1d1b0cc552c0af808be3fa`;
- implementation branch: `codex/p014-visual-phase-b`;
- draft pull request: [#8](https://github.com/oguzkoran-max/delta.lemmata.app/pull/8).

The external package is referenced, not copied into the repository. The
repository therefore retains a content-free, independently checkable source
locator while avoiding duplicate prototype binaries and screenshots.

## Implemented Boundary

- Entry places upload before extended teaching content and retains the three
  declared research purposes without claiming general ease of use.
- Review shows purpose-aware, human-readable issue groups and keeps raw
  diagnostic codes under `Technical details`.
- Results expose all four Guided MFW cells, keep 500 MFW as a display reference,
  show an exact numerical distance matrix, matrix-local heatmap, nearest-neighbour
  ties, and an equal-domain MDS projection with interpretation limits.
- Native Streamlit radio inputs remain keyboard-operable. Every audited view has
  one visible H1, one main landmark, one footer, a functioning skip link, local
  Inter, and no control below the 44 px target threshold.
- Wide tables remain named horizontal scroll regions. Mobile MFW choices reflow
  to two rows without changing scientific configuration.
- P006-P009 scientific calculations, the fixed Guided grid, export contract,
  privacy boundary, and claim lint remain unchanged.

## Canonical Passing Evidence

GitHub Actions push run
[`29541220413`](https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29541220413)
tested the exact implementation commit on GitHub-hosted Ubuntu 24.04 x86_64.
It started at `2026-07-16T23:03:03Z` and completed successfully at
`2026-07-16T23:08:20Z`.

- verify job `87763699921`: `2026-07-16T23:03:07Z` to
  `2026-07-16T23:08:19Z`, passed;
- container job `87763699936`: `2026-07-16T23:03:07Z` to
  `2026-07-16T23:07:12Z`, passed;
- 1,670 Linux tests passed with no skip;
- all 11,507 measured statements and 3,002 branches were covered;
- formatting, Ruff, strict mypy, generated schemas, frozen scientific oracles,
  metadata, 109 pre-existing provenance records, repository scan, R lock,
  wheel-resource, SBOM, dependency, and secret gates passed;
- R 4.5.2 and locked `stylo` 0.7.71 executed the synthetic real-worker flow;
- all four Guided cells completed and remained simultaneously visible;
- the 500-to-1000 MFW display change altered both matrix and MDS semantic
  digests and produced changed, nonblank chart pixel evidence;
- result schema, finite matrix values, semantic tables, interpretation limits,
  filename, payload exclusion, private-material exclusion, and result export
  passed; export SHA-256 was
  `eb6472eae8c855826a32354e973f2853e2bae93b9b9c3ae7b09c9ff510835886`;
- no unexpected console message or external browser host was observed.

The parallel pull-request run
[`29541222417`](https://github.com/oguzkoran-max/delta.lemmata.app/actions/runs/29541222417)
also passed verify job `87763705842` and container job `87763705851`. That run
checked GitHub's synthetic PR merge commit; the push run above is the canonical
exact-head record.

## Responsive and Visual Measurements

Entry and Review passed at 1440x1000, 1280x900, 390x844, 375x844, and 320x800.
Parameters passed at 1280x900, 390x844, and 320x800. Results passed at all five
Entry/Review viewports.

Across those audited views there was no page or main horizontal overflow, no
overflowing control, no unscrollable table region, and no result control below
44 px. Local Inter loaded in every audited view. Each Results viewport exposed
four result cells and two nonblank visualizations.

The actual MDS Vega plot frames were:

| Viewport | Plot width | Plot height | Absolute difference |
|---|---:|---:|---:|
| 1440x1000 | 336.96875 px | 338.015625 px | 1.046875 px |
| 1280x900 | 262.96875 px | 262.453125 px | 0.515625 px |
| 390x844 | 293 px | 294.125 px | 1.125 px |
| 375x844 | 278 px | 278.78125 px | 0.78125 px |
| 320x800 | 222 px | 221.609375 px | 0.390625 px |

Every frame remained within the declared 2 px square tolerance. This geometry
supports visual parity only; MDS axes still have no independent literary
meaning and the distance matrix remains the authoritative evidence.

## Local Verification and Reviews

Before canonical CI, the exact implementation worktree passed
`./scripts/verify.sh` on macOS with 1,669 tests and one documented
canonical-Linux-only skip. All 11,507 measured statements and 3,002 branches
reached 100% measured coverage; 109 provenance records were valid.

Three separate read-only local/agent review passes examined scientific method,
accessibility, and release scope and returned GO after remediation. They were
not GitHub reviews, participant usability tests, or owner activation acceptance.
Oğuz Koran remains the scientific, merge, and activation decision owner.

## Retained Attempts

Earlier failures are retained because they materially improved the browser
gate rather than being erased:

1. Commits `bdddff5b9387f49cb7d5966e6069648748c259fa`, runs
   `29537459996` and `29537500260`: verify tried to click Streamlit's hidden
   native radio input instead of the visible result card; both container jobs
   passed.
2. Commit `698b4d99d2a964c8a195e90b8a3c7741c1f93a7c`, runs
   `29537966800` and `29537990646`: verify exposed a 26x26 Vega action target
   and MDS frame rounding failures at responsive widths; both container jobs
   passed.
3. Commit `b68a75930b07ae482d74b03bd1ee7a7164ff89bf`, runs
   `29539267537` and `29539270235`: verify retained one 375 px MDS rounding
   failure; both container jobs passed.
4. Commit `178a2dfbb217a52a94720cd8aceaee36464ac60e`, runs
   `29540004995` and `29540007009`: the push gate falsely treated normal
   internal text scrolling in a native select input as viewport overflow and
   still searched for removed copy; the PR gate timed out on Streamlit's
   internal script-state signal after the 1000-MFW selection. Both container
   jobs passed.
5. Commit `3a554e0e76522672efaf547b1d03e12cb4f3531b`, runs
   `29541220413` and `29541222417`: result selection was verified through stable
   semantic matrix/MDS digests, input-box geometry was distinguished from text
   value scrolling, and completion was checked through the four visible result
   cards. Both verify and both container jobs passed.

No scientific parameter, corpus value, distance, chart datum, interpretation
threshold, or export payload was altered to make these gates pass.

## Acceptance Mapping

- P014-AC-06: strengthened by accessible release labels, claim-boundary copy,
  responsive controls, landmarks, and automated visual assertions.
- P014-AC-07: strengthened by exact-head canonical Linux source, real-worker,
  installed-wheel, browser, supply-chain, and hardened-container reruns.
- P014-AC-08 through P014-AC-10: not exercised by this work and remain pending.

The branch is review-ready as a draft pull request. This record does not
authorize merge, image publication, VPS modification, Caddy or DNS changes, or
public activation.
