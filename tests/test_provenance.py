from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from delta_lemmata.provenance import (
    canonical_json_bytes,
    sha256_text,
    validate_record,
    write_record_atomic,
)

ROOT = Path(__file__).resolve().parents[1]


def test_sha256_text_preserves_exact_input() -> None:
    assert sha256_text("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert sha256_text("Oğuz") != sha256_text("Oguz")


def test_canonical_json_is_deterministic_and_utf8() -> None:
    first = canonical_json_bytes({"z": 1, "name": "Oğuz"})
    second = canonical_json_bytes({"name": "Oğuz", "z": 1})
    assert first == second
    assert first == b'{"name":"O\xc4\x9fuz","z":1}'


def test_atomic_write_validates_before_replacing(tmp_path: Path) -> None:
    schema = ROOT / "schemas" / "human-decision.schema.json"
    record = {
        "schema_version": "1.0.0",
        "decision_id": "HD-20260710-9999",
        "decided_at_utc": "2026-07-10T12:00:00Z",
        "ticket_ids": ["P001"],
        "adr_ids": ["ADR-0008"],
        "decision_owner": "Oğuz Koran",
        "decision_owner_type": "human",
        "acceptance_owner": "Oğuz Koran",
        "question_or_choice": "Test decision?",
        "ai_assistance": {"providers": ["openai"], "summary": "Fixture only."},
        "alternatives": [{"option": "A", "disposition": "accepted", "reason": "Fixture."}],
        "accepted_option": "A",
        "rationale": "Schema fixture.",
        "evidence_required": ["Automated test"],
        "status": "accepted",
        "source_quote": None,
        "provenance_notes": "Synthetic test record.",
    }
    target = tmp_path / "decision.json"
    write_record_atomic(target, record, schema)
    assert json.loads(target.read_text(encoding="utf-8")) == record

    invalid = dict(record)
    invalid["decision_owner_type"] = "ai"
    with pytest.raises(ValidationError):
        write_record_atomic(target, invalid, schema)
    assert json.loads(target.read_text(encoding="utf-8")) == record


def test_invalid_schema_record_is_rejected() -> None:
    schema = ROOT / "schemas" / "prompt-event.schema.json"
    with pytest.raises(ValidationError):
        validate_record({"schema_version": "1.0.0"}, schema)
