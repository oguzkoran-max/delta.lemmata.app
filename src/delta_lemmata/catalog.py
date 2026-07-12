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
    "brand.subtitle": "Stylometry workbench",
    "header.stage": "Secure intake",
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
    "build.engine_value": "Not connected",
    "setup.eyebrow": "STYLOMETRY, WITHOUT THE CODE",
    "setup.title": "Discover patterns in writing style.",
    "setup.intro": (
        "Stylometry compares measurable patterns in language use across texts, "
        "including how often common words recur. Delta helps you compare texts, "
        "examine documented groups, and trace change over time without writing R or Python."
    ),
    "setup.corpus_scope": (
        "Every comparison is relative to the corpus you provide. Delta documents "
        "the texts before it exposes any method settings."
    ),
    "setup.pattern_tokens": "and · the · but · yet · of · with",
    "setup.method_label": "How stylometry works",
    "setup.method.observe.title": "Observe",
    "setup.method.observe.body": "Common words and recurring patterns",
    "setup.method.compare.title": "Compare",
    "setup.method.compare.body": "Patterns across documented texts",
    "setup.method.interpret.title": "Interpret",
    "setup.method.interpret.body": "With dates, editions, genre, source, and rights",
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
        "Controls stay locked until corpus-health checks and the R stylo engine are "
        "connected. No stylometric analysis is running in this build."
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
    "mode.status": "Configuration remains locked until corpus documentation is connected.",
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
    "corpus.continue_button": "Continue to describe the corpus",
    "corpus.continue_button_help": (
        "Delta will retain only the validated file catalog and will clear the uploaded "
        "browser payload before opening corpus documentation."
    ),
    "corpus.zip_ready": (
        "Each validated TXT member will open as a separate work in corpus documentation."
    ),
    "flow.progress_accessible": "Experiment progress: corpus documentation is active",
    "flow.stage.upload": "Upload",
    "flow.stage.describe": "Describe",
    "flow.stage.review": "Review",
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
        "Corpus documentation has no blockers. Parameter setup remains locked until "
        "the analysis engine and its checks are connected."
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
