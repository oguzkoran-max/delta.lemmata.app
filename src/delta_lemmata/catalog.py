"""Central English UI catalog.

P002 intentionally ships one locale. Keeping every user-facing string here makes
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
    "header.stage": "Interface foundation",
    "header.version": "Version {version}",
    "header.build": "Build {build_id}",
    "sidebar.progress": "Experiment map · 1 of 4",
    "sidebar.step.purpose": "Purpose",
    "sidebar.step.corpus": "Corpus",
    "sidebar.step.parameters": "Parameters",
    "sidebar.step.evidence": "Evidence",
    "sidebar.state.active": "Active",
    "sidebar.state.locked": "Locked",
    "sidebar.boundary_title": "Current boundary",
    "sidebar.boundary_body": "This build does not ingest texts or calculate stylometric results.",
    "build.title": "Build information",
    "build.readiness_label": "Readiness",
    "build.readiness_value": "Interface only",
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
    "mode.status": "Configuration opens after corpus validation.",
    "corpus.eyebrow": "CORPUS · STEP 2",
    "corpus.title": "Add the research corpus",
    "corpus.body": (
        "Secure corpus intake is deliberately unavailable until it has been "
        "implemented and security-tested."
    ),
    "corpus.locked": "Locked for validation",
    "corpus.uploader": "Corpus files - unavailable in this preview",
    "corpus.uploader_help": (
        "The validated release will accept documented text and metadata inputs. "
        "This interface shell does not process files."
    ),
    "corpus.disabled_reason": (
        "These controls are unavailable in this interface preview. Secure corpus "
        "intake must be implemented and tested before files or metadata can be added."
    ),
    "corpus.metadata_button": "Add metadata - unavailable until intake is ready",
    "corpus.metadata_button_help": (
        "Metadata import opens after secure corpus intake has been implemented and tested."
    ),
    "corpus.continue_button": "Continue - unavailable until corpus checks pass",
    "corpus.continue_button_help": (
        "Parameter configuration opens once a corpus has been loaded and checked."
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
    "evidence.parameters": "Parameter sensitivity",
    "evidence.parameters_state": "Awaiting configuration",
    "evidence.limits": "Interpretive limits",
    "evidence.limits_state": "Purpose selected",
    "evidence.run": "Run record",
    "evidence.run_state": "Created on execution",
    "state.empty.label": "No experiment yet",
    "state.empty.title": "The workspace is ready for a research purpose",
    "state.empty.body": (
        "Corpus controls will open only after secure ingestion has been implemented and tested."
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
    "run.help": "Analysis becomes available after validated corpus intake and engine integration.",
    "run.disabled_reason": (
        "Analysis remains unavailable until corpus intake, parameter checks, and the "
        "analysis engine are connected."
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
