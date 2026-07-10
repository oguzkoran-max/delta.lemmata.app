#!/usr/bin/env python3
"""Check the P001 single-version and citation metadata contract."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = json.load(handle)
    return loaded


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = yaml.safe_load(handle)
    return loaded


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    codemeta = load_json(ROOT / "codemeta.json")
    citation = load_yaml(ROOT / "CITATION.cff")
    with (ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)

    errors: list[str] = []
    if codemeta.get("version") != version:
        errors.append("codemeta.json version does not match VERSION")
    if str(citation.get("version")) != version:
        errors.append("CITATION.cff version does not match VERSION")
    dynamic_version = pyproject.get("tool", {}).get("setuptools", {}).get("dynamic", {})
    if dynamic_version.get("version", {}).get("file") != ["VERSION"]:
        errors.append("pyproject.toml does not derive its version from VERSION")
    if pyproject.get("project", {}).get("license") != "MIT":
        errors.append("pyproject.toml license is not MIT")
    if citation.get("license") != "MIT":
        errors.append("CITATION.cff license is not MIT")
    if "MIT" not in str(codemeta.get("license", "")):
        errors.append("codemeta.json license is not MIT")

    serialized = json.dumps(codemeta) + json.dumps(citation)
    for placeholder in ("OWNER", "TODO", "example.com", "10.0000/"):
        if placeholder in serialized:
            errors.append(f"metadata contains placeholder: {placeholder}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"metadata-ok version={version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
