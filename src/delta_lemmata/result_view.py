"""Strict P009 result projection and matrix-derived public views."""

from __future__ import annotations

import hashlib
import json
import math
import sys
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

import numpy as np
import numpy.typing as npt
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from delta_lemmata.corpus_models import PurposeId
from delta_lemmata.stylo_contracts import (
    MAX_DOCUMENTS,
    STRUCTURAL_TOLERANCE,
    AnalysisOutcome,
    CellComplete,
    CellErrorCode,
    CellFailed,
    CellNotEnoughFeatures,
    DistanceMeasure,
    DocumentRole,
    FiniteNumber,
    WorkerResultV1,
)
from delta_lemmata.workflow_models import (
    GUIDED_MFW,
    GUIDED_REFERENCE_MFW,
    AnalysisScope,
    ResolvedWorkflowConfigV1,
    workflow_config_sha256,
)

MAX_RESULT_VIEW_BYTES = 4 * 1024 * 1024
RESULT_VIEW_COMPONENT: Literal[
    "5a6b1a66f34ffa5cb516349bc4f2fe62083a8c4803fa23b2793f57a5ece0621a"
] = "5a6b1a66f34ffa5cb516349bc4f2fe62083a8c4803fa23b2793f57a5ece0621a"
RESULT_VIEW_PROFILE: Literal["relative-proximity-guardrails-v1"] = (
    "relative-proximity-guardrails-v1"
)
MDS_METHOD: Literal["classical-mds-v1"] = "classical-mds-v1"

_JSON_SCHEMA_DRAFT_2020_12 = "https:" + "//json-schema.org/draft/2020-12/schema"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_DOCUMENT_KEY_PATTERN = r"^D(?:0[1-9]|[1-4][0-9]|50)$"

type Sha256 = Annotated[str, Field(pattern=_SHA256_PATTERN)]
type DocumentKey = Annotated[str, Field(pattern=_DOCUMENT_KEY_PATTERN)]
type DisplayTitle = Annotated[str, Field(min_length=1, max_length=200)]
type MfwCount = Annotated[StrictInt, Field(ge=2, le=1000)]
type Percentage = Annotated[StrictInt, Field(ge=0, le=100)]
type PublicCellError = Literal[
    "not_enough_features",
    "fit_unavailable",
    "distance_calculation_failed",
]


class P009Model(BaseModel):
    """Immutable closed-world public result model."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        hide_input_in_errors=True,
        str_strip_whitespace=False,
    )


class ResultCellStatus(StrEnum):
    COMPLETE = "complete"
    NOT_ENOUGH_FEATURES = "not_enough_features"
    FAILED = "failed"


class ResultDocumentV1(P009Model):
    key: DocumentKey
    title: DisplayTitle
    role: DocumentRole = Field(strict=False)

    @field_validator("title")
    @classmethod
    def require_safe_title(cls, value: str) -> str:
        if (
            value != value.strip()
            or unicodedata.normalize("NFC", value) != value
            or len(value.encode("utf-8")) > 800
            or any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in value)
        ):
            raise ValueError("title must be a bounded NFC display string")
        return value


class ResultMatrixV1(P009Model):
    document_keys: tuple[DocumentKey, ...] = Field(
        min_length=2,
        max_length=MAX_DOCUMENTS,
        strict=False,
    )
    values: tuple[tuple[FiniteNumber, ...], ...] = Field(
        min_length=2,
        max_length=MAX_DOCUMENTS,
        strict=False,
    )

    @field_validator("values", mode="before")
    @classmethod
    def normalize_json_rows(cls, value: Any) -> Any:
        if not isinstance(value, (list, tuple)):
            return value
        return tuple(tuple(row) if isinstance(row, (list, tuple)) else row for row in value)

    @model_validator(mode="after")
    def require_distance_matrix(self) -> Self:
        size = len(self.document_keys)
        if len(set(self.document_keys)) != size or len(self.values) != size:
            raise ValueError("result matrix identifiers and rows must align")
        for row_index, row in enumerate(self.values):
            if len(row) != size:
                raise ValueError("result matrix must be square")
            for column_index, value in enumerate(row):
                if value < 0:
                    raise ValueError("result distances must be non-negative")
                if row_index == column_index and abs(value) > STRUCTURAL_TOLERANCE:
                    raise ValueError("result distance diagonal must be zero")
                if abs(value - self.values[column_index][row_index]) > STRUCTURAL_TOLERANCE:
                    raise ValueError("result distance matrix must be symmetric")
        return self


class ResultCellV1(P009Model):
    mfw: MfwCount
    culling_percent: Percentage
    distance: Literal[DistanceMeasure.CLASSIC_DELTA]
    is_reference: bool
    status: ResultCellStatus = Field(strict=False)
    error_code: PublicCellError | None
    matrix: ResultMatrixV1 | None

    @model_validator(mode="after")
    def require_status_payload(self) -> Self:
        if self.status is ResultCellStatus.COMPLETE:
            if self.matrix is None or self.error_code is not None:
                raise ValueError("complete cell requires only a matrix")
        elif self.matrix is not None or self.error_code is None:
            raise ValueError("non-complete cell requires only a public error code")
        if self.is_reference != (self.mfw == GUIDED_REFERENCE_MFW):
            raise ValueError("reference marker must remain fixed at 500 MFW")
        return self


class InterpretationBoundariesV1(P009Model):
    profile: Literal["relative-proximity-guardrails-v1"]
    proximity: Literal[
        "Distances show relative proximity only within this corpus and parameter cell."
    ]
    nearest_neighbour: Literal[
        "A nearest neighbour is not an author identification or evidence of influence."
    ]
    mds: Literal[
        "MDS axes have no intrinsic literary meaning; the map is a two-dimensional approximation."
    ]


BOUNDARIES = InterpretationBoundariesV1(
    profile=RESULT_VIEW_PROFILE,
    proximity="Distances show relative proximity only within this corpus and parameter cell.",
    nearest_neighbour=(
        "A nearest neighbour is not an author identification or evidence of influence."
    ),
    mds=(
        "MDS axes have no intrinsic literary meaning; the map is a two-dimensional approximation."
    ),
)


class ResultViewV1(P009Model):
    schema_version: Literal["result-view-v1"]
    purpose: PurposeId = Field(strict=False)
    analysis_scope: AnalysisScope = Field(strict=False)
    parameter_profile: Literal["guided-grid-v1"]
    workflow_config_sha256: Sha256
    source_result_sha256: Sha256
    source_result_outcome: Literal["complete", "partial"]
    analysis_unit: Literal["whole_text"]
    distance_measure: Literal[DistanceMeasure.CLASSIC_DELTA]
    reference_mfw: Literal[500]
    visualization_method: Literal["classical-mds-v1"]
    documents: tuple[ResultDocumentV1, ...] = Field(
        min_length=2,
        max_length=MAX_DOCUMENTS,
        strict=False,
    )
    cells: tuple[ResultCellV1, ...] = Field(min_length=4, max_length=4, strict=False)
    interpretation: InterpretationBoundariesV1

    @model_validator(mode="after")
    def require_closed_guided_view(self) -> Self:
        keys = tuple(document.key for document in self.documents)
        expected_keys = tuple(f"D{index:02d}" for index in range(1, len(keys) + 1))
        if keys != expected_keys:
            raise ValueError("public document keys must be sequential")
        if tuple(cell.mfw for cell in self.cells) != GUIDED_MFW:
            raise ValueError("result view must retain the complete Guided cell order")
        if tuple(cell.culling_percent for cell in self.cells) != (0, 0, 0, 0):
            raise ValueError("result view must retain the Guided culling profile")
        if sum(cell.is_reference for cell in self.cells) != 1:
            raise ValueError("result view requires one fixed reference")
        for cell in self.cells:
            if cell.matrix is not None and cell.matrix.document_keys != keys:
                raise ValueError("every complete matrix must use the public document order")
        complete = sum(cell.status is ResultCellStatus.COMPLETE for cell in self.cells)
        expected_outcome = "complete" if complete == len(self.cells) else "partial"
        if complete == 0 or self.source_result_outcome != expected_outcome:
            raise ValueError("result outcome must match visible cell completeness")
        known = sum(document.role is DocumentRole.KNOWN for document in self.documents)
        unknown = sum(document.role is DocumentRole.UNKNOWN for document in self.documents)
        expected_scope = (
            AnalysisScope.UNKNOWN_HOLDOUT if unknown else AnalysisScope.TRANSDUCTIVE_EXPLORATORY
        )
        if known < 2 or self.analysis_scope is not expected_scope:
            raise ValueError("result scope must match public document roles")
        return self


@dataclass(frozen=True, slots=True)
class ResultDocumentDescriptor:
    document_id: str
    title: str
    role: DocumentRole


@dataclass(frozen=True, slots=True)
class NearestNeighbourRow:
    document_key: str
    neighbour_key: str
    distance: float
    tie_count: int


@dataclass(frozen=True, slots=True)
class MdsPoint:
    document_key: str
    x: float
    y: float


class P009ContractErrorCode(StrEnum):
    INVALID_REQUEST = "P009_CONTRACT_INVALID_REQUEST"
    BINDING_MISMATCH = "P009_CONTRACT_BINDING_MISMATCH"
    PAYLOAD_TYPE = "P009_CONTRACT_PAYLOAD_TYPE"
    PAYLOAD_EMPTY = "P009_CONTRACT_PAYLOAD_EMPTY"
    PAYLOAD_TOO_LARGE = "P009_CONTRACT_PAYLOAD_TOO_LARGE"
    INVALID_UTF8 = "P009_CONTRACT_INVALID_UTF8"
    INVALID_JSON = "P009_CONTRACT_INVALID_JSON"
    DUPLICATE_KEY = "P009_CONTRACT_DUPLICATE_KEY"
    NON_FINITE_NUMBER = "P009_CONTRACT_NON_FINITE_NUMBER"
    NUMBER_OUT_OF_RANGE = "P009_CONTRACT_NUMBER_OUT_OF_RANGE"
    INVALID_UNICODE = "P009_CONTRACT_INVALID_UNICODE"
    SCHEMA_INVALID = "P009_CONTRACT_SCHEMA_INVALID"


class P009ContractError(ValueError):
    """Content-free P009 projection or parser rejection."""

    def __init__(self, code: P009ContractErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class _DuplicateKey(ValueError):
    pass


class _NonFinite(ValueError):
    pass


class _NumberOutOfRange(ValueError):
    pass


def _error(code: P009ContractErrorCode) -> P009ContractError:
    error = P009ContractError(code)
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


def parse_result_view(payload: bytes) -> ResultViewV1:
    """Parse one closed P009 result view exactly once."""

    if not isinstance(payload, bytes):
        raise _error(P009ContractErrorCode.PAYLOAD_TYPE)
    if not payload:
        raise _error(P009ContractErrorCode.PAYLOAD_EMPTY)
    if len(payload) > MAX_RESULT_VIEW_BYTES:
        raise _error(P009ContractErrorCode.PAYLOAD_TOO_LARGE)
    decode_rejection: P009ContractError | None = None
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        decode_rejection = _error(P009ContractErrorCode.INVALID_UTF8)
        text = ""
    if decode_rejection is not None:
        raise decode_rejection
    parse_rejection: P009ContractError | None = None
    try:
        decoded = json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
        _check_json_tree(decoded)
    except _DuplicateKey:
        parse_rejection = _error(P009ContractErrorCode.DUPLICATE_KEY)
    except _NonFinite:
        parse_rejection = _error(P009ContractErrorCode.NON_FINITE_NUMBER)
    except _NumberOutOfRange:
        parse_rejection = _error(P009ContractErrorCode.NUMBER_OUT_OF_RANGE)
    except UnicodeError:
        parse_rejection = _error(P009ContractErrorCode.INVALID_UNICODE)
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
        parse_rejection = _error(P009ContractErrorCode.INVALID_JSON)
    if parse_rejection is not None:
        raise parse_rejection
    validation_rejection: P009ContractError | None = None
    try:
        result = ResultViewV1.model_validate(decoded)
    except (OverflowError, ValidationError):
        validation_rejection = _error(P009ContractErrorCode.SCHEMA_INVALID)
        result = None
    if validation_rejection is not None:
        raise validation_rejection
    if result is None:  # pragma: no cover - paired validation invariant
        raise _error(P009ContractErrorCode.SCHEMA_INVALID)
    return result


def canonical_result_view(record: ResultViewV1) -> bytes:
    """Serialize one validated result view as deterministic UTF-8 JSON."""

    if not isinstance(record, ResultViewV1):
        raise _error(P009ContractErrorCode.INVALID_REQUEST)
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


def result_view_sha256(record: ResultViewV1) -> str:
    return hashlib.sha256(canonical_result_view(record)).hexdigest()


def project_result_view(
    *,
    config: ResolvedWorkflowConfigV1,
    result: WorkerResultV1,
    source_result_sha256: str,
    documents: tuple[ResultDocumentDescriptor, ...],
) -> ResultViewV1:
    """Bind one validated P006 result to a bounded public P009 view."""

    if (
        not isinstance(config, ResolvedWorkflowConfigV1)
        or not isinstance(result, WorkerResultV1)
        or not isinstance(source_result_sha256, str)
        or len(source_result_sha256) != 64
        or any(character not in "0123456789abcdef" for character in source_result_sha256)
        or not isinstance(documents, tuple)
    ):
        raise _error(P009ContractErrorCode.INVALID_REQUEST)
    if result.outcome not in {AnalysisOutcome.COMPLETE, AnalysisOutcome.PARTIAL}:
        raise _error(P009ContractErrorCode.BINDING_MISMATCH)
    if any(not isinstance(document, ResultDocumentDescriptor) for document in documents):
        raise _error(P009ContractErrorCode.BINDING_MISMATCH)
    fits = {fit.fit_id: fit for fit in result.fits}
    descriptor_ids = tuple(document.document_id for document in documents)
    if (
        len(documents) != config.known_work_count + config.unknown_work_count
        or len(descriptor_ids) != len(set(descriptor_ids))
        or tuple(
            document.document_id for document in documents if document.role is DocumentRole.KNOWN
        )
        != result.fitting_basis.known_document_ids
    ):
        raise _error(P009ContractErrorCode.BINDING_MISMATCH)
    public_documents: list[ResultDocumentV1] = []
    descriptor_rejection: P009ContractError | None = None
    try:
        for index, descriptor in enumerate(documents, start=1):
            public_documents.append(
                ResultDocumentV1(
                    key=f"D{index:02d}",
                    title=descriptor.title,
                    role=descriptor.role,
                )
            )
    except (TypeError, ValueError, ValidationError):
        descriptor_rejection = _error(P009ContractErrorCode.BINDING_MISMATCH)
    if descriptor_rejection is not None:
        raise descriptor_rejection
    public_keys = tuple(document.key for document in public_documents)
    public_cells: list[ResultCellV1] = []
    binding_rejection: P009ContractError | None = None
    projected: ResultViewV1 | None = None
    try:
        if len(result.cells) != len(config.cells):
            raise ValueError
        for configured, cell in zip(config.cells, result.cells, strict=True):
            fit = fits[cell.fit_id]
            if (fit.mfw, fit.culling_percent, cell.distance) != (
                configured.mfw,
                configured.culling_percent,
                configured.distance,
            ):
                raise ValueError
            if isinstance(cell, CellComplete):
                if cell.matrix.document_ids != descriptor_ids:
                    raise ValueError
                status = ResultCellStatus.COMPLETE
                error_code: PublicCellError | None = None
                matrix = ResultMatrixV1(
                    document_keys=public_keys,
                    values=cell.matrix.values,
                )
            elif isinstance(cell, CellNotEnoughFeatures):
                status = ResultCellStatus.NOT_ENOUGH_FEATURES
                error_code = "not_enough_features"
                matrix = None
            elif isinstance(cell, CellFailed):
                status = ResultCellStatus.FAILED
                error_code = (
                    "fit_unavailable"
                    if cell.error_code is CellErrorCode.FIT_UNAVAILABLE
                    else "distance_calculation_failed"
                )
                matrix = None
            else:  # pragma: no cover - closed P006 union
                raise ValueError
            public_cells.append(
                ResultCellV1(
                    mfw=configured.mfw,
                    culling_percent=configured.culling_percent,
                    distance=DistanceMeasure.CLASSIC_DELTA,
                    is_reference=configured.is_reference,
                    status=status,
                    error_code=error_code,
                    matrix=matrix,
                )
            )
        outcome: Literal["complete", "partial"] = (
            "complete" if result.outcome is AnalysisOutcome.COMPLETE else "partial"
        )
        projected = ResultViewV1(
            schema_version="result-view-v1",
            purpose=config.purpose,
            analysis_scope=config.analysis_scope,
            parameter_profile="guided-grid-v1",
            workflow_config_sha256=workflow_config_sha256(config),
            source_result_sha256=source_result_sha256,
            source_result_outcome=outcome,
            analysis_unit="whole_text",
            distance_measure=DistanceMeasure.CLASSIC_DELTA,
            reference_mfw=500,
            visualization_method=MDS_METHOD,
            documents=tuple(public_documents),
            cells=tuple(public_cells),
            interpretation=BOUNDARIES,
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        binding_rejection = _error(P009ContractErrorCode.BINDING_MISMATCH)
    if binding_rejection is not None:
        raise binding_rejection
    if projected is None:  # pragma: no cover - paired projection invariant
        raise _error(P009ContractErrorCode.BINDING_MISMATCH)
    return projected


def nearest_neighbours(cell: ResultCellV1) -> tuple[NearestNeighbourRow, ...]:
    """Return every exact minimum-distance tie for each document."""

    if not isinstance(cell, ResultCellV1) or cell.matrix is None:
        raise _error(P009ContractErrorCode.INVALID_REQUEST)
    rows: list[NearestNeighbourRow] = []
    matrix = cell.matrix
    for row_index, document_key in enumerate(matrix.document_keys):
        candidates = tuple(
            (column_index, value)
            for column_index, value in enumerate(matrix.values[row_index])
            if column_index != row_index
        )
        minimum = min(value for _, value in candidates)
        tied = tuple(
            (index, value)
            for index, value in candidates
            if abs(value - minimum) <= STRUCTURAL_TOLERANCE
        )
        for neighbour_index, distance in tied:
            rows.append(
                NearestNeighbourRow(
                    document_key=document_key,
                    neighbour_key=matrix.document_keys[neighbour_index],
                    distance=float(distance),
                    tie_count=len(tied),
                )
            )
    return tuple(rows)


def _orient_coordinates(coordinates: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    if coordinates.shape[1] == 0:
        return np.zeros((coordinates.shape[0], 2), dtype=np.float64)
    oriented = coordinates.copy()
    for axis in range(oriented.shape[1]):
        column = oriented[:, axis]
        pivot = int(np.argmax(np.abs(column)))
        if column[pivot] < 0:
            oriented[:, axis] *= -1
    if oriented.shape[1] == 1:
        oriented = np.column_stack((oriented[:, 0], np.zeros(oriented.shape[0])))
    return np.asarray(oriented[:, :2], dtype=np.float64)


def classical_mds(cell: ResultCellV1) -> tuple[MdsPoint, ...]:
    """Derive one deterministic two-dimensional classical MDS projection."""

    if not isinstance(cell, ResultCellV1) or cell.matrix is None:
        raise _error(P009ContractErrorCode.INVALID_REQUEST)
    distances = np.asarray(cell.matrix.values, dtype=np.float64)
    size = distances.shape[0]
    centering = np.eye(size, dtype=np.float64) - np.full((size, size), 1.0 / size)
    gram = -0.5 * centering @ np.square(distances) @ centering
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1]
    positive = tuple(index for index in order if eigenvalues[index] > STRUCTURAL_TOLERANCE)
    selected = positive[:2]
    if selected:
        coordinates = eigenvectors[:, selected] * np.sqrt(eigenvalues[list(selected)])
    else:
        coordinates = np.zeros((size, 0), dtype=np.float64)
    oriented = _orient_coordinates(np.asarray(coordinates, dtype=np.float64))
    oriented[np.abs(oriented) <= STRUCTURAL_TOLERANCE] = 0.0
    return tuple(
        MdsPoint(
            document_key=key,
            x=float(oriented[index, 0]),
            y=float(oriented[index, 1]),
        )
        for index, key in enumerate(cell.matrix.document_keys)
    )


def export_p009_schema(model: type[BaseModel], schema_id: str) -> dict[str, Any]:
    return {
        "$schema": _JSON_SCHEMA_DRAFT_2020_12,
        "$id": schema_id,
        **model.model_json_schema(mode="validation"),
    }


__all__ = [
    "BOUNDARIES",
    "MAX_RESULT_VIEW_BYTES",
    "MDS_METHOD",
    "MdsPoint",
    "NearestNeighbourRow",
    "P009ContractError",
    "P009ContractErrorCode",
    "RESULT_VIEW_COMPONENT",
    "RESULT_VIEW_PROFILE",
    "ResultCellStatus",
    "ResultCellV1",
    "ResultDocumentDescriptor",
    "ResultDocumentV1",
    "ResultMatrixV1",
    "ResultViewV1",
    "canonical_result_view",
    "classical_mds",
    "export_p009_schema",
    "nearest_neighbours",
    "parse_result_view",
    "project_result_view",
    "result_view_sha256",
]
