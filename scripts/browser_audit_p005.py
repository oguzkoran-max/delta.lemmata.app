"""Render every P005 lifecycle projection in Chromium and verify DOM semantics."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

from delta_lemmata.job_ui import (
    JobDisplayState,
    PresentationRole,
    project_job_state,
    render_job_presentation_html,
)

VIEWPORTS = ((1280, 900), (320, 800))


def _projection(state: JobDisplayState) -> str:
    return render_job_presentation_html(
        project_job_state(
            state,
            cleanup_confirmed=state is JobDisplayState.SUCCEEDED,
            support_reference="SUP-ABCDEFGHIJKL",
        )
    )


def _document() -> str:
    regions = "".join(_projection(state) for state in JobDisplayState)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Delta P005 lifecycle projection audit</title>
<style>
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; width: 100%; overflow-x: hidden; }}
body {{ background: #f8faf9; color: #1a1a1a; font: 16px/1.5 system-ui, sans-serif; }}
main {{ margin: 0 auto; max-width: 960px; padding: 24px; }}
.delta-job-status {{ border-top: 1px solid #d8dfdc; padding: 18px 0; }}
.delta-job-label {{ color: #0f6e56; font-weight: 700; margin: 0 0 6px; }}
h2 {{ font-size: 20px; letter-spacing: 0; margin: 0 0 6px; overflow-wrap: anywhere; }}
.delta-job-body, .delta-job-support {{ margin: 0 0 6px; overflow-wrap: anywhere; }}
code {{ overflow-wrap: anywhere; }}
@media (max-width: 420px) {{ main {{ padding: 16px; }} }}
</style>
</head>
<body><main aria-label="Analysis lifecycle states">{regions}</main></body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    screenshots = output / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    expected = {
        state.value: {
            "role": project_job_state(
                state,
                cleanup_confirmed=state is JobDisplayState.SUCCEEDED,
            ).role.value,
            "live": (
                "assertive"
                if project_job_state(
                    state,
                    cleanup_confirmed=state is JobDisplayState.SUCCEEDED,
                ).role
                is PresentationRole.ALERT
                else "polite"
            ),
        }
        for state in JobDisplayState
    }
    audits: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for width, height in VIEWPORTS:
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            page.set_content(_document(), wait_until="load")
            observed = page.evaluate(
                """() => ({
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                    forbidden: /P005_AC07|PRIVATE_CORPUS|<script|<img/i.test(
                        document.documentElement.innerHTML
                    ),
                    regions: Array.from(document.querySelectorAll('[data-job-state]')).map(
                        (region) => ({
                            state: region.getAttribute('data-job-state'),
                            role: region.getAttribute('role'),
                            live: region.getAttribute('aria-live'),
                            atomic: region.getAttribute('aria-atomic'),
                            headings: region.querySelectorAll('h2').length,
                            text: (region.textContent || '').trim(),
                        })
                    ),
                })"""
            )
            region_map = {region["state"]: region for region in observed["regions"]}
            semantics_pass = set(region_map) == set(expected) and all(
                region_map[state]["role"] == contract["role"]
                and region_map[state]["live"] == contract["live"]
                and region_map[state]["atomic"] == "true"
                and region_map[state]["headings"] == 1
                and bool(region_map[state]["text"])
                for state, contract in expected.items()
            )
            screenshot = screenshots / f"lifecycle-{width}x{height}.png"
            page.screenshot(path=str(screenshot), full_page=True)
            audits.append(
                {
                    "viewport": {"width": width, "height": height},
                    "region_count": len(region_map),
                    "semantics_pass": semantics_pass,
                    "horizontal_overflow": observed["scrollWidth"] > observed["clientWidth"],
                    "forbidden_marker_present": observed["forbidden"],
                    "screenshot": screenshot.relative_to(Path.cwd()).as_posix(),
                }
            )
            context.close()
        browser.close()

    passed = all(
        audit["semantics_pass"]
        and not audit["horizontal_overflow"]
        and not audit["forbidden_marker_present"]
        for audit in audits
    )
    report = {
        "schema_version": "1.0.0",
        "git_commit": commit,
        "git_dirty": dirty,
        "audit_method": "Tracked Python Playwright harness and generated lifecycle HTML.",
        "public_wiring": "Not connected before P008; this is the P005 component boundary.",
        "state_count": len(JobDisplayState),
        "audits": audits,
        "result": "passed" if passed else "failed",
        "limitations": [
            "This is Chromium component evidence, not Safari or VoiceOver evidence.",
            "It does not activate public analysis or verify production deployment.",
        ],
    }
    (output / "browser-audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"result": report["result"], "output": output.as_posix()}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
