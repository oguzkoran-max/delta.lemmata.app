"""English-only Streamlit workbench shell for P002."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from delta_lemmata.catalog import text
from delta_lemmata.health import public_health
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


def _map_row(number: int, label_key: str, *, active: bool) -> str:
    state_key = "sidebar.state.active" if active else "sidebar.state.locked"
    active_class = " is-active" if active else ""
    return (
        f'<div class="delta-map-row{active_class}">'
        f'<span class="delta-map-number">{number:02d}</span>'
        f'<span class="delta-map-name">{_html(text(label_key))}</span>'
        f'<span class="delta-map-state">{_html(text(state_key))}</span>'
        "</div>"
    )


def _render_sidebar(health: dict[str, Any]) -> None:
    with st.sidebar:
        st.badge(
            text("sidebar.stage_badge"),
            icon=":material/construction:",
            color="green",
        )
        st.caption(text("sidebar.progress"))
        st.progress(25)
        st.markdown(
            '<div class="delta-map">'
            + _map_row(1, "sidebar.step.purpose", active=True)
            + _map_row(2, "sidebar.step.corpus", active=False)
            + _map_row(3, "sidebar.step.parameters", active=False)
            + _map_row(4, "sidebar.step.evidence", active=False)
            + "</div>",
            unsafe_allow_html=True,
        )
        st.divider()
        st.subheader(text("sidebar.boundary_title"))
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


def _render_purpose_detail(purpose: PurposeSpec) -> None:
    with st.container(border=True, key="purpose_detail"):
        st.badge(
            text("purpose.badge"),
            icon=purpose.icon,
            color=purpose.badge_color,  # type: ignore[arg-type]
        )
        st.markdown(
            '<div class="delta-purpose-title" role="heading" aria-level="2">'
            f"{_html(text(purpose.label_key))}</div>"
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
    st.subheader(text("mode.title"))
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


def _render_corpus_stage() -> None:
    with st.container(border=True, key="corpus_stage"):
        st.markdown(
            f'<div class="delta-eyebrow">{_html(text("corpus.eyebrow"))}</div>',
            unsafe_allow_html=True,
        )
        title_column, badge_column = st.columns([2.2, 1.4], vertical_alignment="center")
        with title_column:
            st.subheader(text("corpus.title"))
        with badge_column:
            st.badge(
                text("corpus.locked"),
                icon=":material/lock:",
                color="gray",
            )
        st.caption(text("corpus.body"))
        st.file_uploader(
            text("corpus.uploader"),
            type=["txt", "zip", "csv"],
            accept_multiple_files=True,
            help=text("corpus.uploader_help"),
            disabled=True,
            key="corpus_files",
        )
        metadata_column, continue_column = st.columns(2)
        with metadata_column:
            st.button(
                text("corpus.metadata_button"),
                icon=":material/table_view:",
                disabled=True,
                width="stretch",
            )
        with continue_column:
            st.button(
                text("corpus.continue_button"),
                icon=":material/arrow_forward:",
                disabled=True,
                width="stretch",
            )


def _render_experiment_map() -> None:
    with st.container(border=True, key="experiment_map"):
        st.subheader(text("map.title"))
        st.caption(text("map.body"))
        st.markdown(
            '<div class="delta-map">'
            + _map_row(1, "sidebar.step.purpose", active=True)
            + _map_row(2, "sidebar.step.corpus", active=False)
            + _map_row(3, "sidebar.step.parameters", active=False)
            + _map_row(4, "sidebar.step.evidence", active=False)
            + "</div>",
            unsafe_allow_html=True,
        )


def _render_boundary(purpose: PurposeSpec) -> None:
    with st.container(border=True, key="boundary_panel"):
        st.subheader(text("boundary.title"))
        st.caption(text(purpose.boundary_key))


def _render_evidence_panel() -> None:
    rows = (
        ("evidence.corpus", "evidence.corpus_state"),
        ("evidence.parameters", "evidence.parameters_state"),
        ("evidence.limits", "evidence.limits_state"),
        ("evidence.run", "evidence.run_state"),
    )
    with st.container(border=True, key="evidence_panel"):
        st.subheader(text("evidence.title"))
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
        st.subheader(text(presentation.title_key))
        st.caption(text(presentation.body_key))
        st.button(
            text("run.button"),
            icon=":material/play_arrow:",
            disabled=True,
            help=text("run.help"),
            width="stretch",
        )


def main() -> None:
    """Render the P002 workbench shell."""

    st.set_page_config(
        page_title=text("meta.page_title"),
        page_icon=text("brand.mark"),
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)
    health = dict(public_health())
    _render_header(health)
    _render_sidebar(health)

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
        _render_corpus_stage()

    with right:
        _render_experiment_map()
        _render_boundary(purpose)
        _render_evidence_panel()
        render_interface_state(InterfaceState.EMPTY)

    st.divider()
    footer_left, footer_right = st.columns(2)
    with footer_left:
        st.caption(text("footer.scope"))
    with footer_right:
        st.caption(text("footer.fair"))
