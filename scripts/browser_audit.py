#!/usr/bin/env python3
"""Run the reproducible P002 browser, accessibility, reflow, and egress audit."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Page, sync_playwright

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
    {"level": 2, "name": "Add the research corpus"},
    {"level": 2, "name": "Experiment map"},
    {"level": 2, "name": "Method boundary"},
    {"level": 2, "name": "Evidence reserved with every run"},
    {"level": 2, "name": "The workspace is ready for a research purpose"},
]
DISABLED_NAMES = (
    "Corpus files - unavailable in this preview",
    "Add metadata - unavailable until intake is ready",
    "Continue - unavailable until corpus checks pass",
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


def _audit_viewport(
    page: Page, url: str, target: str, width: int, height: int, output: Path
) -> dict[str, Any]:
    page.goto(url, wait_until="networkidle")
    page.get_by_role("heading", name="Set the research purpose", level=1).wait_for()

    geometry = page.evaluate(
        """() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth
        })"""
    )
    sidebar = page.locator('[data-testid="stSidebar"]')
    main = page.locator('[data-testid="stMain"]')
    sidebar_box = sidebar.bounding_box() if sidebar.is_visible() else None
    main_box = main.bounding_box() if main.is_visible() else None
    mobile = width <= 760
    sidebar_overlaps_main = _boxes_overlap(sidebar_box, main_box)

    disabled = []
    for name in DISABLED_NAMES:
        if name.startswith("Corpus files"):
            control = page.locator('input[type="file"]')
            visible_label = page.get_by_text(name, exact=True).count() > 0
            snapshot = control.aria_snapshot() if control.count() == 1 else ""
            state_pass = control.count() == 1 and control.is_disabled() and visible_label
        else:
            control = page.locator("button:visible", has_text=name)
            visible_label = control.count() == 1
            snapshot = control.aria_snapshot() if control.count() == 1 else ""
            state_pass = (
                control.count() == 1
                and control.is_disabled()
                and "unavailable" in snapshot.casefold()
            )
        disabled.append(
            {
                "name": name,
                "count": control.count(),
                "disabled": control.count() == 1 and control.is_disabled(),
                "visible_label": visible_label,
                "accessibility_snapshot": snapshot,
                "state_and_reason_pass": state_pass,
            }
        )

    visible_reasons = {
        "corpus": page.get_by_text(
            "These controls are unavailable in this interface preview.", exact=False
        ).count(),
        "run": page.get_by_text("Analysis remains unavailable", exact=False).count(),
    }
    headings = _heading_outline(page)
    screenshot = output / "screenshots" / f"{target}.png"
    page.screenshot(path=str(screenshot), full_page=True)
    return {
        "target": target,
        "viewport": {"width": width, "height": height},
        **geometry,
        "horizontal_overflow": geometry["scrollWidth"] > geometry["clientWidth"],
        "sidebar_rendered": sidebar_box is not None,
        "sidebar_box": sidebar_box,
        "main_box": main_box,
        "sidebar_overlaps_main": sidebar_overlaps_main,
        "mobile_initial_sidebar_clear": not mobile or not sidebar_overlaps_main,
        "heading_outline": headings,
        "heading_outline_matches": headings == EXPECTED_HEADINGS,
        "disabled_controls": disabled,
        "disabled_names_and_states_pass": all(item["state_and_reason_pass"] for item in disabled),
        "visible_disabled_reasons": visible_reasons,
        "visible_disabled_reasons_pass": all(value > 0 for value in visible_reasons.values()),
        "screenshot": _display_path(screenshot),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    (output / "screenshots").mkdir(parents=True, exist_ok=True)

    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment["DELTA_BUILD_ID"] = "codex-correction-audit"
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
            audits = []
            for target, width, height in VIEWPORTS:
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                page.on("request", lambda request: requests.append(request.url))
                audits.append(_audit_viewport(page, url, target, width, height, output))
                context.close()

            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()
            page.on("request", lambda request: requests.append(request.url))
            page.goto(url, wait_until="networkidle")
            page.get_by_role("heading", name="Set the research purpose", level=1).wait_for()
            purpose = page.get_by_role("radio", name="Text Proximity", exact=True)
            purpose.focus()
            page.keyboard.press("ArrowRight")
            page.keyboard.press("Space")
            page.get_by_text("How does stylistic structure differ", exact=False).wait_for()
            keyboard_pass = (
                page.get_by_role("radio", name="Group Comparison", exact=True).get_attribute(
                    "aria-checked"
                )
                == "true"
            )

            toggle = page.locator(
                '[data-testid="stExpandSidebarButton"] button, '
                '[data-testid="stSidebarCollapseButton"] button'
            ).first
            toggle_snapshot = {
                "count": toggle.count(),
                "aria_label": toggle.get_attribute("aria-label") if toggle.count() else None,
                "title": toggle.get_attribute("title") if toggle.count() else None,
                "framework_limitation": (
                    "Streamlit 1.59.1 exposes no supported API for assigning a product-specific "
                    "accessible name to its native sidebar toggle."
                ),
            }
            context.close()
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
            and all(audit["mobile_initial_sidebar_clear"] for audit in audits)
            and all(audit["heading_outline_matches"] for audit in audits)
            and all(audit["disabled_names_and_states_pass"] for audit in audits)
            and all(audit["visible_disabled_reasons_pass"] for audit in audits)
            and keyboard_pass
            and not external_hosts
        )
        result = {
            "schema_version": "1.0.0",
            "target_url": url,
            "audit_method": (
                "Tracked Python Playwright harness with a fresh local Streamlit process."
            ),
            "fresh_browser_context_per_viewport": True,
            "audits": audits,
            "keyboard_purpose_selection_pass": keyboard_pass,
            "external_hosts_observed": external_hosts,
            "network_scope": "Browser requests observed by Playwright; not a packet capture.",
            "sidebar_toggle": toggle_snapshot,
            "file_uploader_accessibility_scope": (
                "The disabled native file input remains named 'Choose File' by Streamlit. Its "
                "visible field label contains the unavailable state; Streamlit 1.59.1 exposes no "
                "supported API to replace the native input name."
            ),
            "zoom_scope": (
                "640px and 320px are automated CSS reflow targets. They are not represented as "
                "a real browser zoom session; real 200% zoom is recorded separately."
            ),
            "result": "passed" if passed else "failed",
        }
        (output / "browser-audit.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps({"result": result["result"], "output": str(output)}))
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
