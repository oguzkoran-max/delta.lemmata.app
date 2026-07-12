from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable
from html import unescape
from pathlib import Path
from typing import Any

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"


def run_app() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=20).run()


def make_zip(entries: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return output.getvalue()


def _by_label(elements: Iterable[Any], label: str) -> Any:
    return next(element for element in elements if element.label == label)


def _advance_to_describe(app: AppTest, payload: bytes = b"one text") -> AppTest:
    app.file_uploader[0].upload("one.txt", payload, "text/plain").run()
    app.button(key="corpus_continue").click().run()
    return app


def test_upload_shell_explains_stylometry_and_keeps_future_analysis_absent() -> None:
    app = run_app()
    assert len(app.exception) == 0
    assert [title.value for title in app.title] == []
    assert [control.label for control in app.segmented_control] == [
        "What do you want to investigate?",
        "Corpus input format",
    ]
    assert [(uploader.label, uploader.accept_multiple_files) for uploader in app.file_uploader] == [
        ("Corpus texts (.txt)", True),
        ("Optional metadata table (.csv)", False),
    ]
    assert [(button.label, button.disabled) for button in app.button] == [
        ("Continue to describe the corpus", True),
    ]
    captions = [caption.value for caption in app.caption]
    assert any("Intake limits" in value for value in captions)
    assert [message.value for message in app.info] == [
        "No files submitted. Choose a corpus format and add files when ready."
    ]
    rendered = unescape("\n".join(element.value for element in app.markdown))
    assert rendered.count('<h1 id="delta-entry-title">') == 1
    assert "Discover patterns in writing style." in rendered
    assert "Stylometry compares measurable patterns in language use across texts" in rendered
    assert "such as how often common words recur" in rendered
    assert "without writing R or Python" in rendered
    assert "WHAT STYLOMETRY NOTICES" in rendered
    assert "Small choices become visible when they repeat." in rendered
    assert "Delta compares patterns across documented texts, not isolated words." in rendered
    assert "Illustration only · no corpus analysed" in rendered
    assert rendered.count('class="delta-trace-row"') == 2
    assert rendered.count('<li class="delta-trace-legend-item ') == 4
    assert "delta-entry-pattern" not in rendered
    assert "How stylometry works" in rendered
    assert all(label in rendered for label in ("Observe", "Compare", "Interpret"))
    assert "Conceptual workflow · not an analysis result" in rendered
    assert "Question" in rendered
    assert "Why use it" in rendered
    assert "Do not conclude" in rendered
    assert "Start here" in rendered
    assert "Why parameters come later" in rendered
    assert "Current boundary" not in rendered
    assert "How parameters will work" in rendered
    assert "Tests 100, 300, 500, and 1,000 MFW" in rendered
    assert "500 MFW, 0% culling, whole text, and Classic Delta" in rendered
    assert "this is not a 'best setting'" in rendered
    assert "bounded MFW, culling, segmentation, and distance choices" in rendered
    assert "up to 24 documented combinations" in rendered
    assert "No stylometric analysis is running in this build" in rendered
    assert rendered.count('<nav class="delta-map"') == 1
    assert 'aria-current="step"' in rendered
    assert "Run analysis" not in rendered
    assert "dendrogram" not in rendered.lower()
    assert "distance score" not in rendered.lower()
    assert [heading.value for heading in app.header] == [
        "Upload the research corpus",
        "Method boundary",
    ]


def test_purpose_control_updates_guidance_before_upload() -> None:
    app = run_app()
    app.segmented_control[0].set_value("style_over_time").run()
    assert app.segmented_control[0].value == "style_over_time"
    rendered = unescape("\n".join(element.value for element in app.markdown))
    assert "How does one writer's stylistic position vary" in rendered
    assert "Chronology alone does not establish" in rendered
    assert rendered.count("Chronology alone does not establish") == 1


def test_v01_upload_shell_has_no_locale_selector() -> None:
    app = run_app()
    assert len(app.selectbox) == 0
    assert len(app.radio) == 0


def test_text_and_metadata_uploads_are_validated_and_continue_is_enabled() -> None:
    app = run_app()
    app.file_uploader[0].upload("one.txt", b"one text", "text/plain")
    app.file_uploader[1].upload(
        "metadata.csv",
        b"title,year\nOne,1883",
        "text/csv",
    )
    app.run()
    assert len(app.exception) == 0
    assert [message.value for message in app.success] == [
        "Intake checks passed · Uploads: 2 · Corpus texts: 1 · Input bytes: 27"
    ]
    assert app.button(key="corpus_continue").disabled is False
    rendered = unescape("\n".join(element.value for element in app.markdown))
    assert "one.txt" in rendered
    assert "Corpus text" in rendered
    assert "Lines: 1 · Tokens: 2" in rendered
    assert "metadata.csv" in rendered
    assert "Metadata table" in rendered
    assert "Rows: 1 · Columns: 2" in rendered
    assert "metadata meaning not reviewed" in rendered
    assert "one text" not in rendered


def test_invalid_upload_is_rejected_without_payload_or_label_leakage() -> None:
    app = run_app()
    app.file_uploader[0].upload("secret-label.txt", b"SECRET_PAYLOAD\xff", "")
    app.run()
    assert len(app.exception) == 0
    assert [message.value for message in app.error] == [
        "The submission was rejected and cleared before intake."
    ]
    assert len(app.success) == 0
    rendered = unescape("\n".join(element.value for element in app.markdown))
    captions = "\n".join(element.value for element in app.caption)
    visible_failure = "\n".join((rendered, captions, *(message.value for message in app.error)))
    assert "not valid UTF-8 and NFC" in captions
    assert "Rejection reference: INGEST_INVALID_UTF8" in captions
    assert "SECRET_PAYLOAD" not in visible_failure
    assert "secret-label.txt" not in visible_failure
    assert app.file_uploader[0].value == []
    assert app.file_uploader[1].value is None
    assert app.button(key="corpus_continue").disabled is True
    session_state = repr(app.session_state.filtered_state)
    assert "SECRET_PAYLOAD" not in session_state
    assert "secret-label.txt" not in session_state


def test_metadata_only_is_safe_but_does_not_open_describe() -> None:
    app = run_app()
    app.file_uploader[1].upload(
        "metadata.csv",
        b"title,year\nOne,1883",
        "text/csv",
    ).run()
    assert len(app.exception) == 0
    assert len(app.success) == 0
    assert [message.value for message in app.info] == [
        "Metadata structure passed intake checks. Add a corpus before this stage can be ready."
    ]
    rendered = unescape("\n".join(element.value for element in app.markdown))
    assert "Metadata table" in rendered
    assert app.button(key="corpus_continue").disabled is True


def test_archive_member_catalog_opens_payload_free_guided_documentation() -> None:
    app = run_app()
    app.segmented_control[1].set_value("zip_archive").run()
    assert [uploader.label for uploader in app.file_uploader] == [
        "Corpus archive (.zip)",
        "Optional metadata table (.csv)",
    ]
    app.file_uploader[0].upload(
        "corpus.zip",
        make_zip([("folder/two.txt", b"ZIP_SECRET_TWO"), ("one.txt", b"ZIP_SECRET_ONE")]),
        "application/zip",
    ).run()
    assert len(app.exception) == 0
    assert app.success[0].value.startswith(
        "Intake checks passed · Uploads: 1 · Corpus texts: 2 · Input bytes:"
    )
    rendered = unescape("\n".join(element.value for element in app.markdown))
    assert "corpus.zip" in rendered
    assert "Corpus archive" in rendered
    assert "TXT members: 2 · Expanded bytes: 28" in rendered
    assert "Validated ZIP member catalog" in rendered
    assert "folder/two.txt" in rendered
    assert "one.txt" in rendered
    assert rendered.count("Corpus text from ZIP") == 2
    assert "ZIP_SECRET_ONE" not in rendered
    assert "ZIP_SECRET_TWO" not in rendered
    assert app.button(key="corpus_continue").disabled is False

    app.button(key="corpus_continue").click().run()

    assert [heading.value for heading in app.header][0] == "Describe what each text represents"
    assert [expander.label for expander in app.expander if expander.label[:1].isdigit()] == [
        "1. folder/two.txt",
        "2. one.txt",
    ]
    assert len([item for item in app.text_input if item.label == "Primary author name"]) == 2
    state = repr(app.session_state.filtered_state)
    assert "ZIP_SECRET_ONE" not in state
    assert "ZIP_SECRET_TWO" not in state
    assert "storage_name" not in state


def test_continue_opens_describe_and_clears_every_raw_upload_value() -> None:
    app = _advance_to_describe(run_app(), b"SECRET_TRANSIENT_TEXT")
    assert len(app.exception) == 0
    assert [heading.value for heading in app.header] == [
        "Describe what each text represents",
        "Method boundary",
    ]
    assert [control.label for control in app.segmented_control] == ["Analysis mode"]
    assert len(app.file_uploader) == 0
    assert [button.label for button in app.button] == [
        "Start again with different files",
        "Build corpus review",
    ]
    state = repr(app.session_state.filtered_state)
    assert "SECRET_TRANSIENT_TEXT" not in state
    assert "BrowserUpload" not in state
    assert "storage_name" not in state
    assert "ValidatedCorpusUnit" in state


def test_guided_text_path_builds_review_without_running_analysis() -> None:
    app = _advance_to_describe(run_app())
    _by_label(app.text_input, "Primary author name").input("Carlo Collodi").run()
    _by_label(app.text_input, "Source URL").input("https://www.liberliber.it/").run()
    _by_label(app.selectbox, "Documented rights state").set_value("analysis_only").run()
    app.button(key="guided_build_review").click().run()
    assert len(app.exception) == 0
    assert [heading.value for heading in app.header] == [
        "Review the documented corpus",
        "Method boundary",
    ]
    assert [message.value for message in app.success] == [
        "Corpus documentation has no blockers. Parameter setup remains locked until "
        "the analysis engine and its checks are connected."
    ]
    rendered = unescape("\n".join(element.value for element in app.markdown))
    assert [heading.value for heading in app.subheader] == [
        "Corpus composition",
        "Metadata completeness matrix",
        "Work timeline",
        "Rights action matrix",
        "Actionable corpus checks",
        "Final corpus confirmation",
        "Download the documentation package",
    ]
    assert "Corpus composition data" in rendered
    assert "Metadata completeness matrix" in rendered
    assert 'data-row-key="genre:unknown"' in rendered
    assert 'data-status="warning"' in rendered
    assert 'data-status="complete"' in rendered
    assert "Analysis Only" not in rendered
    assert "Permitted" in rendered
    assert "Prohibited" in rendered
    assert [metric.label for metric in app.metric] == [
        "Independent works",
        "Chronology points",
        "Blockers",
        "Warnings",
        "Rights restrictions",
    ]
    assert any("No stylometric analysis has run" in message.value for message in app.info)
    assert "one text" not in repr(app.session_state.filtered_state)


def test_guided_editor_reports_fields_without_echoing_submitted_values() -> None:
    app = _advance_to_describe(run_app())
    app.button(key="guided_build_review").click().run()
    assert len(app.exception) == 0
    assert len(app.error) == 1
    assert "primary_author_name" in app.error[0].value
    assert "source URL" not in app.error[0].value
    assert [heading.value for heading in app.header][0] == "Describe what each text represents"
