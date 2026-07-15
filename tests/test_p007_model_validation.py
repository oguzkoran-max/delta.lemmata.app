from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from delta_lemmata.corpus import PurposeId
from delta_lemmata.corpus_health_models import (
    CorpusHealthFinding,
    CorpusHealthFindingCode,
    CorpusHealthReadiness,
    CorpusHealthReportV1,
    HealthSeverity,
    MfwCapacity,
    parse_corpus_health_report,
)
from delta_lemmata.preprocessing import build_preprocessing_config, parse_custom_exclusions
from delta_lemmata.preprocessing_models import (
    AnalysisPreparationReceiptV1,
    AnalysisRole,
    CorpusAnalysisAnnotation,
    CorpusAnalysisAnnotationsV1,
    OcrStatus,
    P007ContractError,
    P007ContractErrorCode,
    ParatextStatus,
    PreprocessingManifestV1,
    ReceiptDocumentBinding,
    TextUnit,
    WorkPreparationV1,
    canonical_p007_json,
    parse_corpus_analysis_annotations,
    parse_p007_payload,
    parse_preprocessing_config,
    parse_preprocessing_manifest,
)


def _annotation(index: int) -> CorpusAnalysisAnnotation:
    return CorpusAnalysisAnnotation(
        document_id=f"doc_{index:064x}",
        asset_id=f"asset_work_{index:02d}",
        work_id=f"work_{index:02d}",
        analysis_role=AnalysisRole.KNOWN,
        text_unit=TextUnit.INDEPENDENT_WORK,
        parent_work_id=None,
        ocr_status=OcrStatus.NOT_OCR,
        paratext_status=ParatextStatus.ABSENT,
    )


def _work(index: int) -> WorkPreparationV1:
    annotation = _annotation(index)
    return WorkPreparationV1(
        document_id=annotation.document_id,
        asset_id=annotation.asset_id,
        work_id=annotation.work_id,
        analysis_role=annotation.analysis_role,
        text_unit=annotation.text_unit,
        parent_work_id=None,
        raw_sha256=f"{index:x}" * 64,
        prepared_sha256=f"{index + 2:x}" * 64,
        raw_byte_count=10,
        prepared_byte_count=9,
        token_count=2,
        unique_token_count=2,
        bom_removed=False,
        newline_replacement_count=0,
        lowercase_source_count=0,
        separator_source_count=1,
    )


def _manifest() -> PreprocessingManifestV1:
    return PreprocessingManifestV1(
        schema_version="preprocessing-manifest-v1",
        profile_id="delta-surface-words-v1",
        config_sha256="1" * 64,
        inventory_sha256="2" * 64,
        annotations_sha256="3" * 64,
        candidate_inventory_sha256="4" * 64,
        candidate_feature_count=2,
        implementation_version="0.1.0",
        python_version="3.13.9",
        unicode_version="16.0.0",
        works=(_work(1), _work(2)),
    )


def _receipt() -> AnalysisPreparationReceiptV1:
    issued = datetime(2026, 7, 14, 20, 0, tzinfo=UTC)
    return AnalysisPreparationReceiptV1(
        schema_version="analysis-preparation-receipt-v1",
        receipt_id="receipt_" + ("1" * 64),
        state="READY",
        issued_at_utc=issued,
        expires_at_utc=issued + timedelta(minutes=30),
        admission_nonce_sha256="2" * 64,
        inventory_sha256="3" * 64,
        validation_report_sha256="b" * 64,
        annotations_sha256="4" * 64,
        config_sha256="5" * 64,
        manifest_sha256="6" * 64,
        health_report_sha256="7" * 64,
        candidate_inventory_sha256="8" * 64,
        candidate_feature_count=100,
        blocker_count=0,
        ordered_documents=(
            ReceiptDocumentBinding(
                document_id="doc_" + ("9" * 64),
                asset_id="asset_work_01",
                work_id="work_01",
                analysis_role="known",
            ),
            ReceiptDocumentBinding(
                document_id="doc_" + ("a" * 64),
                asset_id="asset_work_02",
                work_id="work_02",
                analysis_role="known",
            ),
        ),
    )


def _report() -> CorpusHealthReportV1:
    capacities = tuple(
        MfwCapacity(requested_mfw=value, available_features=10, available=False)
        for value in (100, 300, 500, 1000)
    )
    return CorpusHealthReportV1(
        schema_version="corpus-health-report-v1",
        report_id="health_" + ("1" * 64),
        severity_profile="delta-corpus-health-v1",
        purpose=PurposeId.TEXT_PROXIMITY,
        config_sha256="2" * 64,
        inventory_sha256="3" * 64,
        annotations_sha256="4" * 64,
        manifest_sha256="5" * 64,
        candidate_inventory_sha256="6" * 64,
        candidate_feature_count=10,
        independent_work_count=2,
        known_independent_work_count=2,
        chronology_point_count=0,
        readiness=CorpusHealthReadiness.READY,
        blocker_count=0,
        strong_warning_count=0,
        note_count=0,
        mfw_capacity=capacities,
        findings=(),
    )


def _validate(model: type, instance: object, **updates: object) -> object:
    data = instance.model_dump(mode="python")  # type: ignore[attr-defined]
    data.update(updates)
    return model.model_validate(data)


def test_config_annotation_and_annotation_set_semantics_are_closed() -> None:
    config = build_preprocessing_config(parse_custom_exclusions(None))
    with pytest.raises(ValueError):
        _validate(config.__class__, config, custom_exclusion_count=1)

    annotation = _annotation(1)
    with pytest.raises(ValueError):
        _validate(annotation.__class__, annotation, parent_work_id="work_parent")
    for parent in (None, annotation.work_id):
        with pytest.raises(ValueError):
            _validate(
                annotation.__class__,
                annotation,
                text_unit=TextUnit.SEGMENT,
                parent_work_id=parent,
            )
    for note in ("e\u0301", "line\nbreak"):
        with pytest.raises(ValueError):
            _validate(annotation.__class__, annotation, preupload_curation_note=note)
    accepted = _validate(
        annotation.__class__,
        annotation,
        preupload_curation_note="Front matter reviewed before upload",
    )
    assert accepted.preupload_curation_note == "Front matter reviewed before upload"

    second = _annotation(2)
    annotations = CorpusAnalysisAnnotationsV1(
        schema_version="corpus-analysis-annotations-v1",
        inventory_sha256="a" * 64,
        annotations=(annotation, second),
    )
    for field in ("document_id", "asset_id"):
        duplicate = second.model_copy(update={field: getattr(annotation, field)})
        with pytest.raises(ValueError):
            _validate(annotations.__class__, annotations, annotations=(annotation, duplicate))


def test_work_manifest_and_receipt_bindings_fail_closed() -> None:
    work = _work(1)
    with pytest.raises(ValueError):
        _validate(work.__class__, work, token_count=1, unique_token_count=2)
    with pytest.raises(ValueError):
        _validate(work.__class__, work, parent_work_id="work_parent")
    with pytest.raises(ValueError):
        _validate(work.__class__, work, text_unit=TextUnit.EXCERPT, parent_work_id=None)
    with pytest.raises(ValueError):
        _validate(
            work.__class__,
            work,
            text_unit=TextUnit.EXCERPT,
            parent_work_id=work.work_id,
        )

    manifest = _manifest()
    first, second = manifest.works
    for field in ("document_id", "asset_id"):
        duplicate = second.model_copy(update={field: getattr(first, field)})
        with pytest.raises(ValueError):
            _validate(manifest.__class__, manifest, works=(first, duplicate))

    receipt = _receipt()
    offset = timezone(timedelta(hours=1))
    with pytest.raises(ValueError):
        _validate(
            receipt.__class__, receipt, issued_at_utc=receipt.issued_at_utc.astimezone(offset)
        )
    with pytest.raises(ValueError):
        _validate(
            receipt.__class__,
            receipt,
            expires_at_utc=receipt.expires_at_utc.astimezone(offset),
        )
    first_binding, second_binding = receipt.ordered_documents
    for field in ("document_id", "asset_id", "work_id"):
        duplicate = second_binding.model_copy(update={field: getattr(first_binding, field)})
        with pytest.raises(ValueError):
            _validate(
                receipt.__class__,
                receipt,
                ordered_documents=(first_binding, duplicate),
            )
    with pytest.raises(ValueError):
        _validate(
            receipt.__class__,
            receipt,
            ordered_documents=(
                first_binding,
                second_binding.model_copy(update={"analysis_role": AnalysisRole.UNKNOWN}),
            ),
        )


def test_contract_parser_classifies_structural_failures_and_all_wrappers() -> None:
    cases = (
        ("not-bytes", P007ContractErrorCode.PAYLOAD_TYPE),
        (b"{" + (b" " * (64 * 1024)), P007ContractErrorCode.PAYLOAD_TOO_LARGE),
        (b"{", P007ContractErrorCode.INVALID_JSON),
        (b'{"x":1e309}', P007ContractErrorCode.NON_FINITE_NUMBER),
        (b'{"x":' + (b"9" * 400) + b"}", P007ContractErrorCode.NUMBER_OUT_OF_RANGE),
        (b'{"x":"\\ud800"}', P007ContractErrorCode.INVALID_UNICODE),
    )
    for payload, code in cases:
        with pytest.raises(P007ContractError) as captured:
            parse_preprocessing_config(payload)  # type: ignore[arg-type]
        assert captured.value.code is code

    annotations = CorpusAnalysisAnnotationsV1(
        schema_version="corpus-analysis-annotations-v1",
        inventory_sha256="a" * 64,
        annotations=(_annotation(1), _annotation(2)),
    )
    manifest = _manifest()
    assert parse_corpus_analysis_annotations(canonical_p007_json(annotations)) == annotations
    assert parse_preprocessing_manifest(canonical_p007_json(manifest)) == manifest
    with pytest.raises(P007ContractError):
        parse_p007_payload(b"{}", model=CorpusAnalysisAnnotationsV1)


def test_health_report_model_rejects_inconsistent_summaries() -> None:
    with pytest.raises(ValueError):
        MfwCapacity(requested_mfw=100, available_features=99, available=True)

    report = _report()
    with pytest.raises(ValueError):
        _validate(report.__class__, report, mfw_capacity=tuple(reversed(report.mfw_capacity)))

    finding = CorpusHealthFinding(
        finding_id="finding_" + ("1" * 64),
        code=CorpusHealthFindingCode.PREPARATION_SUMMARY,
        severity=HealthSeverity.NOTE,
    )
    with pytest.raises(ValueError):
        _validate(report.__class__, report, findings=(finding, finding), note_count=2)
    with pytest.raises(ValueError):
        _validate(report.__class__, report, note_count=1)
    with pytest.raises(ValueError):
        _validate(report.__class__, report, readiness=CorpusHealthReadiness.BLOCKED)
    with pytest.raises(ValueError):
        _validate(
            report.__class__,
            report,
            independent_work_count=1,
            known_independent_work_count=2,
        )

    assert parse_corpus_health_report(canonical_p007_json(report)) == report
