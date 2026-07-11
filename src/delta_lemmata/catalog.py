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
    "sidebar.step.purpose": "Purpose",
    "sidebar.step.corpus": "Corpus",
    "sidebar.step.parameters": "Parameters",
    "sidebar.step.evidence": "Evidence",
    "sidebar.state.active": "Active",
    "sidebar.state.complete": "Complete",
    "sidebar.state.validated": "Validated",
    "sidebar.state.locked": "Locked",
    "sidebar.boundary_title": "Current boundary",
    "sidebar.boundary_body": (
        "This build validates uploads without creating analysis state. It does not "
        "calculate stylometric results or retain a permanent project copy."
    ),
    "build.title": "Build information",
    "build.readiness_label": "Readiness",
    "build.readiness_value": "Secure intake available",
    "build.engine_label": "Analysis engine",
    "build.engine_value": "Not connected",
    "setup.eyebrow": "EXPERIMENT SETUP · STEP 1",
    "setup.title": "Set the research purpose",
    "setup.intro": (
        "Begin with the question. Delta keeps corpus checks, parameter choices, "
        "interpretive limits, and a rerun record beside the eventual result."
    ),
    "purpose.label": "Research purpose",
    "purpose.badge": "Selected purpose",
    "purpose.question_label": "Working question",
    "purpose.use_label": "Use this when",
    "purpose.boundary_label": "Interpretive boundary",
    "purpose.text_proximity.label": "Text Proximity",
    "purpose.text_proximity.question": (
        "Which known texts are stylistically nearest to a focal text?"
    ),
    "purpose.text_proximity.use": "You have one focal text and a documented comparison corpus.",
    "purpose.text_proximity.boundary": (
        "Proximity is not proof of authorship and does not implement open-set rejection."
    ),
    "purpose.group_comparison.label": "Group Comparison",
    "purpose.group_comparison.question": (
        "How does stylistic structure differ across labelled groups of works?"
    ),
    "purpose.group_comparison.use": (
        "You need to compare groups defined by author, genre, period, audience, or "
        "another recorded category."
    ),
    "purpose.group_comparison.boundary": (
        "Observed separation may reflect corpus balance, genre, period, source, or edition effects."
    ),
    "purpose.style_over_time.label": "Style Over Time",
    "purpose.style_over_time.question": (
        "How does a writer's work-level stylistic position vary across a dated corpus?"
    ),
    "purpose.style_over_time.use": (
        "You have several independently dated works and enough metadata to inspect "
        "chronological confounds."
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
    "corpus.eyebrow": "CORPUS · STEP 2",
    "corpus.title": "Validate the research corpus",
    "corpus.body": (
        "Choose the corpus role before adding files. Delta accepts UTF-8, NFC text "
        "files or one strict ZIP archive containing text files only. A metadata CSV "
        "is checked separately for structure and unsafe cells."
    ),
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
    "corpus.success": (
        "Intake checks passed · Uploads: {uploads} · Corpus texts: {units} · Input bytes: {bytes}"
    ),
    "corpus.metadata_valid": "Metadata structure validated",
    "corpus.role.text": "Corpus text",
    "corpus.role.archive": "Corpus archive",
    "corpus.role.csv": "Metadata table",
    "corpus.receipt.text": "Lines: {lines} · Tokens: {tokens}",
    "corpus.receipt.archive": "TXT members: {members} · Expanded bytes: {expanded}",
    "corpus.receipt.csv": "Rows: {rows} · Columns: {columns}",
    "corpus.error.title": "The submission was rejected before intake.",
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
    "corpus.continue_button": "Continue - corpus documentation is not connected",
    "corpus.continue_button_help": (
        "Validated bytes are not enough for analysis. Corpus inventory, metadata meaning, "
        "and rights checks must be connected before parameter configuration opens."
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
    "evidence.corpus_rejected": "Rejected before intake",
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
