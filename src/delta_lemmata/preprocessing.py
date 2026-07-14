"""Deterministic P007 surface-word preparation and known-only feature ranking."""

from __future__ import annotations

import hashlib
import json
import platform
import unicodedata
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

from delta_lemmata import __version__
from delta_lemmata.preprocessing_models import (
    MAX_CANDIDATE_FEATURES,
    MAX_TOKEN_COUNT,
    AnalysisRole,
    CorpusAnalysisAnnotation,
    CorpusAnalysisAnnotationsV1,
    PreprocessingConfigV1,
    PreprocessingManifestV1,
    TextUnit,
    WorkPreparationV1,
    canonical_p007_json,
)

MAX_RAW_BYTES = 25 * 1024 * 1024
MAX_TEXT_CHARACTERS = 20_000_000
MAX_EXCLUSION_BYTES = 1024 * 1024
MAX_P006_FEATURE_BYTES = 64
MAX_PREPARED_BYTES = 50 * 1024 * 1024
_UTF8_BOM = b"\xef\xbb\xbf"


class PreprocessingErrorCode(StrEnum):
    PAYLOAD_TYPE = "PREPROCESSING_PAYLOAD_TYPE"
    INPUT_TOO_LARGE = "PREPROCESSING_INPUT_TOO_LARGE"
    INVALID_UTF8 = "PREPROCESSING_INVALID_UTF8"
    INPUT_NOT_NFC = "PREPROCESSING_INPUT_NOT_NFC"
    EMBEDDED_BOM = "PREPROCESSING_EMBEDDED_BOM"
    RAW_DIGEST_MISMATCH = "PREPROCESSING_RAW_DIGEST_MISMATCH"
    TEXT_TOO_LONG = "PREPROCESSING_TEXT_TOO_LONG"
    TOKEN_LIMIT = "PREPROCESSING_TOKEN_LIMIT"
    PREPARED_TOO_LARGE = "PREPROCESSING_PREPARED_TOO_LARGE"
    EXCLUSIONS_TOO_LARGE = "PREPROCESSING_EXCLUSIONS_TOO_LARGE"
    EXCLUSIONS_INVALID = "PREPROCESSING_EXCLUSIONS_INVALID"


class PreprocessingError(ValueError):
    """Content-free text-preparation rejection."""

    def __init__(self, code: PreprocessingErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class CandidateInventoryError(ValueError):
    """Fail-closed known-work feature-inventory rejection."""

    def __init__(self) -> None:
        super().__init__("CANDIDATE_INVENTORY_INVALID")


@dataclass(frozen=True, slots=True)
class CustomExclusions:
    tokens: tuple[str, ...]
    source_sha256: str | None


@dataclass(frozen=True, slots=True)
class PreparedText:
    raw_sha256: str
    prepared_sha256: str
    prepared_bytes: bytes
    tokens: tuple[str, ...]
    full_counts: tuple[tuple[str, int], ...]
    token_count: int
    unique_token_count: int
    raw_byte_count: int
    prepared_byte_count: int
    bom_removed: bool
    newline_replacement_count: int
    lowercase_source_count: int
    separator_source_count: int


@dataclass(frozen=True, slots=True)
class PreparedDocument:
    annotation: CorpusAnalysisAnnotation
    prepared: PreparedText

    @property
    def independence_key(self) -> str:
        return self.annotation.parent_work_id or self.annotation.work_id


@dataclass(frozen=True, slots=True)
class CandidateInventory:
    features: tuple[str, ...]
    sha256: str
    known_independent_work_count: int
    transport_excluded_feature_count: int


def _tokenize(value: str) -> tuple[tuple[str, ...], int]:
    tokens: list[str] = []
    current: list[str] = []
    separators = 0
    for character in value:
        category = unicodedata.category(character)
        if category.startswith("L"):
            current.append(character)
        elif category.startswith("M") and current:
            current.append(character)
        else:
            if current:
                tokens.append("".join(current))
                current = []
            separators += 1
    if current:
        tokens.append("".join(current))
    return tuple(tokens), separators


def prepare_text(raw_bytes: bytes, *, expected_raw_sha256: str) -> PreparedText:
    """Apply `delta-surface-words-v1` without mutating the uploaded bytes."""

    if not isinstance(raw_bytes, bytes):
        raise PreprocessingError(PreprocessingErrorCode.PAYLOAD_TYPE)
    if len(raw_bytes) > MAX_RAW_BYTES:
        raise PreprocessingError(PreprocessingErrorCode.INPUT_TOO_LARGE)
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if raw_sha256 != expected_raw_sha256:
        raise PreprocessingError(PreprocessingErrorCode.RAW_DIGEST_MISMATCH)
    bom_removed = raw_bytes.startswith(_UTF8_BOM)
    try:
        text = raw_bytes.decode("utf-8-sig" if bom_removed else "utf-8", errors="strict")
    except UnicodeDecodeError:
        raise PreprocessingError(PreprocessingErrorCode.INVALID_UTF8) from None
    if "\ufeff" in text:
        raise PreprocessingError(PreprocessingErrorCode.EMBEDDED_BOM)
    if len(text) > MAX_TEXT_CHARACTERS:
        raise PreprocessingError(PreprocessingErrorCode.TEXT_TOO_LONG)
    if unicodedata.normalize("NFC", text) != text:
        raise PreprocessingError(PreprocessingErrorCode.INPUT_NOT_NFC)

    crlf_count = text.count("\r\n")
    text_without_crlf = text.replace("\r\n", "\n")
    lone_cr_count = text_without_crlf.count("\r")
    normalized_newlines = text_without_crlf.replace("\r", "\n")
    lowercase_source_count = sum(
        character.lower() != character for character in normalized_newlines
    )
    lowered = normalized_newlines.lower()
    normalized = unicodedata.normalize("NFC", lowered)
    tokens, separator_source_count = _tokenize(normalized)
    if len(tokens) > MAX_TOKEN_COUNT:
        raise PreprocessingError(PreprocessingErrorCode.TOKEN_LIMIT)
    prepared_bytes = (" ".join(tokens) + "\n").encode("utf-8")
    if len(prepared_bytes) > MAX_PREPARED_BYTES:
        raise PreprocessingError(PreprocessingErrorCode.PREPARED_TOO_LARGE)
    counts = Counter(tokens)
    full_counts = tuple(sorted(counts.items(), key=lambda item: item[0].encode("utf-8")))
    return PreparedText(
        raw_sha256=raw_sha256,
        prepared_sha256=hashlib.sha256(prepared_bytes).hexdigest(),
        prepared_bytes=prepared_bytes,
        tokens=tokens,
        full_counts=full_counts,
        token_count=len(tokens),
        unique_token_count=len(counts),
        raw_byte_count=len(raw_bytes),
        prepared_byte_count=len(prepared_bytes),
        bom_removed=bom_removed,
        newline_replacement_count=crlf_count + lone_cr_count,
        lowercase_source_count=lowercase_source_count,
        separator_source_count=separator_source_count,
    )


def prepare_document(
    raw_bytes: bytes,
    *,
    expected_raw_sha256: str,
    annotation: CorpusAnalysisAnnotation,
) -> PreparedDocument:
    return PreparedDocument(
        annotation=annotation,
        prepared=prepare_text(raw_bytes, expected_raw_sha256=expected_raw_sha256),
    )


def parse_custom_exclusions(payload: bytes | None) -> CustomExclusions:
    """Parse exact profile tokens without applying invisible normalization."""

    if payload is None:
        return CustomExclusions(tokens=(), source_sha256=None)
    if not isinstance(payload, bytes):
        raise PreprocessingError(PreprocessingErrorCode.PAYLOAD_TYPE)
    if len(payload) > MAX_EXCLUSION_BYTES:
        raise PreprocessingError(PreprocessingErrorCode.EXCLUSIONS_TOO_LARGE)
    if payload.startswith(_UTF8_BOM):
        raise PreprocessingError(PreprocessingErrorCode.EXCLUSIONS_INVALID)
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise PreprocessingError(PreprocessingErrorCode.INVALID_UTF8) from None
    if "\r" in text or "\ufeff" in text or unicodedata.normalize("NFC", text) != text:
        raise PreprocessingError(PreprocessingErrorCode.EXCLUSIONS_INVALID)
    accepted: set[str] = set()
    for line in text.split("\n"):
        if not line:
            continue
        prepared_tokens, _ = _tokenize(unicodedata.normalize("NFC", line.lower()))
        if prepared_tokens != (line,) or line.lower() != line:
            raise PreprocessingError(PreprocessingErrorCode.EXCLUSIONS_INVALID)
        if len(line.encode("utf-8")) > MAX_P006_FEATURE_BYTES:
            raise PreprocessingError(PreprocessingErrorCode.EXCLUSIONS_INVALID)
        accepted.add(line)
    return CustomExclusions(
        tokens=tuple(sorted(accepted, key=lambda token: token.encode("utf-8"))),
        source_sha256=hashlib.sha256(payload).hexdigest(),
    )


def build_preprocessing_config(exclusions: CustomExclusions) -> PreprocessingConfigV1:
    return PreprocessingConfigV1(
        schema_version="preprocessing-config-v1",
        profile_id="delta-surface-words-v1",
        intake_profile="ingestion-limits-v1",
        unicode_normalization="NFC",
        lowercase_mode="unicode_str_lower",
        token_profile="letter_sequences_with_following_marks",
        preserve_diacritics=True,
        retain_stopwords=True,
        remove_punctuation=True,
        remove_numbers=True,
        lemmatization=False,
        stemming=False,
        automatic_paratext_removal=False,
        custom_exclusions_sha256=exclusions.source_sha256,
        custom_exclusion_count=len(exclusions.tokens),
        max_candidate_features=MAX_CANDIDATE_FEATURES,
    )


def _candidate_digest(features: tuple[str, ...]) -> str:
    payload = json.dumps(
        features,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_candidate_inventory(
    documents: tuple[PreparedDocument, ...],
    *,
    exclusions: CustomExclusions | None = None,
    max_features: int = MAX_CANDIDATE_FEATURES,
) -> CandidateInventory:
    """Rank features from known independent works before unknown projection."""

    if not 2 <= max_features <= MAX_CANDIDATE_FEATURES:
        raise CandidateInventoryError
    known = tuple(
        document
        for document in documents
        if document.annotation.analysis_role is AnalysisRole.KNOWN
        and document.annotation.text_unit is TextUnit.INDEPENDENT_WORK
    )
    independence_keys = tuple(document.independence_key for document in known)
    if len(independence_keys) != len(set(independence_keys)):
        raise CandidateInventoryError
    aggregate: Counter[str] = Counter()
    for document in known:
        aggregate.update(dict(document.prepared.full_counts))
    excluded = frozenset((exclusions or CustomExclusions((), None)).tokens)
    eligible = {
        token: count
        for token, count in aggregate.items()
        if token not in excluded and len(token.encode("utf-8")) <= MAX_P006_FEATURE_BYTES
    }
    transport_excluded = sum(
        token not in excluded and len(token.encode("utf-8")) > MAX_P006_FEATURE_BYTES
        for token in aggregate
    )
    ranked = tuple(
        token
        for token, _count in sorted(
            eligible.items(),
            key=lambda item: (-item[1], item[0].encode("utf-8")),
        )[:max_features]
    )
    return CandidateInventory(
        features=ranked,
        sha256=_candidate_digest(ranked),
        known_independent_work_count=len(known),
        transport_excluded_feature_count=transport_excluded,
    )


def build_preprocessing_manifest(
    *,
    config: PreprocessingConfigV1,
    annotations: CorpusAnalysisAnnotationsV1,
    documents: tuple[PreparedDocument, ...],
    candidate_inventory: CandidateInventory,
) -> PreprocessingManifestV1:
    if tuple(document.annotation for document in documents) != annotations.annotations:
        raise CandidateInventoryError
    works = tuple(
        WorkPreparationV1(
            document_id=document.annotation.document_id,
            asset_id=document.annotation.asset_id,
            work_id=document.annotation.work_id,
            analysis_role=document.annotation.analysis_role,
            text_unit=document.annotation.text_unit,
            parent_work_id=document.annotation.parent_work_id,
            raw_sha256=document.prepared.raw_sha256,
            prepared_sha256=document.prepared.prepared_sha256,
            raw_byte_count=document.prepared.raw_byte_count,
            prepared_byte_count=document.prepared.prepared_byte_count,
            token_count=document.prepared.token_count,
            unique_token_count=document.prepared.unique_token_count,
            bom_removed=document.prepared.bom_removed,
            newline_replacement_count=document.prepared.newline_replacement_count,
            lowercase_source_count=document.prepared.lowercase_source_count,
            separator_source_count=document.prepared.separator_source_count,
        )
        for document in documents
    )
    return PreprocessingManifestV1(
        schema_version="preprocessing-manifest-v1",
        profile_id=config.profile_id,
        config_sha256=hashlib.sha256(canonical_p007_json(config)).hexdigest(),
        inventory_sha256=annotations.inventory_sha256,
        annotations_sha256=hashlib.sha256(canonical_p007_json(annotations)).hexdigest(),
        candidate_inventory_sha256=candidate_inventory.sha256,
        candidate_feature_count=len(candidate_inventory.features),
        implementation_version=__version__,
        python_version=platform.python_version(),
        unicode_version=unicodedata.unidata_version,
        works=works,
    )


__all__ = [
    "CandidateInventory",
    "CandidateInventoryError",
    "CustomExclusions",
    "PreparedDocument",
    "PreparedText",
    "PreprocessingError",
    "PreprocessingErrorCode",
    "build_candidate_inventory",
    "build_preprocessing_config",
    "build_preprocessing_manifest",
    "parse_custom_exclusions",
    "prepare_document",
    "prepare_text",
]
