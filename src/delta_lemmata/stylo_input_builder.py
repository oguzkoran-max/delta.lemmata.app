"""Private P007-to-P006 Guided input construction with closed bindings."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from functools import wraps

from pydantic import ValidationError

from delta_lemmata.clock import require_utc
from delta_lemmata.preprocessing import CandidateInventory, PreparedDocument
from delta_lemmata.preprocessing_models import (
    AnalysisPreparationReceiptV1,
    AnalysisRole,
    PreparationState,
    ReceiptDocumentBinding,
    TextUnit,
)
from delta_lemmata.stylo_contracts import (
    MAX_FEATURE_BYTES,
    MAX_FEATURES,
    MAX_TOKEN_COUNT,
    CellRequest,
    DocumentCounts,
    DocumentRole,
    FitRequest,
    WorkerInputV1,
)
from delta_lemmata.workflow_models import ResolvedWorkflowConfigV1

_REQUEST_ID = re.compile(r"^request_[0-9a-f]{64}$", flags=re.ASCII)
_OPAQUE_DOMAIN = b"delta-lemmata\x00p007-p006-opaque-reference\x00v1\x00"
_REFERENCE_KEY_BYTES = 32


class StyloInputBuilderErrorCode(StrEnum):
    INVALID_REQUEST = "P007_STYLO_INPUT_INVALID_REQUEST"
    NOT_READY = "P007_STYLO_INPUT_NOT_READY"
    BINDING_MISMATCH = "P007_STYLO_INPUT_BINDING_MISMATCH"
    INTEGRITY = "P007_STYLO_INPUT_INTEGRITY"
    OPERATION_FAILED = "P007_STYLO_INPUT_OPERATION_FAILED"


class StyloInputBuilderError(RuntimeError):
    """Content-free rejection at the private P007-to-P006 boundary."""

    def __init__(self, code: StyloInputBuilderErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


def _detach(error: StyloInputBuilderError) -> None:
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True


def _error(code: StyloInputBuilderErrorCode) -> StyloInputBuilderError:
    error = StyloInputBuilderError(code)
    _detach(error)
    return error


def _content_free[**P, ResultT](function: Callable[P, ResultT]) -> Callable[P, ResultT]:
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResultT:
        try:
            return function(*args, **kwargs)
        except StyloInputBuilderError as error:
            rejection = error
        except Exception:
            rejection = StyloInputBuilderError(StyloInputBuilderErrorCode.OPERATION_FAILED)
        _detach(rejection)
        raise rejection

    return wrapped


def _candidate_sha256(features: tuple[str, ...]) -> str:
    payload = json.dumps(features, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _opaque_reference(reference_key: bytes, prefix: str, *values: str) -> str:
    prefix_bytes = prefix.encode("ascii")
    framed = bytearray(_OPAQUE_DOMAIN)
    for value in (prefix_bytes, *(item.encode("utf-8", errors="strict") for item in values)):
        framed.extend(len(value).to_bytes(4, byteorder="big"))
        framed.extend(value)
    digest = hmac.new(reference_key, framed, hashlib.sha256).hexdigest()
    return f"{prefix}_{digest}"


def _document_binding(document: PreparedDocument) -> ReceiptDocumentBinding:
    annotation = document.annotation
    return ReceiptDocumentBinding(
        document_id=annotation.document_id,
        asset_id=annotation.asset_id,
        work_id=annotation.work_id,
        analysis_role=annotation.analysis_role,
    )


def _verify_document(document: PreparedDocument) -> None:
    prepared = document.prepared
    counts = Counter(prepared.tokens)
    expected_counts = tuple(sorted(counts.items(), key=lambda item: item[0].encode("utf-8")))
    expected_bytes = (" ".join(prepared.tokens) + "\n").encode("utf-8")
    if (
        document.annotation.text_unit is not TextUnit.INDEPENDENT_WORK
        or document.annotation.parent_work_id is not None
        or prepared.token_count == 0
        or prepared.token_count > MAX_TOKEN_COUNT
        or prepared.token_count != len(prepared.tokens)
        or prepared.unique_token_count != len(counts)
        or prepared.full_counts != expected_counts
        or prepared.prepared_bytes != expected_bytes
        or prepared.prepared_byte_count != len(expected_bytes)
        or hashlib.sha256(expected_bytes).hexdigest() != prepared.prepared_sha256
    ):
        raise _error(StyloInputBuilderErrorCode.INTEGRITY)


def _verify_candidate_inventory(
    documents: tuple[PreparedDocument, ...],
    candidate_inventory: CandidateInventory,
) -> None:
    features = candidate_inventory.features
    if (
        len(features) < 2
        or len(features) > MAX_FEATURES
        or len(features) != len(set(features))
        or any(
            not isinstance(feature, str)
            or not feature
            or unicodedata.normalize("NFC", feature) != feature
            or len(feature.encode("utf-8")) > MAX_FEATURE_BYTES
            or any(ord(character) < 32 or 127 <= ord(character) <= 159 for character in feature)
            for feature in features
        )
        or candidate_inventory.sha256 != _candidate_sha256(features)
    ):
        raise _error(StyloInputBuilderErrorCode.INTEGRITY)
    known = tuple(
        document
        for document in documents
        if document.annotation.analysis_role is AnalysisRole.KNOWN
    )
    aggregate: Counter[str] = Counter()
    for document in known:
        aggregate.update(dict(document.prepared.full_counts))
    ranked = tuple(
        sorted(
            features,
            key=lambda feature: (-aggregate[feature], feature.encode("utf-8")),
        )
    )
    if (
        candidate_inventory.known_independent_work_count != len(known)
        or ranked != features
        or any(aggregate[feature] <= 0 for feature in features)
    ):
        raise _error(StyloInputBuilderErrorCode.INTEGRITY)


def _fit_id(
    reference_key: bytes,
    request_id: str,
    mfw: int,
    culling_percent: int,
) -> str:
    return _opaque_reference(
        reference_key,
        "fit",
        request_id,
        str(mfw),
        str(culling_percent),
    )


@_content_free
def _build_guided_worker_input(
    *,
    receipt: AnalysisPreparationReceiptV1,
    documents: tuple[PreparedDocument, ...],
    candidate_inventory: CandidateInventory,
    resolved_config: ResolvedWorkflowConfigV1,
    request_id: str,
    reference_key: bytes,
    at_utc: datetime,
) -> WorkerInputV1:
    """Build the accepted alpha grid only after all private bindings are rechecked."""

    if (
        not isinstance(receipt, AnalysisPreparationReceiptV1)
        or not isinstance(documents, tuple)
        or not all(isinstance(document, PreparedDocument) for document in documents)
        or not isinstance(candidate_inventory, CandidateInventory)
        or not isinstance(resolved_config, ResolvedWorkflowConfigV1)
        or not isinstance(request_id, str)
        or _REQUEST_ID.fullmatch(request_id) is None
        or not isinstance(reference_key, bytes)
        or len(reference_key) != _REFERENCE_KEY_BYTES
        or not isinstance(at_utc, datetime)
    ):
        raise _error(StyloInputBuilderErrorCode.INVALID_REQUEST)
    try:
        now = require_utc(at_utc, field_name="P007 admission time")
    except Exception:
        raise _error(StyloInputBuilderErrorCode.INVALID_REQUEST) from None
    if receipt.state is not PreparationState.READY or receipt.blocker_count != 0:
        raise _error(StyloInputBuilderErrorCode.NOT_READY)
    if now < receipt.issued_at_utc or now >= receipt.expires_at_utc:
        raise _error(StyloInputBuilderErrorCode.NOT_READY)
    bindings = tuple(_document_binding(document) for document in documents)
    if bindings != receipt.ordered_documents:
        raise _error(StyloInputBuilderErrorCode.BINDING_MISMATCH)
    for document in documents:
        _verify_document(document)
    _verify_candidate_inventory(documents, candidate_inventory)
    try:
        checked_config = ResolvedWorkflowConfigV1.model_validate(
            resolved_config.model_dump(mode="python")
        )
    except ValidationError:
        raise _error(StyloInputBuilderErrorCode.BINDING_MISMATCH) from None
    known_count = sum(
        document.annotation.analysis_role is AnalysisRole.KNOWN for document in documents
    )
    unknown_count = sum(
        document.annotation.analysis_role is AnalysisRole.UNKNOWN for document in documents
    )
    if (
        receipt.candidate_inventory_sha256 != candidate_inventory.sha256
        or receipt.candidate_feature_count != len(candidate_inventory.features)
        or checked_config != resolved_config
        or resolved_config.known_work_count != known_count
        or resolved_config.unknown_work_count != unknown_count
    ):
        raise _error(StyloInputBuilderErrorCode.BINDING_MISMATCH)

    features = candidate_inventory.features
    document_rows = tuple(
        DocumentCounts(
            document_id=document.annotation.document_id,
            asset_ref=_opaque_reference(
                reference_key,
                "asset",
                receipt.inventory_sha256,
                document.annotation.asset_id,
                document.prepared.raw_sha256,
            ),
            work_ref=_opaque_reference(
                reference_key,
                "work",
                receipt.inventory_sha256,
                document.annotation.work_id,
            ),
            role=(
                DocumentRole.KNOWN
                if document.annotation.analysis_role is AnalysisRole.KNOWN
                else DocumentRole.UNKNOWN
            ),
            token_total=document.prepared.token_count,
            counts=tuple(
                dict(document.prepared.full_counts).get(feature, 0) for feature in features
            ),
        )
        for document in documents
    )
    fit_keys = tuple(
        dict.fromkeys((cell.mfw, cell.culling_percent) for cell in resolved_config.cells)
    )
    fits = tuple(
        FitRequest(
            fit_id=_fit_id(reference_key, request_id, mfw, culling_percent),
            mfw=mfw,
            culling_percent=culling_percent,
        )
        for mfw, culling_percent in fit_keys
    )
    fit_ids = {(fit.mfw, fit.culling_percent): fit.fit_id for fit in fits}
    cells = tuple(
        CellRequest(
            cell_id=_opaque_reference(
                reference_key,
                "cell",
                request_id,
                fit_ids[(cell.mfw, cell.culling_percent)],
                cell.distance.value,
            ),
            fit_id=fit_ids[(cell.mfw, cell.culling_percent)],
            distance=cell.distance,
        )
        for cell in resolved_config.cells
    )
    return WorkerInputV1(
        schema_version="stylo-worker-input-v1",
        request_id=request_id,
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit=resolved_config.analysis_unit,
        seed=resolved_config.seed,
        candidate_features=features,
        documents=document_rows,
        fits=fits,
        cells=cells,
    )


__all__ = [
    "StyloInputBuilderError",
    "StyloInputBuilderErrorCode",
]
