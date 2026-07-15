"""English-only Streamlit workbench through P007 corpus preparation."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from html import escape
from typing import Any, Literal, cast

import streamlit as st
from pydantic import HttpUrl, TypeAdapter, ValidationError

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
    CorpusHealthReadiness,
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
    validate_browser_uploads,
    visit_browser_corpus_payloads,
)
from delta_lemmata.prepared_corpus_service import (
    PreparationOutcome,
    PreparedCorpusError,
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
from delta_lemmata.ui_theme import APP_CSS
from delta_lemmata.web_runtime import WebRuntime, WebRuntimeError, build_web_runtime
from delta_lemmata.workbench import (
    MODE_BODY_KEYS,
    MODE_LABEL_KEYS,
    PURPOSE_BY_ID,
    PURPOSES,
    PurposeSpec,
    WorkbenchMode,
)

_UPLOAD_GENERATION_KEY = "_intake_upload_generation"
_PENDING_ERROR_KEY = "_intake_pending_error"
_PENDING_UPLOAD_CLEAR_KEY = "_intake_pending_widget_clear"
_FLOW_STAGE_KEY = "_p004_flow_stage"
_FLOW_PURPOSE_KEY = "_p004_purpose"
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
_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


class CorpusSubstage(StrEnum):
    UPLOAD = "upload"
    DESCRIBE = "describe"
    REVIEW = "review"
    PREPARE = "prepare"


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


def _render_header(health: dict[str, Any]) -> None:
    version = text("header.version", version=health["version"])
    build = text("header.build", build_id=health["build_id"])
    st.markdown(
        f"""
        <div class="delta-header">
          <div class="delta-brand">
            <span class="delta-mark" aria-hidden="true">{_html(text("brand.mark"))}</span>
            <div>
              <div class="delta-brand-name">{_html(text("brand.name"))}</div>
              <div class="delta-brand-subtitle">{_html(text("brand.subtitle"))}</div>
            </div>
          </div>
          <div class="delta-build">
            <div class="delta-build-status">
              <span class="delta-dot"></span>{_html(text("header.stage"))}
            </div>
            <div class="delta-build-meta">{_html(version)} · {_html(build)}</div>
          </div>
        </div>
        """,
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


def _render_stepper(stage: CorpusSubstage) -> None:
    stage_key = {
        CorpusSubstage.UPLOAD: "flow.stage.upload",
        CorpusSubstage.DESCRIBE: "flow.stage.describe",
        CorpusSubstage.REVIEW: "flow.stage.review",
        CorpusSubstage.PREPARE: "flow.stage.prepare",
    }[stage]
    markup = (
        '<nav class="delta-map" aria-label="Corpus documentation progress">'
        '<ol class="delta-map-list">'
        + _map_row(1, "sidebar.step.purpose", "sidebar.state.complete")
        + _map_row(2, "sidebar.step.corpus", stage_key, active=True)
        + _map_row(3, "sidebar.step.parameters", "flow.locked")
        + _map_row(4, "sidebar.step.evidence", "flow.locked")
        + "</ol></nav>"
    )
    st.markdown(markup, unsafe_allow_html=True)


def _render_sidebar(health: dict[str, Any]) -> None:
    with st.sidebar:
        st.badge(text("sidebar.badge"), icon=":material/menu_book:", color="green")
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


def _render_purpose_guidance(purpose: PurposeSpec) -> None:
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
    st.markdown(
        '<section class="delta-purpose-guide" role="region" aria-live="polite" '
        f'aria-label="{_html(guidance)}">{markup}</section>',
        unsafe_allow_html=True,
    )


def _render_entry_experience() -> None:
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
        <section class="delta-entry" aria-labelledby="delta-entry-title">
          <div class="delta-entry-copy">
            <div class="delta-entry-eyebrow">{_html(text("setup.eyebrow"))}</div>
            <h1 id="delta-entry-title">{_html(text("setup.title"))}</h1>
            <p class="delta-entry-lede">{_html(text("setup.intro"))}</p>
            <p class="delta-entry-scope">{_html(text("setup.corpus_scope"))}</p>
          </div>
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
          <figure class="delta-method" aria-labelledby="delta-method-title">
            <figcaption id="delta-method-title">
              <strong>{_html(text("setup.method_label"))}</strong>
              <span>{_html(text("setup.method.caption"))}</span>
            </figcaption>
            <ol>{method_markup}</ol>
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
    ):
        st.session_state.pop(key, None)
    for session_key in tuple(st.session_state):
        if str(session_key).startswith(
            (
                "draft_",
                "prep_",
                "review_confirmation_",
                "review_timeline_selector_",
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
        selected_mode = st.segmented_control(
            text("corpus.mode.label"),
            options=[mode.value for mode in CorpusInputMode],
            default=CorpusInputMode.TEXT_FILES.value,
            format_func=_corpus_mode_label,
            key="corpus_input_mode",
            width="stretch",
        )
        mode = CorpusInputMode(selected_mode or CorpusInputMode.TEXT_FILES.value)
        if mode is CorpusInputMode.TEXT_FILES:
            uploaded_corpus = st.file_uploader(
                text("corpus.text_uploader"),
                type=["txt"],
                accept_multiple_files=True,
                help=text("corpus.text_uploader_help"),
                key=f"corpus_text_files_{generation}",
            )
            corpus_files = tuple(_browser_upload(upload) for upload in uploaded_corpus)
        else:
            uploaded_archive = st.file_uploader(
                text("corpus.archive_uploader"),
                type=["zip"],
                accept_multiple_files=False,
                help=text("corpus.archive_uploader_help"),
                key=f"corpus_archive_file_{generation}",
            )
            corpus_files = () if uploaded_archive is None else (_browser_upload(uploaded_archive),)
        uploaded_metadata = None
        with st.expander(text("corpus.metadata_advanced")):
            uploaded_metadata = st.file_uploader(
                text("corpus.metadata_uploader"),
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
            text("describe.correction_here", field_path=target.field_path),
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
        st.header(text("describe.title"), anchor=False)
        st.caption(text("describe.body"))
        if st.button(text("describe.back"), icon=":material/arrow_back:"):
            _clear_documentation_state(keep_purpose=True)
            st.rerun()
        target = _correction_target()
        if target is not None:
            st.markdown(
                f"**{_html(target.work_title)} · "
                f"{_html(_choice_label(target.group.value))} · "
                f"{_html(target.field_path)}**",
                unsafe_allow_html=True,
            )
            if _origin() is CorpusOrigin.CSV:
                st.warning(
                    text(
                        "describe.correction_csv",
                        field_path=target.field_path,
                        work_id=target.work_id,
                    ),
                    icon=":material/table_edit:",
                )
                st.caption(text("describe.correction_csv_boundary"))
                return
            st.info(
                text("describe.correction_guided", field_path=target.field_path),
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
                ", ".join(item.field_paths)
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
    st.markdown(
        '<div class="delta-table-scroll" role="region" '
        f'aria-label="{_html(text("review.completeness_title"))}" tabindex="0">'
        '<table class="delta-review-table delta-completeness-table">'
        f"<caption>{_html(text('review.completeness_title'))}</caption>"
        f'<thead><tr><th scope="col">Work</th>{headers}</tr></thead><tbody>'
        + "".join(body)
        + "</tbody></table></div>",
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
                f"{targets[index].field_path}"
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


def _render_issues(report: ValidationReport) -> None:
    st.subheader(text("review.issues_title"), anchor=False)
    if not report.issues:
        st.success(text("review.no_issues"), icon=":material/task_alt:")
        return
    rows = []
    for issue in report.issues:
        rows.append(
            f'<li class="delta-issue delta-issue-{_html(issue.severity.value)}">'
            f'<div class="delta-issue-code">{_html(issue.severity.value.upper())} · '
            f"{_html(issue.code.value)}</div>"
            f"<strong>{_html(issue.message)}</strong>"
            f"<span><b>{_html(text('review.issue_why'))}:</b> "
            f"{_html(issue.why_it_matters)}</span>"
            f"<span><b>{_html(text('review.issue_fix'))}:</b> "
            f"{_html(issue.how_to_fix)}</span></li>"
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


def _render_review_stage() -> None:
    inventory = st.session_state.get(_FLOW_INVENTORY_KEY)
    report = st.session_state.get(_FLOW_REPORT_KEY)
    if not isinstance(inventory, CorpusInventory) or not isinstance(report, ValidationReport):
        _clear_documentation_state(keep_purpose=True)
        st.rerun()
    with st.container(border=True, key="review_stage"):
        st.markdown(
            f'<div class="delta-eyebrow">{_html(text("review.eyebrow"))}</div>',
            unsafe_allow_html=True,
        )
        st.header(text("review.title"), anchor=False)
        st.caption(text("review.body"))
        try:
            projection = build_review_projection(inventory, report)
        except ReviewProjectionError:
            st.error(text("review.projection_unavailable"), icon=":material/block:")
            st.info(text("review.analysis_locked"), icon=":material/lock:")
            return
        edit_column, reset_column = st.columns(2)
        with edit_column:
            if st.button(text("review.edit"), icon=":material/edit:", width="stretch"):
                st.session_state.pop(_FLOW_CORRECTION_KEY, None)
                st.session_state[_FLOW_STAGE_KEY] = CorpusSubstage.DESCRIBE.value
                st.rerun()
        with reset_column:
            if st.button(text("review.start_over"), icon=":material/restart_alt:", width="stretch"):
                _clear_documentation_state(keep_purpose=False)
                st.rerun()
        if report.blocked:
            st.error(text("review.blocked"), icon=":material/block:")
        else:
            st.success(text("review.ready"), icon=":material/check_circle:")
        readiness = report.readiness
        first, second, third, fourth = st.columns(4)
        first.metric(text("review.metric.works"), readiness.independent_work_count)
        second.metric(text("review.metric.chronology"), readiness.chronology_point_count)
        third.metric(text("review.metric.blockers"), readiness.blocker_count)
        fourth.metric(text("review.metric.warnings"), readiness.warning_count)
        st.metric(text("review.metric.rights"), readiness.rights_restriction_count)
        _render_composition(projection)
        _render_completeness(projection)
        _render_timeline(projection)
        _render_rights_matrix(inventory)
        _render_issues(report)
        confirmed = _render_confirmation(projection, report)
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


def _render_preparation_outcome(
    inventory: CorpusInventory,
    outcome: PreparationOutcome,
) -> None:
    health = outcome.health_report
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

    works = {work.work_id: work.title_original for work in inventory.works}
    length_rows = [
        {
            text("prepare.table.work"): works[item.work_id],
            text("prepare.table.tokens"): item.token_count,
            text("prepare.table.unique"): item.unique_token_count,
        }
        for item in outcome.manifest.works
    ]
    st.subheader(text("prepare.length_title"), anchor=False)
    st.caption(text("prepare.length_body"))
    st.bar_chart(
        length_rows,
        x=text("prepare.table.work"),
        y=text("prepare.table.tokens"),
        color="#0f6e56",
    )
    st.dataframe(length_rows, hide_index=True, width="stretch")

    st.subheader(text("prepare.mfw_title"), anchor=False)
    st.caption(text("prepare.mfw_body"))
    capacity_columns = st.columns(4)
    for column, capacity in zip(capacity_columns, health.mfw_capacity, strict=True):
        with column:
            status_key = (
                "prepare.mfw.available" if capacity.available else "prepare.mfw.unavailable"
            )
            st.metric(
                text("prepare.mfw.metric", mfw=capacity.requested_mfw),
                text(status_key),
                delta=text("prepare.mfw.features", count=capacity.available_features),
                delta_color="off",
            )

    st.subheader(text("prepare.findings_title"), anchor=False)
    st.caption(text("prepare.findings_body"))
    for finding in health.findings:
        _render_health_finding(finding)

    st.subheader(text("prepare.downloads_title"), anchor=False)
    first_download, second_download, third_download = st.columns(3)
    with first_download:
        st.download_button(
            text("prepare.download_health"),
            data=canonical_p007_json(health),
            file_name="delta-corpus-health.json",
            mime="application/json",
            width="stretch",
        )
    with second_download:
        st.download_button(
            text("prepare.download_manifest"),
            data=canonical_p007_json(outcome.manifest),
            file_name="delta-preprocessing-manifest.json",
            mime="application/json",
            width="stretch",
        )
    with third_download:
        st.download_button(
            text("prepare.download_config"),
            data=canonical_p007_json(outcome.config),
            file_name="delta-preprocessing-config.json",
            mime="application/json",
            width="stretch",
        )


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
        st.header(text("prepare.title"), anchor=False)
        st.caption(text("prepare.body"))
        st.info(text("prepare.profile_summary"), icon=":material/tune:")

        outcome = st.session_state.get(_FLOW_PREPARATION_KEY)
        if isinstance(outcome, PreparationOutcome):
            _render_preparation_outcome(inventory, outcome)
            if outcome.ready_receipt is None:
                if st.button(
                    text("prepare.start_over"),
                    icon=":material/restart_alt:",
                    width="stretch",
                ):
                    _clear_documentation_state(keep_purpose=True)
                    st.rerun()
            else:
                st.info(text("prepare.parameters_next"), icon=":material/arrow_forward:")
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


def _render_setup(stage: CorpusSubstage) -> PurposeId:
    if stage is CorpusSubstage.UPLOAD:
        _render_entry_experience()
        selected = st.segmented_control(
            text("purpose.label"),
            options=[purpose.purpose_id for purpose in PURPOSES],
            default=PURPOSES[0].purpose_id,
            format_func=_purpose_label,
            key="research_purpose",
            width="stretch",
        )
        purpose_spec = PURPOSE_BY_ID[selected or PURPOSES[0].purpose_id]
        _render_purpose_guidance(purpose_spec)
        return PurposeId(purpose_spec.purpose_id)
    st.markdown(
        f'<div class="delta-eyebrow">{_html(text("setup.eyebrow"))}</div>',
        unsafe_allow_html=True,
    )
    st.title(text("setup.title"))
    purpose = PurposeId(st.session_state.get(_FLOW_PURPOSE_KEY, PurposeId.TEXT_PROXIMITY.value))
    st.caption(f"{text('purpose.label')}: {_purpose_label(purpose.value)}")
    return purpose


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
    _render_header(health)
    stage = _stage()
    purpose = _render_setup(stage)
    _render_stepper(stage)
    column_ratio = [1000, 1] if stage is CorpusSubstage.UPLOAD else [1.8, 0.8]
    column_gap: Literal["large"] | None = None if stage is CorpusSubstage.UPLOAD else "large"
    left, right = st.columns(column_ratio, gap=column_gap)
    with left:
        if stage is CorpusSubstage.UPLOAD:
            _render_corpus_stage(purpose)
            _render_parameter_orientation()
        elif stage is CorpusSubstage.DESCRIBE:
            _render_describe_stage(purpose)
        elif stage is CorpusSubstage.REVIEW:
            _render_review_stage()
        else:
            _render_prepare_stage()
    if stage is CorpusSubstage.UPLOAD:
        _render_boundary()
    else:
        with right:
            _render_boundary()
    _render_sidebar(health)
    st.divider()
    footer_left, footer_right = st.columns(2)
    with footer_left:
        st.caption(text("footer.scope"))
    with footer_right:
        st.caption(text("footer.fair"))


__all__ = ["CorpusSubstage", "main"]
