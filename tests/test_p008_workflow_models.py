from __future__ import annotations

import json
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from delta_lemmata.corpus_models import PurposeId
from delta_lemmata.stylo_contracts import DistanceMeasure
from delta_lemmata.workflow_models import (
    GUIDED_GRID_SHA256,
    PUBLIC_CELL_LIMIT,
    AnalysisScope,
    P008ContractError,
    P008ContractErrorCode,
    ResolvedWorkflowConfigV1,
    WorkflowMode,
    canonical_p008_json,
    export_p008_schema,
    parse_resolved_workflow_config,
    resolve_guided_workflow,
    workflow_config_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "resolved-workflow-config-v1.schema.json"


def _guided(*, unknown: int = 0) -> ResolvedWorkflowConfigV1:
    return resolve_guided_workflow(
        purpose=PurposeId.TEXT_PROXIMITY,
        known_work_count=3,
        unknown_work_count=unknown,
    )


def _payload(record: ResolvedWorkflowConfigV1) -> dict[str, Any]:
    return record.model_dump(mode="json")


def _encoded(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def _expect_error(code: P008ContractErrorCode, action: Callable[[], object]) -> None:
    with pytest.raises(P008ContractError) as captured:
        action()
    assert captured.value.code is code
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


def test_guided_profile_is_exact_ordered_and_not_result_selected() -> None:
    config = _guided()

    assert config.schema_version == "resolved-workflow-config-v1"
    assert config.purpose is PurposeId.TEXT_PROXIMITY
    assert config.mode is WorkflowMode.GUIDED
    assert config.parameter_profile == "guided-grid-v1"
    assert config.analysis_scope is AnalysisScope.TRANSDUCTIVE_EXPLORATORY
    assert config.preprocessing_profile == "delta-surface-words-v1"
    assert config.analysis_unit == "whole_text"
    assert config.seed == 20260713
    assert config.known_work_count == 3
    assert config.unknown_work_count == 0
    assert config.cell_count == 4
    assert config.grid_sha256 == GUIDED_GRID_SHA256
    assert tuple(cell.mfw for cell in config.cells) == (100, 300, 500, 1000)
    assert {cell.culling_percent for cell in config.cells} == {0}
    assert {cell.distance for cell in config.cells} == {DistanceMeasure.CLASSIC_DELTA}
    assert tuple(cell.is_reference for cell in config.cells) == (False, False, True, False)


def test_unknown_scope_is_explicit_and_does_not_change_the_grid() -> None:
    all_known = _guided()
    holdout = _guided(unknown=2)

    assert holdout.analysis_scope is AnalysisScope.UNKNOWN_HOLDOUT
    assert holdout.known_work_count == 3
    assert holdout.unknown_work_count == 2
    assert holdout.cells == all_known.cells
    assert holdout.grid_sha256 == all_known.grid_sha256
    assert workflow_config_sha256(holdout) != workflow_config_sha256(all_known)


def test_canonical_round_trip_and_hash_are_deterministic() -> None:
    config = _guided(unknown=1)
    canonical = canonical_p008_json(config)

    assert parse_resolved_workflow_config(canonical) == config
    assert canonical_p008_json(parse_resolved_workflow_config(canonical)) == canonical
    assert workflow_config_sha256(config) == workflow_config_sha256(config)
    assert len(workflow_config_sha256(config)) == 64
    assert canonical.endswith(b"\n")


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (None, P008ContractErrorCode.PAYLOAD_TYPE),
        (b"", P008ContractErrorCode.PAYLOAD_EMPTY),
        (b"\xff", P008ContractErrorCode.INVALID_UTF8),
        (b"{", P008ContractErrorCode.INVALID_JSON),
        (b'{"schema_version":"x","schema_version":"y"}', P008ContractErrorCode.DUPLICATE_KEY),
        (b'{"value":NaN}', P008ContractErrorCode.NON_FINITE_NUMBER),
        (b'{"value":1e999}', P008ContractErrorCode.NUMBER_OUT_OF_RANGE),
        (b'{"value":"\\ud800"}', P008ContractErrorCode.INVALID_UNICODE),
        (b'{"unexpected":true}', P008ContractErrorCode.SCHEMA_INVALID),
    ],
)
def test_parser_rejects_hostile_or_malformed_payloads(
    payload: Any,
    code: P008ContractErrorCode,
) -> None:
    _expect_error(code, lambda: parse_resolved_workflow_config(payload))


def test_parser_rejects_oversized_payload() -> None:
    _expect_error(
        P008ContractErrorCode.PAYLOAD_TOO_LARGE,
        lambda: parse_resolved_workflow_config(b" " * (64 * 1024 + 1)),
    )


def test_parser_rejects_a_finite_domain_overflowing_json_integer() -> None:
    _expect_error(
        P008ContractErrorCode.NUMBER_OUT_OF_RANGE,
        lambda: parse_resolved_workflow_config(('{"value":' + "9" * 400 + "}").encode("ascii")),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("parameter_profile", "research-grid-v1"),
        ("analysis_unit", "segments"),
        ("seed", 1),
        ("cell_count", 3),
        ("grid_sha256", "f" * 64),
        ("analysis_scope", AnalysisScope.UNKNOWN_HOLDOUT.value),
    ],
)
def test_guided_semantic_mutations_fail_closed(field: str, value: object) -> None:
    payload = _payload(_guided())
    payload[field] = value
    _expect_error(
        P008ContractErrorCode.SCHEMA_INVALID,
        lambda: parse_resolved_workflow_config(_encoded(payload)),
    )


def test_changed_or_reordered_guided_cells_fail_closed() -> None:
    for mutation in ("mfw", "culling_percent", "distance", "is_reference", "reverse"):
        payload = _payload(_guided())
        cells = list(payload["cells"])
        if mutation == "reverse":
            cells.reverse()
        else:
            first = dict(cells[0])
            first[mutation] = {
                "mfw": 200,
                "culling_percent": 50,
                "distance": DistanceMeasure.EDERS_DELTA.value,
                "is_reference": True,
            }[mutation]
            cells[0] = first
        payload["cells"] = cells
        encoded = _encoded(payload)
        _expect_error(
            P008ContractErrorCode.SCHEMA_INVALID,
            partial(parse_resolved_workflow_config, encoded),
        )


def test_research_mode_is_structurally_bounded_but_semantically_locked() -> None:
    payload = _payload(_guided())
    payload["mode"] = WorkflowMode.RESEARCH.value
    payload["parameter_profile"] = "research-grid-v1"
    _expect_error(
        P008ContractErrorCode.SCHEMA_INVALID,
        lambda: parse_resolved_workflow_config(_encoded(payload)),
    )

    payload["parameter_profile"] = "guided-grid-v1"
    _expect_error(
        P008ContractErrorCode.SCHEMA_INVALID,
        lambda: parse_resolved_workflow_config(_encoded(payload)),
    )

    payload["parameter_profile"] = "research-grid-v1"
    payload["cells"] = [payload["cells"][0]] * (PUBLIC_CELL_LIMIT + 1)
    payload["cell_count"] = PUBLIC_CELL_LIMIT + 1
    _expect_error(
        P008ContractErrorCode.SCHEMA_INVALID,
        lambda: parse_resolved_workflow_config(_encoded(payload)),
    )


@pytest.mark.parametrize(
    ("purpose", "known", "unknown"),
    [
        ("bad", 3, 0),
        (PurposeId.TEXT_PROXIMITY, True, 0),
        (PurposeId.TEXT_PROXIMITY, 1, 0),
        (PurposeId.TEXT_PROXIMITY, 50, 1),
        (PurposeId.TEXT_PROXIMITY, 3, -1),
    ],
)
def test_resolver_rejects_invalid_public_requests(
    purpose: Any,
    known: Any,
    unknown: Any,
) -> None:
    _expect_error(
        P008ContractErrorCode.INVALID_REQUEST,
        lambda: resolve_guided_workflow(
            purpose=purpose,
            known_work_count=known,
            unknown_work_count=unknown,
        ),
    )


def test_closed_model_rejects_extra_fields_and_direct_inconsistency() -> None:
    payload = _payload(_guided())
    payload["extra"] = "no"
    with pytest.raises(ValidationError):
        ResolvedWorkflowConfigV1.model_validate(payload)

    payload = _payload(_guided())
    payload["known_work_count"] = 1
    with pytest.raises(ValidationError):
        ResolvedWorkflowConfigV1.model_validate(payload)

    payload = _payload(_guided())
    payload["known_work_count"] = 50
    payload["unknown_work_count"] = 1
    payload["analysis_scope"] = AnalysisScope.UNKNOWN_HOLDOUT.value
    with pytest.raises(ValidationError):
        ResolvedWorkflowConfigV1.model_validate(payload)

    payload = _payload(_guided())
    cells = list(payload["cells"])
    cells[0] = cells[1]
    payload["cells"] = cells
    with pytest.raises(ValidationError):
        ResolvedWorkflowConfigV1.model_validate(payload)


def test_canonical_serializer_rejects_unvalidated_objects() -> None:
    _expect_error(
        P008ContractErrorCode.INVALID_REQUEST,
        lambda: canonical_p008_json(object()),  # type: ignore[arg-type]
    )

    payload = _payload(_guided(unknown=1))
    payload["analysis_scope"] = AnalysisScope.TRANSDUCTIVE_EXPLORATORY.value
    with pytest.raises(ValidationError):
        ResolvedWorkflowConfigV1.model_validate(payload)


def test_checked_in_schema_matches_the_closed_model() -> None:
    expected = export_p008_schema(
        ResolvedWorkflowConfigV1,
        "https://delta.lemmata.app/schemas/resolved-workflow-config-v1.schema.json",
    )
    assert json.loads(SCHEMA.read_text(encoding="utf-8")) == expected
