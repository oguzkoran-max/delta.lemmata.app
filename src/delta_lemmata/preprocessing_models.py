"""Closed P007 contracts for deterministic text preparation and admission."""

from __future__ import annotations

import json
import math
import sys
import unicodedata
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, model_validator

MAX_P007_DOCUMENTS = 200
MAX_P006_DOCUMENTS = 50
MAX_TOKEN_COUNT = 3_000_000
MAX_CANDIDATE_FEATURES = 20_000
MAX_CONTRACT_BYTES = 4 * 1024 * 1024
MAX_NOTE_CHARS = 2_000
MAX_PREPARED_BYTES = 50 * 1024 * 1024
MAX_RAW_BYTES = 25 * 1024 * 1024

_JSON_SCHEMA_DRAFT_2020_12 = "https:" + "//json-schema.org/draft/2020-12/schema"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_DOCUMENT_PATTERN = r"^doc_[0-9a-f]{64}$"
_RECEIPT_PATTERN = r"^receipt_[0-9a-f]{64}$"
_SLUG_PATTERN = r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$"
_ASSET_PATTERN = r"^asset_[a-z0-9]+(?:[._-][a-z0-9]+)*$"

type Sha256 = Annotated[str, Field(pattern=_SHA256_PATTERN)]
type DocumentId = Annotated[str, Field(pattern=_DOCUMENT_PATTERN)]
type ReceiptId = Annotated[str, Field(pattern=_RECEIPT_PATTERN)]
type WorkId = Annotated[str, Field(pattern=_SLUG_PATTERN)]
type AssetId = Annotated[str, Field(pattern=_ASSET_PATTERN)]
type TokenCount = Annotated[StrictInt, Field(ge=0, le=MAX_TOKEN_COUNT)]
type ByteCount = Annotated[StrictInt, Field(ge=0, le=MAX_PREPARED_BYTES)]
type SourceCharacterCount = Annotated[StrictInt, Field(ge=0, le=20_000_000)]


class P007Model(BaseModel):
    """Immutable closed-world P007 model."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        allow_inf_nan=False,
        hide_input_in_errors=True,
        str_strip_whitespace=False,
    )


class AnalysisRole(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"


class TextUnit(StrEnum):
    INDEPENDENT_WORK = "independent_work"
    SEGMENT = "segment"
    EXCERPT = "excerpt"


class OcrStatus(StrEnum):
    NOT_OCR = "not_ocr"
    REVIEWED = "reviewed"
    UNREVIEWED = "unreviewed"
    UNKNOWN = "unknown"


class ParatextStatus(StrEnum):
    ABSENT = "absent"
    RETAINED = "retained"
    MANUALLY_REMOVED_BEFORE_UPLOAD = "manually_removed_before_upload"
    UNKNOWN = "unknown"


class PreparationState(StrEnum):
    READY = "READY"


class PreprocessingConfigV1(P007Model):
    schema_version: Literal["preprocessing-config-v1"]
    profile_id: Literal["delta-surface-words-v1"]
    intake_profile: Literal["ingestion-limits-v1"]
    unicode_normalization: Literal["NFC"]
    lowercase_mode: Literal["unicode_str_lower"]
    token_profile: Literal["letter_sequences_with_following_marks"]
    preserve_diacritics: Literal[True]
    retain_stopwords: Literal[True]
    remove_punctuation: Literal[True]
    remove_numbers: Literal[True]
    lemmatization: Literal[False]
    stemming: Literal[False]
    automatic_paratext_removal: Literal[False]
    custom_exclusions_sha256: Sha256 | None
    custom_exclusion_count: Annotated[StrictInt, Field(ge=0, le=MAX_CANDIDATE_FEATURES)]
    max_candidate_features: Annotated[
        StrictInt,
        Field(ge=2, le=MAX_CANDIDATE_FEATURES),
    ]

    @model_validator(mode="after")
    def require_exclusion_digest_and_count_together(self) -> Self:
        if (self.custom_exclusions_sha256 is None) != (self.custom_exclusion_count == 0):
            raise ValueError("exclusion digest and count must be present together")
        return self


class CorpusAnalysisAnnotation(P007Model):
    document_id: DocumentId
    asset_id: AssetId
    work_id: WorkId
    analysis_role: AnalysisRole = Field(strict=False)
    text_unit: TextUnit = Field(strict=False)
    parent_work_id: WorkId | None
    ocr_status: OcrStatus = Field(strict=False)
    paratext_status: ParatextStatus = Field(strict=False)
    preupload_curation_note: str | None = Field(
        default=None, min_length=1, max_length=MAX_NOTE_CHARS
    )

    @model_validator(mode="after")
    def require_unit_parent_and_safe_note(self) -> Self:
        if self.text_unit is TextUnit.INDEPENDENT_WORK:
            if self.parent_work_id is not None:
                raise ValueError("independent works cannot declare a parent")
        elif self.parent_work_id is None or self.parent_work_id == self.work_id:
            raise ValueError("segments and excerpts require a distinct parent work")
        if self.preupload_curation_note is not None:
            note = self.preupload_curation_note
            if unicodedata.normalize("NFC", note) != note:
                raise ValueError("curation notes must be NFC")
            if any(unicodedata.category(character) in {"Cc", "Cs"} for character in note):
                raise ValueError("curation notes cannot contain control characters")
        return self


class CorpusAnalysisAnnotationsV1(P007Model):
    schema_version: Literal["corpus-analysis-annotations-v1"]
    inventory_sha256: Sha256
    annotations: tuple[CorpusAnalysisAnnotation, ...] = Field(
        min_length=1,
        max_length=MAX_P007_DOCUMENTS,
        strict=False,
    )

    @model_validator(mode="after")
    def require_unique_document_and_asset_ids(self) -> Self:
        for values in (
            tuple(item.document_id for item in self.annotations),
            tuple(item.asset_id for item in self.annotations),
        ):
            if len(values) != len(set(values)):
                raise ValueError("annotation document and asset identifiers must be unique")
        return self


class WorkPreparationV1(P007Model):
    document_id: DocumentId
    asset_id: AssetId
    work_id: WorkId
    analysis_role: AnalysisRole = Field(strict=False)
    text_unit: TextUnit = Field(strict=False)
    parent_work_id: WorkId | None
    raw_sha256: Sha256
    prepared_sha256: Sha256
    raw_byte_count: Annotated[StrictInt, Field(ge=0, le=MAX_RAW_BYTES)]
    prepared_byte_count: ByteCount
    token_count: TokenCount
    unique_token_count: TokenCount
    bom_removed: bool
    newline_replacement_count: SourceCharacterCount
    lowercase_source_count: SourceCharacterCount
    separator_source_count: SourceCharacterCount

    @model_validator(mode="after")
    def require_consistent_counts_and_unit(self) -> Self:
        if self.unique_token_count > self.token_count:
            raise ValueError("unique token count cannot exceed token count")
        if self.text_unit is TextUnit.INDEPENDENT_WORK:
            if self.parent_work_id is not None:
                raise ValueError("independent work preparation cannot declare a parent")
        elif self.parent_work_id is None or self.parent_work_id == self.work_id:
            raise ValueError("non-independent preparation requires a distinct parent")
        return self


class PreprocessingManifestV1(P007Model):
    schema_version: Literal["preprocessing-manifest-v1"]
    profile_id: Literal["delta-surface-words-v1"]
    config_sha256: Sha256
    inventory_sha256: Sha256
    annotations_sha256: Sha256
    candidate_inventory_sha256: Sha256
    candidate_feature_count: Annotated[
        StrictInt,
        Field(ge=0, le=MAX_CANDIDATE_FEATURES),
    ]
    implementation_version: Annotated[str, Field(pattern=r"^[A-Za-z0-9._+-]{1,64}$")]
    python_version: Annotated[str, Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]
    unicode_version: Annotated[str, Field(pattern=r"^[0-9]+(?:\.[0-9]+){1,2}$")]
    works: tuple[WorkPreparationV1, ...] = Field(
        min_length=1,
        max_length=MAX_P007_DOCUMENTS,
        strict=False,
    )

    @model_validator(mode="after")
    def require_unique_manifest_bindings(self) -> Self:
        for values in (
            tuple(item.document_id for item in self.works),
            tuple(item.asset_id for item in self.works),
        ):
            if len(values) != len(set(values)):
                raise ValueError("manifest document and asset identifiers must be unique")
        return self


class ReceiptDocumentBinding(P007Model):
    document_id: DocumentId
    asset_id: AssetId
    work_id: WorkId
    analysis_role: AnalysisRole = Field(strict=False)


class AnalysisPreparationReceiptV1(P007Model):
    schema_version: Literal["analysis-preparation-receipt-v1"]
    receipt_id: ReceiptId
    state: PreparationState = Field(strict=False)
    issued_at_utc: datetime = Field(strict=False)
    expires_at_utc: datetime = Field(strict=False)
    admission_nonce_sha256: Sha256
    inventory_sha256: Sha256
    validation_report_sha256: Sha256
    annotations_sha256: Sha256
    config_sha256: Sha256
    manifest_sha256: Sha256
    health_report_sha256: Sha256
    candidate_inventory_sha256: Sha256
    candidate_feature_count: Annotated[
        StrictInt,
        Field(ge=2, le=MAX_CANDIDATE_FEATURES),
    ]
    blocker_count: Literal[0]
    ordered_documents: tuple[ReceiptDocumentBinding, ...] = Field(
        min_length=2,
        max_length=MAX_P006_DOCUMENTS,
        strict=False,
    )

    @model_validator(mode="after")
    def require_bounded_utc_lease_and_unique_bindings(self) -> Self:
        if self.issued_at_utc.utcoffset() != timedelta(0):
            raise ValueError("receipt issue time must be UTC")
        if self.expires_at_utc.utcoffset() != timedelta(0):
            raise ValueError("receipt expiry time must be UTC")
        lease = self.expires_at_utc - self.issued_at_utc
        if lease <= timedelta(0) or lease > timedelta(hours=1):
            raise ValueError("receipt lease must be positive and at most one hour")
        for values in (
            tuple(item.document_id for item in self.ordered_documents),
            tuple(item.asset_id for item in self.ordered_documents),
            tuple(item.work_id for item in self.ordered_documents),
        ):
            if len(values) != len(set(values)):
                raise ValueError("receipt document, asset, and work identifiers must be unique")
        if sum(item.analysis_role is AnalysisRole.KNOWN for item in self.ordered_documents) < 2:
            raise ValueError("receipt requires at least two known works")
        return self


class P007ContractErrorCode(StrEnum):
    PAYLOAD_TYPE = "P007_CONTRACT_PAYLOAD_TYPE"
    PAYLOAD_EMPTY = "P007_CONTRACT_PAYLOAD_EMPTY"
    PAYLOAD_TOO_LARGE = "P007_CONTRACT_PAYLOAD_TOO_LARGE"
    INVALID_UTF8 = "P007_CONTRACT_INVALID_UTF8"
    INVALID_JSON = "P007_CONTRACT_INVALID_JSON"
    DUPLICATE_KEY = "P007_CONTRACT_DUPLICATE_KEY"
    NON_FINITE_NUMBER = "P007_CONTRACT_NON_FINITE_NUMBER"
    NUMBER_OUT_OF_RANGE = "P007_CONTRACT_NUMBER_OUT_OF_RANGE"
    INVALID_UNICODE = "P007_CONTRACT_INVALID_UNICODE"
    SCHEMA_INVALID = "P007_CONTRACT_SCHEMA_INVALID"
    SEMANTIC_INVALID = "P007_CONTRACT_SEMANTIC_INVALID"


class P007ContractError(ValueError):
    """Content-free P007 contract rejection."""

    def __init__(self, code: P007ContractErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class _DuplicateKey(ValueError):
    pass


class _NonFinite(ValueError):
    pass


class _NumberOutOfRange(ValueError):
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


def parse_p007_payload[ModelT: BaseModel](
    payload: bytes,
    *,
    model: type[ModelT],
    maximum: int = MAX_CONTRACT_BYTES,
) -> ModelT:
    """Parse one closed P007 JSON payload exactly once."""

    if not isinstance(payload, bytes):
        raise P007ContractError(P007ContractErrorCode.PAYLOAD_TYPE)
    if not payload:
        raise P007ContractError(P007ContractErrorCode.PAYLOAD_EMPTY)
    if len(payload) > maximum:
        raise P007ContractError(P007ContractErrorCode.PAYLOAD_TOO_LARGE)
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise P007ContractError(P007ContractErrorCode.INVALID_UTF8) from None
    try:
        decoded = json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
        _check_json_tree(decoded)
    except _DuplicateKey:
        raise P007ContractError(P007ContractErrorCode.DUPLICATE_KEY) from None
    except _NonFinite:
        raise P007ContractError(P007ContractErrorCode.NON_FINITE_NUMBER) from None
    except _NumberOutOfRange:
        raise P007ContractError(P007ContractErrorCode.NUMBER_OUT_OF_RANGE) from None
    except UnicodeError:
        raise P007ContractError(P007ContractErrorCode.INVALID_UNICODE) from None
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
        raise P007ContractError(P007ContractErrorCode.INVALID_JSON) from None
    try:
        return model.model_validate(decoded)
    except (OverflowError, ValidationError):
        raise P007ContractError(P007ContractErrorCode.SCHEMA_INVALID) from None


def parse_preprocessing_config(payload: bytes) -> PreprocessingConfigV1:
    return parse_p007_payload(payload, model=PreprocessingConfigV1, maximum=64 * 1024)


def parse_corpus_analysis_annotations(payload: bytes) -> CorpusAnalysisAnnotationsV1:
    return parse_p007_payload(payload, model=CorpusAnalysisAnnotationsV1)


def parse_preprocessing_manifest(payload: bytes) -> PreprocessingManifestV1:
    return parse_p007_payload(payload, model=PreprocessingManifestV1)


def parse_analysis_preparation_receipt(payload: bytes) -> AnalysisPreparationReceiptV1:
    return parse_p007_payload(payload, model=AnalysisPreparationReceiptV1, maximum=1024 * 1024)


def canonical_p007_json(record: BaseModel) -> bytes:
    """Serialize one validated P007 record as deterministic UTF-8 JSON."""

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


def export_p007_schema(model: type[BaseModel], schema_id: str) -> dict[str, Any]:
    """Return a deterministic Draft 2020-12 schema for one P007 model."""

    return {
        "$schema": _JSON_SCHEMA_DRAFT_2020_12,
        "$id": schema_id,
        **model.model_json_schema(mode="validation"),
    }


__all__ = [
    "MAX_CANDIDATE_FEATURES",
    "MAX_P006_DOCUMENTS",
    "MAX_P007_DOCUMENTS",
    "MAX_TOKEN_COUNT",
    "AnalysisPreparationReceiptV1",
    "AnalysisRole",
    "CorpusAnalysisAnnotation",
    "CorpusAnalysisAnnotationsV1",
    "OcrStatus",
    "P007ContractError",
    "P007ContractErrorCode",
    "P007Model",
    "ParatextStatus",
    "PreparationState",
    "PreprocessingConfigV1",
    "PreprocessingManifestV1",
    "ReceiptDocumentBinding",
    "TextUnit",
    "WorkPreparationV1",
    "canonical_p007_json",
    "export_p007_schema",
    "parse_analysis_preparation_receipt",
    "parse_corpus_analysis_annotations",
    "parse_p007_payload",
    "parse_preprocessing_config",
    "parse_preprocessing_manifest",
]
