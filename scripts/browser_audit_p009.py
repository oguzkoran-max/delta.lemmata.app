#!/usr/bin/env python3
"""Run the reproducible P009 upload-to-public-result browser audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from browser_audit_p008 import (
    FEATURE_COUNT,
    GUIDED_MFW,
    VIEWPORTS,
    _audit_parameters,
    _choose_selectbox,
    _confirm_and_prepare,
    _display_path,
    _document_corpus,
    _download_json,
    _free_port,
    _geometry,
    _observe_console,
    _synthetic_corpus,
    _wait_for_health,
    _wait_until_enabled,
    _word,
)
from PIL import Image
from playwright.sync_api import Browser, Locator, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_EXPORT_KEYS = (
    "selected_features",
    "ranked_features",
    "means",
    "standard_deviations",
    "token",
    "capability",
    "workspace",
)


def _pixel_evidence(locator: Locator, screenshot: Path) -> dict[str, Any]:
    payload = locator.screenshot(path=str(screenshot))
    image = Image.open(BytesIO(payload)).convert("RGB")
    pixels = tuple(image.getdata())
    non_blank = sum(1 for red, green, blue in pixels if min(red, green, blue) < 245)
    sampled_colors = len(set(pixels[:: max(1, len(pixels) // 20_000)]))
    fraction = non_blank / max(1, len(pixels))
    return {
        "width": image.width,
        "height": image.height,
        "non_blank_fraction": round(fraction, 6),
        "sampled_color_count": sampled_colors,
        "pass": (
            image.width >= 200 and image.height >= 120 and fraction >= 0.01 and sampled_colors >= 8
        ),
        "screenshot": _display_path(screenshot),
    }


def _selectbox_text(locator: Locator) -> str:
    return str(
        locator.evaluate(
            """element => {
              let current = element;
              for (let depth = 0; depth < 6 && current; depth += 1) {
                const text = (current.textContent || '').trim();
                if (text.includes('MFW')) return text;
                current = current.parentElement;
              }
              return element.value || '';
            }"""
        )
    )


def _validate_export(filename: str, exported: dict[str, Any], canary: str) -> dict[str, bool]:
    serialized = json.dumps(exported, sort_keys=True, ensure_ascii=False)
    cells = exported.get("cells", [])
    return {
        "filename_pass": filename == "delta-result-view-v1.json",
        "schema_pass": exported.get("schema_version") == "result-view-v1",
        "complete_grid_pass": [cell.get("mfw") for cell in cells] == list(GUIDED_MFW),
        "reference_pass": exported.get("reference_mfw") == 500
        and [cell.get("mfw") for cell in cells if cell.get("is_reference")] == [500],
        "matrix_pass": all(cell.get("matrix") for cell in cells),
        "private_material_absent_pass": canary not in serialized
        and all(key not in serialized for key in FORBIDDEN_EXPORT_KEYS),
    }


def _result_viewports(page: Page, output: Path) -> tuple[dict[str, Any], ...]:
    results = []
    for target, width, height in VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(300)
        geometry = _geometry(page)
        screenshot = output / "screenshots" / f"results-{target}.png"
        page.screenshot(path=str(screenshot), full_page=True)
        results.append(
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
    page.wait_for_timeout(300)
    return tuple(results)


def _run_and_audit_results(page: Page, output: Path, canary: str) -> dict[str, Any]:
    confirmation = page.get_by_role(
        "checkbox",
        name="I reviewed the four comparisons and their interpretation limits.",
        exact=True,
    )
    confirmation.focus()
    page.keyboard.press("Space")
    run_button = page.get_by_role("button", name="Run the four comparisons", exact=False)
    enabled = _wait_until_enabled(page, run_button)
    if not enabled:
        raise RuntimeError("Run control did not become enabled after confirmation")
    run_button.focus()
    page.keyboard.press("Enter")
    result_heading = page.get_by_role(
        "heading",
        name="Explore the relative distances",
        level=2,
        exact=True,
    )
    try:
        result_heading.wait_for(timeout=120_000)
    except PlaywrightTimeoutError:
        screenshot = output / "screenshots" / "result-timeout.png"
        page.screenshot(path=str(screenshot), full_page=True)
        alerts = page.locator('[data-testid="stAlert"]').all_inner_texts()
        headings = page.locator("h1, h2, h3").all_inner_texts()
        raise RuntimeError(
            f"Real worker produced no P009 result UI: alerts={alerts!r}; headings={headings!r}"
        ) from None

    chart_locator = page.locator('[data-testid="stVegaLiteChart"]')
    chart_locator.nth(1).wait_for(timeout=15_000)
    chart_evidence = tuple(
        _pixel_evidence(
            chart_locator.nth(index),
            output / "screenshots" / f"result-chart-{index + 1}.png",
        )
        for index in range(2)
    )
    selector = page.get_by_label("View one completed comparison", exact=True)
    default_reference = "500 MFW" in _selectbox_text(selector)
    filename, exported = _download_json(page, "Download canonical result record")
    export_checks = _validate_export(filename, exported, canary)
    export_digest = hashlib.sha256(
        json.dumps(exported, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    viewports = _result_viewports(page, output)
    _choose_selectbox(page, selector, "1000 MFW")
    page.get_by_role("heading", name="Distance heatmap", level=3, exact=True).wait_for()
    filename_after, exported_after = _download_json(page, "Download canonical result record")
    display_only = (
        "1000 MFW" in _selectbox_text(selector)
        and filename_after == filename
        and exported_after == exported
        and page.locator(".delta-result-cell").count() == 4
    )
    body = page.locator("body").inner_text()
    return {
        "run_enabled_after_confirmation_pass": enabled,
        "analysis_complete_pass": page.get_by_text("Analysis complete", exact=True).count() == 1,
        "all_four_cells_visible_pass": page.locator(".delta-result-cell").count() == 4,
        "all_four_cells_complete_pass": page.locator(".delta-result-cell-complete").count() == 4,
        "default_reference_500_pass": default_reference,
        "display_only_selector_pass": display_only,
        "semantic_tables_pass": all(
            page.get_by_role("table", name=label, exact=True).count() == 1
            for label in (
                "Complete Guided Mode result grid",
                "Exact Classic Delta distance matrix",
                "Nearest-neighbour table with exact ties",
                "Exact MDS coordinate table",
            )
        ),
        "interpretation_boundaries_pass": page.get_by_text(
            "What this does not show", exact=True
        ).count()
        == 3,
        "two_visualizations_pass": chart_locator.count() == 2
        and all(item["pass"] for item in chart_evidence),
        "chart_pixel_evidence": chart_evidence,
        "canonical_export_sha256": export_digest,
        **export_checks,
        "payload_absent_from_page_pass": canary not in body,
        "viewport_pass": all(
            not item["horizontal_overflow"]
            and not item["main_horizontal_overflow"]
            and not item["overflowing_controls"]
            and not item["misframed_table_scroll_regions"]
            for item in viewports
        ),
        "viewports": viewports,
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
    results = _run_and_audit_results(page, output, _word(0))
    context.close()
    return {"preparation": preparation, "parameters": parameters, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-noncanonical-local", action="store_true")
    arguments = parser.parse_args()
    canonical_platform = sys.platform == "linux"
    if not canonical_platform and not arguments.allow_noncanonical_local:
        print(
            json.dumps(
                {
                    "result": "not-run",
                    "reason": "P009_REAL_WORKER_BROWSER_AUDIT_REQUIRES_CANONICAL_LINUX",
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
    environment["DELTA_BUILD_ID"] = "p009-real-worker-browser-audit"
    environment["DELTA_RUNTIME_ROOT"] = str(output / "runtime")
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
                "canonical_worker_platform": canonical_platform,
                "target_url": url,
                "audit_method": (
                    "Tracked Python Playwright harness, fresh local Streamlit process, synthetic "
                    "whole texts, production R/stylo execution, export verification, responsive "
                    "screenshots, and chart pixel inspection."
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
