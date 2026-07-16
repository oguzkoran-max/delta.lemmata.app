#!/usr/bin/env python3
"""Run the reproducible P008 upload-to-real-stylo browser audit."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Browser, Locator, Page, expect, sync_playwright
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = (
    ("desktop-1280x900", 1280, 900),
    ("mobile-390x844", 390, 844),
    ("reflow-320x800", 320, 800),
)
GUIDED_MFW = (100, 300, 500, 1000)
FEATURE_COUNT = 1_100
_STREAMLIT_SETTLE_MS = 250


def _free_port() -> int:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def _wait_for_health(url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 45
    health_url = f"{url}/_stcore/health"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Streamlit exited before becoming healthy")
        try:
            with urllib.request.urlopen(health_url, timeout=1) as response:  # noqa: S310
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"Streamlit did not become healthy at {health_url}")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _observe_console(page: Page, messages: list[dict[str, str]]) -> None:
    def record(message: Any) -> None:
        if message.type in {"error", "warning"}:
            messages.append({"type": message.type, "text": message.text})

    page.on("console", record)
    page.on("pageerror", lambda error: messages.append({"type": "pageerror", "text": str(error)}))


def _word(index: int) -> str:
    """Return a deterministic letters-only token accepted by the fixed tokenizer."""

    value = index
    suffix = []
    for _ in range(4):
        value, remainder = divmod(value, 26)
        suffix.append(chr(ord("a") + remainder))
    return "lex" + "".join(reversed(suffix))


def _synthetic_corpus() -> tuple[tuple[str, bytes], ...]:
    """Build three non-identical whole texts with 1,100 shared varying features."""

    features = tuple(_word(index) for index in range(FEATURE_COUNT))
    steps = (1, 7, 13)
    offsets = (0, 37, 83)
    documents = []
    for document_index, (step, offset) in enumerate(zip(steps, offsets, strict=True)):
        if math.gcd(step, FEATURE_COUNT) != 1:
            raise RuntimeError("Synthetic permutation step is not coprime")
        tokens = []
        for position in range(FEATURE_COUNT):
            feature_index = (position * step + offset) % FEATURE_COUNT
            repeat = 1 + ((feature_index + document_index) % 3)
            tokens.extend((features[feature_index],) * repeat)
        payload = (" ".join(tokens) + "\n").encode("utf-8")
        documents.append((f"delta_synthetic_{document_index + 1}.txt", payload))
    return tuple(documents)


def _wait_until_enabled(page: Page, locator: Locator, *, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if locator.is_enabled():
            return True
        page.wait_for_timeout(100)
    return locator.is_enabled()


def _wait_for_streamlit_idle(page: Page, *, timeout_ms: float = 15_000) -> None:
    condition = """() => {
      const app = document.querySelector('[data-testid="stApp"]');
      return app?.getAttribute('data-test-script-state') === 'notRunning'
        && app?.getAttribute('data-test-connection-state') === 'CONNECTED';
    }"""
    page.wait_for_function(condition, timeout=timeout_ms)
    page.wait_for_timeout(_STREAMLIT_SETTLE_MS)
    page.wait_for_function(condition, timeout=timeout_ms)


def _wait_for_capacity_records(page: Page, table: Locator) -> tuple[tuple[str, ...], ...]:
    """Read the complete capacity table only after its rendered rows settle."""

    rows = table.locator("tbody tr")
    expect(rows).to_have_count(len(GUIDED_MFW), timeout=15_000)
    _wait_for_streamlit_idle(page)

    def snapshot() -> tuple[tuple[str, ...], ...]:
        return tuple(
            tuple(cell.strip() for cell in row.locator("th, td").all_inner_texts())
            for row in rows.all()
        )

    first = snapshot()
    page.wait_for_timeout(_STREAMLIT_SETTLE_MS)
    second = snapshot()
    if first != second or any(len(row) < 3 for row in second):
        raise RuntimeError(
            "MFW capacity table did not settle with complete rows: "
            f"first={first!r}; second={second!r}"
        )
    return second


def _choose_selectbox(page: Page, locator: Locator, option: str) -> None:
    option_locator = page.get_by_role("option", name=option, exact=True)
    last_error = "no option interaction attempted"
    for _ in range(3):
        try:
            _wait_for_streamlit_idle(page)
            locator.wait_for(state="visible", timeout=5_000)
            locator.scroll_into_view_if_needed(timeout=5_000)
            locator.click(timeout=5_000)
            try:
                option_locator.wait_for(state="visible", timeout=2_000)
            except PlaywrightTimeoutError:
                locator.press("ArrowDown", timeout=2_000)
                option_locator.wait_for(state="visible", timeout=5_000)
            option_locator.click(timeout=5_000)
            _wait_for_streamlit_idle(page)
            rendered = locator.evaluate(
                """element => {
                  let current = element;
                  for (let depth = 0; depth < 8 && current; depth += 1) {
                    const text = (current.textContent || '').trim();
                    if (text.includes('Analysis only') || text.includes('MFW')) {
                      return text;
                    }
                    current = current.parentElement;
                  }
                  return (element.value || '').trim();
                }"""
            )
            if option in str(rendered):
                return
            last_error = "selected option was not retained after the Streamlit rerun"
        except PlaywrightTimeoutError as error:
            last_error = str(error).splitlines()[0]
        except Exception as error:
            last_error = f"{type(error).__name__}: {error}"
        page.keyboard.press("Escape")
    raise RuntimeError(
        f"Selectbox option did not become available: {option}; last_error={last_error}"
    )


def _geometry(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const root = document.documentElement;
          const main = document.querySelector('[data-testid="stMainBlockContainer"]');
          const visible = element => {
            const style = getComputedStyle(element);
            const box = element.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden'
              && box.width > 0 && box.height > 0;
          };
          const controls = [...document.querySelectorAll(
            '[data-testid="stMainBlockContainer"] button, '
            + '[data-testid="stMainBlockContainer"] input:not([type="file"]), '
            + '[data-testid="stMainBlockContainer"] [role="radiogroup"]'
          )].filter(visible);
          const tableScrollRegions = [...document.querySelectorAll(
            '[data-testid="stMainBlockContainer"] .delta-table-scroll'
          )].filter(visible);
          return {
            scrollWidth: root.scrollWidth,
            clientWidth: root.clientWidth,
            mainScrollWidth: main?.scrollWidth || 0,
            mainClientWidth: main?.clientWidth || 0,
            overflowingControls: controls.filter(
              element => element.scrollWidth > element.clientWidth + 1
            ).map(element => ({
              tag: element.tagName,
              text: (element.textContent || element.getAttribute('aria-label') || '')
                .trim().slice(0, 80),
              clientWidth: element.clientWidth,
              scrollWidth: element.scrollWidth
            })),
            misframedTableScrollRegions: tableScrollRegions.filter(element => {
              const box = element.getBoundingClientRect();
              return box.left < -1 || box.right > root.clientWidth + 1;
            }).map(element => ({
              left: element.getBoundingClientRect().left,
              right: element.getBoundingClientRect().right,
              viewportWidth: root.clientWidth
            }))
          };
        }"""
    )


def _download_json(page: Page, button_name: str) -> tuple[str, dict[str, Any]]:
    _wait_for_streamlit_idle(page)
    with page.expect_download() as download_info:
        page.get_by_role("button", name=button_name, exact=False).click()
    download = download_info.value
    failure = download.failure()
    if failure is not None:
        raise RuntimeError(f"Browser download failed: {failure}")
    path = download.path()
    if path is None:
        raise RuntimeError("Browser download has no local path")
    return download.suggested_filename, json.loads(path.read_text(encoding="utf-8"))


def _document_corpus(
    page: Page,
    documents: tuple[tuple[str, bytes], ...],
    output: Path,
) -> None:
    page.get_by_role("region", name="Corpus texts (.txt)", exact=True).locator(
        'input[type="file"]'
    ).set_input_files(
        [{"name": name, "mimeType": "text/plain", "buffer": payload} for name, payload in documents]
    )
    page.get_by_text("Intake checks passed · Uploads: 3", exact=False).wait_for()
    page.get_by_role("button", name="Continue to describe the corpus", exact=True).click()
    page.get_by_role("heading", name="Describe what each text represents", level=2).wait_for()

    def document_field(group_label: str, label: str, *, role: str | None = None) -> Locator:
        last_state = "unresolved"
        for _ in range(6):
            expander = page.locator('[data-testid="stExpander"]').filter(
                has=page.get_by_text(group_label, exact=True)
            )
            details = expander.locator("details")
            try:
                details.wait_for(state="attached", timeout=5_000)
                field = (
                    details.get_by_role(role, name=label, exact=True)
                    if role is not None
                    else details.get_by_label(label, exact=True)
                )
                if not field.is_visible() and details.get_attribute("open") is None:
                    summary = details.locator("summary")
                    summary.wait_for(state="visible", timeout=5_000)
                    summary.click(timeout=5_000)
                field.wait_for(state="visible", timeout=5_000)
                return field
            except PlaywrightError:
                try:
                    last_state = (
                        "open"
                        if details.get_attribute("open", timeout=1_000) is not None
                        else "closed"
                    )
                except PlaywrightError:
                    last_state = "rerendering"
                page.wait_for_timeout(250)
        raise RuntimeError(
            f"Document field did not become visible: {group_label} -> {label}; "
            f"expander_state={last_state}"
        )

    def fill_document_field(group_label: str, label: str, value: str) -> None:
        last_value = ""
        for _ in range(5):
            field = document_field(group_label, label)
            field.fill(value)
            field.press("Tab")
            page.wait_for_timeout(500)
            try:
                last_value = document_field(group_label, label).input_value(timeout=3_000)
            except PlaywrightTimeoutError:
                last_value = ""
            if last_value == value:
                return
        raise RuntimeError(
            f"Document field did not retain its value: {group_label} -> {label}; "
            f"last_value={last_value!r}"
        )

    for index, (name, _payload) in enumerate(documents):
        group_label = f"{index + 1}. {name}"
        fill_document_field(group_label, "Primary author name", "Delta Synthetic Author")
        fill_document_field(
            group_label,
            "Bibliographic citation",
            f"Synthetic P008 browser-audit source record for {name}.",
        )
        rights = document_field(
            group_label,
            "Documented rights state",
            role="combobox",
        )
        _choose_selectbox(
            page,
            rights,
            "Analysis only · permit upload and analysis, prohibit text export",
        )

    for index, (name, _payload) in enumerate(documents):
        group_label = f"{index + 1}. {name}"
        expected = {
            "Primary author name": "Delta Synthetic Author",
            "Bibliographic citation": f"Synthetic P008 browser-audit source record for {name}.",
        }
        for label, value in expected.items():
            retained = document_field(group_label, label).input_value(timeout=3_000)
            if retained != value:
                fill_document_field(group_label, label, value)

    page.get_by_role("button", name="Build corpus review", exact=True).click()
    review_heading = page.get_by_role("heading", name="Review the documented corpus", level=2)
    try:
        review_heading.wait_for()
    except Exception:
        page.screenshot(
            path=str(output / "screenshots" / "documentation-failure.png"),
            full_page=True,
        )
        alerts = page.locator('[data-testid="stAlert"]').all_inner_texts()
        raise RuntimeError(f"Documentation did not reach review: {alerts!r}") from None


def _confirm_and_prepare(page: Page, output: Path) -> dict[str, Any]:
    review_ready = (
        page.get_by_text("Corpus documentation has no blockers", exact=False).count() == 1
    )
    confirmation = page.get_by_role(
        "checkbox",
        name="I reviewed the file-to-work mappings and the documented rights records.",
        exact=True,
    )
    confirmation_enabled = _wait_until_enabled(page, confirmation)
    confirmation_recorded = False
    if confirmation_enabled:
        confirmation.focus()
        page.keyboard.press("Space")
        page.get_by_text("Confirmation recorded for this inventory.", exact=True).wait_for()
        confirmation_recorded = confirmation.is_checked()
    continue_button = page.get_by_role("button", name="Continue to corpus preparation", exact=False)
    try:
        continue_button.wait_for()
    except Exception:
        page.screenshot(
            path=str(output / "screenshots" / "review-continuation-failure.png"),
            full_page=True,
        )
        messages = page.locator('[data-testid="stAlert"]').all_inner_texts()
        raise RuntimeError(f"Review could not continue: {messages!r}") from None
    continue_button.click()
    page.get_by_role("heading", name="Prepare and check the corpus", level=2).wait_for()
    page.get_by_role("button", name="Prepare texts and check corpus health", exact=False).click()
    page.get_by_text("Computational preflight passed", exact=False).wait_for(timeout=60_000)

    capacity = page.get_by_role(
        "table", name="Which MFW settings can this corpus support?", exact=True
    )
    capacity_records = _wait_for_capacity_records(page, capacity)
    requested_mfw = tuple(int(re.sub(r"\D", "", row[0])) for row in capacity_records if row)
    available_features = tuple(
        int(re.sub(r"\D", "", row[1])) for row in capacity_records if len(row) >= 2
    )
    preparation = {
        "review_ready_pass": review_ready,
        "confirmation_enabled_pass": confirmation_enabled,
        "confirmation_recorded_pass": confirmation_recorded,
        "preflight_ready_pass": page.get_by_text(
            "Computational preflight passed", exact=False
        ).count()
        == 1,
        "candidate_feature_count_pass": available_features == (FEATURE_COUNT,) * len(GUIDED_MFW),
        "all_mfw_available_pass": requested_mfw == GUIDED_MFW
        and all(len(row) >= 3 and row[2] == "Available" for row in capacity_records),
        "capacity_records": capacity_records,
    }
    page.get_by_role("button", name="Continue to parameter review", exact=False).click()
    page.get_by_role("heading", name="Review what Delta will calculate", level=2).wait_for()
    return preparation


def _audit_parameters(page: Page, output: Path) -> dict[str, Any]:
    table = page.get_by_role("table", name="Guided parameter comparison grid", exact=True)
    rows = table.locator("tbody tr")
    row_mfw = tuple(int(row.locator("th").inner_text()) for row in rows.all())
    reference_rows = table.locator('tbody tr[data-reference="true"]')
    initial_run = page.get_by_role("button", name="Run the four comparisons", exact=False)
    initial_disabled = initial_run.is_disabled()

    page.get_by_role("radio", name="Research", exact=True).click()
    page.get_by_text("Research Mode is not available in this public alpha.", exact=True).wait_for()
    research_locked = (
        page.get_by_text("Research Mode is not available in this public alpha.", exact=True).count()
        == 1
    )
    page.screenshot(path=str(output / "screenshots" / "research-mode-locked.png"), full_page=True)
    page.get_by_role("radio", name="Guided", exact=True).click()
    table.wait_for()

    filename, config = _download_json(page, "Download resolved parameter record")
    config_pass = (
        filename == "delta-resolved-workflow-config-v1.json"
        and config.get("schema_version") == "resolved-workflow-config-v1"
        and config.get("mode") == "guided"
        and config.get("parameter_profile") == "guided-grid-v1"
        and config.get("analysis_unit") == "whole_text"
        and config.get("seed") == 20260713
        and config.get("cell_count") == 4
        and [cell.get("mfw") for cell in config.get("cells", [])] == list(GUIDED_MFW)
        and {cell.get("culling_percent") for cell in config.get("cells", [])} == {0}
        and {cell.get("distance") for cell in config.get("cells", [])} == {"classic_delta"}
    )

    viewport_results = []
    for target, width, height in VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(250)
        geometry = _geometry(page)
        screenshot = output / "screenshots" / f"parameters-{target}.png"
        page.screenshot(path=str(screenshot), full_page=True)
        viewport_results.append(
            {
                "target": target,
                "viewport": {"width": width, "height": height},
                "horizontal_overflow": geometry["scrollWidth"] > geometry["clientWidth"],
                "main_horizontal_overflow": (
                    geometry["mainScrollWidth"] > geometry["mainClientWidth"]
                ),
                "overflowing_controls": geometry["overflowingControls"],
                "misframed_table_scroll_regions": geometry["misframedTableScrollRegions"],
                "screenshot": _display_path(screenshot),
            }
        )

    page.set_viewport_size({"width": 1280, "height": 900})
    page.wait_for_timeout(250)
    return {
        "parameter_rows_pass": row_mfw == GUIDED_MFW,
        "reference_row_pass": reference_rows.count() == 1
        and reference_rows.locator("th").inner_text() == "500",
        "semantic_table_pass": table.count() == 1,
        "beginner_explanations_pass": all(
            page.get_by_text(label, exact=True).count() >= 1
            for label in (
                "Most frequent words (MFW)",
                "Culling",
                "Classic Delta",
                "Why 500 MFW is the display reference",
            )
        ),
        "interpretive_boundary_pass": page.get_by_text(
            "These comparisons describe relative stylistic proximity", exact=False
        ).count()
        == 1,
        "research_locked_pass": research_locked,
        "run_initially_disabled_pass": initial_disabled,
        "config_download_pass": config_pass,
        "viewport_pass": all(
            not item["horizontal_overflow"]
            and not item["main_horizontal_overflow"]
            and not item["overflowing_controls"]
            and not item["misframed_table_scroll_regions"]
            for item in viewport_results
        ),
        "viewports": viewport_results,
    }


def _run_analysis(page: Page, output: Path, canary: str) -> dict[str, Any]:
    confirmation = page.get_by_role(
        "checkbox",
        name="I reviewed the four comparisons and their interpretation limits.",
        exact=True,
    )
    confirmation.focus()
    page.keyboard.press("Space")
    run_button = page.get_by_role("button", name="Run the four comparisons", exact=False)
    enabled_after_confirmation = _wait_until_enabled(page, run_button)
    if not enabled_after_confirmation:
        raise RuntimeError("Run control did not become enabled after confirmation")
    run_button.focus()
    page.keyboard.press("Enter")
    terminal = page.get_by_text(
        re.compile(
            r"Finalizing analysis|Analysis failed|Delta could not complete this bounded analysis"
        )
    )
    try:
        terminal.first.wait_for(timeout=75_000)
    except PlaywrightTimeoutError:
        timeout_screenshot = output / "screenshots" / "analysis-timeout.png"
        page.screenshot(path=str(timeout_screenshot), full_page=True)
        messages = page.locator('[data-testid="stAlert"]').all_inner_texts()
        headings = page.locator("h1, h2, h3").all_inner_texts()
        raise RuntimeError(
            f"Real worker produced no terminal UI: alerts={messages!r}; headings={headings!r}"
        ) from None
    # P008 ends at a validated scientific result. P009 owns the export-backed
    # result surface that changes this lifecycle state to "Analysis complete".
    if page.get_by_text("Finalizing analysis", exact=True).count() != 1:
        failure_screenshot = output / "screenshots" / "analysis-failure.png"
        page.screenshot(path=str(failure_screenshot), full_page=True)
        messages = page.locator('[data-testid="stAlert"]').all_inner_texts()
        raise RuntimeError(f"Real worker did not succeed: {messages!r}")
    screenshot = output / "screenshots" / "validated-p006-result.png"
    page.screenshot(path=str(screenshot), full_page=True)
    body = page.locator("body").inner_text()
    return {
        "run_enabled_after_confirmation_pass": enabled_after_confirmation,
        "real_worker_success_pass": page.get_by_text("Finalizing analysis", exact=True).count()
        == 1,
        "p008_boundary_pass": page.get_by_text("Analysis complete", exact=True).count() == 0
        and page.get_by_text(
            "The run finished. Temporary inputs are being removed before results become available.",
            exact=True,
        ).count()
        == 1,
        "p009_boundary_pass": page.get_by_text(
            "Evidence review and result visualizations are the next step.", exact=False
        ).count()
        == 1,
        "payload_absent_pass": canary not in body,
        "screenshot": _display_path(screenshot),
    }


def _audit_flow(
    browser: Browser,
    url: str,
    requests: list[str],
    console_messages: list[dict[str, str]],
    output: Path,
) -> dict[str, Any]:
    documents = _synthetic_corpus()
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.on("request", lambda request: requests.append(request.url))
    _observe_console(page, console_messages)
    page.goto(url, wait_until="networkidle")
    page.get_by_role("heading", name="Discover patterns in writing style.", level=1).wait_for()
    _document_corpus(page, documents, output)
    preparation = _confirm_and_prepare(page, output)
    parameters = _audit_parameters(page, output)
    analysis = _run_analysis(page, output, _word(0))
    context.close()
    return {"preparation": preparation, "parameters": parameters, "analysis": analysis}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if sys.platform != "linux":
        print(
            json.dumps(
                {
                    "result": "not-run",
                    "reason": "P008_REAL_WORKER_BROWSER_AUDIT_REQUIRES_CANONICAL_LINUX",
                }
            )
        )
        return 2
    output = arguments.output.resolve()

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )

    (output / "screenshots").mkdir(parents=True, exist_ok=True)
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment["DELTA_BUILD_ID"] = "p008-real-worker-browser-audit"
    server_log_path = output / "streamlit-server.log"
    with server_log_path.open("w", encoding="utf-8") as server_log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.headless=true",
                f"--server.port={port}",
                "--server.address=127.0.0.1",
                "--browser.gatherUsageStats=false",
            ],
            cwd=ROOT,
            env=environment,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            _wait_for_health(url, process)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                requests: list[str] = []
                console_messages: list[dict[str, str]] = []
                flow = _audit_flow(browser, url, requests, console_messages, output)
                browser.close()

            external_hosts = sorted(
                {
                    parsed.hostname
                    for request_url in requests
                    if (parsed := urlparse(request_url)).hostname not in {"127.0.0.1", "localhost"}
                }
            )
            boolean_results = [
                value
                for section in flow.values()
                for key, value in section.items()
                if key.endswith("_pass")
            ]
            passed = all(boolean_results) and not external_hosts and not console_messages
            result = {
                "schema_version": "1.0.0",
                "git_commit": commit,
                "git_dirty": dirty,
                "target_url": url,
                "audit_method": (
                    "Tracked Python Playwright harness, fresh local Streamlit process, "
                    "synthetic whole texts, and the production R/stylo worker boundary."
                ),
                "synthetic_inputs_only": True,
                "synthetic_document_count": 3,
                "synthetic_candidate_feature_target": FEATURE_COUNT,
                "flow": flow,
                "console_messages": console_messages,
                "external_hosts_observed": external_hosts,
                "network_scope": "Browser requests observed by Playwright; not a packet capture.",
                "result": "passed" if passed else "failed",
            }
            (output / "browser-audit.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(json.dumps({"result": result["result"], "output": _display_path(output)}))
            return 0 if passed else 1
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
