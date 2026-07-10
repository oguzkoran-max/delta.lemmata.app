from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_all_metadata_uses_the_canonical_version() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    with (ROOT / "codemeta.json").open(encoding="utf-8") as handle:
        codemeta: dict[str, Any] = json.load(handle)
    with (ROOT / "CITATION.cff").open(encoding="utf-8") as handle:
        citation: dict[str, Any] = yaml.safe_load(handle)
    with (ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)

    assert codemeta["version"] == version
    assert str(citation["version"]) == version
    assert pyproject["tool"]["setuptools"]["dynamic"]["version"]["file"] == ["VERSION"]


def test_uncreated_identifiers_are_not_invented() -> None:
    codemeta = (ROOT / "codemeta.json").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    combined = codemeta + citation
    assert "codeRepository" not in combined
    assert "doi:" not in combined.lower()
    assert "swh:" not in combined.lower()
