"""Secure, versioned metadata CSV import and export for P004.

The CSV is one row per analyzed work. Ordinary bibliographic values remain plain
columns; only genuinely one-to-many contributor, rights-source, and rights-record
structures use compact JSON cells. Every uploaded or generated CSV passes the
unchanged P003 boundary.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import PurePath
from typing import Any

from pydantic import Field, ValidationError

from delta_lemmata.corpus_models import (
    AssetRecord,
    AuthorityIdentifier,
    AuthorKind,
    AuthorRecord,
    ContributorRecord,
    ContributorRole,
    DateMode,
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
from delta_lemmata.ingestion import (
    DEFAULT_LIMITS,
    IncomingUpload,
    IngestionLimits,
    IntakeError,
    IntakeErrorCode,
    IntakeRole,
    csv_cell_is_safe,
    validate_upload,
)
from delta_lemmata.inventory import CorpusInventory
from delta_lemmata.metadata_csv_models import (
    CORPUS_METADATA_CSV_VERSION,
    CSV_COLUMNS,
    FIELD_DICTIONARY,
    REQUIRED_VALUE_FIELDS,
    MetadataCsvExportError,
    MetadataCsvExportErrorCode,
    MetadataCsvImportResult,
    MetadataCsvIssue,
    MetadataCsvIssueCode,
)
from delta_lemmata.provenance import canonical_json_bytes
from delta_lemmata.rights import AssetRightsRecord

_INVENTORY_VERSION = "corpus-inventory-v1"
_VOCABULARY_VERSION = "corpus-vocabularies-v1"
_INTAKE_STATUS = "validated-for-intake"
_FIXED_ID = "0" * 32


class _CsvContributor(FrozenModel):
    author_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
    display_name: str = Field(min_length=1)
    kind: AuthorKind
    role: ContributorRole
    authority_identifiers: tuple[AuthorityIdentifier, ...] = ()


@dataclass(frozen=True, slots=True)
class _ParsedRow:
    row_number: int
    authors: tuple[AuthorRecord, ...]
    work: WorkRecord
    edition: EditionRecord
    source: SourceRecord
    rights_sources: tuple[SourceRecord, ...]
    asset: AssetRecord
    rights: tuple[AssetRightsRecord, ...]


@dataclass(frozen=True, slots=True)
class _CellFailure(Exception):
    code: MetadataCsvIssueCode
    field_name: str


class _InvalidJsonValue(ValueError):
    pass


_GUIDANCE: dict[MetadataCsvIssueCode, tuple[str, str, str]] = {
    MetadataCsvIssueCode.INTAKE_REJECTED: (
        "The metadata CSV did not pass secure intake.",
        "Semantic parsing must never bypass P003 encoding, structure, size, or injection checks.",
        "Correct the CSV using the P003 rejection reference, then upload it again.",
    ),
    MetadataCsvIssueCode.HEADER_MISMATCH: (
        "The CSV header does not match the versioned field dictionary.",
        "Missing, renamed, or unknown columns make row meanings ambiguous.",
        "Start from the current downloadable template and keep every header name unchanged.",
    ),
    MetadataCsvIssueCode.REQUIRED_VALUE_MISSING: (
        "A required metadata cell is empty.",
        "Delta cannot create a complete scholarly identity from an unstated required value.",
        (
            "Enter the requested value; use an explicit Unknown option only where the "
            "dictionary permits it."
        ),
    ),
    MetadataCsvIssueCode.VERSION_UNSUPPORTED: (
        "A schema or vocabulary version is not supported.",
        "Silent migration could change field meanings or discard uncertainty.",
        "Download the current template and review the row under its documented version.",
    ),
    MetadataCsvIssueCode.GLOBAL_VALUE_CONFLICT: (
        "Rows disagree about a corpus-level value.",
        "One inventory cannot use different purposes or schema profiles in different rows.",
        "Use the same declared purpose and version values in every row.",
    ),
    MetadataCsvIssueCode.VALUE_INVALID: (
        "A cell does not satisfy the documented value format.",
        (
            "Malformed identifiers, dates, booleans, URLs, or relationships cannot be "
            "repaired silently."
        ),
        "Use the field dictionary example and allowed values to correct the cell.",
    ),
    MetadataCsvIssueCode.JSON_INVALID: (
        "A structured JSON cell is malformed or has the wrong shape.",
        (
            "Contributor and rights arrays must preserve one-to-many records without ad hoc "
            "delimiters."
        ),
        (
            "Enter a compact JSON array that follows the field dictionary, using [] when "
            "empty is allowed."
        ),
    ),
    MetadataCsvIssueCode.JSON_UNSAFE: (
        "A decoded JSON value violates the P003 metadata-cell policy.",
        (
            "Escaped formula, HTML, newline, or path-like text must not bypass secure "
            "intake after JSON decoding."
        ),
        "Remove the unsafe nested value and enter plain scholarly metadata.",
    ),
    MetadataCsvIssueCode.FILE_UNMATCHED: (
        "The row has no exact match in the P003-validated file catalog.",
        "Metadata cannot substitute for proof that the exact TXT bytes passed secure intake.",
        "Use the exact validated file label or upload the intended TXT again.",
    ),
    MetadataCsvIssueCode.FILE_HASH_MISMATCH: (
        "The row hash differs from the P003-validated file hash.",
        "The metadata may describe different bytes from the accepted TXT.",
        "Regenerate the template from the current upload and confirm the mapping again.",
    ),
    MetadataCsvIssueCode.CATALOG_CONFLICT: (
        "The P003 file catalog is empty or contains an ambiguous label.",
        "Exact file mapping requires one unique validated byte sequence per label.",
        "Rebuild the intake catalog from unique validated TXT files.",
    ),
    MetadataCsvIssueCode.ENTITY_CONFLICT: (
        "The same stable identifier is paired with conflicting embedded records.",
        "An author or rights identifier must refer to one reviewed entity.",
        "Make repeated definitions identical or assign a different confirmed identifier.",
    ),
}


def _issue(
    code: MetadataCsvIssueCode,
    field_name: str,
    *,
    row_number: int | None = None,
    intake_error_code: IntakeErrorCode | None = None,
) -> MetadataCsvIssue:
    message, why_it_matters, how_to_fix = _GUIDANCE[code]
    return MetadataCsvIssue(
        code=code,
        row_number=row_number,
        field_name=field_name,
        message=message,
        why_it_matters=why_it_matters,
        how_to_fix=how_to_fix,
        intake_error_code=intake_error_code,
    )


def _json_array(value: str, field_name: str) -> list[Any]:
    try:
        loaded = json.loads(
            value,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as error:
        raise _CellFailure(MetadataCsvIssueCode.JSON_INVALID, field_name) from error
    if not isinstance(loaded, list):
        raise _CellFailure(MetadataCsvIssueCode.JSON_INVALID, field_name)
    if not _json_value_is_safe(loaded):
        raise _CellFailure(MetadataCsvIssueCode.JSON_UNSAFE, field_name)
    return loaded


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidJsonValue
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise _InvalidJsonValue


def _json_value_is_safe(value: Any) -> bool:
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, str):
            if not csv_cell_is_safe(current):
                return False
        elif isinstance(current, list):
            pending.extend(current)
        elif isinstance(current, dict):
            for key, item in current.items():
                if not csv_cell_is_safe(str(key)):
                    return False
                pending.append(item)
    return True


def _optional_int(value: str, field_name: str) -> int | None:
    stripped = value.strip()
    if not stripped:
        return None
    if re.fullmatch(r"[0-9]+", stripped) is None:
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, field_name)
    return int(stripped)


def _optional_date(value: str, field_name: str) -> date | None:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return date.fromisoformat(stripped)
    except ValueError as error:
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, field_name) from error


def _boolean(value: str, field_name: str) -> bool:
    stripped = value.strip()
    if stripped == "true":
        return True
    if stripped == "false":
        return False
    raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, field_name)


def _optional_text(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _validation_field(
    error: ValidationError,
    mapping: dict[str, str],
    fallback: str,
) -> str:
    for detail in error.errors():
        location = detail.get("loc", ())
        if location:
            mapped = mapping.get(str(location[0]))
            if mapped is not None:
                return mapped
    return fallback


def _date_value(row: dict[str, str], prefix: str) -> DateValue:
    try:
        mode = DateMode(row[f"{prefix}_mode"])
    except ValueError as error:
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, f"{prefix}_mode") from error
    try:
        return DateValue(
            mode=mode,
            start_year=_optional_int(row[f"{prefix}_start_year"], f"{prefix}_start_year"),
            end_year=_optional_int(row[f"{prefix}_end_year"], f"{prefix}_end_year"),
            display_label=_optional_text(row[f"{prefix}_label"]),
        )
    except ValidationError as error:
        field_name = _validation_field(
            error,
            {
                "start_year": f"{prefix}_start_year",
                "end_year": f"{prefix}_end_year",
                "display_label": f"{prefix}_label",
            },
            f"{prefix}_mode",
        )
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, field_name) from error


def _term(row: dict[str, str], prefix: str) -> VocabularyTerm:
    try:
        kind = TermKind(row[f"{prefix}_kind"])
    except ValueError as error:
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, f"{prefix}_kind") from error
    try:
        return VocabularyTerm(
            value=row[f"{prefix}_value"],
            label=row[f"{prefix}_label"],
            kind=kind,
        )
    except ValidationError as error:
        field_name = _validation_field(
            error,
            {
                "value": f"{prefix}_value",
                "label": f"{prefix}_label",
                "kind": f"{prefix}_kind",
            },
            f"{prefix}_value",
        )
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, field_name) from error


def _canonical_author(author: AuthorRecord) -> AuthorRecord:
    authorities = tuple(
        sorted(
            author.authority_identifiers,
            key=lambda item: (
                item.scheme.value,
                item.value,
                str(item.url) if item.url is not None else "",
            ),
        )
    )
    return author.model_copy(update={"authority_identifiers": authorities})


def _canonical_rights(rights: AssetRightsRecord) -> AssetRightsRecord:
    evidence = tuple(sorted(rights.evidence, key=lambda item: (item.evidence_type, item.value)))
    return rights.model_copy(update={"evidence": evidence})


def _parse_authorities(row: dict[str, str]) -> tuple[AuthorityIdentifier, ...]:
    loaded = _json_array(row["primary_author_authorities_json"], "primary_author_authorities_json")
    try:
        return tuple(AuthorityIdentifier.model_validate(item) for item in loaded)
    except ValidationError as error:
        raise _CellFailure(
            MetadataCsvIssueCode.JSON_INVALID, "primary_author_authorities_json"
        ) from error


def _parse_additional_contributors(row: dict[str, str]) -> tuple[_CsvContributor, ...]:
    loaded = _json_array(row["additional_contributors_json"], "additional_contributors_json")
    try:
        return tuple(_CsvContributor.model_validate(item) for item in loaded)
    except ValidationError as error:
        raise _CellFailure(
            MetadataCsvIssueCode.JSON_INVALID, "additional_contributors_json"
        ) from error


def _parse_rights(row: dict[str, str]) -> tuple[AssetRightsRecord, ...]:
    loaded = _json_array(row["rights_records_json"], "rights_records_json")
    if not loaded:
        raise _CellFailure(MetadataCsvIssueCode.JSON_INVALID, "rights_records_json")
    try:
        return tuple(_canonical_rights(AssetRightsRecord.model_validate(item)) for item in loaded)
    except ValidationError as error:
        raise _CellFailure(MetadataCsvIssueCode.JSON_INVALID, "rights_records_json") from error


def _parse_rights_sources(row: dict[str, str]) -> tuple[SourceRecord, ...]:
    loaded = _json_array(row["rights_sources_json"], "rights_sources_json")
    try:
        sources = tuple(SourceRecord.model_validate(item) for item in loaded)
    except ValidationError as error:
        raise _CellFailure(MetadataCsvIssueCode.JSON_INVALID, "rights_sources_json") from error
    source_ids = tuple(source.source_id for source in sources)
    if len(source_ids) != len(set(source_ids)):
        raise _CellFailure(MetadataCsvIssueCode.JSON_INVALID, "rights_sources_json")
    return sources


def _parse_row(
    row: dict[str, str],
    row_number: int,
    catalog_by_label: dict[str, ValidatedFileRecord],
) -> _ParsedRow:
    validated_file = catalog_by_label.get(row["file_label"])
    if validated_file is None:
        raise _CellFailure(MetadataCsvIssueCode.FILE_UNMATCHED, "file_label")
    if row["content_sha256"] != validated_file.content_sha256:
        raise _CellFailure(MetadataCsvIssueCode.FILE_HASH_MISMATCH, "content_sha256")
    if (
        row["intake_profile"] != validated_file.intake_profile
        or row["intake_status"] != validated_file.status
    ):
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, "intake_profile")

    try:
        primary_author_kind = AuthorKind(row["primary_author_kind"])
    except ValueError as error:
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, "primary_author_kind") from error
    try:
        primary_author = _canonical_author(
            AuthorRecord(
                author_id=row["primary_author_id"],
                display_name=row["primary_author_name"],
                kind=primary_author_kind,
                authority_identifiers=_parse_authorities(row),
            )
        )
    except ValidationError as error:
        field_name = _validation_field(
            error,
            {
                "author_id": "primary_author_id",
                "display_name": "primary_author_name",
                "kind": "primary_author_kind",
                "authority_identifiers": "primary_author_authorities_json",
            },
            "primary_author_id",
        )
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, field_name) from error

    additional = _parse_additional_contributors(row)
    additional_authors = tuple(
        _canonical_author(
            AuthorRecord(
                author_id=item.author_id,
                display_name=item.display_name,
                kind=item.kind,
                authority_identifiers=item.authority_identifiers,
            )
        )
        for item in additional
    )
    contributors = (
        ContributorRecord(author_id=primary_author.author_id, role=ContributorRole.AUTHOR),
        *(ContributorRecord(author_id=item.author_id, role=item.role) for item in additional),
    )

    first_publication = _date_value(row, "first_publication")
    edition_date = _date_value(row, "edition_date")
    try:
        work = WorkRecord(
            work_id=row["work_id"],
            title_original=row["title_original"],
            title_english=_optional_text(row["title_english"]),
            language=row["language"],
            contributors=contributors,
            first_publication=first_publication,
            genre=_term(row, "genre"),
            audience=_term(row, "audience"),
            adaptation=_term(row, "adaptation"),
            collection=_term(row, "collection"),
            group_label=_optional_text(row["group_label"]),
        )
    except ValidationError as error:
        field_name = _validation_field(
            error,
            {
                "work_id": "work_id",
                "title_original": "title_original",
                "title_english": "title_english",
                "language": "language",
                "contributors": "additional_contributors_json",
                "group_label": "group_label",
            },
            "work_id",
        )
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, field_name) from error

    try:
        edition = EditionRecord(
            edition_id=row["edition_id"],
            work_id=work.work_id,
            edition_label=row["edition_label"],
            edition_date=edition_date,
            citation=_optional_text(row["edition_citation"]),
        )
    except ValidationError as error:
        field_name = _validation_field(
            error,
            {
                "edition_id": "edition_id",
                "work_id": "work_id",
                "edition_label": "edition_label",
                "citation": "edition_citation",
            },
            "edition_id",
        )
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, field_name) from error

    try:
        source = SourceRecord.model_validate(
            {
                "source_id": row["source_id"],
                "edition_id": edition.edition_id,
                "source_type": _term(row, "source_type"),
                "title": row["source_title"],
                "source_url": _optional_text(row["source_url"]),
                "bibliographic_citation": _optional_text(row["source_bibliographic_citation"]),
                "accessed_on": _optional_date(row["source_accessed_on"], "source_accessed_on"),
            }
        )
    except ValidationError as error:
        field_name = _validation_field(
            error,
            {
                "source_id": "source_id",
                "edition_id": "edition_id",
                "source_type": "source_type_value",
                "title": "source_title",
                "source_url": "source_url",
                "bibliographic_citation": "source_bibliographic_citation",
                "accessed_on": "source_accessed_on",
            },
            "source_url",
        )
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, field_name) from error

    rights = _parse_rights(row)
    rights_sources = _parse_rights_sources(row)
    expected_rights_source_ids = {record.source_id for record in rights} - {source.source_id}
    supplied_rights_source_ids = {record.source_id for record in rights_sources}
    if supplied_rights_source_ids != expected_rights_source_ids:
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, "rights_sources_json")
    try:
        asset = AssetRecord(
            asset_id=row["asset_id"],
            file_label=validated_file.file_label,
            content_sha256=validated_file.content_sha256,
            work_id=work.work_id,
            edition_id=edition.edition_id,
            source_id=source.source_id,
            rights_asset_ids=tuple(sorted(record.asset_id for record in rights)),
            rights_chain_confirmed=_boolean(
                row["rights_chain_confirmed"], "rights_chain_confirmed"
            ),
            normalization_profile=row["normalization_profile"],
            normalization_notes=_optional_text(row["normalization_notes"]),
            mapping_confirmed=_boolean(row["mapping_confirmed"], "mapping_confirmed"),
            line_count=_optional_int(row["line_count"], "line_count"),
            token_count=_optional_int(row["token_count"], "token_count"),
        )
    except ValidationError as error:
        field_name = _validation_field(
            error,
            {
                "asset_id": "asset_id",
                "file_label": "file_label",
                "content_sha256": "content_sha256",
                "work_id": "work_id",
                "edition_id": "edition_id",
                "source_id": "source_id",
                "rights_asset_ids": "rights_records_json",
                "rights_chain_confirmed": "rights_chain_confirmed",
                "normalization_profile": "normalization_profile",
                "normalization_notes": "normalization_notes",
                "mapping_confirmed": "mapping_confirmed",
                "line_count": "line_count",
                "token_count": "token_count",
            },
            "asset_id",
        )
        raise _CellFailure(MetadataCsvIssueCode.VALUE_INVALID, field_name) from error

    return _ParsedRow(
        row_number=row_number,
        authors=(primary_author, *additional_authors),
        work=work,
        edition=edition,
        source=source,
        rights_sources=rights_sources,
        asset=asset,
        rights=rights,
    )


def _catalog(
    validated_files: Sequence[ValidatedFileRecord],
) -> tuple[dict[str, ValidatedFileRecord] | None, MetadataCsvIssue | None]:
    if not validated_files:
        return None, _issue(MetadataCsvIssueCode.CATALOG_CONFLICT, "file_label")
    by_label: dict[str, ValidatedFileRecord] = {}
    casefolded: set[str] = set()
    for record in validated_files:
        key = record.file_label.casefold()
        if key in casefolded:
            return None, _issue(MetadataCsvIssueCode.CATALOG_CONFLICT, "file_label")
        casefolded.add(key)
        by_label[record.file_label] = record
    return by_label, None


def _semantic_key(model: FrozenModel) -> bytes:
    return canonical_json_bytes(model.model_dump(mode="json"))


def _merge_embedded_records[RecordT: FrozenModel](
    records: Sequence[RecordT],
    identifier: Callable[[RecordT], str],
    row_numbers: Sequence[int],
    field_names: str | Sequence[str],
) -> tuple[tuple[RecordT, ...], tuple[MetadataCsvIssue, ...]]:
    merged: dict[str, RecordT] = {}
    issues: list[MetadataCsvIssue] = []
    resolved_fields: Sequence[str] = (
        [field_names] * len(records) if isinstance(field_names, str) else field_names
    )
    for record, row_number, field_name in zip(
        records,
        row_numbers,
        resolved_fields,
        strict=True,
    ):
        entity_id = identifier(record)
        existing = merged.get(entity_id)
        if existing is None:
            merged[entity_id] = record
        elif _semantic_key(existing) != _semantic_key(record):
            issues.append(
                _issue(
                    MetadataCsvIssueCode.ENTITY_CONFLICT,
                    field_name,
                    row_number=row_number,
                )
            )
    return (
        tuple(sorted(merged.values(), key=lambda item: (identifier(item), _semantic_key(item)))),
        tuple(issues),
    )


def _annotate_report(
    report: ValidationReport,
    row_map: dict[tuple[str, str], list[int]],
) -> ValidationReport:
    annotated = []
    for issue in report.issues:
        key = (issue.entity_type, issue.entity_id or "")
        rows = row_map.get(key, [])
        annotated.append(issue.model_copy(update={"row_number": rows[-1] if rows else None}))
    return report.model_copy(update={"issues": tuple(annotated)})


def _failed_result(
    payload: bytes,
    issues: Sequence[MetadataCsvIssue],
    *,
    row_count: int,
) -> MetadataCsvImportResult:
    return MetadataCsvImportResult(
        csv_sha256=hashlib.sha256(payload).hexdigest(),
        row_count=row_count,
        blocked=True,
        issues=tuple(issues),
        inventory=None,
        validation_report=None,
    )


def import_metadata_csv(
    payload: bytes,
    validated_files: Sequence[ValidatedFileRecord],
    *,
    display_label: str = "metadata.csv",
    limits: IngestionLimits = DEFAULT_LIMITS,
) -> MetadataCsvImportResult:
    """Validate untrusted bytes, then build and domain-validate one inventory.

    Import failures are content-free. No partial inventory is returned when a row
    cannot be parsed, a file is unmatched, or an embedded identity conflicts.
    """

    digest = hashlib.sha256(payload).hexdigest()
    try:
        receipt = validate_upload(
            IncomingUpload(
                role=IntakeRole.METADATA_CSV,
                display_label=display_label,
                data=payload,
                declared_mime="text/csv",
            ),
            limits=limits,
            id_factory=lambda: _FIXED_ID,
        )
    except IntakeError as error:
        return _failed_result(
            payload,
            (
                _issue(
                    MetadataCsvIssueCode.INTAKE_REJECTED,
                    "csv",
                    intake_error_code=error.code,
                ),
            ),
            row_count=0,
        )

    text = payload.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""), dialect="excel", strict=True)
    fieldnames = tuple(reader.fieldnames or ())
    rows = list(reader)
    row_count = receipt.row_count or len(rows)

    header_issues: list[MetadataCsvIssue] = []
    missing_headers = [name for name in CSV_COLUMNS if name not in fieldnames]
    for name in missing_headers:
        header_issues.append(_issue(MetadataCsvIssueCode.HEADER_MISMATCH, name))
    if len(fieldnames) != len(CSV_COLUMNS) or any(name not in CSV_COLUMNS for name in fieldnames):
        header_issues.append(_issue(MetadataCsvIssueCode.HEADER_MISMATCH, "header"))
    if header_issues:
        return _failed_result(payload, header_issues, row_count=row_count)

    catalog_by_label, catalog_issue = _catalog(validated_files)
    if catalog_issue is not None or catalog_by_label is None:
        assert catalog_issue is not None
        return _failed_result(payload, (catalog_issue,), row_count=row_count)

    issues: list[MetadataCsvIssue] = []
    parsed_rows: list[_ParsedRow] = []
    global_values: tuple[str, str, str, str] | None = None
    for offset, row in enumerate(rows, start=2):
        missing_values = [
            name for name in CSV_COLUMNS if name in REQUIRED_VALUE_FIELDS and not row[name].strip()
        ]
        for name in missing_values:
            issues.append(
                _issue(
                    MetadataCsvIssueCode.REQUIRED_VALUE_MISSING,
                    name,
                    row_number=offset,
                )
            )
        if missing_values:
            continue

        versions = (
            row["csv_schema_version"],
            row["inventory_schema_version"],
            row["vocabulary_profile"],
            row["purpose"],
        )
        if versions[:3] != (
            CORPUS_METADATA_CSV_VERSION,
            _INVENTORY_VERSION,
            _VOCABULARY_VERSION,
        ):
            issues.append(
                _issue(
                    MetadataCsvIssueCode.VERSION_UNSUPPORTED,
                    "csv_schema_version",
                    row_number=offset,
                )
            )
            continue
        if global_values is None:
            global_values = versions
        elif versions != global_values:
            issues.append(
                _issue(
                    MetadataCsvIssueCode.GLOBAL_VALUE_CONFLICT,
                    "purpose",
                    row_number=offset,
                )
            )
            continue
        try:
            PurposeId(row["purpose"])
            parsed_rows.append(_parse_row(row, offset, catalog_by_label))
        except _CellFailure as error:
            issues.append(_issue(error.code, error.field_name, row_number=offset))
        except ValueError:
            issues.append(
                _issue(
                    MetadataCsvIssueCode.VALUE_INVALID,
                    "purpose",
                    row_number=offset,
                )
            )

    if issues:
        return _failed_result(payload, issues, row_count=row_count)

    embedded_authors: list[AuthorRecord] = []
    author_rows: list[int] = []
    embedded_rights: list[AssetRightsRecord] = []
    rights_rows: list[int] = []
    embedded_sources: list[SourceRecord] = []
    source_rows: list[int] = []
    source_fields: list[str] = []
    for parsed in parsed_rows:
        embedded_authors.extend(parsed.authors)
        author_rows.extend([parsed.row_number] * len(parsed.authors))
        embedded_rights.extend(parsed.rights)
        rights_rows.extend([parsed.row_number] * len(parsed.rights))
        embedded_sources.append(parsed.source)
        source_rows.append(parsed.row_number)
        source_fields.append("source_id")
        embedded_sources.extend(parsed.rights_sources)
        source_rows.extend([parsed.row_number] * len(parsed.rights_sources))
        source_fields.extend(["rights_sources_json"] * len(parsed.rights_sources))

    authors, author_issues = _merge_embedded_records(
        embedded_authors,
        lambda item: item.author_id,
        author_rows,
        "primary_author_id",
    )
    rights, rights_issues = _merge_embedded_records(
        embedded_rights,
        lambda item: item.asset_id,
        rights_rows,
        "rights_records_json",
    )
    sources, source_issues = _merge_embedded_records(
        embedded_sources,
        lambda item: item.source_id,
        source_rows,
        source_fields,
    )
    merge_issues = (*author_issues, *rights_issues, *source_issues)
    if merge_issues:
        return _failed_result(payload, merge_issues, row_count=row_count)

    purpose = PurposeId(rows[0]["purpose"])
    inventory = CorpusInventory(
        purpose=purpose,
        authors=authors,
        works=tuple(
            sorted((item.work for item in parsed_rows), key=lambda item: _semantic_key(item))
        ),
        editions=tuple(
            sorted((item.edition for item in parsed_rows), key=lambda item: _semantic_key(item))
        ),
        sources=sources,
        assets=tuple(
            sorted((item.asset for item in parsed_rows), key=lambda item: _semantic_key(item))
        ),
        validated_files=tuple(sorted(validated_files, key=lambda item: _semantic_key(item))),
        rights=rights,
    )

    row_map: dict[tuple[str, str], list[int]] = defaultdict(list)
    for parsed in parsed_rows:
        row_map[("work", parsed.work.work_id)].append(parsed.row_number)
        row_map[("edition", parsed.edition.edition_id)].append(parsed.row_number)
        row_map[("source", parsed.source.source_id)].append(parsed.row_number)
        for rights_source in parsed.rights_sources:
            row_map[("source", rights_source.source_id)].append(parsed.row_number)
        row_map[("asset", parsed.asset.asset_id)].append(parsed.row_number)
        row_map[("validated_file", parsed.asset.file_label)].append(parsed.row_number)
        for author in parsed.authors:
            row_map[("author", author.author_id)].append(parsed.row_number)
        for rights_record in parsed.rights:
            row_map[("rights", rights_record.asset_id)].append(parsed.row_number)

    validation_report = _annotate_report(validate_inventory(inventory), row_map)
    return MetadataCsvImportResult(
        csv_sha256=digest,
        row_count=row_count,
        blocked=validation_report.blocked,
        issues=(),
        inventory=inventory,
        validation_report=validation_report,
    )


def _compact_json(value: Any) -> str:
    if not _json_value_is_safe(value):
        raise MetadataCsvExportError(
            MetadataCsvExportErrorCode.P003_POLICY_REJECTED,
            IntakeErrorCode.CSV_INJECTION,
        )
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _date_columns(value: DateValue, prefix: str) -> dict[str, str]:
    return {
        f"{prefix}_mode": value.mode.value,
        f"{prefix}_start_year": "" if value.start_year is None else str(value.start_year),
        f"{prefix}_end_year": "" if value.end_year is None else str(value.end_year),
        f"{prefix}_label": value.display_label or "",
    }


def _term_columns(value: VocabularyTerm, prefix: str) -> dict[str, str]:
    return {
        f"{prefix}_value": value.value,
        f"{prefix}_label": value.label,
        f"{prefix}_kind": value.kind.value,
    }


def _write_csv(rows: Sequence[dict[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=CSV_COLUMNS,
        dialect="excel",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _validate_generated_csv(payload: bytes, limits: IngestionLimits) -> None:
    try:
        validate_upload(
            IncomingUpload(IntakeRole.METADATA_CSV, "metadata.csv", payload, "text/csv"),
            limits=limits,
            id_factory=lambda: _FIXED_ID,
        )
    except IntakeError as error:
        raise MetadataCsvExportError(
            MetadataCsvExportErrorCode.P003_POLICY_REJECTED,
            error.code,
        ) from None


def _proposed_slug(file_label: str, content_sha256: str) -> str:
    stem = PurePath(file_label).stem
    ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "_", ascii_stem.casefold()).strip("_")
    if not normalized or not normalized[0].isalpha():
        normalized = f"work_{normalized}".rstrip("_")
    label_sha256 = hashlib.sha256(file_label.encode("utf-8")).hexdigest()
    return f"{normalized}_{label_sha256[:16]}_{content_sha256[:8]}"


def metadata_csv_template(
    validated_files: Sequence[ValidatedFileRecord],
    purpose: PurposeId,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
) -> bytes:
    """Create one secure, prefilled row per validated TXT without guessing scholarship."""

    catalog_by_label, catalog_issue = _catalog(validated_files)
    if catalog_issue is not None or catalog_by_label is None:
        raise MetadataCsvExportError(MetadataCsvExportErrorCode.DUPLICATE_IDENTIFIER)
    rows: list[dict[str, str]] = []
    proposed_ids: set[str] = set()
    for validated_file in sorted(validated_files, key=lambda item: item.file_label):
        work_id = _proposed_slug(validated_file.file_label, validated_file.content_sha256)
        if work_id in proposed_ids:
            raise MetadataCsvExportError(MetadataCsvExportErrorCode.DUPLICATE_IDENTIFIER)
        proposed_ids.add(work_id)
        row = dict.fromkeys(CSV_COLUMNS, "")
        row.update(
            {
                "csv_schema_version": CORPUS_METADATA_CSV_VERSION,
                "inventory_schema_version": _INVENTORY_VERSION,
                "vocabulary_profile": _VOCABULARY_VERSION,
                "purpose": purpose.value,
                "file_label": validated_file.file_label,
                "content_sha256": validated_file.content_sha256,
                "asset_id": f"asset_{work_id}",
                "work_id": work_id,
                "primary_author_authorities_json": "[]",
                "additional_contributors_json": "[]",
                "first_publication_mode": "unknown",
                "genre_value": "unknown",
                "genre_label": "Unknown",
                "genre_kind": "unknown",
                "audience_value": "unknown",
                "audience_label": "Unknown",
                "audience_kind": "unknown",
                "adaptation_value": "unknown",
                "adaptation_label": "Unknown",
                "adaptation_kind": "unknown",
                "collection_value": "unknown",
                "collection_label": "Unknown",
                "collection_kind": "unknown",
                "edition_id": f"{work_id}_edition",
                "edition_date_mode": "unknown",
                "source_id": f"{work_id}_source",
                "source_type_value": "unknown",
                "source_type_label": "Unknown",
                "source_type_kind": "unknown",
                "normalization_profile": "nfc_validated_v1",
                "mapping_confirmed": "false",
                "rights_chain_confirmed": "false",
                "intake_profile": validated_file.intake_profile,
                "intake_status": validated_file.status,
                "rights_sources_json": "[]",
                "rights_records_json": "[]",
            }
        )
        rows.append(row)
    payload = _write_csv(rows)
    _validate_generated_csv(payload, limits)
    return payload


def _unique_map[RecordT: FrozenModel](
    records: Sequence[RecordT], identifier: Callable[[RecordT], str]
) -> dict[str, RecordT]:
    result: dict[str, RecordT] = {}
    for record in records:
        key = identifier(record)
        if key in result:
            raise MetadataCsvExportError(MetadataCsvExportErrorCode.DUPLICATE_IDENTIFIER)
        result[key] = record
    return result


def _required[RecordT](records: dict[str, RecordT], identifier: str) -> RecordT:
    record = records.get(identifier)
    if record is None:
        raise MetadataCsvExportError(MetadataCsvExportErrorCode.RELATIONSHIP_UNRESOLVED)
    return record


def _contributor_payload(author: AuthorRecord, role: ContributorRole) -> dict[str, Any]:
    payload = author.model_dump(mode="json")
    payload["role"] = role.value
    return payload


def _require_representable_inventory(
    *,
    authors: dict[str, AuthorRecord],
    works: dict[str, WorkRecord],
    editions: dict[str, EditionRecord],
    sources: dict[str, SourceRecord],
    validated_files: dict[str, ValidatedFileRecord],
    rights: dict[str, AssetRightsRecord],
    assets: dict[str, AssetRecord],
) -> None:
    work_ids = {asset.work_id for asset in assets.values()}
    edition_ids = {asset.edition_id for asset in assets.values()}
    validated_file_labels = {asset.file_label for asset in assets.values()}
    rights_ids = {rights_id for asset in assets.values() for rights_id in asset.rights_asset_ids}
    for work_id in work_ids:
        _required(works, work_id)
    for edition_id in edition_ids:
        _required(editions, edition_id)
    for file_label in validated_file_labels:
        _required(validated_files, file_label)
    for rights_id in rights_ids:
        _required(rights, rights_id)

    source_ids = {asset.source_id for asset in assets.values()}
    source_ids.update(rights[rights_id].source_id for rights_id in rights_ids)
    for source_id in source_ids:
        source = _required(sources, source_id)
        if source.edition_id not in edition_ids:
            raise MetadataCsvExportError(MetadataCsvExportErrorCode.RELATIONSHIP_UNRESOLVED)

    author_ids = {
        contributor.author_id
        for work_id in work_ids
        for contributor in _required(works, work_id).contributors
    }
    for author_id in author_ids:
        _required(authors, author_id)

    represented = (
        (set(authors), author_ids),
        (set(works), work_ids),
        (set(editions), edition_ids),
        (set(sources), source_ids),
        (set(validated_files), validated_file_labels),
        (set(rights), rights_ids),
    )
    if any(available != referenced for available, referenced in represented):
        raise MetadataCsvExportError(MetadataCsvExportErrorCode.RELATIONSHIP_UNRESOLVED)


def export_metadata_csv(
    inventory: CorpusInventory,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
) -> bytes:
    """Export a deterministically ordered, P003-safe metadata CSV."""

    authors = _unique_map(
        tuple(_canonical_author(item) for item in inventory.authors),
        lambda item: item.author_id,
    )
    works = _unique_map(inventory.works, lambda item: item.work_id)
    editions = _unique_map(inventory.editions, lambda item: item.edition_id)
    sources = _unique_map(inventory.sources, lambda item: item.source_id)
    validated_files = _unique_map(inventory.validated_files, lambda item: item.file_label)
    rights = _unique_map(
        tuple(_canonical_rights(item) for item in inventory.rights),
        lambda item: item.asset_id,
    )
    assets = _unique_map(inventory.assets, lambda item: item.asset_id)
    _require_representable_inventory(
        authors=authors,
        works=works,
        editions=editions,
        sources=sources,
        validated_files=validated_files,
        rights=rights,
        assets=assets,
    )

    rows: list[dict[str, str]] = []
    for asset in sorted(
        assets.values(),
        key=lambda item: (item.work_id, item.asset_id, _semantic_key(item)),
    ):
        work = _required(works, asset.work_id)
        edition = _required(editions, asset.edition_id)
        source = _required(sources, asset.source_id)
        validated_file = _required(validated_files, asset.file_label)

        contributor_pairs = []
        for contributor in work.contributors:
            author = _required(authors, contributor.author_id)
            contributor_pairs.append((contributor, author))
        contributor_pairs.sort(
            key=lambda pair: (pair[0].role.value, pair[0].author_id, _semantic_key(pair[1]))
        )
        primary_index = next(
            (
                index
                for index, pair in enumerate(contributor_pairs)
                if pair[0].role is ContributorRole.AUTHOR
            ),
            None,
        )
        if primary_index is None:
            raise MetadataCsvExportError(MetadataCsvExportErrorCode.RELATIONSHIP_UNRESOLVED)
        primary_contributor, primary_author = contributor_pairs.pop(primary_index)
        del primary_contributor
        additional_contributors = [
            _contributor_payload(author, contributor.role)
            for contributor, author in contributor_pairs
        ]

        rights_records = [_required(rights, rights_id) for rights_id in asset.rights_asset_ids]
        rights_records.sort(key=lambda item: (item.asset_id, _semantic_key(item)))
        rights_source_ids = sorted(
            {record.source_id for record in rights_records if record.source_id != source.source_id}
        )
        rights_sources = [_required(sources, source_id) for source_id in rights_source_ids]
        row = dict.fromkeys(CSV_COLUMNS, "")
        row.update(
            {
                "csv_schema_version": CORPUS_METADATA_CSV_VERSION,
                "inventory_schema_version": inventory.schema_version,
                "vocabulary_profile": inventory.vocabulary_profile,
                "purpose": inventory.purpose.value,
                "file_label": asset.file_label,
                "content_sha256": asset.content_sha256,
                "asset_id": asset.asset_id,
                "work_id": work.work_id,
                "title_original": work.title_original,
                "title_english": work.title_english or "",
                "language": work.language,
                "primary_author_id": primary_author.author_id,
                "primary_author_name": primary_author.display_name,
                "primary_author_kind": primary_author.kind.value,
                "primary_author_authorities_json": _compact_json(
                    [item.model_dump(mode="json") for item in primary_author.authority_identifiers]
                ),
                "additional_contributors_json": _compact_json(additional_contributors),
                "group_label": work.group_label or "",
                "edition_id": edition.edition_id,
                "edition_label": edition.edition_label,
                "edition_citation": edition.citation or "",
                "source_id": source.source_id,
                "source_title": source.title,
                "source_url": str(source.source_url) if source.source_url is not None else "",
                "source_bibliographic_citation": source.bibliographic_citation or "",
                "source_accessed_on": (
                    source.accessed_on.isoformat() if source.accessed_on is not None else ""
                ),
                "normalization_profile": asset.normalization_profile,
                "normalization_notes": asset.normalization_notes or "",
                "mapping_confirmed": str(asset.mapping_confirmed).lower(),
                "rights_chain_confirmed": str(asset.rights_chain_confirmed).lower(),
                "line_count": "" if asset.line_count is None else str(asset.line_count),
                "token_count": "" if asset.token_count is None else str(asset.token_count),
                "intake_profile": validated_file.intake_profile,
                "intake_status": validated_file.status,
                "rights_sources_json": _compact_json(
                    [item.model_dump(mode="json") for item in rights_sources]
                ),
                "rights_records_json": _compact_json(
                    [item.model_dump(mode="json") for item in rights_records]
                ),
            }
        )
        row.update(_date_columns(work.first_publication, "first_publication"))
        row.update(_term_columns(work.genre, "genre"))
        row.update(_term_columns(work.audience, "audience"))
        row.update(_term_columns(work.adaptation, "adaptation"))
        row.update(_term_columns(work.collection, "collection"))
        row.update(_date_columns(edition.edition_date, "edition_date"))
        row.update(_term_columns(source.source_type, "source_type"))
        rows.append(row)

    payload = _write_csv(rows)
    _validate_generated_csv(payload, limits)
    return payload


def metadata_csv_field_dictionary_json() -> bytes:
    """Return the exact downloadable field dictionary used by the parser."""

    return FIELD_DICTIONARY.model_dump_json(indent=2, exclude_none=True).encode("utf-8") + b"\n"


__all__ = [
    "export_metadata_csv",
    "import_metadata_csv",
    "metadata_csv_field_dictionary_json",
    "metadata_csv_template",
]
