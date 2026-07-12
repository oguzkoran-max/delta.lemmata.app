# P004 Lemmata Live Comparative Audit

## Scope

- Date: 2026-07-12
- Target: `https://lda.lemmata.app/`
- Reported application version: `v0.1.0`
- Surfaces: live desktop layout and `390x844` mobile viewport
- Purpose: establish a verified sibling-product usability baseline for P004 and later
  Delta result-design work
- Privacy boundary: no user, research, copyrighted, or local project file was uploaded

## Test Input

The successful run used a synthetic Italian corpus generated from three short topic
clusters: family and domestic life, landscape and nature, and war and public life.
Each cluster sentence block was repeated 110 times and the three blocks were
concatenated in that order.

- Characters: `71,060`
- Application estimate: approximately `12,100` words
- SHA-256 of submitted UTF-8 text:
  `461161b342366b58c4f2d3e5a361dad3d19719da2a2d53ebc1bbc617d5313729`
- Language: Italian
- Chunk size: `1,000` words
- Topics: `5`
- Words per topic: `10`
- POS preset: `Content words`
- Advanced settings: application defaults with corpus-size auto-adjust enabled

The first attempt alternated the three clusters throughout the text. It failed after
document-term pruning because every surviving term appeared too broadly. This failure
was retained as evidence about public error handling rather than treated as a model
result.

## Observed Journey

1. The initial page exposed upload and paste-text actions, a compact three-step
   introduction, method help, and sidebar parameters.
2. The sample-data panel linked to a repository rather than loading an example inside
   the application.
3. The paste control required `Command+Enter` before `Run Analysis` became available.
4. The application estimated document count and warned that more than four topics
   could be unreliable for the first approximately eight-document corpus.
5. The failed run displayed a useful plain-language alert but also exposed a raw
   Python traceback, server paths, and dependency internals under Technical details.
6. The grouped synthetic corpus completed and produced Overview, Topics, Topic Map,
   Heatmap, Distribution, Preprocessing, and Export tabs.
7. The successful run reported 13 documents/chunks, 43 unique lemmas, C_v coherence
   `0.8909`, perplexity `17.2`, and log-likelihood `-13447.3`.
8. The application warned that all 50 iterations were used without convergence and
   that 43 unique lemmas might be insufficient for meaningful interpretation.

## Strengths to Preserve

- Upload is visible immediately on desktop and the basic journey is concise.
- Common and advanced controls are separated.
- Topic interpretation clearly states that statistical clusters are not automatically
  humanistic themes.
- The application returns the scholar to representative excerpts, distributions, and
  qualitative review rather than presenting topic labels as automatic conclusions.
- Preprocessing counts expose original tokens, post-stopword tokens, final lemmas,
  unique lemmas, document count, and per-document details.
- The export surface offers a complete ZIP, PDF report, result CSV files, preprocessing
  summary, and environment metadata.

## Gaps Delta Must Surpass

- Parameters precede corpus documentation and corpus-health review.
- The public example is not a one-action in-application workflow.
- A raw traceback exposes implementation details and does not translate the precise
  pruning failure into a field-level correction.
- Mobile content begins with clipped introductory text beneath the fixed Streamlit
  chrome, and closed sidebar controls remain represented in the accessibility tree.
- The mobile result tab strip hides later tabs and can leave the active tab outside the
  first visible group.
- The expanded pasted text remains above results and consumes substantial vertical
  space after analysis.
- Result files do not by themselves form Delta's required FAIR evidence package:
  resolved configuration, input and normalized hashes, rights states, failed cells,
  limitations, checksums, and rerun guidance remain separate Delta requirements.
- Visual richness is not sufficient evidence. Delta requires a table and CSV generated
  from the same validated object for every chart.

## Resulting Decision

Lemmata is the minimum sibling-product usability baseline. Delta preserves its
directness, interpretation discipline, preprocessing transparency, and export
discoverability. Delta must be measurably better in corpus-first sequencing, guided
metadata, rights documentation, actionable errors, mobile accessibility, chart/data
equivalence, method boundaries, and FAIR rerun evidence.

The binding UX consequences and acceptance gates are recorded in
`docs/development/p004-metadata-ux-decisions.md`.

## Limitations

- The live service can change after this date.
- The audit did not upload real research data or assess analysis quality on a natural
  literary corpus.
- The synthetic result validates the interaction and evidence surfaces only; it is not
  a scientific model-quality benchmark.
- VoiceOver and cross-browser manual testing remain separate Delta acceptance work.
