#!/usr/bin/env python3
"""Run the reproducible P003 browser, intake, reflow, and egress audit."""

from __future__ import annotations

import argparse
import io
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = (
    ("desktop-1440x1000", 1440, 1000),
    ("desktop-1280x800", 1280, 800),
    ("mobile-390x844", 390, 844),
    ("mobile-360x800", 360, 800),
    ("reflow-640x800", 640, 800),
    ("reflow-320x800", 320, 800),
)
EXPECTED_HEADINGS = [
    {"level": 1, "name": "Set the research purpose"},
    {"level": 2, "name": "Text Proximity"},
    {"level": 2, "name": "Choose the level of control"},
    {"level": 2, "name": "Validate the research corpus"},
    {"level": 2, "name": "Experiment map"},
    {"level": 2, "name": "Method boundary"},
    {"level": 2, "name": "Evidence reserved with every run"},
    {"level": 2, "name": "No analysis run yet"},
]
DISABLED_BUTTONS = (
    "Continue - corpus documentation is not connected",
    "Run analysis - unavailable until setup is complete",
)


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


def _boxes_overlap(first: dict[str, float] | None, second: dict[str, float] | None) -> bool:
    if first is None or second is None:
        return False
    return not (
        first["x"] + first["width"] <= second["x"]
        or second["x"] + second["width"] <= first["x"]
        or first["y"] + first["height"] <= second["y"]
        or second["y"] + second["height"] <= first["y"]
    )


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _heading_outline(page: Page) -> list[dict[str, Any]]:
    return page.locator("h1, h2, h3").evaluate_all(
        """elements => elements.filter(element => {
          const style = getComputedStyle(element);
          const box = element.getBoundingClientRect();
          return style.visibility !== 'hidden' && style.display !== 'none' && box.height > 0;
        }).map(element => ({
          level: Number(element.tagName.substring(1)),
          name: element.textContent.trim()
        }))"""
    )


def _console_observer(page: Page, messages: list[dict[str, str]]) -> None:
    def record(message: Any) -> None:
        if message.type in {"error", "warning"}:
            messages.append({"type": message.type, "text": message.text})

    page.on("console", record)
    page.on("pageerror", lambda error: messages.append({"type": "pageerror", "text": str(error)}))


def _audit_viewport(
    page: Page, url: str, target: str, width: int, height: int, output: Path
) -> dict[str, Any]:
    page.goto(url, wait_until="networkidle")
    page.get_by_role("heading", name="Set the research purpose", level=1).wait_for()
    geometry = page.evaluate(
        """() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          mainClientWidth: document.querySelector('[data-testid="stMainBlockContainer"]')
            ?.clientWidth ?? null,
          mainScrollWidth: document.querySelector('[data-testid="stMainBlockContainer"]')
            ?.scrollWidth ?? null,
          overflowingControls: [...document.querySelectorAll(
            '[data-testid="stMainBlockContainer"] button, '
            + '[data-testid="stMainBlockContainer"] [role="radiogroup"], '
            + '[data-testid="stMainBlockContainer"] [data-testid="stFileUploaderDropzone"]'
          )].filter(element => element.scrollWidth > element.clientWidth + 1).map(element => ({
            text: element.textContent.trim().slice(0, 80),
            clientWidth: element.clientWidth,
            scrollWidth: element.scrollWidth
          })).slice(0, 20)
        })"""
    )
    sidebar = page.locator('[data-testid="stSidebar"]')
    main = page.locator('[data-testid="stMain"]')
    sidebar_box = sidebar.bounding_box() if sidebar.is_visible() else None
    main_box = main.bounding_box() if main.is_visible() else None
    mobile = width <= 760
    sidebar_overlaps_main = _boxes_overlap(sidebar_box, main_box)

    file_inputs = page.locator('input[type="file"]')
    input_count = file_inputs.count()
    inputs_enabled = input_count == 2 and all(
        file_inputs.nth(index).is_enabled() for index in range(input_count)
    )
    accepts = [file_inputs.nth(index).get_attribute("accept") for index in range(input_count)]
    uploader_labels = ("Corpus texts (.txt)", "Optional metadata table (.csv)")
    labels_visible = all(
        page.get_by_text(label, exact=True).count() == 1 for label in uploader_labels
    )
    labelled_regions = []
    for label in uploader_labels:
        region = page.get_by_role("region", name=label, exact=True)
        labelled_regions.append(
            {
                "label": label,
                "count": region.count(),
                "file_inputs": region.locator('input[type="file"]').count()
                if region.count() == 1
                else 0,
            }
        )
    progress = page.get_by_role("progressbar")
    progress_snapshot = progress.aria_snapshot() if progress.count() == 1 else ""
    progress_accessible = (
        progress.count() == 1 and "Experiment map progress: step 2 of 4" in progress_snapshot
    )

    disabled_controls = []
    for name in DISABLED_BUTTONS:
        control = page.get_by_role("button", name=name, exact=True)
        disabled_controls.append(
            {
                "name": name,
                "count": control.count(),
                "disabled": control.count() == 1 and control.is_disabled(),
            }
        )

    headings = _heading_outline(page)
    screenshot = output / "screenshots" / f"{target}.png"
    page.screenshot(path=str(screenshot), full_page=True)
    return {
        "target": target,
        "viewport": {"width": width, "height": height},
        **geometry,
        "horizontal_overflow": geometry["scrollWidth"] > geometry["clientWidth"],
        "main_horizontal_overflow": geometry["mainScrollWidth"] > geometry["mainClientWidth"],
        "controls_overflow": bool(geometry["overflowingControls"]),
        "sidebar_rendered": sidebar_box is not None,
        "sidebar_box": sidebar_box,
        "main_box": main_box,
        "sidebar_overlaps_main": sidebar_overlaps_main,
        "mobile_initial_sidebar_clear": not mobile or not sidebar_overlaps_main,
        "heading_outline": headings,
        "heading_outline_matches": headings == EXPECTED_HEADINGS,
        "file_inputs": {
            "count": input_count,
            "enabled": inputs_enabled,
            "accepts": accepts,
            "visible_labels": labels_visible,
            "labelled_regions": labelled_regions,
            "semantic_relationships_pass": all(
                item["count"] == 1 and item["file_inputs"] == 1 for item in labelled_regions
            ),
        },
        "progress_accessibility": {
            "count": progress.count(),
            "snapshot": progress_snapshot,
            "pass": progress_accessible,
        },
        "disabled_controls": disabled_controls,
        "disabled_controls_pass": all(
            item["count"] == 1 and item["disabled"] for item in disabled_controls
        ),
        "screenshot": _display_path(screenshot),
    }


def _archive_payload() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("one.txt", b"one")
        archive.writestr("two.txt", b"two")
    return output.getvalue()


def _audit_interactions(
    browser: Browser,
    url: str,
    requests: list[str],
    console_messages: list[dict[str, str]],
    output: Path,
) -> dict[str, Any]:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.on("request", lambda request: requests.append(request.url))
    _console_observer(page, console_messages)
    page.goto(url, wait_until="networkidle")
    page.get_by_role("heading", name="Set the research purpose", level=1).wait_for()

    inputs = page.locator('input[type="file"]')
    initial_input_count = inputs.count()
    inputs.nth(0).set_input_files(
        {"name": "one.txt", "mimeType": "text/plain", "buffer": b"one text"}
    )
    inputs.nth(1).set_input_files(
        {
            "name": "metadata.csv",
            "mimeType": "text/csv",
            "buffer": b"title,year\nOne,1883",
        }
    )
    page.get_by_text("Intake checks passed · Uploads: 2", exact=False).wait_for()
    text_summary = page.get_by_text("Lines: 1 · Tokens: 2", exact=True).count() == 1
    csv_summary = page.get_by_text("Rows: 1 · Columns: 2", exact=True).count() == 1
    valid_body_text = page.locator("body").inner_text()
    payload_not_rendered = "one text" not in valid_body_text
    page.screenshot(
        path=str(output / "screenshots" / "interaction-valid-text-csv.png"), full_page=True
    )

    inputs = page.locator('input[type="file"]')
    inputs.nth(0).set_input_files(
        {
            "name": "rejected.txt",
            "mimeType": "text/plain",
            "buffer": b"SECRET_BROWSER_CANARY\xff",
        }
    )
    page.get_by_text("Rejection reference: INGEST_INVALID_UTF8", exact=True).wait_for()
    rejection_callout = (
        page.get_by_text(
            "The submission was rejected and cleared before intake.", exact=True
        ).count()
        == 1
    )
    body_text = page.locator("body").inner_text()
    payload_not_in_error = "SECRET_BROWSER_CANARY" not in body_text
    rejected_label_not_rendered = "rejected.txt" not in body_text
    inputs = page.locator('input[type="file"]')
    uploaded_file_counts = inputs.evaluate_all(
        "elements => elements.map(element => element.files?.length ?? -1)"
    )
    rejected_uploaders_cleared = uploaded_file_counts == [0, 0]
    page.screenshot(
        path=str(output / "screenshots" / "interaction-rejected-text.png"), full_page=True
    )

    page.get_by_role("radio", name="One ZIP archive", exact=True).click()
    page.get_by_text("Corpus archive (.zip)", exact=True).wait_for()
    inputs = page.locator('input[type="file"]')
    zip_accept = inputs.nth(0).get_attribute("accept")
    inputs.nth(0).set_input_files(
        {"name": "corpus.zip", "mimeType": "application/zip", "buffer": _archive_payload()}
    )
    page.get_by_text("TXT members: 2 · Expanded bytes: 6", exact=True).wait_for()
    archive_summary = (
        page.get_by_text("TXT members: 2 · Expanded bytes: 6", exact=True).count() == 1
    )
    validated_evidence = page.get_by_text("Validated for intake", exact=True).count() == 1
    page.screenshot(path=str(output / "screenshots" / "interaction-valid-zip.png"), full_page=True)

    purpose = page.get_by_role("radio", name="Text Proximity", exact=True)
    purpose.focus()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("Space")
    page.get_by_text("How does stylistic structure differ", exact=False).wait_for()
    keyboard_pass = (
        page.get_by_role("radio", name="Group Comparison", exact=True).get_attribute("aria-checked")
        == "true"
    )

    result = {
        "initial_file_input_count": initial_input_count,
        "text_summary_pass": text_summary,
        "csv_summary_pass": csv_summary,
        "payload_not_rendered": payload_not_rendered,
        "rejection_callout_pass": rejection_callout,
        "rejected_payload_not_rendered": payload_not_in_error,
        "rejected_label_not_rendered_pass": rejected_label_not_rendered,
        "rejected_uploaders_cleared_pass": rejected_uploaders_cleared,
        "zip_accept": zip_accept,
        "archive_summary_pass": archive_summary,
        "validated_evidence_pass": validated_evidence,
        "keyboard_purpose_selection_pass": keyboard_pass,
    }
    context.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    (output / "screenshots").mkdir(parents=True, exist_ok=True)

    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment["DELTA_BUILD_ID"] = "p003-browser-audit"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.headless=true",
        f"--server.port={port}",
        "--server.address=127.0.0.1",
        "--browser.gatherUsageStats=false",
    ]
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_health(url, process)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            requests: list[str] = []
            console_messages: list[dict[str, str]] = []
            audits = []
            for target, width, height in VIEWPORTS:
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                page.on("request", lambda request: requests.append(request.url))
                _console_observer(page, console_messages)
                audits.append(_audit_viewport(page, url, target, width, height, output))
                context.close()
            interactions = _audit_interactions(browser, url, requests, console_messages, output)
            browser.close()

        external_hosts = sorted(
            {
                parsed.hostname
                for request_url in requests
                if (parsed := urlparse(request_url)).hostname not in {"127.0.0.1", "localhost"}
            }
        )
        passed = (
            all(not audit["horizontal_overflow"] for audit in audits)
            and all(not audit["main_horizontal_overflow"] for audit in audits)
            and all(not audit["controls_overflow"] for audit in audits)
            and all(audit["mobile_initial_sidebar_clear"] for audit in audits)
            and all(audit["heading_outline_matches"] for audit in audits)
            and all(audit["file_inputs"]["enabled"] for audit in audits)
            and all(audit["file_inputs"]["visible_labels"] for audit in audits)
            and all(audit["file_inputs"]["semantic_relationships_pass"] for audit in audits)
            and all(audit["progress_accessibility"]["pass"] for audit in audits)
            and all(audit["disabled_controls_pass"] for audit in audits)
            and all(value for key, value in interactions.items() if key.endswith("_pass"))
            and interactions["payload_not_rendered"]
            and interactions["rejected_payload_not_rendered"]
            and ".zip" in str(interactions["zip_accept"]).split(",")
            and not external_hosts
            and not console_messages
        )
        result = {
            "schema_version": "1.0.0",
            "target_url": url,
            "audit_method": (
                "Tracked Python Playwright harness with a fresh local Streamlit process."
            ),
            "synthetic_inputs_only": True,
            "fresh_browser_context_per_viewport": True,
            "audits": audits,
            "interactions": interactions,
            "console_messages": console_messages,
            "external_hosts_observed": external_hosts,
            "network_scope": "Browser requests observed by Playwright; not a packet capture.",
            "zoom_scope": (
                "640px and 320px are automated CSS reflow targets, not a real "
                "browser-chrome zoom session."
            ),
            "retention_scope": (
                "The harness verifies Delta UI state and local requests, not Streamlit, "
                "proxy, container, or host-level retention."
            ),
            "result": "passed" if passed else "failed",
        }
        (output / "browser-audit.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
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
