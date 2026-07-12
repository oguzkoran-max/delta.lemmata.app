"""Purpose-aware, deterministic validation for P004 corpus inventories."""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
from typing import Literal

from pydantic import Field

from delta_lemmata.corpus_models import (
    DEFAULT_VOCABULARY,
    SHA256_PATTERN,
    ContributorRole,
    DateMode,
    EditionRecord,
    FrozenModel,
    PurposeId,
    SourceRecord,
    TermKind,
    VocabularyProfile,
    VocabularyTerm,
    WorkRecord,
)
from delta_lemmata.inventory import (
    CorpusInventory,
    asset_allows_public_redistribution,
    inventory_sha256,
)
from delta_lemmata.provenance import canonical_json_bytes
from delta_lemmata.rights import AssetRightsRecord, PermissionState, RightsStatus

type EntityType = Literal[
    "inventory",
    "author",
    "work",
    "edition",
    "source",
    "validated_file",
    "asset",
    "rights",
]


class IssueSeverity(StrEnum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFORMATION = "information"


class IssueCode(StrEnum):
    DUPLICATE_AUTHOR_ID = "META_DUPLICATE_AUTHOR_ID"
    DUPLICATE_WORK_ID = "META_DUPLICATE_WORK_ID"
    DUPLICATE_EDITION_ID = "META_DUPLICATE_EDITION_ID"
    DUPLICATE_SOURCE_ID = "META_DUPLICATE_SOURCE_ID"
    DUPLICATE_ASSET_ID = "META_DUPLICATE_ASSET_ID"
    DUPLICATE_RIGHTS_ASSET_ID = "META_DUPLICATE_RIGHTS_ASSET_ID"
    DUPLICATE_FILE_LABEL = "META_DUPLICATE_FILE_LABEL"
    DUPLICATE_VALIDATED_FILE = "META_DUPLICATE_VALIDATED_FILE"
    FILE_REFERENCE_MISSING = "META_FILE_REFERENCE_MISSING"
    FILE_HASH_MISMATCH = "META_FILE_HASH_MISMATCH"
    UNMAPPED_VALIDATED_FILE = "META_UNMAPPED_VALIDATED_FILE"
    AUTHOR_REFERENCE_MISSING = "META_AUTHOR_REFERENCE_MISSING"
    AUTHOR_ROLE_REQUIRED = "META_AUTHOR_ROLE_REQUIRED"
    WORK_REFERENCE_MISSING = "META_WORK_REFERENCE_MISSING"
    EDITION_REFERENCE_MISSING = "META_EDITION_REFERENCE_MISSING"
    SOURCE_REFERENCE_MISSING = "META_SOURCE_REFERENCE_MISSING"
    ASSET_REFERENCE_MISSING = "META_ASSET_REFERENCE_MISSING"
    RIGHTS_REFERENCE_MISSING = "META_RIGHTS_REFERENCE_MISSING"
    RIGHTS_CHAIN_SELF_MISSING = "META_RIGHTS_CHAIN_SELF_MISSING"
    RIGHTS_CHAIN_UNCONFIRMED = "META_RIGHTS_CHAIN_UNCONFIRMED"
    RIGHTS_DEPENDENCY_MISSING = "META_RIGHTS_DEPENDENCY_MISSING"
    RELATIONSHIP_CONFLICT = "META_RELATIONSHIP_CONFLICT"
    FILE_MAPPING_UNCONFIRMED = "META_FILE_MAPPING_UNCONFIRMED"
    WORK_ASSET_MISSING = "META_WORK_ASSET_MISSING"
    MULTIPLE_ASSETS_PER_WORK = "META_MULTIPLE_ASSETS_PER_WORK"
    GROUP_LABEL_REQUIRED = "META_GROUP_LABEL_REQUIRED"
    CHRONOLOGY_REQUIRED = "META_CHRONOLOGY_REQUIRED"
    WORK_COUNT_EXPLORATORY = "META_WORK_COUNT_EXPLORATORY"
    CHRONOLOGY_POINTS_EXPLORATORY = "META_CHRONOLOGY_POINTS_EXPLORATORY"
    STYLE_AUTHOR_SET_MIXED = "META_STYLE_AUTHOR_SET_MIXED"
    STYLE_LANGUAGE_MIXED = "META_STYLE_LANGUAGE_MIXED"
    DATE_RANGE_REVERSED = "META_DATE_RANGE_REVERSED"
    EDITION_DATE_UNKNOWN = "META_EDITION_DATE_UNKNOWN"
    EDITION_PRECEDES_PUBLICATION = "META_EDITION_PRECEDES_PUBLICATION"
    DATE_ORDER_UNCERTAIN = "META_DATE_ORDER_UNCERTAIN"
    CONTROLLED_TERM_UNKNOWN = "META_CONTROLLED_TERM_UNKNOWN"
    CONFOUND_METADATA_UNKNOWN = "META_CONFOUND_METADATA_UNKNOWN"
    NORMALIZATION_PROFILE_UNKNOWN = "META_NORMALIZATION_PROFILE_UNKNOWN"
    NORMALIZATION_DETAILS_REQUIRED = "META_NORMALIZATION_DETAILS_REQUIRED"
    UPLOAD_PERMISSION_REQUIRED = "RIGHTS_UPLOAD_PERMISSION_REQUIRED"
    ANALYSIS_PERMISSION_REQUIRED = "RIGHTS_ANALYSIS_PERMISSION_REQUIRED"
    RIGHTS_STATUS_UNRESOLVED = "RIGHTS_STATUS_UNRESOLVED"
    RIGHTS_SOURCE_CONFLICT = "RIGHTS_SOURCE_CONFLICT"
    RIGHTS_SOURCE_REFERENCE_MISSING = "RIGHTS_SOURCE_REFERENCE_MISSING"


class ValidationIssue(FrozenModel):
    code: IssueCode
    severity: IssueSeverity
    entity_type: EntityType
    entity_id: str | None
    row_number: int | None = Field(default=None, ge=1)
    field_path: str = Field(min_length=1)
    message_key: str = Field(pattern=r"^corpus\.validation\.[a-z0-9_.-]+$")
    message: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    how_to_fix: str = Field(min_length=1)


class CorpusReadiness(FrozenModel):
    independent_work_count: int = Field(ge=0)
    chronology_point_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    information_count: int = Field(ge=0)
    rights_restriction_count: int = Field(ge=0)
    style_over_time_minimum_met: bool | None
    threshold_is_sufficiency_claim: Literal[False] = False
    exploratory: bool


class ValidationReport(FrozenModel):
    schema_version: Literal["corpus-validation-v1"] = "corpus-validation-v1"
    inventory_sha256: str = Field(pattern=SHA256_PATTERN)
    purpose: PurposeId
    blocked: bool
    issues: tuple[ValidationIssue, ...]
    readiness: CorpusReadiness


_SEVERITY_ORDER = {
    IssueSeverity.BLOCKER: 0,
    IssueSeverity.WARNING: 1,
    IssueSeverity.INFORMATION: 2,
}

_GUIDANCE: dict[IssueCode, tuple[str, str, str]] = {
    IssueCode.DUPLICATE_AUTHOR_ID: (
        "The author identifier is used more than once.",
        "Stable identifiers must refer to one author record.",
        "Keep one record or assign a different confirmed author_id.",
    ),
    IssueCode.DUPLICATE_WORK_ID: (
        "The work identifier is used more than once.",
        "A work_id must identify one independent work.",
        "Keep one record or assign a different confirmed work_id.",
    ),
    IssueCode.DUPLICATE_EDITION_ID: (
        "The edition identifier is used more than once.",
        "An edition_id must identify one analyzed edition.",
        "Keep one edition record or assign a different edition_id.",
    ),
    IssueCode.DUPLICATE_SOURCE_ID: (
        "The source identifier is used more than once.",
        "A source_id must identify one documented source.",
        "Keep one source record or assign a different source_id.",
    ),
    IssueCode.DUPLICATE_ASSET_ID: (
        "The asset identifier is used more than once.",
        "Each analyzed file needs one stable scholarly asset identity.",
        "Assign a unique asset_id to each analyzed TXT.",
    ),
    IssueCode.DUPLICATE_RIGHTS_ASSET_ID: (
        "More than one rights record refers to this asset.",
        "Conflicting rights records cannot be resolved silently.",
        "Retain one reviewed rights record for the asset.",
    ),
    IssueCode.DUPLICATE_FILE_LABEL: (
        "The same file label appears more than once.",
        "Exact file-to-work mapping requires unique labels.",
        "Rename one file and confirm the mapping again.",
    ),
    IssueCode.DUPLICATE_VALIDATED_FILE: (
        "The P003 file catalog contains the same label more than once.",
        "A file label must identify one validated byte sequence.",
        "Rebuild the intake catalog from unique validated files.",
    ),
    IssueCode.FILE_REFERENCE_MISSING: (
        "The documented asset has no exact match in the P003 file catalog.",
        "A confirmation cannot replace proof that the file passed secure intake.",
        "Upload the file again or correct the exact file label.",
    ),
    IssueCode.FILE_HASH_MISMATCH: (
        "The asset hash differs from the P003-validated file hash.",
        "The metadata may describe different bytes from those accepted at intake.",
        "Discard the mapping and map the validated file again.",
    ),
    IssueCode.UNMAPPED_VALIDATED_FILE: (
        "A P003-validated file is not represented by a scholarly asset.",
        "Every accepted corpus text must be documented or explicitly removed.",
        "Create and confirm its asset-to-work mapping or remove it from the batch.",
    ),
    IssueCode.AUTHOR_REFERENCE_MISSING: (
        "A contributor points to an author that is not documented.",
        "Contributor roles need a stable author identity.",
        "Add the author record or correct the contributor author_id.",
    ),
    IssueCode.AUTHOR_ROLE_REQUIRED: (
        "The work has no contributor with the author role.",
        "Anonymous and unknown authors still need an explicit authorship record.",
        "Add an author-role contributor, using anonymous or unknown when needed.",
    ),
    IssueCode.WORK_REFERENCE_MISSING: (
        "A record points to a work that is not documented.",
        "The file, edition, and work relationship must be explicit.",
        "Add the work record or correct the work_id.",
    ),
    IssueCode.EDITION_REFERENCE_MISSING: (
        "A record points to an edition that is not documented.",
        "The analyzed text must be tied to a specific edition assertion.",
        "Add the edition record or correct the edition_id.",
    ),
    IssueCode.SOURCE_REFERENCE_MISSING: (
        "An asset points to a source that is not documented.",
        "Source evidence is required to audit the corpus.",
        "Add the source record or correct the source_id.",
    ),
    IssueCode.ASSET_REFERENCE_MISSING: (
        "A rights record is not referenced by any analyzed asset's rights chain.",
        "Unattached rights evidence cannot govern a retained corpus asset.",
        "Remove the orphan record or add its asset_id to the correct rights chain.",
    ),
    IssueCode.RIGHTS_REFERENCE_MISSING: (
        "The analyzed asset has no rights record.",
        "Delta must know whether upload and analysis were permitted.",
        "Complete and confirm the rights questionnaire for this asset.",
    ),
    IssueCode.RIGHTS_CHAIN_SELF_MISSING: (
        "The analyzed asset is absent from its own rights dependency chain.",
        "Delta must assess the analyzed file as well as any underlying layers.",
        "Add the asset_id to rights_asset_ids and document its rights record.",
    ),
    IssueCode.RIGHTS_CHAIN_UNCONFIRMED: (
        "The relevant rights layers have not been confirmed as complete.",
        "An omitted underlying work or edition layer could make export unsafe.",
        "Review all applicable layers and explicitly confirm the rights chain.",
    ),
    IssueCode.RIGHTS_DEPENDENCY_MISSING: (
        "A required rights layer has no rights record.",
        "Public export and analysis remain closed until every declared layer is reviewed.",
        "Add the missing rights record or correct rights_asset_ids.",
    ),
    IssueCode.RELATIONSHIP_CONFLICT: (
        "The work, edition, and source identifiers disagree.",
        "A contradictory chain would describe the wrong analyzed text.",
        "Make the asset, edition, and source point to the same work chain.",
    ),
    IssueCode.FILE_MAPPING_UNCONFIRMED: (
        "The proposed file-to-work mapping has not been confirmed.",
        "Delta never assigns scholarly metadata through an unreviewed guess.",
        "Review the exact label match and confirm the mapping.",
    ),
    IssueCode.WORK_ASSET_MISSING: (
        "The work has no analyzed TXT asset.",
        "Every independent work in this inventory must represent one analyzed text.",
        "Map one validated TXT asset to the work.",
    ),
    IssueCode.MULTIPLE_ASSETS_PER_WORK: (
        "More than one analyzed TXT is mapped to the work.",
        "Delta v0.1 treats one TXT as one independent work.",
        "Retain one analyzed TXT or describe the files as separate works.",
    ),
    IssueCode.GROUP_LABEL_REQUIRED: (
        "The work has no group label.",
        "Group Comparison needs an explicit grouping variable.",
        "Enter the intended group label for this work.",
    ),
    IssueCode.CHRONOLOGY_REQUIRED: (
        "The work has no usable first-publication chronology.",
        "Style Over Time must order works by work history, not edition date.",
        "Enter an exact, approximate, or range first-publication date.",
    ),
    IssueCode.WORK_COUNT_EXPLORATORY: (
        "The corpus contains fewer than six independent works.",
        "The accepted minimum-design rule forces a cautious exploratory label.",
        "Add independent works or continue with the exploratory status visible.",
    ),
    IssueCode.CHRONOLOGY_POINTS_EXPLORATORY: (
        "The corpus contains fewer than three chronology points.",
        "A smaller temporal spread cannot support the standard workflow label.",
        "Add distinct chronology points or continue as exploratory.",
    ),
    IssueCode.STYLE_AUTHOR_SET_MIXED: (
        "The Style Over Time corpus does not use one consistent author set.",
        "A changing author set would confound chronology with authorship.",
        "Use works with the same documented author set or choose another workflow.",
    ),
    IssueCode.STYLE_LANGUAGE_MIXED: (
        "The Style Over Time corpus contains more than one language.",
        "Language differences can dominate the stylistic distances under study.",
        "Use one language or document separate language-specific experiments.",
    ),
    IssueCode.DATE_RANGE_REVERSED: (
        "A date range starts after it ends.",
        "A reversed interval cannot establish a valid chronology.",
        "Correct the start and end years without silently swapping them.",
    ),
    IssueCode.EDITION_DATE_UNKNOWN: (
        "The analyzed edition date is unknown.",
        "Edition timing can confound apparent stylistic change.",
        "Document the edition date or retain Unknown as a visible warning.",
    ),
    IssueCode.EDITION_PRECEDES_PUBLICATION: (
        "The edition date precedes the work's first-publication date.",
        "The chronology is internally contradictory.",
        "Correct the work date, edition date, or relationship.",
    ),
    IssueCode.DATE_ORDER_UNCERTAIN: (
        "The edition and first-publication ranges overlap ambiguously.",
        "The available dates do not establish a safe order.",
        "Review the ranges or retain the uncertainty as a visible warning.",
    ),
    IssueCode.CONTROLLED_TERM_UNKNOWN: (
        "A controlled value is not in the selected vocabulary version.",
        "Silent spelling variants would fragment summaries and exports.",
        "Choose a listed value or record a normalized custom term.",
    ),
    IssueCode.CONFOUND_METADATA_UNKNOWN: (
        "A possible corpus confound is documented as Unknown.",
        "Genre, audience, adaptation, collection, or source can affect style.",
        "Research the field or retain Unknown as an explicit limitation.",
    ),
    IssueCode.NORMALIZATION_PROFILE_UNKNOWN: (
        "The normalization profile is missing or unknown.",
        "Text preparation can change the features used by stylometry.",
        "Choose a versioned profile or document a custom profile.",
    ),
    IssueCode.NORMALIZATION_DETAILS_REQUIRED: (
        "The custom normalization profile has no description.",
        "A custom transformation must be reproducible.",
        "Describe the normalization steps and tools.",
    ),
    IssueCode.UPLOAD_PERMISSION_REQUIRED: (
        "Upload permission is not explicitly permitted.",
        "Unknown and prohibited actions remain closed by default.",
        "Confirm evidence for upload permission or remove the asset.",
    ),
    IssueCode.ANALYSIS_PERMISSION_REQUIRED: (
        "Analysis permission is not explicitly permitted.",
        "Delta cannot analyze an asset under an unresolved action permission.",
        "Confirm evidence for analysis permission or remove the asset.",
    ),
    IssueCode.RIGHTS_STATUS_UNRESOLVED: (
        "The overall rights status remains unresolved.",
        "The record may still restrict export or redistribution.",
        "Review the evidence and keep unresolved actions closed.",
    ),
    IssueCode.RIGHTS_SOURCE_CONFLICT: (
        "The asset and rights record point to different sources.",
        "Rights evidence may apply to a different edition or file.",
        "Correct the rights source_id after reviewing the evidence.",
    ),
    IssueCode.RIGHTS_SOURCE_REFERENCE_MISSING: (
        "A rights layer points to a source that is not documented.",
        "Rights evidence cannot be audited without its source record.",
        "Add the source record or correct the rights source_id.",
    ),
}


def _issue(
    code: IssueCode,
    severity: IssueSeverity,
    entity_type: EntityType,
    entity_id: str | None,
    field_path: str,
) -> ValidationIssue:
    message, why_it_matters, how_to_fix = _GUIDANCE[code]
    return ValidationIssue(
        code=code,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        field_path=field_path,
        message_key=f"corpus.validation.{code.value.lower()}",
        message=message,
        why_it_matters=why_it_matters,
        how_to_fix=how_to_fix,
    )


def _duplicate_values(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted(value for value, count in Counter(values).items() if count > 1))


def _canonical_order[RecordT: FrozenModel](
    records: tuple[RecordT, ...],
) -> tuple[RecordT, ...]:
    return tuple(
        sorted(
            records,
            key=lambda record: canonical_json_bytes(record.model_dump(mode="json")),
        )
    )


def _append_duplicate_issues(
    issues: list[ValidationIssue],
    values: list[str],
    code: IssueCode,
    entity_type: EntityType,
    field_path: str,
) -> None:
    for value in _duplicate_values(values):
        issues.append(_issue(code, IssueSeverity.BLOCKER, entity_type, value, field_path))


def _validate_term(
    issues: list[ValidationIssue],
    term: VocabularyTerm,
    allowed: tuple[str, ...],
    entity_type: Literal["work", "source"],
    entity_id: str,
    field_path: str,
) -> None:
    if term.kind is TermKind.CONTROLLED and term.value not in allowed:
        issues.append(
            _issue(
                IssueCode.CONTROLLED_TERM_UNKNOWN,
                IssueSeverity.BLOCKER,
                entity_type,
                entity_id,
                field_path,
            )
        )
    if term.kind is TermKind.UNKNOWN:
        issues.append(
            _issue(
                IssueCode.CONFOUND_METADATA_UNKNOWN,
                IssueSeverity.WARNING,
                entity_type,
                entity_id,
                field_path,
            )
        )


def _validate_duplicates(inventory: CorpusInventory, issues: list[ValidationIssue]) -> None:
    specifications: tuple[tuple[list[str], IssueCode, EntityType, str], ...] = (
        (
            [record.author_id for record in inventory.authors],
            IssueCode.DUPLICATE_AUTHOR_ID,
            "author",
            "author_id",
        ),
        (
            [record.work_id for record in inventory.works],
            IssueCode.DUPLICATE_WORK_ID,
            "work",
            "work_id",
        ),
        (
            [record.edition_id for record in inventory.editions],
            IssueCode.DUPLICATE_EDITION_ID,
            "edition",
            "edition_id",
        ),
        (
            [record.source_id for record in inventory.sources],
            IssueCode.DUPLICATE_SOURCE_ID,
            "source",
            "source_id",
        ),
        (
            [record.asset_id for record in inventory.assets],
            IssueCode.DUPLICATE_ASSET_ID,
            "asset",
            "asset_id",
        ),
        (
            [record.asset_id for record in inventory.rights],
            IssueCode.DUPLICATE_RIGHTS_ASSET_ID,
            "rights",
            "asset_id",
        ),
        (
            [record.file_label.casefold() for record in inventory.assets],
            IssueCode.DUPLICATE_FILE_LABEL,
            "asset",
            "file_label",
        ),
        (
            [record.file_label.casefold() for record in inventory.validated_files],
            IssueCode.DUPLICATE_VALIDATED_FILE,
            "validated_file",
            "file_label",
        ),
    )
    for values, code, entity_type, field_path in specifications:
        _append_duplicate_issues(issues, values, code, entity_type, field_path)


def _validate_file_catalog(
    inventory: CorpusInventory,
    issues: list[ValidationIssue],
) -> None:
    files_by_label: dict[str, list[str]] = {}
    for record in _canonical_order(inventory.validated_files):
        files_by_label.setdefault(record.file_label, []).append(record.content_sha256)
    asset_labels = {record.file_label for record in inventory.assets}
    for asset in inventory.assets:
        validated_hashes = files_by_label.get(asset.file_label)
        if validated_hashes is None:
            issues.append(
                _issue(
                    IssueCode.FILE_REFERENCE_MISSING,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "file_label",
                )
            )
        elif asset.content_sha256 not in validated_hashes:
            issues.append(
                _issue(
                    IssueCode.FILE_HASH_MISMATCH,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "content_sha256",
                )
            )
    for validated_file in inventory.validated_files:
        if validated_file.file_label not in asset_labels:
            issues.append(
                _issue(
                    IssueCode.UNMAPPED_VALIDATED_FILE,
                    IssueSeverity.BLOCKER,
                    "validated_file",
                    validated_file.file_label,
                    "file_label",
                )
            )


def _validate_work_records(
    inventory: CorpusInventory,
    issues: list[ValidationIssue],
    vocabulary: VocabularyProfile,
    author_ids: set[str],
) -> None:
    for work in inventory.works:
        if work.first_publication.is_reversed:
            issues.append(
                _issue(
                    IssueCode.DATE_RANGE_REVERSED,
                    IssueSeverity.BLOCKER,
                    "work",
                    work.work_id,
                    "first_publication",
                )
            )
        if not any(contributor.role is ContributorRole.AUTHOR for contributor in work.contributors):
            issues.append(
                _issue(
                    IssueCode.AUTHOR_ROLE_REQUIRED,
                    IssueSeverity.BLOCKER,
                    "work",
                    work.work_id,
                    "contributors",
                )
            )
        for contributor in work.contributors:
            if contributor.author_id not in author_ids:
                issues.append(
                    _issue(
                        IssueCode.AUTHOR_REFERENCE_MISSING,
                        IssueSeverity.BLOCKER,
                        "work",
                        work.work_id,
                        "contributors.author_id",
                    )
                )
        for term, allowed, field_path in (
            (work.genre, vocabulary.genres, "genre"),
            (work.audience, vocabulary.audiences, "audience"),
            (work.adaptation, vocabulary.adaptation_statuses, "adaptation"),
            (work.collection, vocabulary.collection_statuses, "collection"),
        ):
            _validate_term(issues, term, allowed, "work", work.work_id, field_path)
        if inventory.purpose is PurposeId.GROUP_COMPARISON and work.group_label is None:
            issues.append(
                _issue(
                    IssueCode.GROUP_LABEL_REQUIRED,
                    IssueSeverity.BLOCKER,
                    "work",
                    work.work_id,
                    "group_label",
                )
            )
        if (
            inventory.purpose is PurposeId.STYLE_OVER_TIME
            and work.first_publication.mode is DateMode.UNKNOWN
        ):
            issues.append(
                _issue(
                    IssueCode.CHRONOLOGY_REQUIRED,
                    IssueSeverity.BLOCKER,
                    "work",
                    work.work_id,
                    "first_publication",
                )
            )


def _validate_edition_records(
    inventory: CorpusInventory,
    issues: list[ValidationIssue],
    works_by_id: dict[str, WorkRecord],
) -> None:
    for edition in inventory.editions:
        work = works_by_id.get(edition.work_id)
        if work is None:
            issues.append(
                _issue(
                    IssueCode.WORK_REFERENCE_MISSING,
                    IssueSeverity.BLOCKER,
                    "edition",
                    edition.edition_id,
                    "work_id",
                )
            )
            continue
        if edition.edition_date.mode is DateMode.UNKNOWN:
            issues.append(
                _issue(
                    IssueCode.EDITION_DATE_UNKNOWN,
                    IssueSeverity.WARNING,
                    "edition",
                    edition.edition_id,
                    "edition_date",
                )
            )
            continue
        if edition.edition_date.is_reversed:
            issues.append(
                _issue(
                    IssueCode.DATE_RANGE_REVERSED,
                    IssueSeverity.BLOCKER,
                    "edition",
                    edition.edition_id,
                    "edition_date",
                )
            )
            continue
        if work.first_publication.is_reversed:
            continue
        publication_bounds = work.first_publication.bounds
        edition_bounds = edition.edition_date.bounds
        if publication_bounds is None or edition_bounds is None:
            continue
        if edition_bounds[1] < publication_bounds[0] and DateMode.APPROXIMATE not in {
            edition.edition_date.mode,
            work.first_publication.mode,
        }:
            issues.append(
                _issue(
                    IssueCode.EDITION_PRECEDES_PUBLICATION,
                    IssueSeverity.BLOCKER,
                    "edition",
                    edition.edition_id,
                    "edition_date",
                )
            )
        elif edition_bounds[0] < publication_bounds[1]:
            issues.append(
                _issue(
                    IssueCode.DATE_ORDER_UNCERTAIN,
                    IssueSeverity.WARNING,
                    "edition",
                    edition.edition_id,
                    "edition_date",
                )
            )


def _validate_source_records(
    inventory: CorpusInventory,
    issues: list[ValidationIssue],
    vocabulary: VocabularyProfile,
    edition_ids: set[str],
) -> None:
    for source in inventory.sources:
        if source.edition_id not in edition_ids:
            issues.append(
                _issue(
                    IssueCode.EDITION_REFERENCE_MISSING,
                    IssueSeverity.BLOCKER,
                    "source",
                    source.source_id,
                    "edition_id",
                )
            )
        _validate_term(
            issues,
            source.source_type,
            vocabulary.source_types,
            "source",
            source.source_id,
            "source_type",
        )


def _validate_rights(
    issues: list[ValidationIssue],
    rights_asset_id: str,
    rights: AssetRightsRecord,
) -> None:
    if rights.permissions.upload is not PermissionState.PERMITTED:
        issues.append(
            _issue(
                IssueCode.UPLOAD_PERMISSION_REQUIRED,
                IssueSeverity.BLOCKER,
                "rights",
                rights_asset_id,
                "permissions.upload",
            )
        )
    if rights.permissions.analysis is not PermissionState.PERMITTED:
        issues.append(
            _issue(
                IssueCode.ANALYSIS_PERMISSION_REQUIRED,
                IssueSeverity.BLOCKER,
                "rights",
                rights_asset_id,
                "permissions.analysis",
            )
        )
    if rights.rights_status in {RightsStatus.UNKNOWN, RightsStatus.PERMISSION_REQUIRED}:
        issues.append(
            _issue(
                IssueCode.RIGHTS_STATUS_UNRESOLVED,
                IssueSeverity.WARNING,
                "rights",
                rights_asset_id,
                "rights_status",
            )
        )


def _validate_asset_records(
    inventory: CorpusInventory,
    issues: list[ValidationIssue],
    vocabulary: VocabularyProfile,
    works_by_id: dict[str, WorkRecord],
    editions_by_id: dict[str, EditionRecord],
    sources_by_id: dict[str, SourceRecord],
    rights_by_asset: dict[str, AssetRightsRecord],
) -> None:
    for asset in inventory.assets:
        if not asset.mapping_confirmed:
            issues.append(
                _issue(
                    IssueCode.FILE_MAPPING_UNCONFIRMED,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "mapping_confirmed",
                )
            )
        work = works_by_id.get(asset.work_id)
        edition = editions_by_id.get(asset.edition_id)
        source = sources_by_id.get(asset.source_id)
        if work is None:
            issues.append(
                _issue(
                    IssueCode.WORK_REFERENCE_MISSING,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "work_id",
                )
            )
        if edition is None:
            issues.append(
                _issue(
                    IssueCode.EDITION_REFERENCE_MISSING,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "edition_id",
                )
            )
        elif edition.work_id != asset.work_id:
            issues.append(
                _issue(
                    IssueCode.RELATIONSHIP_CONFLICT,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "edition_id",
                )
            )
        if source is None:
            issues.append(
                _issue(
                    IssueCode.SOURCE_REFERENCE_MISSING,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "source_id",
                )
            )
        elif source.edition_id != asset.edition_id:
            issues.append(
                _issue(
                    IssueCode.RELATIONSHIP_CONFLICT,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "source_id",
                )
            )
        if asset.asset_id not in asset.rights_asset_ids:
            issues.append(
                _issue(
                    IssueCode.RIGHTS_CHAIN_SELF_MISSING,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "rights_asset_ids",
                )
            )
        if not asset.rights_chain_confirmed:
            issues.append(
                _issue(
                    IssueCode.RIGHTS_CHAIN_UNCONFIRMED,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "rights_chain_confirmed",
                )
            )
        for rights_asset_id in asset.rights_asset_ids:
            rights = rights_by_asset.get(rights_asset_id)
            if rights is None:
                code = (
                    IssueCode.RIGHTS_REFERENCE_MISSING
                    if rights_asset_id == asset.asset_id
                    else IssueCode.RIGHTS_DEPENDENCY_MISSING
                )
                issues.append(
                    _issue(
                        code,
                        IssueSeverity.BLOCKER,
                        "asset",
                        asset.asset_id,
                        "rights_asset_ids",
                    )
                )
                continue
            if rights.source_id not in sources_by_id:
                issues.append(
                    _issue(
                        IssueCode.RIGHTS_SOURCE_REFERENCE_MISSING,
                        IssueSeverity.BLOCKER,
                        "rights",
                        rights_asset_id,
                        "source_id",
                    )
                )
            if rights_asset_id == asset.asset_id and rights.source_id != asset.source_id:
                issues.append(
                    _issue(
                        IssueCode.RIGHTS_SOURCE_CONFLICT,
                        IssueSeverity.BLOCKER,
                        "rights",
                        rights_asset_id,
                        "source_id",
                    )
                )
            _validate_rights(issues, rights_asset_id, rights)
        if (
            asset.normalization_profile not in vocabulary.normalization_profiles
            or asset.normalization_profile == "unknown"
        ):
            issues.append(
                _issue(
                    IssueCode.NORMALIZATION_PROFILE_UNKNOWN,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "normalization_profile",
                )
            )
        if asset.normalization_profile == "custom" and asset.normalization_notes is None:
            issues.append(
                _issue(
                    IssueCode.NORMALIZATION_DETAILS_REQUIRED,
                    IssueSeverity.BLOCKER,
                    "asset",
                    asset.asset_id,
                    "normalization_notes",
                )
            )


def _validate_one_asset_per_work(
    inventory: CorpusInventory,
    issues: list[ValidationIssue],
) -> None:
    counts = Counter(asset.work_id for asset in inventory.assets)
    for work in inventory.works:
        count = counts[work.work_id]
        if count == 0:
            issues.append(
                _issue(
                    IssueCode.WORK_ASSET_MISSING,
                    IssueSeverity.BLOCKER,
                    "work",
                    work.work_id,
                    "assets",
                )
            )
        elif count > 1:
            issues.append(
                _issue(
                    IssueCode.MULTIPLE_ASSETS_PER_WORK,
                    IssueSeverity.BLOCKER,
                    "work",
                    work.work_id,
                    "assets",
                )
            )


def _validate_orphan_rights(
    inventory: CorpusInventory,
    issues: list[ValidationIssue],
    referenced_rights_ids: set[str],
) -> None:
    for rights in inventory.rights:
        if rights.asset_id not in referenced_rights_ids:
            issues.append(
                _issue(
                    IssueCode.ASSET_REFERENCE_MISSING,
                    IssueSeverity.BLOCKER,
                    "rights",
                    rights.asset_id,
                    "asset_id",
                )
            )


def _chronology_points(inventory: CorpusInventory) -> tuple[tuple[int, int], ...]:
    intervals = sorted(
        {
            key
            for work in inventory.works
            if not work.first_publication.is_reversed
            and (key := work.first_publication.chronology_key) is not None
        }
    )
    merged: list[tuple[int, int]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def _readiness(
    inventory: CorpusInventory,
    issues: tuple[ValidationIssue, ...],
) -> CorpusReadiness:
    work_ids = {work.work_id for work in inventory.works}
    chronology_points = _chronology_points(inventory)
    minimum_met: bool | None = None
    exploratory = False
    counts = Counter(issue.severity for issue in issues)
    if inventory.purpose is PurposeId.STYLE_OVER_TIME:
        minimum_met = (
            len(work_ids) >= 6
            and len(chronology_points) >= 3
            and counts[IssueSeverity.BLOCKER] == 0
        )
        exploratory = not minimum_met
    restricted_assets = sum(
        not asset_allows_public_redistribution(asset, inventory.rights)
        for asset in inventory.assets
    )
    return CorpusReadiness(
        independent_work_count=len(work_ids),
        chronology_point_count=len(chronology_points),
        blocker_count=counts[IssueSeverity.BLOCKER],
        warning_count=counts[IssueSeverity.WARNING],
        information_count=counts[IssueSeverity.INFORMATION],
        rights_restriction_count=restricted_assets,
        style_over_time_minimum_met=minimum_met,
        exploratory=exploratory,
    )


def validate_inventory(
    inventory: CorpusInventory,
    *,
    vocabulary: VocabularyProfile = DEFAULT_VOCABULARY,
) -> ValidationReport:
    """Return a stable, actionable report without retaining source text."""

    issues: list[ValidationIssue] = []
    _validate_duplicates(inventory, issues)
    _validate_file_catalog(inventory, issues)
    authors_by_id = {record.author_id: record for record in _canonical_order(inventory.authors)}
    works_by_id = {record.work_id: record for record in _canonical_order(inventory.works)}
    editions_by_id = {record.edition_id: record for record in _canonical_order(inventory.editions)}
    sources_by_id = {record.source_id: record for record in _canonical_order(inventory.sources)}
    rights_by_asset = {record.asset_id: record for record in _canonical_order(inventory.rights)}
    _validate_work_records(inventory, issues, vocabulary, set(authors_by_id))
    _validate_edition_records(inventory, issues, works_by_id)
    _validate_source_records(inventory, issues, vocabulary, set(editions_by_id))
    _validate_asset_records(
        inventory,
        issues,
        vocabulary,
        works_by_id,
        editions_by_id,
        sources_by_id,
        rights_by_asset,
    )
    _validate_one_asset_per_work(inventory, issues)
    referenced_rights_ids = {
        rights_id for asset in inventory.assets for rights_id in asset.rights_asset_ids
    }
    _validate_orphan_rights(inventory, issues, referenced_rights_ids)
    if inventory.purpose is PurposeId.STYLE_OVER_TIME:
        author_sets = {
            tuple(
                sorted(
                    contributor.author_id
                    for contributor in work.contributors
                    if contributor.role is ContributorRole.AUTHOR
                )
            )
            for work in inventory.works
        }
        if len(author_sets) > 1:
            issues.append(
                _issue(
                    IssueCode.STYLE_AUTHOR_SET_MIXED,
                    IssueSeverity.BLOCKER,
                    "inventory",
                    None,
                    "works.contributors",
                )
            )
        if len({work.language for work in inventory.works}) > 1:
            issues.append(
                _issue(
                    IssueCode.STYLE_LANGUAGE_MIXED,
                    IssueSeverity.BLOCKER,
                    "inventory",
                    None,
                    "works.language",
                )
            )
        if len(works_by_id) < 6:
            issues.append(
                _issue(
                    IssueCode.WORK_COUNT_EXPLORATORY,
                    IssueSeverity.WARNING,
                    "inventory",
                    None,
                    "works",
                )
            )
        if len(_chronology_points(inventory)) < 3:
            issues.append(
                _issue(
                    IssueCode.CHRONOLOGY_POINTS_EXPLORATORY,
                    IssueSeverity.WARNING,
                    "inventory",
                    None,
                    "works.first_publication",
                )
            )
    ordered = tuple(
        sorted(
            issues,
            key=lambda issue: (
                _SEVERITY_ORDER[issue.severity],
                issue.code.value,
                issue.entity_type,
                issue.entity_id or "",
                issue.field_path,
            ),
        )
    )
    readiness = _readiness(inventory, ordered)
    return ValidationReport(
        inventory_sha256=inventory_sha256(inventory),
        purpose=inventory.purpose,
        blocked=readiness.blocker_count > 0,
        issues=ordered,
        readiness=readiness,
    )


__all__ = [
    "CorpusReadiness",
    "IssueCode",
    "IssueSeverity",
    "ValidationIssue",
    "ValidationReport",
    "validate_inventory",
]
