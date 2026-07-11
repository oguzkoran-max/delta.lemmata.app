from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_records", ROOT / "scripts" / "validate_records.py"
)
assert SPEC is not None and SPEC.loader is not None
VALIDATE_RECORDS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATE_RECORDS)


def test_provenance_links_commits_and_artifacts_are_resolvable() -> None:
    assert VALIDATE_RECORDS.integrity_errors() == []


def _run_record() -> dict[str, Any]:
    path = ROOT / "provenance" / "runs" / "RUN-20260710-0005.json"
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def test_v1_1_input_hash_is_recomputed_from_the_tested_commit() -> None:
    run = _run_record()
    run["configuration_artifacts"] = [copy.deepcopy(run["input_artifacts"][0])]
    run["input_artifacts"][0]["sha256"] = "0" * 64
    run["configuration_artifacts"][0]["sha256"] = "0" * 64
    errors = VALIDATE_RECORDS.artifact_errors(run["run_id"], run)
    assert any("input artifact hash mismatch: .streamlit/config.toml" in error for error in errors)


def test_v1_1_output_hash_is_recomputed_from_the_current_artifact() -> None:
    run = _run_record()
    run["output_artifacts"][0]["sha256"] = "0" * 64
    errors = VALIDATE_RECORDS.artifact_errors(run["run_id"], run)
    assert any("output artifact hash mismatch" in error for error in errors)


def test_v1_1_artifact_paths_must_be_repo_relative() -> None:
    run = copy.deepcopy(_run_record())
    run["input_artifacts"][0]["path"] = "../pyproject.toml"
    errors = VALIDATE_RECORDS.artifact_errors(run["run_id"], run)
    assert any("path is not repo-relative" in error for error in errors)
