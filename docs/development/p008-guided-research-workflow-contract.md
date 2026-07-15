# P008 Guided and Research Workflow Contract

**Status:** Accepted minimum-alpha method boundary; full Research preset remains
locked.

**Owner:** Oğuz Koran

**Implementation branch:** `codex/p008-workflows`

## 1. Purpose

P008 connects a documented corpus to the existing P006 `stylo` engine without
requiring the researcher to write R, Python, or shell commands. It removes the
coding prerequisite; it does not remove responsibility for corpus design,
method choice, or interpretation.

The first public-alpha slice exposes one bounded whole-text Guided workflow.
The complete ticket later adds all three purpose-specific paths, the accepted
Research preset, and the full cancellation/retry browser evidence.

## 2. Closed Guided Profile

| Field | Resolved value | Meaning |
|---|---|---|
| Profile | `guided-grid-v1` | Versioned public Guided profile |
| MFW | 100, 300, 500, 1000 | Four declared feature-count cells |
| Culling | 0% | No document-frequency culling in the alpha profile |
| Analysis unit | `whole_text` | Each independent work remains one document |
| Distance | `classic_delta` | Primary Burrows's Delta implementation in P006 |
| Fixed reference | 500 MFW | A reading reference, never a selected optimum |
| Seed | 20260713 | Frozen P006 environment seed |
| Cell count | 4 | One distance cell for each MFW value |

All four requested cells remain part of the resolved configuration. If the
known corpus cannot support a requested MFW value, P006 returns a typed
`not_enough_features` state for that cell. Delta does not substitute another
MFW value, suppress the cell, or call the reference cell best.

## 3. Analysis Scope

`transductive_exploratory` applies when all documents are declared known. The
distance map describes relative position within the supplied corpus. It is not
an out-of-sample authorship test.

`unknown_holdout` applies when at least one document is explicitly declared
unknown. Unknown documents are projected only after the known basis is frozen.
They cannot alter candidate order, culling eligibility, means, standard
deviations, parameter selection, or a later calibration threshold.

P007 already binds every role to the READY receipt. Changing a role after
review invalidates admission.

## 4. Resolved Configuration

Before Run, the server creates one immutable `resolved-workflow-config-v1`
record containing:

- research purpose;
- workflow mode and profile version;
- analysis scope;
- preprocessing profile;
- whole-text analysis unit;
- ordered MFW, culling, and distance values;
- fixed reference cell;
- deterministic seed and declared cell count.

Canonical UTF-8 JSON is hashed with SHA-256. The review screen and private P006
request builder must use the same validated object. Unknown fields, reordered
or duplicated values, unsupported settings, more than 24 public cells, or a
hash mismatch fail closed. No UI label is a source of authority.

## 5. Admission and Execution

1. P007 validates and privately prepares the corpus.
2. A blocker-free P007 READY receipt is issued for one hour at most.
3. P008 resolves the supported configuration and shows it before Run.
4. The private builder rechecks the corpus, annotations, preprocessing,
   candidate inventory, READY receipt, and resolved configuration.
5. The exact P006 input is written inside the owned workspace.
6. Existing SQLite admission consumes READY and moves the staged job to queued
   in one transaction.
7. The P006 runner claims, executes, validates, persists, and guardian-confirms
   the result.
8. Only a guardian-confirmed scientific result is shown as complete.

A double click, refresh, duplicated browser tab, process restart, reused
receipt, expired receipt, changed configuration, or lower-level enqueue attempt
must not create a second analysis.

## 6. Beginner-Facing Review

The Parameters surface must answer five questions without assuming stylometry
knowledge:

1. What is being compared?
2. Which words enter each cell?
3. What does 0% culling mean here?
4. Which distance is calculated?
5. Which cells are available for this corpus?

The review shows the four cells, availability, fixed reference, analysis scope,
cell count, and content-free configuration hash. It says explicitly that more
features are not automatically better and that proximity is not proof of
authorship, cause, influence, quality, or chronology.

## 7. Research Mode Boundary

Research Mode is not an arbitrary parameter form. Its future public preset is
named `research-grid-v1`, has at most 24 predeclared cells, and is versioned and
hashed before results are viewed. The exact culling values and any future
segmentation choices are not yet human-accepted; therefore the alpha interface
must show Research Mode as unavailable rather than invent a grid.

The P006 192-cell transport capacity is a controlled publication-batch ceiling,
not a public UI allowance.

## 8. Failure and Recovery

- Before admission: validation failure leaves no queued job and permits an exact
  correction/review cycle while the private lease remains valid.
- Queue saturation: READY remains retryable only when the existing durable
  admission contract reports that it was not consumed.
- After admission: the same READY authority cannot be reused.
- Cancellation: a durable cancellation request is shown as requested until the
  worker reaches a terminal state.
- Partial result: every failed or unavailable cell remains visible and counts
  toward completeness.
- Retry after a terminal run creates a new preparation/admission authority; it
  never mutates or erases the earlier run record.

## 9. Public-Alpha Claim Boundary

Passing P008 can establish that the exposed workflow runs the declared P006
configuration without user-written code and preserves the tested admission and
result-validation boundaries. It cannot establish accuracy, reliability across
corpora, general usability, teachability, authorship, causal stylistic change,
stability, calibration, FAIR certification, reproducibility, production
isolation, or publication readiness.

