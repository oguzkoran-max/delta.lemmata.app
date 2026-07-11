from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import ValidationError

from delta_lemmata.corpus import (
    AssetRightsRecord,
    CorpusInventory,
    IssueCode,
    MetadataCsvFieldDictionary,
    ValidationReport,
    VocabularyProfile,
    export_json_schema,
    validate_inventory,
)
from delta_lemmata.provenance import load_schema, validate_record

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
P004_FIXTURES = ROOT / "tests" / "fixtures" / "p004"


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
        "asset-rights-v2",
        "corpus-inventory",
        "corpus-metadata-field-dictionary",
        "corpus-validation-report",
        "corpus-vocabularies",
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
        "schema_version": "2.0.0",
        "asset_id": "asset_fixture",
        "source_id": "fixture-source",
        "asset_type": "transcription",
        "rights_status": "unknown",
        "license": None,
        "permissions": {
            "upload": "unknown",
            "analysis": "unknown",
            "export": "prohibited",
            "public_redistribution": "permitted",
        },
        "evidence": [],
        "jurisdiction": None,
        "assessed_by": "Test suite",
        "assessed_at_utc": "2026-07-10T12:00:00Z",
        "notes": "Synthetic record only.",
    }
    with pytest.raises(ValidationError):
        validate_record(record, SCHEMAS / "asset-rights-v2.schema.json")

    permitted = copy.deepcopy(record)
    permitted["rights_status"] = "verified_open"
    permitted["license"] = "CC0-1.0"
    permitted["permissions"] = {
        "upload": "permitted",
        "analysis": "permitted",
        "export": "permitted",
        "public_redistribution": "permitted",
    }
    permitted["evidence"] = [{"evidence_type": "url", "value": "https://example.org/rights"}]
    permitted["jurisdiction"] = "Italy"
    validate_record(permitted, SCHEMAS / "asset-rights-v2.schema.json")

    no_evidence = copy.deepcopy(permitted)
    no_evidence["evidence"] = []
    with pytest.raises(ValidationError):
        validate_record(no_evidence, SCHEMAS / "asset-rights-v2.schema.json")

    non_utc = copy.deepcopy(permitted)
    non_utc["assessed_at_utc"] = "2026-07-10T15:00:00+03:00"
    with pytest.raises(ValidationError):
        validate_record(non_utc, SCHEMAS / "asset-rights-v2.schema.json")

    unsupported_open_claim = copy.deepcopy(record)
    unsupported_open_claim["rights_status"] = "verified_open"
    unsupported_open_claim["permissions"]["public_redistribution"] = "prohibited"
    with pytest.raises(ValidationError):
        validate_record(unsupported_open_claim, SCHEMAS / "asset-rights-v2.schema.json")

    malformed_evidence_url = copy.deepcopy(permitted)
    malformed_evidence_url["evidence"][0]["value"] = "https://"
    with pytest.raises(ValidationError):
        validate_record(malformed_evidence_url, SCHEMAS / "asset-rights-v2.schema.json")

    statement_only = copy.deepcopy(permitted)
    statement_only["evidence"] = [{"evidence_type": "statement", "value": "Open claim"}]
    with pytest.raises(ValidationError):
        validate_record(statement_only, SCHEMAS / "asset-rights-v2.schema.json")

    no_jurisdiction = copy.deepcopy(permitted)
    no_jurisdiction["jurisdiction"] = None
    with pytest.raises(ValidationError):
        validate_record(no_jurisdiction, SCHEMAS / "asset-rights-v2.schema.json")


def test_asset_rights_v1_remains_valid_only_against_its_immutable_schema() -> None:
    record: dict[str, Any] = {
        "schema_version": "1.0.0",
        "asset_id": "ASSET-fixture",
        "source_id": "fixture-source",
        "title": "Synthetic legacy fixture",
        "asset_type": "transcription",
        "rights_status": "analysis-only",
        "license": None,
        "permissions": {
            "upload": True,
            "analysis": True,
            "export": False,
            "public_redistribution": False,
        },
        "evidence_urls": [],
        "jurisdiction": None,
        "assessed_by": "Test suite",
        "assessed_at_utc": "2026-07-10T12:00:00Z",
        "notes": "Legacy fixture",
    }
    validate_record(record, SCHEMAS / "asset-rights.schema.json")
    with pytest.raises(ValidationError):
        validate_record(record, SCHEMAS / "asset-rights-v2.schema.json")


@pytest.mark.parametrize(
    ("schema_name", "model"),
    [
        ("asset-rights-v2", AssetRightsRecord),
        ("corpus-inventory", CorpusInventory),
        ("corpus-metadata-field-dictionary", MetadataCsvFieldDictionary),
        ("corpus-validation-report", ValidationReport),
        ("corpus-vocabularies", VocabularyProfile),
    ],
)
def test_p004_checked_in_schemas_match_the_canonical_models(
    schema_name: str,
    model: type[Any],
) -> None:
    schema_id = f"https://delta.lemmata.app/schemas/{schema_name}.schema.json"
    assert read_json(SCHEMAS / f"{schema_name}.schema.json") == export_json_schema(model, schema_id)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data["columns"][1].update(position=3),
        lambda data: data["columns"][1].update(name=data["columns"][0]["name"]),
    ],
)
def test_field_dictionary_schema_enforces_exact_ordered_v1_columns(mutation: object) -> None:
    dictionary = read_json(
        ROOT / "src" / "delta_lemmata" / "data" / "corpus-metadata-fields-v1.json"
    )
    validate_record(dictionary, SCHEMAS / "corpus-metadata-field-dictionary.schema.json")
    assert callable(mutation)
    mutation(dictionary)
    with pytest.raises(ValidationError):
        validate_record(dictionary, SCHEMAS / "corpus-metadata-field-dictionary.schema.json")


def test_p004_inventory_schema_preserves_date_modes_and_online_source_dates() -> None:
    record = read_json(P004_FIXTURES / "inventory-valid-text-proximity.json")
    validate_record(record, SCHEMAS / "corpus-inventory.schema.json")

    unknown_with_year = copy.deepcopy(record)
    unknown_with_year["works"][0]["first_publication"] = {
        "mode": "unknown",
        "start_year": 1883,
    }
    with pytest.raises(ValidationError):
        validate_record(unknown_with_year, SCHEMAS / "corpus-inventory.schema.json")

    exact_without_year = copy.deepcopy(record)
    exact_without_year["works"][0]["first_publication"] = {"mode": "exact"}
    with pytest.raises(ValidationError):
        validate_record(exact_without_year, SCHEMAS / "corpus-inventory.schema.json")

    reversed_range = copy.deepcopy(record)
    reversed_range["works"][0]["first_publication"] = {
        "mode": "range",
        "start_year": 1884,
        "end_year": 1883,
    }
    validate_record(reversed_range, SCHEMAS / "corpus-inventory.schema.json")
    semantic_report = validate_inventory(CorpusInventory.model_validate(reversed_range))
    assert semantic_report.blocked is True
    assert IssueCode.DATE_RANGE_REVERSED in {issue.code for issue in semantic_report.issues}

    undated_online_source = copy.deepcopy(record)
    source = undated_online_source["sources"][0]
    source.pop("bibliographic_citation")
    source["source_url"] = "https://example.org/text"
    with pytest.raises(ValidationError):
        validate_record(undated_online_source, SCHEMAS / "corpus-inventory.schema.json")

    local_file_source = copy.deepcopy(record)
    source = local_file_source["sources"][0]
    source.pop("bibliographic_citation")
    source["source_url"] = "file:///tmp/text.txt"
    source["accessed_on"] = "2026-07-12"
    with pytest.raises(ValidationError):
        validate_record(local_file_source, SCHEMAS / "corpus-inventory.schema.json")

    duplicate_rights_dependency = copy.deepcopy(record)
    asset = duplicate_rights_dependency["assets"][0]
    asset["rights_asset_ids"] = [asset["asset_id"], asset["asset_id"]]
    with pytest.raises(ValidationError):
        validate_record(duplicate_rights_dependency, SCHEMAS / "corpus-inventory.schema.json")

    unreviewed_rights_chain = copy.deepcopy(record)
    unreviewed_rights_chain["assets"][0].pop("rights_chain_confirmed")
    with pytest.raises(ValidationError):
        validate_record(unreviewed_rights_chain, SCHEMAS / "corpus-inventory.schema.json")


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
    ticket.pop("run_ids", None)
    ticket.pop("supplemental_evidence", None)
    with pytest.raises(ValidationError):
        validate_record(ticket, SCHEMAS / "ticket.schema.json")

    ticket["run_ids"] = ["RUN-20260710-0003"]
    ticket["supplemental_evidence"] = ["provenance/evidence/P002/report.md"]
    validate_record(ticket, SCHEMAS / "ticket.schema.json")


def test_completed_ticket_schema_1_1_requires_populated_closure_evidence() -> None:
    ticket = read_json(ROOT / "provenance" / "tickets" / "P002.json")
    for field in (
        "decision_ids",
        "prompt_event_ids",
        "commit_ids",
        "run_ids",
        "supplemental_evidence",
        "changed_files",
        "commands",
    ):
        candidate = copy.deepcopy(ticket)
        candidate[field] = []
        with pytest.raises(ValidationError):
            validate_record(candidate, SCHEMAS / "ticket.schema.json")

    pending = copy.deepcopy(ticket)
    pending["acceptance"][0]["status"] = "pending"
    with pytest.raises(ValidationError):
        validate_record(pending, SCHEMAS / "ticket.schema.json")

    no_evidence = copy.deepcopy(ticket)
    no_evidence["acceptance"][0]["evidence"] = []
    with pytest.raises(ValidationError):
        validate_record(no_evidence, SCHEMAS / "ticket.schema.json")

    blocked = copy.deepcopy(ticket)
    blocked["blockers"] = ["Unresolved closure defect"]
    with pytest.raises(ValidationError):
        validate_record(blocked, SCHEMAS / "ticket.schema.json")
