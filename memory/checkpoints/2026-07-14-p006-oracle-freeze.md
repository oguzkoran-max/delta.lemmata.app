# P006 Independent Oracle Freeze Checkpoint

## State

The independent direct-`stylo` reference is frozen before worker implementation.
Source commit `7df1fdf754ecfb3a0b84835dc7f368c481f333f1` passed normal CI run
`29295419945` and one-time capture run `29295419981`. Bot commit
`b5a842fdee5456c7f5f9d0397c0f5a2f7d7a336f` retains the checksum-bound evidence.

## Decisions Preserved

- CC0 project-authored integer-count fixtures only; no literary text.
- Whole-text, known-only fitting under R 4.5.2 and `stylo` 0.7.71.
- Classic Delta primary; Eder and Cosine separate sensitivity distances.
- Exact ordered features, `1e-6` matrix parity, and `1e-12` structural/tie
  thresholds remain the accepted future worker-comparison protocol.
- Claims remain fixture-local and version-specific.

## Failures Preserved

Three capture attempts stopped safely before evidence publication: broad environment
classification, an unreadable locked R cache, and cross-user output permissions.
The successful fourth attempt ran twice without network and produced byte-identical
outputs. Details are in
`provenance/evidence/P006/oracle-freeze-validation.md`.

Independent security review found that the active remote workflow had to be disabled
before the deletion commit and that current-tree hashes did not prove the declared
bot evidence commit. Workflow `312640736` was manually disabled. The durable
validator now checks the exact evidence commit, sole-parent source relationship,
six-file change set, Git blob bytes, and Run-record binding.

## Post-freeze Audit

Independent method review found two P1 fixture blind spots. Every v1 document has
`token_total=100`, so raw counts and relative frequencies are indistinguishable in
the input scale. The only unknown is also the final row, so positional role bugs and
multiple-unknown behavior are untested. V1 is retained as an immutable, correctly
executed intermediate record, not the final parity oracle.

The review also narrowed environment wording: the evidence binds observed package
versions and the `renv` lockfile but does not retain CRAN archives, the built image,
or a fully pinned APT dependency set.

## Current Boundary

The oracle is not the product worker and is not a parity result. Public analysis,
preprocessing, benchmark claims, Pinocchio, production isolation, and FAIR run
packages remain in later tickets. P006-AC-01 and P006-AC-05 alone are passed.

## Next Action

Create and freeze a strengthened v2 suite before implementing the fixed worker. V2
must use unequal document totals, demonstrate a numeric difference from a raw-count
counterfactual, and interleave at least two unknown rows among known rows. Then
implement the fixed `Rscript --vanilla` worker and Python adapter with a separate
trusted `C.UTF-8` execution profile. Do not connect durable success or guardian
acknowledgement until artifact digest/size binding and crash recovery are defined
and tested.
