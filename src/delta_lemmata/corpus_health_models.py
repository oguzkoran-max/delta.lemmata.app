"""Closed P007 corpus-health report contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, StrictInt, model_validator

from delta_lemmata.corpus_models import PurposeId
from delta_lemmata.preprocessing_models import (
    MAX_CANDIDATE_FEATURES,
    P007Model,
    Sha256,
    WorkId,
    parse_p007_payload,
)

_FINDING_PATTERN = r"^finding_[0-9a-f]{64}$"
_REPORT_PATTERN = r"^health_[0-9a-f]{64}$"
_GROUP_PATTERN = r"^group_[0-9a-f]{64}$"


class HealthSeverity(StrEnum):
    BLOCKER = "blocker"
    STRONG_WARNING = "strong_warning"
    NOTE = "note"


class CorpusHealthReadiness(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"


class CorpusHealthFindingCode(StrEnum):
    EMPTY_PREPARED_WORK = "empty_prepared_work"
    TOO_FEW_KNOWN_WORKS = "too_few_known_works"
    NON_INDEPENDENT_UNIT = "non_independent_unit"
    DUPLICATE_INDEPENDENCE_UNIT = "duplicate_independence_unit"
    EXACT_DUPLICATE = "exact_duplicate"
    NO_RUNNABLE_FEATURES = "no_runnable_features"
    TOO_MANY_DOCUMENTS = "too_many_documents"
    TOO_FEW_INDEPENDENT_WORKS = "too_few_independent_works"
    TOO_FEW_CHRONOLOGY_POINTS = "too_few_chronology_points"
    NEAR_DUPLICATE = "near_duplicate"
    SHARED_PASSAGE = "shared_passage"
    LENGTH_IMBALANCE = "length_imbalance"
    GROUP_IMBALANCE = "group_imbalance"
    OCR_CONFOUND = "ocr_confound"
    PARATEXT_CONFOUND = "paratext_confound"
    CURATION_CONFOUND = "curation_confound"
    EDITION_CONFOUND = "edition_confound"
    GENRE_CONFOUND = "genre_confound"
    AUDIENCE_CONFOUND = "audience_confound"
    SOURCE_CONFOUND = "source_confound"
    ADAPTATION_CONFOUND = "adaptation_confound"
    COLLECTION_CONFOUND = "collection_confound"
    CHRONOLOGY_CONFOUND = "chronology_confound"
    MFW_UNAVAILABLE = "mfw_unavailable"
    TRANSPORT_FEATURE_EXCLUDED = "transport_feature_excluded"
    PREPARATION_SUMMARY = "preparation_summary"


class CorpusHealthFinding(P007Model):
    finding_id: Annotated[str, Field(pattern=_FINDING_PATTERN)]
    code: CorpusHealthFindingCode = Field(strict=False)
    severity: HealthSeverity = Field(strict=False)
    subject_refs: tuple[WorkId, ...] = Field(default=(), max_length=200, strict=False)
    observed_count: StrictInt | None = Field(default=None, ge=0)
    threshold_count: StrictInt | None = Field(default=None, ge=0)
    observed_ratio: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    threshold_ratio: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class MfwCapacity(P007Model):
    requested_mfw: Literal[100, 300, 500, 1000]
    available_features: Annotated[StrictInt, Field(ge=0, le=MAX_CANDIDATE_FEATURES)]
    available: bool

    @model_validator(mode="after")
    def require_exact_capacity_flag(self) -> Self:
        if self.available is not (self.available_features >= self.requested_mfw):
            raise ValueError("MFW availability must match the candidate count")
        return self


class GroupCount(P007Model):
    group_ref: Annotated[str, Field(pattern=_GROUP_PATTERN)]
    independent_work_count: Annotated[StrictInt, Field(ge=1, le=200)]


class CorpusHealthReportV1(P007Model):
    schema_version: Literal["corpus-health-report-v1"]
    report_id: Annotated[str, Field(pattern=_REPORT_PATTERN)]
    severity_profile: Literal["delta-corpus-health-v1"]
    purpose: PurposeId = Field(strict=False)
    config_sha256: Sha256
    inventory_sha256: Sha256
    annotations_sha256: Sha256
    manifest_sha256: Sha256
    candidate_inventory_sha256: Sha256
    candidate_feature_count: Annotated[
        StrictInt,
        Field(ge=0, le=MAX_CANDIDATE_FEATURES),
    ]
    independent_work_count: Annotated[StrictInt, Field(ge=0, le=200)]
    known_independent_work_count: Annotated[StrictInt, Field(ge=0, le=200)]
    chronology_point_count: Annotated[StrictInt, Field(ge=0, le=200)]
    readiness: CorpusHealthReadiness = Field(strict=False)
    blocker_count: Annotated[StrictInt, Field(ge=0, le=10_000)]
    strong_warning_count: Annotated[StrictInt, Field(ge=0, le=10_000)]
    note_count: Annotated[StrictInt, Field(ge=0, le=10_000)]
    group_counts: tuple[GroupCount, ...] = Field(default=(), max_length=200, strict=False)
    mfw_capacity: tuple[MfwCapacity, ...] = Field(min_length=4, max_length=4, strict=False)
    findings: tuple[CorpusHealthFinding, ...] = Field(max_length=10_000, strict=False)

    @model_validator(mode="after")
    def require_consistent_summary(self) -> Self:
        expected_mfw = (100, 300, 500, 1000)
        if tuple(item.requested_mfw for item in self.mfw_capacity) != expected_mfw:
            raise ValueError("MFW capacities must use the fixed Guided order")
        if len({item.finding_id for item in self.findings}) != len(self.findings):
            raise ValueError("finding identifiers must be unique")
        counts = {
            severity: sum(item.severity is severity for item in self.findings)
            for severity in HealthSeverity
        }
        if (
            self.blocker_count != counts[HealthSeverity.BLOCKER]
            or self.strong_warning_count != counts[HealthSeverity.STRONG_WARNING]
            or self.note_count != counts[HealthSeverity.NOTE]
        ):
            raise ValueError("finding counts must match findings")
        expected_readiness = (
            CorpusHealthReadiness.READY
            if self.blocker_count == 0
            else CorpusHealthReadiness.BLOCKED
        )
        if self.readiness is not expected_readiness:
            raise ValueError("readiness must match blocker count")
        if self.known_independent_work_count > self.independent_work_count:
            raise ValueError("known independent count cannot exceed total")
        return self


def parse_corpus_health_report(payload: bytes) -> CorpusHealthReportV1:
    return parse_p007_payload(payload, model=CorpusHealthReportV1)


__all__ = [
    "CorpusHealthFinding",
    "CorpusHealthFindingCode",
    "CorpusHealthReadiness",
    "CorpusHealthReportV1",
    "GroupCount",
    "HealthSeverity",
    "MfwCapacity",
    "parse_corpus_health_report",
]
