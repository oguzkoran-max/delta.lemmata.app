from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_and_corpus_directories_are_gitignored() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in ("data/", "uploads/", "workspaces/", "exports/", "secrets/"):
        assert entry in ignored


def test_environment_example_contains_no_secret_value() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "API_KEY=" not in example
    assert "TOKEN=" not in example
    assert "SECRET=" not in example
