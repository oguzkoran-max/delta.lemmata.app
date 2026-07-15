#!/usr/bin/env python3
"""Audit the running P014 gateway, Streamlit WebSocket, and alpha status."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

VIEWPORTS = (
    ("desktop", 1280, 900),
    ("mobile", 390, 844),
    ("reflow", 320, 720),
)


def _geometry(page) -> dict[str, int]:
    measured = page.evaluate(
        """() => {
          const release = document.querySelector('.delta-release-status');
          const bounds = release.getBoundingClientRect();
          return {
            clientWidth: document.documentElement.clientWidth,
            scrollWidth: document.documentElement.scrollWidth,
            releaseRight: Math.ceil(bounds.right),
            releaseLeft: Math.floor(bounds.left)
          };
        }"""
    )
    return {key: int(value) for key, value in measured.items()}


def audit(url: str) -> dict[str, object]:
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname != "delta.lemmata.app" or parsed.port != 8502:
        raise ValueError("P014_BROWSER_URL_INVALID")

    requests: set[str] = set()
    websockets: list[str] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    viewport_records: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--host-resolver-rules=MAP delta.lemmata.app 127.0.0.1"],
        )
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.on("request", lambda request: requests.add(urlparse(request.url).hostname or ""))
        page.on("websocket", lambda socket: websockets.append(socket.url))
        page.on(
            "console",
            lambda message: (
                console_errors.append(message.text) if message.type == "error" else None
            ),
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        if response is None or response.status != 200:
            raise RuntimeError("P014_BROWSER_ENTRY_FAILED")
        page.get_by_text("Discover patterns in writing style.", exact=True).wait_for(timeout=30_000)
        page.get_by_text("Public alpha", exact=True).wait_for(timeout=10_000)
        page.get_by_text("Experimental", exact=True).wait_for(timeout=10_000)
        page.get_by_label("Corpus texts (.txt)").wait_for(timeout=10_000)
        page.wait_for_timeout(500)

        for name, width, height in VIEWPORTS:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(250)
            alpha_visible = page.get_by_text("Public alpha", exact=True).is_visible()
            experimental_visible = page.get_by_text("Experimental", exact=True).is_visible()
            geometry = _geometry(page)
            viewport_records.append(
                {
                    "name": name,
                    "width": width,
                    "height": height,
                    "alpha_visible": alpha_visible,
                    "experimental_visible": experimental_visible,
                    "horizontal_overflow": geometry["scrollWidth"] > geometry["clientWidth"],
                    "release_inside_viewport": (
                        geometry["releaseLeft"] >= 0 and geometry["releaseRight"] <= width
                    ),
                }
            )
        context.close()
        browser.close()

    websocket_pass = any("/_stcore/stream" in value for value in websockets)
    viewport_pass = all(
        item["alpha_visible"]
        and item["experimental_visible"]
        and not item["horizontal_overflow"]
        and item["release_inside_viewport"]
        for item in viewport_records
    )
    hosts = sorted(requests)
    return {
        "schema_version": "p014-gateway-browser-audit-v1",
        "url": url,
        "strict_expected_host_only": hosts == ["delta.lemmata.app"],
        "observed_hosts": hosts,
        "websocket_pass": websocket_pass,
        "websocket_count": len(websockets),
        "console_error_count": len(console_errors),
        "page_error_count": len(page_errors),
        "viewports": viewport_records,
        "result": (
            "passed"
            if hosts == ["delta.lemmata.app"]
            and websocket_pass
            and not console_errors
            and not page_errors
            and viewport_pass
            else "failed"
        ),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://delta.lemmata.app:8502")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_args(argv)
    record = audit(arguments.url)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(record, sort_keys=True))
    return 0 if record["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
