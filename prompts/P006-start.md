# P006 Execution Brief

**Record type:** Agent-prepared, human-owned ticket execution brief

**Not a PromptEvent:** The user's native continuation request is retained separately
as a hash-bound PromptEvent. This file expands the accepted roadmap into an
engineering plan; it is not presented as the user's verbatim request.

```text
P006: R stylo Worker and Computational Parity

Read START_HERE.md, SESSION_HANDOFF.md, the P006 roadmap section, CE-04 and CE-07,
SEC-06 through SEC-08, RP-05, EPI-03, ADR-0002, ADR-0012, and proposed ADR-0013.
Do not reopen accepted product decisions. Do not treat the start package as parity,
scientific validation, public analysis, deployment, or human acceptance.

Implement in this order:

1. Freeze closed v1 input, output, and error schemas before implementing the worker.
   Reject duplicate JSON keys, NaN, Infinity, unknown fields, malformed UTF-8, and
   unbounded strings or arrays. JSON Schema is necessary but not sufficient; add a
   semantic validator for all matrix and fitting invariants.
2. Keep P006 whole-text and frequency-table based. Upstream tokenization,
   normalization, punctuation/number handling, segmentation, duplicate checks, and
   corpus-health behavior remain P007. P006 receives candidate features and raw
   per-document counts with opaque asset/work identifiers.
3. Rank features, perform culling, compute relative frequencies, and derive mean and
   standard deviation using known documents only. Unknown documents are projected
   into the already frozen feature and scaling space. A changed unknown canary must
   not change any fitting artifact or known-known distance.
4. Match stylo 0.7.71 ordering: aggregate known counts establish the MFW order under
   the frozen C collation; culling is applied to the ranked full table before the
   requested MFW prefix is selected. Insufficient features fail explicitly rather
   than silently lowering MFW.
5. Use Classic Burrows Delta as the primary distance. Eder's Delta and Cosine Delta
   are independent sensitivity results and are never averaged. For known-derived
   z-scores call stylo distances without re-fitting. Do not use a path that rescales
   combined known and unknown rows.
6. Treat process exit and analysis acceptance as different states. Exit zero only
   means the process stopped normally. Read the bounded output securely, validate
   schema and scientific invariants, persist the mapped terminal result, and only
   then acknowledge the guardian.
7. Use exactly one fixed command shape: trusted absolute Rscript, --vanilla, and the
   trusted absolute R/stylo_worker.R entrypoint. User content, parameters, labels,
   metadata, filenames, paths, or R expressions never enter argv or environment.
8. Preserve the P005 opaque-file boundary. Use fixed 64-character hexadecimal file
   names, private creation permissions, atomic temporary-to-final replacement,
   O_NOFOLLOW reads, regular-file and single-link checks, bounded size, and inode
   stability. Do not weaken the workspace filename policy for readable names.
9. Validate one output or one fatal-error envelope. Every requested cell appears
   exactly once. Complete, partial, and failed analysis outcomes are derived from
   validated cells; missing or corrupt cells invalidate the complete envelope.
10. Validate finite non-negative matrices, exact square shape, unique canonical
    labels, zero diagonal, symmetry, feature order, fitting document IDs, positive
    known-only standard deviations, and exact input/output cardinality.
11. Build project-authored deterministic synthetic fixtures only after Oğuz records
    a HumanDecision for the proposed CC0 license, C.UTF-8/UTC environment, seed,
    tolerances, metric scope, and claim boundary. Do not use LiberLiber, Pinocchio,
    P010 locked data, or any literary case-study result as the P006 oracle.
12. Run an independent direct-stylo reference harness before comparing the Delta
    worker. It may use stylo and base R only; it must not import the Python adapter,
    worker helpers, expected result files, or Delta calculations. Hash and freeze
    the reference outputs before worker evaluation.
13. Predeclare feature equality as exact, parity matrix maximum absolute difference
    as 1e-6, structural symmetry/diagonal tolerance as 1e-12, and tie grouping as
    1e-12, subject to the separate HumanDecision. Record actual locale, R/stylo,
    packages, RNG, BLAS, LAPACK, image digest, and entrypoint version in every run.
14. Test injection, malformed output, duplicate keys, non-finite numbers, ragged and
    asymmetric matrices, wrong labels, insufficient features, unknown leakage,
    process timeout, cancellation, partial cells, output races, clean clone, Linux
    CI, and canonical container execution. Preserve failed evidence honestly.

P006 may establish only fixture-local whole-text worker parity and the worker-level
known/unknown fitting-invariance portion of CE-07. Do not mark CE-04 fully verified
before P007 or CE-07 fully verified before P010/P011. Do not activate the public Run
button or claim accuracy, reliability, preprocessing parity, clean-room
reproducibility, FAIR certification, Pinocchio findings, or production isolation.
```
