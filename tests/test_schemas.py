from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import ValidationError

from delta_lemmata.provenance import load_schema, validate_record

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = json.load(handle)
    return loaded


def read_first_jsonl(path: Path) -> dict[str, Any]:
    first = next(line for line in path.read_text(encoding="utf-8").splitlines() if line)
    loaded: dict[str, Any] = json.loads(first)
    return loaded


@pytest.mark.parametrize(
    "schema_name",
    [
        "asset-rights",
        "human-decision",
        "prompt-event",
        "release-manifest",
        "run",
        "ticket",
    ],
)
def test_schema_is_valid_draft_2020_12(schema_name: str) -> None:
    loaded = load_schema(SCHEMAS / f"{schema_name}.schema.json")
    assert loaded["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_actual_p001_prompt_event_validates() -> None:
    event = read_first_jsonl(ROOT / "provenance" / "prompt-events.jsonl")
    validate_record(event, SCHEMAS / "prompt-event.schema.json")


def test_summary_only_prompt_cannot_claim_a_response_hash() -> None:
    event = read_first_jsonl(ROOT / "provenance" / "prompt-events.jsonl")
    event["response_sha256"] = "0" * 64
    with pytest.raises(ValidationError):
        validate_record(event, SCHEMAS / "prompt-event.schema.json")


def test_invalid_timestamp_is_rejected() -> None:
    event = read_first_jsonl(ROOT / "provenance" / "prompt-events.jsonl")
    event["captured_at_utc"] = "not-a-timestamp"
    with pytest.raises(ValidationError):
        validate_record(event, SCHEMAS / "prompt-event.schema.json")


def test_accepted_human_decision_requires_human_acceptance() -> None:
    decision = read_first_jsonl(ROOT / "provenance" / "human-decision-ledger.jsonl")
    decision["acceptance_owner"] = None
    with pytest.raises(ValidationError):
        validate_record(decision, SCHEMAS / "human-decision.schema.json")


def test_unknown_rights_cannot_allow_public_redistribution() -> None:
    record: dict[str, Any] = {
        "schema_version": "1.0.0",
        "asset_id": "ASSET-fixture",
        "source_id": "fixture-source",
        "title": "Synthetic fixture",
        "asset_type": "transcription",
        "rights_status": "unknown",
        "license": None,
        "permissions": {
            "upload": True,
            "analysis": True,
            "export": False,
            "public_redistribution": True,
        },
        "evidence_urls": [],
        "jurisdiction": None,
        "assessed_by": "Test suite",
        "assessed_at_utc": "2026-07-10T12:00:00Z",
        "notes": "Synthetic record only.",
    }
    with pytest.raises(ValidationError):
        validate_record(record, SCHEMAS / "asset-rights.schema.json")

    permitted = copy.deepcopy(record)
    permitted["rights_status"] = "verified-open"
    permitted["license"] = "CC0-1.0"
    validate_record(permitted, SCHEMAS / "asset-rights.schema.json")


def test_completed_ticket_requires_close_time() -> None:
    ticket = read_json(ROOT / "provenance" / "tickets" / "P001.json")
    ticket["status"] = "complete"
    ticket["closed_at_utc"] = None
    with pytest.raises(ValidationError):
        validate_record(ticket, SCHEMAS / "ticket.schema.json")


def test_run_schema_1_1_requires_path_qualified_configuration_and_replay() -> None:
    run = read_json(ROOT / "provenance" / "runs" / "RUN-20260710-0005.json")
    run["schema_version"] = "1.1.0"
    run.pop("config_sha256")
    run["configuration_artifacts"] = [run["input_artifacts"][0]]
    run["replay"] = {
        "level": "partial",
        "working_directory": "repository root",
        "command": "./scripts/verify.sh",
        "limitations": ["Browser checks are separate."],
    }
    run["command"] = run["replay"]["command"]
    run["supersedes"] = []
    validate_record(run, SCHEMAS / "run.schema.json")

    run["config_sha256"] = "0" * 64
    with pytest.raises(ValidationError):
        validate_record(run, SCHEMAS / "run.schema.json")


def test_ticket_schema_1_1_requires_run_and_supplemental_evidence_links() -> None:
    ticket = read_json(ROOT / "provenance" / "tickets" / "P002.json")
    ticket["schema_version"] = "1.1.0"
    with pytest.raises(ValidationError):
        validate_record(ticket, SCHEMAS / "ticket.schema.json")

    ticket["run_ids"] = ["RUN-20260710-0003"]
    ticket["supplemental_evidence"] = ["provenance/evidence/P002/report.md"]
    validate_record(ticket, SCHEMAS / "ticket.schema.json")
