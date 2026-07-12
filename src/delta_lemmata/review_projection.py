"""Deterministic, payload-free projections for the P004 corpus review."""

from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from delta_lemmata.corpus_models import (
    AssetRecord,
    AuthorKind,
    DateMode,
    DateValue,
    FrozenModel,
    TermKind,
    VocabularyTerm,
    WorkRecord,
)
from delta_lemmata.corpus_validation import (
    IssueCode,
    IssueSeverity,
    ValidationIssue,
    ValidationReport,
)
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
from delta_lemmata.provenance import canonical_json_bytes
from delta_lemmata.rights import RightsStatus


class CompositionDimension(StrEnum):
    GENRE = "genre"
    AUDIENCE = "audience"
    ADAPTATION = "adaptation"
    COLLECTION = "collection"
    SOURCE_TYPE = "source_type"


class CompletenessGroup(StrEnum):
    IDENTITY = "identity"
    CHRONOLOGY = "chronology"
    EDITION = "edition"
    SOURCE = "source"
    CLASSIFICATION = "classification"
    RIGHTS = "rights"
    NORMALIZATION = "normalization"


class CompletenessStatus(StrEnum):
    COMPLETE = "complete"
    MISSING = "missing"
    WARNING = "warning"
    CONFLICT = "conflict"


class ReviewProjectionErrorCode(StrEnum):
    STALE_VALIDATION_REPORT = "REVIEW_STALE_VALIDATION_REPORT"
    CSV_POLICY_REJECTED = "REVIEW_CSV_POLICY_REJECTED"


class ReviewProjectionError(ValueError):
    """A content-free projection or export failure."""

    def __init__(
        self,
        code: ReviewProjectionErrorCode,
        intake_error_code: IntakeErrorCode | None = None,
    ) -> None:
        self.code = code
        self.intake_error_code = intake_error_code
        detail = "" if intake_error_code is None else f":{intake_error_code.value}"
        super().__init__(f"{code.value}{detail}")


_DIMENSION_LABELS = {
    CompositionDimension.GENRE: "Genre",
    CompositionDimension.AUDIENCE: "Audience",
    CompositionDimension.ADAPTATION: "Adaptation",
    CompositionDimension.COLLECTION: "Collection",
    CompositionDimension.SOURCE_TYPE: "Acquisition source type",
}

_GROUP_LABELS = {
    CompletenessGroup.IDENTITY: "Identity",
    CompletenessGroup.CHRONOLOGY: "Chronology",
    CompletenessGroup.EDITION: "Edition",
    CompletenessGroup.SOURCE: "Source",
    CompletenessGroup.CLASSIFICATION: "Classification",
    CompletenessGroup.RIGHTS: "Rights",
    CompletenessGroup.NORMALIZATION: "Normalization",
}

_STATUS_RANK = {
    CompletenessStatus.COMPLETE: 0,
    CompletenessStatus.WARNING: 1,
    CompletenessStatus.MISSING: 2,
    CompletenessStatus.CONFLICT: 3,
}

_SEVERITY_RANK = {
    IssueSeverity.INFORMATION: 0,
    IssueSeverity.WARNING: 1,
    IssueSeverity.BLOCKER: 2,
}

_CONFLICT_CODES = frozenset(
    {
        IssueCode.DUPLICATE_AUTHOR_ID,
        IssueCode.DUPLICATE_WORK_ID,
        IssueCode.DUPLICATE_EDITION_ID,
        IssueCode.DUPLICATE_SOURCE_ID,
        IssueCode.DUPLICATE_ASSET_ID,
        IssueCode.DUPLICATE_RIGHTS_ASSET_ID,
        IssueCode.DUPLICATE_FILE_LABEL,
        IssueCode.DUPLICATE_VALIDATED_FILE,
        IssueCode.FILE_HASH_MISMATCH,
        IssueCode.RELATIONSHIP_CONFLICT,
        IssueCode.MULTIPLE_ASSETS_PER_WORK,
        IssueCode.DATE_RANGE_REVERSED,
        IssueCode.EDITION_PRECEDES_PUBLICATION,
        IssueCode.CONTROLLED_TERM_UNKNOWN,
        IssueCode.RIGHTS_SOURCE_CONFLICT,
    }
)

_MISSING_CODES = frozenset(
    {
        IssueCode.FILE_REFERENCE_MISSING,
        IssueCode.UNMAPPED_VALIDATED_FILE,
        IssueCode.AUTHOR_REFERENCE_MISSING,
        IssueCode.AUTHOR_ROLE_REQUIRED,
        IssueCode.WORK_REFERENCE_MISSING,
        IssueCode.EDITION_REFERENCE_MISSING,
        IssueCode.SOURCE_REFERENCE_MISSING,
        IssueCode.ASSET_REFERENCE_MISSING,
        IssueCode.RIGHTS_REFERENCE_MISSING,
        IssueCode.RIGHTS_CHAIN_SELF_MISSING,
        IssueCode.RIGHTS_CHAIN_UNCONFIRMED,
        IssueCode.RIGHTS_DEPENDENCY_MISSING,
        IssueCode.FILE_MAPPING_UNCONFIRMED,
        IssueCode.WORK_ASSET_MISSING,
        IssueCode.GROUP_LABEL_REQUIRED,
        IssueCode.CHRONOLOGY_REQUIRED,
        IssueCode.NORMALIZATION_PROFILE_UNKNOWN,
        IssueCode.NORMALIZATION_DETAILS_REQUIRED,
        IssueCode.RIGHTS_STATUS_UNRESOLVED,
        IssueCode.RIGHTS_SOURCE_REFERENCE_MISSING,
    }
)

_WARNING_CODES = frozenset(
    {
        IssueCode.EDITION_DATE_UNKNOWN,
        IssueCode.DATE_ORDER_UNCERTAIN,
        IssueCode.CONFOUND_METADATA_UNKNOWN,
    }
)

_ISSUE_STATUS_BY_CODE = {
    **{code: CompletenessStatus.CONFLICT for code in _CONFLICT_CODES},
    **{code: CompletenessStatus.MISSING for code in _MISSING_CODES},
    **{code: CompletenessStatus.WARNING for code in _WARNING_CODES},
}

_RIGHTS_CODES = frozenset(
    {
        IssueCode.DUPLICATE_RIGHTS_ASSET_ID,
        IssueCode.ASSET_REFERENCE_MISSING,
        IssueCode.RIGHTS_REFERENCE_MISSING,
        IssueCode.RIGHTS_CHAIN_SELF_MISSING,
        IssueCode.RIGHTS_CHAIN_UNCONFIRMED,
        IssueCode.RIGHTS_DEPENDENCY_MISSING,
        IssueCode.UPLOAD_PERMISSION_REQUIRED,
        IssueCode.ANALYSIS_PERMISSION_REQUIRED,
        IssueCode.RIGHTS_STATUS_UNRESOLVED,
        IssueCode.RIGHTS_SOURCE_CONFLICT,
        IssueCode.RIGHTS_SOURCE_REFERENCE_MISSING,
    }
)

_NORMALIZATION_CODES = frozenset(
    {
        IssueCode.NORMALIZATION_PROFILE_UNKNOWN,
        IssueCode.NORMALIZATION_DETAILS_REQUIRED,
    }
)

_CORPUS_LEVEL_CODES = frozenset(
    {
        IssueCode.UNMAPPED_VALIDATED_FILE,
        IssueCode.DUPLICATE_VALIDATED_FILE,
        IssueCode.STYLE_AUTHOR_SET_MIXED,
        IssueCode.STYLE_LANGUAGE_MIXED,
        IssueCode.WORK_COUNT_EXPLORATORY,
        IssueCode.CHRONOLOGY_POINTS_EXPLORATORY,
    }
)

_ACTION_RESTRICTION_CODES = frozenset(
    {
        IssueCode.UPLOAD_PERMISSION_REQUIRED,
        IssueCode.ANALYSIS_PERMISSION_REQUIRED,
    }
)


class CompositionDatum(FrozenModel):
    dimension: CompositionDimension
    dimension_label: str = Field(min_length=1)
    category_value: str = Field(min_length=1)
    category_label: str = Field(min_length=1)
    work_row_keys: tuple[str, ...]
    work_count: int = Field(ge=0)
    corpus_work_count: int = Field(gt=0)

    @model_validator(mode="after")
    def require_consistent_count(self) -> Self:
        if self.work_count != len(self.work_row_keys):
            raise ValueError("work_count must equal the number of work row keys")
        if self.work_count > self.corpus_work_count:
            raise ValueError("work_count cannot exceed corpus_work_count")
        if self.work_row_keys != tuple(sorted(self.work_row_keys)):
            raise ValueError("work row keys must be sorted")
        return self


class TimelineEditionDatum(FrozenModel):
    edition_id: str = Field(min_length=1)
    edition_label: str = Field(min_length=1)
    edition_date: DateValue


class TimelineSourceDatum(FrozenModel):
    source_id: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_type_label: str = Field(min_length=1)


class TimelineDatum(FrozenModel):
    row_key: str = Field(min_length=1)
    work_id: str = Field(min_length=1)
    work_title: str = Field(min_length=1)
    author_names: tuple[str, ...]
    language: str = Field(min_length=1)
    first_publication: DateValue
    genre_label: str = Field(min_length=1)
    audience_label: str = Field(min_length=1)
    editions: tuple[TimelineEditionDatum, ...]
    sources: tuple[TimelineSourceDatum, ...]


class CompletenessDatum(FrozenModel):
    row_key: str = Field(min_length=1)
    work_id: str = Field(min_length=1)
    work_title: str = Field(min_length=1)
    group: CompletenessGroup
    group_label: str = Field(min_length=1)
    status: CompletenessStatus
    summary: str = Field(min_length=1)
    field_paths: tuple[str, ...] = ()
    issue_codes: tuple[IssueCode, ...] = ()
    highest_issue_severity: IssueSeverity | None = None

    @model_validator(mode="after")
    def require_sorted_evidence(self) -> Self:
        if self.field_paths != tuple(sorted(set(self.field_paths))):
            raise ValueError("field paths must be sorted and unique")
        if self.issue_codes != tuple(sorted(set(self.issue_codes), key=lambda item: item.value)):
            raise ValueError("issue codes must be sorted and unique")
        return self


class CorpusReviewProjection(FrozenModel):
    schema_version: Literal["corpus-review-projection-v1"] = "corpus-review-projection-v1"
    inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    corpus_work_count: int = Field(gt=0)
    composition: tuple[CompositionDatum, ...]
    timeline: tuple[TimelineDatum, ...]
    completeness: tuple[CompletenessDatum, ...]
    corpus_issues: tuple[ValidationIssue, ...] = ()

    @model_validator(mode="after")
    def require_complete_projection(self) -> Self:
        for dimension in CompositionDimension:
            rows = tuple(item for item in self.composition if item.dimension is dimension)
            if not rows or sum(item.work_count for item in rows) != self.corpus_work_count:
                raise ValueError("each composition dimension must represent every work")
        row_groups: dict[str, set[CompletenessGroup]] = defaultdict(set)
        for item in self.completeness:
            row_groups[item.row_key].add(item.group)
        if len(row_groups) != self.corpus_work_count:
            raise ValueError("completeness must contain one row per corpus work")
        expected_groups = set(CompletenessGroup)
        if any(groups != expected_groups for groups in row_groups.values()):
            raise ValueError("each work must contain every completeness group")
        timeline_keys = tuple(item.row_key for item in self.timeline)
        if len(timeline_keys) != len(set(timeline_keys)):
            raise ValueError("timeline row keys must be unique")
        if len(timeline_keys) != self.corpus_work_count or set(timeline_keys) != set(row_groups):
            raise ValueError("timeline must contain the same corpus work rows")
        expected_timeline = tuple(
            sorted(
                self.timeline,
                key=lambda item: (
                    item.first_publication.chronology_key or (10000, 10000),
                    item.work_title.casefold(),
                    item.row_key,
                ),
            )
        )
        if self.timeline != expected_timeline:
            raise ValueError("timeline rows must use deterministic chronology order")
        return self


@dataclass(frozen=True, slots=True)
class _WorkEntry:
    row_key: str
    work: WorkRecord


@dataclass(frozen=True, slots=True)
class _CellBase:
    status: CompletenessStatus
    summary: str
    field_paths: tuple[str, ...] = ()


def _canonical_model_key(value: FrozenModel) -> bytes:
    return canonical_json_bytes(value.model_dump(mode="json"))


def _work_entries(inventory: CorpusInventory) -> tuple[_WorkEntry, ...]:
    works = tuple(
        sorted(
            inventory.works,
            key=lambda item: (item.work_id, _canonical_model_key(item)),
        )
    )
    totals = Counter(work.work_id for work in works)
    seen: Counter[str] = Counter()
    entries = []
    for work in works:
        seen[work.work_id] += 1
        row_key = (
            work.work_id if totals[work.work_id] == 1 else f"{work.work_id}#{seen[work.work_id]}"
        )
        entries.append(_WorkEntry(row_key=row_key, work=work))
    return tuple(entries)


def _term_category(term: VocabularyTerm) -> tuple[str, str]:
    return (term.value, term.label)


def _source_category(
    entry: _WorkEntry,
    inventory: CorpusInventory,
) -> tuple[str, str]:
    source_terms = {
        (source.source_type.value, source.source_type.label, source.source_type.kind.value)
        for asset in inventory.assets
        if asset.work_id == entry.work.work_id
        for source in inventory.sources
        if source.source_id == asset.source_id
    }
    if not source_terms:
        return ("missing", "Missing source mapping")
    if len(source_terms) > 1:
        return ("conflict", "Conflicting source types")
    value, label, _kind = next(iter(source_terms))
    return (value, label)


def _composition(
    inventory: CorpusInventory,
    entries: tuple[_WorkEntry, ...],
) -> tuple[CompositionDatum, ...]:
    categories: dict[
        CompositionDimension,
        dict[tuple[str, str], list[str]],
    ] = {dimension: defaultdict(list) for dimension in CompositionDimension}
    for entry in entries:
        work = entry.work
        values = {
            CompositionDimension.GENRE: _term_category(work.genre),
            CompositionDimension.AUDIENCE: _term_category(work.audience),
            CompositionDimension.ADAPTATION: _term_category(work.adaptation),
            CompositionDimension.COLLECTION: _term_category(work.collection),
            CompositionDimension.SOURCE_TYPE: _source_category(entry, inventory),
        }
        for dimension, category in values.items():
            categories[dimension][category].append(entry.row_key)
    result = []
    total = len(entries)
    for dimension in CompositionDimension:
        ordered = sorted(
            categories[dimension].items(),
            key=lambda item: (-len(item[1]), item[0][1].casefold(), item[0][0]),
        )
        for (category_value, category_label), row_keys in ordered:
            sorted_keys = tuple(sorted(row_keys))
            result.append(
                CompositionDatum(
                    dimension=dimension,
                    dimension_label=_DIMENSION_LABELS[dimension],
                    category_value=category_value,
                    category_label=category_label,
                    work_row_keys=sorted_keys,
                    work_count=len(sorted_keys),
                    corpus_work_count=total,
                )
            )
    return tuple(result)


def _timeline(
    inventory: CorpusInventory,
    entries: tuple[_WorkEntry, ...],
) -> tuple[TimelineDatum, ...]:
    authors_by_id: dict[str, list[str]] = defaultdict(list)
    for author in inventory.authors:
        authors_by_id[author.author_id].append(author.display_name)
    timeline = []
    for entry in entries:
        work = entry.work
        asset_edition_ids = {
            asset.edition_id for asset in inventory.assets if asset.work_id == work.work_id
        }
        asset_source_ids = {
            asset.source_id for asset in inventory.assets if asset.work_id == work.work_id
        }
        editions = tuple(
            TimelineEditionDatum(
                edition_id=edition.edition_id,
                edition_label=edition.edition_label,
                edition_date=edition.edition_date,
            )
            for edition in sorted(
                (item for item in inventory.editions if item.edition_id in asset_edition_ids),
                key=lambda item: (item.edition_id, _canonical_model_key(item)),
            )
        )
        sources = tuple(
            TimelineSourceDatum(
                source_id=source.source_id,
                source_title=source.title,
                source_type_label=source.source_type.label,
            )
            for source in sorted(
                (item for item in inventory.sources if item.source_id in asset_source_ids),
                key=lambda item: (item.source_id, _canonical_model_key(item)),
            )
        )
        author_names = tuple(
            sorted(
                {
                    name
                    for contributor in work.contributors
                    for name in authors_by_id.get(
                        contributor.author_id,
                        [contributor.author_id],
                    )
                },
                key=str.casefold,
            )
        )
        timeline.append(
            TimelineDatum(
                row_key=entry.row_key,
                work_id=work.work_id,
                work_title=work.title_original,
                author_names=author_names,
                language=work.language,
                first_publication=work.first_publication,
                genre_label=work.genre.label,
                audience_label=work.audience.label,
                editions=editions,
                sources=sources,
            )
        )
    return tuple(
        sorted(
            timeline,
            key=lambda item: (
                item.first_publication.chronology_key or (10000, 10000),
                item.work_title.casefold(),
                item.row_key,
            ),
        )
    )


def _assets_for(
    entry: _WorkEntry,
    inventory: CorpusInventory,
) -> tuple[AssetRecord, ...]:
    return tuple(
        sorted(
            (asset for asset in inventory.assets if asset.work_id == entry.work.work_id),
            key=lambda item: (item.asset_id, _canonical_model_key(item)),
        )
    )


def _identity_base(entry: _WorkEntry, inventory: CorpusInventory) -> _CellBase:
    assets = _assets_for(entry, inventory)
    if not assets:
        return _CellBase(
            CompletenessStatus.MISSING,
            "The work has no analyzed-file mapping.",
            ("assets",),
        )
    if len(assets) > 1:
        return _CellBase(
            CompletenessStatus.CONFLICT,
            "More than one analyzed file is mapped to this work.",
            ("assets",),
        )
    asset = assets[0]
    files = tuple(item for item in inventory.validated_files if item.file_label == asset.file_label)
    if not files or not asset.mapping_confirmed:
        fields = ["file_label"] if not files else []
        if not asset.mapping_confirmed:
            fields.append("mapping_confirmed")
        return _CellBase(
            CompletenessStatus.MISSING,
            "The file-to-work identity is not fully confirmed.",
            tuple(fields),
        )
    if any(item.content_sha256 != asset.content_sha256 for item in files):
        return _CellBase(
            CompletenessStatus.CONFLICT,
            "The documented file hash conflicts with the intake catalog.",
            ("content_sha256",),
        )
    referenced_authors = {contributor.author_id for contributor in entry.work.contributors}
    resolved_authors = tuple(
        author for author in inventory.authors if author.author_id in referenced_authors
    )
    if not resolved_authors:
        return _CellBase(
            CompletenessStatus.MISSING,
            "Contributor identity is missing or unresolved.",
            ("contributors.author_id",),
        )
    if any(author.kind is AuthorKind.UNKNOWN for author in resolved_authors):
        return _CellBase(
            CompletenessStatus.WARNING,
            "Contributor identity is documented as unknown.",
            ("contributors.author.kind",),
        )
    return _CellBase(
        CompletenessStatus.COMPLETE,
        "Work identity, contributors, language, and file mapping are documented.",
    )


def _chronology_base(entry: _WorkEntry) -> _CellBase:
    value = entry.work.first_publication
    if value.mode is DateMode.UNKNOWN:
        return _CellBase(
            CompletenessStatus.MISSING,
            "First-publication chronology is explicitly unknown.",
            ("first_publication",),
        )
    if value.is_reversed:
        return _CellBase(
            CompletenessStatus.CONFLICT,
            "The first-publication date range is reversed.",
            ("first_publication",),
        )
    if value.mode in {DateMode.APPROXIMATE, DateMode.RANGE}:
        return _CellBase(
            CompletenessStatus.WARNING,
            "First-publication chronology is documented with uncertainty.",
            ("first_publication",),
        )
    return _CellBase(
        CompletenessStatus.COMPLETE,
        "First-publication chronology is documented.",
    )


def _edition_base(entry: _WorkEntry, inventory: CorpusInventory) -> _CellBase:
    assets = _assets_for(entry, inventory)
    edition_ids = {asset.edition_id for asset in assets}
    editions = tuple(edition for edition in inventory.editions if edition.edition_id in edition_ids)
    if not editions:
        return _CellBase(
            CompletenessStatus.MISSING,
            "The analyzed edition is missing or unresolved.",
            ("edition_id",),
        )
    if len(edition_ids) > 1 or len(editions) > 1:
        return _CellBase(
            CompletenessStatus.CONFLICT,
            "More than one analyzed edition is documented for this work.",
            ("edition_id",),
        )
    date_value = editions[0].edition_date
    if date_value.is_reversed:
        return _CellBase(
            CompletenessStatus.CONFLICT,
            "The analyzed-edition date range is reversed.",
            ("edition_date",),
        )
    if date_value.mode is DateMode.UNKNOWN:
        return _CellBase(
            CompletenessStatus.WARNING,
            "The analyzed edition is identified, but its date is unknown.",
            ("edition_date",),
        )
    if date_value.mode in {DateMode.APPROXIMATE, DateMode.RANGE}:
        return _CellBase(
            CompletenessStatus.WARNING,
            "The analyzed-edition date is documented with uncertainty.",
            ("edition_date",),
        )
    return _CellBase(CompletenessStatus.COMPLETE, "The analyzed edition is documented.")


def _source_base(entry: _WorkEntry, inventory: CorpusInventory) -> _CellBase:
    assets = _assets_for(entry, inventory)
    source_ids = {asset.source_id for asset in assets}
    sources = tuple(source for source in inventory.sources if source.source_id in source_ids)
    if not sources:
        return _CellBase(
            CompletenessStatus.MISSING,
            "The acquisition source is missing or unresolved.",
            ("source_id",),
        )
    source_terms = {
        (source.source_type.value, source.source_type.label, source.source_type.kind)
        for source in sources
    }
    if len(source_ids) > 1 or len(source_terms) > 1:
        return _CellBase(
            CompletenessStatus.CONFLICT,
            "Conflicting acquisition sources are documented for this work.",
            ("source_id", "source_type"),
        )
    if any(source.source_type.kind is TermKind.UNKNOWN for source in sources):
        return _CellBase(
            CompletenessStatus.WARNING,
            "The acquisition source is documented with an unknown source type.",
            ("source_type",),
        )
    return _CellBase(CompletenessStatus.COMPLETE, "The acquisition source is documented.")


def _classification_base(entry: _WorkEntry) -> _CellBase:
    terms = {
        "genre": entry.work.genre,
        "audience": entry.work.audience,
        "adaptation": entry.work.adaptation,
        "collection": entry.work.collection,
    }
    unknown = tuple(sorted(name for name, term in terms.items() if term.kind is TermKind.UNKNOWN))
    if unknown:
        return _CellBase(
            CompletenessStatus.WARNING,
            "One or more classification fields are explicitly unknown.",
            unknown,
        )
    return _CellBase(
        CompletenessStatus.COMPLETE,
        "Genre, audience, adaptation, and collection metadata are documented.",
    )


def _rights_base(entry: _WorkEntry, inventory: CorpusInventory) -> _CellBase:
    assets = _assets_for(entry, inventory)
    if not assets:
        return _CellBase(
            CompletenessStatus.MISSING,
            "Rights documentation cannot be linked without an analyzed asset.",
            ("rights_asset_ids",),
        )
    rights_by_id = defaultdict(list)
    for record in inventory.rights:
        rights_by_id[record.asset_id].append(record)
    missing = False
    conflict = False
    unresolved = False
    for asset in assets:
        if not asset.rights_chain_confirmed or asset.asset_id not in asset.rights_asset_ids:
            missing = True
        for rights_id in asset.rights_asset_ids:
            records = rights_by_id[rights_id]
            if not records:
                missing = True
                continue
            if len(records) > 1:
                conflict = True
            for record in records:
                if rights_id == asset.asset_id and record.source_id != asset.source_id:
                    conflict = True
                if record.rights_status in {
                    RightsStatus.UNKNOWN,
                    RightsStatus.PERMISSION_REQUIRED,
                }:
                    unresolved = True
    if conflict:
        return _CellBase(
            CompletenessStatus.CONFLICT,
            "Rights records or their source relationships conflict.",
            ("rights_asset_ids", "rights.source_id"),
        )
    if missing or unresolved:
        fields = ["rights_asset_ids"] if missing else []
        if unresolved:
            fields.append("rights_status")
        return _CellBase(
            CompletenessStatus.MISSING,
            "Rights documentation is missing, unconfirmed, or unresolved.",
            tuple(fields),
        )
    return _CellBase(
        CompletenessStatus.COMPLETE,
        "Rights documentation is complete; permissions are reported separately.",
    )


def _normalization_base(entry: _WorkEntry, inventory: CorpusInventory) -> _CellBase:
    assets = _assets_for(entry, inventory)
    if not assets:
        return _CellBase(
            CompletenessStatus.MISSING,
            "No normalization profile is linked to this work.",
            ("normalization_profile",),
        )
    missing_profile = any(asset.normalization_profile == "unknown" for asset in assets)
    missing_notes = any(
        asset.normalization_profile == "custom" and asset.normalization_notes is None
        for asset in assets
    )
    if missing_profile or missing_notes:
        fields = ["normalization_profile"] if missing_profile else []
        if missing_notes:
            fields.append("normalization_notes")
        return _CellBase(
            CompletenessStatus.MISSING,
            "The normalization profile is unknown or insufficiently documented.",
            tuple(fields),
        )
    return _CellBase(
        CompletenessStatus.COMPLETE,
        "The normalization profile is documented.",
    )


def _cell_base(
    entry: _WorkEntry,
    inventory: CorpusInventory,
    group: CompletenessGroup,
) -> _CellBase:
    if group is CompletenessGroup.IDENTITY:
        return _identity_base(entry, inventory)
    if group is CompletenessGroup.CHRONOLOGY:
        return _chronology_base(entry)
    if group is CompletenessGroup.EDITION:
        return _edition_base(entry, inventory)
    if group is CompletenessGroup.SOURCE:
        return _source_base(entry, inventory)
    if group is CompletenessGroup.CLASSIFICATION:
        return _classification_base(entry)
    if group is CompletenessGroup.RIGHTS:
        return _rights_base(entry, inventory)
    return _normalization_base(entry, inventory)


def _issue_group(issue: ValidationIssue) -> CompletenessGroup | None:
    code = issue.code
    if code in _CORPUS_LEVEL_CODES:
        return None
    if code in _RIGHTS_CODES:
        return CompletenessGroup.RIGHTS
    if code in _NORMALIZATION_CODES:
        return CompletenessGroup.NORMALIZATION
    if code in {IssueCode.GROUP_LABEL_REQUIRED}:
        return CompletenessGroup.CLASSIFICATION
    if code in {IssueCode.CONTROLLED_TERM_UNKNOWN, IssueCode.CONFOUND_METADATA_UNKNOWN}:
        return (
            CompletenessGroup.SOURCE
            if issue.entity_type == "source"
            else CompletenessGroup.CLASSIFICATION
        )
    if code in {IssueCode.CHRONOLOGY_REQUIRED}:
        return CompletenessGroup.CHRONOLOGY
    if code in {
        IssueCode.EDITION_DATE_UNKNOWN,
        IssueCode.EDITION_PRECEDES_PUBLICATION,
        IssueCode.DATE_ORDER_UNCERTAIN,
    }:
        return CompletenessGroup.EDITION
    if code is IssueCode.DATE_RANGE_REVERSED:
        return (
            CompletenessGroup.CHRONOLOGY
            if issue.entity_type == "work"
            else CompletenessGroup.EDITION
        )
    if code is IssueCode.DUPLICATE_EDITION_ID:
        return CompletenessGroup.EDITION
    if code is IssueCode.DUPLICATE_SOURCE_ID:
        return CompletenessGroup.SOURCE
    if code is IssueCode.EDITION_REFERENCE_MISSING:
        return (
            CompletenessGroup.SOURCE if issue.entity_type == "source" else CompletenessGroup.EDITION
        )
    if code in {IssueCode.SOURCE_REFERENCE_MISSING}:
        return CompletenessGroup.SOURCE
    if code is IssueCode.RELATIONSHIP_CONFLICT:
        return (
            CompletenessGroup.SOURCE
            if issue.field_path == "source_id"
            else CompletenessGroup.EDITION
        )
    if code is IssueCode.WORK_REFERENCE_MISSING and issue.entity_type == "edition":
        return CompletenessGroup.EDITION
    return CompletenessGroup.IDENTITY


def _issue_status(code: IssueCode) -> CompletenessStatus | None:
    return None if code in _ACTION_RESTRICTION_CODES else _ISSUE_STATUS_BY_CODE.get(code)


def _work_ids_for_issue(issue: ValidationIssue, inventory: CorpusInventory) -> set[str]:
    entity_id = issue.entity_id
    if entity_id is None or issue.entity_type == "inventory":
        return set()
    if issue.entity_type == "work":
        return {entity_id}
    if issue.entity_type == "author":
        return {
            work.work_id
            for work in inventory.works
            if any(item.author_id == entity_id for item in work.contributors)
        }
    if issue.entity_type == "edition":
        work_ids = {
            edition.work_id for edition in inventory.editions if edition.edition_id == entity_id
        }
        work_ids.update(
            asset.work_id for asset in inventory.assets if asset.edition_id == entity_id
        )
        return work_ids
    if issue.entity_type == "source":
        edition_ids = {
            source.edition_id for source in inventory.sources if source.source_id == entity_id
        }
        work_ids = {
            edition.work_id for edition in inventory.editions if edition.edition_id in edition_ids
        }
        work_ids.update(asset.work_id for asset in inventory.assets if asset.source_id == entity_id)
        return work_ids
    if issue.entity_type == "asset":
        if issue.code is IssueCode.DUPLICATE_FILE_LABEL:
            folded = entity_id.casefold()
            return {
                asset.work_id for asset in inventory.assets if asset.file_label.casefold() == folded
            }
        return {asset.work_id for asset in inventory.assets if asset.asset_id == entity_id}
    if issue.entity_type == "rights":
        return {
            asset.work_id
            for asset in inventory.assets
            if entity_id == asset.asset_id or entity_id in asset.rights_asset_ids
        }
    if issue.entity_type == "validated_file":
        folded = entity_id.casefold()
        return {
            asset.work_id for asset in inventory.assets if asset.file_label.casefold() == folded
        }
    return set()  # pragma: no cover - EntityType is closed by ValidationIssue.


def _issue_assignments(
    inventory: CorpusInventory,
    report: ValidationReport,
    entries: tuple[_WorkEntry, ...],
) -> tuple[
    dict[tuple[str, CompletenessGroup], tuple[ValidationIssue, ...]],
    tuple[ValidationIssue, ...],
]:
    row_keys_by_work_id: dict[str, tuple[str, ...]] = {}
    for work_id in sorted({entry.work.work_id for entry in entries}):
        row_keys_by_work_id[work_id] = tuple(
            entry.row_key for entry in entries if entry.work.work_id == work_id
        )
    assigned: dict[tuple[str, CompletenessGroup], list[ValidationIssue]] = defaultdict(list)
    corpus_issues = []
    for issue in report.issues:
        group = _issue_group(issue)
        work_ids = _work_ids_for_issue(issue, inventory)
        row_keys = {
            row_key for work_id in work_ids for row_key in row_keys_by_work_id.get(work_id, ())
        }
        if group is None or not row_keys:
            corpus_issues.append(issue)
            continue
        for row_key in sorted(row_keys):
            assigned[(row_key, group)].append(issue)
    frozen = {
        key: tuple(
            sorted(
                value,
                key=lambda item: (
                    item.code.value,
                    item.entity_type,
                    item.entity_id or "",
                    item.field_path,
                ),
            )
        )
        for key, value in assigned.items()
    }
    return frozen, tuple(corpus_issues)


def _highest_status(
    base: CompletenessStatus,
    issues: tuple[ValidationIssue, ...],
) -> CompletenessStatus:
    statuses = [base]
    statuses.extend(status for issue in issues if (status := _issue_status(issue.code)) is not None)
    return max(statuses, key=_STATUS_RANK.__getitem__)


def _highest_severity(issues: tuple[ValidationIssue, ...]) -> IssueSeverity | None:
    if not issues:
        return None
    return max((issue.severity for issue in issues), key=_SEVERITY_RANK.__getitem__)


def _summary(
    base: _CellBase,
    status: CompletenessStatus,
    issues: tuple[ValidationIssue, ...],
) -> str:
    effective = tuple(issue for issue in issues if _issue_status(issue.code) is not None)
    if not effective or status is base.status:
        return base.summary
    summaries = {
        CompletenessStatus.CONFLICT: "Conflicting documentation requires correction.",
        CompletenessStatus.MISSING: (
            "Required documentation is missing, unconfirmed, or unresolved."
        ),
        CompletenessStatus.WARNING: "Documentation is present with explicit uncertainty.",
        CompletenessStatus.COMPLETE: base.summary,
    }
    return summaries[status]


def _completeness(
    inventory: CorpusInventory,
    report: ValidationReport,
    entries: tuple[_WorkEntry, ...],
) -> tuple[tuple[CompletenessDatum, ...], tuple[ValidationIssue, ...]]:
    assignments, corpus_issues = _issue_assignments(inventory, report, entries)
    result = []
    for entry in entries:
        for group in CompletenessGroup:
            base = _cell_base(entry, inventory, group)
            issues = assignments.get((entry.row_key, group), ())
            status = _highest_status(base.status, issues)
            result.append(
                CompletenessDatum(
                    row_key=entry.row_key,
                    work_id=entry.work.work_id,
                    work_title=entry.work.title_original,
                    group=group,
                    group_label=_GROUP_LABELS[group],
                    status=status,
                    summary=_summary(base, status, issues),
                    field_paths=tuple(
                        sorted({*base.field_paths, *(issue.field_path for issue in issues)})
                    ),
                    issue_codes=tuple(
                        sorted({issue.code for issue in issues}, key=lambda item: item.value)
                    ),
                    highest_issue_severity=_highest_severity(issues),
                )
            )
    return tuple(result), corpus_issues


def build_review_projection(
    inventory: CorpusInventory,
    report: ValidationReport,
) -> CorpusReviewProjection:
    """Bind review summaries to one exact validated inventory."""

    digest = inventory_sha256(inventory)
    if report.inventory_sha256 != digest or report.purpose is not inventory.purpose:
        raise ReviewProjectionError(ReviewProjectionErrorCode.STALE_VALIDATION_REPORT)
    entries = _work_entries(inventory)
    completeness, corpus_issues = _completeness(inventory, report, entries)
    return CorpusReviewProjection(
        inventory_sha256=digest,
        corpus_work_count=len(entries),
        composition=_composition(inventory, entries),
        timeline=_timeline(inventory, entries),
        completeness=completeness,
        corpus_issues=corpus_issues,
    )


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
        raise ReviewProjectionError(
            ReviewProjectionErrorCode.CSV_POLICY_REJECTED,
            error.code,
        ) from None


def export_composition_csv(
    projection: CorpusReviewProjection,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
) -> bytes:
    """Export the exact composition projection under the P003 CSV policy."""

    fieldnames = (
        "inventory_sha256",
        "dimension",
        "dimension_label",
        "category_value",
        "category_label",
        "work_count",
        "corpus_work_count",
        "share_percent",
        "work_row_keys",
    )
    rows = [
        {
            "inventory_sha256": projection.inventory_sha256,
            "dimension": item.dimension.value,
            "dimension_label": item.dimension_label,
            "category_value": item.category_value,
            "category_label": item.category_label,
            "work_count": str(item.work_count),
            "corpus_work_count": str(item.corpus_work_count),
            "share_percent": f"{100 * item.work_count / item.corpus_work_count:.4f}",
            "work_row_keys": ";".join(item.work_row_keys),
        }
        for item in projection.composition
    ]
    payload = _write_csv(fieldnames, rows)
    _validate_generated_csv(payload, "delta-corpus-composition.csv", limits)
    return payload


def export_completeness_csv(
    projection: CorpusReviewProjection,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
) -> bytes:
    """Export one row per projected work/group cell under the P003 CSV policy."""

    fieldnames = (
        "inventory_sha256",
        "row_key",
        "work_id",
        "work_title",
        "group",
        "group_label",
        "status",
        "summary",
        "field_paths",
        "issue_codes",
        "highest_issue_severity",
    )
    rows = [
        {
            "inventory_sha256": projection.inventory_sha256,
            "row_key": item.row_key,
            "work_id": item.work_id,
            "work_title": item.work_title,
            "group": item.group.value,
            "group_label": item.group_label,
            "status": item.status.value,
            "summary": item.summary,
            "field_paths": ";".join(item.field_paths),
            "issue_codes": ";".join(code.value for code in item.issue_codes),
            "highest_issue_severity": (
                "" if item.highest_issue_severity is None else item.highest_issue_severity.value
            ),
        }
        for item in projection.completeness
    ]
    payload = _write_csv(fieldnames, rows)
    _validate_generated_csv(payload, "delta-metadata-completeness.csv", limits)
    return payload


__all__ = [
    "CompletenessDatum",
    "CompletenessGroup",
    "CompletenessStatus",
    "CompositionDatum",
    "CompositionDimension",
    "CorpusReviewProjection",
    "ReviewProjectionError",
    "ReviewProjectionErrorCode",
    "build_review_projection",
    "export_completeness_csv",
    "export_composition_csv",
    "TimelineDatum",
    "TimelineEditionDatum",
    "TimelineSourceDatum",
]
