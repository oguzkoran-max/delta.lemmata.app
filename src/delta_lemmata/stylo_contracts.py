"""Closed P006 wire contracts and scientific semantic validation.

The worker receives post-preprocessing whole-text feature counts.  This module
does not tokenize text or calculate Delta distances; it validates the bounded
data exchanged with the fixed R worker and rejects scientifically inconsistent
results before lifecycle success can be persisted.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import unicodedata
from collections.abc import Iterable
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

INPUT_MAX_BYTES = 32 * 1024 * 1024
RESULT_MAX_BYTES = 32 * 1024 * 1024
FATAL_ERROR_MAX_BYTES = 4 * 1024
MAX_FEATURES = 20_000
MAX_DOCUMENTS = 50
MAX_FITS = 64
MAX_CELLS = 192
MAX_MFW = 1_000
MAX_TOKEN_COUNT = 3_000_000
MAX_AGGREGATE_COUNT = MAX_TOKEN_COUNT * MAX_DOCUMENTS
MAX_FEATURE_BYTES = 64
MAX_ABSOLUTE_NUMBER = sys.float_info.max
STRUCTURAL_TOLERANCE = 1e-12

# Conservative canonical-JSON bounds for the closed v1 shape. A feature made
# entirely of quotes or backslashes can double when escaped. Bounded Python
# IEEE-754 doubles serialize in at most 24 bytes, including sign and exponent.
_MAX_ESCAPED_FEATURE_WIRE_BYTES = (MAX_FEATURE_BYTES * 2) + 2
_MAX_NUMBER_WIRE_BYTES = 24
INPUT_WIRE_UPPER_BOUND = (
    1024 * 1024
    + (MAX_FEATURES * _MAX_ESCAPED_FEATURE_WIRE_BYTES)
    + (MAX_DOCUMENTS * MAX_FEATURES * 8)
)
RESULT_WIRE_UPPER_BOUND = (
    1024 * 1024
    + (MAX_FEATURES * (_MAX_ESCAPED_FEATURE_WIRE_BYTES + 128))
    + (
        MAX_FITS
        * (
            1024
            + MAX_MFW * (_MAX_ESCAPED_FEATURE_WIRE_BYTES + (2 * (_MAX_NUMBER_WIRE_BYTES + 1)) + 4)
        )
    )
    + (MAX_CELLS * (8192 + (MAX_DOCUMENTS * MAX_DOCUMENTS * (_MAX_NUMBER_WIRE_BYTES + 1))))
)

_JSON_SCHEMA_DRAFT_2020_12 = "https:" + "//json-schema.org/draft/2020-12/schema"
_REQUEST_PATTERN = r"^request_[0-9a-f]{64}$"
_DOCUMENT_PATTERN = r"^doc_[0-9a-f]{64}$"
_ASSET_PATTERN = r"^asset_[0-9a-f]{64}$"
_WORK_PATTERN = r"^work_[0-9a-f]{64}$"
_FIT_PATTERN = r"^fit_[0-9a-f]{64}$"
_CELL_PATTERN = r"^cell_[0-9a-f]{64}$"
_SAFE_SESSION_TEXT_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9 ._()+-]{0,127}$"

type RequestId = Annotated[str, Field(pattern=_REQUEST_PATTERN)]
type DocumentId = Annotated[str, Field(pattern=_DOCUMENT_PATTERN)]
type AssetRef = Annotated[str, Field(pattern=_ASSET_PATTERN)]
type WorkRef = Annotated[str, Field(pattern=_WORK_PATTERN)]
type FitId = Annotated[str, Field(pattern=_FIT_PATTERN)]
type CellId = Annotated[str, Field(pattern=_CELL_PATTERN)]
type Feature = Annotated[str, Field(min_length=1, max_length=MAX_FEATURE_BYTES)]
type Count = Annotated[StrictInt, Field(ge=0, le=MAX_TOKEN_COUNT)]
type AggregateCount = Annotated[StrictInt, Field(ge=0, le=MAX_AGGREGATE_COUNT)]
type PositiveCount = Annotated[StrictInt, Field(ge=1, le=MAX_TOKEN_COUNT)]
type MfwCount = Annotated[StrictInt, Field(ge=2, le=MAX_MFW)]
type Percentage = Annotated[StrictInt, Field(ge=0, le=100)]
type BoundedCardinality = Annotated[StrictInt, Field(ge=0, le=MAX_FEATURES)]
type FiniteNumber = Annotated[
    float,
    Field(ge=-MAX_ABSOLUTE_NUMBER, le=MAX_ABSOLUTE_NUMBER, allow_inf_nan=False),
]


class WireModel(BaseModel):
    """Immutable closed-world configuration for the worker wire format."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        hide_input_in_errors=True,
        str_strip_whitespace=False,
    )


class DocumentRole(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"


class DistanceMeasure(StrEnum):
    CLASSIC_DELTA = "classic_delta"
    EDERS_DELTA = "eders_delta"
    COSINE_DELTA = "cosine_delta"


class AnalysisOutcome(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class FitErrorCode(StrEnum):
    NON_POSITIVE_STANDARD_DEVIATION = "non_positive_standard_deviation"
    CALCULATION_FAILED = "calculation_failed"


class CellErrorCode(StrEnum):
    FIT_UNAVAILABLE = "fit_unavailable"
    DISTANCE_CALCULATION_FAILED = "distance_calculation_failed"


class FatalStage(StrEnum):
    INPUT_READ = "input_read"
    INPUT_PARSE = "input_parse"
    INPUT_VALIDATE = "input_validate"
    ENGINE_INIT = "engine_init"
    ANALYSIS = "analysis"
    RESULT_WRITE = "result_write"


class FatalErrorCode(StrEnum):
    INPUT_MISSING = "INPUT_MISSING"
    INPUT_TOO_LARGE = "INPUT_TOO_LARGE"
    INPUT_INVALID_UTF8 = "INPUT_INVALID_UTF8"
    INPUT_INVALID_JSON = "INPUT_INVALID_JSON"
    INPUT_INVALID_CONTRACT = "INPUT_INVALID_CONTRACT"
    ENVIRONMENT_INVALID = "ENVIRONMENT_INVALID"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    RESULT_WRITE_FAILED = "RESULT_WRITE_FAILED"


class StyloContractErrorCode(StrEnum):
    PAYLOAD_TYPE = "STYLO_CONTRACT_PAYLOAD_TYPE"
    PAYLOAD_EMPTY = "STYLO_CONTRACT_PAYLOAD_EMPTY"
    PAYLOAD_TOO_LARGE = "STYLO_CONTRACT_PAYLOAD_TOO_LARGE"
    INVALID_UTF8 = "STYLO_CONTRACT_INVALID_UTF8"
    INVALID_JSON = "STYLO_CONTRACT_INVALID_JSON"
    DUPLICATE_KEY = "STYLO_CONTRACT_DUPLICATE_KEY"
    NON_FINITE_NUMBER = "STYLO_CONTRACT_NON_FINITE_NUMBER"
    NUMBER_OUT_OF_RANGE = "STYLO_CONTRACT_NUMBER_OUT_OF_RANGE"
    INVALID_UNICODE = "STYLO_CONTRACT_INVALID_UNICODE"
    SCHEMA_INVALID = "STYLO_CONTRACT_SCHEMA_INVALID"
    SEMANTIC_INVALID = "STYLO_CONTRACT_SEMANTIC_INVALID"


class StyloContractError(ValueError):
    """Content-free parser or semantic rejection."""

    def __init__(self, code: StyloContractErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


def _feature_is_valid(value: str) -> bool:
    if unicodedata.normalize("NFC", value) != value:
        return False
    if len(value.encode("utf-8")) > MAX_FEATURE_BYTES:
        return False
    return all(not (ord(character) < 32 or 127 <= ord(character) <= 159) for character in value)


def _validate_features(values: tuple[str, ...]) -> tuple[str, ...]:
    if len(set(values)) != len(values) or any(not _feature_is_valid(value) for value in values):
        raise ValueError("features must be unique bounded NFC strings")
    return values


def _validate_finite_sequence(value: Any) -> tuple[int | float, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("a numeric sequence is required")
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError("finite JSON numbers are required")
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("finite JSON numbers are required")
        if abs(item) > MAX_ABSOLUTE_NUMBER:
            raise ValueError("finite JSON numbers are required")
    return tuple(value)


class DocumentCounts(WireModel):
    document_id: DocumentId
    asset_ref: AssetRef
    work_ref: WorkRef
    role: DocumentRole = Field(strict=False)
    token_total: PositiveCount
    counts: tuple[Count, ...] = Field(
        min_length=1,
        max_length=MAX_FEATURES,
        strict=False,
    )

    @model_validator(mode="after")
    def require_bounded_candidate_counts(self) -> Self:
        counted = sum(self.counts)
        if counted > self.token_total:
            raise ValueError("candidate counts must not exceed token_total")
        return self


class FitRequest(WireModel):
    fit_id: FitId
    mfw: MfwCount
    culling_percent: Percentage


class CellRequest(WireModel):
    cell_id: CellId
    fit_id: FitId
    distance: DistanceMeasure = Field(strict=False)


class WorkerInputV1(WireModel):
    schema_version: Literal["stylo-worker-input-v1"]
    request_id: RequestId
    limit_profile: Literal["stylo-worker-contract-limits-v1"]
    analysis_unit: Literal["whole_text"]
    seed: Literal[20260713]
    candidate_features: tuple[Feature, ...] = Field(
        min_length=1,
        max_length=MAX_FEATURES,
        strict=False,
    )
    documents: tuple[DocumentCounts, ...] = Field(
        min_length=2,
        max_length=MAX_DOCUMENTS,
        strict=False,
    )
    fits: tuple[FitRequest, ...] = Field(
        min_length=1,
        max_length=MAX_FITS,
        strict=False,
    )
    cells: tuple[CellRequest, ...] = Field(
        min_length=1,
        max_length=MAX_CELLS,
        strict=False,
    )

    @field_validator("candidate_features")
    @classmethod
    def require_valid_features(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_features(value)

    @model_validator(mode="after")
    def require_closed_request_graph(self) -> Self:
        feature_count = len(self.candidate_features)
        if any(len(document.counts) != feature_count for document in self.documents):
            raise ValueError("every count row must match the candidate feature inventory")
        if sum(document.role is DocumentRole.KNOWN for document in self.documents) < 2:
            raise ValueError("at least two known documents are required")
        for values in (
            tuple(document.document_id for document in self.documents),
            tuple(document.asset_ref for document in self.documents),
            tuple(document.work_ref for document in self.documents),
            tuple(fit.fit_id for fit in self.fits),
            tuple(cell.cell_id for cell in self.cells),
        ):
            if len(values) != len(set(values)):
                raise ValueError("opaque identifiers must be unique")
        fit_keys = tuple((fit.mfw, fit.culling_percent) for fit in self.fits)
        cell_keys = tuple((cell.fit_id, cell.distance) for cell in self.cells)
        if len(fit_keys) != len(set(fit_keys)) or len(cell_keys) != len(set(cell_keys)):
            raise ValueError("fit and cell configurations must be unique")
        fit_ids = {fit.fit_id for fit in self.fits}
        referenced = {cell.fit_id for cell in self.cells}
        if referenced != fit_ids:
            raise ValueError("every fit must be referenced and every cell reference must exist")
        return self


class RankedFeature(WireModel):
    feature: Feature
    known_total_count: AggregateCount
    known_document_count: Annotated[StrictInt, Field(ge=1, le=MAX_DOCUMENTS)]

    @field_validator("feature")
    @classmethod
    def require_valid_feature(cls, value: str) -> str:
        if not _feature_is_valid(value):
            raise ValueError("feature must be a bounded NFC string")
        return value


class FittingBasis(WireModel):
    known_document_ids: tuple[DocumentId, ...] = Field(
        min_length=2,
        max_length=MAX_DOCUMENTS,
        strict=False,
    )
    ranked_features: tuple[RankedFeature, ...] = Field(
        max_length=MAX_FEATURES,
        strict=False,
    )

    @model_validator(mode="after")
    def require_unique_basis(self) -> Self:
        document_ids = self.known_document_ids
        features = tuple(item.feature for item in self.ranked_features)
        if len(document_ids) != len(set(document_ids)) or len(features) != len(set(features)):
            raise ValueError("fitting basis identifiers and features must be unique")
        return self


class FitComplete(WireModel):
    fit_id: FitId
    mfw: MfwCount
    culling_percent: Percentage
    status: Literal["complete"]
    eligible_feature_count: BoundedCardinality
    selected_features: tuple[Feature, ...] = Field(
        min_length=1,
        max_length=MAX_MFW,
        strict=False,
    )
    means: tuple[FiniteNumber, ...] = Field(
        min_length=1,
        max_length=MAX_MFW,
        strict=False,
    )
    standard_deviations: tuple[FiniteNumber, ...] = Field(
        min_length=1,
        max_length=MAX_MFW,
        strict=False,
    )

    @field_validator("selected_features")
    @classmethod
    def require_valid_features(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_features(value)

    @field_validator("means", "standard_deviations", mode="before")
    @classmethod
    def require_finite_numbers(cls, value: Any) -> Any:
        return _validate_finite_sequence(value)

    @model_validator(mode="after")
    def require_aligned_fit_vectors(self) -> Self:
        if not (
            len(self.selected_features) == self.mfw
            and len(self.means) == self.mfw
            and len(self.standard_deviations) == self.mfw
            and self.eligible_feature_count >= self.mfw
        ):
            raise ValueError("complete fit vectors must match the requested MFW")
        if any(value <= 0 for value in self.standard_deviations):
            raise ValueError("complete fits require positive standard deviations")
        return self


class FitNotEnoughFeatures(WireModel):
    fit_id: FitId
    mfw: MfwCount
    culling_percent: Percentage
    status: Literal["not_enough_features"]
    eligible_feature_count: BoundedCardinality

    @model_validator(mode="after")
    def require_actual_shortfall(self) -> Self:
        if self.eligible_feature_count >= self.mfw:
            raise ValueError("not-enough status requires fewer eligible features than MFW")
        return self


class FitFailed(WireModel):
    fit_id: FitId
    mfw: MfwCount
    culling_percent: Percentage
    status: Literal["failed"]
    eligible_feature_count: BoundedCardinality
    error_code: FitErrorCode = Field(strict=False)


type FitResult = Annotated[
    FitComplete | FitNotEnoughFeatures | FitFailed,
    Field(discriminator="status"),
]


class DistanceMatrix(WireModel):
    document_ids: tuple[DocumentId, ...] = Field(
        min_length=2,
        max_length=MAX_DOCUMENTS,
        strict=False,
    )
    values: tuple[tuple[FiniteNumber, ...], ...] = Field(
        min_length=2,
        max_length=MAX_DOCUMENTS,
    )

    @field_validator("values", mode="before")
    @classmethod
    def require_finite_matrix(cls, value: Any) -> Any:
        if not isinstance(value, (list, tuple)):
            raise ValueError("a matrix is required")
        rows: list[tuple[int | float, ...]] = []
        for row in value:
            rows.append(_validate_finite_sequence(row))
        return tuple(rows)

    @model_validator(mode="after")
    def require_local_matrix_shape(self) -> Self:
        size = len(self.document_ids)
        if len(set(self.document_ids)) != size or any(len(row) != size for row in self.values):
            raise ValueError("distance matrix must be square with unique labels")
        return self


class CellComplete(WireModel):
    cell_id: CellId
    fit_id: FitId
    distance: DistanceMeasure = Field(strict=False)
    status: Literal["complete"]
    matrix: DistanceMatrix


class CellNotEnoughFeatures(WireModel):
    cell_id: CellId
    fit_id: FitId
    distance: DistanceMeasure = Field(strict=False)
    status: Literal["not_enough_features"]
    error_code: Literal["not_enough_features"]


class CellFailed(WireModel):
    cell_id: CellId
    fit_id: FitId
    distance: DistanceMeasure = Field(strict=False)
    status: Literal["failed"]
    error_code: CellErrorCode = Field(strict=False)


type CellResult = Annotated[
    CellComplete | CellNotEnoughFeatures | CellFailed,
    Field(discriminator="status"),
]


class RSessionInfoV1(WireModel):
    r_version: Literal["4.5.2"]
    stylo_version: Literal["0.7.71"]
    jsonlite_version: Literal["2.0.0"]
    platform: str = Field(pattern=_SAFE_SESSION_TEXT_PATTERN)
    operating_system: str = Field(pattern=_SAFE_SESSION_TEXT_PATTERN)
    lang: Literal["C.UTF-8"]
    lc_collate: Literal["C.UTF-8"]
    lc_ctype: Literal["C.UTF-8"]
    lc_numeric: Literal["C"]
    timezone: Literal["UTC"]
    unicode_normalization: Literal["NFC"]
    rng_generator: Literal["Mersenne-Twister"]
    rng_normal_generator: Literal["Inversion"]
    rng_sample_kind: Literal["Rejection"]
    seed: Literal[20260713]
    blas: str = Field(pattern=_SAFE_SESSION_TEXT_PATTERN)
    lapack: str = Field(pattern=_SAFE_SESSION_TEXT_PATTERN)


class WorkerResultV1(WireModel):
    schema_version: Literal["stylo-worker-result-v1"]
    request_id: RequestId
    limit_profile: Literal["stylo-worker-contract-limits-v1"]
    analysis_unit: Literal["whole_text"]
    seed: Literal[20260713]
    worker_version: Literal["stylo-worker-v1"]
    outcome: AnalysisOutcome = Field(strict=False)
    fitting_basis: FittingBasis
    fits: tuple[FitResult, ...] = Field(
        min_length=1,
        max_length=MAX_FITS,
        strict=False,
    )
    cells: tuple[CellResult, ...] = Field(
        min_length=1,
        max_length=MAX_CELLS,
        strict=False,
    )
    session: RSessionInfoV1

    @model_validator(mode="after")
    def require_unique_result_graph(self) -> Self:
        fit_ids = tuple(fit.fit_id for fit in self.fits)
        cell_ids = tuple(cell.cell_id for cell in self.cells)
        if len(fit_ids) != len(set(fit_ids)) or len(cell_ids) != len(set(cell_ids)):
            raise ValueError("result identifiers must be unique")
        return self


class DirectStyloOracleV1(WireModel):
    """Independent direct-stylo evidence envelope for the frozen P006 fixtures."""

    schema_version: Literal["direct-stylo-oracle-v1"]
    fixture_ref: Annotated[str, Field(pattern=r"^fixture_[0-9a-f]{64}$")]
    input_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    request_id: RequestId
    limit_profile: Literal["stylo-worker-contract-limits-v1"]
    analysis_unit: Literal["whole_text"]
    seed: Literal[20260713]
    oracle_version: Literal["p006-direct-stylo-v1"]
    outcome: AnalysisOutcome = Field(strict=False)
    fitting_basis: FittingBasis
    fits: tuple[FitResult, ...] = Field(
        min_length=1,
        max_length=MAX_FITS,
        strict=False,
    )
    cells: tuple[CellResult, ...] = Field(
        min_length=1,
        max_length=MAX_CELLS,
        strict=False,
    )
    session: RSessionInfoV1

    @model_validator(mode="after")
    def require_unique_result_graph(self) -> Self:
        fit_ids = tuple(fit.fit_id for fit in self.fits)
        cell_ids = tuple(cell.cell_id for cell in self.cells)
        if len(fit_ids) != len(set(fit_ids)) or len(cell_ids) != len(set(cell_ids)):
            raise ValueError("result identifiers must be unique")
        return self


_FATAL_CODES_BY_STAGE = {
    FatalStage.INPUT_READ: frozenset(
        {FatalErrorCode.INPUT_MISSING, FatalErrorCode.INPUT_TOO_LARGE}
    ),
    FatalStage.INPUT_PARSE: frozenset(
        {
            FatalErrorCode.INPUT_INVALID_UTF8,
            FatalErrorCode.INPUT_INVALID_JSON,
        }
    ),
    FatalStage.INPUT_VALIDATE: frozenset({FatalErrorCode.INPUT_INVALID_CONTRACT}),
    FatalStage.ENGINE_INIT: frozenset({FatalErrorCode.ENVIRONMENT_INVALID}),
    FatalStage.ANALYSIS: frozenset({FatalErrorCode.ANALYSIS_FAILED}),
    FatalStage.RESULT_WRITE: frozenset({FatalErrorCode.RESULT_WRITE_FAILED}),
}


class WorkerFatalErrorV1(WireModel):
    schema_version: Literal["stylo-worker-fatal-error-v1"]
    request_id: RequestId | None
    worker_version: Literal["stylo-worker-v1"]
    status: Literal["fatal_error"]
    stage: FatalStage = Field(strict=False)
    error_code: FatalErrorCode = Field(strict=False)

    @model_validator(mode="after")
    def require_stage_code_pair(self) -> Self:
        if self.error_code not in _FATAL_CODES_BY_STAGE[self.stage]:
            raise ValueError("fatal stage and code must agree")
        if self.request_id is None and self.stage not in {
            FatalStage.INPUT_READ,
            FatalStage.INPUT_PARSE,
            FatalStage.INPUT_VALIDATE,
        }:
            raise ValueError("post-validation failures require a request identifier")
        return self


class _DuplicateKey(ValueError):
    pass


class _NonFinite(ValueError):
    pass


class _NumberOutOfRange(ValueError):
    pass


class _SemanticFailure(ValueError):
    pass


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
                raise _NonFinite
            if abs(current) > MAX_ABSOLUTE_NUMBER:
                raise _NumberOutOfRange
        if isinstance(current, str):
            if any(0xD800 <= ord(character) <= 0xDFFF for character in current):
                raise UnicodeError
        elif isinstance(current, list):
            pending.extend(current)
        elif isinstance(current, dict):
            pending.extend(current.keys())
            pending.extend(current.values())


def _parse_payload[ModelT: BaseModel](
    payload: bytes,
    *,
    maximum: int,
    model: type[ModelT],
) -> ModelT:
    if not isinstance(payload, bytes):
        raise StyloContractError(StyloContractErrorCode.PAYLOAD_TYPE)
    if not payload:
        raise StyloContractError(StyloContractErrorCode.PAYLOAD_EMPTY)
    if len(payload) > maximum:
        raise StyloContractError(StyloContractErrorCode.PAYLOAD_TOO_LARGE)
    invalid_utf8 = False
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        invalid_utf8 = True
        text = ""
    if invalid_utf8:
        raise StyloContractError(StyloContractErrorCode.INVALID_UTF8)
    lexical_error: StyloContractErrorCode | None = None
    try:
        decoded = json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
        _check_json_tree(decoded)
    except _DuplicateKey:
        lexical_error = StyloContractErrorCode.DUPLICATE_KEY
    except _NonFinite:
        lexical_error = StyloContractErrorCode.NON_FINITE_NUMBER
    except _NumberOutOfRange:
        lexical_error = StyloContractErrorCode.NUMBER_OUT_OF_RANGE
    except UnicodeError:
        lexical_error = StyloContractErrorCode.INVALID_UNICODE
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
        lexical_error = StyloContractErrorCode.INVALID_JSON
    if lexical_error is not None:
        raise StyloContractError(lexical_error)
    validated: ModelT | None = None
    try:
        validated = model.model_validate(decoded)
    except (ValidationError, OverflowError):
        pass
    if validated is None:
        raise StyloContractError(StyloContractErrorCode.SCHEMA_INVALID)
    return validated


def parse_worker_input(payload: bytes) -> WorkerInputV1:
    return _parse_payload(payload, maximum=INPUT_MAX_BYTES, model=WorkerInputV1)


def parse_worker_result(payload: bytes) -> WorkerResultV1:
    return _parse_payload(payload, maximum=RESULT_MAX_BYTES, model=WorkerResultV1)


def parse_direct_stylo_oracle(payload: bytes) -> DirectStyloOracleV1:
    return _parse_payload(payload, maximum=RESULT_MAX_BYTES, model=DirectStyloOracleV1)


def parse_worker_fatal_error(payload: bytes) -> WorkerFatalErrorV1:
    return _parse_payload(payload, maximum=FATAL_ERROR_MAX_BYTES, model=WorkerFatalErrorV1)


def canonical_worker_json(
    record: WorkerInputV1 | WorkerResultV1 | WorkerFatalErrorV1 | DirectStyloOracleV1,
) -> bytes:
    """Serialize one already validated worker record without non-standard numbers."""

    payload = (
        json.dumps(
            record.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    maximum = (
        INPUT_MAX_BYTES
        if isinstance(record, WorkerInputV1)
        else RESULT_MAX_BYTES
        if isinstance(record, (WorkerResultV1, DirectStyloOracleV1))
        else FATAL_ERROR_MAX_BYTES
    )
    if len(payload) > maximum:
        raise StyloContractError(StyloContractErrorCode.PAYLOAD_TOO_LARGE)
    return payload


def export_stylo_schema(model: type[BaseModel], schema_id: str) -> dict[str, Any]:
    """Return a deterministic Draft 2020-12 schema for one P006 wire model."""

    return {
        "$schema": _JSON_SCHEMA_DRAFT_2020_12,
        "$id": schema_id,
        **model.model_json_schema(mode="validation"),
    }


def _ranked_features(request: WorkerInputV1) -> tuple[RankedFeature, ...]:
    known = tuple(document for document in request.documents if document.role is DocumentRole.KNOWN)
    items: list[RankedFeature] = []
    for index, feature in enumerate(request.candidate_features):
        values = tuple(document.counts[index] for document in known)
        total = sum(values)
        present = sum(value > 0 for value in values)
        if total > 0:
            items.append(
                RankedFeature(
                    feature=feature,
                    known_total_count=total,
                    known_document_count=present,
                )
            )
    return tuple(sorted(items, key=lambda item: (-item.known_total_count, item.feature.encode())))


def _eligible_features(
    ranked: tuple[RankedFeature, ...],
    *,
    known_count: int,
    culling_percent: int,
) -> tuple[str, ...]:
    return tuple(
        item.feature
        for item in ranked
        if item.known_document_count * 100 >= culling_percent * known_count
    )


def _fit_statistics(
    request: WorkerInputV1,
    selected: tuple[str, ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    feature_indexes = {feature: index for index, feature in enumerate(request.candidate_features)}
    known = tuple(document for document in request.documents if document.role is DocumentRole.KNOWN)
    means: list[float] = []
    deviations: list[float] = []
    for feature in selected:
        index = feature_indexes[feature]
        values = tuple(document.counts[index] * 100.0 / document.token_total for document in known)
        mean = math.fsum(values) / len(values)
        variance = math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1)
        means.append(mean)
        deviations.append(math.sqrt(variance))
    return tuple(means), tuple(deviations)


def _same_numbers(actual: Iterable[float], expected: Iterable[float]) -> bool:
    return all(
        abs(left - right) <= STRUCTURAL_TOLERANCE
        for left, right in zip(actual, expected, strict=True)
    )


def _validate_matrix(matrix: DistanceMatrix, expected_ids: tuple[str, ...]) -> None:
    if matrix.document_ids != expected_ids or len(matrix.values) != len(expected_ids):
        raise _SemanticFailure
    for row_index, row in enumerate(matrix.values):
        if len(row) != len(expected_ids):
            raise _SemanticFailure
        for column_index, value in enumerate(row):
            if value < 0:
                raise _SemanticFailure
            if row_index == column_index and abs(value) > STRUCTURAL_TOLERANCE:
                raise _SemanticFailure
            if abs(value - matrix.values[column_index][row_index]) > STRUCTURAL_TOLERANCE:
                raise _SemanticFailure


def _require(condition: bool) -> None:
    if not condition:
        raise _SemanticFailure


def validate_worker_result(request: WorkerInputV1, result: WorkerResultV1) -> WorkerResultV1:
    """Validate all input-dependent fitting, cell, and matrix invariants."""

    invalid = False
    try:
        _require(result.request_id == request.request_id)
        known_ids = tuple(
            document.document_id
            for document in request.documents
            if document.role is DocumentRole.KNOWN
        )
        document_ids = tuple(document.document_id for document in request.documents)
        ranked = _ranked_features(request)
        _require(result.fitting_basis.known_document_ids == known_ids)
        _require(result.fitting_basis.ranked_features == ranked)
        _require(len(result.fits) == len(request.fits))
        _require(len(result.cells) == len(request.cells))

        fits_by_id: dict[str, FitResult] = {}
        for fit_request, fit_result in zip(request.fits, result.fits, strict=True):
            _require(
                (fit_result.fit_id, fit_result.mfw, fit_result.culling_percent)
                == (fit_request.fit_id, fit_request.mfw, fit_request.culling_percent)
            )
            eligible = _eligible_features(
                ranked,
                known_count=len(known_ids),
                culling_percent=fit_request.culling_percent,
            )
            eligible_count = len(eligible)
            _require(fit_result.eligible_feature_count == eligible_count)
            if eligible_count < fit_request.mfw:
                _require(isinstance(fit_result, FitNotEnoughFeatures))
            else:
                selected = eligible[: fit_request.mfw]
                means, deviations = _fit_statistics(request, selected)
                if any(value <= 0 for value in deviations):
                    _require(
                        isinstance(fit_result, FitFailed)
                        and fit_result.error_code is FitErrorCode.NON_POSITIVE_STANDARD_DEVIATION
                    )
                elif isinstance(fit_result, FitComplete):
                    _require(fit_result.selected_features == selected)
                    _require(len(fit_result.means) == len(means))
                    _require(len(fit_result.standard_deviations) == len(deviations))
                    _require(_same_numbers(fit_result.means, means))
                    _require(_same_numbers(fit_result.standard_deviations, deviations))
                else:
                    _require(
                        isinstance(fit_result, FitFailed)
                        and fit_result.error_code is FitErrorCode.CALCULATION_FAILED
                    )
            fits_by_id[fit_result.fit_id] = fit_result

        complete_cells = 0
        for cell_request, cell_result in zip(request.cells, result.cells, strict=True):
            _require(
                (cell_result.cell_id, cell_result.fit_id, cell_result.distance)
                == (cell_request.cell_id, cell_request.fit_id, cell_request.distance)
            )
            fit_result = fits_by_id[cell_request.fit_id]
            if isinstance(fit_result, FitNotEnoughFeatures):
                _require(isinstance(cell_result, CellNotEnoughFeatures))
            elif isinstance(fit_result, FitFailed):
                _require(
                    isinstance(cell_result, CellFailed)
                    and cell_result.error_code is CellErrorCode.FIT_UNAVAILABLE
                )
            elif isinstance(cell_result, CellComplete):
                _validate_matrix(cell_result.matrix, document_ids)
                complete_cells += 1
            else:
                _require(
                    isinstance(cell_result, CellFailed)
                    and cell_result.error_code is CellErrorCode.DISTANCE_CALCULATION_FAILED
                )

        expected_outcome = (
            AnalysisOutcome.COMPLETE
            if complete_cells == len(request.cells)
            else AnalysisOutcome.PARTIAL
            if complete_cells > 0
            else AnalysisOutcome.FAILED
        )
        _require(result.outcome is expected_outcome)
    except (ArithmeticError, KeyError, ValidationError, ValueError):
        invalid = True
    if invalid:
        raise StyloContractError(StyloContractErrorCode.SEMANTIC_INVALID)
    return result


def validate_direct_stylo_oracle(
    request: WorkerInputV1,
    oracle: DirectStyloOracleV1,
) -> DirectStyloOracleV1:
    """Bind independent oracle evidence to exact input bytes and scientific semantics."""

    expected_digest = hashlib.sha256(canonical_worker_json(request)).hexdigest()
    if oracle.input_sha256 != expected_digest:
        raise StyloContractError(StyloContractErrorCode.SEMANTIC_INVALID) from None
    worker_equivalent = WorkerResultV1(
        schema_version="stylo-worker-result-v1",
        request_id=oracle.request_id,
        limit_profile=oracle.limit_profile,
        analysis_unit=oracle.analysis_unit,
        seed=oracle.seed,
        worker_version="stylo-worker-v1",
        outcome=oracle.outcome,
        fitting_basis=oracle.fitting_basis,
        fits=oracle.fits,
        cells=oracle.cells,
        session=oracle.session,
    )
    validate_worker_result(request, worker_equivalent)
    return oracle


def validate_worker_fatal_error(
    request: WorkerInputV1,
    error: WorkerFatalErrorV1,
) -> WorkerFatalErrorV1:
    """Bind a post-parse fatal envelope to the trusted request."""

    if error.request_id != request.request_id:
        raise StyloContractError(StyloContractErrorCode.SEMANTIC_INVALID) from None
    return error


__all__ = [
    "FATAL_ERROR_MAX_BYTES",
    "INPUT_MAX_BYTES",
    "INPUT_WIRE_UPPER_BOUND",
    "RESULT_MAX_BYTES",
    "RESULT_WIRE_UPPER_BOUND",
    "STRUCTURAL_TOLERANCE",
    "AnalysisOutcome",
    "CellComplete",
    "CellErrorCode",
    "CellFailed",
    "CellNotEnoughFeatures",
    "CellRequest",
    "DistanceMatrix",
    "DistanceMeasure",
    "DirectStyloOracleV1",
    "DocumentCounts",
    "DocumentRole",
    "FatalErrorCode",
    "FatalStage",
    "FitComplete",
    "FitErrorCode",
    "FitFailed",
    "FitNotEnoughFeatures",
    "FitRequest",
    "FittingBasis",
    "RSessionInfoV1",
    "RankedFeature",
    "StyloContractError",
    "StyloContractErrorCode",
    "WorkerFatalErrorV1",
    "WorkerInputV1",
    "WorkerResultV1",
    "canonical_worker_json",
    "export_stylo_schema",
    "parse_worker_fatal_error",
    "parse_direct_stylo_oracle",
    "parse_worker_input",
    "parse_worker_result",
    "validate_worker_fatal_error",
    "validate_direct_stylo_oracle",
    "validate_worker_result",
]
