"""Versioned metadata-CSV contracts and content-free diagnostics for P004."""

from __future__ import annotations

from enum import StrEnum
from importlib.resources import files
from typing import Any, Literal, Self

from pydantic import Field, model_validator

from delta_lemmata.corpus_models import FrozenModel
from delta_lemmata.corpus_validation import ValidationReport
from delta_lemmata.ingestion import IntakeErrorCode
from delta_lemmata.inventory import CorpusInventory

CORPUS_METADATA_CSV_VERSION = "corpus-metadata-csv-v1"
CORPUS_METADATA_FIELD_DICTIONARY_VERSION = "corpus-metadata-field-dictionary-v1"


class FieldRequirement(StrEnum):
    REQUIRED = "required"
    CONDITIONAL = "conditional"
    OPTIONAL = "optional"


class MetadataCsvField(FrozenModel):
    position: int = Field(ge=1)
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    section: Literal[
        "version",
        "mapping",
        "work",
        "contributors",
        "chronology",
        "classification",
        "edition",
        "source",
        "normalization",
        "rights",
        "intake",
    ]
    requirement: FieldRequirement
    value_format: str = Field(min_length=1)
    description: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    example: str
    allowed_values: tuple[str, ...] = ()


class MetadataCsvFieldDictionary(FrozenModel):
    schema_version: Literal["corpus-metadata-field-dictionary-v1"]
    csv_schema_version: Literal["corpus-metadata-csv-v1"]
    inventory_schema_version: Literal["corpus-inventory-v1"]
    vocabulary_profile: Literal["corpus-vocabularies-v1"]
    columns: tuple[MetadataCsvField, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def require_complete_order(self) -> Self:
        positions = tuple(field.position for field in self.columns)
        names = tuple(field.name for field in self.columns)
        if positions != tuple(range(1, len(self.columns) + 1)):
            raise ValueError("field positions must be consecutive and ordered")
        if len(names) != len(set(names)):
            raise ValueError("field names must be unique")
        return self

    @classmethod
    def customize_public_json_schema(cls, schema: dict[str, Any]) -> dict[str, Any]:
        """Expose this version's exact ordered columns to non-Python consumers."""

        columns_schema = schema["properties"]["columns"]
        item_schema = columns_schema.pop("items")
        columns_schema.update(
            {
                "minItems": len(FIELD_DICTIONARY.columns),
                "maxItems": len(FIELD_DICTIONARY.columns),
                "prefixItems": [
                    {
                        "allOf": [
                            item_schema,
                            {
                                "type": "object",
                                "properties": {
                                    "position": {"const": field.position},
                                    "name": {"const": field.name},
                                },
                                "required": ["position", "name"],
                            },
                        ]
                    }
                    for field in FIELD_DICTIONARY.columns
                ],
                "items": False,
            }
        )
        return schema


FIELD_DICTIONARY = MetadataCsvFieldDictionary.model_validate_json(
    files("delta_lemmata")
    .joinpath("data/corpus-metadata-fields-v1.json")
    .read_text(encoding="utf-8")
)
CSV_COLUMNS = tuple(field.name for field in FIELD_DICTIONARY.columns)
REQUIRED_VALUE_FIELDS = frozenset(
    field.name
    for field in FIELD_DICTIONARY.columns
    if field.requirement is FieldRequirement.REQUIRED
)


class MetadataCsvIssueCode(StrEnum):
    INTAKE_REJECTED = "META_CSV_INTAKE_REJECTED"
    HEADER_MISMATCH = "META_CSV_HEADER_MISMATCH"
    REQUIRED_VALUE_MISSING = "META_CSV_REQUIRED_VALUE_MISSING"
    VERSION_UNSUPPORTED = "META_CSV_VERSION_UNSUPPORTED"
    GLOBAL_VALUE_CONFLICT = "META_CSV_GLOBAL_VALUE_CONFLICT"
    VALUE_INVALID = "META_CSV_VALUE_INVALID"
    JSON_INVALID = "META_CSV_JSON_INVALID"
    JSON_UNSAFE = "META_CSV_JSON_UNSAFE"
    FILE_UNMATCHED = "META_CSV_FILE_UNMATCHED"
    FILE_HASH_MISMATCH = "META_CSV_FILE_HASH_MISMATCH"
    CATALOG_CONFLICT = "META_CSV_CATALOG_CONFLICT"
    ENTITY_CONFLICT = "META_CSV_ENTITY_CONFLICT"


class MetadataCsvIssue(FrozenModel):
    code: MetadataCsvIssueCode
    row_number: int | None = Field(default=None, ge=2)
    field_name: str = Field(min_length=1)
    message: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    how_to_fix: str = Field(min_length=1)
    intake_error_code: IntakeErrorCode | None = None


class MetadataCsvImportResult(FrozenModel):
    schema_version: Literal["corpus-metadata-csv-import-v1"] = "corpus-metadata-csv-import-v1"
    csv_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    row_count: int = Field(ge=0)
    blocked: bool
    issues: tuple[MetadataCsvIssue, ...]
    inventory: CorpusInventory | None
    validation_report: ValidationReport | None

    @model_validator(mode="after")
    def require_coherent_result(self) -> Self:
        if self.issues and self.inventory is not None:
            raise ValueError("structural CSV issues cannot retain a partial inventory")
        if self.inventory is None and self.validation_report is not None:
            raise ValueError("a validation report requires a parsed inventory")
        if self.inventory is not None and self.validation_report is None:
            raise ValueError("a parsed inventory requires a validation report")
        if not self.blocked and (self.inventory is None or self.validation_report is None):
            raise ValueError("an unblocked import requires a validated inventory")
        return self


class MetadataCsvExportErrorCode(StrEnum):
    DUPLICATE_IDENTIFIER = "META_CSV_EXPORT_DUPLICATE_IDENTIFIER"
    RELATIONSHIP_UNRESOLVED = "META_CSV_EXPORT_RELATIONSHIP_UNRESOLVED"
    P003_POLICY_REJECTED = "META_CSV_EXPORT_P003_POLICY_REJECTED"


class MetadataCsvExportError(ValueError):
    """A content-free export failure with a stable machine-readable code."""

    def __init__(
        self,
        code: MetadataCsvExportErrorCode,
        intake_error_code: IntakeErrorCode | None = None,
    ) -> None:
        self.code = code
        self.intake_error_code = intake_error_code
        super().__init__(code.value)


__all__ = [
    "CORPUS_METADATA_CSV_VERSION",
    "CORPUS_METADATA_FIELD_DICTIONARY_VERSION",
    "CSV_COLUMNS",
    "FIELD_DICTIONARY",
    "REQUIRED_VALUE_FIELDS",
    "FieldRequirement",
    "MetadataCsvExportError",
    "MetadataCsvExportErrorCode",
    "MetadataCsvField",
    "MetadataCsvFieldDictionary",
    "MetadataCsvImportResult",
    "MetadataCsvIssue",
    "MetadataCsvIssueCode",
]
