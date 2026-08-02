# Collodi teaching-demo execution overlay

## Purpose

This directory freezes the results-blind execution state for the bounded
Collodi worked example in the Delta paper. The example demonstrates how
`delta.lemmata.app` prepares, executes, verifies, and documents a Classic
Delta analysis without requiring the researcher to write R or Python code.

The example is not designed to establish authorship, ageing, a causal
Pinocchio effect, a formal periodisation, or a population-level claim. It
contains three known works by Carlo Collodi and is therefore a descriptive,
non-inferential teaching demo only.

## Frozen analysis design

- Dataset: `DATA-COLLODI-DEMO-V1`
- Protocol: `PROTO-EVAL-DELTA-1.1`
- Documents: 3 whole texts
- Preprocessing: `delta-surface-words-v1`
- Distance: Classic Delta
- Culling: 0 percent
- MFW sensitivity grid: 100, 300, 500, and 1000
- Display condition: 500 MFW only
- Seed: `20260713`
- Candidate features: 13,495

All four MFW conditions are confirmatory execution cells registered before
any result was produced. The 500-MFW condition is the display condition, not
a condition selected after inspecting results.

## Frozen software and request

- Source commit: `31e09782ba07e6709cbdcca48bc9db22e6c49723`
- Container image: `ghcr.io/oguzkoran-max/delta.lemmata.app@sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa`
- Canonical request SHA-256: `0eb1c53ca5e1f930cd7a331cf13b6b090cf68083b8a16a0bb846c496160fe5f0`
- Request component name: `28e9d3d83efa686b8b51b80eccd9b4f3439aeb56141e459abd97729c9c5b9184`
- Result component name: `053bf21e22c557bd2e9cc53b858b02603c19200680fe1cc2d885bd1b11d6987b`
- Fatal component name: `24ae13b5ee15a59e2f7924a480c4160907d13e900a8d879f1d81b0faab8f6548`

The request was generated twice in separate directories. Both complete input
trees were byte-identical. The canonical request was also parsed and
re-serialised by the frozen application contract without any byte change.

## Rights-preserving public execution

The clean text files are intentionally excluded from the public GitHub
evaluation branch because the corpus lock authorises internal analysis and
derived numerical publication but does not yet authorise public redistribution
of the cleaned texts. The public workflow therefore verifies and executes the
sealed canonical request rather than reconstructing it from redistributed
texts. Source URLs, witness metadata, cleaning hashes, clean-text hashes, the
deterministic builder, and the local preflight evidence remain documented.

Researchers with lawful access to the source witnesses can reconstruct the
same request and compare its SHA-256 value. This is an explicit FAIR access
condition, not an omitted provenance step.

## Directory map

- `config/`: immutable execution contract and results-blind preflight record
- `input/`: canonical worker request and prepared matrices for four MFW cells
- `scripts/`: deterministic request builder, independent R oracle, comparator,
  and preflight validator
- `workflow/`: isolated GitHub Actions execution recipe

The parity comparator intentionally retains its accepted internal literary
fixture filenames. It is copied byte-for-byte from the previously accepted
parity workflow so that the comparator itself is not silently changed for
this example.

## Execution rule

The Delta worker and the direct `stylo` oracle must receive the same prepared
matrix. The workflow runs inside the pinned container with no network,
read-only filesystem access, and all Linux capabilities dropped. A run is
accepted only if every MFW cell satisfies the locked numerical, structural,
ordering, and tie-group checks.

No distance matrix, MDS coordinate, cluster, or literary interpretation may
be retained unless the complete parity gate passes. A failed run remains a
methodological record and cannot be converted into a substantive result.

## Reproduction order

1. Verify the upstream corpus lock.
2. Rebuild the canonical request from the three clean texts.
3. Run `validate_demo_execution.py` against the frozen source tree.
4. Verify the sealed request SHA and canonical application contract in the
   rights-preserving public evaluation branch.
5. Execute `workflow/collodi-demo.yml` in that isolated branch.
6. Verify worker output against the independent direct-R oracle.
7. Package raw outputs, comparison reports, software identity, and checksums.
8. Interpret only the descriptive pattern and the MFW sensitivity after all
   parity checks pass.

This README describes a results-blind state. It contains no numerical Delta
result and no claim about Collodi's stylistic development.
