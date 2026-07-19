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
from datetime import UTC, datetime, timedelta
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
    _document_corpus,
    _download_json,
    _free_port,
    _geometry,
    _observe_console,
    _synthetic_corpus,
    _wait_for_health,
    _wait_for_streamlit_idle,
    _wait_until_enabled,
    _word,
)
from PIL import Image
from playwright.sync_api import Browser, Locator, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from delta_lemmata.job_store import SQLiteJobStore
from delta_lemmata.result_view import ResultCellV1, classical_mds
from delta_lemmata.session_identity import JobId, SessionCapability

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
_A51_MOBILE_PRIMARY_ACTION_WIDTHS = frozenset({375, 390})
_A51_MOBILE_PRIMARY_ACTION_MAX_Y = 780.0


def _evidence_path(path: Path, output: Path) -> str:
    """Serialize one audit artifact relative to its portable evidence root."""

    return path.relative_to(output).as_posix()


def _entry_primary_action_max_y(width: int, height: int) -> float:
    """Return the approved A5.1 first-action fold budget for an entry viewport."""

    if width in _A51_MOBILE_PRIMARY_ACTION_WIDTHS:
        return _A51_MOBILE_PRIMARY_ACTION_MAX_Y
    return float(height)


def _preload_missing_distinct_owner_job(runtime_root: Path) -> None:
    runtime_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(runtime_root, 0o700)
    database_root = runtime_root / "database"
    database_root.mkdir(mode=0o700, exist_ok=True)
    os.chmod(database_root, 0o700)
    store = SQLiteJobStore(
        database_root / "control.sqlite3",
        owner_secret=b"p009-distinct-owner-secret-32-bytes",
        job_id_factory=lambda: JobId.generate(lambda size: b"q" * size),
    )
    capability = SessionCapability.generate(lambda size: b"p" * size)
    at_utc = datetime.now(UTC)
    staged = store.stage_job(capability=capability, at_utc=at_utc)
    store.enqueue_job(
        job_id=staged.job_id,
        capability=capability,
        at_utc=at_utc + timedelta(microseconds=1),
        expected_version=staged.version,
        operation_id="op_" + "9" * 64,
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


def _terminal_payload_cleanup_pass(diagnostics: dict[str, Any]) -> bool:
    """Require every recorded terminal job to have no retained input or work payload."""

    records = diagnostics.get("records")
    if diagnostics.get("available") is not True or not isinstance(records, list) or not records:
        return False
    return all(
        record.get("execution_state") == "terminal"
        and record.get("artifact_states", {}).get("input") == "verified_absent"
        and record.get("artifact_states", {}).get("work") == "verified_absent"
        for record in records
        if isinstance(record, dict)
    ) and all(isinstance(record, dict) for record in records)


def _write_failure_record(
    *,
    output: Path,
    commit: str,
    dirty: bool,
    canonical_platform: bool,
    error: Exception,
) -> None:
    lifecycle = _lifecycle_diagnostics(output)
    record = {
        "schema_version": "1.0.0",
        "git_commit": commit,
        "git_dirty": dirty,
        "canonical_worker_platform": canonical_platform,
        "synthetic_inputs_only": True,
        "failure_type": type(error).__name__,
        "failure_message": str(error),
        "lifecycle_diagnostics": lifecycle,
        "terminal_payload_cleanup_pass": _terminal_payload_cleanup_pass(lifecycle),
        "result": "failed",
    }
    (output / "browser-audit.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _pixel_evidence(locator: Locator, screenshot: Path, output: Path) -> dict[str, Any]:
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
        "screenshot": _evidence_path(screenshot, output),
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


def _persistent_text_evidence(page: Page) -> dict[str, Any]:
    return page.locator('div[data-testid="stMainBlockContainer"]').evaluate(
        r"""root => {
          const offenders = [];
          let checked = 0;
          for (const element of root.querySelectorAll('*')) {
            if (element.closest('[aria-hidden="true"], svg, script, style, template')) continue;
            if (element.classList.contains('material-symbols-rounded')) continue;
            const directText = Array.from(element.childNodes)
              .filter(node => node.nodeType === Node.TEXT_NODE)
              .map(node => node.textContent || '')
              .join(' ')
              .replace(/\s+/g, ' ')
              .trim();
            if (!directText) continue;
            const style = getComputedStyle(element);
            const box = element.getBoundingClientRect();
            if (style.display === 'none' || style.visibility === 'hidden' ||
                Number(style.opacity) === 0 || box.width <= 1 || box.height <= 1) continue;
            checked += 1;
            const size = Number.parseFloat(style.fontSize);
            if (Number.isFinite(size) && size < 12) {
              offenders.push({
                tag: element.tagName.toLowerCase(),
                className: String(element.className || '').slice(0, 120),
                text: directText.slice(0, 120),
                fontSize: size,
              });
            }
          }
          return {checked, offenders, pass: offenders.length === 0};
        }"""
    )


def _table_region_accessibility(page: Page) -> dict[str, Any]:
    regions = page.locator(".delta-table-scroll")
    records = regions.evaluate_all(
        """elements => elements.map((element, index) => {
          const style = getComputedStyle(element);
          const box = element.getBoundingClientRect();
          const visible = style.display !== 'none' && style.visibility !== 'hidden' &&
            box.width > 0 && box.height > 0;
          return {
            index,
            visible,
            role: element.getAttribute('role'),
            label: (element.getAttribute('aria-label') || '').trim(),
            tabIndex: element.getAttribute('tabindex'),
            scrollable: element.scrollWidth > element.clientWidth + 1,
          };
        }).filter(record => record.visible)"""
    )
    contracts_pass = bool(records) and all(
        record["role"] == "region" and bool(record["label"]) and record["tabIndex"] == "0"
        for record in records
    )
    scrollable = next((record for record in records if record["scrollable"]), None)
    focus_ring_pass = False
    keyboard_scroll_pass = scrollable is None
    if scrollable is not None:
        region = regions.nth(int(scrollable["index"]))
        region.focus()
        focus_ring = region.evaluate(
            """element => {
              const style = getComputedStyle(element);
              return {
                active: document.activeElement === element,
                width: Number.parseFloat(style.outlineWidth),
                style: style.outlineStyle,
              };
            }"""
        )
        focus_ring_pass = bool(
            focus_ring["active"]
            and focus_ring["style"] not in {"none", "hidden"}
            and focus_ring["width"] >= 2
        )
        before = int(region.evaluate("element => element.scrollLeft"))
        for _ in range(4):
            page.keyboard.press("ArrowRight")
        page.wait_for_timeout(150)
        after = int(region.evaluate("element => element.scrollLeft"))
        keyboard_scroll_pass = after > before
        region.evaluate("element => { element.scrollLeft = 0; }")
    elif records:
        region = regions.nth(int(records[0]["index"]))
        region.focus()
        focus_ring = region.evaluate(
            """element => {
              const style = getComputedStyle(element);
              return {
                active: document.activeElement === element,
                width: Number.parseFloat(style.outlineWidth),
                style: style.outlineStyle,
              };
            }"""
        )
        focus_ring_pass = bool(
            focus_ring["active"]
            and focus_ring["style"] not in {"none", "hidden"}
            and focus_ring["width"] >= 2
        )
    return {
        "region_count": len(records),
        "contracts_pass": contracts_pass,
        "focus_ring_pass": focus_ring_pass,
        "keyboard_scroll_pass": keyboard_scroll_pass,
        "regions": records,
    }


def _semantic_table_evidence(page: Page, label: str) -> dict[str, Any]:
    table = page.get_by_role("table", name=label, exact=True)
    payload = table.inner_text().encode("utf-8")
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "row_count": table.locator("tbody tr").count(),
    }


def _semantic_table_rows(page: Page, label: str) -> tuple[tuple[str, ...], ...]:
    table = page.get_by_role("table", name=label, exact=True)
    rows = table.locator("tbody tr").evaluate_all(
        """elements => elements.map(row =>
          Array.from(row.querySelectorAll(':scope > th, :scope > td'))
            .map(cell => cell.innerText.trim())
        )"""
    )
    return tuple(tuple(str(cell).strip() for cell in row) for row in rows)


def _semantic_rows_sha256(rows: tuple[tuple[str, ...], ...]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _semantic_result_parity(
    page: Page,
    exported: dict[str, Any],
    mfw: int,
) -> dict[str, Any]:
    cell_payload = next(cell for cell in exported["cells"] if cell["mfw"] == mfw)
    matrix_payload = cell_payload["matrix"]
    document_keys = tuple(matrix_payload["document_keys"])
    expected_matrix = tuple(
        (key, *(f"{float(value):.6f}" for value in values))
        for key, values in zip(document_keys, matrix_payload["values"], strict=True)
    )
    documents = {document["key"]: document for document in exported["documents"]}
    points = classical_mds(ResultCellV1.model_validate(cell_payload))
    expected_mds = tuple(
        (
            str(documents[point.document_key]["title"]),
            str(documents[point.document_key]["role"]),
            f"{point.x:.6f}",
            f"{point.y:.6f}",
        )
        for point in points
    )
    observed_matrix = _semantic_table_rows(page, "Classic Delta distance matrix")
    observed_mds = _semantic_table_rows(page, "MDS coordinate table")
    return {
        "mfw": mfw,
        "matrix_row_count": len(observed_matrix),
        "matrix_expected_sha256": _semantic_rows_sha256(expected_matrix),
        "matrix_observed_sha256": _semantic_rows_sha256(observed_matrix),
        "matrix_export_parity_pass": observed_matrix == expected_matrix,
        "mds_row_count": len(observed_mds),
        "mds_expected_sha256": _semantic_rows_sha256(expected_mds),
        "mds_observed_sha256": _semantic_rows_sha256(observed_mds),
        "mds_matrix_parity_pass": observed_mds == expected_mds,
    }


def _choose_next_result_option(page: Page, reference_radio: Locator) -> None:
    """Move from the checked reference to the next native radio option."""

    if not reference_radio.is_checked():
        raise RuntimeError("Expected the 500 MFW reference option to be checked")
    reference_radio.focus()
    page.keyboard.press("ArrowRight")


def _retry_next_result_option(
    page: Page,
    reference_radio: Locator,
    target_radio: Locator,
) -> None:
    """Repeat one native change sequence after a bounded missing server update."""

    if target_radio.is_checked():
        target_radio.focus()
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(250)
    _choose_next_result_option(page, reference_radio)


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


def _select_next_result_and_wait_for_change(
    page: Page,
    reference_radio: Locator,
    target_radio: Locator,
    semantic_before: dict[str, dict[str, Any]],
    output: Path,
    *,
    max_cycles: int = 8,
    settle_attempts: int = 40,
) -> tuple[dict[str, dict[str, Any]], str]:
    """Drive the native-keyboard result switch until the tables actually change.

    A keyboard event dispatched into the native Streamlit radio can occasionally
    fail to trigger the server rerun that recomputes the 1000 MFW result, leaving
    the target checked while the semantic tables still show 500 MFW (a harness
    event-delivery race, not a user-facing defect). Re-issue the same native
    keyboard sequence, waiting for Streamlit to go idle each cycle, until the
    user-visible tables change. The change requirement is never relaxed: if the
    tables never change, this still fails and captures the stuck state.
    """

    last_error: RuntimeError | None = None
    for cycle in range(max_cycles):
        if cycle == 0:
            _choose_next_result_option(page, reference_radio)
        else:
            _retry_next_result_option(page, reference_radio, target_radio)
        try:
            _wait_for_streamlit_idle(page, timeout_ms=20_000)
        except PlaywrightTimeoutError:
            pass
        try:
            semantic_after = _wait_for_result_selection_update(
                page, target_radio, semantic_before, attempts=settle_attempts
            )
        except RuntimeError as error:
            last_error = error
            continue
        path = "native-keyboard" if cycle == 0 else f"native-keyboard-retry-{cycle}"
        return semantic_after, path
    screenshot = output / "screenshots" / "result-selection-stuck.png"
    page.screenshot(path=str(screenshot), full_page=True)
    raise RuntimeError(
        "Result selection did not produce a stable semantic-table update after "
        f"{max_cycles} native-keyboard cycles; screenshot={screenshot.name}; "
        f"last_error={last_error!r}"
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
        upload = page.get_by_role(
            "region",
            name="Corpus texts (.txt) · Compare Texts · Individual TXT files",
            exact=True,
        )
        upload_button = upload.get_by_role("button").first
        input_mode = page.get_by_role("radiogroup", name="Corpus input format", exact=True)
        desktop_guide = page.locator(".delta-purpose-guide-desktop")
        mobile_guide = page.locator("details.delta-purpose-guide-mobile")
        teaching = page.get_by_role("heading", name="How stylometry works", exact=True)
        skip = _skip_link_evidence(page)
        upload_box = upload.bounding_box()
        upload_button_box = upload_button.bounding_box()
        input_mode_box = input_mode.bounding_box()
        desktop_guide_box = desktop_guide.bounding_box()
        mobile_guide_box = mobile_guide.bounding_box()
        if upload_box is None or upload_button_box is None or input_mode_box is None:
            raise RuntimeError(f"Entry controls are not measurable at {width}x{height}")
        corpus_mode_dom_order_pass = page.evaluate(
            """() => {
                const scope = document.querySelector('.st-key-corpus_inputs');
                const uploader = scope && scope.querySelector(
                    '[class*="st-key-corpus_text_files_"], '
                    + '[class*="st-key-corpus_archive_file_"]'
                );
                const mode = scope && scope.querySelector('.st-key-corpus_input_mode');
                return Boolean(
                    uploader && mode
                    && (mode.compareDocumentPosition(uploader) & Node.DOCUMENT_POSITION_FOLLOWING)
                );
            }"""
        )
        mobile = width <= 760
        if mobile:
            purpose_guide_layout_pass = (
                not desktop_guide.is_visible()
                and mobile_guide.is_visible()
                and mobile_guide_box is not None
                and mobile_guide_box["y"] >= upload_box["y"] + upload_box["height"]
            )
        else:
            purpose_guide_layout_pass = (
                desktop_guide.is_visible()
                and not mobile_guide.is_visible()
                and desktop_guide_box is not None
                and desktop_guide_box["y"] < upload_box["y"]
            )
        corpus_mode_layout_pass = upload_box["y"] >= (
            input_mode_box["y"] + input_mode_box["height"]
        )
        primary_action_max_y = _entry_primary_action_max_y(width, height)
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
                "source_sans_font_loaded": geometry["sourceSansFontLoaded"],
                "uploader_context_pass": upload.count() == 1,
                "upload_before_teaching": (upload_box["y"] < teaching.bounding_box()["y"]),
                "primary_upload_action_y": round(upload_button_box["y"], 3),
                "primary_upload_action_max_y": primary_action_max_y,
                "primary_upload_action_pass": (upload_button_box["y"] <= primary_action_max_y),
                "purpose_guide_layout_pass": purpose_guide_layout_pass,
                "corpus_mode_layout_pass": corpus_mode_layout_pass,
                "corpus_mode_dom_order_pass": corpus_mode_dom_order_pass,
                "skip_target_pass": skip["target_pass"],
                "skip_activation_pass": skip["activation_pass"],
                "skip_bypass_pass": skip["bypass_pass"],
                "screenshot": _evidence_path(screenshot, output),
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
        readiness_status = page.locator(
            '.delta-readiness-band[role="status"][aria-live="polite"][aria-atomic="true"]'
        )
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
                "source_sans_font_loaded": geometry["sourceSansFontLoaded"],
                "readiness_status_pass": readiness_status.count() == 1,
                "correction_selector_count": selector_count,
                "correction_selector_pass": (
                    selector_count == 1
                    and selector_box is not None
                    and selector_box["height"] >= 44
                ),
                "skip_target_pass": skip["target_pass"],
                "skip_activation_pass": skip["activation_pass"],
                "skip_bypass_pass": skip["bypass_pass"],
                "screenshot": _evidence_path(screenshot, output),
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
        persistent_text = _persistent_text_evidence(page)
        table_regions = _table_region_accessibility(page)
        chart_locator = page.locator('[data-testid="stVegaLiteChart"]')
        chart_pixels = tuple(
            _pixel_evidence(
                chart_locator.nth(index),
                output / "screenshots" / f"results-{target}-chart-{index + 1}.png",
                output,
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
                "source_sans_font_loaded": geometry["sourceSansFontLoaded"],
                "persistent_text": persistent_text,
                "table_regions": table_regions,
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
                "screenshot": _evidence_path(screenshot, output),
            }
        )
    page.set_viewport_size({"width": 1280, "height": 900})
    page.wait_for_timeout(300)
    return tuple(results)


def _result_viewport_pass(item: dict[str, Any]) -> bool:
    """Evaluate only contracts that exist on the result surface."""

    return bool(
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
        and item["source_sans_font_loaded"]
        and item["persistent_text"]["pass"]
        and item["table_regions"]["contracts_pass"]
        and item["table_regions"]["focus_ring_pass"]
        and item["table_regions"]["keyboard_scroll_pass"]
        and item["mfw_radio_layout_pass"]
        and item["all_result_cells_visible_pass"]
        and item["mds_metric_aspect_pass"]
        and all(chart["pass"] for chart in item["chart_pixels"])
    )


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
    queue_status = page.locator(
        '.delta-analysis-status[role="status"][aria-live="polite"][aria-atomic="true"]'
    )
    terminal_status = page.locator(
        '.delta-analysis-status[role="alert"][aria-live="assertive"][aria-atomic="true"]'
    )
    queue_evidence: dict[str, Any] | None = None
    for _ in range(600):
        if result_heading.is_visible():
            break
        if queue_evidence is None and queue_status.count() == 1 and queue_status.is_visible():
            queue_text = queue_status.inner_text()
            queue_evidence = {
                "single_status_region_pass": queue_status.count() == 1,
                "complete_instruction_pass": all(
                    phrase in queue_text
                    for phrase in (
                        "Your analysis remains in the queue.",
                        "Run the four comparisons again",
                        "you do not need to upload the texts again",
                        "Status reference: WEB_RUNTIME_ANALYSIS_NOT_READY",
                    )
                ),
                "rejection_language_absent_pass": "Rejection reference" not in queue_text,
            }
            queue_screenshot = output / "screenshots" / "fifo-queue-status.png"
            page.screenshot(path=str(queue_screenshot), full_page=True)
            queue_evidence["screenshot"] = _evidence_path(queue_screenshot, output)
            run_button.focus()
            page.keyboard.press("Enter")
            page.wait_for_timeout(500)
            continue
        if terminal_status.count() == 1 and terminal_status.is_visible():
            terminal_text = terminal_status.inner_text()
            restart = page.get_by_role(
                "button",
                name="Start over with this research purpose",
                exact=False,
            )
            restart_available = False
            for _ in range(25):
                if restart.count() == 1 and restart.is_visible():
                    restart_available = True
                    break
                page.wait_for_timeout(200)
            screenshot = output / "screenshots" / "result-terminal-recovery.png"
            page.screenshot(path=str(screenshot), full_page=True)
            raise RuntimeError(
                "Real worker ended safely with terminal recovery UI: "
                f"restart_available={restart_available}; "
                f"status={terminal_text!r}"
            ) from None
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
            output,
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
    parity_before = _semantic_result_parity(page, exported, 500)

    viewports = _result_viewports(page, output)
    target_option = selector.locator(
        'label[data-testid="stRadioOption"]',
        has_text="1000 MFW",
    )
    if target_option.count() != 1:
        raise RuntimeError("Expected exactly one visible 1000 MFW result card")
    target_radio = selector.get_by_role("radio", name="1000 MFW", exact=True)
    semantic_after, selection_path = _select_next_result_and_wait_for_change(
        page,
        reference_radio,
        target_radio,
        semantic_before,
        output,
    )
    parity_after = _semantic_result_parity(page, exported, 1000)
    page.get_by_role("heading", name="Distance heatmap", level=3, exact=True).wait_for()
    changed_chart_evidence = tuple(
        _pixel_evidence(
            chart_locator.nth(index),
            output / "screenshots" / f"result-chart-{index + 1}-1000-mfw.png",
            output,
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
        "fifo_queue_status_pass": queue_evidence is not None
        and all(value for key, value in queue_evidence.items() if key.endswith("_pass")),
        "fifo_queue_status_evidence": queue_evidence,
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
        "semantic_export_parity_pass": all(
            evidence[check]
            for evidence in (parity_before, parity_after)
            for check in ("matrix_export_parity_pass", "mds_matrix_parity_pass")
        ),
        "semantic_export_parity_evidence": (parity_before, parity_after),
        "semantic_table_evidence_before": semantic_before,
        "semantic_table_evidence_after": semantic_after,
        "result_selection_path": selection_path,
        "chart_pixel_evidence": chart_evidence,
        "changed_chart_pixel_evidence": changed_chart_evidence,
        "canonical_export_sha256": export_digest,
        **export_checks,
        "payload_absent_from_page_pass": canary not in body,
        "viewport_pass": all(_result_viewport_pass(item) for item in viewports),
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
            and item["source_sans_font_loaded"]
            and item["uploader_context_pass"]
            and item["upload_before_teaching"]
            and item["primary_upload_action_pass"]
            and item["purpose_guide_layout_pass"]
            and item["corpus_mode_layout_pass"]
            and item["corpus_mode_dom_order_pass"]
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
            and item["source_sans_font_loaded"]
            and item["readiness_status_pass"]
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
    _preload_missing_distinct_owner_job(output / "runtime")
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

            lifecycle = _lifecycle_diagnostics(output)
            flow["lifecycle"] = {
                "terminal_payload_cleanup_pass": _terminal_payload_cleanup_pass(lifecycle),
                "diagnostics": lifecycle,
            }

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
            print(json.dumps({"result": result["result"], "output": "."}))
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
