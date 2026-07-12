#!/usr/bin/env python3
"""Audit the P004 Upload -> Describe -> Review flow in a fresh browser."""

from __future__ import annotations

import argparse
import csv
import hashlib
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
    ("reflow-640x800", 640, 800),
    ("mobile-390x844", 390, 844),
    ("mobile-360x800", 360, 800),
    ("reflow-320x800", 320, 800),
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
            log = process.stdout.read() if process.stdout is not None else ""
            raise RuntimeError(f"Streamlit exited before becoming healthy:\n{log[-4000:]}")
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


def _geometry(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const main = document.querySelector('[data-testid="stMainBlockContainer"]');
          const visible = element => {
            const style = getComputedStyle(element);
            const box = element.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden'
              && box.width > 0 && box.height > 0;
          };
          const rgb = value => {
            const channels = value.match(/[0-9.]+/g)?.slice(0, 3).map(Number);
            return channels?.length === 3 ? channels : null;
          };
          const luminance = value => {
            const channels = rgb(value);
            if (!channels) return null;
            const linear = channels.map(channel => {
              const normalized = channel / 255;
              return normalized <= 0.04045
                ? normalized / 12.92
                : ((normalized + 0.055) / 1.055) ** 2.4;
            });
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
          };
          const contrast = (foreground, background) => {
            const first = luminance(foreground);
            const second = luminance(background);
            if (first === null || second === null) return null;
            return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
          };
          const controls = [...document.querySelectorAll(
            '[data-testid="stMainBlockContainer"] button, '
            + '[data-testid="stMainBlockContainer"] input:not([type="file"]), '
            + '[data-testid="stMainBlockContainer"] textarea, '
            + '[data-testid="stMainBlockContainer"] [role="radiogroup"]'
          )].filter(visible);
          const overflowingControls = controls.filter(
            element => element.scrollWidth > element.clientWidth + 1
          ).map(element => ({
            text: (element.textContent || element.getAttribute('aria-label') || '')
              .trim().slice(0, 80),
            clientWidth: element.clientWidth,
            scrollWidth: element.scrollWidth
          }));
          const headings = [...document.querySelectorAll('h1, h2, h3')]
            .filter(visible).map(element => ({
              level: Number(element.tagName.slice(1)),
              text: element.textContent.trim(),
              fontSize: Number.parseFloat(getComputedStyle(element).fontSize),
              box: element.getBoundingClientRect().toJSON()
            }));
          const focusables = [...document.querySelectorAll(
            '[data-testid="stSidebar"] a[href], [data-testid="stSidebar"] button, '
            + '[data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea, '
            + '[data-testid="stSidebar"] select, [data-testid="stSidebar"] [tabindex]'
          )].filter(element => visible(element) && element.tabIndex >= 0);
          const segmentedButtons = [...document.querySelectorAll(
            '[data-testid="stButtonGroup"] button[role="radio"]'
          )].filter(visible).map(element => element.getBoundingClientRect().height);
          const helpButtons = [...document.querySelectorAll('button[aria-label^="Help for"]')]
            .filter(visible).map(element => {
              const box = element.getBoundingClientRect();
              return Math.min(box.width, box.height);
            });
          const entryRegions = [...document.querySelectorAll('section.delta-entry')]
            .filter(visible);
          const methodSteps = [...document.querySelectorAll('.delta-method-step')].filter(visible);
          const purposeGuides = [...document.querySelectorAll('section.delta-purpose-guide')]
            .filter(visible);
          const parameterNotes = [...document.querySelectorAll('section.delta-parameter-note')]
            .filter(visible);
          const parameterItems = [...document.querySelectorAll('.delta-parameter-item')]
            .filter(visible);
          const purposeButtons = [...document.querySelectorAll(
            '.st-key-research_purpose button[role="radio"]'
          )].filter(visible);
          const purposeButtonFontSizes = purposeButtons.map(element =>
            Number.parseFloat(getComputedStyle(element).fontSize)
          );
          const purposeButtonBox = purposeButtons[0]?.getBoundingClientRect();
          const corpusStageBox = document.querySelector(
            '.st-key-corpus_stage'
          )?.getBoundingClientRect();
          const brand = document.querySelector('.delta-brand-name');
          const brandBox = brand?.getBoundingClientRect();
          const brandHit = brandBox
            ? document.elementFromPoint(
                brandBox.left + brandBox.width / 2,
                brandBox.top + brandBox.height / 2
              )
            : null;
          const app = document.querySelector('[data-testid="stAppViewContainer"]');
          const sidebar = document.querySelector('[data-testid="stSidebar"]');
          const entry = document.querySelector('.delta-entry');
          const entryTitle = document.querySelector('.delta-entry h1');
          const sidebarTitle = document.querySelector('.delta-sidebar-title');
          const parameterNote = document.querySelector('.delta-parameter-note');
          const parameterCopy = document.querySelector('.delta-parameter-intro p');
          const appBackground = app ? getComputedStyle(app).backgroundColor : null;
          const sidebarBackground = sidebar ? getComputedStyle(sidebar).backgroundColor : null;
          const entryBackground = entry ? getComputedStyle(entry).backgroundColor : null;
          const entryForeground = entryTitle ? getComputedStyle(entryTitle).color : null;
          const parameterBackground = parameterNote
            ? getComputedStyle(parameterNote).backgroundColor
            : null;
          const parameterForeground = parameterCopy
            ? getComputedStyle(parameterCopy).color
            : null;
          return {
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
            mainScrollWidth: main?.scrollWidth ?? null,
            mainClientWidth: main?.clientWidth ?? null,
            overflowingControls,
            headings,
            sidebarVisibleFocusables: focusables.length,
            expandSidebarVisible: [...document.querySelectorAll(
              '[data-testid="stExpandSidebarButton"]'
            )].some(visible),
            segmentedButtonHeights: segmentedButtons,
            helpButtonTargets: helpButtons,
            entryRegionCount: entryRegions.length,
            methodStepCount: methodSteps.length,
            purposeGuideCount: purposeGuides.length,
            parameterNoteCount: parameterNotes.length,
            parameterItemCount: parameterItems.length,
            purposeButtonCount: purposeButtons.length,
            purposeButtonFontSizes,
            purposeButtonsTop: purposeButtonBox?.top ?? null,
            corpusStageTop: corpusStageBox?.top ?? null,
            brandUnoccluded: Boolean(brand && brandHit && brand.contains(brandHit)),
            palette: {
              appBackground,
              sidebarBackground,
              entryBackground,
              entryBackgroundImage: entry ? getComputedStyle(entry).backgroundImage : null,
              parameterBackground
            },
            contrast: {
              entryTitle: entryForeground && entryBackground
                ? contrast(entryForeground, entryBackground)
                : null,
              sidebarTitle: sidebarTitle && sidebarBackground
                ? contrast(getComputedStyle(sidebarTitle).color, sidebarBackground)
                : null,
              parameterCopy: parameterForeground && parameterBackground
                ? contrast(parameterForeground, parameterBackground)
                : null
            }
          };
        }"""
    )


def _audit_viewport(
    page: Page,
    url: str,
    target: str,
    width: int,
    height: int,
    output: Path,
) -> dict[str, Any]:
    page.goto(url, wait_until="networkidle")
    page.get_by_role("heading", name="Discover patterns in writing style.", level=1).wait_for()
    page.get_by_role("heading", name="Upload the research corpus", level=2).wait_for()
    page.get_by_role("region", name="Corpus texts (.txt)", exact=True).wait_for()
    geometry = _geometry(page)
    map_count = page.locator("nav.delta-map").count()
    active_step_count = page.locator("nav.delta-map [aria-current='step']").count()
    uploader_region = page.get_by_role("region", name="Corpus texts (.txt)", exact=True)
    uploader_box = uploader_region.bounding_box() if uploader_region.count() == 1 else None
    uploader_top = None if uploader_box is None else uploader_box["y"]
    mobile = width <= 760
    h1_sizes = [item["fontSize"] for item in geometry["headings"] if item["level"] == 1]
    h2_sizes = [item["fontSize"] for item in geometry["headings"] if item["level"] == 2]
    expected_h1 = 30 if width <= 340 else (32 if mobile else 40.8)
    heading_scale_pass = (
        len(h1_sizes) == 1
        and abs(h1_sizes[0] - expected_h1) < 0.6
        and bool(h2_sizes)
        and all(abs(size - 20) < 0.6 for size in h2_sizes)
    )
    segmented_pass = bool(geometry["segmentedButtonHeights"]) and all(
        value >= 43.5 for value in geometry["segmentedButtonHeights"]
    )
    help_targets_pass = all(value >= 23.5 for value in geometry["helpButtonTargets"])
    entry_experience_pass = (
        geometry["entryRegionCount"] == 1
        and geometry["methodStepCount"] == 3
        and geometry["purposeGuideCount"] == 1
        and geometry["purposeButtonCount"] == 3
        and all(value >= 13.9 for value in geometry["purposeButtonFontSizes"])
        and page.get_by_text(
            "Stylometry compares measurable patterns in language use", exact=False
        ).count()
        == 1
        and page.get_by_text("Conceptual workflow · not an analysis result", exact=True).count()
        == 1
    )
    parameter_orientation_pass = (
        geometry["parameterNoteCount"] == 1
        and geometry["parameterItemCount"] == 3
        and page.get_by_role("region", name="How parameters will work", exact=True).count() == 1
        and page.get_by_text("Tests 100, 300, 500, and 1,000 MFW", exact=False).count() == 1
        and page.get_by_text("up to 24 documented combinations", exact=False).count() == 1
        and page.get_by_text("No stylometric analysis is running", exact=False).count() == 1
    )
    sidebar_guidance_pass = page.get_by_text("Current boundary", exact=True).count() == 0 and (
        mobile
        or (
            page.get_by_role("region", name="Start here", exact=True).count() == 1
            and page.get_by_text("Why parameters come later", exact=True).count() == 1
        )
    )
    expected_palette = {
        "appBackground": "rgb(248, 249, 250)",
        "sidebarBackground": "rgb(240, 242, 246)",
        "entryBackground": "rgb(225, 245, 238)",
        "entryBackgroundImage": "none",
        "parameterBackground": "rgb(240, 250, 246)",
    }
    family_palette_pass = geometry["palette"] == expected_palette and all(
        value is not None and value >= 4.5 for value in geometry["contrast"].values()
    )
    visible_text = page.locator("body").inner_text().lower()
    no_fake_result_pass = all(
        phrase not in visible_text for phrase in ("dendrogram", "distance score", "cluster result")
    )
    first_action_visible_pass = (
        geometry["purposeButtonsTop"] is not None and geometry["purposeButtonsTop"] <= height + 1
    )
    next_stage_hint_pass = mobile or (
        geometry["corpusStageTop"] is not None and geometry["corpusStageTop"] <= height + 80
    )
    screenshot = output / "screenshots" / f"{target}.png"
    page.screenshot(path=str(screenshot), full_page=True)
    return {
        "target": target,
        "viewport": {"width": width, "height": height},
        "horizontal_overflow": geometry["scrollWidth"] > geometry["clientWidth"],
        "main_horizontal_overflow": geometry["mainScrollWidth"] > geometry["mainClientWidth"],
        "overflowing_controls": geometry["overflowingControls"],
        "single_stepper_pass": map_count == 1 and active_step_count == 1,
        "stepper_count": map_count,
        "active_step_count": active_step_count,
        "uploader_top": uploader_top,
        "first_action_visible_pass": first_action_visible_pass,
        "purpose_buttons_top": geometry["purposeButtonsTop"],
        "next_stage_hint_pass": next_stage_hint_pass,
        "corpus_stage_top": geometry["corpusStageTop"],
        "mobile_sidebar_focus_pass": not mobile or geometry["sidebarVisibleFocusables"] == 0,
        "mobile_sidebar_control_hidden_pass": not mobile or not geometry["expandSidebarVisible"],
        "visible_sidebar_focusables": geometry["sidebarVisibleFocusables"],
        "heading_scale_pass": heading_scale_pass,
        "headings": geometry["headings"],
        "segmented_target_pass": segmented_pass,
        "segmented_button_heights": geometry["segmentedButtonHeights"],
        "help_target_pass": help_targets_pass,
        "help_button_targets": geometry["helpButtonTargets"],
        "entry_experience_pass": entry_experience_pass,
        "parameter_orientation_pass": parameter_orientation_pass,
        "sidebar_guidance_pass": sidebar_guidance_pass,
        "family_palette_pass": family_palette_pass,
        "family_palette": geometry["palette"],
        "family_contrast": geometry["contrast"],
        "entry_region_count": geometry["entryRegionCount"],
        "method_step_count": geometry["methodStepCount"],
        "purpose_guide_count": geometry["purposeGuideCount"],
        "purpose_button_font_sizes": geometry["purposeButtonFontSizes"],
        "no_fake_result_pass": no_fake_result_pass,
        "brand_unoccluded_pass": geometry["brandUnoccluded"],
        "continue_initially_disabled_pass": page.get_by_role(
            "button", name="Continue to describe the corpus", exact=True
        ).is_disabled(),
        "screenshot": _display_path(screenshot),
    }


def _choose_selectbox(page: Page, label: str, option: str) -> None:
    page.get_by_label(label, exact=True).click()
    page.get_by_role("option", name=option, exact=True).click()


def _download_csv(page: Page, button_name: str) -> tuple[str, list[dict[str, str]]]:
    with page.expect_download() as download_info:
        page.get_by_role("button", name=button_name, exact=True).click()
    download = download_info.value
    path = download.path()
    if path is None:
        raise RuntimeError(f"Browser download has no local path: {button_name}")
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"), newline="")))
    return download.suggested_filename, rows


def _zip_payload(entries: tuple[tuple[str, bytes], ...]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return output.getvalue()


def _audit_guided_flow(
    browser: Browser,
    url: str,
    requests: list[str],
    console_messages: list[dict[str, str]],
    output: Path,
) -> dict[str, Any]:
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.on("request", lambda request: requests.append(request.url))
    _observe_console(page, console_messages)
    page.goto(url, wait_until="networkidle")
    page.get_by_role("heading", name="Discover patterns in writing style.", level=1).wait_for()

    proximity = page.get_by_role("radio", name="Compare Texts", exact=True)
    proximity.focus()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("Space")
    page.wait_for_timeout(800)
    keyboard_selection_pass = (
        page.get_by_role("radio", name="Compare Groups", exact=True).get_attribute("aria-checked")
        == "true"
    )
    page.keyboard.press("ArrowLeft")
    page.keyboard.press("Space")
    page.wait_for_timeout(800)

    corpus_region = page.get_by_role("region", name="Corpus texts (.txt)", exact=True)
    corpus_region.locator('input[type="file"]').set_input_files(
        {"name": "one.txt", "mimeType": "text/plain", "buffer": b"one text"}
    )
    page.get_by_text("Intake checks passed · Uploads: 1", exact=False).wait_for()
    continue_button = page.get_by_role("button", name="Continue to describe the corpus", exact=True)
    continue_enabled_pass = continue_button.is_enabled()
    page.screenshot(
        path=str(output / "screenshots" / "guided-upload-ready.png"),
        full_page=True,
    )
    continue_button.click()
    page.get_by_role("heading", name="Describe what each text represents", level=2).wait_for()
    describe_file_inputs_removed = page.locator('input[type="file"]').count() == 0
    payload_absent_describe = "one text" not in page.locator("body").inner_text()
    describe_active_pass = (
        "DESCRIBE" in page.locator("nav.delta-map [aria-current='step']").inner_text().upper()
    )
    page.get_by_label("Primary author name", exact=True).fill("Carlo Collodi")
    source_url = page.get_by_label("Source URL", exact=True)
    source_url.fill("https://www.liberliber.it/")
    source_url.press("Tab")
    page.get_by_text("Date accessed", exact=True).wait_for()
    _choose_selectbox(
        page,
        "Documented rights state",
        "Analysis only · permit upload and analysis, prohibit text export",
    )
    page.keyboard.press("Escape")
    page.screenshot(
        path=str(output / "screenshots" / "guided-describe-complete.png"),
        full_page=True,
    )
    page.get_by_role("button", name="Build corpus review", exact=True).click()
    page.get_by_role("heading", name="Review the documented corpus", level=2).wait_for()
    review_ready_pass = (
        page.get_by_text("Corpus documentation has no blockers", exact=False).count() == 1
    )
    review_active_pass = (
        "REVIEW" in page.locator("nav.delta-map [aria-current='step']").inner_text().upper()
    )
    rights_table_pass = (
        page.get_by_role("table", name="Rights action matrix", exact=True).count() == 1
    )
    composition_table = page.get_by_role("table", name="Corpus composition data", exact=True)
    completeness_table = page.get_by_role("table", name="Metadata completeness matrix", exact=True)
    timeline_table = page.get_by_role("table", name="Work timeline data", exact=True)
    composition_table_pass = composition_table.count() == 1
    completeness_table_pass = completeness_table.count() == 1
    timeline_table_pass = timeline_table.count() == 1
    composition_layout_pass = page.locator(".delta-composition-row").evaluate_all(
        """elements => elements.every(element => {
          const count = element.querySelector('.delta-composition-count');
          if (!count) return false;
          const rowBox = element.getBoundingClientRect();
          const countBox = count.getBoundingClientRect();
          const style = getComputedStyle(count);
          return element.scrollWidth <= element.clientWidth + 1
            && style.display !== 'none'
            && style.visibility !== 'hidden'
            && countBox.left >= rowBox.left - 1
            && countBox.right <= rowBox.right + 1;
        })"""
    )
    visual_keys = page.locator(".delta-composition-bars [data-row-key]").evaluate_all(
        "elements => elements.map(element => element.dataset.rowKey)"
    )
    composition_table_keys = composition_table.locator("tbody tr[data-row-key]").evaluate_all(
        "elements => elements.map(element => element.dataset.rowKey)"
    )
    composition_filename, composition_rows = _download_csv(page, "Download composition CSV")
    completeness_filename, completeness_rows = _download_csv(page, "Download completeness CSV")
    composition_csv_keys = [
        f"{row['dimension']}:{row['category_value']}" for row in composition_rows
    ]
    composition_key_parity_pass = visual_keys == composition_table_keys == composition_csv_keys
    totals_by_dimension: dict[str, int] = {}
    denominators = set()
    for row in composition_rows:
        totals_by_dimension[row["dimension"]] = totals_by_dimension.get(row["dimension"], 0) + int(
            row["work_count"]
        )
        denominators.add(int(row["corpus_work_count"]))
    composition_sum_pass = (
        len(denominators) == 1
        and len(totals_by_dimension) == 5
        and set(totals_by_dimension.values()) == denominators
    )
    work_count = next(iter(denominators), 0)
    timeline_rows = timeline_table.locator("tbody tr[data-row-key]")
    timeline_selector = page.get_by_role(
        "radiogroup", name="Select a documented work on the chronology", exact=True
    )
    selected_timeline_row = timeline_table.locator("tbody tr[aria-current='true']")
    timeline_detail = page.locator(".delta-timeline-detail[data-row-key]")
    timeline_selection_pass = (
        timeline_selector.count() == 1
        and timeline_selector.get_by_role("radio").count() == work_count
        and timeline_rows.count() == work_count
        and selected_timeline_row.count() == 1
        and timeline_detail.count() == 1
        and selected_timeline_row.get_attribute("data-row-key")
        == timeline_detail.get_attribute("data-row-key")
    )
    matrix_rows = completeness_table.locator("tbody tr[data-row-key]")
    matrix_cells = completeness_table.locator("tbody td[data-group][data-status]")
    completeness_table_keys = matrix_cells.evaluate_all(
        "elements => elements.map(element => "
        "`${element.closest('tr').dataset.rowKey}:${element.dataset.group}`)"
    )
    completeness_csv_keys = [f"{row['row_key']}:{row['group']}" for row in completeness_rows]
    allowed_statuses = {"complete", "missing", "warning", "conflict"}
    completeness_shape_pass = (
        matrix_rows.count() == work_count
        and matrix_cells.count() == work_count * 7
        and len(completeness_rows) == work_count * 7
    )
    completeness_key_parity_pass = completeness_table_keys == completeness_csv_keys
    completeness_status_pass = (
        {row["status"] for row in completeness_rows} <= allowed_statuses
        and set(matrix_cells.evaluate_all("elements => elements.map(e => e.dataset.status)"))
        <= allowed_statuses
        and all(
            cell.inner_text().splitlines()[0].casefold() in allowed_statuses
            for cell in matrix_cells.all()
        )
    )
    review_csv_payload_absent = "one text" not in repr(composition_rows + completeness_rows)
    download_names_pass = (
        composition_filename == "delta-corpus-composition.csv"
        and completeness_filename == "delta-metadata-completeness.csv"
    )
    download_count = page.get_by_role("button", name="Download", exact=False).count()
    scroll_regions = page.locator(".delta-table-scroll[role='region'][aria-label][tabindex='0']")
    scroll_region_pass = scroll_regions.count() == 4
    focus_results = []
    for region in scroll_regions.all():
        region.focus()
        focus_results.append(
            region.evaluate(
                "element => { const style = getComputedStyle(element); "
                "return document.activeElement === element "
                "&& style.outlineStyle !== 'none' "
                "&& Number.parseFloat(style.outlineWidth) >= 2; }"
            )
        )
    scroll_focus_pass = bool(focus_results) and all(focus_results)
    confirmation = page.get_by_role(
        "checkbox",
        name="I reviewed the file-to-work mappings and the documented rights records.",
        exact=True,
    )
    confirmation_initial_pass = confirmation.is_enabled() and not confirmation.is_checked()
    confirmation.focus()
    page.keyboard.press("Space")
    page.get_by_text("Confirmation recorded for this inventory.", exact=True).wait_for()
    confirmation_recorded_pass = confirmation.is_checked()
    analysis_locked_pass = (
        page.get_by_text("No stylometric analysis has run", exact=False).count() == 1
    )
    payload_absent_review = "one text" not in page.locator("body").inner_text()
    composition_screenshot = output / "screenshots" / "guided-composition-bars.png"
    completeness_screenshot = output / "screenshots" / "guided-completeness-matrix.png"
    timeline_screenshot = output / "screenshots" / "guided-work-timeline.png"
    page.locator(".delta-composition-bars").screenshot(path=str(composition_screenshot))
    completeness_table.screenshot(path=str(completeness_screenshot))
    timeline_table.screenshot(path=str(timeline_screenshot))
    page.evaluate(
        """() => {
          window.scrollTo(0, 0);
          const main = document.querySelector('[data-testid="stMain"]');
          if (main) main.scrollTop = 0;
        }"""
    )
    page.screenshot(
        path=str(output / "screenshots" / "guided-review-ready.png"),
        full_page=True,
    )
    review_viewports = []
    for target, viewport_width, viewport_height in VIEWPORTS:
        page.set_viewport_size({"width": viewport_width, "height": viewport_height})
        page.wait_for_timeout(150)
        geometry = _geometry(page)
        screenshot = output / "screenshots" / f"review-{target}.png"
        page.screenshot(path=str(screenshot), full_page=True)
        if target == "mobile-390x844":
            page.locator(".delta-composition-bars").screenshot(
                path=str(output / "screenshots" / "guided-composition-bars-mobile.png")
            )
        review_viewports.append(
            {
                "target": target,
                "viewport": {"width": viewport_width, "height": viewport_height},
                "horizontal_overflow": geometry["scrollWidth"] > geometry["clientWidth"],
                "main_horizontal_overflow": (
                    geometry["mainScrollWidth"] > geometry["mainClientWidth"]
                ),
                "overflowing_controls": geometry["overflowingControls"],
                "screenshot": _display_path(screenshot),
            }
        )
    review_viewports_pass = all(
        not item["horizontal_overflow"]
        and not item["main_horizontal_overflow"]
        and not item["overflowing_controls"]
        for item in review_viewports
    )
    result = {
        "keyboard_purpose_selection_pass": keyboard_selection_pass,
        "continue_enabled_pass": continue_enabled_pass,
        "describe_file_inputs_removed_pass": describe_file_inputs_removed,
        "payload_absent_describe_pass": payload_absent_describe,
        "describe_active_step_pass": describe_active_pass,
        "review_ready_pass": review_ready_pass,
        "review_active_step_pass": review_active_pass,
        "composition_table_pass": composition_table_pass,
        "composition_layout_pass": composition_layout_pass,
        "completeness_table_pass": completeness_table_pass,
        "timeline_table_pass": timeline_table_pass,
        "timeline_selection_pass": timeline_selection_pass,
        "rights_table_pass": rights_table_pass,
        "composition_key_parity_pass": composition_key_parity_pass,
        "composition_sum_pass": composition_sum_pass,
        "completeness_shape_pass": completeness_shape_pass,
        "completeness_key_parity_pass": completeness_key_parity_pass,
        "completeness_status_pass": completeness_status_pass,
        "scroll_region_semantics_pass": scroll_region_pass,
        "scroll_region_focus_pass": scroll_focus_pass,
        "review_csv_payload_absent_pass": review_csv_payload_absent,
        "download_names_pass": download_names_pass,
        "download_buttons_pass": download_count == 5,
        "download_button_count": download_count,
        "confirmation_initial_pass": confirmation_initial_pass,
        "confirmation_recorded_pass": confirmation_recorded_pass,
        "analysis_locked_pass": analysis_locked_pass,
        "payload_absent_review_pass": payload_absent_review,
        "review_viewports_pass": review_viewports_pass,
        "review_viewports": review_viewports,
        "composition_screenshot": _display_path(composition_screenshot),
        "completeness_screenshot": _display_path(completeness_screenshot),
        "timeline_screenshot": _display_path(timeline_screenshot),
    }
    context.close()
    return result


def _audit_zip_flow(
    browser: Browser,
    url: str,
    requests: list[str],
    console_messages: list[dict[str, str]],
    output: Path,
) -> dict[str, Any]:
    entries = (
        ("early/one.txt", b"ZIP_CANARY_EARLY text"),
        ("late/two.txt", b"ZIP_CANARY_LATE text"),
    )
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.on("request", lambda request: requests.append(request.url))
    _observe_console(page, console_messages)
    page.goto(url, wait_until="networkidle")
    page.get_by_role("heading", name="Discover patterns in writing style.", level=1).wait_for()
    page.get_by_role("radio", name="One ZIP archive", exact=True).click()
    archive_region = page.get_by_role("region", name="Corpus archive (.zip)", exact=True)
    archive_region.locator('input[type="file"]').set_input_files(
        {
            "name": "collodi.zip",
            "mimeType": "application/zip",
            "buffer": _zip_payload(entries),
        }
    )
    page.get_by_text("Intake checks passed · Uploads: 1 · Corpus texts: 2", exact=False).wait_for()
    member_region = page.get_by_role("region", name="Validated ZIP member catalog", exact=True)
    member_rows = member_region.locator(".delta-intake-row[role='listitem']")
    member_text = member_region.inner_text()
    expected_digests = [hashlib.sha256(payload).hexdigest()[:12] for _, payload in entries]
    member_catalog_pass = (
        member_rows.count() == 2
        and all(name in member_text for name, _ in entries)
        and all(digest in member_text for digest in expected_digests)
    )
    member_catalog_screenshot = output / "screenshots" / "zip-member-catalog.png"
    member_region.screenshot(path=str(member_catalog_screenshot))
    payload_absent_upload_pass = all(
        payload.decode("utf-8") not in page.locator("body").inner_text() for _, payload in entries
    )
    continue_button = page.get_by_role("button", name="Continue to describe the corpus")
    continue_enabled_pass = continue_button.is_enabled()
    page.screenshot(path=str(output / "screenshots" / "zip-upload-ready.png"), full_page=True)

    continue_button.click()
    page.get_by_role("heading", name="Describe what each text represents", level=2).wait_for()
    describe_work_count_pass = page.get_by_label("Primary author name", exact=True).count() == 2
    describe_labels_pass = all(
        page.get_by_text(f"{index}. {name}", exact=True).count() == 1
        for index, (name, _) in enumerate(entries, start=1)
    )
    describe_payload_absent_pass = all(
        payload.decode("utf-8") not in page.locator("body").inner_text() for _, payload in entries
    )
    describe_file_inputs_removed_pass = page.locator('input[type="file"]').count() == 0
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate(
        """() => {
          window.scrollTo(0, 0);
          const main = document.querySelector('[data-testid="stMain"]');
          if (main) main.scrollTop = 0;
        }"""
    )
    page.wait_for_timeout(150)
    mobile_describe_geometry = _geometry(page)
    mobile_describe_pass = (
        mobile_describe_geometry["scrollWidth"] <= mobile_describe_geometry["clientWidth"]
        and mobile_describe_geometry["mainScrollWidth"]
        <= mobile_describe_geometry["mainClientWidth"]
        and not mobile_describe_geometry["overflowingControls"]
        and mobile_describe_geometry["brandUnoccluded"]
    )
    page.screenshot(path=str(output / "screenshots" / "zip-describe-mobile.png"), full_page=True)
    page.set_viewport_size({"width": 1280, "height": 900})

    second_expander = page.locator('[data-testid="stExpander"]').filter(has_text="2. late/two.txt")
    second_expander.locator("summary").click()
    authors = page.get_by_label("Primary author name", exact=True)
    sources = page.get_by_label("Source URL", exact=True)
    for index in range(2):
        authors.nth(index).fill("Carlo Collodi")
        sources.nth(index).fill("https://www.liberliber.it/")
    sources.nth(1).press("Tab")
    page.get_by_text("Date accessed", exact=True).nth(1).wait_for()
    page.get_by_role("button", name="Build corpus review", exact=True).click()
    page.get_by_role("heading", name="Review the documented corpus", level=2).wait_for()
    review_blocked_transparently_pass = (
        page.get_by_text("Corpus documentation contains blockers", exact=False).count() == 1
    )

    timeline = page.get_by_role("table", name="Work timeline data", exact=True)
    completeness = page.get_by_role("table", name="Metadata completeness matrix", exact=True)
    rights = page.get_by_role("table", name="Rights action matrix", exact=True)
    review_shape_pass = (
        timeline.locator("tbody tr[data-row-key]").count() == 2
        and completeness.locator("tbody tr[data-row-key]").count() == 2
        and rights.locator("tbody tr").count() == 2
        and page.get_by_role(
            "radiogroup", name="Select a documented work on the chronology", exact=True
        )
        .get_by_role("radio")
        .count()
        == 2
    )
    review_payload_absent_pass = all(
        payload.decode("utf-8") not in page.locator("body").inner_text() for _, payload in entries
    )
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate(
        """() => {
          window.scrollTo(0, 0);
          const main = document.querySelector('[data-testid="stMain"]');
          if (main) main.scrollTop = 0;
        }"""
    )
    page.wait_for_timeout(150)
    mobile_review_geometry = _geometry(page)
    mobile_review_pass = (
        mobile_review_geometry["scrollWidth"] <= mobile_review_geometry["clientWidth"]
        and mobile_review_geometry["mainScrollWidth"] <= mobile_review_geometry["mainClientWidth"]
        and not mobile_review_geometry["overflowingControls"]
        and mobile_review_geometry["brandUnoccluded"]
    )
    page.screenshot(path=str(output / "screenshots" / "zip-review-mobile.png"), full_page=True)
    context.close()
    return {
        "member_catalog_pass": member_catalog_pass,
        "member_catalog_screenshot": _display_path(member_catalog_screenshot),
        "payload_absent_upload_pass": payload_absent_upload_pass,
        "continue_enabled_pass": continue_enabled_pass,
        "describe_work_count_pass": describe_work_count_pass,
        "describe_labels_pass": describe_labels_pass,
        "describe_payload_absent_pass": describe_payload_absent_pass,
        "describe_file_inputs_removed_pass": describe_file_inputs_removed_pass,
        "mobile_describe_pass": mobile_describe_pass,
        "mobile_describe_geometry": mobile_describe_geometry,
        "review_blocked_transparently_pass": review_blocked_transparently_pass,
        "review_shape_pass": review_shape_pass,
        "review_payload_absent_pass": review_payload_absent_pass,
        "mobile_review_pass": mobile_review_pass,
        "mobile_review_geometry": mobile_review_geometry,
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
    environment["DELTA_BUILD_ID"] = "p004-guided-browser-audit"
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
                _observe_console(page, console_messages)
                audits.append(_audit_viewport(page, url, target, width, height, output))
                context.close()
            guided_flow = _audit_guided_flow(browser, url, requests, console_messages, output)
            zip_flow = _audit_zip_flow(browser, url, requests, console_messages, output)
            browser.close()

        external_hosts = sorted(
            {
                parsed.hostname
                for request_url in requests
                if (parsed := urlparse(request_url)).hostname not in {"127.0.0.1", "localhost"}
            }
        )
        viewport_pass = all(
            not audit["horizontal_overflow"]
            and not audit["main_horizontal_overflow"]
            and not audit["overflowing_controls"]
            and audit["single_stepper_pass"]
            and audit["first_action_visible_pass"]
            and audit["next_stage_hint_pass"]
            and audit["mobile_sidebar_focus_pass"]
            and audit["mobile_sidebar_control_hidden_pass"]
            and audit["heading_scale_pass"]
            and audit["segmented_target_pass"]
            and audit["help_target_pass"]
            and audit["entry_experience_pass"]
            and audit["parameter_orientation_pass"]
            and audit["sidebar_guidance_pass"]
            and audit["family_palette_pass"]
            and audit["no_fake_result_pass"]
            and audit["brand_unoccluded_pass"]
            and audit["continue_initially_disabled_pass"]
            for audit in audits
        )
        interaction_pass = all(value for key, value in guided_flow.items() if key.endswith("_pass"))
        zip_pass = all(value for key, value in zip_flow.items() if key.endswith("_pass"))
        passed = (
            viewport_pass
            and interaction_pass
            and zip_pass
            and not external_hosts
            and not console_messages
        )
        result = {
            "schema_version": "1.0.0",
            "target_url": url,
            "audit_method": "Tracked Python Playwright harness and fresh local Streamlit process.",
            "synthetic_inputs_only": True,
            "fresh_browser_context_per_viewport": True,
            "audits": audits,
            "guided_flow": guided_flow,
            "zip_flow": zip_flow,
            "console_messages": console_messages,
            "external_hosts_observed": external_hosts,
            "network_scope": "Browser requests observed by Playwright; not a packet capture.",
            "retention_scope": (
                "The harness verifies rendered UI and browser-visible state, not proxy, "
                "container, operating-system, or host retention."
            ),
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
