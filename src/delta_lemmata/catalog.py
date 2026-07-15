"""Central English UI catalog.

Delta currently ships one locale. Keeping every user-facing string here makes
copy audits deterministic and leaves a clean boundary for later localization.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

DEFAULT_LOCALE = "en"

_ENGLISH_STRINGS: dict[str, str] = {
    "meta.page_title": "Delta · Stylometry workbench",
    "brand.mark": "Δ",
    "brand.name": "Delta",
    "brand.subtitle": "A Lemmata stylometry workbench",
    "header.stage.upload": "Secure intake",
    "header.stage.corpus": "Corpus setup",
    "header.stage.parameters": "Guided parameters",
    "header.version": "Version {version}",
    "header.build": "Build {build_id}",
    "sidebar.progress": "Experiment map · 2 of 4",
    "sidebar.progress_accessible": "Experiment map progress: step 2 of 4",
    "sidebar.step.purpose": "Purpose",
    "sidebar.step.corpus": "Corpus",
    "sidebar.step.parameters": "Parameters",
    "sidebar.step.evidence": "Evidence",
    "sidebar.state.active": "Active",
    "sidebar.state.complete": "Complete",
    "sidebar.state.validated": "Validated",
    "sidebar.state.locked": "Locked",
    "sidebar.badge": "Corpus setup",
    "sidebar.badge.parameters": "Guided analysis",
    "sidebar.guide_title": "Start here",
    "sidebar.guide_body": (
        "Delta checks and documents your corpus before any analysis settings appear."
    ),
    "sidebar.guide.question": "Choose a research question",
    "sidebar.guide.corpus": "Upload and document the texts",
    "sidebar.guide.parameters": "Review parameters before analysis",
    "sidebar.parameters_title": "Why parameters come later",
    "sidebar.parameters_body": (
        "Stylometric settings depend on the size and structure of your corpus. "
        "Delta checks the texts first, then explains the available choices."
    ),
    "build.title": "Technical status",
    "build.readiness_label": "Readiness",
    "build.readiness_value": "Secure intake available",
    "build.engine_label": "Analysis engine",
    "build.engine_value": "Connected · R stylo",
    "setup.eyebrow": "COMPARE HOW TEXTS ARE WRITTEN",
    "setup.title": "Discover patterns in writing style.",
    "setup.intro": (
        "Stylometry compares measurable patterns in language use across texts, such as "
        "how often common words recur. Delta compares texts, groups, and change over time "
        "without writing R or Python."
    ),
    "setup.corpus_scope": (
        "Every comparison is relative to your corpus. Delta documents the texts before "
        "method settings appear."
    ),
    "setup.trace.kicker": "WHAT STYLOMETRY NOTICES",
    "setup.trace.title": "Small choices become visible when they repeat.",
    "setup.trace.body": ("Delta compares patterns across documented texts, not isolated words."),
    "setup.trace.caption": "Illustration only · no corpus analysed",
    "setup.trace.row_a_label": "Illustrative text A",
    "setup.trace.row_a": "the and of but with",
    "setup.trace.row_b_label": "Illustrative text B",
    "setup.trace.row_b": "and the with yet of",
    "setup.trace.legend": "Signals that can be compared",
    "setup.trace.common_words": "Common words",
    "setup.trace.punctuation": "Punctuation",
    "setup.trace.rhythm": "Sentence rhythm",
    "setup.trace.vocabulary": "Vocabulary",
    "setup.method_label": "How stylometry works",
    "setup.method.observe.title": "Observe",
    "setup.method.observe.body": "Recurring language features",
    "setup.method.compare.title": "Compare",
    "setup.method.compare.body": "Across documented texts",
    "setup.method.interpret.title": "Interpret",
    "setup.method.interpret.body": "With context and limits",
    "setup.method.caption": "Conceptual workflow · not an analysis result",
    "parameters.orientation_title": "How parameters will work",
    "parameters.orientation_body": (
        "Usable settings depend on text length, feature count, and corpus structure. "
        "Delta checks the corpus before exposing them."
    ),
    "parameters.guided.title": "Guided mode",
    "parameters.guided.body": (
        "Tests 100, 300, 500, and 1,000 MFW. Its fixed reference is 500 MFW, "
        "0% culling, whole text, and Classic Delta; this is not a 'best setting'."
    ),
    "parameters.research.title": "Research mode",
    "parameters.research.body": (
        "Offers bounded MFW, culling, segmentation, and distance choices, then "
        "compares up to 24 documented combinations instead of hiding sensitivity."
    ),
    "parameters.status.title": "Current status",
    "parameters.status.body": (
        "Guided Mode becomes available after corpus documentation and computational "
        "preflight. Research Mode remains locked in this public alpha."
    ),
    "parameters.eyebrow": "PARAMETERS · GUIDED MODE",
    "parameters.title": "Review what Delta will calculate",
    "parameters.body": (
        "Guided Mode runs four pre-registered comparisons on the same documented corpus. "
        "Review the complete grid and its limits before starting the analysis."
    ),
    "parameters.mode.label": "Parameter mode",
    "parameters.research_locked": "Research Mode is not available in this public alpha.",
    "parameters.research_locked_body": (
        "Its larger parameter grid will open only after resource limits, result checks, "
        "and owner acceptance are complete. Guided Mode is the bounded runnable workflow."
    ),
    "parameters.back_prepare": "Back to corpus preparation",
    "parameters.guided_ready": (
        "The exact Guided Mode grid is resolved and ready for your confirmation."
    ),
    "parameters.metric.cells": "Comparisons",
    "parameters.metric.reference": "Display reference",
    "parameters.metric.culling": "Culling",
    "parameters.metric.unit": "Analysis unit",
    "parameters.unit.whole": "Whole text",
    "parameters.table.mfw": "Most frequent words",
    "parameters.table.culling": "Culling",
    "parameters.table.distance": "Distance measure",
    "parameters.table.role": "Evidence role",
    "parameters.table.label": "Guided parameter comparison grid",
    "parameters.table.reference": "Display reference",
    "parameters.table.sensitivity": "Sensitivity check",
    "parameters.distance.classic_delta": "Classic Delta",
    "parameters.grid_caption": (
        "Every row is retained as evidence. The 500-MFW row is a fixed display reference, "
        "not a claim that it is the best result."
    ),
    "parameters.learn.title": "Understand these settings",
    "parameters.learn.mfw.title": "Most frequent words (MFW)",
    "parameters.learn.mfw.body": (
        "MFW is the number of common word features compared across the corpus. A larger "
        "number includes more vocabulary; it is not automatically more accurate. Delta "
        "tests 100, 300, 500, and 1,000 so sensitivity stays visible."
    ),
    "parameters.learn.culling.title": "Culling",
    "parameters.learn.culling.body": (
        "Culling can require a word to occur in a minimum share of texts before comparison. "
        "The alpha uses 0%, so it adds no cross-document presence threshold."
    ),
    "parameters.learn.delta.title": "Classic Delta",
    "parameters.learn.delta.body": (
        "Classic Delta standardizes word frequencies and measures the average distance "
        "between texts. A smaller distance means relatively greater stylistic proximity "
        "inside this corpus; it does not prove authorship."
    ),
    "parameters.learn.reference.title": "Why 500 MFW is the display reference",
    "parameters.learn.reference.body": (
        "Delta uses 500 MFW as a fixed, reproducible visual anchor. It does not select the "
        "most attractive result. The other three comparisons remain equally visible."
    ),
    "parameters.interpretive_boundary": (
        "These comparisons describe relative stylistic proximity within this corpus. They "
        "do not prove authorship, authenticity, influence, intention, chronology, or causation."
    ),
    "parameters.download_config": "Download resolved parameter record",
    "parameters.confirm": "I reviewed the four comparisons and their interpretation limits.",
    "parameters.confirm_help": (
        "Confirmation records that you saw the complete grid before calculation; it is not "
        "an endorsement of any future result."
    ),
    "parameters.run": "Run the four comparisons",
    "parameters.run_error": (
        "Delta could not complete this bounded analysis safely. No partial result is presented."
    ),
    "parameters.configuration_error": (
        "The resolved parameter record no longer matches this documented corpus. Return to "
        "preparation and try again."
    ),
    "parameters.run_status_unknown": "Analysis status is unavailable.",
    "parameters.evidence_next": (
        "The calculation finished. Evidence review and result visualizations are the next step."
    ),
    "purpose.guidance": "Understand this research path",
    "purpose.label": "What do you want to investigate?",
    "purpose.badge": "Selected purpose",
    "purpose.question_label": "Question",
    "purpose.use_label": "Why use it",
    "purpose.boundary_label": "Do not conclude",
    "purpose.text_proximity.label": "Compare Texts",
    "purpose.text_proximity.question": (
        "Which texts show more similar recurring language patterns within this corpus?"
    ),
    "purpose.text_proximity.use": (
        "Explore relative similarity or place one focal text beside documented comparison texts."
    ),
    "purpose.text_proximity.boundary": (
        "Nearer does not mean the same author, influence, intention, or authenticity."
    ),
    "purpose.group_comparison.label": "Compare Groups",
    "purpose.group_comparison.question": (
        "Do documented groups show different recurring stylistic patterns?"
    ),
    "purpose.group_comparison.use": (
        "Compare works grouped by author, genre, period, audience, or another recorded category."
    ),
    "purpose.group_comparison.boundary": (
        "Observed separation may reflect corpus balance, genre, period, source, or edition effects."
    ),
    "purpose.style_over_time.label": "Trace Style Over Time",
    "purpose.style_over_time.question": (
        "How does one writer's stylistic position vary across dated independent works?"
    ),
    "purpose.style_over_time.use": (
        "Explore a documented sequence of independently dated works while keeping "
        "edition, genre, audience, and source differences visible."
    ),
    "purpose.style_over_time.boundary": (
        "Chronology alone does not establish ageing, maturation, a turning point, or causation."
    ),
    "mode.eyebrow": "ANALYSIS MODE",
    "mode.title": "Choose the level of control",
    "mode.label": "Analysis mode",
    "mode.guided.label": "Guided",
    "mode.guided.body": (
        "Will run a constrained parameter sweep with method explanations and visible defaults."
    ),
    "mode.research.label": "Research",
    "mode.research.body": (
        "Will run a documented parameter grid with explicit resource limits "
        "and complete cell reporting."
    ),
    "mode.status": (
        "Guided parameters open after corpus documentation and computational preflight."
    ),
    "corpus.eyebrow": "CORPUS · UPLOAD",
    "corpus.title": "Upload the research corpus",
    "corpus.body": ("Add UTF-8, NFC TXT files or one strict ZIP. Metadata CSV is optional."),
    "corpus.available": "Secure intake available",
    "corpus.mode.label": "Corpus input format",
    "corpus.mode.text": "Individual TXT files",
    "corpus.mode.archive": "One ZIP archive",
    "corpus.text_uploader": "Corpus texts (.txt)",
    "corpus.text_uploader_help": (
        "Add one or more plain-text files. Each file is validated independently "
        "and again as part of the complete batch."
    ),
    "corpus.archive_uploader": "Corpus archive (.zip)",
    "corpus.archive_uploader_help": (
        "Add one standard ZIP containing TXT files only. Nested archives, links, "
        "ambiguous paths, extra fields, encryption, and ZIP64 are rejected."
    ),
    "corpus.metadata_uploader": "Optional metadata table (.csv)",
    "corpus.metadata_uploader_help": (
        "This stage checks CSV structure and unsafe cells only. Column meaning, corpus "
        "matching, dates, groups, and rights are reviewed in the next stage."
    ),
    "corpus.limits": (
        "Intake limits · {upload_mib} MiB per upload · {batch_files} files per batch "
        "· {archive_members} ZIP members · {archive_mib} MiB expanded ZIP content"
    ),
    "corpus.empty": "No files submitted. Choose a corpus format and add files when ready.",
    "corpus.metadata_only": (
        "Metadata structure passed intake checks. Add a corpus before this stage can be ready."
    ),
    "corpus.success": (
        "Intake checks passed · Uploads: {uploads} · Corpus texts: {units} · Input bytes: {bytes}"
    ),
    "corpus.metadata_valid": "File safety checked · metadata meaning not reviewed",
    "corpus.metadata_advanced": "Advanced · import a versioned metadata CSV",
    "corpus.role.text": "Corpus text",
    "corpus.role.archive": "Corpus archive",
    "corpus.role.member": "Corpus text from ZIP",
    "corpus.role.csv": "Metadata table",
    "corpus.receipt.text": "Lines: {lines} · Tokens: {tokens}",
    "corpus.receipt.archive": "TXT members: {members} · Expanded bytes: {expanded}",
    "corpus.receipt.member": "Lines: {lines} · Tokens: {tokens} · SHA-256 {digest}",
    "corpus.receipt.csv": "Rows: {rows} · Columns: {columns}",
    "corpus.archive_catalog": "Validated ZIP member catalog",
    "corpus.error.title": "The submission was rejected and cleared before intake.",
    "corpus.error.empty": "The selected file contains no bytes.",
    "corpus.error.limit": (
        "A versioned size, count, line, token, path, or compression limit was exceeded."
    ),
    "corpus.error.role": (
        "The selected role, extension, media type, display label, and detected content "
        "do not agree."
    ),
    "corpus.error.text": (
        "A text is empty, not valid UTF-8 and NFC, contains unsafe controls, or appears "
        "to be markup rather than plain text."
    ),
    "corpus.error.csv": (
        "The metadata table is malformed or contains a formula, markup, newline, or "
        "path-like cell that is unsafe to retain or export."
    ),
    "corpus.error.archive": (
        "The ZIP is malformed or uses an unsupported or unsafe member, path, flag, "
        "compression feature, or nested archive."
    ),
    "corpus.error.internal": (
        "Delta could not complete the intake operation safely. No analysis state was created."
    ),
    "corpus.error.reference": "Rejection reference: {code}",
    "corpus.materialization_error": (
        "Delta could not create a private, temporary corpus workspace. "
        "The documentation stage was not opened and no analysis ran."
    ),
    "corpus.continue_button": "Continue to describe the corpus",
    "corpus.continue_button_help": (
        "Delta will move validated corpus text into a private, temporary server workspace, "
        "retain only a content-free receipt in this browser session, and clear the upload widgets."
    ),
    "corpus.zip_ready": (
        "Each validated TXT member will open as a separate work in corpus documentation."
    ),
    "flow.progress_accessible": "Experiment progress: corpus documentation is active",
    "flow.stage.upload": "Upload",
    "flow.stage.describe": "Describe",
    "flow.stage.review": "Review",
    "flow.stage.prepare": "Prepare",
    "flow.stage.parameters": "Parameter review",
    "flow.locked": "Locked",
    "describe.eyebrow": "CORPUS · DESCRIBE",
    "describe.title": "Describe what each text represents",
    "describe.body": (
        "Confirm work, chronology, edition, source, and rights information. Suggested "
        "titles and identifiers remain editable or visibly generated; Delta makes no "
        "automatic scholarly or legal determination."
    ),
    "describe.back": "Start again with different files",
    "describe.import_title": "Advanced metadata import",
    "describe.import_ready": (
        "The versioned CSV was parsed and domain-checked against the validated files."
    ),
    "describe.import_blocked": (
        "The CSV passed file-safety checks but cannot yet produce a complete inventory."
    ),
    "describe.import_review": "Review imported metadata",
    "describe.guided_title": "Guided metadata editor",
    "describe.guided_body": (
        "Complete the visible fields for every TXT. Unknown remains an explicit value; "
        "Delta never invents a date, source, permission, or classification."
    ),
    "describe.work_heading": "{index}. {file_label}",
    "describe.file_metric": "{lines} lines · {tokens} tokens · SHA-256 {digest}",
    "describe.title_original": "Original work title",
    "describe.author_name": "Primary author name",
    "describe.author_kind": "Author type",
    "describe.language": "Text language (BCP 47)",
    "describe.publication_mode": "First-publication certainty",
    "describe.publication_start": "First-publication year",
    "describe.publication_end": "End year",
    "describe.edition_label": "Analyzed edition label",
    "describe.edition_mode": "Analyzed-edition date certainty",
    "describe.edition_start": "Analyzed-edition year",
    "describe.edition_end": "Edition end year",
    "describe.genre": "Genre",
    "describe.audience": "Audience",
    "describe.adaptation": "Adaptation status",
    "describe.collection": "Collection status",
    "describe.group_label": "Group label",
    "describe.source_type": "Source type",
    "describe.source_title": "Source title",
    "describe.source_url": "Source URL",
    "describe.source_citation": "Bibliographic citation",
    "describe.source_accessed": "Date accessed",
    "describe.rights_heading": "Rights questionnaire",
    "describe.rights_help": (
        "Choose the documented state for this analyzed text. Delta records your answer "
        "and keeps unresolved actions closed; it does not issue a legal opinion."
    ),
    "describe.rights_status": "Documented rights state",
    "describe.rights.unknown": "Unknown · keep every action closed",
    "describe.rights.permission_required": "Permission required · unresolved",
    "describe.rights.analysis_only": (
        "Analysis only · permit upload and analysis, prohibit text export"
    ),
    "describe.rights.verified_open": (
        "Researcher-documented open · requires URL, license, and jurisdiction"
    ),
    "describe.rights.excluded": "Exclude · prohibit every action",
    "describe.rights_license": "License or public-domain statement",
    "describe.rights_jurisdiction": "Jurisdiction",
    "describe.rights_notes": "Rights notes",
    "describe.build_review": "Build corpus review",
    "describe.build_error": "Review these fields before continuing: {fields}",
    "describe.correction_guided": (
        "The selected work is open below. Review the highlighted {field_path} field."
    ),
    "describe.correction_here": "Correction target: {field_path}",
    "describe.correction_csv": (
        "This inventory came from CSV. Correct {field_path} for work_id {work_id} in "
        "the source CSV, then start again with the corrected file."
    ),
    "describe.correction_csv_boundary": (
        "Delta no longer retains the uploaded CSV bytes, so it cannot silently rewrite "
        "or prefill that source file."
    ),
    "describe.year_error": "{field} must be a year from 1 to 9999.",
    "describe.csv_issue": "Row {row} · {field} · {code}",
    "review.eyebrow": "CORPUS · REVIEW",
    "review.title": "Review the documented corpus",
    "review.body": (
        "Inspect blockers, chronology, rights, and the exact exportable inventory before "
        "any parameter configuration is allowed."
    ),
    "review.ready": (
        "Corpus documentation has no blockers. Confirm this inventory to continue to "
        "computational preflight and parameter review."
    ),
    "review.blocked": (
        "Corpus documentation contains blockers. Return to Describe and correct them; "
        "no analysis state has been created."
    ),
    "review.edit": "Edit metadata",
    "review.start_over": "Start over",
    "review.metric.works": "Independent works",
    "review.metric.chronology": "Chronology points",
    "review.metric.blockers": "Blockers",
    "review.metric.warnings": "Warnings",
    "review.metric.rights": "Rights restrictions",
    "review.composition_title": "Corpus composition",
    "review.composition_body": (
        "Counts describe the metadata documented for this inventory. They do not measure "
        "style, representativeness, balance, or scholarly quality."
    ),
    "review.composition_table": "Corpus composition data",
    "review.completeness_title": "Metadata completeness matrix",
    "review.completeness_body": (
        "Completeness states describe documentation, not research quality, scientific "
        "validity, or permission to analyze or redistribute a text."
    ),
    "review.completeness_fields": "Review fields",
    "review.completeness_no_field": "No correction field",
    "review.timeline_title": "Work timeline",
    "review.timeline_body": (
        "One entry per independent work. This is corpus chronology, not a stylistic trajectory."
    ),
    "review.timeline_selector": "Select a documented work on the chronology",
    "review.timeline_table": "Work timeline data",
    "review.timeline_unknown": "Unknown date",
    "review.timeline_unresolved": "Unresolved",
    "review.timeline_conflict": "Conflict",
    "review.corrections_title": "Correction shortcuts",
    "review.corrections_body": (
        "Choose a documented warning, missing field, or conflict to return to its exact "
        "work and metadata section."
    ),
    "review.corrections_label": "Metadata field to correct",
    "review.corrections_edit": "Edit selected field",
    "review.rights_title": "Rights action matrix",
    "review.rights_body": (
        "These states reproduce the researcher's documentation; they are not legal approval."
    ),
    "review.issues_title": "Actionable corpus checks",
    "review.issue_why": "Why it matters",
    "review.issue_fix": "How to correct it",
    "review.no_issues": "No corpus-documentation issues were reported.",
    "review.confirmation_title": "Final corpus confirmation",
    "review.confirmation_body": (
        "One confirmation covers this exact inventory hash. Any rebuilt metadata or rights "
        "record requires confirmation again."
    ),
    "review.confirmation_checkbox": (
        "I reviewed the file-to-work mappings and the documented rights records."
    ),
    "review.confirmation_help": (
        "This records review of documentation only. It is not legal approval or a claim of "
        "scientific sufficiency."
    ),
    "review.confirmation_recorded": "Confirmation recorded for this inventory.",
    "review.confirmation_required": (
        "Final corpus confirmation is still required before a future parameter stage can open."
    ),
    "review.confirmation_blocked": (
        "Resolve every corpus blocker before final confirmation can be recorded."
    ),
    "review.downloads_title": "Download the documentation package",
    "review.download_metadata": "Download metadata CSV",
    "review.download_inventory": "Download canonical inventory JSON",
    "review.download_validation": "Download validation report JSON",
    "review.download_composition": "Download composition CSV",
    "review.download_completeness": "Download completeness CSV",
    "review.export_unavailable": (
        "The metadata CSV cannot be generated safely from the current inventory."
    ),
    "review.review_export_unavailable": (
        "The review CSV files cannot be generated safely from the current projection."
    ),
    "review.projection_unavailable": (
        "This review no longer matches the documented inventory. Return to Describe and "
        "rebuild it before continuing."
    ),
    "review.analysis_locked": (
        "No stylometric analysis has run. Parameters and the analysis engine remain locked."
    ),
    "review.analysis_locked_confirmation": (
        "No stylometric analysis has run. Final corpus confirmation, parameters, and the "
        "analysis engine remain locked."
    ),
    "review.continue_prepare": "Continue to corpus preparation",
    "review.temporary_corpus_missing": (
        "The temporary corpus is no longer attached to this browser session. Start again "
        "with the same files; the documentation package can still be downloaded first."
    ),
    "prepare.eyebrow": "CORPUS · PREPARE",
    "prepare.title": "Prepare and check the corpus",
    "prepare.body": (
        "Tell Delta how each uploaded text should be treated. Delta then applies one visible, "
        "deterministic text-preparation profile and checks whether the corpus can support the "
        "next analysis step."
    ),
    "prepare.profile_summary": (
        "Fixed alpha profile: Unicode NFC, lowercase surface words, accents preserved, common "
        "words retained, punctuation and numbers removed, no lemmatization or stemming, and no "
        "automatic removal of titles, prefaces, notes, or other paratext."
    ),
    "prepare.decisions_title": "Document the analysis role of each text",
    "prepare.decisions_body": (
        "These choices do not change the uploaded file. They record how Delta may use it and "
        "which editorial risks must remain visible when results are interpreted."
    ),
    "prepare.work_label": "{index}. {title} · {file}",
    "prepare.role.label": "Analysis role",
    "prepare.role.help": (
        "Known texts define the comparison space. An unknown or focal text is placed into that "
        "space afterwards; its nearest neighbour is not automatically its author."
    ),
    "prepare.role.known.label": "Known reference text",
    "prepare.role.known.body": (
        "Use this when the documented work identity is accepted for this experiment. At least "
        "two independent known works are required."
    ),
    "prepare.role.unknown.label": "Unknown or focal text",
    "prepare.role.unknown.body": (
        "Use this for a text you want to position against known references. Delta reports "
        "relative proximity and does not prove authorship or authenticity."
    ),
    "prepare.ocr.label": "OCR status",
    "prepare.ocr.help": (
        "OCR means text produced by optical character recognition from page images. Recognition "
        "errors can imitate stylistic differences, so record what you actually know."
    ),
    "prepare.ocr.not_ocr": "Not produced by OCR",
    "prepare.ocr.reviewed": "OCR reviewed against the source",
    "prepare.ocr.unreviewed": "OCR not fully reviewed",
    "prepare.ocr.unknown": "OCR status unknown",
    "prepare.paratext.label": "Paratext status",
    "prepare.paratext.help": (
        "Paratext includes titles, contents pages, prefaces, editorial notes, page headers, and "
        "similar material outside the main literary text."
    ),
    "prepare.paratext.absent": "No paratext present",
    "prepare.paratext.retained": "Paratext retained in the file",
    "prepare.paratext.manually_removed_before_upload": "Paratext removed before upload",
    "prepare.paratext.unknown": "Paratext status unknown",
    "prepare.note.label": "Optional pre-upload curation note",
    "prepare.note.help": (
        "Briefly record manual changes already made to this file. Do not paste corpus text here."
    ),
    "prepare.unit_fixed": (
        "Analysis unit: one independent work. Segment and excerpt analysis is not admitted in "
        "this public-alpha workflow."
    ),
    "prepare.run_check": "Prepare texts and check corpus health",
    "prepare.back_review": "Back to corpus review",
    "prepare.start_over": "Start again with revised files",
    "prepare.confirmation_missing": (
        "Corpus documentation changed or is not confirmed. Return to Review and confirm the "
        "current inventory before preparation."
    ),
    "prepare.error": (
        "Delta could not prepare this temporary corpus safely. No stylometric result was created."
    ),
    "prepare.annotation_error": (
        "Review the analysis roles, OCR states, paratext states, and curation notes "
        "before retrying."
    ),
    "prepare.ready": (
        "Computational preflight passed. The prepared corpus can continue to bounded "
        "parameter review."
    ),
    "prepare.blocked": (
        "Computational preflight found one or more blockers. No analysis request was created."
    ),
    "prepare.preflight_scope": (
        "This is a computational preflight only. It does not establish corpus validity, "
        "authorship, "
        "causation, representativeness, or the soundness of a later interpretation."
    ),
    "prepare.parameters_next": (
        "The corpus is ready. Parameter review is the next step; no stylometric analysis "
        "has run yet."
    ),
    "prepare.continue_parameters": "Continue to parameter review",
    "prepare.metric.works": "Independent works",
    "prepare.metric.known": "Known references",
    "prepare.metric.features": "Candidate features",
    "prepare.metric.blockers": "Blockers",
    "prepare.metric.warnings": "Strong warnings",
    "prepare.length_title": "Compare usable text lengths",
    "prepare.length_body": (
        "Token counts are measured after the fixed preparation profile. Large differences can "
        "dominate a comparison and should be interpreted or corrected before analysis."
    ),
    "prepare.table.work": "Work",
    "prepare.table.work_id": "Work ID",
    "prepare.table.tokens": "Prepared tokens",
    "prepare.table.unique": "Unique surface words",
    "prepare.panel.boundary_label": "What this does not establish",
    "prepare.length_boundary": (
        "Similar text lengths do not make the works comparable or make a later result valid."
    ),
    "prepare.download_work_csv": "Download work-preparation CSV",
    "prepare.transform_title": "See what the fixed profile changed",
    "prepare.transform_body": (
        "These counts document how the same preparation profile handled each source. Separator "
        "counts include spaces, punctuation, numbers, symbols, and other token boundaries; they "
        "are not error counts."
    ),
    "prepare.transform.lowercase": "Characters changed to lowercase",
    "prepare.transform.separators": "Source separators",
    "prepare.transform.newlines": "Newline replacements",
    "prepare.transform.raw_bytes": "Raw bytes",
    "prepare.transform.prepared_bytes": "Prepared bytes",
    "prepare.transform.bom": "BOM removed",
    "prepare.transform_boundary": (
        "Transformation counts do not measure textual quality, editorial accuracy, or the amount "
        "of stylistically meaningful change."
    ),
    "prepare.confound_title": "Review factors that may travel with style",
    "prepare.confound_body": (
        "A confound is a documented difference that may vary alongside the factor you want to "
        "study. The matrix keeps those differences visible before calculation."
    ),
    "prepare.confound.edition": "Edition",
    "prepare.confound.genre": "Genre",
    "prepare.confound.audience": "Audience",
    "prepare.confound.source": "Source type",
    "prepare.confound.adaptation": "Adaptation",
    "prepare.confound.collection": "Collection",
    "prepare.confound.chronology": "Chronology",
    "prepare.confound.chronology.exact": "{year}",
    "prepare.confound.chronology.approximate": "About {year}",
    "prepare.confound.chronology.range": "{start}-{end}",
    "prepare.confound.chronology.unknown": "Unknown",
    "prepare.confound.ocr": "OCR",
    "prepare.confound.paratext": "Paratext",
    "prepare.confound.curation": "Curation note",
    "prepare.confound.disclosed": "Disclosed",
    "prepare.confound.not_disclosed": "Not disclosed",
    "prepare.confound_boundary": (
        "The matrix does not prove that a factor caused a pattern, remove that factor, or "
        "statistically control it."
    ),
    "prepare.download_confound_csv": "Download confound-matrix CSV",
    "prepare.overlap_title": "Check independence and repeated material",
    "prepare.overlap_body": (
        "Delta screens prepared texts for exact copies, near-duplicates, and long shared runs. "
        "Only pairs that cross a declared Delta v0.1 threshold are flagged."
    ),
    "prepare.overlap.matrix_title": "Threshold-screening matrix",
    "prepare.overlap.pairs_title": "Flagged pairs",
    "prepare.overlap.left": "First work",
    "prepare.overlap.right": "Second work",
    "prepare.overlap.check": "Check",
    "prepare.overlap.observed": "Observed",
    "prepare.overlap.same_work": "Same work",
    "prepare.overlap.not_flagged": "Not flagged",
    "prepare.overlap.none": "No pair crossed the declared overlap-screening thresholds.",
    "prepare.overlap.code.exact_duplicate": "Exact duplicate",
    "prepare.overlap.code.near_duplicate": "Near duplicate",
    "prepare.overlap.code.shared_passage": "Shared passage",
    "prepare.overlap.hash_match": "Prepared hashes match",
    "prepare.overlap.tokens": "{count} shared tokens",
    "prepare.overlap.ratio": "{ratio:.2%}",
    "prepare.overlap.no_measure": "Threshold crossed",
    "prepare.overlap_boundary": (
        "A pair that is not flagged may still share shorter material or other dependencies. A "
        "flag also does not identify its editorial or historical cause."
    ),
    "prepare.mfw_title": "Which MFW settings can this corpus support?",
    "prepare.mfw_body": (
        "MFW means most frequent words. A setting is available only when the known reference texts "
        "jointly provide at least that many usable features. Higher is not automatically better."
    ),
    "prepare.mfw.metric": "{mfw} MFW",
    "prepare.mfw.available": "Available",
    "prepare.mfw.unavailable": "Unavailable",
    "prepare.mfw.features": "{count} features found",
    "prepare.mfw.requested": "Requested MFW",
    "prepare.mfw.available_features": "Available features",
    "prepare.mfw.status": "Status",
    "prepare.mfw_boundary": (
        "Feature capacity does not identify a best MFW setting or show that a supported setting "
        "will produce a stable or meaningful result."
    ),
    "prepare.download_capacity_csv": "Download feature-capacity CSV",
    "prepare.findings_title": "What Delta found",
    "prepare.findings_body": (
        "Blockers stop the run. Strong warnings permit a later run but must remain visible in "
        "interpretation. Notes document preparation without claiming a problem."
    ),
    "prepare.finding.action_label": "What to do",
    "prepare.finding.observed_count": "Observed {value}",
    "prepare.finding.threshold_count": "Reference threshold {value}",
    "prepare.finding.observed_ratio": "Observed ratio {value:.2f}",
    "prepare.finding.threshold_ratio": "Reference ratio {value:.2f}",
    "prepare.downloads_title": "Download the preparation evidence",
    "prepare.download_health": "Download corpus-health report",
    "prepare.download_manifest": "Download preparation manifest",
    "prepare.download_config": "Download preparation settings",
    "prepare.download_findings_csv": "Download health-findings CSV",
    "prepare.download_receipt": "Download READY receipt",
    "prepare.projection_error": (
        "Delta could not bind the preparation evidence to this corpus. No review projection or "
        "analysis request was created."
    ),
    "prepare.finding.empty_prepared_work.title": "A text has no usable words",
    "prepare.finding.empty_prepared_work.body": (
        "After the declared preparation rules, this work produced zero surface-word tokens."
    ),
    "prepare.finding.empty_prepared_work.action": (
        "Inspect the source file, encoding, and whether it contains literary text rather "
        "than only markup or numbers."
    ),
    "prepare.finding.too_few_known_works.title": "Too few known reference works",
    "prepare.finding.too_few_known_works.body": (
        "Delta needs at least two independent known works to define feature statistics "
        "and distances."
    ),
    "prepare.finding.too_few_known_works.action": (
        "Mark at least two documented independent works as known references, or add "
        "suitable reference texts."
    ),
    "prepare.finding.non_independent_unit.title": "A segment or excerpt is not runnable here",
    "prepare.finding.non_independent_unit.body": (
        "This alpha workflow compares complete independent works and blocks mixed analysis units."
    ),
    "prepare.finding.non_independent_unit.action": (
        "Upload comparable complete works; use a later documented segmentation workflow "
        "for excerpts or chapters."
    ),
    "prepare.finding.duplicate_independence_unit.title": "One work is represented more than once",
    "prepare.finding.duplicate_independence_unit.body": (
        "Repeated segments or editions of one work would be counted as if they were "
        "independent evidence."
    ),
    "prepare.finding.duplicate_independence_unit.action": (
        "Keep one documented analysis copy per independent work or redesign the corpus "
        "as a declared segment study."
    ),
    "prepare.finding.exact_duplicate.title": "Two prepared texts are identical",
    "prepare.finding.exact_duplicate.body": (
        "Exact copies add no independent stylistic evidence and can distort the geometry "
        "of the corpus."
    ),
    "prepare.finding.exact_duplicate.action": (
        "Remove the duplicate or verify whether the files represent the same edition "
        "under different names."
    ),
    "prepare.finding.no_runnable_features.title": "The corpus has too few shared usable features",
    "prepare.finding.no_runnable_features.body": (
        "The known texts do not provide the minimum feature inventory required by the "
        "analysis engine."
    ),
    "prepare.finding.no_runnable_features.action": (
        "Use longer language-comparable texts and review any exclusions before trying again."
    ),
    "prepare.finding.too_many_documents.title": "The corpus exceeds the alpha document limit",
    "prepare.finding.too_many_documents.body": (
        "The bounded analysis worker accepts at most 50 documents in one run."
    ),
    "prepare.finding.too_many_documents.action": (
        "Reduce the corpus to a documented comparison set or divide the research question "
        "into separate runs."
    ),
    "prepare.finding.too_few_independent_works.title": (
        "The corpus is small for a robust comparison"
    ),
    "prepare.finding.too_few_independent_works.body": (
        "Fewer than six independent works makes corpus-specific patterns and outliers "
        "harder to distinguish."
    ),
    "prepare.finding.too_few_independent_works.action": (
        "Add comparable independent works when possible and describe a smaller run as exploratory."
    ),
    "prepare.finding.too_few_chronology_points.title": "The timeline has too few documented points",
    "prepare.finding.too_few_chronology_points.body": (
        "A style-over-time question needs at least three distinct documented chronology "
        "points to show a trajectory."
    ),
    "prepare.finding.too_few_chronology_points.action": (
        "Add dated works from another period or narrow the claim to a comparison rather "
        "than a developmental trend."
    ),
    "prepare.finding.near_duplicate.title": "Two texts are near-duplicates",
    "prepare.finding.near_duplicate.body": (
        "Large repeated portions may indicate the same edition, a reprint, or overlapping "
        "source material."
    ),
    "prepare.finding.near_duplicate.action": (
        "Compare the editions and remove or explicitly justify overlapping material before "
        "interpreting distance."
    ),
    "prepare.finding.shared_passage.title": "A long passage is shared across works",
    "prepare.finding.shared_passage.body": (
        "Repeated editorial matter or embedded source text can create similarity unrelated "
        "to authorial style."
    ),
    "prepare.finding.shared_passage.action": (
        "Inspect the files for repeated prefaces, contents, quotations, collection headers, "
        "or duplicated chapters."
    ),
    "prepare.finding.length_imbalance.title": "Text lengths are strongly imbalanced",
    "prepare.finding.length_imbalance.body": (
        "The longest independent work has at least four times as many prepared tokens as "
        "the shortest."
    ),
    "prepare.finding.length_imbalance.action": (
        "Prefer comparably sized works or use a later, explicitly validated segmentation "
        "design; do not trim silently."
    ),
    "prepare.finding.group_imbalance.title": "Documented groups are imbalanced",
    "prepare.finding.group_imbalance.body": (
        "One group contains at least three times as many independent works as another."
    ),
    "prepare.finding.group_imbalance.action": (
        "Add comparable works to the smaller group or treat group patterns as exploratory "
        "and report the imbalance."
    ),
    "prepare.finding.ocr_confound.title": "OCR histories may not be comparable",
    "prepare.finding.ocr_confound.body": (
        "The texts have different or uncertain optical character recognition and review states. "
        "Recognition errors can alter the words Delta counts, but this warning does not prove "
        "that OCR caused a later pattern."
    ),
    "prepare.finding.ocr_confound.action": (
        "Check each digital text against its source, document the OCR and review process, and "
        "make the states as comparable as the sources allow."
    ),
    "prepare.finding.paratext_confound.title": "Paratext treatment differs across texts",
    "prepare.finding.paratext_confound.body": (
        "Prefaces, contents, notes, or other surrounding material were retained, removed, or "
        "left uncertain under different policies. This warning does not prove that paratext "
        "caused a later pattern."
    ),
    "prepare.finding.paratext_confound.action": (
        "Review the files, apply one documented paratext policy where appropriate, and report "
        "any difference that must remain."
    ),
    "prepare.finding.curation_confound.title": "Pre-upload curation differs across texts",
    "prepare.finding.curation_confound.body": (
        "Some works disclose editing before upload while others do not. Delta records this "
        "difference but cannot reconstruct or statistically correct those interventions."
    ),
    "prepare.finding.curation_confound.action": (
        "Document what was changed before upload and use a consistent curation procedure where "
        "possible."
    ),
    "prepare.finding.edition_confound.title": "The editions may not be comparable",
    "prepare.finding.edition_confound.body": (
        "Edition descriptions differ or remain uncertain. Editorial choices can affect measured "
        "language patterns, but Delta does not collate editions or prove an edition effect."
    ),
    "prepare.finding.edition_confound.action": (
        "Verify the edition used for each work, prefer a documented comparable edition policy, "
        "and retain unavoidable differences in the interpretation."
    ),
    "prepare.finding.genre_confound.title": "Genre differs or is uncertain",
    "prepare.finding.genre_confound.body": (
        "The corpus mixes documented genres or includes an unknown genre. A later distance may "
        "reflect genre as well as the research factor; this check does not control genre."
    ),
    "prepare.finding.genre_confound.action": (
        "Compare like genres where the question allows, or report the mixture and test a balanced "
        "comparison in a later sensitivity analysis."
    ),
    "prepare.finding.audience_confound.title": "Intended audience differs or is uncertain",
    "prepare.finding.audience_confound.body": (
        "The works target different or undocumented audiences. Audience can shape language use, "
        "but this warning does not establish that it explains a later pattern."
    ),
    "prepare.finding.audience_confound.action": (
        "Verify the audience metadata, prefer comparable audiences where possible, and keep any "
        "difference visible in the interpretation."
    ),
    "prepare.finding.source_confound.title": "Source types are not uniform",
    "prepare.finding.source_confound.body": (
        "The corpus combines different or uncertain source types, such as scans and born-digital "
        "texts. Source production may affect the counted text, but this check does not measure "
        "that effect."
    ),
    "prepare.finding.source_confound.action": (
        "Verify source provenance, compare the prepared files with their sources, and document "
        "why mixed source types are necessary."
    ),
    "prepare.finding.adaptation_confound.title": "Adaptation status differs or is uncertain",
    "prepare.finding.adaptation_confound.body": (
        "Original and adapted works may be mixed, or adaptation status may be unknown. Delta "
        "flags the design difference but does not separate its effect statistically."
    ),
    "prepare.finding.adaptation_confound.action": (
        "Verify adaptation status and compare works with the same status where the research "
        "question permits."
    ),
    "prepare.finding.collection_confound.title": "Collection context differs or is uncertain",
    "prepare.finding.collection_confound.body": (
        "Some works belong to collections while others stand alone, or that context is unknown. "
        "This may accompany editorial or genre differences, but the warning proves no effect."
    ),
    "prepare.finding.collection_confound.action": (
        "Check collection membership and editorial context, then balance the corpus or report the "
        "difference as a limitation."
    ),
    "prepare.finding.chronology_confound.title": "Chronology may complicate this comparison",
    "prepare.finding.chronology_confound.body": (
        "Dates differ in a way relevant to the selected purpose or include approximate, ranged, "
        "or unknown values. Chronology alone does not prove ageing, development, or causation."
    ),
    "prepare.finding.chronology_confound.action": (
        "Verify publication dates and their certainty, then align the corpus design with the "
        "research question and report unavoidable uncertainty."
    ),
    "prepare.finding.mfw_unavailable.title": "One or more planned MFW levels are unavailable",
    "prepare.finding.mfw_unavailable.body": (
        "The known reference corpus contains fewer candidate features than a planned MFW "
        "setting requires."
    ),
    "prepare.finding.mfw_unavailable.action": (
        "Use only the available lower MFW settings; do not invent or pad missing features."
    ),
    "prepare.finding.transport_feature_excluded.title": "An overlong feature was excluded",
    "prepare.finding.transport_feature_excluded.body": (
        "A surface word exceeded the fixed worker transport limit and was not sent to the "
        "analysis engine."
    ),
    "prepare.finding.transport_feature_excluded.action": (
        "Usually no change is required; retain this note in the evidence package and "
        "inspect unusual tokenization if frequent."
    ),
    "prepare.finding.preparation_summary.title": "Preparation completed deterministically",
    "prepare.finding.preparation_summary.body": (
        "Delta recorded document counts, token counts, feature capacity, and the exact "
        "preparation profile without exporting raw text."
    ),
    "prepare.finding.preparation_summary.action": (
        "Review the manifest and health report, then keep both with the later run evidence."
    ),
    "map.title": "Experiment map",
    "map.body": "Each stage opens only after its own checks pass.",
    "boundary.title": "Method boundary",
    "boundary.body": (
        "Stylometric distance describes patterns within the selected corpus. By itself, "
        "it does not prove authorship, intention, influence, or causation."
    ),
    "evidence.title": "Evidence reserved with every run",
    "evidence.body": "A completed experiment will keep these records visible and exportable.",
    "evidence.corpus": "Corpus health",
    "evidence.corpus_state": "Awaiting corpus",
    "evidence.corpus_validated": "Validated for intake",
    "evidence.corpus_rejected": "Intake submission rejected",
    "evidence.parameters": "Parameter sensitivity",
    "evidence.parameters_state": "Awaiting configuration",
    "evidence.limits": "Interpretive limits",
    "evidence.limits_state": "Purpose selected",
    "evidence.run": "Run record",
    "evidence.run_state": "Created on execution",
    "state.empty.label": "No experiment yet",
    "state.empty.title": "No analysis run yet",
    "state.empty.body": (
        "Secure intake is available. Corpus documentation, parameter setup, and the "
        "analysis engine remain locked until their own checks are implemented."
    ),
    "state.loading.label": "Analysis running",
    "state.loading.title": "The experiment is being calculated",
    "state.loading.body": (
        "Progress, active parameters, and elapsed time remain visible while the worker runs."
    ),
    "state.error.label": "Analysis stopped",
    "state.error.title": "The experiment did not produce a valid result",
    "state.error.body": (
        "The run record preserves the failure stage without exposing text content or a system path."
    ),
    "state.cancelled.label": "Analysis cancelled",
    "state.cancelled.title": "The experiment was cancelled",
    "state.cancelled.body": (
        "Partial outputs are not presented as complete results; the cancellation "
        "remains in the run record."
    ),
    "state.complete.label": "Analysis complete",
    "state.complete.title": "The result package is ready for review",
    "state.complete.body": (
        "Review corpus health, sensitivity, and limits before interpreting or exporting the result."
    ),
    "run.button": "Run analysis - unavailable until setup is complete",
    "run.help": (
        "Analysis becomes available after corpus documentation, parameter validation, "
        "and engine integration."
    ),
    "run.disabled_reason": (
        "Analysis remains unavailable until corpus documentation, parameter checks, "
        "and the analysis engine are connected."
    ),
    "footer.scope": (
        "Designed to remove R and Python coding from supported workflows. Method "
        "knowledge and interpretation remain the researcher's responsibility."
    ),
    "footer.fair": (
        "FAIR-oriented development record · decisions, tests, failures, and "
        "limitations are versioned."
    ),
}

UI_CATALOG: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {DEFAULT_LOCALE: MappingProxyType(_ENGLISH_STRINGS)}
)
SUPPORTED_LOCALES = tuple(UI_CATALOG)


def text(key: str, /, **values: object) -> str:
    """Return one English UI string and interpolate explicitly supplied values."""

    template = UI_CATALOG[DEFAULT_LOCALE][key]
    return template.format(**values)
