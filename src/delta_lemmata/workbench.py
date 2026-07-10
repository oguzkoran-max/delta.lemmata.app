"""Versioned shell contracts for purposes, modes, runtime boundaries, and states."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class PurposeSpec:
    """One research purpose exposed by the v0.1 workbench."""

    purpose_id: str
    label_key: str
    question_key: str
    use_key: str
    boundary_key: str
    icon: str
    badge_color: str


PURPOSES = (
    PurposeSpec(
        purpose_id="text_proximity",
        label_key="purpose.text_proximity.label",
        question_key="purpose.text_proximity.question",
        use_key="purpose.text_proximity.use",
        boundary_key="purpose.text_proximity.boundary",
        icon=":material/compare_arrows:",
        badge_color="blue",
    ),
    PurposeSpec(
        purpose_id="group_comparison",
        label_key="purpose.group_comparison.label",
        question_key="purpose.group_comparison.question",
        use_key="purpose.group_comparison.use",
        boundary_key="purpose.group_comparison.boundary",
        icon=":material/groups:",
        badge_color="orange",
    ),
    PurposeSpec(
        purpose_id="style_over_time",
        label_key="purpose.style_over_time.label",
        question_key="purpose.style_over_time.question",
        use_key="purpose.style_over_time.use",
        boundary_key="purpose.style_over_time.boundary",
        icon=":material/timeline:",
        badge_color="green",
    ),
)
PURPOSE_BY_ID = {purpose.purpose_id: purpose for purpose in PURPOSES}


class WorkbenchMode(StrEnum):
    """Modes visible in the shell before workflow implementation."""

    GUIDED = "guided"
    RESEARCH = "research"


MODE_LABEL_KEYS = {
    WorkbenchMode.GUIDED: "mode.guided.label",
    WorkbenchMode.RESEARCH: "mode.research.label",
}
MODE_BODY_KEYS = {
    WorkbenchMode.GUIDED: "mode.guided.body",
    WorkbenchMode.RESEARCH: "mode.research.body",
}


class InterfaceState(StrEnum):
    """Shared presentation states for later asynchronous workflows."""

    EMPTY = "empty"
    LOADING = "loading"
    ERROR = "error"
    CANCELLED = "cancelled"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class StatePresentation:
    """Copy and icon keys for one interface state."""

    label_key: str
    title_key: str
    body_key: str
    icon: str
    badge_color: str


STATE_PRESENTATIONS = {
    InterfaceState.EMPTY: StatePresentation(
        label_key="state.empty.label",
        title_key="state.empty.title",
        body_key="state.empty.body",
        icon=":material/inbox:",
        badge_color="gray",
    ),
    InterfaceState.LOADING: StatePresentation(
        label_key="state.loading.label",
        title_key="state.loading.title",
        body_key="state.loading.body",
        icon=":material/progress_activity:",
        badge_color="blue",
    ),
    InterfaceState.ERROR: StatePresentation(
        label_key="state.error.label",
        title_key="state.error.title",
        body_key="state.error.body",
        icon=":material/error:",
        badge_color="red",
    ),
    InterfaceState.CANCELLED: StatePresentation(
        label_key="state.cancelled.label",
        title_key="state.cancelled.title",
        body_key="state.cancelled.body",
        icon=":material/cancel:",
        badge_color="orange",
    ),
    InterfaceState.COMPLETE: StatePresentation(
        label_key="state.complete.label",
        title_key="state.complete.title",
        body_key="state.complete.body",
        icon=":material/check_circle:",
        badge_color="green",
    ),
}


@dataclass(frozen=True, slots=True)
class RuntimePolicy:
    """P002 runtime features that must remain absent."""

    runtime_ai: bool = False
    analytics: bool = False
    login: bool = False
    permanent_storage: bool = False
    external_endpoints: tuple[str, ...] = ()


RUNTIME_POLICY = RuntimePolicy()
