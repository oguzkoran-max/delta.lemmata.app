"""Versioned scholarly corpus records for P004.

These immutable records describe what an uploaded text represents. They do not
retain upload bytes, execute stylometry, or make legal determinations.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from importlib.resources import files
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

SLUG_PATTERN = r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$"
ASSET_ID_PATTERN = r"^asset_[a-z0-9]+(?:[._-][a-z0-9]+)*$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
LANGUAGE_PATTERN = r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$"
_RESERVED_TERMS = frozenset({"unknown", "not_applicable"})
_JSON_SCHEMA_DRAFT_2020_12 = "https:" + "//json-schema.org/draft/2020-12/schema"

type AssetId = Annotated[str, Field(pattern=ASSET_ID_PATTERN)]


class FrozenModel(BaseModel):
    """Shared immutable, closed-world Pydantic configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class PurposeId(StrEnum):
    TEXT_PROXIMITY = "text_proximity"
    GROUP_COMPARISON = "group_comparison"
    STYLE_OVER_TIME = "style_over_time"


class DateMode(StrEnum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    RANGE = "range"
    UNKNOWN = "unknown"


class TermKind(StrEnum):
    CONTROLLED = "controlled"
    CUSTOM = "custom"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class AuthorKind(StrEnum):
    PERSON = "person"
    COLLECTIVE = "collective"
    ANONYMOUS = "anonymous"
    UNKNOWN = "unknown"


class ContributorRole(StrEnum):
    AUTHOR = "author"
    EDITOR = "editor"
    TRANSLATOR = "translator"
    ADAPTER = "adapter"
    COMPILER = "compiler"


class AuthorityScheme(StrEnum):
    VIAF = "viaf"
    WIKIDATA = "wikidata"
    ISNI = "isni"
    ORCID = "orcid"
    OTHER = "other"


class VocabularyProfile(FrozenModel):
    profile_version: Literal["corpus-vocabularies-v1"]
    adaptation_statuses: tuple[str, ...] = Field(min_length=1)
    asset_types: tuple[str, ...] = Field(min_length=1)
    audiences: tuple[str, ...] = Field(min_length=1)
    author_kinds: tuple[str, ...] = Field(min_length=1)
    authority_schemes: tuple[str, ...] = Field(min_length=1)
    collection_statuses: tuple[str, ...] = Field(min_length=1)
    contributor_roles: tuple[str, ...] = Field(min_length=1)
    date_modes: tuple[str, ...] = Field(min_length=1)
    genres: tuple[str, ...] = Field(min_length=1)
    normalization_profiles: tuple[str, ...] = Field(min_length=1)
    permission_states: tuple[str, ...] = Field(min_length=1)
    rights_statuses: tuple[str, ...] = Field(min_length=1)
    source_types: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_sorted_unique_values(self) -> Self:
        for field_name in type(self).model_fields:
            if field_name == "profile_version":
                continue
            values = getattr(self, field_name)
            if values != tuple(sorted(set(values))):
                raise ValueError("vocabulary values must be sorted and unique")
        return self


DEFAULT_VOCABULARY = VocabularyProfile.model_validate_json(
    files("delta_lemmata").joinpath("data/corpus-vocabularies-v1.json").read_text(encoding="utf-8")
)


class DateValue(FrozenModel):
    """A date assertion that preserves uncertainty instead of inventing precision."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "properties": {"mode": {"const": "unknown"}},
                        "required": ["mode"],
                    },
                    "then": {
                        "properties": {
                            "end_year": {"type": "null"},
                            "start_year": {"type": "null"},
                        }
                    },
                },
                {
                    "if": {
                        "properties": {"mode": {"enum": ["exact", "approximate"]}},
                        "required": ["mode"],
                    },
                    "then": {
                        "properties": {
                            "end_year": {"type": "null"},
                            "start_year": {"type": "integer"},
                        },
                        "required": ["start_year"],
                    },
                },
                {
                    "if": {
                        "properties": {"mode": {"const": "range"}},
                        "required": ["mode"],
                    },
                    "then": {
                        "properties": {
                            "end_year": {"type": "integer"},
                            "start_year": {"type": "integer"},
                        },
                        "required": ["start_year", "end_year"],
                    },
                },
            ]
        },
    )

    mode: DateMode
    start_year: int | None = Field(default=None, ge=1, le=9999)
    end_year: int | None = Field(default=None, ge=1, le=9999)
    display_label: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_mode_fields(self) -> Self:
        if self.mode is DateMode.UNKNOWN:
            if self.start_year is not None or self.end_year is not None:
                raise ValueError("unknown dates cannot include year bounds")
            return self
        if self.mode is DateMode.RANGE:
            if self.start_year is None or self.end_year is None:
                raise ValueError("range dates require both year bounds")
            return self
        if self.start_year is None or self.end_year is not None:
            raise ValueError("exact and approximate dates require one start year")
        return self

    @property
    def bounds(self) -> tuple[int, int] | None:
        if self.start_year is None:
            return None
        if self.end_year is not None:
            return (self.start_year, self.end_year)
        return (self.start_year, self.start_year)

    @property
    def chronology_key(self) -> tuple[int, int] | None:
        """Return a threshold key without treating certainty as another date point."""

        return self.bounds

    @property
    def is_reversed(self) -> bool:
        return (
            self.mode is DateMode.RANGE
            and self.start_year is not None
            and self.end_year is not None
            and self.start_year > self.end_year
        )


class VocabularyTerm(FrozenModel):
    """A normalized chart value plus the wording shown to the researcher."""

    value: str = Field(pattern=SLUG_PATTERN)
    label: str = Field(min_length=1)
    kind: TermKind

    @model_validator(mode="after")
    def require_explicit_reserved_kind(self) -> Self:
        if self.kind is TermKind.UNKNOWN and self.value != "unknown":
            raise ValueError("unknown terms must use the unknown value")
        if self.kind is TermKind.NOT_APPLICABLE and self.value != "not_applicable":
            raise ValueError("not-applicable terms must use the not_applicable value")
        if self.kind in {TermKind.CONTROLLED, TermKind.CUSTOM} and self.value in _RESERVED_TERMS:
            raise ValueError("reserved values require an explicit reserved kind")
        return self


class AuthorityIdentifier(FrozenModel):
    scheme: AuthorityScheme
    value: str = Field(min_length=1)
    url: HttpUrl | None = Field(
        default=None,
        json_schema_extra={"pattern": r"^https?://[^\s]+$"},
    )


class AuthorRecord(FrozenModel):
    author_id: str = Field(pattern=SLUG_PATTERN)
    display_name: str = Field(min_length=1)
    kind: AuthorKind
    authority_identifiers: tuple[AuthorityIdentifier, ...] = ()


class ContributorRecord(FrozenModel):
    author_id: str = Field(pattern=SLUG_PATTERN)
    role: ContributorRole


class WorkRecord(FrozenModel):
    work_id: str = Field(pattern=SLUG_PATTERN)
    title_original: str = Field(min_length=1)
    title_english: str | None = Field(default=None, min_length=1)
    language: str = Field(pattern=LANGUAGE_PATTERN)
    contributors: tuple[ContributorRecord, ...] = Field(min_length=1)
    first_publication: DateValue
    genre: VocabularyTerm
    audience: VocabularyTerm
    adaptation: VocabularyTerm
    collection: VocabularyTerm
    group_label: str | None = Field(default=None, min_length=1)


class EditionRecord(FrozenModel):
    edition_id: str = Field(pattern=SLUG_PATTERN)
    work_id: str = Field(pattern=SLUG_PATTERN)
    edition_label: str = Field(min_length=1)
    edition_date: DateValue
    citation: str | None = Field(default=None, min_length=1)


class SourceRecord(FrozenModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "anyOf": [
                {
                    "properties": {"source_url": {"type": "string"}},
                    "required": ["source_url"],
                },
                {
                    "properties": {"bibliographic_citation": {"type": "string"}},
                    "required": ["bibliographic_citation"],
                },
            ],
            "allOf": [
                {
                    "if": {
                        "properties": {"source_url": {"type": "string"}},
                        "required": ["source_url"],
                    },
                    "then": {"required": ["accessed_on"]},
                },
                {
                    "if": {
                        "properties": {"accessed_on": {"type": "string"}},
                        "required": ["accessed_on"],
                    },
                    "then": {"required": ["source_url"]},
                },
            ],
        },
    )

    source_id: str = Field(pattern=SLUG_PATTERN)
    edition_id: str = Field(pattern=SLUG_PATTERN)
    source_type: VocabularyTerm
    title: str = Field(min_length=1)
    source_url: HttpUrl | None = Field(
        default=None,
        json_schema_extra={"pattern": r"^https?://[^\s]+$"},
    )
    bibliographic_citation: str | None = Field(default=None, min_length=1)
    accessed_on: date | None = None

    @model_validator(mode="after")
    def require_source_evidence(self) -> Self:
        if self.source_url is None and self.bibliographic_citation is None:
            raise ValueError("a source URL or bibliographic citation is required")
        if self.source_url is not None and self.accessed_on is None:
            raise ValueError("online sources require an access date")
        if self.source_url is None and self.accessed_on is not None:
            raise ValueError("an access date requires an online source")
        return self


class AssetRecord(FrozenModel):
    """One validated analyzed TXT mapped to one independent work in v0.1."""

    asset_id: AssetId
    file_label: str = Field(min_length=1)
    content_sha256: str = Field(pattern=SHA256_PATTERN)
    work_id: str = Field(pattern=SLUG_PATTERN)
    edition_id: str = Field(pattern=SLUG_PATTERN)
    source_id: str = Field(pattern=SLUG_PATTERN)
    rights_asset_ids: tuple[AssetId, ...] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )
    rights_chain_confirmed: bool
    normalization_profile: str = Field(pattern=SLUG_PATTERN)
    normalization_notes: str | None = Field(default=None, min_length=1)
    mapping_confirmed: bool
    line_count: int | None = Field(default=None, ge=1)
    token_count: int | None = Field(default=None, ge=1)

    @field_validator("rights_asset_ids")
    @classmethod
    def require_unique_rights_dependencies(cls, value: tuple[AssetId, ...]) -> tuple[AssetId, ...]:
        if len(value) != len(set(value)):
            raise ValueError("rights dependency identifiers must be unique")
        return value


class ValidatedFileRecord(FrozenModel):
    """Stable P003 receipt projection; transient storage IDs are excluded."""

    file_label: str = Field(min_length=1)
    content_sha256: str = Field(pattern=SHA256_PATTERN)
    intake_profile: str = Field(pattern=r"^ingestion-limits-v[0-9]+$")
    status: Literal["validated-for-intake"] = "validated-for-intake"


def export_json_schema(model: type[BaseModel], schema_id: str) -> dict[str, Any]:
    """Return one deterministic Draft 2020-12 schema for a public P004 model."""

    schema = model.model_json_schema(mode="validation")
    return {
        "$schema": _JSON_SCHEMA_DRAFT_2020_12,
        "$id": schema_id,
        **schema,
    }


__all__ = [
    "ASSET_ID_PATTERN",
    "DEFAULT_VOCABULARY",
    "AssetRecord",
    "AuthorKind",
    "AuthorRecord",
    "AuthorityIdentifier",
    "AuthorityScheme",
    "ContributorRecord",
    "ContributorRole",
    "DateMode",
    "DateValue",
    "EditionRecord",
    "FrozenModel",
    "PurposeId",
    "SourceRecord",
    "TermKind",
    "VocabularyProfile",
    "VocabularyTerm",
    "ValidatedFileRecord",
    "WorkRecord",
    "export_json_schema",
]
