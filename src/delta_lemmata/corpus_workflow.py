"""Payload-free adapters for the P004 guided corpus workflow."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import UTC, date, datetime
from pathlib import PurePath
from typing import Self, cast

from pydantic import Field, HttpUrl, model_validator

from delta_lemmata.corpus_models import (
    DEFAULT_VOCABULARY,
    AssetRecord,
    AuthorKind,
    AuthorRecord,
    ContributorRecord,
    ContributorRole,
    DateValue,
    EditionRecord,
    FrozenModel,
    PurposeId,
    SourceRecord,
    TermKind,
    ValidatedFileRecord,
    VocabularyTerm,
    WorkRecord,
)
from delta_lemmata.corpus_validation import ValidationReport, validate_inventory
from delta_lemmata.ingestion import IntakeReceipt, IntakeRole
from delta_lemmata.inventory import CorpusInventory, inventory_sha256
from delta_lemmata.provenance import canonical_json_bytes
from delta_lemmata.rights import (
    ActionPermissions,
    AssetRightsRecord,
    AssetType,
    PermissionState,
    RightsEvidence,
    RightsStatus,
)


class ValidatedCorpusUnit(FrozenModel):
    """A P003-validated TXT projection that contains no source text or storage ID."""

    validated_file: ValidatedFileRecord
    line_count: int = Field(ge=1)
    token_count: int = Field(ge=1)


class GuidedWorkInput(FrozenModel):
    """Complete values submitted for one work in the guided editor."""

    unit: ValidatedCorpusUnit
    title_original: str = Field(min_length=1)
    primary_author_name: str = Field(min_length=1)
    author_kind: AuthorKind = AuthorKind.PERSON
    language: str = Field(pattern=r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    first_publication: DateValue
    genre: str
    audience: str
    adaptation: str
    collection: str
    group_label: str | None = Field(default=None, min_length=1)
    edition_label: str = Field(min_length=1)
    edition_date: DateValue
    source_type: str
    source_title: str = Field(min_length=1)
    source_url: HttpUrl | None = None
    bibliographic_citation: str | None = Field(default=None, min_length=1)
    accessed_on: date | None = None
    normalization_profile: str = "nfc_validated_v1"
    normalization_notes: str | None = Field(default=None, min_length=1)
    rights_status: RightsStatus
    rights_license: str | None = Field(default=None, min_length=1)
    rights_jurisdiction: str | None = Field(default=None, min_length=1)
    rights_notes: str = ""

    @model_validator(mode="after")
    def require_source_evidence(self) -> Self:
        if self.source_url is None and self.bibliographic_citation is None:
            raise ValueError("a source URL or bibliographic citation is required")
        if self.source_url is not None and self.accessed_on is None:
            raise ValueError("an online source requires an access date")
        if self.source_url is None and self.accessed_on is not None:
            raise ValueError("an access date requires an online source")
        return self


class GuidedInventoryBuild(FrozenModel):
    """One immutable guided build and its canonical domain validation report."""

    inventory: CorpusInventory
    validation_report: ValidationReport

    @model_validator(mode="after")
    def require_matching_identity(self) -> Self:
        if self.validation_report.inventory_sha256 != inventory_sha256(self.inventory):
            raise ValueError("validation report does not match the inventory")
        return self

    @property
    def inventory_sha256(self) -> str:
        return self.validation_report.inventory_sha256


def project_text_receipts(receipts: tuple[IntakeReceipt, ...]) -> tuple[ValidatedCorpusUnit, ...]:
    """Project accepted individual TXT receipts into a stable P004 file catalog."""

    units = tuple(
        ValidatedCorpusUnit(
            validated_file=ValidatedFileRecord(
                file_label=receipt.display_label,
                content_sha256=receipt.sha256,
                intake_profile=receipt.limit_profile,
            ),
            line_count=receipt.line_count or 1,
            token_count=receipt.token_count or 1,
        )
        for receipt in receipts
        if receipt.role is IntakeRole.CORPUS_TEXT
    )
    return tuple(
        sorted(
            units,
            key=lambda unit: (
                unit.validated_file.file_label.casefold(),
                unit.validated_file.content_sha256,
            ),
        )
    )


def project_corpus_receipts(
    receipts: tuple[IntakeReceipt, ...],
) -> tuple[ValidatedCorpusUnit, ...]:
    """Project accepted TXT uploads or ZIP members into one stable P004 catalog."""

    units = list(project_text_receipts(receipts))
    units.extend(
        ValidatedCorpusUnit(
            validated_file=ValidatedFileRecord(
                file_label=member.display_label,
                content_sha256=member.sha256,
                intake_profile=member.limit_profile,
            ),
            line_count=member.line_count,
            token_count=member.token_count,
        )
        for receipt in receipts
        if receipt.role is IntakeRole.CORPUS_ARCHIVE
        for member in receipt.archive_members
    )
    return tuple(
        sorted(
            units,
            key=lambda unit: (
                unit.validated_file.file_label.casefold(),
                unit.validated_file.file_label,
                unit.validated_file.content_sha256,
            ),
        )
    )


def corpus_catalog_sha256(units: tuple[ValidatedCorpusUnit, ...]) -> str:
    """Return an upload-order-invariant identity for one payload-free file catalog."""

    payload = [
        unit.model_dump(mode="json")
        for unit in sorted(
            units,
            key=lambda item: (
                item.validated_file.file_label.casefold(),
                item.validated_file.content_sha256,
            ),
        )
    ]
    return hashlib.sha256(canonical_json_bytes({"units": payload})).hexdigest()


def suggested_title(file_label: str) -> str:
    """Return a non-authoritative editable title suggestion from a safe label."""

    stem = PurePath(file_label).stem
    words = re.sub(r"[._-]+", " ", stem).strip()
    return words.title() or "Untitled work"


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "_", ascii_value.casefold()).strip("_")
    return normalized or "record"


def _record_id(prefix: str, label: str, digest: str) -> str:
    return f"{prefix}_{_slug(label)}_{digest[:10]}"


def guided_work_id(unit: ValidatedCorpusUnit) -> str:
    """Return the stable work identifier proposed for one guided corpus unit."""

    validated = unit.validated_file
    return _record_id("work", validated.file_label, validated.content_sha256)


def _author_id(display_name: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFC", display_name).casefold().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10]
    return f"author_{_slug(display_name)}_{digest}"


def _term(value: str, allowed: tuple[str, ...]) -> VocabularyTerm:
    if value not in allowed:
        raise ValueError(f"unsupported controlled value: {value}")
    if value == "unknown":
        kind = TermKind.UNKNOWN
    elif value == "not_applicable":
        kind = TermKind.NOT_APPLICABLE
    else:
        kind = TermKind.CONTROLLED
    return VocabularyTerm(value=value, label=value.replace("_", " ").title(), kind=kind)


def _rights_permissions(status: RightsStatus) -> ActionPermissions:
    if status is RightsStatus.VERIFIED_OPEN:
        return ActionPermissions(
            upload=PermissionState.PERMITTED,
            analysis=PermissionState.PERMITTED,
            export=PermissionState.PERMITTED,
            public_redistribution=PermissionState.PERMITTED,
        )
    if status is RightsStatus.ANALYSIS_ONLY:
        return ActionPermissions(
            upload=PermissionState.PERMITTED,
            analysis=PermissionState.PERMITTED,
            export=PermissionState.PROHIBITED,
            public_redistribution=PermissionState.PROHIBITED,
        )
    if status is RightsStatus.EXCLUDED:
        prohibited = PermissionState.PROHIBITED
        return ActionPermissions(
            upload=prohibited,
            analysis=prohibited,
            export=prohibited,
            public_redistribution=prohibited,
        )
    unknown = PermissionState.UNKNOWN
    return ActionPermissions(
        upload=unknown,
        analysis=unknown,
        export=unknown,
        public_redistribution=unknown,
    )


def _rights_evidence(item: GuidedWorkInput) -> tuple[RightsEvidence, ...]:
    if item.rights_status not in {RightsStatus.VERIFIED_OPEN, RightsStatus.ANALYSIS_ONLY}:
        return ()
    if item.source_url is not None:
        return (RightsEvidence(evidence_type="url", value=str(item.source_url)),)
    return (
        RightsEvidence(
            evidence_type="citation",
            value=cast(str, item.bibliographic_citation),
        ),
    )


def build_guided_inventory(
    purpose: PurposeId,
    inputs: tuple[GuidedWorkInput, ...],
    *,
    assessed_by: str = "Researcher using Delta",
    assessed_at_utc: datetime | None = None,
) -> GuidedInventoryBuild:
    """Build and validate one inventory from explicitly confirmed guided values."""

    if not inputs:
        raise ValueError("at least one documented work is required")
    assessed_at = assessed_at_utc or datetime.now(UTC)
    authors: dict[str, AuthorRecord] = {}
    works: list[WorkRecord] = []
    editions: list[EditionRecord] = []
    sources: list[SourceRecord] = []
    assets: list[AssetRecord] = []
    rights_records: list[AssetRightsRecord] = []
    for item in inputs:
        validated = item.unit.validated_file
        digest = validated.content_sha256
        work_id = guided_work_id(item.unit)
        edition_id = _record_id("edition", validated.file_label, digest)
        source_id = _record_id("source", validated.file_label, digest)
        asset_id = _record_id("asset", validated.file_label, digest)
        author_id = _author_id(item.primary_author_name)
        authors.setdefault(
            author_id,
            AuthorRecord(
                author_id=author_id,
                display_name=item.primary_author_name,
                kind=item.author_kind,
            ),
        )
        works.append(
            WorkRecord(
                work_id=work_id,
                title_original=item.title_original,
                language=item.language,
                contributors=(ContributorRecord(author_id=author_id, role=ContributorRole.AUTHOR),),
                first_publication=item.first_publication,
                genre=_term(item.genre, DEFAULT_VOCABULARY.genres),
                audience=_term(item.audience, DEFAULT_VOCABULARY.audiences),
                adaptation=_term(item.adaptation, DEFAULT_VOCABULARY.adaptation_statuses),
                collection=_term(item.collection, DEFAULT_VOCABULARY.collection_statuses),
                group_label=item.group_label,
            )
        )
        editions.append(
            EditionRecord(
                edition_id=edition_id,
                work_id=work_id,
                edition_label=item.edition_label,
                edition_date=item.edition_date,
                citation=item.bibliographic_citation,
            )
        )
        sources.append(
            SourceRecord(
                source_id=source_id,
                edition_id=edition_id,
                source_type=_term(item.source_type, DEFAULT_VOCABULARY.source_types),
                title=item.source_title,
                source_url=item.source_url,
                bibliographic_citation=item.bibliographic_citation,
                accessed_on=item.accessed_on,
            )
        )
        assets.append(
            AssetRecord(
                asset_id=asset_id,
                file_label=validated.file_label,
                content_sha256=digest,
                work_id=work_id,
                edition_id=edition_id,
                source_id=source_id,
                rights_asset_ids=(asset_id,),
                rights_chain_confirmed=True,
                normalization_profile=item.normalization_profile,
                normalization_notes=item.normalization_notes,
                mapping_confirmed=True,
                line_count=item.unit.line_count,
                token_count=item.unit.token_count,
            )
        )
        rights_records.append(
            AssetRightsRecord(
                asset_id=asset_id,
                source_id=source_id,
                asset_type=AssetType.TRANSCRIPTION,
                rights_status=item.rights_status,
                license=item.rights_license,
                permissions=_rights_permissions(item.rights_status),
                evidence=_rights_evidence(item),
                jurisdiction=item.rights_jurisdiction,
                assessed_by=assessed_by,
                assessed_at_utc=assessed_at,
                notes=item.rights_notes,
            )
        )
    inventory = CorpusInventory(
        purpose=purpose,
        authors=tuple(sorted(authors.values(), key=lambda item: item.author_id)),
        works=tuple(sorted(works, key=lambda item: item.work_id)),
        editions=tuple(sorted(editions, key=lambda item: item.edition_id)),
        sources=tuple(sorted(sources, key=lambda item: item.source_id)),
        assets=tuple(sorted(assets, key=lambda item: item.asset_id)),
        validated_files=tuple(
            sorted(
                (item.unit.validated_file for item in inputs),
                key=lambda item: (item.file_label.casefold(), item.content_sha256),
            )
        ),
        rights=tuple(sorted(rights_records, key=lambda item: item.asset_id)),
    )
    return GuidedInventoryBuild(
        inventory=inventory,
        validation_report=validate_inventory(inventory),
    )


__all__ = [
    "GuidedInventoryBuild",
    "GuidedWorkInput",
    "ValidatedCorpusUnit",
    "build_guided_inventory",
    "corpus_catalog_sha256",
    "guided_work_id",
    "project_corpus_receipts",
    "project_text_receipts",
    "suggested_title",
]
