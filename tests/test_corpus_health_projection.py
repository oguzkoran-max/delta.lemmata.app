from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

import pytest
from pydantic import ValidationError

import delta_lemmata.corpus_health_projection as projection_module
from delta_lemmata.corpus import (
    CorpusInventory,
    DateMode,
    DateValue,
    TermKind,
    VocabularyTerm,
    inventory_sha256,
)
from delta_lemmata.corpus_health import WorkHealthContext, assess_corpus_health
from delta_lemmata.corpus_health_models import CorpusHealthFindingCode
from delta_lemmata.corpus_health_projection import (
    ConfoundDatum,
    CorpusHealthProjection,
    CorpusHealthProjectionError,
    CorpusHealthProjectionErrorCode,
    OverlapDatum,
    build_corpus_health_projection,
    export_confound_matrix_csv,
    export_feature_capacity_csv,
    export_health_findings_csv,
    export_work_preparation_csv,
)
from delta_lemmata.ingestion import IntakeError, IntakeErrorCode
from delta_lemmata.preprocessing import (
    build_candidate_inventory,
    build_preprocessing_config,
    build_preprocessing_manifest,
    parse_custom_exclusions,
    prepare_document,
)
from delta_lemmata.preprocessing_models import (
    AnalysisRole,
    CorpusAnalysisAnnotation,
    CorpusAnalysisAnnotationsV1,
    OcrStatus,
    ParatextStatus,
    TextUnit,
    canonical_p007_json,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "p004"


def _word(prefix: str, index: int) -> str:
    suffix = ""
    value = index
    while True:
        suffix = chr(ord("a") + (value % 26)) + suffix
        value = (value // 26) - 1
        if value < 0:
            return prefix + suffix


def _rows(payload: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(payload.decode("utf-8"), newline="")))


def _rebind(inventory, annotations, manifest, health):
    digest = inventory_sha256(inventory)
    rebound_annotations = annotations.model_copy(update={"inventory_sha256": digest})
    annotations_sha256 = hashlib.sha256(canonical_p007_json(rebound_annotations)).hexdigest()
    rebound_manifest = manifest.model_copy(
        update={
            "inventory_sha256": digest,
            "annotations_sha256": annotations_sha256,
        }
    )
    manifest_sha256 = hashlib.sha256(canonical_p007_json(rebound_manifest)).hexdigest()
    rebound_health = health.model_copy(
        update={
            "inventory_sha256": digest,
            "annotations_sha256": annotations_sha256,
            "manifest_sha256": manifest_sha256,
        }
    )
    return rebound_annotations, rebound_manifest, rebound_health


def _artifacts():
    base = CorpusInventory.model_validate_json(
        (FIXTURES / "inventory-valid-text-proximity.json").read_text(encoding="utf-8")
    )
    shared = [_word("shared", index) for index in range(20)]
    raw_a = " ".join((*shared, *(_word("alpha", index) for index in range(80)))).encode()
    raw_b = " ".join((*shared, *(_word("beta", index) for index in range(80)))).encode()
    sha_a = hashlib.sha256(raw_a).hexdigest()
    sha_b = hashlib.sha256(raw_b).hexdigest()

    first_work = base.works[0].model_copy(
        update={
            "work_id": "work_early",
            "title_original": "=Private early title",
            "first_publication": DateValue(mode=DateMode.EXACT, start_year=1883),
        }
    )
    second_work = base.works[0].model_copy(
        update={
            "work_id": "work_late",
            "title_original": "Private later title",
            "first_publication": DateValue(mode=DateMode.APPROXIMATE, start_year=1900),
            "genre": VocabularyTerm(
                value="short_story",
                label="Short story",
                kind=TermKind.CUSTOM,
            ),
            "audience": VocabularyTerm(
                value="children",
                label="Children",
                kind=TermKind.CUSTOM,
            ),
            "adaptation": VocabularyTerm(
                value="adapted",
                label="Adapted",
                kind=TermKind.CUSTOM,
            ),
            "collection": VocabularyTerm(
                value="collection",
                label="Collection",
                kind=TermKind.CUSTOM,
            ),
        }
    )
    first_edition = base.editions[0].model_copy(
        update={
            "edition_id": "edition_early",
            "work_id": first_work.work_id,
            "edition_label": "=Private edition label",
        }
    )
    second_edition = base.editions[0].model_copy(
        update={
            "edition_id": "edition_late",
            "work_id": second_work.work_id,
            "edition_label": "Later critical edition",
        }
    )
    first_source = base.sources[0].model_copy(
        update={
            "source_id": "source_early",
            "edition_id": first_edition.edition_id,
        }
    )
    second_source = base.sources[0].model_copy(
        update={
            "source_id": "source_late",
            "edition_id": second_edition.edition_id,
            "source_type": VocabularyTerm(
                value="scanned_book",
                label="Scanned book",
                kind=TermKind.CUSTOM,
            ),
        }
    )
    first_asset = base.assets[0].model_copy(
        update={
            "asset_id": "asset_work_early",
            "file_label": "early.txt",
            "content_sha256": sha_a,
            "work_id": first_work.work_id,
            "edition_id": first_edition.edition_id,
            "source_id": first_source.source_id,
            "rights_asset_ids": ("asset_work_early",),
        }
    )
    second_asset = base.assets[0].model_copy(
        update={
            "asset_id": "asset_work_late",
            "file_label": "late.txt",
            "content_sha256": sha_b,
            "work_id": second_work.work_id,
            "edition_id": second_edition.edition_id,
            "source_id": second_source.source_id,
            "rights_asset_ids": ("asset_work_late",),
        }
    )
    first_file = base.validated_files[0].model_copy(
        update={"file_label": "early.txt", "content_sha256": sha_a}
    )
    second_file = base.validated_files[0].model_copy(
        update={"file_label": "late.txt", "content_sha256": sha_b}
    )
    first_rights = base.rights[0].model_copy(
        update={"asset_id": first_asset.asset_id, "source_id": first_source.source_id}
    )
    second_rights = base.rights[0].model_copy(
        update={"asset_id": second_asset.asset_id, "source_id": second_source.source_id}
    )
    inventory = base.model_copy(
        update={
            "works": (first_work, second_work),
            "editions": (first_edition, second_edition),
            "sources": (first_source, second_source),
            "assets": (first_asset, second_asset),
            "validated_files": (first_file, second_file),
            "rights": (first_rights, second_rights),
        }
    )
    annotations = CorpusAnalysisAnnotationsV1(
        schema_version="corpus-analysis-annotations-v1",
        inventory_sha256=inventory_sha256(inventory),
        annotations=(
            CorpusAnalysisAnnotation(
                document_id="doc_" + "1" * 64,
                asset_id=first_asset.asset_id,
                work_id=first_work.work_id,
                analysis_role=AnalysisRole.KNOWN,
                text_unit=TextUnit.INDEPENDENT_WORK,
                parent_work_id=None,
                ocr_status=OcrStatus.NOT_OCR,
                paratext_status=ParatextStatus.ABSENT,
            ),
            CorpusAnalysisAnnotation(
                document_id="doc_" + "2" * 64,
                asset_id=second_asset.asset_id,
                work_id=second_work.work_id,
                analysis_role=AnalysisRole.KNOWN,
                text_unit=TextUnit.INDEPENDENT_WORK,
                parent_work_id=None,
                ocr_status=OcrStatus.UNREVIEWED,
                paratext_status=ParatextStatus.RETAINED,
                preupload_curation_note="PRIVATE CURATION NOTE",
            ),
        ),
    )
    documents = tuple(
        prepare_document(
            raw,
            expected_raw_sha256=asset.content_sha256,
            annotation=annotation,
        )
        for raw, asset, annotation in zip(
            (raw_a, raw_b),
            inventory.assets,
            annotations.annotations,
            strict=True,
        )
    )
    config = build_preprocessing_config(parse_custom_exclusions(None))
    candidates = build_candidate_inventory(documents)
    manifest = build_preprocessing_manifest(
        config=config,
        annotations=annotations,
        documents=documents,
        candidate_inventory=candidates,
    )
    contexts = (
        WorkHealthContext(
            work_id=first_work.work_id,
            chronology_point="exact:1883:",
            chronology_certainty="exact",
            edition_context=first_edition.edition_label,
            genre=first_work.genre.value,
            audience=first_work.audience.value,
            source_type=first_source.source_type.value,
            adaptation=first_work.adaptation.value,
            collection=first_work.collection.value,
            ocr_status="not_ocr",
            paratext_status="absent",
            curation_state="not_disclosed",
        ),
        WorkHealthContext(
            work_id=second_work.work_id,
            chronology_point="approximate:1900:",
            chronology_certainty="approximate",
            edition_context=second_edition.edition_label,
            genre=second_work.genre.value,
            audience=second_work.audience.value,
            source_type=second_source.source_type.value,
            adaptation=second_work.adaptation.value,
            collection=second_work.collection.value,
            ocr_status="unreviewed",
            paratext_status="retained",
            curation_state="disclosed",
        ),
    )
    health = assess_corpus_health(
        purpose=inventory.purpose,
        config=config,
        annotations=annotations,
        manifest=manifest,
        documents=documents,
        candidate_inventory=candidates,
        work_contexts=contexts,
    )
    return inventory, annotations, manifest, health, raw_a, raw_b


def test_projection_binds_readable_panels_to_content_free_rows() -> None:
    inventory, annotations, manifest, health, raw_a, raw_b = _artifacts()
    projection = build_corpus_health_projection(
        inventory=inventory,
        annotations=annotations,
        manifest=manifest,
        health_report=health,
    )

    assert [item.work_id for item in projection.work_preparation] == [
        "work_early",
        "work_late",
    ]
    assert projection.work_preparation[0].display_label == "=Private early title"
    assert projection.confounds[1].edition_label == "Later critical edition"
    assert projection.confounds[1].curation_state == "disclosed"
    assert projection.confounds[1].curation_note_disclosed is True
    assert [item.code for item in projection.overlaps] == [CorpusHealthFindingCode.SHARED_PASSAGE]
    assert projection.overlaps[0].work_ids == ("work_early", "work_late")
    assert projection.overlaps[0].display_labels == (
        "=Private early title",
        "Private later title",
    )
    assert [item.requested_mfw for item in projection.feature_capacity] == [100, 300, 500, 1000]

    exports = (
        export_work_preparation_csv(projection),
        export_health_findings_csv(projection),
        export_confound_matrix_csv(projection),
        export_feature_capacity_csv(projection),
    )
    assert exports == tuple(
        exporter(projection)
        for exporter in (
            export_work_preparation_csv,
            export_health_findings_csv,
            export_confound_matrix_csv,
            export_feature_capacity_csv,
        )
    )
    joined = b"\n".join(exports)
    for private in (
        raw_a,
        raw_b,
        b"PRIVATE CURATION NOTE",
        b"Private early title",
        b"Private later title",
        b"Private edition label",
        b"Later critical edition",
    ):
        assert private not in joined

    work_rows = _rows(exports[0])
    confound_rows = _rows(exports[2])
    capacity_rows = _rows(exports[3])
    assert [row["work_id"] for row in work_rows] == ["work_early", "work_late"]
    assert confound_rows[1]["edition_id"] == "edition_late"
    assert confound_rows[1]["chronology_mode"] == "approximate"
    assert confound_rows[1]["curation_state"] == "disclosed"
    assert [row["requested_mfw"] for row in capacity_rows] == ["100", "300", "500", "1000"]


def test_projection_rejects_stale_bindings_and_invalid_overlap_shape() -> None:
    inventory, annotations, manifest, health, _raw_a, _raw_b = _artifacts()
    stale = manifest.model_copy(update={"inventory_sha256": "0" * 64})
    with pytest.raises(CorpusHealthProjectionError) as captured:
        build_corpus_health_projection(
            inventory=inventory,
            annotations=annotations,
            manifest=stale,
            health_report=health,
        )
    assert captured.value.code is CorpusHealthProjectionErrorCode.BINDING_MISMATCH
    assert str(captured.value) == "P007_HEALTH_PROJECTION_BINDING_MISMATCH"
    assert "Private" not in str(captured.value)

    overlap = next(
        item for item in health.findings if item.code is CorpusHealthFindingCode.SHARED_PASSAGE
    )
    malformed = overlap.model_copy(update={"subject_refs": ("work_early",)})
    changed_health = health.model_copy(
        update={
            "findings": tuple(
                malformed if item.finding_id == overlap.finding_id else item
                for item in health.findings
            )
        }
    )
    with pytest.raises(CorpusHealthProjectionError) as malformed_error:
        build_corpus_health_projection(
            inventory=inventory,
            annotations=annotations,
            manifest=manifest,
            health_report=changed_health,
        )
    assert malformed_error.value.code is CorpusHealthProjectionErrorCode.INVALID_PROJECTION

    repeated = overlap.model_copy(update={"subject_refs": ("work_early", "work_early")})
    repeated_health = health.model_copy(
        update={
            "findings": tuple(
                repeated if item.finding_id == overlap.finding_id else item
                for item in health.findings
            )
        }
    )
    with pytest.raises(CorpusHealthProjectionError) as repeated_error:
        build_corpus_health_projection(
            inventory=inventory,
            annotations=annotations,
            manifest=manifest,
            health_report=repeated_health,
        )
    assert repeated_error.value.code is CorpusHealthProjectionErrorCode.INVALID_PROJECTION


def test_csv_policy_failure_remains_content_free(monkeypatch: pytest.MonkeyPatch) -> None:
    inventory, annotations, manifest, health, _raw_a, _raw_b = _artifacts()
    projection = build_corpus_health_projection(
        inventory=inventory,
        annotations=annotations,
        manifest=manifest,
        health_report=health,
    )

    def reject(*_args: object, **_kwargs: object) -> None:
        raise IntakeError(IntakeErrorCode.CSV_INJECTION)

    monkeypatch.setattr(projection_module, "validate_upload", reject)
    with pytest.raises(CorpusHealthProjectionError) as captured:
        export_work_preparation_csv(projection)
    assert captured.value.code is CorpusHealthProjectionErrorCode.CSV_POLICY_REJECTED
    assert captured.value.intake_error_code is IntakeErrorCode.CSV_INJECTION
    assert "Private" not in str(captured.value)


def test_projection_models_reject_internal_row_drift() -> None:
    inventory, annotations, manifest, health, _raw_a, _raw_b = _artifacts()
    projection = build_corpus_health_projection(
        inventory=inventory,
        annotations=annotations,
        manifest=manifest,
        health_report=health,
    )
    confound = projection.confounds[0]
    overlap = projection.overlaps[0]

    with pytest.raises(ValidationError, match="curation disclosure"):
        ConfoundDatum.model_validate(
            {
                **confound.model_dump(),
                "curation_note_disclosed": not confound.curation_note_disclosed,
            }
        )
    with pytest.raises(ValidationError, match="declared overlap code"):
        OverlapDatum.model_validate(
            {**overlap.model_dump(), "code": CorpusHealthFindingCode.LENGTH_IMBALANCE}
        )
    with pytest.raises(ValidationError, match="two different works"):
        OverlapDatum.model_validate(
            {**overlap.model_dump(), "work_ids": ("work_early", "work_early")}
        )

    with pytest.raises(ValidationError, match="sorted and unique"):
        CorpusHealthProjection.model_validate(
            {
                **projection.model_dump(),
                "work_preparation": tuple(reversed(projection.work_preparation)),
            }
        )
    with pytest.raises(ValidationError, match="must match"):
        CorpusHealthProjection.model_validate(
            {
                **projection.model_dump(),
                "confounds": tuple(reversed(projection.confounds)),
            }
        )
    unknown_overlap = overlap.model_copy(update={"work_ids": ("work_early", "work_missing")})
    with pytest.raises(ValidationError, match="reference projected works"):
        CorpusHealthProjection.model_validate(
            {**projection.model_dump(), "overlaps": (unknown_overlap,)}
        )


def test_builder_rejects_duplicate_missing_and_cross_record_metadata() -> None:
    inventory, annotations, manifest, health, _raw_a, _raw_b = _artifacts()

    duplicate_inventory = inventory.model_copy(
        update={"sources": (*inventory.sources, inventory.sources[0])}
    )
    duplicate_annotations, duplicate_manifest, duplicate_health = _rebind(
        duplicate_inventory,
        annotations,
        manifest,
        health,
    )
    with pytest.raises(CorpusHealthProjectionError) as duplicate_error:
        build_corpus_health_projection(
            inventory=duplicate_inventory,
            annotations=duplicate_annotations,
            manifest=duplicate_manifest,
            health_report=duplicate_health,
        )
    assert duplicate_error.value.code is CorpusHealthProjectionErrorCode.INVALID_PROJECTION

    missing_work = manifest.works[0].model_copy(update={"asset_id": "asset_missing"})
    changed_manifest = manifest.model_copy(update={"works": (missing_work, *manifest.works[1:])})
    missing_annotations, missing_manifest, missing_health = _rebind(
        inventory,
        annotations,
        changed_manifest,
        health,
    )
    with pytest.raises(CorpusHealthProjectionError) as missing_error:
        build_corpus_health_projection(
            inventory=inventory,
            annotations=missing_annotations,
            manifest=missing_manifest,
            health_report=missing_health,
        )
    assert missing_error.value.code is CorpusHealthProjectionErrorCode.INVALID_PROJECTION

    broken_asset = inventory.assets[0].model_copy(update={"source_id": "source_missing"})
    broken_inventory = inventory.model_copy(
        update={"assets": (broken_asset, *inventory.assets[1:])}
    )
    broken_annotations, broken_manifest, broken_health = _rebind(
        broken_inventory,
        annotations,
        manifest,
        health,
    )
    with pytest.raises(CorpusHealthProjectionError) as relationship_error:
        build_corpus_health_projection(
            inventory=broken_inventory,
            annotations=broken_annotations,
            manifest=broken_manifest,
            health_report=broken_health,
        )
    assert relationship_error.value.code is CorpusHealthProjectionErrorCode.INVALID_PROJECTION

    crossed_asset = inventory.assets[0].model_copy(
        update={
            "edition_id": inventory.editions[1].edition_id,
            "source_id": inventory.sources[1].source_id,
        }
    )
    crossed_inventory = inventory.model_copy(
        update={"assets": (crossed_asset, *inventory.assets[1:])}
    )
    crossed_annotations, crossed_manifest, crossed_health = _rebind(
        crossed_inventory,
        annotations,
        manifest,
        health,
    )
    with pytest.raises(CorpusHealthProjectionError) as crossed_error:
        build_corpus_health_projection(
            inventory=crossed_inventory,
            annotations=crossed_annotations,
            manifest=crossed_manifest,
            health_report=crossed_health,
        )
    assert crossed_error.value.code is CorpusHealthProjectionErrorCode.INVALID_PROJECTION


def test_builder_translates_projection_validation_without_echoing_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inventory, annotations, manifest, health, _raw_a, _raw_b = _artifacts()

    def reject(**_kwargs: object) -> None:
        raise ValueError("PRIVATE PROJECTION VALUE")

    monkeypatch.setattr(projection_module, "CorpusHealthProjection", reject)
    with pytest.raises(CorpusHealthProjectionError) as captured:
        build_corpus_health_projection(
            inventory=inventory,
            annotations=annotations,
            manifest=manifest,
            health_report=health,
        )
    assert captured.value.code is CorpusHealthProjectionErrorCode.INVALID_PROJECTION
    assert "PRIVATE" not in str(captured.value)
