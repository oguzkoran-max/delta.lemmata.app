from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from delta_lemmata.corpus_health_models import CorpusHealthReportV1
from delta_lemmata.preprocessing import build_preprocessing_config, parse_custom_exclusions
from delta_lemmata.preprocessing_models import (
    AnalysisPreparationReceiptV1,
    CorpusAnalysisAnnotationsV1,
    P007ContractError,
    P007ContractErrorCode,
    PreprocessingConfigV1,
    PreprocessingManifestV1,
    ReceiptDocumentBinding,
    canonical_p007_json,
    export_p007_schema,
    parse_analysis_preparation_receipt,
    parse_preprocessing_config,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def _read_json(path: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


@pytest.mark.parametrize(
    ("schema_name", "model"),
    [
        ("preprocessing-config-v1", PreprocessingConfigV1),
        ("corpus-analysis-annotations-v1", CorpusAnalysisAnnotationsV1),
        ("preprocessing-manifest-v1", PreprocessingManifestV1),
        ("corpus-health-report-v1", CorpusHealthReportV1),
        ("analysis-preparation-receipt-v1", AnalysisPreparationReceiptV1),
    ],
)
def test_p007_checked_in_schemas_match_closed_models(
    schema_name: str,
    model: type[Any],
) -> None:
    schema_id = f"https://delta.lemmata.app/schemas/{schema_name}.schema.json"
    assert _read_json(SCHEMAS / f"{schema_name}.schema.json") == export_p007_schema(
        model,
        schema_id,
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


def test_p007_parser_rejects_duplicate_keys_nonfinite_unknown_and_oversized() -> None:
    config = build_preprocessing_config(parse_custom_exclusions(None))
    assert parse_preprocessing_config(canonical_p007_json(config)) == config

    cases = (
        (
            b'{"schema_version":"preprocessing-config-v1","schema_version":"x"}',
            P007ContractErrorCode.DUPLICATE_KEY,
        ),
        (b'{"x":NaN}', P007ContractErrorCode.NON_FINITE_NUMBER),
        (b'{"unexpected":true}', P007ContractErrorCode.SCHEMA_INVALID),
        (b"", P007ContractErrorCode.PAYLOAD_EMPTY),
        (b"\xff", P007ContractErrorCode.INVALID_UTF8),
    )
    for payload, code in cases:
        with pytest.raises(P007ContractError) as captured:
            parse_preprocessing_config(payload)
        assert captured.value.code is code


def test_ready_receipt_is_closed_hash_bound_and_expires_within_one_hour() -> None:
    receipt = _receipt()
    assert parse_analysis_preparation_receipt(canonical_p007_json(receipt)) == receipt

    with pytest.raises(ValueError):
        receipt.model_copy(
            update={"expires_at_utc": receipt.issued_at_utc + timedelta(hours=2)}
        ).__class__.model_validate(
            {
                **receipt.model_dump(mode="python"),
                "expires_at_utc": receipt.issued_at_utc + timedelta(hours=2),
            }
        )

    with pytest.raises(ValueError):
        AnalysisPreparationReceiptV1.model_validate(
            {**receipt.model_dump(mode="python"), "blocker_count": 1}
        )
