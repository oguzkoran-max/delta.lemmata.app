from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path
from typing import Any, cast

import pytest
from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "browser_audit_p008",
    ROOT / "scripts" / "browser_audit_p008.py",
)
assert SPEC is not None and SPEC.loader is not None
BROWSER_AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BROWSER_AUDIT)
sys.modules.setdefault("browser_audit_p008", BROWSER_AUDIT)
P009_SPEC = importlib.util.spec_from_file_location(
    "browser_audit_p009",
    ROOT / "scripts" / "browser_audit_p009.py",
)
assert P009_SPEC is not None and P009_SPEC.loader is not None
P009_BROWSER_AUDIT = importlib.util.module_from_spec(P009_SPEC)
P009_SPEC.loader.exec_module(P009_BROWSER_AUDIT)
_download_json = BROWSER_AUDIT._download_json
_choose_selectbox = BROWSER_AUDIT._choose_selectbox
_wait_for_capacity_records = BROWSER_AUDIT._wait_for_capacity_records
_wait_for_streamlit_idle = BROWSER_AUDIT._wait_for_streamlit_idle
_geometry = BROWSER_AUDIT._geometry
_choose_next_result_option = P009_BROWSER_AUDIT._choose_next_result_option
_retry_next_result_option = P009_BROWSER_AUDIT._retry_next_result_option
_wait_for_result_selection_update = P009_BROWSER_AUDIT._wait_for_result_selection_update
_entry_primary_action_max_y = P009_BROWSER_AUDIT._entry_primary_action_max_y
_preload_missing_distinct_owner_job = P009_BROWSER_AUDIT._preload_missing_distinct_owner_job
_semantic_result_parity = P009_BROWSER_AUDIT._semantic_result_parity
_semantic_table_rows = P009_BROWSER_AUDIT._semantic_table_rows
_terminal_payload_cleanup_pass = P009_BROWSER_AUDIT._terminal_payload_cleanup_pass
_result_viewport_pass = P009_BROWSER_AUDIT._result_viewport_pass


class _Download:
    def __init__(self, *, path: Path | None, failure: str | None) -> None:
        self.suggested_filename = "record.json"
        self._path = path
        self._failure = failure
        self.path_called = False

    def failure(self) -> str | None:
        return self._failure

    def path(self) -> Path | None:
        self.path_called = True
        return self._path


class _DownloadInfo:
    def __init__(self, download: _Download) -> None:
        self.value = download

    def __enter__(self) -> _DownloadInfo:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _Button:
    def __init__(self, calls: list[tuple[str, Any]]) -> None:
        self._calls = calls

    def click(self) -> None:
        self._calls.append(("click", None))


class _Page:
    def __init__(self, download: _Download) -> None:
        self.calls: list[tuple[str, Any]] = []
        self._download = download

    def wait_for_function(self, condition: str, *, timeout: float) -> None:
        self.calls.append(("wait_for_function", (condition, timeout)))

    def wait_for_timeout(self, timeout: float) -> None:
        self.calls.append(("wait_for_timeout", timeout))

    def expect_download(self) -> _DownloadInfo:
        self.calls.append(("expect_download", None))
        return _DownloadInfo(self._download)

    def get_by_role(self, role: str, **kwargs: object) -> _Button:
        self.calls.append(("get_by_role", (role, kwargs)))
        return _Button(self.calls)


class _SemanticRows:
    def __init__(self, rows: list[list[str]]) -> None:
        self._rows = rows

    def evaluate_all(self, _script: str) -> list[list[str]]:
        return self._rows


class _SemanticTable:
    def __init__(self, rows: list[list[str]]) -> None:
        self._rows = rows

    def locator(self, selector: str) -> _SemanticRows:
        assert selector == "tbody tr"
        return _SemanticRows(self._rows)


class _SemanticPage:
    def __init__(self, tables: dict[str, list[list[str]]]) -> None:
        self._tables = tables

    def get_by_role(self, role: str, **kwargs: object) -> _SemanticTable:
        assert role == "table"
        assert kwargs["exact"] is True
        return _SemanticTable(self._tables[cast(str, kwargs["name"])])


class _Keyboard:
    def __init__(self, calls: list[tuple[str, Any]]) -> None:
        self._calls = calls

    def press(self, key: str) -> None:
        self._calls.append(("keyboard_press", key))


class _SelectOption:
    def __init__(self, calls: list[tuple[str, Any]], *, require_keyboard: bool) -> None:
        self._calls = calls
        self._require_keyboard = require_keyboard
        self._wait_count = 0

    def wait_for(self, *, state: str, timeout: float) -> None:
        self._wait_count += 1
        self._calls.append(("option_wait", (state, timeout)))
        if self._require_keyboard and self._wait_count == 1:
            raise PlaywrightTimeoutError("option did not open after pointer click")

    def click(self, *, timeout: float) -> None:
        self._calls.append(("option_click", timeout))


class _SelectLocator:
    def __init__(self, calls: list[tuple[str, Any]], selected: str) -> None:
        self._calls = calls
        self._selected = selected

    def wait_for(self, *, state: str, timeout: float) -> None:
        self._calls.append(("locator_wait", (state, timeout)))

    def scroll_into_view_if_needed(self, *, timeout: float) -> None:
        self._calls.append(("locator_scroll", timeout))

    def click(self, *, timeout: float) -> None:
        self._calls.append(("locator_click", timeout))

    def press(self, key: str, *, timeout: float) -> None:
        self._calls.append(("locator_press", (key, timeout)))

    def evaluate(self, _expression: str) -> str:
        self._calls.append(("locator_evaluate", None))
        return self._selected


class _SelectPage(_Page):
    def __init__(self, *, require_keyboard: bool) -> None:
        super().__init__(_Download(path=None, failure=None))
        self.keyboard = _Keyboard(self.calls)
        self.option = _SelectOption(self.calls, require_keyboard=require_keyboard)

    def get_by_role(self, role: str, **kwargs: object) -> _SelectOption:
        self.calls.append(("get_by_role", (role, kwargs)))
        return self.option


class _CapacityRow:
    def __init__(self, cells: tuple[str, ...]) -> None:
        self._cells = cells

    def locator(self, selector: str) -> _CapacityRow:
        assert selector == "th, td"
        return self

    def all_inner_texts(self) -> list[str]:
        return list(self._cells)


class _CapacityRows:
    def __init__(self, snapshots: list[tuple[tuple[str, ...], ...]]) -> None:
        self._snapshots = snapshots
        self._index = 0

    def all(self) -> list[_CapacityRow]:
        snapshot = self._snapshots[min(self._index, len(self._snapshots) - 1)]
        self._index += 1
        return [_CapacityRow(cells) for cells in snapshot]


class _CapacityTable:
    def __init__(self, rows: _CapacityRows) -> None:
        self.rows = rows

    def locator(self, selector: str) -> _CapacityRows:
        assert selector == "tbody tr"
        return self.rows


class _CapacityExpectation:
    def __init__(self, calls: list[tuple[str, Any]]) -> None:
        self._calls = calls

    def to_have_count(self, count: int, *, timeout: float) -> None:
        self._calls.append(("to_have_count", (count, timeout)))


class _CheckedRadio:
    def __init__(self, states: list[bool]) -> None:
        self._states = states
        self._index = 0

    def is_checked(self) -> bool:
        state = self._states[min(self._index, len(self._states) - 1)]
        self._index += 1
        return state


class _FocusableRadio:
    def __init__(self, calls: list[tuple[str, Any]], *, checked: bool) -> None:
        self._calls = calls
        self._checked = checked

    def is_checked(self) -> bool:
        self._calls.append(("radio_is_checked", None))
        return self._checked

    def focus(self) -> None:
        self._calls.append(("radio_focus", None))


class _GeometryPage:
    def __init__(self) -> None:
        self.expression = ""

    def evaluate(self, expression: str) -> dict[str, object]:
        self.expression = expression
        return {}


def test_streamlit_idle_wait_requires_two_connected_not_running_observations() -> None:
    page = _Page(_Download(path=None, failure=None))

    _wait_for_streamlit_idle(cast(Page, page))

    assert [name for name, _value in page.calls] == [
        "wait_for_function",
        "wait_for_timeout",
        "wait_for_function",
    ]
    first_condition, first_timeout = page.calls[0][1]
    assert "data-test-script-state" in first_condition
    assert "notRunning" in first_condition
    assert "data-test-connection-state" in first_condition
    assert "CONNECTED" in first_condition
    assert first_timeout == 15_000
    assert page.calls[1][1] == 250
    assert page.calls[2][1] == page.calls[0][1]


def test_geometry_distinguishes_internal_input_text_scroll_from_box_overflow() -> None:
    page = _GeometryPage()

    _geometry(cast(Page, page))

    assert "box.left < -1 || box.right > root.clientWidth + 1" in page.expression
    assert "element.tagName !== 'INPUT'" in page.expression
    assert "controls.filter(controlOverflows)" in page.expression
    assert "document.fonts.check('16px \"Source Sans Pro\"')" in page.expression


def test_entry_primary_action_uses_the_a51_mobile_fold_budget() -> None:
    assert _entry_primary_action_max_y(375, 844) == 780.0
    assert _entry_primary_action_max_y(390, 844) == 780.0
    assert _entry_primary_action_max_y(320, 800) == 800.0
    assert _entry_primary_action_max_y(1440, 1000) == 1000.0


def test_browser_audit_preloads_one_payload_free_distinct_owner_predecessor(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"

    _preload_missing_distinct_owner_job(runtime_root)

    with sqlite3.connect(runtime_root / "database" / "control.sqlite3") as connection:
        assert connection.execute(
            "SELECT execution_state, COUNT(*) FROM jobs GROUP BY execution_state"
        ).fetchall() == [("queued", 1)]
    assert not (runtime_root / "workspaces").exists()


def test_result_viewport_contract_does_not_require_entry_uploader_evidence() -> None:
    viewport = {
        "horizontal_overflow": False,
        "main_horizontal_overflow": False,
        "overflowing_controls": [],
        "small_targets": [],
        "misframed_table_scroll_regions": [],
        "unscrollable_table_regions": [],
        "visible_h1_count": 1,
        "main_landmark_count": 1,
        "footer_count": 1,
        "inter_font_loaded": True,
        "source_sans_font_loaded": True,
        "persistent_text": {"pass": True},
        "table_regions": {
            "contracts_pass": True,
            "focus_ring_pass": True,
            "keyboard_scroll_pass": True,
        },
        "mfw_radio_layout_pass": True,
        "all_result_cells_visible_pass": True,
        "mds_metric_aspect_pass": True,
        "chart_pixels": ({"pass": True}, {"pass": True}),
    }

    assert "uploader_context_pass" not in viewport
    assert _result_viewport_pass(viewport) is True
    assert _result_viewport_pass({**viewport, "horizontal_overflow": True}) is False


def test_download_json_waits_for_idle_and_rejects_canceled_download() -> None:
    download = _Download(path=None, failure="canceled")
    page = _Page(download)

    with pytest.raises(RuntimeError, match="Browser download failed: canceled"):
        _download_json(cast(Page, page), "Download record")

    assert download.path_called is False
    assert [name for name, _value in page.calls[:4]] == [
        "wait_for_function",
        "wait_for_timeout",
        "wait_for_function",
        "expect_download",
    ]
    assert page.calls[-1] == ("click", None)


def test_download_json_reads_successful_payload_after_idle(tmp_path: Path) -> None:
    record = tmp_path / "record.json"
    record.write_text('{"schema_version":"1.0.0"}', encoding="utf-8")
    download = _Download(path=record, failure=None)
    page = _Page(download)

    filename, payload = _download_json(cast(Page, page), "Download record")

    assert filename == "record.json"
    assert payload == {"schema_version": "1.0.0"}
    assert download.path_called is True


def test_choose_selectbox_uses_semantic_option_without_force_or_fill() -> None:
    page = _SelectPage(require_keyboard=False)
    locator = _SelectLocator(page.calls, "1000 MFW")

    _choose_selectbox(cast(Page, page), cast(Locator, locator), "1000 MFW")

    assert ("locator_click", 5_000) in page.calls
    assert ("option_click", 5_000) in page.calls
    assert not any(name in {"locator_fill", "force_click"} for name, _value in page.calls)
    assert [name for name, _value in page.calls].count("wait_for_function") == 4
    assert ("keyboard_press", "Escape") not in page.calls


def test_choose_selectbox_uses_arrow_key_only_when_pointer_does_not_open_list() -> None:
    page = _SelectPage(require_keyboard=True)
    locator = _SelectLocator(page.calls, "1000 MFW")

    _choose_selectbox(cast(Page, page), cast(Locator, locator), "1000 MFW")

    assert ("locator_press", ("ArrowDown", 2_000)) in page.calls
    assert [name for name, _value in page.calls].count("option_wait") == 2
    assert ("option_click", 5_000) in page.calls


def test_capacity_records_wait_for_four_rows_and_two_stable_snapshots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = tuple((str(mfw), "1100", "Available") for mfw in (100, 300, 500, 1000))
    rows = _CapacityRows([records, records])
    table = _CapacityTable(rows)
    page = _Page(_Download(path=None, failure=None))
    monkeypatch.setattr(
        BROWSER_AUDIT,
        "expect",
        lambda _rows: _CapacityExpectation(page.calls),
    )

    observed = _wait_for_capacity_records(cast(Page, page), cast(Locator, table))

    assert observed == records
    assert ("to_have_count", (4, 15_000)) in page.calls
    assert [name for name, _value in page.calls].count("wait_for_function") == 2
    assert [name for name, _value in page.calls].count("wait_for_timeout") == 2


def test_capacity_records_reject_changed_or_incomplete_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tuple((str(mfw), "1100", "Available") for mfw in (100, 300, 500, 1000))
    second = (*first[:-1], ("1000", "1100"))
    rows = _CapacityRows([first, second])
    table = _CapacityTable(rows)
    page = _Page(_Download(path=None, failure=None))
    monkeypatch.setattr(
        BROWSER_AUDIT,
        "expect",
        lambda _rows: _CapacityExpectation(page.calls),
    )

    with pytest.raises(RuntimeError, match="MFW capacity table did not settle"):
        _wait_for_capacity_records(cast(Page, page), cast(Locator, table))


def test_result_selection_waits_for_changed_stable_semantic_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = {
        "Classic Delta distance matrix": {"sha256": "old-matrix", "row_count": 3},
        "MDS coordinate table": {"sha256": "old-mds", "row_count": 3},
    }
    observations = iter(
        (
            {"sha256": "old-matrix", "row_count": 3},
            {"sha256": "old-mds", "row_count": 3},
            {"sha256": "new-matrix", "row_count": 3},
            {"sha256": "new-mds", "row_count": 3},
            {"sha256": "new-matrix", "row_count": 3},
            {"sha256": "new-mds", "row_count": 3},
        )
    )
    monkeypatch.setattr(
        P009_BROWSER_AUDIT,
        "_semantic_table_evidence",
        lambda _page, _label: next(observations),
    )
    page = _Page(_Download(path=None, failure=None))
    radio = _CheckedRadio([False, True, True])

    observed = _wait_for_result_selection_update(
        cast(Page, page),
        cast(Locator, radio),
        before,
        attempts=3,
    )

    assert observed == {
        "Classic Delta distance matrix": {"sha256": "new-matrix", "row_count": 3},
        "MDS coordinate table": {"sha256": "new-mds", "row_count": 3},
    }
    assert ("wait_for_timeout", 250) in page.calls


def test_semantic_table_rows_normalize_cells() -> None:
    page = _SemanticPage({"Matrix": [[" D01 ", " 0.000000\n"]]})

    assert _semantic_table_rows(cast(Page, page), "Matrix") == (("D01", "0.000000"),)


def test_semantic_result_parity_binds_tables_to_exported_matrix_and_mds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exported = {
        "documents": [
            {"key": "D01", "title": "Early work", "role": "known"},
            {"key": "D02", "title": "Late work", "role": "known"},
        ],
        "cells": [
            {
                "mfw": 500,
                "culling_percent": 0,
                "distance": "classic_delta",
                "is_reference": True,
                "status": "complete",
                "error_code": None,
                "matrix": {
                    "document_keys": ["D01", "D02"],
                    "values": [[0.0, 2.0], [2.0, 0.0]],
                },
            }
        ],
    }
    expected = {
        "Classic Delta distance matrix": (
            ("D01", "0.000000", "2.000000"),
            ("D02", "2.000000", "0.000000"),
        ),
        "MDS coordinate table": (
            ("Early work", "known", "1.000000", "0.000000"),
            ("Late work", "known", "-1.000000", "0.000000"),
        ),
    }
    monkeypatch.setattr(
        P009_BROWSER_AUDIT,
        "_semantic_table_rows",
        lambda _page, label: expected[label],
    )

    evidence = _semantic_result_parity(cast(Page, object()), exported, 500)

    assert evidence["matrix_export_parity_pass"] is True
    assert evidence["mds_matrix_parity_pass"] is True
    assert evidence["matrix_expected_sha256"] == evidence["matrix_observed_sha256"]
    assert evidence["mds_expected_sha256"] == evidence["mds_observed_sha256"]

    monkeypatch.setattr(
        P009_BROWSER_AUDIT,
        "_semantic_table_rows",
        lambda _page, label: (
            (("D01", "0.000000", "9.000000"),) if label.startswith("Classic") else expected[label]
        ),
    )
    mismatch = _semantic_result_parity(cast(Page, object()), exported, 500)
    assert mismatch["matrix_export_parity_pass"] is False
    assert mismatch["mds_matrix_parity_pass"] is True


def test_result_selection_uses_native_keyboard_change_event() -> None:
    page = _SelectPage(require_keyboard=False)
    radio = _FocusableRadio(page.calls, checked=True)

    _choose_next_result_option(cast(Page, page), cast(Locator, radio))

    assert page.calls == [
        ("radio_is_checked", None),
        ("radio_focus", None),
        ("keyboard_press", "ArrowRight"),
    ]


def test_result_selection_rejects_an_unchecked_reference() -> None:
    page = _SelectPage(require_keyboard=False)
    radio = _FocusableRadio(page.calls, checked=False)

    with pytest.raises(RuntimeError, match="reference option to be checked"):
        _choose_next_result_option(cast(Page, page), cast(Locator, radio))

    assert page.calls == [("radio_is_checked", None)]


def test_result_selection_retry_replays_one_native_back_forward_change() -> None:
    page = _SelectPage(require_keyboard=False)
    reference = _FocusableRadio(page.calls, checked=True)
    target = _FocusableRadio(page.calls, checked=True)

    _retry_next_result_option(
        cast(Page, page),
        cast(Locator, reference),
        cast(Locator, target),
    )

    assert page.calls == [
        ("radio_is_checked", None),
        ("radio_focus", None),
        ("keyboard_press", "ArrowLeft"),
        ("wait_for_timeout", 250),
        ("radio_is_checked", None),
        ("radio_focus", None),
        ("keyboard_press", "ArrowRight"),
    ]


def test_result_selection_retry_repeats_forward_change_when_target_is_unchecked() -> None:
    page = _SelectPage(require_keyboard=False)
    reference = _FocusableRadio(page.calls, checked=True)
    target = _FocusableRadio(page.calls, checked=False)

    _retry_next_result_option(
        cast(Page, page),
        cast(Locator, reference),
        cast(Locator, target),
    )

    assert page.calls == [
        ("radio_is_checked", None),
        ("radio_is_checked", None),
        ("radio_focus", None),
        ("keyboard_press", "ArrowRight"),
    ]


def test_result_selection_rejects_unchanged_semantic_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = {
        "Classic Delta distance matrix": {"sha256": "old-matrix", "row_count": 3},
        "MDS coordinate table": {"sha256": "old-mds", "row_count": 3},
    }
    monkeypatch.setattr(
        P009_BROWSER_AUDIT,
        "_semantic_table_evidence",
        lambda _page, label: before[label],
    )
    page = _Page(_Download(path=None, failure=None))
    radio = _CheckedRadio([True])

    with pytest.raises(RuntimeError, match="stable semantic-table update"):
        _wait_for_result_selection_update(
            cast(Page, page),
            cast(Locator, radio),
            before,
            attempts=2,
        )


@pytest.mark.parametrize(
    "diagnostics",
    (
        {"available": False},
        {"available": True, "records": None},
        {"available": True, "records": []},
        {"available": True, "records": ["not-a-record"]},
        {
            "available": True,
            "records": [
                {
                    "execution_state": "terminal",
                    "artifact_states": {"input": "present", "work": "verified_absent"},
                }
            ],
        },
    ),
)
def test_terminal_payload_cleanup_rejects_incomplete_evidence(
    diagnostics: dict[str, object],
) -> None:
    assert _terminal_payload_cleanup_pass(diagnostics) is False


def test_terminal_payload_cleanup_accepts_only_terminal_verified_absence() -> None:
    diagnostics = {
        "available": True,
        "records": [
            {
                "execution_state": "terminal",
                "artifact_states": {
                    "input": "verified_absent",
                    "work": "verified_absent",
                },
            }
        ],
    }

    assert _terminal_payload_cleanup_pass(diagnostics) is True
