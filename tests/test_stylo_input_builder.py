from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

import delta_lemmata.stylo_input_builder as input_builder
from delta_lemmata.corpus_models import PurposeId
from delta_lemmata.preprocessing import (
    CandidateInventory,
    PreparedDocument,
    build_candidate_inventory,
    prepare_document,
)
from delta_lemmata.preprocessing_models import (
    AnalysisPreparationReceiptV1,
    AnalysisRole,
    CorpusAnalysisAnnotation,
    OcrStatus,
    ParatextStatus,
    PreparationState,
    ReceiptDocumentBinding,
    TextUnit,
)
from delta_lemmata.stylo_contracts import DistanceMeasure, DocumentRole
from delta_lemmata.stylo_input_builder import (
    StyloInputBuilderError,
    StyloInputBuilderErrorCode,
)
from delta_lemmata.workflow_models import ResolvedWorkflowConfigV1, resolve_guided_workflow

NOW = datetime(2026, 7, 14, 22, 0, tzinfo=UTC)
REQUEST_ID = "request_" + "9" * 64
REFERENCE_KEY = bytes(range(32))


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _document(index: int, raw: bytes, *, role: AnalysisRole) -> PreparedDocument:
    annotation = CorpusAnalysisAnnotation(
        document_id=f"doc_{index:064x}",
        asset_id=f"asset_work_{index:02d}",
        work_id=f"work_{index:02d}",
        analysis_role=role,
        text_unit=TextUnit.INDEPENDENT_WORK,
        parent_work_id=None,
        ocr_status=OcrStatus.NOT_OCR,
        paratext_status=ParatextStatus.ABSENT,
    )
    return prepare_document(raw, expected_raw_sha256=_sha(raw), annotation=annotation)


def _inputs() -> tuple[
    tuple[PreparedDocument, ...],
    CandidateInventory,
    AnalysisPreparationReceiptV1,
]:
    documents = (
        _document(1, b"alpha alpha beta gamma", role=AnalysisRole.KNOWN),
        _document(2, b"alpha beta beta delta", role=AnalysisRole.KNOWN),
        _document(3, b"alpha unknown unknown", role=AnalysisRole.UNKNOWN),
    )
    candidates = build_candidate_inventory(documents)
    bindings = tuple(
        ReceiptDocumentBinding(
            document_id=document.annotation.document_id,
            asset_id=document.annotation.asset_id,
            work_id=document.annotation.work_id,
            analysis_role=document.annotation.analysis_role,
        )
        for document in documents
    )
    receipt = AnalysisPreparationReceiptV1(
        schema_version="analysis-preparation-receipt-v1",
        receipt_id="receipt_" + "8" * 64,
        state=PreparationState.READY,
        issued_at_utc=NOW,
        expires_at_utc=NOW + timedelta(hours=1),
        admission_nonce_sha256="1" * 64,
        inventory_sha256="2" * 64,
        validation_report_sha256="a" * 64,
        annotations_sha256="3" * 64,
        config_sha256="4" * 64,
        manifest_sha256="5" * 64,
        health_report_sha256="6" * 64,
        candidate_inventory_sha256=candidates.sha256,
        candidate_feature_count=len(candidates.features),
        blocker_count=0,
        ordered_documents=bindings,
    )
    return documents, candidates, receipt


def _workflow(documents: tuple[PreparedDocument, ...]) -> ResolvedWorkflowConfigV1:
    return resolve_guided_workflow(
        purpose=PurposeId.TEXT_PROXIMITY,
        known_work_count=sum(
            document.annotation.analysis_role is AnalysisRole.KNOWN for document in documents
        ),
        unknown_work_count=sum(
            document.annotation.analysis_role is AnalysisRole.UNKNOWN for document in documents
        ),
    )


def _expect_error(
    action: Callable[[], object],
    code: StyloInputBuilderErrorCode,
) -> None:
    with pytest.raises(StyloInputBuilderError) as captured:
        action()
    assert captured.value.code is code
    assert str(captured.value) == code.value
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


def test_guided_builder_preserves_order_counts_roles_and_fixed_alpha_grid() -> None:
    documents, candidates, receipt = _inputs()

    request = input_builder._build_guided_worker_input(
        receipt=receipt,
        documents=documents,
        candidate_inventory=candidates,
        resolved_config=_workflow(documents),
        request_id=REQUEST_ID,
        reference_key=REFERENCE_KEY,
        at_utc=NOW,
    )

    assert request.candidate_features == ("alpha", "beta", "delta", "gamma")
    assert tuple(document.document_id for document in request.documents) == tuple(
        document.annotation.document_id for document in documents
    )
    assert tuple(document.role for document in request.documents) == (
        DocumentRole.KNOWN,
        DocumentRole.KNOWN,
        DocumentRole.UNKNOWN,
    )
    assert request.documents[0].counts == (2, 1, 0, 1)
    assert request.documents[1].counts == (1, 2, 1, 0)
    assert request.documents[2].counts == (1, 0, 0, 0)
    assert tuple((fit.mfw, fit.culling_percent) for fit in request.fits) == (
        (100, 0),
        (300, 0),
        (500, 0),
        (1000, 0),
    )
    assert tuple(cell.distance for cell in request.cells) == (DistanceMeasure.CLASSIC_DELTA,) * 4
    assert {cell.fit_id for cell in request.cells} == {fit.fit_id for fit in request.fits}
    assert all(
        document.asset_ref != source.annotation.asset_id
        for document, source in zip(request.documents, documents, strict=True)
    )
    assert all(
        document.work_ref != source.annotation.work_id
        for document, source in zip(request.documents, documents, strict=True)
    )

    repeated = input_builder._build_guided_worker_input(
        receipt=receipt,
        documents=documents,
        candidate_inventory=candidates,
        resolved_config=_workflow(documents),
        request_id=REQUEST_ID,
        reference_key=REFERENCE_KEY,
        at_utc=NOW,
    )
    assert repeated == request

    unlinked = input_builder._build_guided_worker_input(
        receipt=receipt,
        documents=documents,
        candidate_inventory=candidates,
        resolved_config=_workflow(documents),
        request_id=REQUEST_ID,
        reference_key=bytes(reversed(range(32))),
        at_utc=NOW,
    )
    assert tuple(document.asset_ref for document in unlinked.documents) != tuple(
        document.asset_ref for document in request.documents
    )
    assert tuple(document.work_ref for document in unlinked.documents) != tuple(
        document.work_ref for document in request.documents
    )
    assert tuple(fit.fit_id for fit in unlinked.fits) != tuple(fit.fit_id for fit in request.fits)
    assert tuple(cell.cell_id for cell in unlinked.cells) != tuple(
        cell.cell_id for cell in request.cells
    )


def test_builder_rejects_invalid_request_not_ready_and_binding_mutations() -> None:
    documents, candidates, receipt = _inputs()
    _expect_error(
        lambda: input_builder._build_guided_worker_input(
            receipt=object(),  # type: ignore[arg-type]
            documents=documents,
            candidate_inventory=candidates,
            resolved_config=_workflow(documents),
            request_id=REQUEST_ID,
            reference_key=REFERENCE_KEY,
            at_utc=NOW,
        ),
        StyloInputBuilderErrorCode.INVALID_REQUEST,
    )
    _expect_error(
        lambda: input_builder._build_guided_worker_input(
            receipt=receipt,
            documents=documents,
            candidate_inventory=candidates,
            resolved_config=_workflow(documents),
            request_id=REQUEST_ID,
            reference_key=b"too-short",
            at_utc=NOW,
        ),
        StyloInputBuilderErrorCode.INVALID_REQUEST,
    )
    _expect_error(
        lambda: input_builder._build_guided_worker_input(
            receipt=receipt,
            documents=documents,
            candidate_inventory=candidates,
            resolved_config=_workflow(documents),
            request_id="request-invalid",
            reference_key=REFERENCE_KEY,
            at_utc=NOW,
        ),
        StyloInputBuilderErrorCode.INVALID_REQUEST,
    )
    blocked = receipt.model_copy(update={"state": "BLOCKED"})
    _expect_error(
        lambda: input_builder._build_guided_worker_input(
            receipt=blocked,
            documents=documents,
            candidate_inventory=candidates,
            resolved_config=_workflow(documents),
            request_id=REQUEST_ID,
            reference_key=REFERENCE_KEY,
            at_utc=NOW,
        ),
        StyloInputBuilderErrorCode.NOT_READY,
    )
    _expect_error(
        lambda: input_builder._build_guided_worker_input(
            receipt=receipt,
            documents=tuple(reversed(documents)),
            candidate_inventory=candidates,
            resolved_config=_workflow(documents),
            request_id=REQUEST_ID,
            reference_key=REFERENCE_KEY,
            at_utc=NOW,
        ),
        StyloInputBuilderErrorCode.BINDING_MISMATCH,
    )


def test_builder_binds_the_exact_resolved_workflow_to_document_roles() -> None:
    documents, candidates, receipt = _inputs()
    wrong_counts = _workflow(documents).model_copy(update={"unknown_work_count": 0})

    _expect_error(
        lambda: input_builder._build_guided_worker_input(
            receipt=receipt,
            documents=documents,
            candidate_inventory=candidates,
            resolved_config=wrong_counts,
            request_id=REQUEST_ID,
            reference_key=REFERENCE_KEY,
            at_utc=NOW,
        ),
        StyloInputBuilderErrorCode.BINDING_MISMATCH,
    )
    _expect_error(
        lambda: input_builder._build_guided_worker_input(
            receipt=receipt,
            documents=documents,
            candidate_inventory=candidates,
            resolved_config=object(),  # type: ignore[arg-type]
            request_id=REQUEST_ID,
            reference_key=REFERENCE_KEY,
            at_utc=NOW,
        ),
        StyloInputBuilderErrorCode.INVALID_REQUEST,
    )
    changed_hash = receipt.model_copy(update={"candidate_inventory_sha256": "f" * 64})
    _expect_error(
        lambda: input_builder._build_guided_worker_input(
            receipt=changed_hash,
            documents=documents,
            candidate_inventory=candidates,
            resolved_config=_workflow(documents),
            request_id=REQUEST_ID,
            reference_key=REFERENCE_KEY,
            at_utc=NOW,
        ),
        StyloInputBuilderErrorCode.BINDING_MISMATCH,
    )


@pytest.mark.parametrize(
    ("at_utc", "expected_code"),
    [
        (datetime(2026, 7, 14, 22, 0), StyloInputBuilderErrorCode.INVALID_REQUEST),
        (NOW - timedelta(microseconds=1), StyloInputBuilderErrorCode.NOT_READY),
        (NOW + timedelta(hours=1), StyloInputBuilderErrorCode.NOT_READY),
        (NOW + timedelta(hours=1, microseconds=1), StyloInputBuilderErrorCode.NOT_READY),
    ],
)
def test_builder_enforces_utc_and_receipt_validity_window(
    at_utc: datetime,
    expected_code: StyloInputBuilderErrorCode,
) -> None:
    documents, candidates, receipt = _inputs()

    _expect_error(
        lambda: input_builder._build_guided_worker_input(
            receipt=receipt,
            documents=documents,
            candidate_inventory=candidates,
            resolved_config=_workflow(documents),
            request_id=REQUEST_ID,
            reference_key=REFERENCE_KEY,
            at_utc=at_utc,
        ),
        expected_code,
    )


def test_opaque_reference_framing_and_domains_are_distinct() -> None:
    assert input_builder._opaque_reference(REFERENCE_KEY, "asset", "ab", "c") != (
        input_builder._opaque_reference(REFERENCE_KEY, "asset", "a", "bc")
    )
    assert input_builder._opaque_reference(REFERENCE_KEY, "asset", "same") != (
        input_builder._opaque_reference(REFERENCE_KEY, "work", "same")
    )


def test_private_text_features_and_count_rows_are_absent_from_repr() -> None:
    documents, candidates, receipt = _inputs()
    request = input_builder._build_guided_worker_input(
        receipt=receipt,
        documents=documents,
        candidate_inventory=candidates,
        resolved_config=_workflow(documents),
        request_id=REQUEST_ID,
        reference_key=REFERENCE_KEY,
        at_utc=NOW,
    )

    for value in (documents, candidates, request):
        rendered = repr(value)
        for private_token in ("alpha", "beta", "gamma", "delta"):
            assert repr(private_token) not in rendered


@pytest.mark.parametrize(
    "mutation", ["counts", "bytes", "candidate-hash", "candidate-order", "known-count"]
)
def test_builder_rechecks_private_preparation_and_candidate_integrity(mutation: str) -> None:
    documents, candidates, receipt = _inputs()
    changed_documents = documents
    changed_candidates = candidates
    if mutation == "counts":
        prepared = replace(documents[0].prepared, full_counts=(("alpha", 99),))
        changed_documents = (replace(documents[0], prepared=prepared), *documents[1:])
    elif mutation == "bytes":
        prepared = replace(documents[0].prepared, prepared_bytes=b"private mutation\n")
        changed_documents = (replace(documents[0], prepared=prepared), *documents[1:])
    elif mutation == "candidate-hash":
        changed_candidates = replace(candidates, sha256="f" * 64)
    elif mutation == "candidate-order":
        features = tuple(reversed(candidates.features))
        payload = json.dumps(features, ensure_ascii=False, separators=(",", ":")).encode()
        changed_candidates = replace(
            candidates,
            features=features,
            sha256=hashlib.sha256(payload).hexdigest(),
        )
    else:
        changed_candidates = replace(candidates, known_independent_work_count=1)

    _expect_error(
        lambda: input_builder._build_guided_worker_input(
            receipt=receipt,
            documents=changed_documents,
            candidate_inventory=changed_candidates,
            resolved_config=_workflow(documents),
            request_id=REQUEST_ID,
            reference_key=REFERENCE_KEY,
            at_utc=NOW,
        ),
        StyloInputBuilderErrorCode.INTEGRITY,
    )


def test_builder_detaches_unexpected_private_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    documents, candidates, receipt = _inputs()

    def fail_reference(_key: bytes, _prefix: str, *_values: str) -> str:
        raise RuntimeError("private builder content")

    monkeypatch.setattr(input_builder, "_opaque_reference", fail_reference)
    _expect_error(
        lambda: input_builder._build_guided_worker_input(
            receipt=receipt,
            documents=documents,
            candidate_inventory=candidates,
            resolved_config=_workflow(documents),
            request_id=REQUEST_ID,
            reference_key=REFERENCE_KEY,
            at_utc=NOW,
        ),
        StyloInputBuilderErrorCode.OPERATION_FAILED,
    )
