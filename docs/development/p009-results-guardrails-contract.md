# P009 Results and Guardrails Contract

**Status:** Accepted minimum-alpha implementation boundary.

**Owner:** Oğuz Koran

**Implementation branch:** `codex/p009-results`

## 1. Purpose

P009 turns a validated P006 distance result into an inspectable workbench view.
It helps a researcher see how relative proximity changes across the declared MFW
cells while keeping failed cells and interpretation limits visible. It does not
write a literary conclusion, estimate authorship probability, or choose a
preferred parameter after seeing the output.

## 2. Trusted Input

The only numerical input is one guardian-confirmed `stylo-worker-result-v1`
artifact retained by P006. Before use, the server reauthorizes the owning session
and checks the artifact against its durable receipt: component, byte count,
SHA-256, strict JSON/schema semantics, request ID, worker version, and complete
or partial outcome. A missing, expired, altered, unconfirmed, invalid, or
unauthorized result fails closed. The retained R payload need not reproduce
Python's byte spelling for equivalent JSON numbers; its exact received bytes are
still bound to the durable receipt before semantic validation.

The browser receives a bounded presentation model, not the private worker input
or workspace. Raw text, token streams, candidate/selected feature words,
capabilities, secrets, server paths, and private workspace identifiers are not
part of the result-view contract.

## 3. Complete Cell Visibility

The result overview lists all four requested Guided cells in declared order. Each
cell is exactly one of:

- `complete`: its validated matrix is available;
- `not_enough_features`: the corpus could not support the requested MFW count;
- `failed`: fitting or distance calculation failed with a typed public code.

The 500-MFW reference opens first if complete. Otherwise the first complete
declared cell opens with an explicit notice that the reference was unavailable.
Changing the selected detail cell only changes the view; it does not rerun the
analysis, erase other cells, or mark the selected cell as best.

## 4. Visual and Tabular Views

Every complete selected cell has three views derived from the same validated
matrix:

1. **Distance heatmap:** every ordered matrix pair and exact Delta distance.
2. **Nearest neighbours:** one row per work, preserving all exact minimum-distance
   ties rather than choosing one arbitrarily.
3. **Classical MDS map:** a deterministic two-dimensional representation of the
   matrix, with sign-stable coordinates and an explicit approximation warning.

Every chart has a semantic table containing the same work labels and values.
The heatmap legend says that smaller values mean greater relative proximity. MDS
axis names are computational coordinates, not literary dimensions.

## 5. Result View and Download

The canonical `result-view-v1` package contains:

- research purpose, analysis scope, workflow profile, and configuration digest;
- non-secret display document keys, titles, and known/unknown roles;
- every declared cell and its exact status;
- validated distance matrices for complete cells;
- fixed-reference identity and public interpretation boundaries.

It excludes raw/prepared text, word-frequency vectors, ranked or selected feature
words, fitting means/standard deviations, server paths, capabilities, secrets,
and private ownership identifiers. Its canonical bytes are written to the export
area before P005 cleanup; the lifecycle exposes `Analysis complete` only after
input and work areas are verified absent and the export is published.

## 6. Interpretation Guardrails

Each analytical panel answers:

- `What this shows`: the exact relative pattern represented by that panel.
- `What this does not show`: authorship, authenticity, influence, intention,
  chronology, quality, cause, or an intrinsically meaningful map axis.

The UI copy, download, fixtures, and tests reject confidence, probability of
authorship, proof, pure style, caused by age, maturation, and turning-point claims.
Unknown work remains a projection-only holdout; an all-known result remains
transductive and exploratory.

## 7. Public-Alpha Scope

The minimum slice includes the four-cell overview, selectable matrix heatmap,
nearest-neighbour table, classical MDS map, semantic-table parity, bounded JSON
download, claim lint, and desktop/mobile/reflow browser evidence. Dendrograms,
purpose-specific Style Over Time graphics, group inferential summaries, broad
glossary, calibration, stability labels, FAIR release packages, and literary case
study findings remain in later full P009-P013 work.

Passing this slice can establish that Delta presents the tested result artifact
through the declared views and guardrails. It cannot establish accuracy across
corpora, general usability, teachability, authorship, causal stylistic change,
stability, FAIR certification, reproducibility, production isolation, or
publication readiness.
