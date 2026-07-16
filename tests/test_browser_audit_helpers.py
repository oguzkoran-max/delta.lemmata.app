from __future__ import annotations

import importlib.util
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
_download_json = BROWSER_AUDIT._download_json
_choose_selectbox = BROWSER_AUDIT._choose_selectbox
_wait_for_streamlit_idle = BROWSER_AUDIT._wait_for_streamlit_idle


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
