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


def test_completed_ticket_acceptance_evidence_must_resolve() -> None:
    path = ROOT / "provenance" / "tickets" / "P002.json"
    ticket: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    ticket["acceptance"][0]["status"] = "pending"
    ticket["acceptance"][1]["evidence"] = []
    ticket["acceptance"][2]["evidence"] = ["../outside.json"]
    ticket["acceptance"][3]["evidence"] = ["provenance/evidence/P002/missing.json"]
    errors = VALIDATE_RECORDS.acceptance_evidence_errors("P002", ticket)
    assert any("incomplete acceptance P002-AC-01" in error for error in errors)
    assert any("acceptance has no evidence P002-AC-02" in error for error in errors)
    assert any("path is not repo-relative" in error for error in errors)
    assert any("missing acceptance evidence P002-AC-04" in error for error in errors)


def test_ticket_and_run_links_must_be_reciprocal() -> None:
    tickets = {
        "P001": {
            "schema_version": "1.1.0",
            "run_ids": ["RUN-VALID", "RUN-NO-BACKLINK", "RUN-MISSING"],
        },
    }
    runs = {
        "RUN-VALID": {"ticket_ids": ["P001"]},
        "RUN-NO-BACKLINK": {"ticket_ids": []},
        "RUN-REVERSE-ONLY": {"ticket_ids": ["P001"]},
        "RUN-MISSING-TICKET": {"ticket_ids": ["P404"]},
    }
    errors = VALIDATE_RECORDS.reciprocal_ticket_run_errors(tickets, runs)
    assert "P001: unresolved Run RUN-MISSING" in errors
    assert "P001: Run does not link back to Ticket RUN-NO-BACKLINK" in errors
    assert "RUN-REVERSE-ONLY: Ticket does not link back to Run P001" in errors
    assert "RUN-MISSING-TICKET: unresolved Ticket P404" in errors
    assert all("RUN-VALID" not in error for error in errors)


def test_only_one_ticket_may_be_in_progress() -> None:
    tickets = {
        "P007": {"status": "blocked"},
        "P008": {"status": "in-progress"},
        "P009": {"status": "in-progress"},
    }

    assert VALIDATE_RECORDS.active_ticket_errors(tickets) == ["multiple active tickets: P008, P009"]
    tickets["P009"]["status"] = "blocked"
    assert VALIDATE_RECORDS.active_ticket_errors(tickets) == []
