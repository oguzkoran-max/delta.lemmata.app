from __future__ import annotations

from html import unescape
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"


def run_app() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=20).run()


def test_shell_renders_without_exception_and_future_actions_are_disabled() -> None:
    app = run_app()
    assert len(app.exception) == 0
    assert [title.value for title in app.title] == ["Set the research purpose"]
    assert [control.label for control in app.segmented_control] == [
        "Research purpose",
        "Analysis mode",
    ]
    assert len(app.file_uploader) == 1
    assert app.file_uploader[0].disabled is True
    assert [(button.label, button.disabled) for button in app.button] == [
        ("Add metadata table", True),
        ("Continue to parameters", True),
        ("Run analysis", True),
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
    assert "documented parameter grid" in captions


def test_v01_shell_has_no_language_selector() -> None:
    app = run_app()
    assert len(app.selectbox) == 0
    assert len(app.radio) == 0
