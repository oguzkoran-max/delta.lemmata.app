from __future__ import annotations

from delta_lemmata.workbench import (
    PURPOSES,
    STATE_PRESENTATIONS,
    InterfaceState,
    WorkbenchMode,
)


def test_workbench_has_exactly_three_first_class_research_purposes() -> None:
    assert tuple(purpose.purpose_id for purpose in PURPOSES) == (
        "text_proximity",
        "group_comparison",
        "style_over_time",
    )
    assert len({purpose.icon for purpose in PURPOSES}) == 3


def test_workbench_modes_are_guided_and_research() -> None:
    assert tuple(mode.value for mode in WorkbenchMode) == ("guided", "research")


def test_state_contract_is_complete_and_versionable() -> None:
    assert set(STATE_PRESENTATIONS) == set(InterfaceState)
    assert tuple(state.value for state in InterfaceState) == (
        "empty",
        "loading",
        "error",
        "cancelled",
        "complete",
    )
    for presentation in STATE_PRESENTATIONS.values():
        assert presentation.icon.startswith(":material/")
        assert presentation.icon.endswith(":")
