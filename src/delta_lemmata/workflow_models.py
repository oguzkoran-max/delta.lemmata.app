"""Closed P008 workflow configuration and deterministic public presets."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, model_validator

from delta_lemmata.corpus_models import PurposeId
from delta_lemmata.stylo_contracts import MAX_DOCUMENTS, DistanceMeasure

PUBLIC_CELL_LIMIT = 24
MAX_WORKFLOW_CONFIG_BYTES = 64 * 1024
GUIDED_MFW = (100, 300, 500, 1000)
GUIDED_REFERENCE_MFW = 500
WORKFLOW_SEED = 20260713

_JSON_SCHEMA_DRAFT_2020_12 = "https:" + "//json-schema.org/draft/2020-12/schema"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"

type Sha256 = Annotated[str, Field(pattern=_SHA256_PATTERN)]
type WorkCount = Annotated[StrictInt, Field(ge=0, le=MAX_DOCUMENTS)]
type MfwCount = Annotated[StrictInt, Field(ge=2, le=1000)]
type Percentage = Annotated[StrictInt, Field(ge=0, le=100)]
type CellCount = Annotated[StrictInt, Field(ge=1, le=PUBLIC_CELL_LIMIT)]


class P008Model(BaseModel):
    """Immutable closed-world P008 model."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        hide_input_in_errors=True,
        str_strip_whitespace=False,
    )


class WorkflowMode(StrEnum):
    GUIDED = "guided"
    RESEARCH = "research"


class AnalysisScope(StrEnum):
    TRANSDUCTIVE_EXPLORATORY = "transductive_exploratory"
    UNKNOWN_HOLDOUT = "unknown_holdout"


class ParameterCellV1(P008Model):
    mfw: MfwCount
    culling_percent: Percentage
    distance: DistanceMeasure = Field(strict=False)
    is_reference: bool


def _cells_payload(cells: tuple[ParameterCellV1, ...]) -> bytes:
    return json.dumps(
        [cell.model_dump(mode="json") for cell in cells],
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _cells_sha256(cells: tuple[ParameterCellV1, ...]) -> str:
    return hashlib.sha256(_cells_payload(cells)).hexdigest()


GUIDED_CELLS = tuple(
    ParameterCellV1(
        mfw=mfw,
        culling_percent=0,
        distance=DistanceMeasure.CLASSIC_DELTA,
        is_reference=mfw == GUIDED_REFERENCE_MFW,
    )
    for mfw in GUIDED_MFW
)
GUIDED_GRID_SHA256 = _cells_sha256(GUIDED_CELLS)


class ResolvedWorkflowConfigV1(P008Model):
    schema_version: Literal["resolved-workflow-config-v1"]
    purpose: PurposeId = Field(strict=False)
    mode: WorkflowMode = Field(strict=False)
    parameter_profile: Literal["guided-grid-v1", "research-grid-v1"]
    analysis_scope: AnalysisScope = Field(strict=False)
    preprocessing_profile: Literal["delta-surface-words-v1"]
    analysis_unit: Literal["whole_text"]
    seed: Literal[20260713]
    known_work_count: WorkCount
    unknown_work_count: WorkCount
    cell_count: CellCount
    grid_sha256: Sha256
    cells: tuple[ParameterCellV1, ...] = Field(
        min_length=1,
        max_length=PUBLIC_CELL_LIMIT,
        strict=False,
    )

    @model_validator(mode="after")
    def require_registered_closed_grid(self) -> Self:
        if (
            self.known_work_count < 2
            or self.known_work_count + self.unknown_work_count > MAX_DOCUMENTS
        ):
            raise ValueError("workflow requires two known works within the P006 document limit")
        expected_scope = (
            AnalysisScope.UNKNOWN_HOLDOUT
            if self.unknown_work_count
            else AnalysisScope.TRANSDUCTIVE_EXPLORATORY
        )
        if self.analysis_scope is not expected_scope:
            raise ValueError("analysis scope must match the declared unknown-work count")
        if self.cell_count != len(self.cells):
            raise ValueError("cell count must match the resolved grid")
        cell_keys = tuple((cell.mfw, cell.culling_percent, cell.distance) for cell in self.cells)
        if len(cell_keys) != len(set(cell_keys)):
            raise ValueError("workflow cells must be unique")
        if sum(cell.is_reference for cell in self.cells) != 1:
            raise ValueError("the resolved grid requires exactly one fixed reference")
        if self.grid_sha256 != _cells_sha256(self.cells):
            raise ValueError("grid digest must bind the exact ordered cells")
        if self.mode is WorkflowMode.GUIDED:
            if self.parameter_profile != "guided-grid-v1" or self.cells != GUIDED_CELLS:
                raise ValueError("Guided Mode must use the complete guided-grid-v1 preset")
        else:
            if self.parameter_profile != "research-grid-v1":
                raise ValueError("Research Mode requires the research-grid-v1 profile")
            raise ValueError("Research Mode remains locked until its exact preset is accepted")
        return self


class P008ContractErrorCode(StrEnum):
    INVALID_REQUEST = "P008_CONTRACT_INVALID_REQUEST"
    PAYLOAD_TYPE = "P008_CONTRACT_PAYLOAD_TYPE"
    PAYLOAD_EMPTY = "P008_CONTRACT_PAYLOAD_EMPTY"
    PAYLOAD_TOO_LARGE = "P008_CONTRACT_PAYLOAD_TOO_LARGE"
    INVALID_UTF8 = "P008_CONTRACT_INVALID_UTF8"
    INVALID_JSON = "P008_CONTRACT_INVALID_JSON"
    DUPLICATE_KEY = "P008_CONTRACT_DUPLICATE_KEY"
    NON_FINITE_NUMBER = "P008_CONTRACT_NON_FINITE_NUMBER"
    NUMBER_OUT_OF_RANGE = "P008_CONTRACT_NUMBER_OUT_OF_RANGE"
    INVALID_UNICODE = "P008_CONTRACT_INVALID_UNICODE"
    SCHEMA_INVALID = "P008_CONTRACT_SCHEMA_INVALID"


class P008ContractError(ValueError):
    """Content-free workflow configuration rejection."""

    def __init__(self, code: P008ContractErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class _DuplicateKey(ValueError):
    pass


class _NonFinite(ValueError):
    pass


class _NumberOutOfRange(ValueError):
    pass


def _error(code: P008ContractErrorCode) -> P008ContractError:
    error = P008ContractError(code)
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True
    return error


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise _NonFinite


def _check_json_tree(value: Any) -> None:
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, (int, float)) and not isinstance(current, bool):
            if isinstance(current, float) and not math.isfinite(current):
                raise _NumberOutOfRange
            if abs(current) > sys.float_info.max:
                raise _NumberOutOfRange
        if isinstance(current, str):
            if any(0xD800 <= ord(character) <= 0xDFFF for character in current):
                raise UnicodeError
        elif isinstance(current, list):
            pending.extend(current)
        elif isinstance(current, dict):
            pending.extend(current.keys())
            pending.extend(current.values())


def parse_resolved_workflow_config(payload: bytes) -> ResolvedWorkflowConfigV1:
    """Parse one closed P008 configuration exactly once."""

    if not isinstance(payload, bytes):
        raise _error(P008ContractErrorCode.PAYLOAD_TYPE)
    if not payload:
        raise _error(P008ContractErrorCode.PAYLOAD_EMPTY)
    if len(payload) > MAX_WORKFLOW_CONFIG_BYTES:
        raise _error(P008ContractErrorCode.PAYLOAD_TOO_LARGE)
    decode_rejection: P008ContractError | None = None
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        decode_rejection = _error(P008ContractErrorCode.INVALID_UTF8)
        text = ""
    if decode_rejection is not None:
        raise decode_rejection
    parse_rejection: P008ContractError | None = None
    try:
        decoded = json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
        _check_json_tree(decoded)
    except _DuplicateKey:
        parse_rejection = _error(P008ContractErrorCode.DUPLICATE_KEY)
    except _NonFinite:
        parse_rejection = _error(P008ContractErrorCode.NON_FINITE_NUMBER)
    except _NumberOutOfRange:
        parse_rejection = _error(P008ContractErrorCode.NUMBER_OUT_OF_RANGE)
    except UnicodeError:
        parse_rejection = _error(P008ContractErrorCode.INVALID_UNICODE)
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
        parse_rejection = _error(P008ContractErrorCode.INVALID_JSON)
    if parse_rejection is not None:
        raise parse_rejection
    validation_rejection: P008ContractError | None = None
    try:
        resolved = ResolvedWorkflowConfigV1.model_validate(decoded)
    except (OverflowError, ValidationError):
        validation_rejection = _error(P008ContractErrorCode.SCHEMA_INVALID)
        resolved = None
    if validation_rejection is not None:
        raise validation_rejection
    if resolved is None:  # pragma: no cover - paired validation invariant
        raise _error(P008ContractErrorCode.SCHEMA_INVALID)
    return resolved


def canonical_p008_json(record: ResolvedWorkflowConfigV1) -> bytes:
    """Serialize one validated P008 record as deterministic UTF-8 JSON."""

    if not isinstance(record, ResolvedWorkflowConfigV1):
        raise _error(P008ContractErrorCode.INVALID_REQUEST)
    return (
        json.dumps(
            record.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def workflow_config_sha256(record: ResolvedWorkflowConfigV1) -> str:
    return hashlib.sha256(canonical_p008_json(record)).hexdigest()


def resolve_guided_workflow(
    *,
    purpose: PurposeId,
    known_work_count: int,
    unknown_work_count: int,
) -> ResolvedWorkflowConfigV1:
    """Resolve the single accepted public-alpha Guided profile."""

    if (
        not isinstance(purpose, PurposeId)
        or isinstance(known_work_count, bool)
        or not isinstance(known_work_count, int)
        or isinstance(unknown_work_count, bool)
        or not isinstance(unknown_work_count, int)
        or known_work_count < 2
        or unknown_work_count < 0
        or known_work_count + unknown_work_count > MAX_DOCUMENTS
    ):
        raise _error(P008ContractErrorCode.INVALID_REQUEST)
    scope = (
        AnalysisScope.UNKNOWN_HOLDOUT
        if unknown_work_count
        else AnalysisScope.TRANSDUCTIVE_EXPLORATORY
    )
    return ResolvedWorkflowConfigV1(
        schema_version="resolved-workflow-config-v1",
        purpose=purpose,
        mode=WorkflowMode.GUIDED,
        parameter_profile="guided-grid-v1",
        analysis_scope=scope,
        preprocessing_profile="delta-surface-words-v1",
        analysis_unit="whole_text",
        seed=20260713,
        known_work_count=known_work_count,
        unknown_work_count=unknown_work_count,
        cell_count=len(GUIDED_CELLS),
        grid_sha256=GUIDED_GRID_SHA256,
        cells=GUIDED_CELLS,
    )


def export_p008_schema(model: type[BaseModel], schema_id: str) -> dict[str, Any]:
    return {
        "$schema": _JSON_SCHEMA_DRAFT_2020_12,
        "$id": schema_id,
        **model.model_json_schema(mode="validation"),
    }


__all__ = [
    "GUIDED_CELLS",
    "GUIDED_GRID_SHA256",
    "GUIDED_MFW",
    "GUIDED_REFERENCE_MFW",
    "PUBLIC_CELL_LIMIT",
    "AnalysisScope",
    "P008ContractError",
    "P008ContractErrorCode",
    "ParameterCellV1",
    "ResolvedWorkflowConfigV1",
    "WorkflowMode",
    "canonical_p008_json",
    "export_p008_schema",
    "parse_resolved_workflow_config",
    "resolve_guided_workflow",
    "workflow_config_sha256",
]
