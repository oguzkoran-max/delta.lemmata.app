#!/usr/bin/env python3
"""Run the reproducible P009 upload-to-public-result browser audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from browser_audit_p008 import (
    FEATURE_COUNT,
    GUIDED_MFW,
    VIEWPORTS,
    _audit_parameters,
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
_ALLOWED_TRANSIENT_VEGA_WARNINGS = frozenset(
    {
        'WARN Infinite extent for field "distance": [Infinity, -Infinity]',
        'WARN Infinite extent for field "x": [Infinity, -Infinity]',
        'WARN Infinite extent for field "y": [Infinity, -Infinity]',
    }
)
_MAX_ALLOWED_TRANSIENT_VEGA_WARNINGS = 12
PHASE_B_VIEWPORTS = (
    ("desktop-1440x1000", 1440, 1000),
    *VIEWPORTS,
    ("mobile-375x844", 375, 844),
)


def _lifecycle_diagnostics(output: Path) -> dict[str, Any]:
    """Project content-free lifecycle fields from the private audit database."""

    database = output / "runtime" / "database" / "control.sqlite3"
    if not database.is_file():
        return {"available": False, "reason": "control_database_absent"}
    try:
        with closing(
            sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=1.0)
        ) as connection:
            rows = connection.execute(
                "SELECT model_json FROM jobs ORDER BY queue_sequence ASC"
            ).fetchall()
        records = []
        for (raw_model,) in rows:
            model = json.loads(raw_model)
            artifacts = model.get("artifacts", {})
            records.append(
                {
                    "execution_state": model.get("execution", {}).get("state"),
                    "terminal_outcome": (model.get("outcome") or {}).get("kind"),
                    "scientific_result_present": model.get("scientific_result") is not None,
                    "scientific_result_confirmed": model.get(
                        "scientific_result_confirmed",
                        False,
                    ),
                    "result_view_present": model.get("result_view") is not None,
                    "export_available": model.get("export_available", False),
                    "artifact_states": {
                        area: artifacts.get(area, {}).get("state")
                        for area in ("input", "work", "result", "export")
                    },
                    "operation_count": len(model.get("operations", [])),
                }
            )
        return {"available": True, "job_count": len(records), "records": records}
    except (json.JSONDecodeError, OSError, sqlite3.Error, TypeError):
        return {"available": False, "reason": "control_database_unreadable"}


def _write_failure_record(
    *,
    output: Path,
    commit: str,
    dirty: bool,
    canonical_platform: bool,
    error: Exception,
) -> None:
    record = {
        "schema_version": "1.0.0",
        "git_commit": commit,
        "git_dirty": dirty,
        "canonical_worker_platform": canonical_platform,
        "synthetic_inputs_only": True,
        "failure_type": type(error).__name__,
        "failure_message": str(error),
        "lifecycle_diagnostics": _lifecycle_diagnostics(output),
        "result": "failed",
    }
    (output / "browser-audit.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _pixel_evidence(locator: Locator, screenshot: Path) -> dict[str, Any]:
    payload = locator.screenshot(path=str(screenshot))
    image = Image.open(BytesIO(payload)).convert("RGB")
    pixels = tuple(image.get_flattened_data())
    non_blank = sum(1 for red, green, blue in pixels if min(red, green, blue) < 245)
    sampled_colors = len(set(pixels[:: max(1, len(pixels) // 20_000)]))
    fraction = non_blank / max(1, len(pixels))
    return {
        "width": image.width,
        "height": image.height,
        "non_blank_fraction": round(fraction, 6),
        "sampled_color_count": sampled_colors,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "pass": (
            image.width >= 200 and image.height >= 120 and fraction >= 0.01 and sampled_colors >= 8
        ),
        "screenshot": _display_path(screenshot),
    }


def _visible_count(locator: Locator) -> int:
    return int(
        locator.evaluate_all(
            "elements => elements.filter(element => { "
            "const style = getComputedStyle(element); "
            "const box = element.getBoundingClientRect(); "
            "return style.display !== 'none' && style.visibility !== 'hidden' "
            "&& box.width > 0 && box.height > 0; }).length"
        )
    )


def _semantic_table_evidence(page: Page, label: str) -> dict[str, Any]:
    table = page.get_by_role("table", name=label, exact=True)
    payload = table.inner_text().encode("utf-8")
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "row_count": table.locator("tbody tr").count(),
    }


def _wait_for_result_selection_update(
    page: Page,
    target_radio: Locator,
    semantic_before: dict[str, dict[str, Any]],
    *,
    attempts: int = 600,
) -> dict[str, dict[str, Any]]:
    """Wait up to 60 seconds for a stable, user-visible result update."""

    if attempts < 1:
        raise ValueError("attempts must be positive")
    labels = tuple(semantic_before)
    latest = semantic_before
    for _ in range(attempts):
        if target_radio.is_checked():
            latest = {label: _semantic_table_evidence(page, label) for label in labels}
            changed = all(
                semantic_before[label]["sha256"] != latest[label]["sha256"] for label in labels
            )
            if changed:
                page.wait_for_timeout(250)
                confirmed = {label: _semantic_table_evidence(page, label) for label in labels}
                if confirmed == latest:
                    return confirmed
        page.wait_for_timeout(100)
    raise RuntimeError(
        "Result selection did not produce a stable semantic-table update: "
        f"checked={target_radio.is_checked()!r}; before={semantic_before!r}; "
        f"latest={latest!r}"
    )


def _skip_link_evidence(page: Page) -> dict[str, bool]:
    skip_link = page.locator(".delta-skip-link")
    skip_link.focus()
    target_pass = skip_link.get_attribute("href") == "#delta-content-start" and page.evaluate(
        "() => document.activeElement?.classList.contains('delta-skip-link')"
    )
    skip_link.press("Enter")
    page.wait_for_timeout(100)
    activation_pass = page.evaluate("() => document.activeElement?.id === 'delta-content-start'")
    bypass_pass = page.evaluate(
        """() => {
          const link = document.querySelector('.delta-skip-link');
          const target = document.querySelector('#delta-content-start');
          const header = document.querySelector('.delta-header');
          if (!link || !target || !header) return false;
          const relation = header.compareDocumentPosition(target);
          return !target.contains(link)
            && Boolean(relation & Node.DOCUMENT_POSITION_FOLLOWING)
            && target.getBoundingClientRect().top >= header.getBoundingClientRect().bottom - 1;
        }"""
    )
    page.evaluate("() => { document.activeElement?.blur(); window.scrollTo(0, 0); }")
    return {
        "target_pass": bool(target_pass),
        "activation_pass": bool(activation_pass),
        "bypass_pass": bool(bypass_pass),
    }


def _matrix_values_are_finite(matrix: Any) -> bool:
    if not isinstance(matrix, dict):
        return False
    keys = matrix.get("document_keys")
    rows = matrix.get("values")
    if not isinstance(keys, list) or not isinstance(rows, list) or len(keys) < 2:
        return False
    if len(rows) != len(keys):
        return False
    return all(
        isinstance(row, list)
        and len(row) == len(keys)
        and all(
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(float(value))
            for value in row
        )
        for row in rows
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
        "finite_matrix_values_pass": all(
            _matrix_values_are_finite(cell.get("matrix")) for cell in cells
        ),
        "private_material_absent_pass": canary not in serialized
        and all(key not in serialized for key in FORBIDDEN_EXPORT_KEYS),
    }


def _partition_console_messages(
    messages: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    allowed: list[dict[str, str]] = []
    unexpected: list[dict[str, str]] = []
    for message in messages:
        if (
            len(allowed) < _MAX_ALLOWED_TRANSIENT_VEGA_WARNINGS
            and message.get("type") == "warning"
            and message.get("text") in _ALLOWED_TRANSIENT_VEGA_WARNINGS
        ):
            allowed.append(message)
        else:
            unexpected.append(message)
    return allowed, unexpected


def _entry_viewports(page: Page, output: Path) -> tuple[dict[str, Any], ...]:
    results = []
    for target, width, height in PHASE_B_VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(300)
        geometry = _geometry(page)
        upload = page.get_by_role("region", name="Corpus texts (.txt)", exact=True)
        teaching = page.get_by_role("heading", name="How stylometry works", exact=True)
        skip = _skip_link_evidence(page)
        screenshot = output / "screenshots" / f"entry-{target}.png"
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
                "small_targets": geometry["smallTargets"],
                "unscrollable_table_regions": geometry["unscrollableTableRegions"],
                "visible_h1_count": geometry["visibleH1Count"],
                "main_landmark_count": geometry["mainLandmarkCount"],
                "footer_count": geometry["visibleFooterCount"],
                "inter_font_loaded": geometry["interFontLoaded"],
                "upload_before_teaching": (
                    upload.bounding_box()["y"] < teaching.bounding_box()["y"]
                ),
                "skip_target_pass": skip["target_pass"],
                "skip_activation_pass": skip["activation_pass"],
                "skip_bypass_pass": skip["bypass_pass"],
                "screenshot": _display_path(screenshot),
            }
        )
    page.set_viewport_size({"width": 1280, "height": 900})
    page.wait_for_timeout(300)
    return tuple(results)


def _review_viewports(page: Page, output: Path) -> tuple[dict[str, Any], ...]:
    results = []
    for target, width, height in PHASE_B_VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(300)
        geometry = _geometry(page)
        skip = _skip_link_evidence(page)
        correction_selector = page.get_by_role(
            "combobox", name="Metadata field to correct", exact=True
        )
        selector_count = correction_selector.count()
        selector_box = correction_selector.bounding_box() if selector_count == 1 else None
        screenshot = output / "screenshots" / f"review-{target}.png"
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
                "small_targets": geometry["smallTargets"],
                "unscrollable_table_regions": geometry["unscrollableTableRegions"],
                "visible_h1_count": geometry["visibleH1Count"],
                "main_landmark_count": geometry["mainLandmarkCount"],
                "footer_count": geometry["visibleFooterCount"],
                "inter_font_loaded": geometry["interFontLoaded"],
                "correction_selector_count": selector_count,
                "correction_selector_pass": (
                    selector_count == 1
                    and selector_box is not None
                    and selector_box["height"] >= 44
                ),
                "skip_target_pass": skip["target_pass"],
                "skip_activation_pass": skip["activation_pass"],
                "skip_bypass_pass": skip["bypass_pass"],
                "screenshot": _display_path(screenshot),
            }
        )
    page.set_viewport_size({"width": 1280, "height": 900})
    page.wait_for_timeout(300)
    return tuple(results)


def _result_viewports(page: Page, output: Path) -> tuple[dict[str, Any], ...]:
    results = []
    for target, width, height in PHASE_B_VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(300)
        geometry = _geometry(page)
        chart_locator = page.locator('[data-testid="stVegaLiteChart"]')
        chart_pixels = tuple(
            _pixel_evidence(
                chart_locator.nth(index),
                output / "screenshots" / f"results-{target}-chart-{index + 1}.png",
            )
            for index in range(2)
        )
        mds_plot_box = (
            chart_locator.nth(1).locator("svg .role-frame .background").first.bounding_box()
        )
        radio_boxes = (
            page.get_by_role("radiogroup", name="View one completed comparison", exact=True)
            .locator('label[data-testid="stRadioOption"]')
            .evaluate_all(
                "elements => elements.map(element => { "
                "const box = element.getBoundingClientRect(); "
                "return {x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), "
                "height: Math.round(box.height)}; })"
            )
        )
        radio_rows = len({box["y"] for box in radio_boxes})
        visible_result_cells = _visible_count(page.locator(".delta-result-cell"))
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
                "small_targets": geometry["smallTargets"],
                "misframed_table_scroll_regions": geometry["misframedTableScrollRegions"],
                "unscrollable_table_regions": geometry["unscrollableTableRegions"],
                "visible_h1_count": geometry["visibleH1Count"],
                "main_landmark_count": geometry["mainLandmarkCount"],
                "footer_count": geometry["visibleFooterCount"],
                "inter_font_loaded": geometry["interFontLoaded"],
                "mfw_radio_rows": radio_rows,
                "mfw_radio_layout_pass": (radio_rows == 1 if width > 760 else radio_rows == 2),
                "visible_result_cell_count": visible_result_cells,
                "all_result_cells_visible_pass": visible_result_cells == 4,
                "mds_metric_aspect_pass": (
                    mds_plot_box is not None
                    and abs(mds_plot_box["width"] - mds_plot_box["height"]) <= 2
                ),
                "mds_plot_box": mds_plot_box,
                "chart_pixels": chart_pixels,
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
        level=1,
        exact=True,
    )
    error_reference = page.get_by_text("Rejection reference:", exact=False)
    for _ in range(600):
        if result_heading.is_visible():
            break
        if error_reference.count() > 0:
            screenshot = output / "screenshots" / "result-failure.png"
            page.screenshot(path=str(screenshot), full_page=True)
            alerts = page.locator('[data-testid="stAlert"]').all_inner_texts()
            references = error_reference.all_inner_texts()
            headings = page.locator("h1, h2, h3").all_inner_texts()
            raise RuntimeError(
                "Real worker or result publication failed safely: "
                f"references={references!r}; alerts={alerts!r}; headings={headings!r}"
            )
        page.wait_for_timeout(200)
    else:
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
    selector = page.get_by_role(
        "radiogroup",
        name="View one completed comparison",
        exact=True,
    )
    reference_radio = selector.get_by_role("radio", name="500 MFW", exact=True)
    default_reference = reference_radio.is_checked()
    filename, exported = _download_json(page, "Download canonical result record")
    export_checks = _validate_export(filename, exported, canary)
    export_digest = hashlib.sha256(
        json.dumps(exported, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    run_details = page.locator('[data-testid="stExpander"]').filter(has_text="run details")
    run_details.locator("summary").click()
    page.get_by_role(
        "table",
        name="Complete Guided Mode result grid",
        exact=True,
    ).wait_for()
    semantic_labels = (
        "Classic Delta distance matrix",
        "MDS coordinate table",
    )
    semantic_before = {label: _semantic_table_evidence(page, label) for label in semantic_labels}

    viewports = _result_viewports(page, output)
    target_option = selector.locator(
        'label[data-testid="stRadioOption"]',
        has_text="1000 MFW",
    )
    if target_option.count() != 1:
        raise RuntimeError("Expected exactly one visible 1000 MFW result card")
    target_radio = selector.get_by_role("radio", name="1000 MFW", exact=True)
    target_option.click()
    semantic_after = _wait_for_result_selection_update(
        page,
        target_radio,
        semantic_before,
    )
    page.get_by_role("heading", name="Distance heatmap", level=3, exact=True).wait_for()
    changed_chart_evidence = tuple(
        _pixel_evidence(
            chart_locator.nth(index),
            output / "screenshots" / f"result-chart-{index + 1}-1000-mfw.png",
        )
        for index in range(2)
    )
    semantic_change = all(
        semantic_before[label]["sha256"] != semantic_after[label]["sha256"]
        for label in semantic_labels
    )
    filename_after, exported_after = _download_json(page, "Download canonical result record")
    result_cells = page.locator(".delta-result-cell")
    complete_result_cells = page.locator(".delta-result-cell-complete")
    display_only = (
        selector.get_by_role("radio", name="1000 MFW", exact=True).is_checked()
        and filename_after == filename
        and exported_after == exported
        and _visible_count(result_cells) == 4
    )
    body = page.locator("body").inner_text()
    return {
        "run_enabled_after_confirmation_pass": enabled,
        "analysis_complete_pass": result_heading.is_visible()
        and _visible_count(complete_result_cells) == 4,
        "all_four_cells_visible_pass": _visible_count(result_cells) == 4,
        "all_four_cells_complete_pass": _visible_count(complete_result_cells) == 4,
        "default_reference_500_pass": default_reference,
        "display_only_selector_pass": display_only,
        "semantic_tables_pass": all(
            page.get_by_role("table", name=label, exact=True).count() == 1
            for label in (
                "Complete Guided Mode result grid",
                "Classic Delta distance matrix",
                "Nearest-neighbour table with tolerance-aware ties",
                "MDS coordinate table",
            )
        ),
        "interpretation_boundaries_pass": page.get_by_text(
            "What this does not show", exact=True
        ).count()
        == 1,
        "two_visualizations_pass": chart_locator.count() == 2
        and all(item["pass"] for item in chart_evidence),
        "visualizations_change_with_mfw_pass": all(item["pass"] for item in changed_chart_evidence)
        and semantic_change
        and all(
            before["sha256"] != after["sha256"]
            for before, after in zip(chart_evidence, changed_chart_evidence, strict=True)
        ),
        "semantic_table_change_pass": semantic_change,
        "semantic_table_evidence_before": semantic_before,
        "semantic_table_evidence_after": semantic_after,
        "chart_pixel_evidence": chart_evidence,
        "changed_chart_pixel_evidence": changed_chart_evidence,
        "canonical_export_sha256": export_digest,
        **export_checks,
        "payload_absent_from_page_pass": canary not in body,
        "viewport_pass": all(
            not item["horizontal_overflow"]
            and not item["main_horizontal_overflow"]
            and not item["overflowing_controls"]
            and not item["small_targets"]
            and not item["misframed_table_scroll_regions"]
            and not item["unscrollable_table_regions"]
            and item["visible_h1_count"] == 1
            and item["main_landmark_count"] == 1
            and item["footer_count"] == 1
            and item["inter_font_loaded"]
            and item["mfw_radio_layout_pass"]
            and item["all_result_cells_visible_pass"]
            and item["mds_metric_aspect_pass"]
            and all(chart["pass"] for chart in item["chart_pixels"])
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
    entry_viewports = _entry_viewports(page, output)
    _document_corpus(page, documents, output)
    review_viewports = _review_viewports(page, output)
    preparation = _confirm_and_prepare(page, output)
    parameters = _audit_parameters(page, output)
    results = _run_and_audit_results(page, output, _word(0))
    context.close()
    entry = {
        "viewport_pass": all(
            not item["horizontal_overflow"]
            and not item["main_horizontal_overflow"]
            and not item["overflowing_controls"]
            and not item["small_targets"]
            and not item["unscrollable_table_regions"]
            and item["visible_h1_count"] == 1
            and item["main_landmark_count"] == 1
            and item["footer_count"] == 1
            and item["inter_font_loaded"]
            and item["upload_before_teaching"]
            and item["skip_target_pass"]
            and item["skip_activation_pass"]
            and item["skip_bypass_pass"]
            for item in entry_viewports
        ),
        "viewports": entry_viewports,
    }
    review = {
        "viewport_pass": all(
            not item["horizontal_overflow"]
            and not item["main_horizontal_overflow"]
            and not item["overflowing_controls"]
            and not item["small_targets"]
            and not item["unscrollable_table_regions"]
            and item["visible_h1_count"] == 1
            and item["main_landmark_count"] == 1
            and item["footer_count"] == 1
            and item["inter_font_loaded"]
            and item["correction_selector_pass"]
            and item["skip_target_pass"]
            and item["skip_activation_pass"]
            and item["skip_bypass_pass"]
            for item in review_viewports
        ),
        "viewports": review_viewports,
    }
    return {
        "entry": entry,
        "review": review,
        "preparation": preparation,
        "parameters": parameters,
        "results": results,
    }


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
            allowed_console_messages, unexpected_console_messages = _partition_console_messages(
                console_messages
            )
            console_policy_pass = not unexpected_console_messages
            passed = all(boolean_results) and not external_hosts and console_policy_pass
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
                "console_policy": (
                    "Only a bounded set of exact Vega transient empty-dataset warnings is "
                    "allowed after finite exported matrices and non-blank chart pixels pass."
                ),
                "console_policy_pass": console_policy_pass,
                "allowed_console_messages": allowed_console_messages,
                "console_messages": unexpected_console_messages,
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
        except Exception as error:
            _write_failure_record(
                output=output,
                commit=commit,
                dirty=dirty,
                canonical_platform=canonical_platform,
                error=error,
            )
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
