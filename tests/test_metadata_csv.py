from __future__ import annotations

import csv
import io
import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from delta_lemmata import metadata_csv as metadata_csv_module
from delta_lemmata.corpus import (
    CORPUS_METADATA_CSV_VERSION,
    CSV_COLUMNS,
    FIELD_DICTIONARY,
    ActionPermissions,
    AssetRightsRecord,
    AssetType,
    AuthorityIdentifier,
    AuthorityScheme,
    AuthorKind,
    AuthorRecord,
    ContributorRecord,
    ContributorRole,
    CorpusInventory,
    DateMode,
    DateValue,
    FieldRequirement,
    IssueCode,
    MetadataCsvExportError,
    MetadataCsvExportErrorCode,
    MetadataCsvFieldDictionary,
    MetadataCsvImportResult,
    MetadataCsvIssue,
    MetadataCsvIssueCode,
    PermissionState,
    PurposeId,
    RightsEvidence,
    RightsStatus,
    SourceRecord,
    ValidatedFileRecord,
    canonical_inventory_payload,
    export_metadata_csv,
    import_metadata_csv,
    inventory_sha256,
    metadata_csv_field_dictionary_json,
    metadata_csv_template,
)
from delta_lemmata.ingestion import DEFAULT_LIMITS, IntakeErrorCode, csv_cell_is_safe

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "p004"


def _inventory() -> CorpusInventory:
    return CorpusInventory.model_validate_json(
        (FIXTURES / "inventory-valid-text-proximity.json").read_text(encoding="utf-8")
    )


def _rows(payload: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(payload.decode("utf-8"), newline=""), strict=True))


def _payload(rows: list[dict[str, str]], headers: tuple[str, ...] = CSV_COLUMNS) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _two_rows() -> tuple[list[dict[str, str]], tuple[ValidatedFileRecord, ...]]:
    inventory = _inventory()
    first = _rows(export_metadata_csv(inventory))[0]
    second = dict(first)
    second.update(
        {
            "file_label": "fixture_two.txt",
            "content_sha256": "2" * 64,
            "asset_id": "asset_fixture_two",
            "work_id": "fixture_work_two",
            "title_original": "Fixture opera two",
            "first_publication_start_year": "1890",
            "edition_id": "fixture_edition_two",
            "source_id": "fixture_source_two",
        }
    )
    rights = json.loads(second["rights_records_json"])
    rights[0]["asset_id"] = "asset_fixture_two"
    rights[0]["source_id"] = "fixture_source_two"
    second["rights_records_json"] = json.dumps(
        rights, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    second_file = ValidatedFileRecord(
        file_label="fixture_two.txt",
        content_sha256="2" * 64,
        intake_profile="ingestion-limits-v1",
    )
    return [first, second], (*inventory.validated_files, second_file)


def _domain_codes(result: MetadataCsvImportResult) -> dict[IssueCode, int | None]:
    assert result.validation_report is not None
    return {issue.code: issue.row_number for issue in result.validation_report.issues}


def test_field_dictionary_is_versioned_ordered_downloadable_and_below_p003_limit() -> None:
    assert FIELD_DICTIONARY.csv_schema_version == CORPUS_METADATA_CSV_VERSION
    assert len(CSV_COLUMNS) == 58
    assert len(CSV_COLUMNS) <= DEFAULT_LIMITS.max_csv_columns
    assert CSV_COLUMNS == tuple(field.name for field in FIELD_DICTIONARY.columns)
    assert FIELD_DICTIONARY.columns[0].requirement is FieldRequirement.REQUIRED
    downloaded = json.loads(metadata_csv_field_dictionary_json())
    assert downloaded["schema_version"] == "corpus-metadata-field-dictionary-v1"
    assert [field["name"] for field in downloaded["columns"]] == list(CSV_COLUMNS)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data["columns"][1].update(position=3),
        lambda data: data["columns"][1].update(name=data["columns"][0]["name"]),
    ],
)
def test_field_dictionary_rejects_nonconsecutive_or_duplicate_columns(mutation: object) -> None:
    payload = FIELD_DICTIONARY.model_dump(mode="json")
    assert callable(mutation)
    mutation(payload)
    with pytest.raises(ValidationError):
        MetadataCsvFieldDictionary.model_validate(payload)


def test_template_prefills_only_safe_technical_values_and_passes_p003() -> None:
    validated_file = ValidatedFileRecord(
        file_label="123-collodi-à.txt",
        content_sha256="a" * 64,
        intake_profile="ingestion-limits-v1",
    )
    payload = metadata_csv_template((validated_file,), PurposeId.STYLE_OVER_TIME)
    row = _rows(payload)[0]
    assert tuple(row) == CSV_COLUMNS
    assert row["file_label"] == validated_file.file_label
    assert row["work_id"].startswith("work_123_collodi_a_")
    assert row["asset_id"] == f"asset_{row['work_id']}"
    assert row["title_original"] == ""
    assert row["primary_author_name"] == ""
    assert row["mapping_confirmed"] == "false"
    assert row["rights_sources_json"] == "[]"
    assert row["rights_records_json"] == "[]"

    result = import_metadata_csv(payload, (validated_file,))
    assert result.blocked is True
    assert result.inventory is None
    assert any(
        issue.code is MetadataCsvIssueCode.REQUIRED_VALUE_MISSING
        and issue.row_number == 2
        and issue.field_name == "title_original"
        for issue in result.issues
    )


def test_valid_inventory_round_trips_exactly_and_export_is_deterministic() -> None:
    inventory = _inventory()
    first = export_metadata_csv(inventory)
    second = export_metadata_csv(inventory)
    assert first == second
    assert tuple(_rows(first)[0]) == CSV_COLUMNS

    imported = import_metadata_csv(first, inventory.validated_files)
    assert imported.blocked is False
    assert imported.issues == ()
    assert imported.inventory == inventory
    assert imported.validation_report is not None
    assert imported.validation_report.issues == ()
    assert inventory_sha256(imported.inventory) == inventory_sha256(inventory)


def test_checked_in_valid_invalid_and_blank_templates_match_the_executable_contract() -> None:
    inventory = _inventory()
    valid_fixture = (FIXTURES / "metadata-valid-v1.csv").read_bytes()
    assert valid_fixture == export_metadata_csv(inventory)
    valid_result = import_metadata_csv(valid_fixture, inventory.validated_files)
    assert valid_result.inventory == inventory

    invalid_fixture = (FIXTURES / "metadata-invalid-domain-v1.csv").read_bytes()
    invalid_result = import_metadata_csv(invalid_fixture, inventory.validated_files)
    invalid_codes = _domain_codes(invalid_result)
    assert {
        IssueCode.DATE_RANGE_REVERSED,
        IssueCode.CONTROLLED_TERM_UNKNOWN,
        IssueCode.FILE_MAPPING_UNCONFIRMED,
    } <= set(invalid_codes)
    assert all(invalid_codes[code] == 2 for code in invalid_codes)

    example_file = ValidatedFileRecord(
        file_label="example_work.txt",
        content_sha256="0" * 64,
        intake_profile="ingestion-limits-v1",
    )
    checked_in_template = (
        Path(__file__).resolve().parents[1] / "templates" / "corpus-metadata-v1.csv"
    ).read_bytes()
    assert checked_in_template == metadata_csv_template((example_file,), PurposeId.TEXT_PROXIMITY)


def test_round_trip_preserves_multiple_contributors_authorities_and_rights_layers() -> None:
    inventory = _inventory()
    translator = AuthorRecord(
        author_id="fixture_translator",
        display_name="Fixture Translator",
        kind=AuthorKind.PERSON,
        authority_identifiers=(
            AuthorityIdentifier(
                scheme=AuthorityScheme.ORCID,
                value="0000-0000-0000-0001",
                url="https://orcid.org/0000-0000-0000-0001",
            ),
        ),
    )
    work = inventory.works[0].model_copy(
        update={
            "contributors": (
                *inventory.works[0].contributors,
                ContributorRecord(
                    author_id=translator.author_id,
                    role=ContributorRole.TRANSLATOR,
                ),
            )
        }
    )
    underlying = inventory.rights[0].model_copy(
        update={
            "asset_id": "asset_underlying_fixture",
            "asset_type": AssetType.UNDERLYING_WORK,
            "source_id": "fixture_rights_source",
        }
    )
    rights_source = inventory.sources[0].model_copy(
        update={
            "source_id": "fixture_rights_source",
            "title": "Fixture rights source",
        }
    )
    asset = inventory.assets[0].model_copy(
        update={
            "rights_asset_ids": (
                inventory.assets[0].asset_id,
                underlying.asset_id,
            )
        }
    )
    expanded = inventory.model_copy(
        update={
            "authors": (*inventory.authors, translator),
            "works": (work,),
            "sources": (*inventory.sources, rights_source),
            "assets": (asset,),
            "rights": (*inventory.rights, underlying),
        }
    )
    payload = export_metadata_csv(expanded)
    row = _rows(payload)[0]
    assert json.loads(row["additional_contributors_json"])[0]["role"] == "translator"
    assert json.loads(row["rights_sources_json"])[0]["source_id"] == "fixture_rights_source"
    assert len(json.loads(row["rights_records_json"])) == 2

    imported = import_metadata_csv(payload, expanded.validated_files)
    assert imported.blocked is False
    assert imported.inventory == expanded
    assert inventory_sha256(imported.inventory) == inventory_sha256(expanded)


def test_missing_or_duplicate_dependency_source_is_reported_at_rights_sources_column() -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    rights = json.loads(row["rights_records_json"])
    rights[0]["source_id"] = "separate_rights_source"
    row["rights_records_json"] = json.dumps(rights, separators=(",", ":"))

    missing = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert missing.issues[0].code is MetadataCsvIssueCode.VALUE_INVALID
    assert missing.issues[0].field_name == "rights_sources_json"

    source = inventory.sources[0].model_copy(update={"source_id": "separate_rights_source"})
    source_payload = source.model_dump(mode="json")
    row["rights_sources_json"] = json.dumps([source_payload, source_payload], separators=(",", ":"))
    duplicate = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert duplicate.issues[0].code is MetadataCsvIssueCode.JSON_INVALID
    assert duplicate.issues[0].field_name == "rights_sources_json"


def test_statement_only_claim_cannot_open_public_redistribution_through_csv() -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    rights = json.loads(row["rights_records_json"])
    rights[0].update(
        {
            "rights_status": "verified_open",
            "license": "CC0-1.0",
            "permissions": {
                "upload": "permitted",
                "analysis": "permitted",
                "export": "permitted",
                "public_redistribution": "permitted",
            },
            "evidence": [{"evidence_type": "statement", "value": "Open claim"}],
            "jurisdiction": "Italy",
        }
    )
    row["rights_records_json"] = json.dumps(rights, separators=(",", ":"))
    result = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert result.inventory is None
    assert result.issues[0].code is MetadataCsvIssueCode.JSON_INVALID
    assert result.issues[0].field_name == "rights_records_json"


def test_export_canonicalizes_set_like_authority_and_evidence_order() -> None:
    inventory = _inventory()
    authorities = (
        AuthorityIdentifier(scheme=AuthorityScheme.VIAF, value="123"),
        AuthorityIdentifier(scheme=AuthorityScheme.ORCID, value="0000-0000-0000-0001"),
    )
    evidence = (
        RightsEvidence(evidence_type="statement", value="Second"),
        RightsEvidence(evidence_type="citation", value="First"),
    )
    first = inventory.model_copy(
        update={
            "authors": (
                inventory.authors[0].model_copy(update={"authority_identifiers": authorities}),
            ),
            "rights": (inventory.rights[0].model_copy(update={"evidence": evidence}),),
        }
    )
    second = inventory.model_copy(
        update={
            "authors": (
                inventory.authors[0].model_copy(
                    update={"authority_identifiers": tuple(reversed(authorities))}
                ),
            ),
            "rights": (
                inventory.rights[0].model_copy(update={"evidence": tuple(reversed(evidence))}),
            ),
        }
    )
    assert inventory_sha256(first) == inventory_sha256(second)
    assert export_metadata_csv(first) == export_metadata_csv(second)

    imported = import_metadata_csv(export_metadata_csv(second), second.validated_files)
    assert imported.inventory is not None
    assert canonical_inventory_payload(imported.inventory) == canonical_inventory_payload(second)
    assert export_metadata_csv(imported.inventory) == export_metadata_csv(second)


def test_header_order_may_change_but_export_returns_canonical_order() -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    imported = import_metadata_csv(
        _payload([row], tuple(reversed(CSV_COLUMNS))), inventory.validated_files
    )
    assert imported.inventory == inventory
    assert tuple(_rows(export_metadata_csv(imported.inventory))[0]) == CSV_COLUMNS


@pytest.mark.parametrize(
    ("change", "code", "field"),
    [
        ({"title_original": ""}, MetadataCsvIssueCode.REQUIRED_VALUE_MISSING, "title_original"),
        (
            {"csv_schema_version": "future-v9"},
            MetadataCsvIssueCode.VERSION_UNSUPPORTED,
            "csv_schema_version",
        ),
        ({"purpose": "invalid"}, MetadataCsvIssueCode.VALUE_INVALID, "purpose"),
        (
            {"first_publication_start_year": "not-a-year"},
            MetadataCsvIssueCode.VALUE_INVALID,
            "first_publication_start_year",
        ),
        (
            {"first_publication_mode": "future"},
            MetadataCsvIssueCode.VALUE_INVALID,
            "first_publication_mode",
        ),
        (
            {"first_publication_start_year": ""},
            MetadataCsvIssueCode.VALUE_INVALID,
            "first_publication_mode",
        ),
        (
            {"genre_kind": "unknown", "genre_value": "novel"},
            MetadataCsvIssueCode.VALUE_INVALID,
            "genre_value",
        ),
        ({"genre_kind": "future"}, MetadataCsvIssueCode.VALUE_INVALID, "genre_kind"),
        ({"mapping_confirmed": "yes"}, MetadataCsvIssueCode.VALUE_INVALID, "mapping_confirmed"),
        (
            {"source_accessed_on": "12/07/2026"},
            MetadataCsvIssueCode.VALUE_INVALID,
            "source_accessed_on",
        ),
        ({"rights_records_json": "{}"}, MetadataCsvIssueCode.JSON_INVALID, "rights_records_json"),
        ({"rights_records_json": "["}, MetadataCsvIssueCode.JSON_INVALID, "rights_records_json"),
        ({"rights_records_json": "[{}]"}, MetadataCsvIssueCode.JSON_INVALID, "rights_records_json"),
        ({"rights_sources_json": "{}"}, MetadataCsvIssueCode.JSON_INVALID, "rights_sources_json"),
        ({"rights_sources_json": "[{}]"}, MetadataCsvIssueCode.JSON_INVALID, "rights_sources_json"),
        (
            {"additional_contributors_json": "[{}]"},
            MetadataCsvIssueCode.JSON_INVALID,
            "additional_contributors_json",
        ),
        (
            {"primary_author_authorities_json": "[{}]"},
            MetadataCsvIssueCode.JSON_INVALID,
            "primary_author_authorities_json",
        ),
        ({"file_label": "unmatched.txt"}, MetadataCsvIssueCode.FILE_UNMATCHED, "file_label"),
        ({"content_sha256": "f" * 64}, MetadataCsvIssueCode.FILE_HASH_MISMATCH, "content_sha256"),
        (
            {"intake_profile": "ingestion-limits-v2"},
            MetadataCsvIssueCode.VALUE_INVALID,
            "intake_profile",
        ),
        ({"primary_author_id": "Bad Id"}, MetadataCsvIssueCode.VALUE_INVALID, "primary_author_id"),
        (
            {"primary_author_kind": "future"},
            MetadataCsvIssueCode.VALUE_INVALID,
            "primary_author_kind",
        ),
        ({"language": "not a language"}, MetadataCsvIssueCode.VALUE_INVALID, "language"),
        ({"asset_id": "Bad Id"}, MetadataCsvIssueCode.VALUE_INVALID, "asset_id"),
        ({"edition_id": "Bad Id"}, MetadataCsvIssueCode.VALUE_INVALID, "edition_id"),
        (
            {"source_url": "", "source_bibliographic_citation": ""},
            MetadataCsvIssueCode.VALUE_INVALID,
            "source_url",
        ),
        ({"rights_records_json": "[]"}, MetadataCsvIssueCode.JSON_INVALID, "rights_records_json"),
    ],
)
def test_import_reports_content_free_actionable_row_errors(
    change: dict[str, str], code: MetadataCsvIssueCode, field: str
) -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    row.update(change)
    result = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert result.blocked is True
    assert result.inventory is None
    assert result.validation_report is None
    assert any(
        issue.code is code and issue.row_number == 2 and issue.field_name == field
        for issue in result.issues
    )


def test_p003_rejection_is_retained_without_payload_content() -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    canary = "=SECRET-CANARY"
    row["title_original"] = canary
    result = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert result.issues[0].code is MetadataCsvIssueCode.INTAKE_REJECTED
    assert result.issues[0].intake_error_code is IntakeErrorCode.CSV_INJECTION
    assert canary not in result.model_dump_json()


def test_validation_field_uses_content_free_fallback_for_unmapped_model_location() -> None:
    with pytest.raises(ValidationError) as captured:
        SourceRecord.model_validate(
            {
                **_inventory().sources[0].model_dump(mode="json"),
                "source_id": "Bad Id",
            }
        )
    assert metadata_csv_module._validation_field(captured.value, {}, "source_id") == "source_id"


@pytest.mark.parametrize(
    "nested_value",
    [
        "=FORMULA",
        "../private",
        "line\nfeed",
        "<script>",
        "e\u0301",
        "\u202ehidden",
        "\ufeffhidden",
        "\x00hidden",
    ],
)
def test_decoded_nested_json_cannot_bypass_p003_cell_policy(nested_value: str) -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    rights = json.loads(row["rights_records_json"])
    rights[0]["notes"] = nested_value
    encoded = json.dumps(rights, ensure_ascii=True, separators=(",", ":"))
    if nested_value == "<script>":
        encoded = encoded.replace("<", r"\u003c").replace(">", r"\u003e")
    elif nested_value == "../private":
        encoded = encoded.replace("../private", r"\u002e\u002e\u002fprivate")
    row["rights_records_json"] = encoded
    result = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert result.inventory is None
    assert result.issues[0].code is MetadataCsvIssueCode.JSON_UNSAFE
    assert result.issues[0].field_name == "rights_records_json"
    assert csv_cell_is_safe(nested_value) is False


def test_p003_scalar_helper_accepts_ordinary_decoded_json_text() -> None:
    assert csv_cell_is_safe("Ordinary scholarly note") is True
    assert csv_cell_is_safe("tab\tinside") is True


def test_unsafe_decoded_json_key_and_excessive_depth_fail_closed() -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    row["additional_contributors_json"] = '[{"\\u003dformula":"value"}]'
    unsafe_key = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert unsafe_key.issues[0].code is MetadataCsvIssueCode.JSON_UNSAFE

    row = _rows(export_metadata_csv(inventory))[0]
    row["rights_records_json"] = "[" * 1200 + "]" * 1200
    deep = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert deep.issues[0].code is MetadataCsvIssueCode.JSON_INVALID
    assert deep.inventory is None


def test_nonstandard_json_constant_is_rejected() -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    row["additional_contributors_json"] = "[NaN]"
    result = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert result.issues[0].code is MetadataCsvIssueCode.JSON_INVALID
    assert result.inventory is None


def test_oversized_numeric_json_is_stopped_by_p003_token_limit() -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    row["additional_contributors_json"] = "[" + "9" * 5000 + "]"
    result = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert result.issues[0].code is MetadataCsvIssueCode.INTAKE_REJECTED
    assert result.issues[0].intake_error_code is IntakeErrorCode.TEXT_LIMIT


def test_duplicate_json_object_keys_are_not_silently_overwritten() -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    row["rights_records_json"] = row["rights_records_json"].replace(
        '"notes":""', '"notes":"first","notes":"second"'
    )
    result = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert result.issues[0].code is MetadataCsvIssueCode.JSON_INVALID
    assert result.inventory is None


def test_header_mismatch_identifies_expected_field_without_echoing_unknown_header() -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    row["unexpected"] = row.pop("title_original")
    headers = tuple(name for name in CSV_COLUMNS if name != "title_original") + ("unexpected",)
    result = import_metadata_csv(_payload([row], headers), inventory.validated_files)
    assert result.inventory is None
    assert any(
        issue.code is MetadataCsvIssueCode.HEADER_MISMATCH and issue.field_name == "title_original"
        for issue in result.issues
    )
    assert "unexpected" not in result.model_dump_json()


def test_rows_must_agree_on_corpus_level_values() -> None:
    rows, catalog = _two_rows()
    rows[1]["purpose"] = PurposeId.GROUP_COMPARISON.value
    result = import_metadata_csv(_payload(rows), catalog)
    assert result.inventory is None
    assert result.issues == (
        MetadataCsvIssue(
            code=MetadataCsvIssueCode.GLOBAL_VALUE_CONFLICT,
            row_number=3,
            field_name="purpose",
            message="Rows disagree about a corpus-level value.",
            why_it_matters=(
                "One inventory cannot use different purposes or schema profiles in different rows."
            ),
            how_to_fix="Use the same declared purpose and version values in every row.",
        ),
    )


@pytest.mark.parametrize("validated_files", [(), None])
def test_missing_or_ambiguous_catalog_fails_closed(validated_files: object) -> None:
    inventory = _inventory()
    payload = export_metadata_csv(inventory)
    if validated_files is None:
        original = inventory.validated_files[0]
        supplied = (original, original.model_copy(update={"file_label": "COLLODI_FIXTURE.TXT"}))
    else:
        supplied = validated_files
    result = import_metadata_csv(payload, supplied)
    assert result.issues[0].code is MetadataCsvIssueCode.CATALOG_CONFLICT
    assert result.inventory is None


def test_conflicting_embedded_author_or_rights_identity_is_rejected() -> None:
    rows, catalog = _two_rows()
    rows[1]["primary_author_name"] = "Conflicting Name"
    author_conflict = import_metadata_csv(_payload(rows), catalog)
    assert author_conflict.issues[0].code is MetadataCsvIssueCode.ENTITY_CONFLICT
    assert author_conflict.issues[0].row_number == 3

    rows, catalog = _two_rows()
    second_rights = json.loads(rows[1]["rights_records_json"])
    first_rights = json.loads(rows[0]["rights_records_json"])
    second_rights[0]["asset_id"] = first_rights[0]["asset_id"]
    second_rights[0]["notes"] = "conflict"
    rows[1]["rights_records_json"] = json.dumps(second_rights, separators=(",", ":"))
    rights_conflict = import_metadata_csv(_payload(rows), catalog)
    assert rights_conflict.issues[0].code is MetadataCsvIssueCode.ENTITY_CONFLICT
    assert rights_conflict.issues[0].field_name == "rights_records_json"


def test_domain_validation_adds_csv_rows_for_duplicate_date_and_vocabulary_errors() -> None:
    rows, catalog = _two_rows()
    rows[1]["work_id"] = rows[0]["work_id"]
    duplicate = import_metadata_csv(_payload(rows), catalog)
    assert duplicate.inventory is not None
    assert _domain_codes(duplicate)[IssueCode.DUPLICATE_WORK_ID] == 3

    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    row.update(
        {
            "first_publication_mode": "range",
            "first_publication_start_year": "1900",
            "first_publication_end_year": "1800",
        }
    )
    reversed_date = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert _domain_codes(reversed_date)[IssueCode.DATE_RANGE_REVERSED] == 2

    row = _rows(export_metadata_csv(inventory))[0]
    row["genre_value"] = "unregistered_genre"
    unknown_term = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert _domain_codes(unknown_term)[IssueCode.CONTROLLED_TERM_UNKNOWN] == 2


def test_false_confirmations_and_blank_counts_parse_then_block_at_domain_layer() -> None:
    inventory = _inventory()
    row = _rows(export_metadata_csv(inventory))[0]
    row.update(
        {
            "mapping_confirmed": "false",
            "rights_chain_confirmed": "false",
            "line_count": "",
            "token_count": "",
        }
    )
    result = import_metadata_csv(_payload([row]), inventory.validated_files)
    assert result.inventory is not None
    assert result.inventory.assets[0].line_count is None
    assert result.inventory.assets[0].token_count is None
    assert {
        IssueCode.FILE_MAPPING_UNCONFIRMED,
        IssueCode.RIGHTS_CHAIN_UNCONFIRMED,
    } <= set(_domain_codes(result))


def test_optional_online_source_range_dates_and_labels_round_trip() -> None:
    inventory = _inventory()
    work = inventory.works[0].model_copy(
        update={
            "title_english": "Fixture Work",
            "first_publication": DateValue(
                mode=DateMode.RANGE,
                start_year=1881,
                end_year=1883,
                display_label="Serial publication",
            ),
        }
    )
    edition = inventory.editions[0].model_copy(
        update={
            "edition_date": inventory.editions[0].edition_date.model_copy(
                update={"display_label": "Edition date"}
            )
        }
    )
    source = SourceRecord.model_validate(
        {
            **inventory.sources[0].model_dump(mode="json"),
            "source_url": "https://example.org/fixture",
            "accessed_on": date(2026, 7, 12),
        }
    )
    asset = inventory.assets[0].model_copy(
        update={
            "normalization_notes": "NFC checked",
            "line_count": None,
            "token_count": None,
        }
    )
    expanded = inventory.model_copy(
        update={
            "works": (work,),
            "editions": (edition,),
            "sources": (source,),
            "assets": (asset,),
        }
    )
    payload = export_metadata_csv(expanded)
    row = _rows(payload)[0]
    assert row["first_publication_end_year"] == "1883"
    assert row["source_url"] == "https://example.org/fixture"
    assert row["normalization_notes"] == "NFC checked"
    imported = import_metadata_csv(payload, expanded.validated_files)
    assert imported.inventory == expanded


def test_export_fails_closed_for_ambiguous_missing_or_p003_unsafe_state() -> None:
    inventory = _inventory()
    with pytest.raises(MetadataCsvExportError) as duplicate:
        export_metadata_csv(inventory.model_copy(update={"authors": inventory.authors * 2}))
    assert duplicate.value.code is MetadataCsvExportErrorCode.DUPLICATE_IDENTIFIER

    with pytest.raises(MetadataCsvExportError) as duplicate_asset:
        export_metadata_csv(inventory.model_copy(update={"assets": inventory.assets * 2}))
    assert duplicate_asset.value.code is MetadataCsvExportErrorCode.DUPLICATE_IDENTIFIER

    with pytest.raises(MetadataCsvExportError) as missing:
        export_metadata_csv(inventory.model_copy(update={"works": ()}))
    assert missing.value.code is MetadataCsvExportErrorCode.RELATIONSHIP_UNRESOLVED

    orphan_source = inventory.sources[0].model_copy(update={"source_id": "orphan_source"})
    with pytest.raises(MetadataCsvExportError) as orphan:
        export_metadata_csv(
            inventory.model_copy(update={"sources": (*inventory.sources, orphan_source)})
        )
    assert orphan.value.code is MetadataCsvExportErrorCode.RELATIONSHIP_UNRESOLVED

    separate_edition = inventory.editions[0].model_copy(update={"edition_id": "rights_edition"})
    separate_source = inventory.sources[0].model_copy(
        update={"source_id": "rights_source", "edition_id": separate_edition.edition_id}
    )
    dependency = inventory.rights[0].model_copy(
        update={"asset_id": "asset_dependency", "source_id": separate_source.source_id}
    )
    layered_asset = inventory.assets[0].model_copy(
        update={"rights_asset_ids": (*inventory.assets[0].rights_asset_ids, dependency.asset_id)}
    )
    with pytest.raises(MetadataCsvExportError) as unrepresentable_edition:
        export_metadata_csv(
            inventory.model_copy(
                update={
                    "editions": (*inventory.editions, separate_edition),
                    "sources": (*inventory.sources, separate_source),
                    "rights": (*inventory.rights, dependency),
                    "assets": (layered_asset,),
                }
            )
        )
    assert unrepresentable_edition.value.code is MetadataCsvExportErrorCode.RELATIONSHIP_UNRESOLVED

    unsafe_work = inventory.works[0].model_copy(update={"title_original": "<script>"})
    with pytest.raises(MetadataCsvExportError) as unsafe:
        export_metadata_csv(inventory.model_copy(update={"works": (unsafe_work,)}))
    assert unsafe.value.code is MetadataCsvExportErrorCode.P003_POLICY_REJECTED
    assert unsafe.value.intake_error_code is IntakeErrorCode.CSV_INJECTION

    unsafe_rights = inventory.rights[0].model_copy(
        update={"evidence": (RightsEvidence(evidence_type="statement", value="=FORMULA"),)}
    )
    with pytest.raises(MetadataCsvExportError) as nested_unsafe:
        export_metadata_csv(inventory.model_copy(update={"rights": (unsafe_rights,)}))
    assert nested_unsafe.value.code is MetadataCsvExportErrorCode.P003_POLICY_REJECTED
    assert nested_unsafe.value.intake_error_code is IntakeErrorCode.CSV_INJECTION

    no_author = inventory.works[0].model_copy(
        update={
            "contributors": (
                ContributorRecord(
                    author_id=inventory.authors[0].author_id,
                    role=ContributorRole.EDITOR,
                ),
            )
        }
    )
    with pytest.raises(MetadataCsvExportError) as author_role:
        export_metadata_csv(inventory.model_copy(update={"works": (no_author,)}))
    assert author_role.value.code is MetadataCsvExportErrorCode.RELATIONSHIP_UNRESOLVED


def test_template_rejects_empty_or_casefold_duplicate_catalog() -> None:
    with pytest.raises(MetadataCsvExportError) as empty:
        metadata_csv_template((), PurposeId.TEXT_PROXIMITY)
    assert empty.value.code is MetadataCsvExportErrorCode.DUPLICATE_IDENTIFIER

    first = ValidatedFileRecord(
        file_label="same.txt", content_sha256="1" * 64, intake_profile="ingestion-limits-v1"
    )
    second = first.model_copy(update={"file_label": "SAME.TXT", "content_sha256": "2" * 64})
    with pytest.raises(MetadataCsvExportError):
        metadata_csv_template((first, second), PurposeId.TEXT_PROXIMITY)

    ordinary = metadata_csv_template((first,), PurposeId.TEXT_PROXIMITY)
    assert _rows(ordinary)[0]["work_id"].startswith("same_")

    accent = ValidatedFileRecord(
        file_label="café.txt",
        content_sha256="3" * 64,
        intake_profile="ingestion-limits-v1",
    )
    ascii_label = accent.model_copy(update={"file_label": "cafe.txt"})
    collision_rows = _rows(metadata_csv_template((accent, ascii_label), PurposeId.TEXT_PROXIMITY))
    assert collision_rows[0]["work_id"] != collision_rows[1]["work_id"]


def test_template_fails_closed_if_proposed_identifier_digest_collides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = ValidatedFileRecord(
        file_label="first.txt", content_sha256="1" * 64, intake_profile="ingestion-limits-v1"
    )
    second = ValidatedFileRecord(
        file_label="second.txt", content_sha256="2" * 64, intake_profile="ingestion-limits-v1"
    )
    monkeypatch.setattr(metadata_csv_module, "_proposed_slug", lambda *_args: "same_id")
    with pytest.raises(MetadataCsvExportError) as collision:
        metadata_csv_template((first, second), PurposeId.TEXT_PROXIMITY)
    assert collision.value.code is MetadataCsvExportErrorCode.DUPLICATE_IDENTIFIER


def test_import_result_rejects_incoherent_partial_states() -> None:
    inventory = _inventory()
    report = import_metadata_csv(
        export_metadata_csv(inventory), inventory.validated_files
    ).validation_report
    assert report is not None
    base = {
        "csv_sha256": "1" * 64,
        "row_count": 1,
        "blocked": True,
        "issues": (),
        "inventory": inventory,
        "validation_report": report,
    }
    with pytest.raises(ValidationError):
        MetadataCsvImportResult.model_validate(
            {**base, "issues": (_dummy_issue(),), "inventory": inventory}
        )
    with pytest.raises(ValidationError):
        MetadataCsvImportResult.model_validate(
            {**base, "inventory": None, "validation_report": report}
        )
    with pytest.raises(ValidationError):
        MetadataCsvImportResult.model_validate(
            {**base, "inventory": inventory, "validation_report": None}
        )
    with pytest.raises(ValidationError):
        MetadataCsvImportResult.model_validate(
            {
                **base,
                "blocked": False,
                "inventory": None,
                "validation_report": None,
            }
        )


def _dummy_issue() -> MetadataCsvIssue:
    return MetadataCsvIssue(
        code=MetadataCsvIssueCode.VALUE_INVALID,
        row_number=2,
        field_name="work_id",
        message="Invalid.",
        why_it_matters="Identity matters.",
        how_to_fix="Correct the identifier.",
    )


def test_rights_json_fixture_uses_independent_action_permissions() -> None:
    rights = AssetRightsRecord(
        asset_id="asset_fixture",
        source_id="fixture_source",
        asset_type=AssetType.TRANSCRIPTION,
        rights_status=RightsStatus.PERMISSION_REQUIRED,
        permissions=ActionPermissions(
            upload=PermissionState.PERMITTED,
            analysis=PermissionState.PERMITTED,
            export=PermissionState.UNKNOWN,
            public_redistribution=PermissionState.PROHIBITED,
        ),
        evidence=(RightsEvidence(evidence_type="statement", value="Fixture permission"),),
        assessed_by="Test suite",
        assessed_at_utc="2026-07-12T00:00:00Z",
    )
    assert rights.permissions.export is PermissionState.UNKNOWN
