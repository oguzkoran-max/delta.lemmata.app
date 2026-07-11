"""English-only Streamlit workbench with a secure P003 intake boundary."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from delta_lemmata.catalog import text
from delta_lemmata.health import public_health
from delta_lemmata.ingestion import DEFAULT_LIMITS, IntakeReceipt, IntakeRole
from delta_lemmata.intake_ui import (
    CORPUS_MODE_LABEL_KEYS,
    INTAKE_ERROR_MESSAGE_KEYS,
    BrowserUpload,
    CorpusInputMode,
    IntakeOutcome,
    validate_browser_uploads,
)
from delta_lemmata.ui_theme import APP_CSS
from delta_lemmata.workbench import (
    MODE_BODY_KEYS,
    MODE_LABEL_KEYS,
    PURPOSE_BY_ID,
    PURPOSES,
    STATE_PRESENTATIONS,
    InterfaceState,
    PurposeSpec,
    WorkbenchMode,
)


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


def _map_row(number: int, label_key: str, state_key: str, *, active: bool = False) -> str:
    active_class = " is-active" if active else ""
    return (
        f'<div class="delta-map-row{active_class}">'
        f'<span class="delta-map-number">{number:02d}</span>'
        f'<span class="delta-map-name">{_html(text(label_key))}</span>'
        f'<span class="delta-map-state">{_html(text(state_key))}</span>'
        "</div>"
    )


def _experiment_map_markup(corpus_ready: bool) -> str:
    """Return the shared experiment-map markup used by the sidebar and the panel."""

    corpus_state = "sidebar.state.validated" if corpus_ready else "sidebar.state.active"
    return (
        '<div class="delta-map">'
        + _map_row(1, "sidebar.step.purpose", "sidebar.state.complete")
        + _map_row(2, "sidebar.step.corpus", corpus_state, active=not corpus_ready)
        + _map_row(3, "sidebar.step.parameters", "sidebar.state.locked")
        + _map_row(4, "sidebar.step.evidence", "sidebar.state.locked")
        + "</div>"
    )


def _render_sidebar(health: dict[str, Any], outcome: IntakeOutcome) -> None:
    with st.sidebar:
        st.badge(
            text("header.stage"),
            icon=":material/construction:",
            color="green",
        )
        st.caption(text("sidebar.progress"))
        st.progress(50)
        st.markdown(_experiment_map_markup(outcome.corpus_ready), unsafe_allow_html=True)
        st.divider()
        st.markdown(f"**{text('sidebar.boundary_title')}**")
        st.caption(text("sidebar.boundary_body"))
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


def _browser_upload(upload: Any) -> BrowserUpload:
    return BrowserUpload(
        display_label=upload.name,
        data=upload.getvalue(),
        declared_mime=upload.type or None,
    )


def _receipt_metric(receipt: IntakeReceipt) -> str:
    if receipt.role is IntakeRole.CORPUS_TEXT:
        return text(
            "corpus.receipt.text",
            lines=receipt.line_count,
            tokens=receipt.token_count,
        )
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


def _render_purpose_detail(purpose: PurposeSpec) -> None:
    with st.container(border=True, key="purpose_detail"):
        st.badge(
            text("purpose.badge"),
            icon=purpose.icon,
            color=purpose.badge_color,  # type: ignore[arg-type]
        )
        st.header(text(purpose.label_key), anchor=False)
        st.markdown(
            f'<div class="delta-field-label">{_html(text("purpose.question_label"))}</div>'
            f'<div class="delta-purpose-question">{_html(text(purpose.question_key))}</div>',
            unsafe_allow_html=True,
        )
        use_column, boundary_column = st.columns(2, gap="medium")
        with use_column:
            st.markdown(
                f'<div class="delta-field-label">{_html(text("purpose.use_label"))}</div>'
                f'<div class="delta-detail-text">{_html(text(purpose.use_key))}</div>',
                unsafe_allow_html=True,
            )
        with boundary_column:
            st.markdown(
                f'<div class="delta-field-label">{_html(text("purpose.boundary_label"))}</div>'
                f'<div class="delta-detail-text">{_html(text(purpose.boundary_key))}</div>',
                unsafe_allow_html=True,
            )


def _render_mode() -> WorkbenchMode:
    st.markdown(
        f'<div class="delta-eyebrow">{_html(text("mode.eyebrow"))}</div>',
        unsafe_allow_html=True,
    )
    st.header(text("mode.title"), anchor=False)
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


def _render_corpus_stage() -> IntakeOutcome:
    with st.container(border=True, key="corpus_stage"):
        st.markdown(
            f'<div class="delta-eyebrow">{_html(text("corpus.eyebrow"))}</div>',
            unsafe_allow_html=True,
        )
        title_column, badge_column = st.columns([2.2, 1.4], vertical_alignment="center")
        with title_column:
            st.header(text("corpus.title"), anchor=False)
        with badge_column:
            st.badge(
                text("corpus.available"),
                icon=":material/shield:",
                color="green",
            )
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
                key="corpus_text_files",
            )
            corpus_files = tuple(_browser_upload(upload) for upload in uploaded_corpus)
        else:
            uploaded_archive = st.file_uploader(
                text("corpus.archive_uploader"),
                type=["zip"],
                accept_multiple_files=False,
                help=text("corpus.archive_uploader_help"),
                key="corpus_archive_file",
            )
            corpus_files = () if uploaded_archive is None else (_browser_upload(uploaded_archive),)
        uploaded_metadata = st.file_uploader(
            text("corpus.metadata_uploader"),
            type=["csv"],
            accept_multiple_files=False,
            help=text("corpus.metadata_uploader_help"),
            key="metadata_file",
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
        if not outcome.has_inputs:
            st.info(text("corpus.empty"), icon=":material/upload_file:")
        elif outcome.error_code is not None:
            st.error(text("corpus.error.title"), icon=":material/gpp_bad:")
            st.caption(text(INTAKE_ERROR_MESSAGE_KEYS[outcome.error_code]))
            st.caption(text("corpus.error.reference", code=outcome.error_code.value))
        else:
            st.success(
                text(
                    "corpus.success",
                    uploads=outcome.submitted_count,
                    units=outcome.corpus_units,
                    bytes=outcome.total_bytes,
                ),
                icon=":material/verified_user:",
            )
            if outcome.metadata_ready:
                st.badge(
                    text("corpus.metadata_valid"),
                    icon=":material/table_view:",
                    color="blue",
                )
            _render_receipts(outcome)
        st.button(
            text("corpus.continue_button"),
            disabled=True,
            help=text("corpus.continue_button_help"),
            width="stretch",
        )
        return outcome


def _render_experiment_map(outcome: IntakeOutcome) -> None:
    with st.container(border=True, key="experiment_map"):
        st.header(text("map.title"), anchor=False)
        st.caption(text("map.body"))
        st.markdown(_experiment_map_markup(outcome.corpus_ready), unsafe_allow_html=True)


def _render_boundary() -> None:
    with st.container(border=True, key="boundary_panel"):
        st.header(text("boundary.title"), anchor=False)
        st.caption(text("boundary.body"))


def _render_evidence_panel(outcome: IntakeOutcome) -> None:
    corpus_state = "evidence.corpus_state"
    if outcome.error_code is not None:
        corpus_state = "evidence.corpus_rejected"
    elif outcome.corpus_ready:
        corpus_state = "evidence.corpus_validated"
    rows = (
        ("evidence.corpus", corpus_state),
        ("evidence.parameters", "evidence.parameters_state"),
        ("evidence.limits", "evidence.limits_state"),
        ("evidence.run", "evidence.run_state"),
    )
    with st.container(border=True, key="evidence_panel"):
        st.header(text("evidence.title"), anchor=False)
        st.caption(text("evidence.body"))
        markup = "".join(
            '<div class="delta-evidence-row">'
            f'<span class="delta-evidence-name">{_html(text(name_key))}</span>'
            f'<span class="delta-evidence-state">{_html(text(state_key))}</span>'
            "</div>"
            for name_key, state_key in rows
        )
        st.markdown(markup, unsafe_allow_html=True)


def render_interface_state(state: InterfaceState) -> None:
    """Render one state through the shared, versioned state contract."""

    presentation = STATE_PRESENTATIONS[state]
    with st.container(border=True, key="run_state"):
        st.badge(
            text(presentation.label_key),
            icon=presentation.icon,
            color=presentation.badge_color,  # type: ignore[arg-type]
        )
        st.header(text(presentation.title_key), anchor=False)
        st.caption(text(presentation.body_key))
        st.caption(text("run.disabled_reason"))
        st.button(
            text("run.button"),
            disabled=True,
            help=text("run.help"),
            width="stretch",
        )


def main() -> None:
    """Render the workbench through the implemented secure-intake boundary."""

    st.set_page_config(
        page_title=text("meta.page_title"),
        page_icon=text("brand.mark"),
        layout="wide",
        initial_sidebar_state="auto",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)
    health = dict(public_health())
    _render_header(health)

    left, right = st.columns([1.7, 0.9], gap="large")
    with left:
        st.markdown(
            f'<div class="delta-eyebrow">{_html(text("setup.eyebrow"))}</div>',
            unsafe_allow_html=True,
        )
        st.title(text("setup.title"))
        st.caption(text("setup.intro"))
        selected_purpose = st.segmented_control(
            text("purpose.label"),
            options=[purpose.purpose_id for purpose in PURPOSES],
            default=PURPOSES[0].purpose_id,
            format_func=_purpose_label,
            key="research_purpose",
            width="stretch",
        )
        purpose = PURPOSE_BY_ID[selected_purpose or PURPOSES[0].purpose_id]
        _render_purpose_detail(purpose)
        st.divider()
        _render_mode()
        st.divider()
        outcome = _render_corpus_stage()

    with right:
        _render_experiment_map(outcome)
        _render_boundary()
        _render_evidence_panel(outcome)
        render_interface_state(InterfaceState.EMPTY)

    _render_sidebar(health, outcome)

    st.divider()
    footer_left, footer_right = st.columns(2)
    with footer_left:
        st.caption(text("footer.scope"))
    with footer_right:
        st.caption(text("footer.fair"))
