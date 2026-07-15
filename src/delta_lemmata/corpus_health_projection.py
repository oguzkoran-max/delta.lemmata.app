"""Bound, content-free P007 projections shared by visuals, tables, and CSV."""

from __future__ import annotations

import csv
import hashlib
import io
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from delta_lemmata.corpus_health_models import (
    CorpusHealthFinding,
    CorpusHealthFindingCode,
    CorpusHealthReportV1,
    MfwCapacity,
)
from delta_lemmata.corpus_models import DateMode, FrozenModel
from delta_lemmata.ingestion import (
    DEFAULT_LIMITS,
    IncomingUpload,
    IngestionLimits,
    IntakeError,
    IntakeErrorCode,
    IntakeRole,
    validate_upload,
)
from delta_lemmata.inventory import CorpusInventory, inventory_sha256
from delta_lemmata.preprocessing_models import (
    AnalysisRole,
    CorpusAnalysisAnnotationsV1,
    PreprocessingManifestV1,
    TextUnit,
    canonical_p007_json,
)

_OVERLAP_CODES = frozenset(
    {
        CorpusHealthFindingCode.EXACT_DUPLICATE,
        CorpusHealthFindingCode.NEAR_DUPLICATE,
        CorpusHealthFindingCode.SHARED_PASSAGE,
    }
)


class CorpusHealthProjectionErrorCode(StrEnum):
    BINDING_MISMATCH = "P007_HEALTH_PROJECTION_BINDING_MISMATCH"
    INVALID_PROJECTION = "P007_HEALTH_PROJECTION_INVALID"
    CSV_POLICY_REJECTED = "P007_HEALTH_PROJECTION_CSV_POLICY_REJECTED"


class CorpusHealthProjectionError(ValueError):
    """A content-free projection or export failure."""

    def __init__(
        self,
        code: CorpusHealthProjectionErrorCode,
        intake_error_code: IntakeErrorCode | None = None,
    ) -> None:
        self.code = code
        self.intake_error_code = intake_error_code
        detail = "" if intake_error_code is None else f":{intake_error_code.value}"
        super().__init__(f"{code.value}{detail}")


class WorkPreparationDatum(FrozenModel):
    document_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    work_id: str = Field(min_length=1)
    display_label: str = Field(min_length=1)
    analysis_role: AnalysisRole
    text_unit: TextUnit
    parent_work_id: str | None
    raw_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prepared_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_byte_count: int = Field(ge=0)
    prepared_byte_count: int = Field(ge=0)
    token_count: int = Field(ge=0)
    unique_token_count: int = Field(ge=0)
    bom_removed: bool
    newline_replacement_count: int = Field(ge=0)
    lowercase_source_count: int = Field(ge=0)
    separator_source_count: int = Field(ge=0)


class ConfoundDatum(FrozenModel):
    work_id: str = Field(min_length=1)
    display_label: str = Field(min_length=1)
    edition_id: str = Field(min_length=1)
    edition_label: str = Field(min_length=1)
    genre: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    adaptation: str = Field(min_length=1)
    collection: str = Field(min_length=1)
    chronology_mode: DateMode
    chronology_start_year: int | None = Field(default=None, ge=1, le=9999)
    chronology_end_year: int | None = Field(default=None, ge=1, le=9999)
    ocr_status: str = Field(min_length=1)
    paratext_status: str = Field(min_length=1)
    curation_state: Literal["disclosed", "not_disclosed"]
    curation_note_disclosed: bool

    @model_validator(mode="after")
    def require_consistent_curation_state(self) -> Self:
        if self.curation_note_disclosed is not (self.curation_state == "disclosed"):
            raise ValueError("curation disclosure state must be consistent")
        return self


class OverlapDatum(FrozenModel):
    finding_id: str = Field(pattern=r"^finding_[0-9a-f]{64}$")
    code: CorpusHealthFindingCode
    work_ids: tuple[str, str]
    display_labels: tuple[str, str]
    observed_count: int | None = Field(default=None, ge=0)
    threshold_count: int | None = Field(default=None, ge=0)
    observed_ratio: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    threshold_ratio: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def require_overlap_code_and_pair(self) -> Self:
        if self.code not in _OVERLAP_CODES:
            raise ValueError("overlap rows require one declared overlap code")
        if self.work_ids[0] == self.work_ids[1]:
            raise ValueError("overlap rows require two different works")
        return self


class CorpusHealthProjection(FrozenModel):
    schema_version: Literal["corpus-health-projection-v1"] = "corpus-health-projection-v1"
    inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    annotations_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    health_report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_id: str = Field(pattern=r"^health_[0-9a-f]{64}$")
    profile_id: Literal["delta-surface-words-v1"]
    candidate_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_preparation: tuple[WorkPreparationDatum, ...] = Field(min_length=1)
    confounds: tuple[ConfoundDatum, ...] = Field(min_length=1)
    overlaps: tuple[OverlapDatum, ...]
    findings: tuple[CorpusHealthFinding, ...] = Field(min_length=1)
    feature_capacity: tuple[MfwCapacity, ...] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def require_complete_work_projection(self) -> Self:
        work_ids = tuple(item.work_id for item in self.work_preparation)
        if work_ids != tuple(sorted(set(work_ids))):
            raise ValueError("work preparation rows must be sorted and unique")
        confound_ids = tuple(item.work_id for item in self.confounds)
        if confound_ids != work_ids:
            raise ValueError("confound rows must match work preparation rows")
        if any(set(item.work_ids) - set(work_ids) for item in self.overlaps):
            raise ValueError("overlap rows must reference projected works")
        return self


def _projection_error(code: CorpusHealthProjectionErrorCode) -> CorpusHealthProjectionError:
    return CorpusHealthProjectionError(code)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_corpus_health_projection(
    *,
    inventory: CorpusInventory,
    annotations: CorpusAnalysisAnnotationsV1,
    manifest: PreprocessingManifestV1,
    health_report: CorpusHealthReportV1,
) -> CorpusHealthProjection:
    """Bind all P007 review surfaces to one exact report set."""

    inventory_digest = inventory_sha256(inventory)
    annotations_digest = _sha256(canonical_p007_json(annotations))
    manifest_digest = _sha256(canonical_p007_json(manifest))
    health_digest = _sha256(canonical_p007_json(health_report))
    observed_binding = (
        annotations.inventory_sha256,
        manifest.inventory_sha256,
        health_report.inventory_sha256,
        manifest.annotations_sha256,
        health_report.annotations_sha256,
        health_report.manifest_sha256,
        health_report.config_sha256,
        health_report.candidate_inventory_sha256,
        health_report.candidate_feature_count,
        health_report.purpose,
    )
    expected_binding = (
        inventory_digest,
        inventory_digest,
        inventory_digest,
        annotations_digest,
        annotations_digest,
        manifest_digest,
        manifest.config_sha256,
        manifest.candidate_inventory_sha256,
        manifest.candidate_feature_count,
        inventory.purpose,
    )
    if observed_binding != expected_binding:
        raise _projection_error(CorpusHealthProjectionErrorCode.BINDING_MISMATCH)

    works = {item.work_id: item for item in inventory.works}
    editions = {item.edition_id: item for item in inventory.editions}
    sources = {item.source_id: item for item in inventory.sources}
    assets = {item.asset_id: item for item in inventory.assets}
    annotation_by_asset = {item.asset_id: item for item in annotations.annotations}
    projected_sizes = (
        len(works),
        len(editions),
        len(sources),
        len(assets),
        len(annotation_by_asset),
    )
    source_sizes = (
        len(inventory.works),
        len(inventory.editions),
        len(inventory.sources),
        len(inventory.assets),
        len(annotations.annotations),
    )
    if projected_sizes != source_sizes:
        raise _projection_error(CorpusHealthProjectionErrorCode.INVALID_PROJECTION)

    preparation_rows: list[WorkPreparationDatum] = []
    confound_rows: list[ConfoundDatum] = []
    for prepared in sorted(manifest.works, key=lambda item: (item.work_id, item.asset_id)):
        annotation = annotation_by_asset.get(prepared.asset_id)
        asset = assets.get(prepared.asset_id)
        work = works.get(prepared.work_id)
        if annotation is None or asset is None or work is None:
            raise _projection_error(CorpusHealthProjectionErrorCode.INVALID_PROJECTION)
        edition = editions.get(asset.edition_id)
        source = sources.get(asset.source_id)
        if edition is None or source is None:
            raise _projection_error(CorpusHealthProjectionErrorCode.INVALID_PROJECTION)
        observed_relationships = (
            annotation.document_id,
            annotation.work_id,
            annotation.analysis_role,
            annotation.text_unit,
            annotation.parent_work_id,
            asset.work_id,
            edition.work_id,
            source.edition_id,
        )
        expected_relationships = (
            prepared.document_id,
            prepared.work_id,
            prepared.analysis_role,
            prepared.text_unit,
            prepared.parent_work_id,
            work.work_id,
            work.work_id,
            edition.edition_id,
        )
        if observed_relationships != expected_relationships:
            raise _projection_error(CorpusHealthProjectionErrorCode.INVALID_PROJECTION)
        preparation_rows.append(
            WorkPreparationDatum(
                document_id=prepared.document_id,
                asset_id=prepared.asset_id,
                work_id=prepared.work_id,
                display_label=work.title_original,
                analysis_role=prepared.analysis_role,
                text_unit=prepared.text_unit,
                parent_work_id=prepared.parent_work_id,
                raw_sha256=prepared.raw_sha256,
                prepared_sha256=prepared.prepared_sha256,
                raw_byte_count=prepared.raw_byte_count,
                prepared_byte_count=prepared.prepared_byte_count,
                token_count=prepared.token_count,
                unique_token_count=prepared.unique_token_count,
                bom_removed=prepared.bom_removed,
                newline_replacement_count=prepared.newline_replacement_count,
                lowercase_source_count=prepared.lowercase_source_count,
                separator_source_count=prepared.separator_source_count,
            )
        )
        curation_disclosed = annotation.preupload_curation_note is not None
        confound_rows.append(
            ConfoundDatum(
                work_id=work.work_id,
                display_label=work.title_original,
                edition_id=edition.edition_id,
                edition_label=edition.edition_label,
                genre=work.genre.value,
                audience=work.audience.value,
                source_type=source.source_type.value,
                adaptation=work.adaptation.value,
                collection=work.collection.value,
                chronology_mode=work.first_publication.mode,
                chronology_start_year=work.first_publication.start_year,
                chronology_end_year=work.first_publication.end_year,
                ocr_status=annotation.ocr_status.value,
                paratext_status=annotation.paratext_status.value,
                curation_state="disclosed" if curation_disclosed else "not_disclosed",
                curation_note_disclosed=curation_disclosed,
            )
        )

    labels = {item.work_id: item.display_label for item in preparation_rows}
    overlap_rows: list[OverlapDatum] = []
    for finding in health_report.findings:
        if finding.code not in _OVERLAP_CODES:
            continue
        if len(finding.subject_refs) != 2:
            raise _projection_error(CorpusHealthProjectionErrorCode.INVALID_PROJECTION)
        left, right = finding.subject_refs
        if (left == right, left in labels, right in labels) != (False, True, True):
            raise _projection_error(CorpusHealthProjectionErrorCode.INVALID_PROJECTION)
        pair = tuple(sorted(finding.subject_refs))
        overlap_rows.append(
            OverlapDatum(
                finding_id=finding.finding_id,
                code=finding.code,
                work_ids=(pair[0], pair[1]),
                display_labels=(labels[pair[0]], labels[pair[1]]),
                observed_count=finding.observed_count,
                threshold_count=finding.threshold_count,
                observed_ratio=finding.observed_ratio,
                threshold_ratio=finding.threshold_ratio,
            )
        )
    overlap_rows.sort(key=lambda item: (item.work_ids, item.code.value, item.finding_id))

    try:
        return CorpusHealthProjection(
            inventory_sha256=inventory_digest,
            annotations_sha256=annotations_digest,
            manifest_sha256=manifest_digest,
            health_report_sha256=health_digest,
            report_id=health_report.report_id,
            profile_id=manifest.profile_id,
            candidate_inventory_sha256=manifest.candidate_inventory_sha256,
            work_preparation=tuple(preparation_rows),
            confounds=tuple(confound_rows),
            overlaps=tuple(overlap_rows),
            findings=health_report.findings,
            feature_capacity=health_report.mfw_capacity,
        )
    except ValueError:
        raise _projection_error(CorpusHealthProjectionErrorCode.INVALID_PROJECTION) from None


def _write_csv(fieldnames: tuple[str, ...], rows: list[dict[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=fieldnames,
        dialect="excel",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _validate_generated_csv(
    payload: bytes,
    display_label: str,
    limits: IngestionLimits,
) -> None:
    try:
        validate_upload(
            IncomingUpload(IntakeRole.METADATA_CSV, display_label, payload, "text/csv"),
            limits=limits,
            id_factory=lambda: "0" * 32,
        )
    except IntakeError as error:
        raise CorpusHealthProjectionError(
            CorpusHealthProjectionErrorCode.CSV_POLICY_REJECTED,
            error.code,
        ) from None


def _optional(value: object | None) -> str:
    return "" if value is None else str(value)


def export_work_preparation_csv(
    projection: CorpusHealthProjection,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
) -> bytes:
    fieldnames = (
        "inventory_sha256",
        "manifest_sha256",
        "profile_id",
        "document_id",
        "asset_id",
        "work_id",
        "analysis_role",
        "text_unit",
        "parent_work_id",
        "raw_sha256",
        "prepared_sha256",
        "raw_byte_count",
        "prepared_byte_count",
        "token_count",
        "unique_token_count",
        "bom_removed",
        "newline_replacement_count",
        "lowercase_source_count",
        "separator_source_count",
    )
    rows = [
        {
            "inventory_sha256": projection.inventory_sha256,
            "manifest_sha256": projection.manifest_sha256,
            "profile_id": projection.profile_id,
            "document_id": item.document_id,
            "asset_id": item.asset_id,
            "work_id": item.work_id,
            "analysis_role": item.analysis_role.value,
            "text_unit": item.text_unit.value,
            "parent_work_id": _optional(item.parent_work_id),
            "raw_sha256": item.raw_sha256,
            "prepared_sha256": item.prepared_sha256,
            "raw_byte_count": str(item.raw_byte_count),
            "prepared_byte_count": str(item.prepared_byte_count),
            "token_count": str(item.token_count),
            "unique_token_count": str(item.unique_token_count),
            "bom_removed": str(item.bom_removed).lower(),
            "newline_replacement_count": str(item.newline_replacement_count),
            "lowercase_source_count": str(item.lowercase_source_count),
            "separator_source_count": str(item.separator_source_count),
        }
        for item in projection.work_preparation
    ]
    payload = _write_csv(fieldnames, rows)
    _validate_generated_csv(payload, "delta-work-preparation-v1.csv", limits)
    return payload


def export_health_findings_csv(
    projection: CorpusHealthProjection,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
) -> bytes:
    fieldnames = (
        "inventory_sha256",
        "health_report_sha256",
        "report_id",
        "finding_id",
        "code",
        "severity",
        "subject_refs",
        "observed_count",
        "threshold_count",
        "observed_ratio",
        "threshold_ratio",
    )
    rows = [
        {
            "inventory_sha256": projection.inventory_sha256,
            "health_report_sha256": projection.health_report_sha256,
            "report_id": projection.report_id,
            "finding_id": item.finding_id,
            "code": item.code.value,
            "severity": item.severity.value,
            "subject_refs": ";".join(item.subject_refs),
            "observed_count": _optional(item.observed_count),
            "threshold_count": _optional(item.threshold_count),
            "observed_ratio": _optional(item.observed_ratio),
            "threshold_ratio": _optional(item.threshold_ratio),
        }
        for item in projection.findings
    ]
    payload = _write_csv(fieldnames, rows)
    _validate_generated_csv(payload, "delta-health-findings-v1.csv", limits)
    return payload


def export_confound_matrix_csv(
    projection: CorpusHealthProjection,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
) -> bytes:
    fieldnames = (
        "inventory_sha256",
        "work_id",
        "edition_id",
        "genre",
        "audience",
        "source_type",
        "adaptation",
        "collection",
        "chronology_mode",
        "chronology_start_year",
        "chronology_end_year",
        "ocr_status",
        "paratext_status",
        "curation_state",
    )
    rows = [
        {
            "inventory_sha256": projection.inventory_sha256,
            "work_id": item.work_id,
            "edition_id": item.edition_id,
            "genre": item.genre,
            "audience": item.audience,
            "source_type": item.source_type,
            "adaptation": item.adaptation,
            "collection": item.collection,
            "chronology_mode": item.chronology_mode.value,
            "chronology_start_year": _optional(item.chronology_start_year),
            "chronology_end_year": _optional(item.chronology_end_year),
            "ocr_status": item.ocr_status,
            "paratext_status": item.paratext_status,
            "curation_state": item.curation_state,
        }
        for item in projection.confounds
    ]
    payload = _write_csv(fieldnames, rows)
    _validate_generated_csv(payload, "delta-confound-matrix-v1.csv", limits)
    return payload


def export_feature_capacity_csv(
    projection: CorpusHealthProjection,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
) -> bytes:
    fieldnames = (
        "inventory_sha256",
        "candidate_inventory_sha256",
        "requested_mfw",
        "available_features",
        "available",
    )
    rows = [
        {
            "inventory_sha256": projection.inventory_sha256,
            "candidate_inventory_sha256": projection.candidate_inventory_sha256,
            "requested_mfw": str(item.requested_mfw),
            "available_features": str(item.available_features),
            "available": str(item.available).lower(),
        }
        for item in projection.feature_capacity
    ]
    payload = _write_csv(fieldnames, rows)
    _validate_generated_csv(payload, "delta-feature-capacity-v1.csv", limits)
    return payload


__all__ = [
    "ConfoundDatum",
    "CorpusHealthProjection",
    "CorpusHealthProjectionError",
    "CorpusHealthProjectionErrorCode",
    "OverlapDatum",
    "WorkPreparationDatum",
    "build_corpus_health_projection",
    "export_confound_matrix_csv",
    "export_feature_capacity_csv",
    "export_health_findings_csv",
    "export_work_preparation_csv",
]
