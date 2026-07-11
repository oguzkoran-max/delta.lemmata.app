from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = json.load(handle)
    return loaded


def test_ci_actions_are_commit_pinned_and_match_lock() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    lock = load_json(ROOT / "containers" / "ci-actions.lock.json")
    for action in lock["actions"]:
        reference = f"{action['uses']}@{action['commit']}"
        assert reference in workflow
        assert len(action["commit"]) == 40


def test_ci_verify_fetches_complete_history_for_provenance() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    verify_job = workflow.split("  container:", maxsplit=1)[0]
    assert "fetch-depth: 0" in verify_job


def test_container_base_digest_matches_lock() -> None:
    dockerfile = (ROOT / "containers" / "Dockerfile").read_text(encoding="utf-8")
    lock = load_json(ROOT / "containers" / "base-images.lock.json")
    expected = f"{lock['repository']}:{lock['tag']}@{lock['manifest_list_digest']}"
    assert expected in dockerfile
    assert "--platform=linux/amd64" in dockerfile
    assert lock["verification_status"] == "digest-verified-build-not-run"


def test_python_direct_dependencies_are_locked() -> None:
    with (ROOT / "uv.lock").open("rb") as handle:
        lock = tomllib.load(handle)
    versions = {
        package["name"]: package["version"] for package in lock["package"] if "version" in package
    }
    assert versions["jsonschema"] == "4.26.0"
    assert versions["pydantic"] == "2.13.4"
    assert versions["streamlit"] == "1.59.1"


def test_r_direct_dependencies_are_locked() -> None:
    lock = load_json(ROOT / "renv.lock")
    assert lock["R"]["Version"] == "4.5.2"
    assert lock["Packages"]["renv"]["Version"] == "1.2.3"
    assert lock["Packages"]["stylo"]["Version"] == "0.7.71"
    assert lock["Packages"]["jsonlite"]["Version"] == "2.0.0"
