"""English-only Streamlit workbench through P008 guided analysis."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from html import escape
from typing import Any, Literal, cast

import pyarrow as pa  # type: ignore[import-untyped]
import streamlit as st
from pydantic import HttpUrl, TypeAdapter, ValidationError

from delta_lemmata.analysis_orchestrator import AnalysisOrchestratorError
from delta_lemmata.catalog import text
from delta_lemmata.corpus import (
    DEFAULT_VOCABULARY,
    AuthorKind,
    CompletenessGroup,
    CompletenessStatus,
    CorpusInventory,
    CorpusReviewProjection,
    DateMode,
    DateValue,
    GuidedWorkInput,
    IssueSeverity,
    MetadataCsvExportError,
    MetadataCsvImportResult,
    PurposeId,
    ReviewProjectionError,
    RightsStatus,
    TimelineDatum,
    ValidatedCorpusUnit,
    ValidationReport,
    build_guided_inventory,
    build_review_projection,
    corpus_catalog_sha256,
    export_completeness_csv,
    export_composition_csv,
    export_metadata_csv,
    guided_work_id,
    import_metadata_csv,
    inventory_sha256,
    project_corpus_receipts,
    suggested_title,
)
from delta_lemmata.corpus_health_models import (
    CorpusHealthFinding,
    CorpusHealthFindingCode,
    CorpusHealthReadiness,
)
from delta_lemmata.corpus_health_projection import (
    ConfoundDatum,
    CorpusHealthProjectionError,
    OverlapDatum,
    build_corpus_health_projection,
    export_confound_matrix_csv,
    export_feature_capacity_csv,
    export_health_findings_csv,
    export_work_preparation_csv,
)
from delta_lemmata.corpus_materialization import (
    CorpusMaterializationError,
    CorpusMaterializationReceipt,
)
from delta_lemmata.health import public_health
from delta_lemmata.ingestion import (
    DEFAULT_LIMITS,
    ArchiveMemberReceipt,
    IntakeError,
    IntakeErrorCode,
    IntakeReceipt,
    IntakeRole,
)
from delta_lemmata.intake_ui import (
    CORPUS_MODE_LABEL_KEYS,
    INTAKE_ERROR_MESSAGE_KEYS,
    BrowserUpload,
    CorpusInputMode,
    IntakeOutcome,
    intake_recovery_guidance_key,
    validate_browser_uploads,
    visit_browser_corpus_payloads,
)
from delta_lemmata.prepared_corpus_service import (
    PreparationOutcome,
    PreparedCorpusError,
    PreparedCorpusErrorCode,
)
from delta_lemmata.preprocessing import build_preprocessing_config, parse_custom_exclusions
from delta_lemmata.preprocessing_models import (
    AnalysisRole,
    CorpusAnalysisAnnotation,
    CorpusAnalysisAnnotationsV1,
    OcrStatus,
    ParatextStatus,
    TextUnit,
    canonical_p007_json,
)
from delta_lemmata.provenance import canonical_json_bytes
from delta_lemmata.result_service import VerifiedScientificResult
from delta_lemmata.result_view import (
    ResultCellStatus,
    ResultCellV1,
    ResultDocumentDescriptor,
    ResultViewV1,
    canonical_result_view,
    classical_mds,
    nearest_neighbours,
    project_result_view,
)
from delta_lemmata.stylo_contracts import DocumentRole
from delta_lemmata.ui_theme import APP_CSS
from delta_lemmata.web_runtime import (
    WebRuntime,
    WebRuntimeError,
    WebRuntimeErrorCode,
    build_web_runtime,
)
from delta_lemmata.workbench import (
    MODE_BODY_KEYS,
    MODE_LABEL_KEYS,
    PURPOSE_BY_ID,
    PURPOSES,
    PurposeSpec,
    WorkbenchMode,
)
from delta_lemmata.workflow_models import (
    ResolvedWorkflowConfigV1,
    canonical_p008_json,
    resolve_guided_workflow,
)

_UPLOAD_GENERATION_KEY = "_intake_upload_generation"
_PENDING_ERROR_KEY = "_intake_pending_error"
_PENDING_UPLOAD_CLEAR_KEY = "_intake_pending_widget_clear"
_FLOW_STAGE_KEY = "_p004_flow_stage"
_FLOW_PURPOSE_KEY = "_p004_purpose"
_FLOW_INPUT_MODE_KEY = "_p004_input_mode"
_FLOW_CATALOG_KEY = "_p004_catalog"
_FLOW_CATALOG_HASH_KEY = "_p004_catalog_sha256"
_FLOW_IMPORT_KEY = "_p004_metadata_import"
_FLOW_INVENTORY_KEY = "_p004_inventory"
_FLOW_REPORT_KEY = "_p004_validation_report"
_FLOW_ORIGIN_KEY = "_p004_inventory_origin"
_FLOW_GUIDED_INPUTS_KEY = "_p004_guided_inputs"
_FLOW_CORRECTION_KEY = "_p004_correction_target"
_FLOW_CONFIRMATION_HASH_KEY = "_p004_confirmation_inventory_sha256"
_FLOW_OWNER_KEY = "_private_owner_key"
_FLOW_MATERIALIZATION_KEY = "_p005_materialization_receipt"
_FLOW_ANNOTATIONS_KEY = "_p007_annotations"
_FLOW_PREPARATION_KEY = "_p007_preparation_outcome"
_FLOW_WORKFLOW_CONFIG_KEY = "_p008_resolved_workflow_config"
_FLOW_JOB_PRESENTATION_KEY = "_p008_job_presentation"
_RECOVERABLE_JOB_STATES = frozenset(
    {"failed", "cancelled", "timed_out", "crashed", "abandoned", "expired"}
)
_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


class CorpusSubstage(StrEnum):
    UPLOAD = "upload"
    DESCRIBE = "describe"
    REVIEW = "review"
    PREPARE = "prepare"
    PARAMETERS = "parameters"


class CorpusOrigin(StrEnum):
    GUIDED = "guided"
    CSV = "csv"


@dataclass(frozen=True, slots=True)
class CorrectionTarget:
    row_key: str
    work_id: str
    work_title: str
    group: CompletenessGroup
    field_path: str


@dataclass(frozen=True, slots=True)
class PreparationSelection:
    asset_id: str
    work_id: str
    analysis_role: AnalysisRole
    ocr_status: OcrStatus
    paratext_status: ParatextStatus
    curation_note: str | None


@st.cache_resource(show_spinner=False)
def _runtime() -> WebRuntime:
    return build_web_runtime()


def _owner_key() -> str:
    value = st.session_state.get(_FLOW_OWNER_KEY)
    if not isinstance(value, str) or len(value) != 64:
        value = secrets.token_hex(32)
        st.session_state[_FLOW_OWNER_KEY] = value
    return value


def _html(value: str) -> str:
    return escape(value, quote=True)


def _render_main_landmark_bridge() -> None:
    """Promote Streamlit's application section to the page's main landmark."""

    st.html(
        """
        <script>
        (() => {
          const main = document.querySelector('[data-testid="stMain"]');
          if (main) {
            main.id = 'delta-main-landmark';
            main.setAttribute('role', 'main');
          }

          const root = document.documentElement;
          if (!root.dataset.deltaSkipHandler) {
            document.addEventListener('click', (event) => {
              const link = event.target.closest?.('.delta-skip-link');
              if (!link) return;
              const target = document.getElementById('delta-content-start');
              if (!target) return;
              event.preventDefault();
              target.focus({preventScroll: true});
              target.scrollIntoView({block: 'start'});
            }, true);
            root.dataset.deltaSkipHandler = 'ready';
          }
        })();
        </script>
        """,
        width="content",
        unsafe_allow_javascript=True,
    )


def _render_header(
    health: dict[str, Any],
    stage: CorpusSubstage,
    *,
    evidence_active: bool,
) -> None:
    _render_main_landmark_bridge()
    version = text("header.version", version=health["version"])
    build_id_full = str(health["build_id"])
    build_id_short = build_id_full if len(build_id_full) <= 12 else build_id_full[:12]
    build = text("header.build", build_id=build_id_short)
    build_full = text("header.build", build_id=build_id_full)
    release_alpha = _html(text("header.release_public_alpha"))
    release_experimental = _html(text("header.release_experimental"))
    if evidence_active:
        stage_label = text("header.stage.evidence")
    elif stage is CorpusSubstage.UPLOAD:
        stage_label = text("header.stage.upload")
    elif stage is CorpusSubstage.PARAMETERS:
        stage_label = text("header.stage.parameters")
    else:
        stage_label = text("header.stage.corpus")
    st.markdown(
        f"""
        <a class="delta-skip-link" href="#delta-content-start">
          {_html(text("accessibility.skip_to_main"))}
        </a>
        <div class="delta-header">
          <div class="delta-brand">
            <span class="delta-mark" aria-hidden="true">{_html(text("brand.mark"))}</span>
            <div>
              <div class="delta-brand-name">{_html(text("brand.name"))}</div>
              <div class="delta-brand-subtitle">{_html(text("brand.subtitle"))}</div>
              <div class="delta-release-status"
                   aria-label="{_html(text("header.release_status"))}">
                <span class="delta-release-alpha">{release_alpha}</span>
                <span class="delta-release-experimental">{release_experimental}</span>
              </div>
            </div>
          </div>
          <div class="delta-build">
            <div class="delta-build-status">
              <span class="delta-dot"></span>{_html(stage_label)}
            </div>
            <div class="delta-build-meta" title="{_html(build_full)}">
              {_html(version)} · {_html(build)}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_content_anchor() -> None:
    st.markdown(
        '<span id="delta-content-start" class="delta-main-anchor" tabindex="-1"></span>',
        unsafe_allow_html=True,
    )


def _stage() -> CorpusSubstage:
    value = st.session_state.get(_FLOW_STAGE_KEY, CorpusSubstage.UPLOAD.value)
    try:
        return CorpusSubstage(value)
    except ValueError:
        st.session_state[_FLOW_STAGE_KEY] = CorpusSubstage.UPLOAD.value
        return CorpusSubstage.UPLOAD


def _set_stage(stage: CorpusSubstage) -> None:
    st.session_state[_FLOW_STAGE_KEY] = stage.value


def _map_row(
    number: int,
    label_key: str,
    state_key: str,
    *,
    active: bool = False,
) -> str:
    active_class = " is-active" if active else ""
    current = ' aria-current="step"' if active else ""
    return (
        f'<li class="delta-map-row{active_class}"{current}>'
        f'<span class="delta-map-number">{number:02d}</span>'
        f'<span class="delta-map-name">{_html(text(label_key))}</span>'
        f'<span class="delta-map-state">{_html(text(state_key))}</span>'
        "</li>"
    )


def _render_stepper(stage: CorpusSubstage, *, evidence_active: bool) -> None:
    stage_key = {
        CorpusSubstage.UPLOAD: "flow.stage.upload",
        CorpusSubstage.DESCRIBE: "flow.stage.describe",
        CorpusSubstage.REVIEW: "flow.stage.review",
        CorpusSubstage.PREPARE: "flow.stage.prepare",
        CorpusSubstage.PARAMETERS: "flow.stage.parameters",
    }[stage]
    parameter_stage = stage is CorpusSubstage.PARAMETERS and not evidence_active
    corpus_state = "sidebar.state.complete" if parameter_stage else stage_key
    parameter_state = stage_key if parameter_stage else "flow.locked"
    if evidence_active:
        corpus_state = "sidebar.state.complete"
        parameter_state = "sidebar.state.complete"
    markup = (
        f'<nav class="delta-map delta-map-{stage.value}" '
        'aria-label="Experiment progress">'
        '<ol class="delta-map-list">'
        + _map_row(1, "sidebar.step.purpose", "sidebar.state.complete")
        + _map_row(
            2,
            "sidebar.step.corpus",
            corpus_state,
            active=not parameter_stage and not evidence_active,
        )
        + _map_row(
            3,
            "sidebar.step.parameters",
            parameter_state,
            active=parameter_stage,
        )
        + _map_row(
            4,
            "sidebar.step.evidence",
            "sidebar.state.active" if evidence_active else "flow.locked",
            active=evidence_active,
        )
        + "</ol></nav>"
    )
    st.markdown(markup, unsafe_allow_html=True)


def _sidebar_readiness_counts() -> tuple[dict[str, int], bool]:
    """Read the live corpus readiness from session state for the sidebar summary."""

    report = st.session_state.get(_FLOW_REPORT_KEY)
    if isinstance(report, ValidationReport):
        readiness = report.readiness
        return (
            {
                "works": readiness.independent_work_count,
                "blockers": readiness.blocker_count,
                "warnings": readiness.warning_count,
                "rights": readiness.rights_restriction_count,
            },
            True,
        )
    return ({"works": 0, "blockers": 0, "warnings": 0, "rights": 0}, False)


def _render_sidebar_summary() -> None:
    counts, has_corpus = _sidebar_readiness_counts()
    metric_rows = "".join(
        '<div class="delta-sidebar-metric">'
        f"<span>{_html(text(label_key))}</span>"
        f'<b class="delta-sidebar-metric-{tone}">{counts[value_key]}</b></div>'
        for label_key, value_key, tone in (
            ("review.metric.works", "works", "plain"),
            ("review.metric.blockers", "blockers", "blocker" if counts["blockers"] else "plain"),
            ("review.metric.warnings", "warnings", "warning" if counts["warnings"] else "plain"),
            ("review.metric.rights", "rights", "plain"),
        )
    )
    corpus_state_key = "evidence.corpus_validated" if has_corpus else "evidence.corpus_state"
    evidence_rows = "".join(
        '<div class="delta-sidebar-evidence-row">'
        f"<span>{_html(text(name_key))}</span>"
        f"<small>{_html(text(state_key))}</small></div>"
        for name_key, state_key in (
            ("evidence.corpus", corpus_state_key),
            ("evidence.parameters", "evidence.parameters_state"),
            ("evidence.limits", "evidence.limits_state"),
            ("evidence.run", "evidence.run_state"),
        )
    )
    st.markdown(
        '<section class="delta-sidebar-summary" role="region" '
        'aria-labelledby="delta-sidebar-summary-title">'
        '<strong class="delta-sidebar-summary-title" id="delta-sidebar-summary-title">'
        f"{_html(text('sidebar.summary_title'))}</strong>"
        f'<div class="delta-sidebar-metrics">{metric_rows}</div>'
        '<div class="delta-sidebar-evidence">'
        f'<span class="delta-sidebar-evidence-head">{_html(text("evidence.title"))}</span>'
        f"{evidence_rows}</div></section>",
        unsafe_allow_html=True,
    )


def _render_sidebar(health: dict[str, Any], stage: CorpusSubstage) -> None:
    with st.sidebar:
        badge_key = (
            "sidebar.badge.parameters" if stage is CorpusSubstage.PARAMETERS else "sidebar.badge"
        )
        st.badge(text(badge_key), icon=":material/menu_book:", color="green")
        guide_items = "".join(
            f"<li>{_html(text(key))}</li>"
            for key in (
                "sidebar.guide.question",
                "sidebar.guide.corpus",
                "sidebar.guide.parameters",
            )
        )
        st.markdown(
            '<section class="delta-sidebar-guide" role="region" '
            'aria-labelledby="delta-sidebar-title">'
            f'<strong class="delta-sidebar-title" id="delta-sidebar-title">'
            f"{_html(text('sidebar.guide_title'))}</strong>"
            f"<p>{_html(text('sidebar.guide_body'))}</p>"
            f"<ol>{guide_items}</ol>"
            '<div class="delta-sidebar-parameters">'
            f"<strong>{_html(text('sidebar.parameters_title'))}</strong>"
            f"<p>{_html(text('sidebar.parameters_body'))}</p>"
            "</div></section>",
            unsafe_allow_html=True,
        )
        _render_sidebar_summary()
        with st.expander(text("build.title"), icon=":material/info:"):
            st.markdown(f"**{text('build.readiness_label')}**")
            st.caption(text("build.readiness_value"))
            st.markdown(f"**{text('build.engine_label')}**")
            st.caption(text("build.engine_value"))
            st.caption(text("header.version", version=health["version"]))
            st.caption(text("header.build", build_id=health["build_id"]))


def _purpose_label(purpose_id: str) -> str:
    return text(PURPOSE_BY_ID[purpose_id].label_key)


def _mode_label(mode_id: str) -> str:
    return text(MODE_LABEL_KEYS[WorkbenchMode(mode_id)])


def _corpus_mode_label(mode_id: str) -> str:
    return text(CORPUS_MODE_LABEL_KEYS[CorpusInputMode(mode_id)])


def _choice_label(value: str) -> str:
    return value.replace("_", " ").title()


def _field_label(field_path: str) -> str:
    """Return a readable field name while keeping the raw path for audit details."""

    parts = tuple(part for part in field_path.split(".") if part)
    if not parts:
        return field_path
    leaf = parts[-1].split("[")[0]
    parent = parts[-2].split("[")[0] if len(parts) > 1 else ""
    if leaf in {"start_year", "end_year", "mode"} and parent:
        return f"{_choice_label(parent)}: {_choice_label(leaf)}"
    return _choice_label(leaf)


def _rights_label(value: str) -> str:
    return text(f"describe.rights.{value}")


def _analysis_role_label(value: str) -> str:
    return text(f"prepare.role.{value}.label")


def _ocr_label(value: str) -> str:
    return text(f"prepare.ocr.{value}")


def _paratext_label(value: str) -> str:
    return text(f"prepare.paratext.{value}")


def _browser_upload(upload: Any) -> BrowserUpload:
    return BrowserUpload(
        display_label=upload.name,
        data=upload.getvalue(),
        declared_mime=upload.type or None,
    )


def _receipt_metric(receipt: IntakeReceipt) -> str:
    if receipt.role is IntakeRole.CORPUS_TEXT:
        return text("corpus.receipt.text", lines=receipt.line_count, tokens=receipt.token_count)
    if receipt.role is IntakeRole.CORPUS_ARCHIVE:
        return text(
            "corpus.receipt.archive",
            members=receipt.member_count,
            expanded=receipt.expanded_bytes,
        )
    return text(
        "corpus.receipt.csv",
        rows=receipt.row_count,
        columns=receipt.column_count,
    )


def _archive_member_metric(member: ArchiveMemberReceipt) -> str:
    return text(
        "corpus.receipt.member",
        lines=member.line_count,
        tokens=member.token_count,
        digest=member.sha256[:12],
    )


def _render_receipts(outcome: IntakeOutcome) -> None:
    role_keys = {
        IntakeRole.CORPUS_TEXT: "corpus.role.text",
        IntakeRole.CORPUS_ARCHIVE: "corpus.role.archive",
        IntakeRole.METADATA_CSV: "corpus.role.csv",
    }
    markup = "".join(
        '<div class="delta-intake-row">'
        '<div class="delta-intake-identity">'
        f'<span class="delta-intake-name">{_html(receipt.display_label)}</span>'
        f'<span class="delta-intake-role">{_html(text(role_keys[receipt.role]))}</span>'
        "</div>"
        f'<span class="delta-intake-metric">{_html(_receipt_metric(receipt))}</span>'
        "</div>"
        for receipt in outcome.receipts
    )
    st.markdown(markup, unsafe_allow_html=True)
    members = tuple(
        member
        for receipt in outcome.receipts
        if receipt.role is IntakeRole.CORPUS_ARCHIVE
        for member in receipt.archive_members
    )
    if members:
        member_markup = "".join(
            '<div class="delta-intake-row" role="listitem">'
            '<div class="delta-intake-identity">'
            f'<span class="delta-intake-name">{_html(member.display_label)}</span>'
            f'<span class="delta-intake-role">{_html(text("corpus.role.member"))}</span>'
            "</div>"
            f'<span class="delta-intake-metric">{_html(_archive_member_metric(member))}</span>'
            "</div>"
            for member in members
        )
        title = text("corpus.archive_catalog")
        st.markdown(
            '<div class="delta-archive-catalog" role="region" '
            f'aria-label="{_html(title)}">'
            f'<div class="delta-field-label">{_html(title)}</div>'
            f'<div role="list">{member_markup}</div></div>',
            unsafe_allow_html=True,
        )


def _purpose_guidance_markup(purpose: PurposeSpec) -> str:
    guidance = text("purpose.guidance")
    items = (
        ("purpose.question_label", purpose.question_key, "question"),
        ("purpose.use_label", purpose.use_key, "use"),
        ("purpose.boundary_label", purpose.boundary_key, "boundary"),
    )
    markup = "".join(
        '<div class="delta-purpose-guide-item '
        f'delta-purpose-guide-{kind}">'
        f"<span>{_html(text(label_key))}</span>"
        f"<p>{_html(text(body_key))}</p>"
        "</div>"
        for label_key, body_key, kind in items
    )
    return f'<section class="delta-purpose-guide" aria-label="{_html(guidance)}">{markup}</section>'


def _render_purpose_guidance(purpose: PurposeSpec) -> None:
    st.markdown(
        f'<div class="delta-purpose-guide-desktop">{_purpose_guidance_markup(purpose)}</div>',
        unsafe_allow_html=True,
    )


def _render_mobile_purpose_guidance(purpose: PurposeSpec) -> None:
    guidance = text("purpose.guidance")
    st.markdown(
        '<details class="delta-purpose-guide-mobile">'
        f"<summary>{_html(guidance)}</summary>"
        f"{_purpose_guidance_markup(purpose)}</details>",
        unsafe_allow_html=True,
    )


def _render_entry_experience() -> None:
    st.markdown(
        f"""
        <section class="delta-entry" aria-labelledby="delta-entry-title">
          <div class="delta-entry-copy">
            <div class="delta-entry-eyebrow">{_html(text("setup.eyebrow"))}</div>
            <h1 id="delta-entry-title">{_html(text("setup.title"))}</h1>
            <p class="delta-entry-lede">{_html(text("setup.intro"))}</p>
            <p class="delta-entry-scope">{_html(text("setup.corpus_scope"))}</p>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_stylometry_orientation() -> None:
    trace_rows = tuple(
        (
            text(f"setup.trace.row_{row}_label"),
            tuple(text(f"setup.trace.row_{row}").split()),
        )
        for row in ("a", "b")
    )
    trace_markup = "".join(
        '<div class="delta-trace-row">'
        f'<span class="delta-trace-row-label">{_html(label)}</span>'
        '<span class="delta-trace-tokens">'
        + "".join(
            f'<span class="delta-trace-token delta-trace-tone-{index % 4}">{_html(token)}</span>'
            for index, token in enumerate(tokens)
        )
        + "</span></div>"
        for label, tokens in trace_rows
    )
    trace_legend = "".join(
        '<li class="delta-trace-legend-item '
        f'delta-trace-legend-{tone}"><span aria-hidden="true"></span>'
        f"{_html(text(label_key))}</li>"
        for tone, label_key in (
            ("teal", "setup.trace.common_words"),
            ("blue", "setup.trace.punctuation"),
            ("amber", "setup.trace.rhythm"),
            ("purple", "setup.trace.vocabulary"),
        )
    )
    method_steps = (
        ("01", "setup.method.observe.title", "setup.method.observe.body"),
        ("02", "setup.method.compare.title", "setup.method.compare.body"),
        ("03", "setup.method.interpret.title", "setup.method.interpret.body"),
    )
    method_markup = "".join(
        '<li class="delta-method-step">'
        f'<span class="delta-method-number">{number}</span>'
        '<span class="delta-method-copy">'
        f"<strong>{_html(text(title_key))}</strong>"
        f"<small>{_html(text(body_key))}</small>"
        "</span></li>"
        for number, title_key, body_key in method_steps
    )
    st.markdown(
        f"""
        <section class="delta-stylometry-orientation" aria-labelledby="delta-method-title">
          <h2 id="delta-method-title">{_html(text("setup.method_label"))}</h2>
          <p class="delta-orientation-caption">{_html(text("setup.method.caption"))}</p>
          <figure class="delta-method" aria-label="{_html(text("setup.method_label"))}">
            <ol>{method_markup}</ol>
          </figure>
          <figure class="delta-style-trace" aria-labelledby="delta-trace-title">
            <figcaption>
              <span class="delta-trace-kicker">{_html(text("setup.trace.kicker"))}</span>
              <strong id="delta-trace-title">{_html(text("setup.trace.title"))}</strong>
              <span>{_html(text("setup.trace.body"))}</span>
              <small>{_html(text("setup.trace.caption"))}</small>
            </figcaption>
            <div class="delta-trace-samples" aria-hidden="true">{trace_markup}</div>
            <div class="delta-trace-key">
              <span>{_html(text("setup.trace.legend"))}</span>
              <ul>{trace_legend}</ul>
            </div>
          </figure>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_parameter_orientation() -> None:
    items = "".join(
        '<div class="delta-parameter-item">'
        f"<strong>{_html(text(f'parameters.{item}.title'))}</strong>"
        f"<p>{_html(text(f'parameters.{item}.body'))}</p>"
        "</div>"
        for item in ("guided", "research", "status")
    )
    st.markdown(
        '<section class="delta-parameter-note" role="region" '
        'aria-labelledby="delta-parameter-note-title">'
        '<div class="delta-parameter-intro">'
        f'<strong id="delta-parameter-note-title">'
        f"{_html(text('parameters.orientation_title'))}</strong>"
        f"<p>{_html(text('parameters.orientation_body'))}</p>"
        "</div>"
        f'<div class="delta-parameter-grid">{items}</div>'
        "</section>",
        unsafe_allow_html=True,
    )


def _analysis_status_markup(
    *,
    title: str,
    body: str,
    reference: str | None,
    alert: bool,
) -> str:
    role = "alert" if alert else "status"
    live = "assertive" if alert else "polite"
    reference_markup = (
        ""
        if reference is None
        else f'<small class="delta-analysis-reference">{_html(reference)}</small>'
    )
    state_class = " is-alert" if alert else ""
    return (
        f'<section class="delta-analysis-status{state_class}" role="{role}" '
        f'aria-live="{live}" aria-atomic="true">'
        '<span class="delta-analysis-status-icon" aria-hidden="true">'
        f"{'!' if alert else 'i'}</span>"
        '<div class="delta-analysis-status-copy">'
        f"<strong>{_html(title)}</strong>"
        f"<p>{_html(body)}</p>"
        f"{reference_markup}"
        "</div></section>"
    )


def _terminal_presentation(
    runtime: WebRuntime,
    materialization: CorpusMaterializationReceipt,
) -> object | None:
    try:
        presentation = runtime.prepared_corpora.status(
            owner_key=_owner_key(),
            materialization_receipt=materialization,
        )
    except (PreparedCorpusError, WebRuntimeError, AttributeError):
        return None
    return (
        presentation if getattr(presentation, "state_id", "") in _RECOVERABLE_JOB_STATES else None
    )


def _render_mode() -> WorkbenchMode:
    selected = st.segmented_control(
        text("mode.label"),
        options=[mode.value for mode in WorkbenchMode],
        default=WorkbenchMode.GUIDED.value,
        format_func=_mode_label,
        key="analysis_mode",
        width="stretch",
    )
    mode = WorkbenchMode(selected or WorkbenchMode.GUIDED.value)
    st.caption(text(MODE_BODY_KEYS[mode]))
    st.caption(text("mode.status"))
    return mode


def _render_boundary() -> None:
    with st.container(border=False, key="boundary_panel"):
        st.header(text("boundary.title"), anchor=False)
        st.caption(text("boundary.body"))


def _upload_widget_keys(generation: int) -> tuple[str, ...]:
    return (
        f"corpus_text_files_{generation}",
        f"corpus_archive_file_{generation}",
        f"metadata_file_{generation}",
    )


def _clear_pending_upload_widgets() -> None:
    keys = st.session_state.pop(_PENDING_UPLOAD_CLEAR_KEY, ())
    for key in keys:
        st.session_state.pop(key, None)
    if keys:
        # Complete one payload-free rerun before rendering the documentation view.
        st.rerun()


def _clear_documentation_state(*, keep_purpose: bool) -> None:
    materialization = st.session_state.get(_FLOW_MATERIALIZATION_KEY)
    owner_key = st.session_state.get(_FLOW_OWNER_KEY)
    preparation = st.session_state.get(_FLOW_PREPARATION_KEY)
    materialization_already_cleaned = (
        isinstance(preparation, PreparationOutcome) and preparation.ready_receipt is None
    )
    if (
        isinstance(materialization, CorpusMaterializationReceipt)
        and isinstance(owner_key, str)
        and not materialization_already_cleaned
    ):
        _runtime().materializations.cleanup(
            owner_key=owner_key,
            receipt=materialization,
        )
    for key in (
        _FLOW_CATALOG_KEY,
        _FLOW_INPUT_MODE_KEY,
        _FLOW_CATALOG_HASH_KEY,
        _FLOW_IMPORT_KEY,
        _FLOW_INVENTORY_KEY,
        _FLOW_REPORT_KEY,
        _FLOW_ORIGIN_KEY,
        _FLOW_GUIDED_INPUTS_KEY,
        _FLOW_CORRECTION_KEY,
        _FLOW_CONFIRMATION_HASH_KEY,
        _FLOW_MATERIALIZATION_KEY,
        _FLOW_ANNOTATIONS_KEY,
        _FLOW_PREPARATION_KEY,
        _FLOW_WORKFLOW_CONFIG_KEY,
        _FLOW_JOB_PRESENTATION_KEY,
    ):
        st.session_state.pop(key, None)
    for session_key in tuple(st.session_state):
        if str(session_key).startswith(
            (
                "draft_",
                "prep_",
                "review_confirmation_",
                "review_timeline_selector_",
                "p008_",
            )
        ):
            st.session_state.pop(session_key, None)
    if not keep_purpose:
        st.session_state.pop(_FLOW_PURPOSE_KEY, None)
        st.session_state.pop("research_purpose", None)
    st.session_state[_FLOW_STAGE_KEY] = CorpusSubstage.UPLOAD.value


def _origin() -> CorpusOrigin:
    value = st.session_state.get(_FLOW_ORIGIN_KEY, CorpusOrigin.GUIDED.value)
    try:
        return CorpusOrigin(value)
    except ValueError:
        return CorpusOrigin.GUIDED


def _correction_target() -> CorrectionTarget | None:
    value = st.session_state.get(_FLOW_CORRECTION_KEY)
    return value if isinstance(value, CorrectionTarget) else None


def _render_corpus_stage(purpose: PurposeId) -> IntakeOutcome:
    generation = int(st.session_state.get(_UPLOAD_GENERATION_KEY, 0))
    pending_error_value = st.session_state.pop(_PENDING_ERROR_KEY, None)
    pending_error = None if pending_error_value is None else IntakeErrorCode(pending_error_value)
    try:
        mode = CorpusInputMode(
            st.session_state.get("corpus_input_mode", CorpusInputMode.TEXT_FILES.value)
        )
    except (TypeError, ValueError):
        mode = CorpusInputMode.TEXT_FILES
        st.session_state["corpus_input_mode"] = mode.value
    with st.container(border=True, key="corpus_stage"):
        st.markdown(
            f'<div class="delta-eyebrow">{_html(text("corpus.eyebrow"))}</div>',
            unsafe_allow_html=True,
        )
        title_column, badge_column = st.columns([2.2, 1.2], vertical_alignment="center")
        with title_column:
            st.header(text("corpus.title"), anchor=False)
        with badge_column:
            st.badge(text("corpus.available"), icon=":material/shield:", color="green")
        st.caption(text("corpus.body"))
        with st.container(key="corpus_inputs"):
            selected_mode = st.radio(
                text("corpus.mode.label"),
                options=[item.value for item in CorpusInputMode],
                index=tuple(CorpusInputMode).index(mode),
                format_func=_corpus_mode_label,
                key="corpus_input_mode",
                horizontal=True,
            )
            mode = CorpusInputMode(selected_mode)
            uploader_context = {
                "purpose": _purpose_label(purpose.value),
                "mode": _corpus_mode_label(mode.value),
            }
            if mode is CorpusInputMode.TEXT_FILES:
                uploaded_corpus = st.file_uploader(
                    text("corpus.text_uploader", **uploader_context),
                    type=["txt"],
                    accept_multiple_files=True,
                    help=text("corpus.text_uploader_help"),
                    key=f"corpus_text_files_{generation}",
                )
                corpus_files = tuple(_browser_upload(upload) for upload in uploaded_corpus)
            else:
                uploaded_archive = st.file_uploader(
                    text("corpus.archive_uploader", **uploader_context),
                    type=["zip"],
                    accept_multiple_files=False,
                    help=text("corpus.archive_uploader_help"),
                    key=f"corpus_archive_file_{generation}",
                )
                corpus_files = (
                    () if uploaded_archive is None else (_browser_upload(uploaded_archive),)
                )
        uploaded_metadata = None
        with st.expander(text("corpus.metadata_advanced")):
            uploaded_metadata = st.file_uploader(
                text("corpus.metadata_uploader", **uploader_context),
                type=["csv"],
                accept_multiple_files=False,
                help=text("corpus.metadata_uploader_help"),
                key=f"metadata_file_{generation}",
            )
        metadata_file = None if uploaded_metadata is None else _browser_upload(uploaded_metadata)
        st.caption(
            text(
                "corpus.limits",
                upload_mib=DEFAULT_LIMITS.max_upload_bytes // (1024 * 1024),
                batch_files=DEFAULT_LIMITS.max_batch_files,
                archive_members=DEFAULT_LIMITS.max_archive_members,
                archive_mib=DEFAULT_LIMITS.max_archive_expanded_bytes // (1024 * 1024),
            )
        )
        outcome = validate_browser_uploads(mode, corpus_files, metadata_file)
        if outcome.error_code is not None:
            st.session_state[_PENDING_ERROR_KEY] = outcome.error_code.value
            st.session_state[_PENDING_UPLOAD_CLEAR_KEY] = _upload_widget_keys(generation)
            st.session_state[_UPLOAD_GENERATION_KEY] = generation + 1
            st.rerun()
        display_outcome = (
            IntakeOutcome(submitted_count=1, error_code=pending_error)
            if pending_error is not None and not outcome.has_inputs
            else outcome
        )
        if not display_outcome.has_inputs:
            st.info(text("corpus.empty"), icon=":material/upload_file:")
        elif display_outcome.error_code is not None:
            st.error(text("corpus.error.title"), icon=":material/gpp_bad:")
            st.caption(text(INTAKE_ERROR_MESSAGE_KEYS[display_outcome.error_code]))
            st.caption(text(intake_recovery_guidance_key(display_outcome.error_code)))
            st.caption(text("corpus.error.reference", code=display_outcome.error_code.value))
        else:
            if display_outcome.corpus_ready:
                st.success(
                    text(
                        "corpus.success",
                        uploads=display_outcome.submitted_count,
                        units=display_outcome.corpus_units,
                        bytes=display_outcome.total_bytes,
                    ),
                    icon=":material/verified_user:",
                )
            else:
                st.info(text("corpus.metadata_only"), icon=":material/table_view:")
            if display_outcome.metadata_ready:
                st.badge(text("corpus.metadata_valid"), icon=":material/table_view:", color="blue")
            _render_receipts(display_outcome)
        catalog_units = (
            project_corpus_receipts(display_outcome.receipts)
            if display_outcome.corpus_ready
            else ()
        )
        can_continue = bool(catalog_units)
        if can_continue and mode is CorpusInputMode.ZIP_ARCHIVE:
            st.caption(text("corpus.zip_ready"))
        if st.button(
            text("corpus.continue_button"),
            disabled=not can_continue,
            help=text("corpus.continue_button_help"),
            width="stretch",
            key="corpus_continue",
        ):
            units = catalog_units
            metadata_result = None
            if metadata_file is not None:
                metadata_result = import_metadata_csv(
                    metadata_file.data,
                    tuple(unit.validated_file for unit in units),
                    display_label=metadata_file.display_label,
                )
            owner_key = _owner_key()
            try:
                runtime = _runtime()
                runtime.maintain()
                materialization = visit_browser_corpus_payloads(
                    mode,
                    corpus_files,
                    lambda payloads: runtime.materializations.materialize(
                        owner_key=owner_key,
                        payloads=payloads,
                    ),
                )
            except (CorpusMaterializationError, IntakeError, WebRuntimeError) as error:
                code = error.code.value
                st.error(text("corpus.materialization_error"), icon=":material/gpp_bad:")
                st.caption(text("corpus.error.reference", code=code))
            else:
                st.session_state[_FLOW_PURPOSE_KEY] = purpose.value
                st.session_state[_FLOW_INPUT_MODE_KEY] = mode.value
                st.session_state[_FLOW_CATALOG_KEY] = units
                st.session_state[_FLOW_CATALOG_HASH_KEY] = corpus_catalog_sha256(units)
                st.session_state[_FLOW_IMPORT_KEY] = metadata_result
                st.session_state[_FLOW_MATERIALIZATION_KEY] = materialization
                st.session_state[_FLOW_STAGE_KEY] = CorpusSubstage.DESCRIBE.value
                st.session_state[_PENDING_UPLOAD_CLEAR_KEY] = _upload_widget_keys(generation)
                st.session_state[_UPLOAD_GENERATION_KEY] = generation + 1
                st.rerun()
        return display_outcome


def _unit_key(unit: ValidatedCorpusUnit) -> str:
    validated = unit.validated_file
    value = f"{validated.file_label}\0{validated.content_sha256}".encode()
    return hashlib.sha256(value).hexdigest()[:12]


def _date_widgets(
    prefix: str,
    mode_label: str,
    start_label: str,
    end_label: str,
    *,
    initial: DateValue | None = None,
) -> dict[str, Any]:
    initial = initial or DateValue(mode=DateMode.UNKNOWN)
    modes = [mode.value for mode in DateMode]
    selected = st.selectbox(
        mode_label,
        options=modes,
        index=modes.index(initial.mode.value),
        format_func=_choice_label,
        key=f"{prefix}_mode",
    )
    mode = DateMode(selected)
    start = ""
    end = ""
    if mode in {DateMode.EXACT, DateMode.APPROXIMATE}:
        start = st.text_input(
            start_label,
            value=str(initial.start_year or ""),
            key=f"{prefix}_start",
        )
    elif mode is DateMode.RANGE:
        start_column, end_column = st.columns(2)
        with start_column:
            start = st.text_input(
                start_label,
                value=str(initial.start_year or ""),
                key=f"{prefix}_start",
            )
        with end_column:
            end = st.text_input(
                end_label,
                value=str(initial.end_year or ""),
                key=f"{prefix}_end",
            )
    return {"mode": mode, "start": start, "end": end}


def _render_target_notice(
    target: CorrectionTarget | None,
    group: CompletenessGroup,
) -> None:
    if target is not None and target.group is group:
        st.info(
            text("describe.correction_here", field_path=_field_label(target.field_path)),
            icon=":material/edit_location_alt:",
        )


def _render_work_editor(
    unit: ValidatedCorpusUnit,
    purpose: PurposeId,
    *,
    index: int,
    target: CorrectionTarget | None = None,
    initial: GuidedWorkInput | None = None,
) -> dict[str, Any]:
    validated = unit.validated_file
    prefix = f"draft_{_unit_key(unit)}"
    heading = text("describe.work_heading", index=index, file_label=validated.file_label)
    is_target = target is not None and guided_work_id(unit) == target.work_id
    with st.expander(heading, expanded=index == 1 or is_target):
        st.caption(
            text(
                "describe.file_metric",
                lines=unit.line_count,
                tokens=unit.token_count,
                digest=validated.content_sha256[:12],
            )
        )
        _render_target_notice(target if is_target else None, CompletenessGroup.IDENTITY)
        title_column, author_column = st.columns(2)
        with title_column:
            title_original = st.text_input(
                text("describe.title_original"),
                value=initial.title_original if initial else suggested_title(validated.file_label),
                key=f"{prefix}_title",
            )
        with author_column:
            author_name = st.text_input(
                text("describe.author_name"),
                value=initial.primary_author_name if initial else "",
                key=f"{prefix}_author",
            )
        author_column, language_column = st.columns(2)
        with author_column:
            author_kind_value = initial.author_kind.value if initial else "person"
            author_kind = st.selectbox(
                text("describe.author_kind"),
                options=list(DEFAULT_VOCABULARY.author_kinds),
                index=list(DEFAULT_VOCABULARY.author_kinds).index(author_kind_value),
                format_func=_choice_label,
                key=f"{prefix}_author_kind",
            )
        with language_column:
            language = st.text_input(
                text("describe.language"),
                value=initial.language if initial else "it",
                key=f"{prefix}_language",
            )
        _render_target_notice(target if is_target else None, CompletenessGroup.CHRONOLOGY)
        publication = _date_widgets(
            f"{prefix}_publication",
            text("describe.publication_mode"),
            text("describe.publication_start"),
            text("describe.publication_end"),
            initial=initial.first_publication if initial else None,
        )
        group_label = None
        if purpose is PurposeId.GROUP_COMPARISON:
            group_label = st.text_input(
                text("describe.group_label"),
                value=initial.group_label or "" if initial else "",
                key=f"{prefix}_group",
            )
        st.divider()
        _render_target_notice(target if is_target else None, CompletenessGroup.EDITION)
        edition_label = st.text_input(
            text("describe.edition_label"),
            value=initial.edition_label if initial else "Uploaded text edition",
            key=f"{prefix}_edition_label",
        )
        edition = _date_widgets(
            f"{prefix}_edition",
            text("describe.edition_mode"),
            text("describe.edition_start"),
            text("describe.edition_end"),
            initial=initial.edition_date if initial else None,
        )
        _render_target_notice(target if is_target else None, CompletenessGroup.CLASSIFICATION)
        genre_column, audience_column = st.columns(2)
        with genre_column:
            genre = st.selectbox(
                text("describe.genre"),
                options=list(DEFAULT_VOCABULARY.genres),
                index=list(DEFAULT_VOCABULARY.genres).index(
                    initial.genre if initial else "unknown"
                ),
                format_func=_choice_label,
                key=f"{prefix}_genre",
            )
        with audience_column:
            audience = st.selectbox(
                text("describe.audience"),
                options=list(DEFAULT_VOCABULARY.audiences),
                index=list(DEFAULT_VOCABULARY.audiences).index(
                    initial.audience if initial else "unknown"
                ),
                format_func=_choice_label,
                key=f"{prefix}_audience",
            )
        adaptation_column, collection_column = st.columns(2)
        with adaptation_column:
            adaptation = st.selectbox(
                text("describe.adaptation"),
                options=list(DEFAULT_VOCABULARY.adaptation_statuses),
                index=list(DEFAULT_VOCABULARY.adaptation_statuses).index(
                    initial.adaptation if initial else "unknown"
                ),
                format_func=_choice_label,
                key=f"{prefix}_adaptation",
            )
        with collection_column:
            collection = st.selectbox(
                text("describe.collection"),
                options=list(DEFAULT_VOCABULARY.collection_statuses),
                index=list(DEFAULT_VOCABULARY.collection_statuses).index(
                    initial.collection if initial else "independent_work"
                ),
                format_func=_choice_label,
                key=f"{prefix}_collection",
            )
        st.divider()
        _render_target_notice(target if is_target else None, CompletenessGroup.SOURCE)
        source_type = st.selectbox(
            text("describe.source_type"),
            options=list(DEFAULT_VOCABULARY.source_types),
            index=list(DEFAULT_VOCABULARY.source_types).index(
                initial.source_type if initial else "digital_library"
            ),
            format_func=_choice_label,
            key=f"{prefix}_source_type",
        )
        source_title = st.text_input(
            text("describe.source_title"),
            value=initial.source_title if initial else validated.file_label,
            key=f"{prefix}_source_title",
        )
        source_url = st.text_input(
            text("describe.source_url"),
            value=str(initial.source_url) if initial and initial.source_url else "",
            key=f"{prefix}_source_url",
        )
        citation = st.text_area(
            text("describe.source_citation"),
            value=initial.bibliographic_citation or "" if initial else "",
            key=f"{prefix}_citation",
            height=80,
        )
        accessed_on = None
        if source_url.strip():
            accessed_on = st.date_input(
                text("describe.source_accessed"),
                value=initial.accessed_on if initial and initial.accessed_on else date.today(),
                key=f"{prefix}_accessed",
            )
        st.divider()
        _render_target_notice(target if is_target else None, CompletenessGroup.RIGHTS)
        st.markdown(f"**{text('describe.rights_heading')}**")
        st.caption(text("describe.rights_help"))
        rights_status_value = initial.rights_status.value if initial else RightsStatus.UNKNOWN.value
        rights_status = st.selectbox(
            text("describe.rights_status"),
            options=[status.value for status in RightsStatus],
            index=[status.value for status in RightsStatus].index(rights_status_value),
            format_func=_rights_label,
            key=f"{prefix}_rights",
        )
        rights_license = None
        rights_jurisdiction = None
        if rights_status == RightsStatus.VERIFIED_OPEN.value:
            rights_column, jurisdiction_column = st.columns(2)
            with rights_column:
                rights_license = st.text_input(
                    text("describe.rights_license"),
                    value=initial.rights_license or "" if initial else "",
                    key=f"{prefix}_license",
                )
            with jurisdiction_column:
                rights_jurisdiction = st.text_input(
                    text("describe.rights_jurisdiction"),
                    value=initial.rights_jurisdiction or "" if initial else "",
                    key=f"{prefix}_jurisdiction",
                )
        rights_notes = st.text_area(
            text("describe.rights_notes"),
            value=initial.rights_notes if initial else "",
            key=f"{prefix}_rights_notes",
            height=70,
        )
    return {
        "title_original": title_original,
        "author_name": author_name,
        "author_kind": author_kind,
        "language": language,
        "publication": publication,
        "group_label": group_label,
        "edition_label": edition_label,
        "edition": edition,
        "genre": genre,
        "audience": audience,
        "adaptation": adaptation,
        "collection": collection,
        "source_type": source_type,
        "source_title": source_title,
        "source_url": source_url,
        "citation": citation,
        "accessed_on": accessed_on,
        "rights_status": rights_status,
        "rights_license": rights_license,
        "rights_jurisdiction": rights_jurisdiction,
        "rights_notes": rights_notes,
    }


def _parse_year(value: object, field: str) -> int:
    try:
        year = int(str(value).strip())
    except ValueError as error:
        raise ValueError(text("describe.year_error", field=field)) from error
    if not 1 <= year <= 9999:
        raise ValueError(text("describe.year_error", field=field))
    return year


def _date_from_values(values: dict[str, Any], field: str) -> DateValue:
    mode = cast(DateMode, values["mode"])
    if mode is DateMode.UNKNOWN:
        return DateValue(mode=mode)
    start = _parse_year(values["start"], field)
    if mode is DateMode.RANGE:
        end = _parse_year(values["end"], field)
        return DateValue(mode=mode, start_year=start, end_year=end)
    return DateValue(mode=mode, start_year=start)


def _guided_input(unit: ValidatedCorpusUnit, values: dict[str, Any]) -> GuidedWorkInput:
    source_url_value = str(values["source_url"]).strip()
    source_url = _HTTP_URL_ADAPTER.validate_python(source_url_value) if source_url_value else None
    citation = str(values["citation"]).strip() or None
    return GuidedWorkInput(
        unit=unit,
        title_original=str(values["title_original"]).strip(),
        primary_author_name=str(values["author_name"]).strip(),
        author_kind=AuthorKind(str(values["author_kind"])),
        language=str(values["language"]).strip(),
        first_publication=_date_from_values(
            cast(dict[str, Any], values["publication"]),
            text("describe.publication_start"),
        ),
        genre=str(values["genre"]),
        audience=str(values["audience"]),
        adaptation=str(values["adaptation"]),
        collection=str(values["collection"]),
        group_label=str(values["group_label"]).strip() or None
        if values["group_label"] is not None
        else None,
        edition_label=str(values["edition_label"]).strip(),
        edition_date=_date_from_values(
            cast(dict[str, Any], values["edition"]),
            text("describe.edition_start"),
        ),
        source_type=str(values["source_type"]),
        source_title=str(values["source_title"]).strip(),
        source_url=source_url,
        bibliographic_citation=citation,
        accessed_on=cast(date | None, values["accessed_on"]) if source_url else None,
        rights_status=RightsStatus(str(values["rights_status"])),
        rights_license=str(values["rights_license"]).strip() if values["rights_license"] else None,
        rights_jurisdiction=str(values["rights_jurisdiction"]).strip()
        if values["rights_jurisdiction"]
        else None,
        rights_notes=str(values["rights_notes"]).strip(),
    )


def _validation_fields(error: ValidationError) -> str:
    fields = sorted({".".join(str(part) for part in item["loc"]) for item in error.errors()})
    return ", ".join(fields) or "metadata"


def _render_csv_issues(result: MetadataCsvImportResult) -> None:
    for issue in result.issues:
        row = issue.row_number if issue.row_number is not None else "-"
        st.error(
            text(
                "describe.csv_issue",
                row=row,
                field=issue.field_name,
                code=issue.code.value,
            )
        )
        st.caption(issue.message)
        st.caption(f"{text('review.issue_why')}: {issue.why_it_matters}")
        st.caption(f"{text('review.issue_fix')}: {issue.how_to_fix}")


def _store_inventory(
    inventory: CorpusInventory,
    report: ValidationReport,
    *,
    origin: CorpusOrigin,
) -> None:
    st.session_state[_FLOW_INVENTORY_KEY] = inventory
    st.session_state[_FLOW_REPORT_KEY] = report
    st.session_state[_FLOW_ORIGIN_KEY] = origin.value
    if origin is CorpusOrigin.CSV:
        st.session_state.pop(_FLOW_GUIDED_INPUTS_KEY, None)
    st.session_state.pop(_FLOW_CORRECTION_KEY, None)
    st.session_state.pop(_FLOW_CONFIRMATION_HASH_KEY, None)
    for session_key in tuple(st.session_state):
        if str(session_key).startswith("review_confirmation_"):
            st.session_state.pop(session_key, None)
    st.session_state[_FLOW_STAGE_KEY] = CorpusSubstage.REVIEW.value


def _render_describe_stage(purpose: PurposeId) -> None:
    units = cast(tuple[ValidatedCorpusUnit, ...], st.session_state.get(_FLOW_CATALOG_KEY, ()))
    if not units:
        _clear_documentation_state(keep_purpose=True)
        st.rerun()
    with st.container(border=True, key="describe_stage"):
        st.markdown(
            f'<div class="delta-eyebrow">{_html(text("describe.eyebrow"))}</div>',
            unsafe_allow_html=True,
        )
        st.title(text("describe.title"), anchor=False)
        st.caption(text("describe.body"))
        if st.button(text("describe.back"), icon=":material/arrow_back:"):
            _clear_documentation_state(keep_purpose=True)
            st.rerun()
        target = _correction_target()
        if target is not None:
            st.markdown(
                f"**{_html(target.work_title)} · "
                f"{_html(_choice_label(target.group.value))} · "
                f"{_html(_field_label(target.field_path))}**",
                unsafe_allow_html=True,
            )
            if _origin() is CorpusOrigin.CSV:
                st.warning(
                    text(
                        "describe.correction_csv",
                        field_path=_field_label(target.field_path),
                        work_id=target.work_id,
                    ),
                    icon=":material/table_edit:",
                )
                st.caption(text("describe.correction_csv_boundary"))
                return
            st.info(
                text(
                    "describe.correction_guided",
                    field_path=_field_label(target.field_path),
                ),
                icon=":material/edit_location_alt:",
            )
        _render_mode()
        imported = st.session_state.get(_FLOW_IMPORT_KEY)
        if isinstance(imported, MetadataCsvImportResult):
            st.subheader(text("describe.import_title"), anchor=False)
            if imported.inventory is None or imported.validation_report is None:
                st.warning(text("describe.import_blocked"), icon=":material/table_view:")
                _render_csv_issues(imported)
            elif imported.inventory.purpose is not purpose:
                st.warning(text("describe.import_blocked"), icon=":material/table_view:")
            else:
                st.success(text("describe.import_ready"), icon=":material/table_view:")
                if st.button(text("describe.import_review"), width="stretch"):
                    _store_inventory(
                        imported.inventory,
                        imported.validation_report,
                        origin=CorpusOrigin.CSV,
                    )
                    st.rerun()
        st.divider()
        st.subheader(text("describe.guided_title"), anchor=False)
        st.caption(text("describe.guided_body"))
        indexed_units = list(enumerate(units, start=1))
        if target is not None:
            indexed_units.sort(key=lambda item: guided_work_id(item[1]) != target.work_id)
        saved_inputs = st.session_state.get(_FLOW_GUIDED_INPUTS_KEY, ())
        inputs_by_work = {
            guided_work_id(item.unit): item
            for item in saved_inputs
            if isinstance(item, GuidedWorkInput)
        }
        rendered_inputs = tuple(
            (
                unit,
                _render_work_editor(
                    unit,
                    purpose,
                    index=index,
                    target=target,
                    initial=inputs_by_work.get(guided_work_id(unit)),
                ),
            )
            for index, unit in indexed_units
        )
        if st.button(
            text("describe.build_review"),
            type="primary",
            width="stretch",
            key="guided_build_review",
        ):
            try:
                guided_inputs = tuple(
                    _guided_input(unit, values) for unit, values in rendered_inputs
                )
                build = build_guided_inventory(purpose, guided_inputs)
            except ValidationError as error:
                st.error(
                    text("describe.build_error", fields=_validation_fields(error)),
                    icon=":material/error:",
                )
            except ValueError as error:
                st.error(
                    text("describe.build_error", fields=str(error)),
                    icon=":material/error:",
                )
            else:
                st.session_state[_FLOW_GUIDED_INPUTS_KEY] = guided_inputs
                _store_inventory(
                    build.inventory,
                    build.validation_report,
                    origin=CorpusOrigin.GUIDED,
                )
                st.rerun()


def _date_label(value: DateValue) -> str:
    if value.mode is DateMode.UNKNOWN:
        return text("review.timeline_unknown")
    if value.mode is DateMode.RANGE:
        return f"{value.start_year}–{value.end_year} ({_choice_label(value.mode.value)})"
    return f"{value.start_year} ({_choice_label(value.mode.value)})"


def _timeline_edition_label(item: TimelineDatum) -> str:
    if not item.editions:
        return text("review.timeline_unresolved")
    value = "; ".join(
        f"{edition.edition_label} · {_date_label(edition.edition_date)}"
        for edition in item.editions
    )
    return value if len(item.editions) == 1 else f"{text('review.timeline_conflict')}: {value}"


def _timeline_source_label(item: TimelineDatum) -> str:
    if not item.sources:
        return text("review.timeline_unresolved")
    value = "; ".join(
        f"{source.source_title} · {source.source_type_label}" for source in item.sources
    )
    return value if len(item.sources) == 1 else f"{text('review.timeline_conflict')}: {value}"


def _render_timeline(projection: CorpusReviewProjection) -> None:
    st.subheader(text("review.timeline_title"), anchor=False)
    st.caption(text("review.timeline_body"))
    items_by_key = {item.row_key: item for item in projection.timeline}
    selected_key = st.radio(
        text("review.timeline_selector"),
        options=list(items_by_key),
        index=0,
        format_func=lambda row_key: (
            f"{_date_label(items_by_key[row_key].first_publication)} · "
            f"{items_by_key[row_key].work_title}"
        ),
        key=f"review_timeline_selector_{projection.inventory_sha256[:12]}",
        horizontal=True,
        label_visibility="collapsed",
    )
    selected = items_by_key[selected_key]
    selected_authors = ", ".join(selected.author_names) or text("review.timeline_unresolved")
    selected_edition = _timeline_edition_label(selected)
    selected_source = _timeline_source_label(selected)
    detail_items = (
        ("First publication", _date_label(selected.first_publication)),
        ("Date certainty", _choice_label(selected.first_publication.mode.value)),
        ("Analyzed edition", selected_edition),
        ("Genre", selected.genre_label),
        ("Audience", selected.audience_label),
        ("Acquisition source", selected_source),
        ("Language", selected.language),
        ("Contributors", selected_authors),
    )
    st.markdown(
        '<section class="delta-timeline-detail" aria-live="polite" '
        f'data-row-key="{_html(selected.row_key)}">'
        f"<h3>{_html(selected.work_title)}</h3><dl>"
        + "".join(
            f"<div><dt>{_html(label)}</dt><dd>{_html(value)}</dd></div>"
            for label, value in detail_items
        )
        + "</dl></section>",
        unsafe_allow_html=True,
    )
    rows = []
    for item in projection.timeline:
        selected_state = ' aria-current="true"' if item.row_key == selected.row_key else ""
        rows.append(
            f'<tr data-row-key="{_html(item.row_key)}"{selected_state}>'
            f'<th scope="row">{_html(item.work_title)}</th>'
            f"<td>{_html(_date_label(item.first_publication))}</td>"
            f"<td>{_html(_choice_label(item.first_publication.mode.value))}</td>"
            f"<td>{_html(_timeline_edition_label(item))}</td>"
            f"<td>{_html(item.genre_label)}</td>"
            f"<td>{_html(item.audience_label)}</td>"
            f"<td>{_html(_timeline_source_label(item))}</td></tr>"
        )
    _render_table_scroll_note("review.table_scroll")
    st.markdown(
        '<div class="delta-table-scroll" role="region" '
        f'aria-label="{_html(text("review.timeline_table"))}" tabindex="0">'
        '<table class="delta-review-table delta-timeline-table">'
        f"<caption>{_html(text('review.timeline_table'))}</caption>"
        '<thead><tr><th scope="col">Work</th><th scope="col">First publication</th>'
        '<th scope="col">Certainty</th><th scope="col">Analyzed edition</th>'
        '<th scope="col">Genre</th><th scope="col">Audience</th>'
        '<th scope="col">Acquisition source</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_composition(projection: CorpusReviewProjection) -> None:
    st.subheader(text("review.composition_title"), anchor=False)
    st.caption(text("review.composition_body"))
    bars = []
    table_rows = []
    for item in projection.composition:
        share = 100 * item.work_count / item.corpus_work_count
        row_key = f"{item.dimension.value}:{item.category_value}"
        bars.append(
            '<div class="delta-composition-row" '
            f'data-row-key="{_html(row_key)}" data-count="{item.work_count}">'
            f'<span class="delta-composition-dimension">{_html(item.dimension_label)}</span>'
            f'<span class="delta-composition-label">{_html(item.category_label)}</span>'
            '<span class="delta-bar-track">'
            f'<span class="delta-bar-fill" style="--delta-share: {share:.4f}%"></span>'
            "</span>"
            f'<span class="delta-composition-count">{item.work_count} of '
            f"{item.corpus_work_count}</span></div>"
        )
        table_rows.append(
            f'<tr data-row-key="{_html(row_key)}">'
            f'<th scope="row">{_html(item.dimension_label)}</th>'
            f"<td>{_html(item.category_label)}</td>"
            f"<td>{item.work_count}</td>"
            f"<td>{share:.2f}%</td></tr>"
        )
    _render_table_scroll_note("review.table_scroll")
    st.markdown(
        '<div class="delta-composition-bars" aria-hidden="true">' + "".join(bars) + "</div>"
        '<div class="delta-table-scroll" role="region" '
        f'aria-label="{_html(text("review.composition_table"))}" tabindex="0">'
        '<table class="delta-review-table delta-composition-table">'
        f"<caption>{_html(text('review.composition_table'))}</caption>"
        '<thead><tr><th scope="col">Dimension</th><th scope="col">Category</th>'
        '<th scope="col">Works</th><th scope="col">Share</th></tr></thead><tbody>'
        + "".join(table_rows)
        + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_completeness(projection: CorpusReviewProjection) -> None:
    st.subheader(text("review.completeness_title"), anchor=False)
    st.caption(text("review.completeness_body"))
    rows_by_key: dict[str, dict[CompletenessGroup, Any]] = {}
    for item in projection.completeness:
        rows_by_key.setdefault(item.row_key, {})[item.group] = item
    body = []
    for row_key, groups in rows_by_key.items():
        first = groups[CompletenessGroup.IDENTITY]
        cells = []
        for group in CompletenessGroup:
            item = groups[group]
            fields = (
                ", ".join(dict.fromkeys(_field_label(path) for path in item.field_paths))
                if item.field_paths
                else text("review.completeness_no_field")
            )
            status_label = _choice_label(item.status.value)
            cells.append(
                f'<td class="delta-completeness-cell delta-status-{item.status.value}" '
                f'data-group="{item.group.value}" data-status="{item.status.value}">'
                f"<strong>{_html(status_label)}</strong>"
                f"<span>{_html(item.summary)}</span>"
                f"<small>{_html(text('review.completeness_fields'))}: "
                f"{_html(fields)}</small></td>"
            )
        body.append(
            f'<tr data-row-key="{_html(row_key)}">'
            f'<th scope="row">{_html(first.work_title)}</th>' + "".join(cells) + "</tr>"
        )
    headers = "".join(
        f'<th scope="col">{_html(_choice_label(group.value))}</th>' for group in CompletenessGroup
    )
    raw_details = "".join(
        f"<li><strong>{_html(item.work_title)} · "
        f"{_html(_choice_label(item.group.value))}</strong>: "
        f"{_html(', '.join(item.field_paths) or text('review.completeness_no_field'))}"
        + (
            " · " + _html(", ".join(code.value for code in item.issue_codes))
            if item.issue_codes
            else ""
        )
        + "</li>"
        for item in projection.completeness
        if item.field_paths or item.issue_codes
    )
    _render_table_scroll_note("review.table_scroll")
    st.markdown(
        '<div class="delta-table-scroll" role="region" '
        f'aria-label="{_html(text("review.completeness_title"))}" tabindex="0">'
        '<table class="delta-review-table delta-completeness-table">'
        f"<caption>{_html(text('review.completeness_title'))}</caption>"
        f'<thead><tr><th scope="col">Work</th>{headers}</tr></thead><tbody>'
        + "".join(body)
        + "</tbody></table></div>"
        + (
            '<details class="delta-tech"><summary>'
            f"{_html(text('review.technical_details'))}</summary>"
            f'<div class="delta-tech-body"><ul>{raw_details}</ul></div></details>'
            if raw_details
            else ""
        ),
        unsafe_allow_html=True,
    )
    targets = tuple(
        CorrectionTarget(
            row_key=item.row_key,
            work_id=item.work_id,
            work_title=item.work_title,
            group=item.group,
            field_path=field_path,
        )
        for item in projection.completeness
        if item.status is not CompletenessStatus.COMPLETE
        for field_path in item.field_paths
    )
    if targets:
        st.markdown(f"**{text('review.corrections_title')}**")
        st.caption(text("review.corrections_body"))
        selected_index = st.selectbox(
            text("review.corrections_label"),
            options=list(range(len(targets))),
            format_func=lambda index: (
                f"{targets[index].work_title} · "
                f"{_choice_label(targets[index].group.value)} · "
                f"{_field_label(targets[index].field_path)}"
            ),
            key=f"review_correction_target_{projection.inventory_sha256[:12]}",
        )
        if st.button(
            text("review.corrections_edit"),
            icon=":material/edit_location_alt:",
            key="review_edit_selected_field",
            width="stretch",
        ):
            st.session_state[_FLOW_CORRECTION_KEY] = targets[selected_index]
            st.session_state[_FLOW_STAGE_KEY] = CorpusSubstage.DESCRIBE.value
            st.rerun()


def _render_rights_matrix(inventory: CorpusInventory) -> None:
    st.subheader(text("review.rights_title"), anchor=False)
    st.caption(text("review.rights_body"))
    rights = {record.asset_id: record for record in inventory.rights}
    works = {record.work_id: record.title_original for record in inventory.works}
    body = []
    for asset in sorted(inventory.assets, key=lambda item: item.file_label.casefold()):
        record = rights[asset.asset_id]
        permissions = record.permissions
        cells = (
            permissions.upload.value,
            permissions.analysis.value,
            permissions.export.value,
            permissions.public_redistribution.value,
        )
        body.append(
            "<tr>"
            f'<th scope="row">{_html(works[asset.work_id])}</th>'
            + "".join(f"<td>{_html(_choice_label(value))}</td>" for value in cells)
            + "</tr>"
        )
    _render_table_scroll_note("review.table_scroll")
    st.markdown(
        '<div class="delta-table-scroll" role="region" '
        f'aria-label="{_html(text("review.rights_title"))}" tabindex="0">'
        '<table class="delta-review-table">'
        f"<caption>{_html(text('review.rights_title'))}</caption>"
        '<thead><tr><th scope="col">Work</th><th scope="col">Upload</th>'
        '<th scope="col">Analysis</th><th scope="col">Export</th>'
        '<th scope="col">Public redistribution</th></tr></thead><tbody>'
        + "".join(body)
        + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _issue_affected_label(issue: Any, inventory: CorpusInventory) -> str:
    entity_id = str(issue.entity_id or "")
    entity_type = getattr(issue.entity_type, "value", issue.entity_type)
    if not entity_id:
        return _choice_label(entity_type)
    if entity_type == "author":
        author = next((item for item in inventory.authors if item.author_id == entity_id), None)
        return author.display_name if author is not None else entity_id
    if entity_type == "work":
        work = next((item for item in inventory.works if item.work_id == entity_id), None)
        return work.title_original if work is not None else entity_id
    if entity_type == "edition":
        edition = next((item for item in inventory.editions if item.edition_id == entity_id), None)
        if edition is not None:
            work = next((item for item in inventory.works if item.work_id == edition.work_id), None)
            title = work.title_original if work is not None else edition.work_id
            return f"{title} · {edition.edition_label}"
    if entity_type == "source":
        source = next((item for item in inventory.sources if item.source_id == entity_id), None)
        return source.title if source is not None else entity_id
    if entity_type in {"asset", "rights"}:
        asset = next((item for item in inventory.assets if item.asset_id == entity_id), None)
        return asset.file_label if asset is not None else entity_id
    return entity_id


def _render_issues(report: ValidationReport, inventory: CorpusInventory) -> None:
    st.subheader(text("review.issues_title"), anchor=False)
    if not report.issues:
        st.success(text("review.no_issues"), icon=":material/task_alt:")
        return
    grouped: dict[tuple[str, str, str, str, str], list[Any]] = {}
    for issue in report.issues:
        key = (
            issue.code.value,
            issue.severity.value,
            issue.message,
            issue.why_it_matters,
            issue.how_to_fix,
        )
        grouped.setdefault(key, []).append(issue)
    rows = []
    for (code, severity, message, why, fix), issues in grouped.items():
        affected = tuple(dict.fromkeys(_issue_affected_label(issue, inventory) for issue in issues))
        technical = "".join(
            "<li>"
            f"<code>{_html(code)}</code> · "
            f"<code>{_html(getattr(issue.entity_type, 'value', issue.entity_type))}:"
            f"{_html(issue.entity_id or 'corpus')}</code> · "
            f"<code>{_html(issue.field_path)}</code>"
            "</li>"
            for issue in issues
        )
        rows.append(
            f'<li class="delta-issue delta-issue-{_html(severity)}">'
            '<div class="delta-issue-heading">'
            f'<span class="delta-issue-count">'
            f"{_html(text('review.issue_count', count=len(issues)))}</span>"
            f'<span class="delta-issue-severity">{_html(severity)}</span>'
            f"<strong>{_html(message)}</strong></div>"
            f"<span><b>{_html(text('review.issue_affected'))}:</b> "
            f"{_html(', '.join(affected))}</span>"
            f"<span><b>{_html(text('review.issue_why'))}:</b> {_html(why)}</span>"
            f"<span><b>{_html(text('review.issue_fix'))}:</b> {_html(fix)}</span>"
            '<details class="delta-tech"><summary>'
            f"{_html(text('review.technical_details'))}</summary>"
            f'<div class="delta-tech-body"><ul>{technical}</ul></div></details></li>'
        )
    st.markdown('<ul class="delta-issues">' + "".join(rows) + "</ul>", unsafe_allow_html=True)


def _render_confirmation(
    projection: CorpusReviewProjection,
    report: ValidationReport,
) -> bool:
    st.subheader(text("review.confirmation_title"), anchor=False)
    st.caption(text("review.confirmation_body"))
    stored = st.session_state.get(_FLOW_CONFIRMATION_HASH_KEY) == projection.inventory_sha256
    checked = st.checkbox(
        text("review.confirmation_checkbox"),
        value=stored and not report.blocked,
        disabled=report.blocked,
        help=text("review.confirmation_help"),
        key=f"review_confirmation_{projection.inventory_sha256[:12]}",
    )
    confirmed = checked and not report.blocked
    if confirmed:
        st.session_state[_FLOW_CONFIRMATION_HASH_KEY] = projection.inventory_sha256
        st.success(text("review.confirmation_recorded"), icon=":material/fact_check:")
    else:
        if stored:
            st.session_state.pop(_FLOW_CONFIRMATION_HASH_KEY, None)
        if report.blocked:
            st.error(text("review.confirmation_blocked"), icon=":material/block:")
        else:
            st.info(text("review.confirmation_required"), icon=":material/pending_actions:")
    return confirmed


def _render_downloads(
    inventory: CorpusInventory,
    report: ValidationReport,
    projection: CorpusReviewProjection,
) -> None:
    st.subheader(text("review.downloads_title"), anchor=False)
    inventory_json = canonical_json_bytes(inventory.model_dump(mode="json")) + b"\n"
    report_json = canonical_json_bytes(report.model_dump(mode="json")) + b"\n"
    metadata_csv = None
    try:
        metadata_csv = export_metadata_csv(inventory)
    except MetadataCsvExportError:
        st.warning(text("review.export_unavailable"))
    composition_csv = None
    completeness_csv = None
    try:
        composition_csv = export_composition_csv(projection)
        completeness_csv = export_completeness_csv(projection)
    except ReviewProjectionError:
        st.warning(text("review.review_export_unavailable"))
    first, second, third = st.columns(3)
    with first:
        st.download_button(
            text("review.download_inventory"),
            data=inventory_json,
            file_name="delta-corpus-inventory.json",
            mime="application/json",
            width="stretch",
        )
    with second:
        st.download_button(
            text("review.download_validation"),
            data=report_json,
            file_name="delta-corpus-validation.json",
            mime="application/json",
            width="stretch",
        )
    with third:
        st.download_button(
            text("review.download_metadata"),
            data=metadata_csv or b"",
            file_name="delta-corpus-metadata.csv",
            mime="text/csv",
            disabled=metadata_csv is None,
            width="stretch",
        )
    composition_column, completeness_column = st.columns(2)
    with composition_column:
        st.download_button(
            text("review.download_composition"),
            data=composition_csv or b"",
            file_name="delta-corpus-composition.csv",
            mime="text/csv",
            disabled=composition_csv is None,
            width="stretch",
        )
    with completeness_column:
        st.download_button(
            text("review.download_completeness"),
            data=completeness_csv or b"",
            file_name="delta-metadata-completeness.csv",
            mime="text/csv",
            disabled=completeness_csv is None,
            width="stretch",
        )


def _review_issue_type_count(report: ValidationReport) -> int:
    return len({issue.code for issue in report.issues if issue.severity is IssueSeverity.WARNING})


def _review_readiness_detail(inventory: CorpusInventory, report: ValidationReport) -> str:
    readiness = report.readiness
    if inventory.purpose is PurposeId.STYLE_OVER_TIME and readiness.exploratory:
        return text(
            "review.style_over_time_exploratory",
            works_label=_review_count_label(
                readiness.independent_work_count,
                "independent work",
                "independent works",
            ),
            points_label=_review_count_label(
                readiness.chronology_point_count,
                "chronology point",
                "chronology points",
            ),
        )
    return " ".join((text("review.ready"), text("review.other_purposes_separate")))


def _review_count_label(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _render_review_readiness(
    inventory: CorpusInventory,
    report: ValidationReport,
    purpose_label: str,
) -> None:
    readiness = report.readiness
    if report.blocked:
        st.error(text("review.blocked"), icon=":material/block:")
    else:
        exploratory = inventory.purpose is PurposeId.STYLE_OVER_TIME and readiness.exploratory
        blocker_summary = _review_count_label(readiness.blocker_count, "blocker", "blockers")
        warning_summary = _review_count_label(readiness.warning_count, "warning", "warnings")
        rights_summary = _review_count_label(
            readiness.rights_restriction_count, "rights limit", "rights limits"
        )
        band_state = " is-exploratory" if exploratory else ""
        band_icon = "&#9888;" if exploratory else "&#10003;"
        readiness_title = text(
            "review.exploratory_for_purpose" if exploratory else "review.ready_for_purpose",
            purpose=purpose_label,
        )
        st.markdown(
            f'<section class="delta-readiness-band{band_state}" role="status" '
            'aria-live="polite" aria-atomic="true" '
            'aria-labelledby="delta-readiness-title">'
            f'<span class="delta-readiness-icon" aria-hidden="true">{band_icon}</span>'
            '<div class="delta-readiness-copy">'
            '<strong id="delta-readiness-title">'
            f"{_html(readiness_title)}</strong>"
            f"<p>{_html(_review_readiness_detail(inventory, report))}</p></div>"
            '<div class="delta-readiness-counts">'
            f"<span>{_html(blocker_summary)}</span>"
            f"<span>{_html(warning_summary)}</span>"
            f"<span>{_html(rights_summary)}</span>"
            "</div></section>",
            unsafe_allow_html=True,
        )

    chronology_shortfall = (
        inventory.purpose is PurposeId.STYLE_OVER_TIME and readiness.chronology_point_count < 3
    )
    if inventory.purpose is not PurposeId.STYLE_OVER_TIME:
        chronology_note = text("review.metric.chronology_not_required")
    elif chronology_shortfall:
        chronology_note = text("review.metric.chronology_note")
    else:
        chronology_note = text("review.metric.documented")
    warning_types = _review_issue_type_count(report)
    rights_note = (
        text("review.metric.rights_note")
        if readiness.rights_restriction_count
        else text("review.metric.none_documented")
    )
    tiles = (
        ("review.metric.works", readiness.independent_work_count, "", ""),
        (
            "review.metric.chronology",
            readiness.chronology_point_count,
            chronology_note,
            " is-warning" if chronology_shortfall else "",
        ),
        (
            "review.metric.blockers",
            readiness.blocker_count,
            "",
            " is-blocked" if readiness.blocker_count else "",
        ),
        (
            "review.metric.warnings",
            readiness.warning_count,
            _review_count_label(warning_types, "issue type", "issue types"),
            " is-warning" if readiness.warning_count else "",
        ),
        (
            "review.metric.rights",
            readiness.rights_restriction_count,
            rights_note,
            " is-warning" if readiness.rights_restriction_count else "",
        ),
    )
    tile_markup = "".join(
        f'<div class="delta-review-metric{state}">'
        f"<span>{_html(text(label_key))}</span><strong>{value}</strong>"
        + (f"<small>{_html(note)}</small>" if note else "")
        + "</div>"
        for label_key, value, note, state in tiles
    )
    st.markdown(
        '<section class="delta-review-metrics" '
        f'aria-label="{_html(text("review.metrics_summary"))}">{tile_markup}</section>',
        unsafe_allow_html=True,
    )


def _render_review_stage() -> None:
    inventory = st.session_state.get(_FLOW_INVENTORY_KEY)
    report = st.session_state.get(_FLOW_REPORT_KEY)
    if not isinstance(inventory, CorpusInventory) or not isinstance(report, ValidationReport):
        _clear_documentation_state(keep_purpose=True)
        st.rerun()
    with st.container(key="review_stage"):
        st.markdown(
            f'<div class="delta-eyebrow">{_html(text("review.eyebrow"))}</div>',
            unsafe_allow_html=True,
        )
        st.title(text("review.title"), anchor=False)
        purpose_spec = PURPOSE_BY_ID[inventory.purpose.value]
        purpose_label = _purpose_label(inventory.purpose.value)
        st.markdown(
            '<div class="delta-context-strip delta-selected-purpose">'
            f"<span>{_html(text('review.selected_purpose', purpose=purpose_label))}</span>"
            f"<p>{_html(text(purpose_spec.question_key))}</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(text("review.body"))
        try:
            projection = build_review_projection(inventory, report)
        except ReviewProjectionError:
            st.error(text("review.projection_unavailable"), icon=":material/block:")
            st.info(text("review.analysis_locked"), icon=":material/lock:")
            return
        _render_review_readiness(inventory, report, purpose_label)
        _render_issues(report, inventory)
        _render_completeness(projection)
        _render_timeline(projection)
        _render_composition(projection)
        _render_rights_matrix(inventory)
        confirmed = _render_confirmation(projection, report)
        edit_column, reset_column = st.columns(2)
        with edit_column:
            if st.button(text("review.edit"), icon=":material/edit:", width="stretch"):
                st.session_state.pop(_FLOW_CORRECTION_KEY, None)
                st.session_state.pop(_FLOW_CONFIRMATION_HASH_KEY, None)
                st.session_state[_FLOW_STAGE_KEY] = CorpusSubstage.DESCRIBE.value
                st.rerun()
        with reset_column:
            if st.button(text("review.start_over"), icon=":material/restart_alt:", width="stretch"):
                _clear_documentation_state(keep_purpose=False)
                st.rerun()
        _render_downloads(inventory, report, projection)
        st.info(
            text("review.analysis_locked" if confirmed else "review.analysis_locked_confirmation"),
            icon=":material/lock:",
        )
        materialization = st.session_state.get(_FLOW_MATERIALIZATION_KEY)
        if confirmed and not report.blocked:
            if isinstance(materialization, CorpusMaterializationReceipt):
                st.button(
                    text("review.continue_prepare"),
                    icon=":material/arrow_forward:",
                    type="primary",
                    width="stretch",
                    key="review_continue_prepare",
                    on_click=_set_stage,
                    args=(CorpusSubstage.PREPARE,),
                )
            else:
                st.warning(text("review.temporary_corpus_missing"), icon=":material/timer_off:")


def _preparation_document_id(inventory_digest: str, asset_id: str) -> str:
    material = (
        b"delta-lemmata\x00preparation-document-id\x00v1\x00"
        + inventory_digest.encode("ascii")
        + b"\x00"
        + asset_id.encode("utf-8", errors="strict")
    )
    return "doc_" + hashlib.sha256(material).hexdigest()


def _build_preparation_annotations(
    inventory: CorpusInventory,
    selections: tuple[PreparationSelection, ...],
) -> CorpusAnalysisAnnotationsV1:
    digest = inventory_sha256(inventory)
    assets = {asset.asset_id: asset for asset in inventory.assets}
    if len(selections) != len(assets) or {item.asset_id for item in selections} != set(assets):
        raise ValueError("preparation selections do not match the corpus assets")
    return CorpusAnalysisAnnotationsV1(
        schema_version="corpus-analysis-annotations-v1",
        inventory_sha256=digest,
        annotations=tuple(
            CorpusAnalysisAnnotation(
                document_id=_preparation_document_id(digest, selection.asset_id),
                asset_id=selection.asset_id,
                work_id=selection.work_id,
                analysis_role=selection.analysis_role,
                text_unit=TextUnit.INDEPENDENT_WORK,
                parent_work_id=None,
                ocr_status=selection.ocr_status,
                paratext_status=selection.paratext_status,
                preupload_curation_note=selection.curation_note,
            )
            for selection in selections
        ),
    )


def _render_preparation_selections(
    inventory: CorpusInventory,
) -> tuple[PreparationSelection, ...]:
    works = {work.work_id: work for work in inventory.works}
    selections: list[PreparationSelection] = []
    st.subheader(text("prepare.decisions_title"), anchor=False)
    st.caption(text("prepare.decisions_body"))
    role_options = [AnalysisRole.KNOWN.value]
    if inventory.purpose is PurposeId.TEXT_PROXIMITY:
        role_options.append(AnalysisRole.UNKNOWN.value)
    for index, asset in enumerate(inventory.assets, start=1):
        work = works[asset.work_id]
        label = text(
            "prepare.work_label",
            index=index,
            title=work.title_original,
            file=asset.file_label,
        )
        with st.expander(label, expanded=index == 1):
            role = st.selectbox(
                text("prepare.role.label"),
                options=role_options,
                format_func=_analysis_role_label,
                key=f"prep_role_{asset.asset_id}",
                help=text("prepare.role.help"),
            )
            st.caption(text(f"prepare.role.{role}.body"))
            first, second = st.columns(2)
            with first:
                ocr = st.selectbox(
                    text("prepare.ocr.label"),
                    options=[status.value for status in OcrStatus],
                    index=[status.value for status in OcrStatus].index(OcrStatus.UNKNOWN.value),
                    format_func=_ocr_label,
                    key=f"prep_ocr_{asset.asset_id}",
                    help=text("prepare.ocr.help"),
                )
            with second:
                paratext = st.selectbox(
                    text("prepare.paratext.label"),
                    options=[status.value for status in ParatextStatus],
                    index=[status.value for status in ParatextStatus].index(
                        ParatextStatus.UNKNOWN.value
                    ),
                    format_func=_paratext_label,
                    key=f"prep_paratext_{asset.asset_id}",
                    help=text("prepare.paratext.help"),
                )
            note_value = st.text_area(
                text("prepare.note.label"),
                key=f"prep_note_{asset.asset_id}",
                help=text("prepare.note.help"),
                max_chars=2_000,
            ).strip()
            st.caption(text("prepare.unit_fixed"))
        selections.append(
            PreparationSelection(
                asset_id=asset.asset_id,
                work_id=asset.work_id,
                analysis_role=AnalysisRole(role),
                ocr_status=OcrStatus(ocr),
                paratext_status=ParatextStatus(paratext),
                curation_note=note_value or None,
            )
        )
    return tuple(selections)


def _finding_measure(finding: CorpusHealthFinding) -> str | None:
    values: list[str] = []
    if finding.observed_count is not None:
        values.append(text("prepare.finding.observed_count", value=finding.observed_count))
    if finding.threshold_count is not None:
        values.append(text("prepare.finding.threshold_count", value=finding.threshold_count))
    if finding.observed_ratio is not None:
        values.append(text("prepare.finding.observed_ratio", value=finding.observed_ratio))
    if finding.threshold_ratio is not None:
        values.append(text("prepare.finding.threshold_ratio", value=finding.threshold_ratio))
    return " · ".join(values) or None


def _render_health_finding(finding: CorpusHealthFinding) -> None:
    key = f"prepare.finding.{finding.code.value}"
    icon = {
        "blocker": ":material/block:",
        "strong_warning": ":material/warning:",
        "note": ":material/info:",
    }[finding.severity.value]
    with st.container(border=True):
        st.markdown(f"**{text(f'{key}.title')}**")
        st.caption(text(f"{key}.body"))
        st.caption(f"{text('prepare.finding.action_label')}: {text(f'{key}.action')}")
        measure = _finding_measure(finding)
        if measure is not None:
            st.caption(f"{icon} {measure}")


def _render_panel_boundary(copy_key: str) -> None:
    st.caption(f"**{text('prepare.panel.boundary_label')}:** {text(copy_key)}")


def _chronology_label(item: ConfoundDatum) -> str:
    if item.chronology_mode is DateMode.EXACT and item.chronology_start_year is not None:
        return text("prepare.confound.chronology.exact", year=item.chronology_start_year)
    if item.chronology_mode is DateMode.APPROXIMATE and item.chronology_start_year is not None:
        return text("prepare.confound.chronology.approximate", year=item.chronology_start_year)
    if (
        item.chronology_mode is DateMode.RANGE
        and item.chronology_start_year is not None
        and item.chronology_end_year is not None
    ):
        return text(
            "prepare.confound.chronology.range",
            start=item.chronology_start_year,
            end=item.chronology_end_year,
        )
    return text("prepare.confound.chronology.unknown")


def _overlap_code_label(code: CorpusHealthFindingCode) -> str:
    return text(f"prepare.overlap.code.{code.value}")


def _overlap_measure(item: OverlapDatum) -> str:
    if item.code is CorpusHealthFindingCode.EXACT_DUPLICATE:
        return text("prepare.overlap.hash_match")
    values: list[str] = []
    if item.observed_count is not None:
        values.append(text("prepare.overlap.tokens", count=item.observed_count))
    if item.observed_ratio is not None:
        values.append(text("prepare.overlap.ratio", ratio=item.observed_ratio))
    return " · ".join(values) or text("prepare.overlap.no_measure")


def _table_value(value: object) -> str:
    if isinstance(value, bool):
        return text("table.yes" if value else "table.no")
    return str(value)


def _render_record_table(
    rows: Sequence[Mapping[str, object]],
    *,
    label: str,
) -> None:
    headers = tuple(rows[0])
    body = []
    for row in rows:
        body.append(
            "<tr>"
            + "".join(
                (
                    f'<th scope="row">{_html(_table_value(row[header]))}</th>'
                    if index == 0
                    else f"<td>{_html(_table_value(row[header]))}</td>"
                )
                for index, header in enumerate(headers)
            )
            + "</tr>"
        )
    safe_label = _html(label)
    st.markdown(
        '<div class="delta-table-scroll" role="region" '
        f'aria-label="{safe_label}" tabindex="0">'
        '<table class="delta-review-table">'
        f"<caption>{safe_label}</caption><thead><tr>"
        + "".join(f'<th scope="col">{_html(header)}</th>' for header in headers)
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_evidence_bars(
    rows: Sequence[tuple[str, Sequence[tuple[str, int]]]],
) -> None:
    maximum = max(value for _label, series in rows for _name, value in series) or 1
    rendered_rows = []
    for label, series in rows:
        rendered_series = []
        for index, (name, value) in enumerate(series):
            share = 100 * value / maximum
            rendered_series.append(
                f'<div class="delta-evidence-bar-item" data-series="{index}">'
                f"<span>{_html(name)}</span>"
                '<span class="delta-evidence-bar-track">'
                f'<span class="delta-evidence-bar-fill" style="--delta-share: {share:.4f}%">'
                "</span></span>"
                f'<span class="delta-evidence-bar-value">{value}</span></div>'
            )
        rendered_rows.append(
            '<div class="delta-evidence-bar-row">'
            f'<span class="delta-evidence-bar-label">{_html(label)}</span>'
            '<div class="delta-evidence-bar-series">' + "".join(rendered_series) + "</div></div>"
        )
    st.markdown(
        '<div class="delta-evidence-bars" aria-hidden="true">' + "".join(rendered_rows) + "</div>",
        unsafe_allow_html=True,
    )


def _render_preparation_outcome(
    inventory: CorpusInventory,
    annotations: CorpusAnalysisAnnotationsV1,
    outcome: PreparationOutcome,
) -> bool:
    health = outcome.health_report
    try:
        projection = build_corpus_health_projection(
            inventory=inventory,
            annotations=annotations,
            manifest=outcome.manifest,
            health_report=health,
        )
        work_csv = export_work_preparation_csv(projection)
        confound_csv = export_confound_matrix_csv(projection)
        findings_csv = export_health_findings_csv(projection)
        capacity_csv = export_feature_capacity_csv(projection)
    except CorpusHealthProjectionError as error:
        st.error(text("prepare.projection_error"), icon=":material/link_off:")
        st.caption(text("corpus.error.reference", code=error.code.value))
        return False

    if health.readiness is CorpusHealthReadiness.READY:
        st.success(text("prepare.ready"), icon=":material/check_circle:")
    else:
        st.error(text("prepare.blocked"), icon=":material/block:")
    st.caption(text("prepare.preflight_scope"))
    first, second, third, fourth, fifth = st.columns(5)
    first.metric(text("prepare.metric.works"), health.independent_work_count)
    second.metric(text("prepare.metric.known"), health.known_independent_work_count)
    third.metric(text("prepare.metric.features"), health.candidate_feature_count)
    fourth.metric(text("prepare.metric.blockers"), health.blocker_count)
    fifth.metric(text("prepare.metric.warnings"), health.strong_warning_count)

    length_rows = [
        {
            text("prepare.table.work"): item.display_label,
            text("prepare.table.tokens"): item.token_count,
            text("prepare.table.unique"): item.unique_token_count,
        }
        for item in projection.work_preparation
    ]
    st.subheader(text("prepare.length_title"), anchor=False)
    st.caption(text("prepare.length_body"))
    _render_evidence_bars(
        tuple(
            (
                item.display_label,
                ((text("prepare.table.tokens"), item.token_count),),
            )
            for item in projection.work_preparation
        )
    )
    _render_record_table(length_rows, label=text("prepare.length_title"))
    _render_panel_boundary("prepare.length_boundary")

    transformation_rows = [
        {
            text("prepare.table.work"): item.display_label,
            text("prepare.transform.lowercase"): item.lowercase_source_count,
            text("prepare.transform.separators"): item.separator_source_count,
            text("prepare.transform.newlines"): item.newline_replacement_count,
            text("prepare.transform.raw_bytes"): item.raw_byte_count,
            text("prepare.transform.prepared_bytes"): item.prepared_byte_count,
            text("prepare.transform.bom"): item.bom_removed,
        }
        for item in projection.work_preparation
    ]
    st.subheader(text("prepare.transform_title"), anchor=False)
    st.caption(text("prepare.transform_body"))
    _render_evidence_bars(
        tuple(
            (
                item.display_label,
                (
                    (text("prepare.transform.lowercase"), item.lowercase_source_count),
                    (text("prepare.transform.separators"), item.separator_source_count),
                    (text("prepare.transform.newlines"), item.newline_replacement_count),
                ),
            )
            for item in projection.work_preparation
        )
    )
    _render_record_table(transformation_rows, label=text("prepare.transform_title"))
    _render_panel_boundary("prepare.transform_boundary")
    st.download_button(
        text("prepare.download_work_csv"),
        data=work_csv,
        file_name="delta-work-preparation-v1.csv",
        mime="text/csv",
        icon=":material/download:",
        key="prepare_download_work_csv",
    )

    confound_rows = [
        {
            text("prepare.table.work"): item.display_label,
            text("prepare.confound.edition"): item.edition_label,
            text("prepare.confound.genre"): item.genre,
            text("prepare.confound.audience"): item.audience,
            text("prepare.confound.source"): item.source_type,
            text("prepare.confound.adaptation"): item.adaptation,
            text("prepare.confound.collection"): item.collection,
            text("prepare.confound.chronology"): _chronology_label(item),
            text("prepare.confound.ocr"): item.ocr_status,
            text("prepare.confound.paratext"): item.paratext_status,
            text("prepare.confound.curation"): text(
                "prepare.confound.disclosed"
                if item.curation_note_disclosed
                else "prepare.confound.not_disclosed"
            ),
        }
        for item in projection.confounds
    ]
    st.subheader(text("prepare.confound_title"), anchor=False)
    st.caption(text("prepare.confound_body"))
    _render_record_table(confound_rows, label=text("prepare.confound_title"))
    _render_panel_boundary("prepare.confound_boundary")
    st.download_button(
        text("prepare.download_confound_csv"),
        data=confound_csv,
        file_name="delta-confound-matrix-v1.csv",
        mime="text/csv",
        icon=":material/download:",
        key="prepare_download_confound_csv",
    )

    work_labels = {
        item.work_id: f"{item.display_label} [{item.work_id}]"
        for item in projection.work_preparation
    }
    pair_codes: dict[tuple[str, str], list[str]] = {}
    for item in projection.overlaps:
        pair_codes.setdefault(item.work_ids, []).append(_overlap_code_label(item.code))
    matrix_rows: list[dict[str, str]] = []
    for row_id, row_label in work_labels.items():
        matrix_row = {text("prepare.table.work"): row_label}
        for column_id, column_label in work_labels.items():
            if row_id == column_id:
                value = text("prepare.overlap.same_work")
            else:
                pair = tuple(sorted((row_id, column_id)))
                value = " · ".join(pair_codes.get((pair[0], pair[1]), ())) or text(
                    "prepare.overlap.not_flagged"
                )
            matrix_row[column_label] = value
        matrix_rows.append(matrix_row)

    st.subheader(text("prepare.overlap_title"), anchor=False)
    st.caption(text("prepare.overlap_body"))
    st.markdown(f"**{text('prepare.overlap.matrix_title')}**")
    _render_record_table(matrix_rows, label=text("prepare.overlap.matrix_title"))
    st.markdown(f"**{text('prepare.overlap.pairs_title')}**")
    if projection.overlaps:
        overlap_rows = [
            {
                text("prepare.overlap.left"): item.display_labels[0],
                text("prepare.overlap.right"): item.display_labels[1],
                text("prepare.overlap.check"): _overlap_code_label(item.code),
                text("prepare.overlap.observed"): _overlap_measure(item),
            }
            for item in projection.overlaps
        ]
        _render_record_table(overlap_rows, label=text("prepare.overlap.pairs_title"))
    else:
        st.info(text("prepare.overlap.none"), icon=":material/rule:")
    _render_panel_boundary("prepare.overlap_boundary")
    st.download_button(
        text("prepare.download_findings_csv"),
        data=findings_csv,
        file_name="delta-health-findings-v1.csv",
        mime="text/csv",
        icon=":material/download:",
        key="prepare_download_findings_csv",
    )

    st.subheader(text("prepare.mfw_title"), anchor=False)
    st.caption(text("prepare.mfw_body"))
    capacity_columns = st.columns(4)
    capacity_rows = []
    for column, capacity in zip(
        capacity_columns,
        projection.feature_capacity,
        strict=True,
    ):
        status_key = "prepare.mfw.available" if capacity.available else "prepare.mfw.unavailable"
        with column:
            st.metric(
                text("prepare.mfw.metric", mfw=capacity.requested_mfw),
                text(status_key),
                delta=text("prepare.mfw.features", count=capacity.available_features),
                delta_color="off",
            )
        capacity_rows.append(
            {
                text("prepare.mfw.requested"): capacity.requested_mfw,
                text("prepare.mfw.available_features"): capacity.available_features,
                text("prepare.mfw.status"): text(status_key),
            }
        )
    _render_record_table(capacity_rows, label=text("prepare.mfw_title"))
    _render_panel_boundary("prepare.mfw_boundary")
    st.download_button(
        text("prepare.download_capacity_csv"),
        data=capacity_csv,
        file_name="delta-feature-capacity-v1.csv",
        mime="text/csv",
        icon=":material/download:",
        key="prepare_download_capacity_csv",
    )

    st.subheader(text("prepare.findings_title"), anchor=False)
    st.caption(text("prepare.findings_body"))
    for finding in health.findings:
        _render_health_finding(finding)

    st.subheader(text("prepare.downloads_title"), anchor=False)
    first_download, second_download = st.columns(2)
    with first_download:
        st.download_button(
            text("prepare.download_health"),
            data=canonical_p007_json(health),
            file_name="delta-corpus-health-v1.json",
            mime="application/json",
            width="stretch",
        )
        st.download_button(
            text("prepare.download_config"),
            data=canonical_p007_json(outcome.config),
            file_name="delta-preprocessing-config-v1.json",
            mime="application/json",
            width="stretch",
        )
    with second_download:
        st.download_button(
            text("prepare.download_manifest"),
            data=canonical_p007_json(outcome.manifest),
            file_name="delta-preparation-manifest-v1.json",
            mime="application/json",
            width="stretch",
        )
        if outcome.ready_receipt is not None:
            st.download_button(
                text("prepare.download_receipt"),
                data=canonical_p007_json(outcome.ready_receipt),
                file_name="delta-analysis-preparation-receipt-v1.json",
                mime="application/json",
                width="stretch",
            )
    return True


def _render_prepare_stage() -> None:
    inventory = st.session_state.get(_FLOW_INVENTORY_KEY)
    report = st.session_state.get(_FLOW_REPORT_KEY)
    materialization = st.session_state.get(_FLOW_MATERIALIZATION_KEY)
    if (
        not isinstance(inventory, CorpusInventory)
        or not isinstance(report, ValidationReport)
        or not isinstance(materialization, CorpusMaterializationReceipt)
    ):
        _clear_documentation_state(keep_purpose=True)
        st.rerun()

    with st.container(border=True, key="prepare_stage"):
        st.markdown(
            f'<div class="delta-eyebrow">{_html(text("prepare.eyebrow"))}</div>',
            unsafe_allow_html=True,
        )
        st.title(text("prepare.title"), anchor=False)
        st.caption(text("prepare.body"))
        st.info(text("prepare.profile_summary"), icon=":material/tune:")

        outcome = st.session_state.get(_FLOW_PREPARATION_KEY)
        if isinstance(outcome, PreparationOutcome):
            annotations = st.session_state.get(_FLOW_ANNOTATIONS_KEY)
            rendered = False
            if isinstance(annotations, CorpusAnalysisAnnotationsV1):
                rendered = _render_preparation_outcome(inventory, annotations, outcome)
            else:
                st.error(text("prepare.projection_error"), icon=":material/link_off:")
            if outcome.ready_receipt is None:
                if st.button(
                    text("prepare.start_over"),
                    icon=":material/restart_alt:",
                    width="stretch",
                ):
                    _clear_documentation_state(keep_purpose=True)
                    st.rerun()
            elif rendered:
                st.info(text("prepare.parameters_next"), icon=":material/arrow_forward:")
                if st.button(
                    text("prepare.continue_parameters"),
                    type="primary",
                    icon=":material/tune:",
                    width="stretch",
                    key="prepare_continue_parameters",
                ):
                    _set_stage(CorpusSubstage.PARAMETERS)
                    st.rerun()
            return

        expected_hash = inventory_sha256(inventory)
        confirmed_hash = st.session_state.get(_FLOW_CONFIRMATION_HASH_KEY)
        if (
            report.blocked
            or report.inventory_sha256 != expected_hash
            or confirmed_hash != expected_hash
        ):
            st.warning(text("prepare.confirmation_missing"), icon=":material/rule:")
            if st.button(text("prepare.back_review"), icon=":material/arrow_back:"):
                st.session_state[_FLOW_STAGE_KEY] = CorpusSubstage.REVIEW.value
                st.rerun()
            return

        if st.button(text("prepare.back_review"), icon=":material/arrow_back:"):
            st.session_state[_FLOW_STAGE_KEY] = CorpusSubstage.REVIEW.value
            st.rerun()

        selections = _render_preparation_selections(inventory)
        if st.button(
            text("prepare.run_check"),
            type="primary",
            icon=":material/fact_check:",
            width="stretch",
            key="prepare_run_check",
        ):
            try:
                annotations = _build_preparation_annotations(inventory, selections)
                config = build_preprocessing_config(parse_custom_exclusions(None))
                preparation = _runtime().prepared_corpora.prepare(
                    owner_key=_owner_key(),
                    materialization_receipt=materialization,
                    inventory=inventory,
                    annotations=annotations,
                    config=config,
                )
            except (PreparedCorpusError, WebRuntimeError) as error:
                st.error(text("prepare.error"), icon=":material/gpp_bad:")
                st.caption(text("corpus.error.reference", code=error.code.value))
            except (ValidationError, ValueError):
                st.error(text("prepare.annotation_error"), icon=":material/error:")
            else:
                st.session_state[_FLOW_ANNOTATIONS_KEY] = annotations
                st.session_state[_FLOW_PREPARATION_KEY] = preparation
                st.rerun()


def _resolve_session_workflow(
    inventory: CorpusInventory,
    annotations: CorpusAnalysisAnnotationsV1,
) -> ResolvedWorkflowConfigV1:
    known_count = sum(
        annotation.analysis_role is AnalysisRole.KNOWN for annotation in annotations.annotations
    )
    unknown_count = sum(
        annotation.analysis_role is AnalysisRole.UNKNOWN for annotation in annotations.annotations
    )
    return resolve_guided_workflow(
        purpose=inventory.purpose,
        known_work_count=known_count,
        unknown_work_count=unknown_count,
    )


def _render_table_scroll_note(copy_key: str) -> None:
    st.markdown(
        '<p class="delta-scroll-note">'
        '<span aria-hidden="true">↔</span>'
        f"{_html(text(copy_key))}</p>",
        unsafe_allow_html=True,
    )


def _render_parameter_grid(config: ResolvedWorkflowConfigV1) -> None:
    rows = []
    for cell in config.cells:
        role = text(
            "parameters.table.reference" if cell.is_reference else "parameters.table.sensitivity"
        )
        rows.append(
            f'<tr data-reference="{str(cell.is_reference).lower()}">'
            f'<th scope="row">{cell.mfw}</th>'
            f"<td>{cell.culling_percent}%</td>"
            f"<td>{_html(text('parameters.distance.classic_delta'))}</td>"
            f"<td>{_html(role)}</td></tr>"
        )
    label = _html(text("parameters.table.label"))
    _render_table_scroll_note("results.table_scroll")
    st.markdown(
        '<div class="delta-table-scroll" role="region" '
        f'aria-label="{label}" tabindex="0">'
        '<table class="delta-review-table delta-parameter-table">'
        f"<caption>{label}</caption><thead><tr>"
        f'<th scope="col">{_html(text("parameters.table.mfw"))}</th>'
        f'<th scope="col">{_html(text("parameters.table.culling"))}</th>'
        f'<th scope="col">{_html(text("parameters.table.distance"))}</th>'
        f'<th scope="col">{_html(text("parameters.table.role"))}</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_parameter_explanations() -> None:
    with st.expander(text("parameters.learn.title"), expanded=True):
        st.markdown(f"**{text('parameters.learn.mfw.title')}**")
        st.caption(text("parameters.learn.mfw.body"))
        st.markdown(f"**{text('parameters.learn.culling.title')}**")
        st.caption(text("parameters.learn.culling.body"))
        st.markdown(f"**{text('parameters.learn.delta.title')}**")
        st.caption(text("parameters.learn.delta.body"))
        st.markdown(f"**{text('parameters.learn.reference.title')}**")
        st.caption(text("parameters.learn.reference.body"))


def _result_descriptors(
    inventory: CorpusInventory,
    preparation: PreparationOutcome,
) -> tuple[ResultDocumentDescriptor, ...]:
    receipt = preparation.ready_receipt
    if receipt is None:
        raise ValueError("result descriptors require a READY receipt")
    titles = {work.work_id: work.title_original for work in inventory.works}
    try:
        return tuple(
            ResultDocumentDescriptor(
                document_id=binding.document_id,
                title=titles[binding.work_id],
                role=DocumentRole(binding.analysis_role.value),
            )
            for binding in receipt.ordered_documents
        )
    except (KeyError, ValueError):
        raise ValueError("result descriptor binding failed") from None


def _result_status_label(cell: ResultCellV1) -> str:
    return text(f"results.cell.{cell.status.value}")


def _distance_label(value: int | float) -> str:
    return f"{float(value):.6f}"


def _render_result_status_summary(view: ResultViewV1) -> None:
    cards = []
    for cell in view.cells:
        evidence_role = text(
            "results.cell.reference" if cell.is_reference else "results.cell.sensitivity"
        )
        status_label = _result_status_label(cell)
        status_symbol = {
            ResultCellStatus.COMPLETE: "&#10003;",
            ResultCellStatus.NOT_ENOUGH_FEATURES: "!",
            ResultCellStatus.FAILED: "&times;",
        }[cell.status]
        accessible_label = _html(f"{cell.mfw} MFW, {status_label}, {evidence_role}")
        cards.append(
            f'<article class="delta-result-cell delta-result-cell-{cell.status.value}" '
            'role="listitem" '
            f'aria-label="{accessible_label}" data-mfw="{cell.mfw}" '
            f'data-status="{cell.status.value}">'
            f'<span class="delta-result-cell-icon" aria-hidden="true">{status_symbol}</span>'
            f'<span class="delta-result-cell-mfw">{cell.mfw} MFW</span>'
            '<span class="delta-result-cell-divider" aria-hidden="true">&middot;</span>'
            f"<strong>{_html(status_label)}</strong></article>"
        )
    label = _html(text("results.cell_grid.label"))
    st.markdown(
        f'<div class="delta-result-cell-grid" role="list" aria-label="{label}">'
        + "".join(cards)
        + "</div>",
        unsafe_allow_html=True,
    )


def _render_result_status_table(view: ResultViewV1) -> None:
    rows = []
    for cell in view.cells:
        evidence_role = text(
            "results.cell.reference" if cell.is_reference else "results.cell.sensitivity"
        )
        output = text(
            "results.cell.available"
            if cell.status is ResultCellStatus.COMPLETE
            else "results.cell.unavailable"
        )
        rows.append(
            f'<tr data-mfw="{cell.mfw}" data-status="{cell.status.value}">'
            f'<th scope="row">{cell.mfw}</th><td>{_html(evidence_role)}</td>'
            f"<td>{_html(_result_status_label(cell))}</td><td>{_html(output)}</td></tr>"
        )
    _render_table_scroll_note("results.table_scroll")
    st.markdown(
        '<div class="delta-table-scroll" role="region" '
        f'aria-label="{_html(text("results.status.table"))}" tabindex="0">'
        '<table class="delta-review-table delta-result-status-table">'
        f"<caption>{_html(text('results.status.table'))}</caption><thead><tr>"
        f'<th scope="col">{_html(text("results.status.mfw"))}</th>'
        f'<th scope="col">{_html(text("results.status.role"))}</th>'
        f'<th scope="col">{_html(text("results.status.state"))}</th>'
        f'<th scope="col">{_html(text("results.status.output"))}</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_result_boundary() -> None:
    st.markdown(
        '<section class="delta-result-boundary">'
        f"<div><strong>{_html(text('results.boundary.shows'))}</strong>"
        f"<p>{_html(text('results.boundary.shows.body'))}</p></div>"
        f"<div><strong>{_html(text('results.boundary.not'))}</strong>"
        f"<p>{_html(text('results.boundary.not.body'))}</p></div></section>",
        unsafe_allow_html=True,
    )


def _render_result_method_key() -> None:
    terms = tuple(
        (
            text(f"results.method.{key}.term"),
            text(f"results.method.{key}.definition"),
        )
        for key in ("mfw", "delta", "smaller", "threshold", "cell")
    )
    st.markdown(
        '<aside class="delta-method-key" aria-labelledby="delta-method-key-title">'
        f'<h3 id="delta-method-key-title">{_html(text("results.method.title"))}</h3><dl>'
        + "".join(
            f"<div><dt>{_html(term)}</dt><dd>{_html(definition)}</dd></div>"
            for term, definition in terms
        )
        + "</dl></aside>",
        unsafe_allow_html=True,
    )


def _render_mds_guide() -> None:
    st.markdown(
        '<aside class="delta-method-key" aria-labelledby="delta-mds-guide-title">'
        f'<h3 id="delta-mds-guide-title">{_html(text("results.mds.guide.title"))}</h3>'
        f"<p>{_html(text('results.mds.guide.body'))}</p>"
        '<div class="delta-mds-legend" role="group" '
        f'aria-label="{_html(text("results.mds.guide.legend"))}">'
        '<span><i class="delta-mds-known" aria-hidden="true"></i>'
        f"{_html(text('results.mds.guide.known'))}</span>"
        '<span><i class="delta-mds-unknown" aria-hidden="true"></i>'
        f"{_html(text('results.mds.guide.unknown'))}</span>"
        "</div></aside>",
        unsafe_allow_html=True,
    )


def _render_distance_matrix(cell: ResultCellV1, view: ResultViewV1) -> None:
    matrix = cell.matrix
    if matrix is None:
        raise ValueError("distance matrix is unavailable")
    titles = {document.key: document.title for document in view.documents}
    header = "".join(
        f'<th scope="col" title="{_html(titles[key])}">{_html(key)}</th>'
        for key in matrix.document_keys
    )
    rows = []
    for key, values in zip(matrix.document_keys, matrix.values, strict=True):
        cells = "".join(f"<td>{_distance_label(value)}</td>" for value in values)
        rows.append(
            f'<tr><th scope="row" title="{_html(titles[key])}">{_html(key)}</th>' + cells + "</tr>"
        )
    _render_table_scroll_note("results.table_scroll")
    st.markdown(
        '<div class="delta-table-scroll" role="region" '
        f'aria-label="{_html(text("results.matrix.label"))}" tabindex="0">'
        '<table class="delta-review-table delta-result-matrix">'
        f"<caption>{_html(text('results.matrix.label'))}</caption>"
        f'<thead><tr><th scope="col"></th>{header}</tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


_HEATMAP_TEXT_MAX_DOCUMENTS = 6


def _chart_axis_label(key: str, title: str, *, limit: int = 14) -> str:
    """Pair the compact document key with a truncated title so charts stay decodable."""

    cleaned = " ".join(title.split())
    if len(cleaned) > limit:
        cleaned = cleaned[: limit - 1].rstrip() + "…"
    return f"{key} · {cleaned}"


def _render_heatmap(cell: ResultCellV1, view: ResultViewV1) -> None:
    matrix = cell.matrix
    if matrix is None:
        raise ValueError("distance matrix is unavailable")
    titles = {document.key: document.title for document in view.documents}
    values = [
        {
            "reference": row_key,
            "reference_title": titles[row_key],
            "reference_display": _chart_axis_label(row_key, titles[row_key]),
            "compared": column_key,
            "compared_title": titles[column_key],
            "compared_display": _chart_axis_label(column_key, titles[column_key]),
            "distance": float(distance),
            "distance_label": _distance_label(distance),
        }
        for row_key, row in zip(matrix.document_keys, matrix.values, strict=True)
        for column_key, distance in zip(matrix.document_keys, row, strict=True)
    ]
    order = [_chart_axis_label(key, titles[key]) for key in matrix.document_keys]
    off_diagonal_distances = tuple(
        float(distance)
        for row_index, row in enumerate(matrix.values)
        for column_index, distance in enumerate(row)
        if row_index != column_index
    )
    scale_min = min(off_diagonal_distances, default=0.0)
    scale_max = max(off_diagonal_distances, default=0.0)
    if scale_min == scale_max:
        color_encoding: dict[str, Any] = {
            "condition": {
                "test": "datum.reference === datum.compared",
                "value": "#ffffff",
            },
            "value": "#a9dcc7",
        }
        contrast_test = "false"
    else:
        color_encoding = {
            "condition": {
                "test": "datum.reference === datum.compared",
                "value": "#ffffff",
            },
            "field": "distance",
            "type": "quantitative",
            "scale": {
                "type": "quantize",
                "domain": [scale_min, scale_max],
                "range": [
                    "#f4faf7",
                    "#d7efe5",
                    "#a9dcc7",
                    "#6fbf9f",
                    "#297658",
                    "#0a5443",
                ],
            },
            "legend": {"title": "Classic Delta", "orient": "bottom"},
        }
        contrast_threshold = scale_min + (scale_max - scale_min) * (4 / 6)
        contrast_test = f"datum.distance >= {contrast_threshold!r}"
    chart_data = pa.table(
        {
            "reference": pa.array((value["reference"] for value in values), type=pa.string()),
            "reference_title": pa.array(
                (value["reference_title"] for value in values), type=pa.string()
            ),
            "reference_display": pa.array(
                (value["reference_display"] for value in values), type=pa.string()
            ),
            "compared": pa.array((value["compared"] for value in values), type=pa.string()),
            "compared_title": pa.array(
                (value["compared_title"] for value in values), type=pa.string()
            ),
            "compared_display": pa.array(
                (value["compared_display"] for value in values), type=pa.string()
            ),
            "distance": pa.array((value["distance"] for value in values), type=pa.float64()),
            "distance_label": pa.array(
                (value["distance_label"] for value in values), type=pa.string()
            ),
        }
    )
    layers: list[dict[str, Any]] = [
        {
            "mark": {"type": "rect", "cornerRadius": 3},
            "encoding": {
                "x": {
                    "field": "compared_display",
                    "type": "ordinal",
                    "sort": order,
                    "title": text("results.heatmap.x"),
                },
                "y": {
                    "field": "reference_display",
                    "type": "ordinal",
                    "sort": order,
                    "title": text("results.heatmap.y"),
                },
                "color": color_encoding,
                "stroke": {
                    "condition": {
                        "test": "datum.reference === datum.compared",
                        "value": "#596762",
                    },
                    "value": "#d5ddda",
                },
                "strokeWidth": {
                    "condition": {
                        "test": "datum.reference === datum.compared",
                        "value": 1.5,
                    },
                    "value": 0.5,
                },
                "tooltip": [
                    {"field": "reference_title", "type": "nominal", "title": "Text"},
                    {
                        "field": "compared_title",
                        "type": "nominal",
                        "title": "Compared with",
                    },
                    {
                        "field": "distance_label",
                        "type": "nominal",
                        "title": "Distance",
                    },
                ],
            },
        }
    ]
    if len(order) <= _HEATMAP_TEXT_MAX_DOCUMENTS:
        layers.append(
            {
                "mark": {"type": "text", "fontSize": 12},
                "encoding": {
                    "x": {"field": "compared_display", "type": "ordinal", "sort": order},
                    "y": {"field": "reference_display", "type": "ordinal", "sort": order},
                    "text": {"field": "distance_label", "type": "nominal"},
                    "color": {
                        "condition": [
                            {
                                "test": "datum.reference === datum.compared",
                                "value": "#6f6f6f",
                            },
                            {
                                "test": contrast_test,
                                "value": "#ffffff",
                            },
                        ],
                        "value": "#1a1a1a",
                    },
                },
            }
        )
    spec = {
        "data": {"values": chart_data},
        "width": 360,
        "height": 360,
        "layer": layers,
        "config": {
            "background": "#ffffff",
            "view": {"stroke": None},
            "axis": {"labelColor": "#31333f", "titleColor": "#31333f"},
        },
    }
    st.vega_lite_chart(
        spec=spec,
        width="stretch",
        height=360,
        theme=None,
        key=f"p009_heatmap_{cell.mfw}",
    )


def _render_nearest_neighbours(cell: ResultCellV1, view: ResultViewV1) -> None:
    titles = {document.key: document.title for document in view.documents}

    def tie_label(count: int) -> str:
        if count == 1:
            return text("results.neighbour.no_tie")
        return text("results.neighbour.tie_count", count=count)

    rows = "".join(
        f'<tr><th scope="row">{_html(titles[item.document_key])}</th>'
        f"<td>{_html(titles[item.neighbour_key])}</td>"
        f"<td>{_distance_label(item.distance)}</td>"
        f"<td>{_html(tie_label(item.tie_count))}</td></tr>"
        for item in nearest_neighbours(cell)
    )
    _render_table_scroll_note("results.table_scroll")
    st.markdown(
        '<div class="delta-table-scroll" role="region" '
        f'aria-label="{_html(text("results.neighbour.label"))}" tabindex="0">'
        '<table class="delta-review-table delta-neighbour-table">'
        f"<caption>{_html(text('results.neighbour.label'))}</caption><thead><tr>"
        f'<th scope="col">{_html(text("results.neighbour.document"))}</th>'
        f'<th scope="col">{_html(text("results.neighbour.neighbour"))}</th>'
        f'<th scope="col">{_html(text("results.neighbour.distance"))}</th>'
        f'<th scope="col">{_html(text("results.neighbour.ties"))}</th>'
        "</tr></thead><tbody>" + rows + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_mds(cell: ResultCellV1, view: ResultViewV1) -> None:
    points = classical_mds(cell)
    documents = {document.key: document for document in view.documents}
    values = [
        {
            "key": point.document_key,
            "title": documents[point.document_key].title,
            "role": documents[point.document_key].role.value,
            "x": point.x,
            "y": point.y,
        }
        for point in points
    ]
    coordinate_extent = max(
        (abs(value) for point in points for value in (point.x, point.y)),
        default=1.0,
    )
    if coordinate_extent == 0:
        coordinate_extent = 1.0
    shared_domain = [-coordinate_extent * 1.08, coordinate_extent * 1.08]
    chart_data = pa.table(
        {
            "key": pa.array((value["key"] for value in values), type=pa.string()),
            "title": pa.array((value["title"] for value in values), type=pa.string()),
            "role": pa.array((value["role"] for value in values), type=pa.string()),
            "x": pa.array((value["x"] for value in values), type=pa.float64()),
            "y": pa.array((value["y"] for value in values), type=pa.float64()),
        }
    )
    spec = {
        "data": {"values": chart_data},
        "width": 360,
        "height": 360,
        "layer": [
            {
                "mark": {
                    "type": "point",
                    "filled": True,
                    "size": 260,
                    "opacity": 0.9,
                    "stroke": "#ffffff",
                    "strokeWidth": 2,
                },
                "encoding": {
                    "x": {
                        "field": "x",
                        "type": "quantitative",
                        "title": text("results.mds.x"),
                        "scale": {"domain": shared_domain, "nice": False, "zero": False},
                    },
                    "y": {
                        "field": "y",
                        "type": "quantitative",
                        "title": text("results.mds.y"),
                        "scale": {"domain": shared_domain, "nice": False, "zero": False},
                    },
                    "color": {
                        "field": "role",
                        "type": "nominal",
                        "scale": {
                            "domain": ["known", "unknown"],
                            "range": ["#0f6e56", "#d85a30"],
                        },
                        "legend": None,
                    },
                    "shape": {
                        "field": "role",
                        "type": "nominal",
                        "scale": {
                            "domain": ["known", "unknown"],
                            "range": ["circle", "diamond"],
                        },
                        "legend": None,
                    },
                    "tooltip": [
                        {"field": "title", "type": "nominal", "title": "Text"},
                        {"field": "role", "type": "nominal", "title": "Role"},
                        {"field": "x", "type": "quantitative", "format": ".6f"},
                        {"field": "y", "type": "quantitative", "format": ".6f"},
                    ],
                },
            },
            {
                "mark": {"type": "text", "dy": -16, "fontSize": 12, "color": "#1a1a1a"},
                "encoding": {
                    "x": {
                        "field": "x",
                        "type": "quantitative",
                        "scale": {"domain": shared_domain, "nice": False, "zero": False},
                    },
                    "y": {
                        "field": "y",
                        "type": "quantitative",
                        "scale": {"domain": shared_domain, "nice": False, "zero": False},
                    },
                    "text": {"field": "key", "type": "nominal"},
                },
            },
        ],
        "config": {
            "background": "#ffffff",
            "view": {"stroke": "#e2e5e4"},
            "axis": {"gridColor": "#eef0ef", "labelColor": "#31333f"},
        },
    }
    with st.container(key="p009_mds_square"):
        st.vega_lite_chart(
            spec=spec,
            width="stretch",
            height=360,
            theme=None,
            key=f"p009_mds_{cell.mfw}",
        )
    rows = "".join(
        f'<tr><th scope="row">{_html(documents[point.document_key].title)}</th>'
        f"<td>{_html(documents[point.document_key].role.value)}</td>"
        f"<td>{_distance_label(point.x)}</td><td>{_distance_label(point.y)}</td></tr>"
        for point in points
    )
    _render_table_scroll_note("results.table_scroll")
    st.markdown(
        '<div class="delta-table-scroll" role="region" '
        f'aria-label="{_html(text("results.mds.coordinates"))}" tabindex="0">'
        '<table class="delta-review-table delta-mds-table">'
        f"<caption>{_html(text('results.mds.coordinates'))}</caption><thead><tr>"
        f'<th scope="col">{_html(text("results.mds.document"))}</th>'
        f'<th scope="col">{_html(text("results.mds.role"))}</th>'
        f'<th scope="col">{_html(text("results.mds.x"))}</th>'
        f'<th scope="col">{_html(text("results.mds.y"))}</th>'
        "</tr></thead><tbody>" + rows + "</tbody></table></div>",
        unsafe_allow_html=True,
    )


def _render_result_view(view: ResultViewV1) -> None:
    st.markdown(
        f'<div class="delta-eyebrow">{_html(text("results.eyebrow"))}</div>',
        unsafe_allow_html=True,
    )
    st.title(text("results.title"), anchor=False)
    st.caption(text("results.body"))
    complete_count = sum(cell.status is ResultCellStatus.COMPLETE for cell in view.cells)
    with st.expander(
        text("results.run_details", complete=complete_count, total=len(view.cells)),
        expanded=False,
    ):
        _render_result_status_table(view)
    _render_result_status_summary(view)
    if view.source_result_outcome == "partial":
        st.warning(text("results.partial"), icon=":material/warning:")
    completed = tuple(cell for cell in view.cells if cell.status is ResultCellStatus.COMPLETE)
    reference_index = next(
        (index for index, cell in enumerate(completed) if cell.mfw == view.reference_mfw),
        None,
    )
    default_index = 0 if reference_index is None else reference_index
    selected_mfw = st.radio(
        text("results.selector"),
        options=[cell.mfw for cell in completed],
        index=default_index,
        format_func=lambda mfw: text(
            "results.selector.option",
            mfw=mfw,
            reference=(
                text("results.selector.reference_suffix") if mfw == view.reference_mfw else ""
            ),
        ),
        key="p009_result_cell_selector",
        horizontal=True,
    )
    selected = next(cell for cell in completed if cell.mfw == selected_mfw)
    reference_note = (
        "results.reference_note"
        if reference_index is not None
        else "results.reference_unavailable_note"
    )
    st.info(text(reference_note), icon=":material/push_pin:")

    heatmap_column, method_column = st.columns([1.45, 0.75], gap="large")
    with heatmap_column:
        st.subheader(text("results.heatmap.title"), anchor=False)
        st.caption(text("results.heatmap.body"))
        _render_heatmap(selected, view)
    with method_column:
        _render_result_method_key()

    st.subheader(text("results.matrix.title"), anchor=False)
    st.caption(text("results.matrix.body"))
    _render_distance_matrix(selected, view)

    st.subheader(text("results.neighbour.title"), anchor=False)
    st.caption(text("results.neighbour.body"))
    _render_nearest_neighbours(selected, view)

    mds_column, guide_column = st.columns([1.45, 0.75], gap="large")
    with mds_column:
        st.subheader(text("results.mds.title"), anchor=False)
        st.caption(text("results.mds.body"))
        _render_mds(selected, view)
    with guide_column:
        _render_mds_guide()

    _render_result_boundary()
    st.download_button(
        text("results.download"),
        data=canonical_result_view(view),
        file_name="delta-result-view-v1.json",
        mime="application/json",
        help=text("results.download.help"),
        on_click="ignore",
        width="stretch",
        key="p009_download_result",
    )


def _render_parameters_stage() -> None:
    inventory = st.session_state.get(_FLOW_INVENTORY_KEY)
    annotations = st.session_state.get(_FLOW_ANNOTATIONS_KEY)
    preparation = st.session_state.get(_FLOW_PREPARATION_KEY)
    materialization = st.session_state.get(_FLOW_MATERIALIZATION_KEY)
    if (
        not isinstance(inventory, CorpusInventory)
        or not isinstance(annotations, CorpusAnalysisAnnotationsV1)
        or not isinstance(preparation, PreparationOutcome)
        or preparation.ready_receipt is None
        or not isinstance(materialization, CorpusMaterializationReceipt)
    ):
        _clear_documentation_state(keep_purpose=True)
        st.rerun()
    ready_receipt = preparation.ready_receipt
    assert ready_receipt is not None

    try:
        config = _resolve_session_workflow(inventory, annotations)
    except (ValidationError, ValueError):
        with st.container(key="parameters_stage"):
            st.markdown(
                f'<div class="delta-eyebrow">{_html(text("parameters.eyebrow"))}</div>',
                unsafe_allow_html=True,
            )
            st.title(text("parameters.title"), anchor=False)
            st.caption(text("parameters.body"))
            st.error(text("parameters.configuration_error"), icon=":material/error:")
            if st.button(
                text("parameters.back_prepare"),
                icon=":material/arrow_back:",
                key="p008_back_prepare_invalid",
            ):
                _set_stage(CorpusSubstage.PREPARE)
                st.rerun()
        return
    st.session_state[_FLOW_WORKFLOW_CONFIG_KEY] = config
    presentation = st.session_state.get(_FLOW_JOB_PRESENTATION_KEY)
    if getattr(presentation, "state_id", "") == "succeeded":
        with st.container(key="evidence_panel"):
            try:
                result_view = _runtime().prepared_corpora.result_view(
                    owner_key=_owner_key(),
                    materialization_receipt=materialization,
                )
            except (PreparedCorpusError, WebRuntimeError):
                st.title(text("results.title"), anchor=False)
                st.error(text("results.unavailable"), icon=":material/gpp_bad:")
            else:
                _render_result_view(result_view)
        return
    with st.container(key="parameters_stage"):
        st.markdown(
            f'<div class="delta-eyebrow">{_html(text("parameters.eyebrow"))}</div>',
            unsafe_allow_html=True,
        )
        st.title(text("parameters.title"), anchor=False)
        st.caption(text("parameters.body"))

        selected = st.segmented_control(
            text("parameters.mode.label"),
            options=[mode.value for mode in WorkbenchMode],
            default=WorkbenchMode.GUIDED.value,
            format_func=_mode_label,
            key="p008_analysis_mode",
            width="stretch",
        )
        mode = WorkbenchMode(selected or WorkbenchMode.GUIDED.value)
        if mode is WorkbenchMode.RESEARCH:
            st.warning(text("parameters.research_locked"), icon=":material/lock:")
            st.caption(text("parameters.research_locked_body"))
            if st.button(
                text("parameters.back_prepare"),
                icon=":material/arrow_back:",
                key="p008_back_prepare_research",
            ):
                _set_stage(CorpusSubstage.PREPARE)
                st.rerun()
            return

        st.success(text("parameters.guided_ready"), icon=":material/check_circle:")
        metric_columns = st.columns(4)
        metric_columns[0].metric(text("parameters.metric.cells"), config.cell_count)
        metric_columns[1].metric(text("parameters.metric.reference"), "500 MFW")
        metric_columns[2].metric(text("parameters.metric.culling"), "0%")
        metric_columns[3].metric(text("parameters.metric.unit"), text("parameters.unit.whole"))
        _render_parameter_grid(config)
        st.caption(text("parameters.grid_caption"))
        st.info(text("parameters.interpretive_boundary"), icon=":material/info:")
        st.download_button(
            text("parameters.download_config"),
            data=canonical_p008_json(config),
            file_name="delta-resolved-workflow-config-v1.json",
            mime="application/json",
            width="stretch",
        )
        _render_parameter_explanations()

        if presentation is not None:
            state_id = getattr(presentation, "state_id", "")
            title = getattr(presentation, "title", text("parameters.run_status_unknown"))
            body = getattr(presentation, "body", text("parameters.run_status_unknown"))
            recoverable = state_id in _RECOVERABLE_JOB_STATES
            st.markdown(
                _analysis_status_markup(
                    title=title,
                    body=(text("parameters.recovery.body") if recoverable else body),
                    reference=getattr(presentation, "support_reference", None),
                    alert=recoverable,
                ),
                unsafe_allow_html=True,
            )
            if recoverable and st.button(
                text("parameters.recovery.start_over"),
                icon=":material/restart_alt:",
                type="primary",
                width="stretch",
                key="analysis_start_over",
            ):
                _clear_documentation_state(keep_purpose=True)
                st.rerun()
            return

        confirmed = st.checkbox(
            text("parameters.confirm"),
            help=text("parameters.confirm_help"),
            key="p008_parameter_confirmation",
        )
        action_left, action_right = st.columns(2)
        with action_left:
            if st.button(
                text("parameters.back_prepare"),
                icon=":material/arrow_back:",
                width="stretch",
                key="p008_back_prepare",
            ):
                _set_stage(CorpusSubstage.PREPARE)
                st.rerun()
        with action_right:
            run_clicked = st.button(
                text("parameters.run"),
                type="primary",
                icon=":material/play_arrow:",
                width="stretch",
                disabled=not confirmed,
                key="parameters_run_analysis",
            )
        if run_clicked:
            runtime = _runtime()
            try:

                def admit_analysis() -> object:
                    try:
                        return runtime.prepared_corpora.admit_once(
                            owner_key=_owner_key(),
                            materialization_receipt=materialization,
                            ready_receipt=ready_receipt,
                            inventory=inventory,
                            annotations=annotations,
                            config=preparation.config,
                            resolved_workflow_config=config,
                        )
                    except PreparedCorpusError as error:
                        if error.code is not PreparedCorpusErrorCode.ADMISSION_REUSED:
                            raise
                        queued = runtime.prepared_corpora.status(
                            owner_key=_owner_key(),
                            materialization_receipt=materialization,
                        )
                        if getattr(queued, "state_id", "") not in {"queued", "running"}:
                            raise
                        return queued

                def publish_verified(verified: VerifiedScientificResult) -> None:
                    result_view = project_result_view(
                        config=config,
                        result=verified.result,
                        source_result_sha256=verified.sha256,
                        documents=_result_descriptors(inventory, preparation),
                    )
                    runtime.prepared_corpora.publish_result_view(
                        owner_key=_owner_key(),
                        materialization_receipt=materialization,
                        view=result_view,
                    )

                def resume_result() -> bool:
                    try:
                        verified = runtime.prepared_corpora.scientific_result(
                            owner_key=_owner_key(),
                            materialization_receipt=materialization,
                        )
                    except PreparedCorpusError as error:
                        if error.code is PreparedCorpusErrorCode.RESULT_NOT_AVAILABLE:
                            return False
                        raise
                    publish_verified(verified)
                    return True

                def finalize_result() -> None:
                    verified = runtime.prepared_corpora.scientific_result(
                        owner_key=_owner_key(),
                        materialization_receipt=materialization,
                    )
                    publish_verified(verified)

                def present_result() -> object:
                    return runtime.prepared_corpora.status(
                        owner_key=_owner_key(),
                        materialization_receipt=materialization,
                    )

                presentation = runtime.run_analysis_once(
                    expected_job_id=materialization.job_id,
                    admit_analysis=admit_analysis,
                    resume_result=resume_result,
                    finalize_result=finalize_result,
                    present_result=present_result,
                )
            except WebRuntimeError as error:
                if error.code is WebRuntimeErrorCode.ANALYSIS_NOT_READY:
                    st.markdown(
                        _analysis_status_markup(
                            title=text("parameters.queue_wait.title"),
                            body=text("parameters.queue_wait.body"),
                            reference=text(
                                "parameters.status_reference",
                                code=error.code.value,
                            ),
                            alert=False,
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    st.error(text("parameters.run_error"), icon=":material/gpp_bad:")
                    st.caption(text("corpus.error.reference", code=error.code.value))
            except (PreparedCorpusError, AnalysisOrchestratorError) as error:
                terminal = _terminal_presentation(runtime, materialization)
                if terminal is not None:
                    st.session_state[_FLOW_JOB_PRESENTATION_KEY] = terminal
                    st.rerun()
                else:
                    st.error(text("parameters.run_error"), icon=":material/gpp_bad:")
                    st.caption(text("corpus.error.reference", code=error.code.value))
            except (ValidationError, ValueError):
                st.error(text("parameters.configuration_error"), icon=":material/error:")
            else:
                st.session_state[_FLOW_JOB_PRESENTATION_KEY] = presentation
                st.rerun()


def _render_setup(stage: CorpusSubstage) -> PurposeId:
    if stage is CorpusSubstage.UPLOAD:
        _render_entry_experience()
        selected = st.radio(
            text("purpose.label"),
            options=[purpose.purpose_id for purpose in PURPOSES],
            index=0,
            format_func=_purpose_label,
            key="research_purpose",
            horizontal=True,
            captions=[text(f"purpose.{purpose.purpose_id}.summary") for purpose in PURPOSES],
        )
        purpose_spec = PURPOSE_BY_ID[selected]
        _render_purpose_guidance(purpose_spec)
        return PurposeId(purpose_spec.purpose_id)
    purpose = PurposeId(st.session_state.get(_FLOW_PURPOSE_KEY, PurposeId.TEXT_PROXIMITY.value))
    input_mode = CorpusInputMode(
        st.session_state.get(_FLOW_INPUT_MODE_KEY, CorpusInputMode.TEXT_FILES.value)
    )
    with st.container(key="persisted_upload_choices"):
        st.radio(
            text("purpose.label"),
            options=[item.purpose_id for item in PURPOSES],
            index=next(
                index for index, item in enumerate(PURPOSES) if item.purpose_id == purpose.value
            ),
            format_func=_purpose_label,
            key="research_purpose",
            horizontal=True,
            captions=[text(f"purpose.{item.purpose_id}.summary") for item in PURPOSES],
            disabled=True,
        )
        st.radio(
            text("corpus.mode.label"),
            options=[mode.value for mode in CorpusInputMode],
            index=next(index for index, mode in enumerate(CorpusInputMode) if mode is input_mode),
            format_func=_corpus_mode_label,
            key="corpus_input_mode",
            horizontal=True,
            disabled=True,
        )
    return purpose


def _evidence_is_active(stage: CorpusSubstage) -> bool:
    if stage is not CorpusSubstage.PARAMETERS:
        return False
    presentation = st.session_state.get(_FLOW_JOB_PRESENTATION_KEY)
    return getattr(presentation, "state_id", "") == "succeeded"


def main() -> None:
    """Render the workbench without retaining uploaded text beyond secure intake."""

    st.set_page_config(
        page_title=text("meta.page_title"),
        page_icon=text("brand.mark"),
        layout="wide",
        initial_sidebar_state="auto",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)
    _clear_pending_upload_widgets()
    health = dict(public_health())
    stage = _stage()
    evidence_active = _evidence_is_active(stage)
    _render_header(health, stage, evidence_active=evidence_active)
    if stage is CorpusSubstage.UPLOAD:
        _render_content_anchor()
    purpose = _render_setup(stage)
    _render_stepper(stage, evidence_active=evidence_active)
    if stage is not CorpusSubstage.UPLOAD:
        _render_content_anchor()
    column_ratio = [1000, 1] if stage is CorpusSubstage.UPLOAD else [1.8, 0.8]
    column_gap: Literal["large"] | None = None if stage is CorpusSubstage.UPLOAD else "large"
    left, right = st.columns(column_ratio, gap=column_gap)
    with left:
        if stage is CorpusSubstage.UPLOAD:
            _render_corpus_stage(purpose)
            _render_mobile_purpose_guidance(PURPOSE_BY_ID[purpose.value])
            _render_stylometry_orientation()
            _render_parameter_orientation()
        elif stage is CorpusSubstage.DESCRIBE:
            _render_describe_stage(purpose)
        elif stage is CorpusSubstage.REVIEW:
            _render_review_stage()
        elif stage is CorpusSubstage.PREPARE:
            _render_prepare_stage()
        else:
            _render_parameters_stage()
    if stage is CorpusSubstage.UPLOAD:
        _render_boundary()
    else:
        with right:
            _render_boundary()
    _render_sidebar(health, stage)
    st.markdown(
        '<footer class="delta-footer">'
        f"<p>{_html(text('footer.scope'))}</p>"
        f"<p>{_html(text('footer.fair'))}</p>"
        "</footer>",
        unsafe_allow_html=True,
    )


__all__ = ["CorpusSubstage", "main"]
