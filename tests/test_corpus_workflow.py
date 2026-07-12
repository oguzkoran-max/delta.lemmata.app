from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from delta_lemmata.corpus import (
    DateMode,
    DateValue,
    GuidedInventoryBuild,
    GuidedWorkInput,
    IssueCode,
    PurposeId,
    RightsStatus,
    build_guided_inventory,
    corpus_catalog_sha256,
    guided_work_id,
    metadata_csv_template,
    project_corpus_receipts,
    project_text_receipts,
    suggested_title,
)
from delta_lemmata.ingestion import ArchiveMemberReceipt, IntakeReceipt, IntakeRole


def _receipt(label: str, digest: str, transient: str) -> IntakeReceipt:
    return IntakeReceipt(
        asset_id=f"asset_{transient}",
        role=IntakeRole.CORPUS_TEXT,
        display_label=label,
        storage_name=f"asset_{transient}.txt",
        byte_size=12,
        expanded_bytes=12,
        sha256=digest,
        line_count=2,
        token_count=4,
        limit_profile="ingestion-limits-v1",
    )


def _guided_input(
    receipt: IntakeReceipt,
    *,
    author: str = "Carlo Collodi",
    language: str = "it",
    year: int = 1883,
    rights_status: RightsStatus = RightsStatus.ANALYSIS_ONLY,
) -> GuidedWorkInput:
    unit = project_text_receipts((receipt,))[0]
    return GuidedWorkInput(
        unit=unit,
        title_original=suggested_title(receipt.display_label),
        primary_author_name=author,
        language=language,
        first_publication=DateValue(mode=DateMode.EXACT, start_year=year),
        genre="children_fiction",
        audience="children",
        adaptation="original",
        collection="independent_work",
        edition_label="Liber Liber digital edition",
        edition_date=DateValue(mode=DateMode.UNKNOWN),
        source_type="digital_library",
        source_title="Liber Liber",
        source_url="https://www.liberliber.it/",
        accessed_on=date(2026, 7, 12),
        rights_status=rights_status,
    )


def test_text_receipt_projection_is_payload_free_and_order_invariant() -> None:
    first = _receipt("b.txt", "2" * 64, "1" * 32)
    second = _receipt("a.txt", "1" * 64, "2" * 32)
    units = project_text_receipts((first, second))
    reordered = project_text_receipts((second, first))
    assert [unit.validated_file.file_label for unit in units] == ["a.txt", "b.txt"]
    assert units == reordered
    assert corpus_catalog_sha256(units) == corpus_catalog_sha256(reordered)
    rendered = repr(units)
    assert first.asset_id not in rendered
    assert first.storage_name not in rendered


def test_archive_member_projection_matches_individual_text_catalog_semantics() -> None:
    members = (
        ArchiveMemberReceipt(
            display_label="folder/b.txt",
            byte_size=8,
            sha256="2" * 64,
            line_count=2,
            token_count=3,
            limit_profile="ingestion-limits-v1",
        ),
        ArchiveMemberReceipt(
            display_label="a.txt",
            byte_size=7,
            sha256="1" * 64,
            line_count=1,
            token_count=2,
            limit_profile="ingestion-limits-v1",
        ),
    )
    archive = IntakeReceipt(
        asset_id=f"asset_{'9' * 32}",
        role=IntakeRole.CORPUS_ARCHIVE,
        display_label="corpus.zip",
        storage_name=f"asset_{'9' * 32}.zip",
        byte_size=200,
        expanded_bytes=15,
        sha256="f" * 64,
        member_count=2,
        archive_members=members,
        limit_profile="ingestion-limits-v1",
    )
    reversed_archive = IntakeReceipt.model_validate(
        {**archive.model_dump(mode="json"), "archive_members": list(reversed(members))}
    )

    units = project_corpus_receipts((archive,))
    reordered = project_corpus_receipts((reversed_archive,))
    assert [unit.validated_file.file_label for unit in units] == ["a.txt", "folder/b.txt"]
    assert units == reordered
    assert corpus_catalog_sha256(units) == corpus_catalog_sha256(reordered)
    assert project_text_receipts((archive,)) == ()
    rendered = repr(units)
    assert archive.asset_id not in rendered
    assert archive.storage_name not in rendered
    assert archive.sha256 not in rendered
    template = metadata_csv_template(
        tuple(unit.validated_file for unit in units),
        PurposeId.TEXT_PROXIMITY,
    )
    assert b"folder/b.txt" in template


def test_guided_build_uses_existing_models_and_returns_actionable_readiness() -> None:
    receipt = _receipt("pinocchio.txt", "a" * 64, "3" * 32)
    build = build_guided_inventory(
        PurposeId.TEXT_PROXIMITY,
        (_guided_input(receipt),),
        assessed_by="Test researcher",
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    assert build.validation_report.inventory_sha256 == build.inventory_sha256
    assert build.validation_report.blocked is False
    assert build.inventory.assets[0].file_label == "pinocchio.txt"
    assert build.inventory.assets[0].content_sha256 == "a" * 64
    assert build.inventory.works[0].work_id == guided_work_id(_guided_input(receipt).unit)
    assert build.inventory.rights[0].allows_analysis is True
    assert build.inventory.rights[0].allows_public_redistribution is False


def test_unknown_rights_remain_visible_and_fail_closed() -> None:
    receipt = _receipt("unknown.txt", "b" * 64, "4" * 32)
    build = build_guided_inventory(
        PurposeId.TEXT_PROXIMITY,
        (_guided_input(receipt, rights_status=RightsStatus.UNKNOWN),),
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    codes = {issue.code for issue in build.validation_report.issues}
    assert build.validation_report.blocked is True
    assert IssueCode.UPLOAD_PERMISSION_REQUIRED in codes
    assert IssueCode.ANALYSIS_PERMISSION_REQUIRED in codes
    assert IssueCode.RIGHTS_STATUS_UNRESOLVED in codes


def test_style_over_time_blocks_mixed_authors_and_languages() -> None:
    inputs = (
        _guided_input(_receipt("one.txt", "1" * 64, "5" * 32), year=1880),
        _guided_input(
            _receipt("two.txt", "2" * 64, "6" * 32),
            author="Emilio Salgari",
            language="en",
            year=1890,
        ),
    )
    build = build_guided_inventory(
        PurposeId.STYLE_OVER_TIME,
        inputs,
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    codes = {issue.code for issue in build.validation_report.issues}
    assert IssueCode.STYLE_AUTHOR_SET_MIXED in codes
    assert IssueCode.STYLE_LANGUAGE_MIXED in codes
    assert build.validation_report.blocked is True
    assert build.validation_report.readiness.style_over_time_minimum_met is False


def test_guided_source_requires_a_url_or_citation() -> None:
    data = _guided_input(_receipt("source.txt", "c" * 64, "7" * 32)).model_dump()
    data.update(source_url=None, accessed_on=None, bibliographic_citation=None)
    with pytest.raises(ValidationError, match="source URL or bibliographic citation"):
        GuidedWorkInput.model_validate(data)


@pytest.mark.parametrize(
    ("source_url", "accessed_on", "citation", "message"),
    [
        (
            "https://www.liberliber.it/",
            None,
            None,
            "online source requires an access date",
        ),
        (
            None,
            date(2026, 7, 12),
            "Collodi, Pinocchio, documented edition.",
            "access date requires an online source",
        ),
    ],
)
def test_guided_source_linkage_is_fail_closed(
    source_url: str | None,
    accessed_on: date | None,
    citation: str | None,
    message: str,
) -> None:
    data = _guided_input(_receipt("source.txt", "d" * 64, "8" * 32)).model_dump()
    data.update(
        source_url=source_url,
        accessed_on=accessed_on,
        bibliographic_citation=citation,
    )
    with pytest.raises(ValidationError, match=message):
        GuidedWorkInput.model_validate(data)


def test_guided_build_rejects_a_report_bound_to_different_inventory() -> None:
    build = build_guided_inventory(
        PurposeId.TEXT_PROXIMITY,
        (_guided_input(_receipt("bound.txt", "e" * 64, "9" * 32)),),
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    changed_work = build.inventory.works[0].model_copy(update={"title_original": "Changed"})
    changed_inventory = build.inventory.model_copy(update={"works": (changed_work,)})
    with pytest.raises(ValidationError, match="does not match the inventory"):
        GuidedInventoryBuild(
            inventory=changed_inventory,
            validation_report=build.validation_report,
        )


def test_controlled_term_kinds_and_invalid_values_are_explicit() -> None:
    guided = _guided_input(_receipt("terms.txt", "f" * 64, "a" * 32))
    not_applicable = guided.model_copy(update={"genre": "not_applicable"})
    build = build_guided_inventory(
        PurposeId.TEXT_PROXIMITY,
        (not_applicable,),
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    assert build.inventory.works[0].genre.kind.value == "not_applicable"

    unsupported = guided.model_copy(update={"genre": "invented_category"})
    with pytest.raises(ValueError, match="unsupported controlled value"):
        build_guided_inventory(PurposeId.TEXT_PROXIMITY, (unsupported,))


@pytest.mark.parametrize(
    ("status", "license_name", "jurisdiction", "expected_permissions"),
    [
        (
            RightsStatus.VERIFIED_OPEN,
            "Public Domain Mark 1.0",
            "Italy",
            ("permitted", "permitted", "permitted", "permitted"),
        ),
        (
            RightsStatus.EXCLUDED,
            None,
            None,
            ("prohibited", "prohibited", "prohibited", "prohibited"),
        ),
    ],
)
def test_guided_rights_profiles_are_deterministic(
    status: RightsStatus,
    license_name: str | None,
    jurisdiction: str | None,
    expected_permissions: tuple[str, str, str, str],
) -> None:
    guided = _guided_input(_receipt("rights.txt", "1" * 64, "b" * 32)).model_copy(
        update={
            "rights_status": status,
            "rights_license": license_name,
            "rights_jurisdiction": jurisdiction,
        }
    )
    build = build_guided_inventory(
        PurposeId.TEXT_PROXIMITY,
        (guided,),
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    permissions = build.inventory.rights[0].permissions
    assert tuple(permissions.model_dump(mode="json").values()) == expected_permissions


def test_guided_citation_is_retained_as_rights_evidence() -> None:
    guided = _guided_input(_receipt("citation.txt", "2" * 64, "c" * 32)).model_copy(
        update={
            "source_url": None,
            "accessed_on": None,
            "bibliographic_citation": "Collodi, Pinocchio, documented edition.",
        }
    )
    build = build_guided_inventory(
        PurposeId.TEXT_PROXIMITY,
        (guided,),
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    assert build.inventory.rights[0].evidence[0].evidence_type == "citation"


def test_guided_build_requires_at_least_one_work() -> None:
    with pytest.raises(ValueError, match="at least one documented work"):
        build_guided_inventory(PurposeId.TEXT_PROXIMITY, ())


def test_title_suggestion_is_editable_and_unicode_safe() -> None:
    assert suggested_title("01-le_avventure-di_pinocchio.txt") == ("01 Le Avventure Di Pinocchio")
