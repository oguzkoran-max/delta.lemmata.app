from __future__ import annotations

import io
import zipfile
from html import unescape
from pathlib import Path

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


def test_shell_renders_without_exception_and_future_actions_are_disabled() -> None:
    app = run_app()
    assert len(app.exception) == 0
    assert [title.value for title in app.title] == ["Set the research purpose"]
    assert [control.label for control in app.segmented_control] == [
        "Research purpose",
        "Analysis mode",
        "Corpus input format",
    ]
    assert [(uploader.label, uploader.accept_multiple_files) for uploader in app.file_uploader] == [
        ("Corpus texts (.txt)", True),
        ("Optional metadata table (.csv)", False),
    ]
    assert [(button.label, button.disabled) for button in app.button] == [
        ("Continue - corpus documentation is not connected", True),
        ("Run analysis - unavailable until setup is complete", True),
    ]
    assert "unavailable" in app.button[1].label.lower()
    captions = [caption.value for caption in app.caption]
    assert any("Intake limits" in value for value in captions)
    assert any("Analysis remains unavailable" in value for value in captions)
    assert [message.value for message in app.info] == [
        "No files submitted. Choose a corpus format and add files when ready."
    ]
    assert len(app.subheader) == 0
    assert [heading.value for heading in app.header] == [
        "Text Proximity",
        "Choose the level of control",
        "Validate the research corpus",
        "Experiment map",
        "Method boundary",
        "Evidence reserved with every run",
        "No analysis run yet",
    ]


def test_purpose_and_mode_controls_update_the_visible_shell() -> None:
    app = run_app()
    app.segmented_control[0].set_value("style_over_time").run()
    app.segmented_control[1].set_value("research").run()
    assert app.segmented_control[0].value == "style_over_time"
    assert app.segmented_control[1].value == "research"
    rendered = unescape("\n".join(element.value for element in app.markdown))
    captions = "\n".join(element.value for element in app.caption)
    assert "How does a writer's work-level stylistic position vary" in rendered
    assert "Chronology alone does not establish" in rendered
    assert rendered.count("Chronology alone does not establish") == 1
    assert "does not prove authorship, intention, influence, or causation" in captions
    assert "documented parameter grid" in captions


def test_v01_shell_has_no_language_selector() -> None:
    app = run_app()
    assert len(app.selectbox) == 0
    assert len(app.radio) == 0


def test_text_and_metadata_uploads_are_validated_and_summarized() -> None:
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
    assert len(app.error) == 0
    rendered = unescape("\n".join(element.value for element in app.markdown))
    assert "one.txt" in rendered
    assert "Corpus text" in rendered
    assert "Lines: 1 · Tokens: 2" in rendered
    assert "metadata.csv" in rendered
    assert "Metadata table" in rendered
    assert "Rows: 1 · Columns: 2" in rendered
    assert "Validated for intake" in rendered
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
    assert "Intake submission rejected" in rendered
    assert "SECRET_PAYLOAD" not in visible_failure
    assert "secret-label.txt" not in visible_failure
    assert app.file_uploader[0].value == []
    assert app.file_uploader[1].value is None
    session_state = repr(app.session_state.filtered_state)
    assert "SECRET_PAYLOAD" not in session_state
    assert "secret-label.txt" not in session_state


def test_metadata_only_is_validated_without_claiming_corpus_readiness() -> None:
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
    assert "Awaiting corpus" in rendered
    assert "Validated for intake" not in rendered


def test_archive_mode_validates_one_zip_and_reports_member_count() -> None:
    app = run_app()
    app.segmented_control[2].set_value("zip_archive").run()
    assert [uploader.label for uploader in app.file_uploader] == [
        "Corpus archive (.zip)",
        "Optional metadata table (.csv)",
    ]
    app.file_uploader[0].upload(
        "corpus.zip",
        make_zip([("one.txt", b"one"), ("two.txt", b"two")]),
        "application/zip",
    ).run()
    assert len(app.exception) == 0
    assert len(app.success) == 1
    assert app.success[0].value.startswith(
        "Intake checks passed · Uploads: 1 · Corpus texts: 2 · Input bytes:"
    )
    rendered = unescape("\n".join(element.value for element in app.markdown))
    assert "corpus.zip" in rendered
    assert "Corpus archive" in rendered
    assert "TXT members: 2 · Expanded bytes: 6" in rendered
    assert "Validated for intake" in rendered
