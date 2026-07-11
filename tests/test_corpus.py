from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from delta_lemmata.corpus import (
    DEFAULT_VOCABULARY,
    ActionPermissions,
    AssetRecord,
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
    EditionRecord,
    IssueCode,
    PermissionState,
    PurposeId,
    RightsEvidence,
    RightsStatus,
    SourceRecord,
    TermKind,
    ValidatedFileRecord,
    VocabularyProfile,
    VocabularyTerm,
    WorkRecord,
    asset_allows_public_redistribution,
    bind_inventory,
    canonical_inventory_payload,
    export_json_schema,
    inventory_sha256,
    validate_inventory,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "p004"


def _term(value: str, *, kind: TermKind = TermKind.CONTROLLED) -> VocabularyTerm:
    return VocabularyTerm(value=value, label=value.replace("_", " ").title(), kind=kind)


def _analysis_only_rights(
    asset_id: str,
    source_id: str,
    *,
    asset_type: AssetType = AssetType.TRANSCRIPTION,
) -> AssetRightsRecord:
    return AssetRightsRecord(
        asset_id=asset_id,
        source_id=source_id,
        asset_type=asset_type,
        rights_status=RightsStatus.ANALYSIS_ONLY,
        permissions=ActionPermissions(
            upload=PermissionState.PERMITTED,
            analysis=PermissionState.PERMITTED,
            export=PermissionState.PROHIBITED,
            public_redistribution=PermissionState.PROHIBITED,
        ),
        evidence=(RightsEvidence(evidence_type="citation", value="Synthetic fixture"),),
        assessed_by="Test suite",
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )


def _inventory(
    *,
    count: int = 6,
    purpose: PurposeId = PurposeId.STYLE_OVER_TIME,
    years: list[int] | None = None,
) -> CorpusInventory:
    chronology = years or [1876 + (index * 2) for index in range(count)]
    author = AuthorRecord(
        author_id="carlo_collodi",
        display_name="Carlo Collodi",
        kind=AuthorKind.PERSON,
    )
    works: list[WorkRecord] = []
    editions: list[EditionRecord] = []
    sources: list[SourceRecord] = []
    assets: list[AssetRecord] = []
    validated_files: list[ValidatedFileRecord] = []
    rights: list[AssetRightsRecord] = []
    for index, year in enumerate(chronology, start=1):
        work_id = f"work_{index:02d}"
        edition_id = f"edition_{index:02d}"
        source_id = f"source_{index:02d}"
        asset_id = f"asset_work_{index:02d}"
        works.append(
            WorkRecord(
                work_id=work_id,
                title_original=f"Opera {index}",
                language="it",
                contributors=(
                    ContributorRecord(
                        author_id=author.author_id,
                        role=ContributorRole.AUTHOR,
                    ),
                ),
                first_publication=DateValue(mode=DateMode.EXACT, start_year=year),
                genre=_term("novel"),
                audience=_term("general"),
                adaptation=_term("original"),
                collection=_term("independent_work"),
                group_label="career",
            )
        )
        editions.append(
            EditionRecord(
                edition_id=edition_id,
                work_id=work_id,
                edition_label=f"Test edition {index}",
                edition_date=DateValue(mode=DateMode.EXACT, start_year=year + 1),
                citation=f"Fixture citation {index}",
            )
        )
        sources.append(
            SourceRecord(
                source_id=source_id,
                edition_id=edition_id,
                source_type=_term("digital_library"),
                title=f"Fixture source {index}",
                bibliographic_citation=f"Fixture citation {index}",
            )
        )
        assets.append(
            AssetRecord(
                asset_id=asset_id,
                file_label=f"work_{index:02d}.txt",
                content_sha256=f"{index:064x}",
                work_id=work_id,
                edition_id=edition_id,
                source_id=source_id,
                rights_asset_ids=(asset_id,),
                rights_chain_confirmed=True,
                normalization_profile="nfc_validated_v1",
                mapping_confirmed=True,
                line_count=100,
                token_count=1000,
            )
        )
        validated_files.append(
            ValidatedFileRecord(
                file_label=f"work_{index:02d}.txt",
                content_sha256=f"{index:064x}",
                intake_profile="ingestion-limits-v1",
            )
        )
        rights.append(_analysis_only_rights(asset_id, source_id))
    return CorpusInventory(
        purpose=purpose,
        authors=(author,),
        works=tuple(works),
        editions=tuple(editions),
        sources=tuple(sources),
        assets=tuple(assets),
        validated_files=tuple(validated_files),
        rights=tuple(rights),
    )


def _codes(inventory: CorpusInventory) -> set[IssueCode]:
    return {issue.code for issue in validate_inventory(inventory).issues}


def test_versioned_inventory_fixtures_cover_valid_and_invalid_cross_record_states() -> None:
    valid = CorpusInventory.model_validate_json(
        (FIXTURES / "inventory-valid-text-proximity.json").read_text(encoding="utf-8")
    )
    invalid = CorpusInventory.model_validate_json(
        (FIXTURES / "inventory-invalid-cross-record.json").read_text(encoding="utf-8")
    )
    assert validate_inventory(valid).blocked is False
    report = validate_inventory(invalid)
    assert report.blocked is True
    assert {
        IssueCode.GROUP_LABEL_REQUIRED,
        IssueCode.WORK_REFERENCE_MISSING,
        IssueCode.RELATIONSHIP_CONFLICT,
        IssueCode.FILE_MAPPING_UNCONFIRMED,
        IssueCode.NORMALIZATION_PROFILE_UNKNOWN,
        IssueCode.UPLOAD_PERMISSION_REQUIRED,
        IssueCode.ANALYSIS_PERMISSION_REQUIRED,
        IssueCode.RIGHTS_SOURCE_CONFLICT,
    } <= {issue.code for issue in report.issues}


def test_default_vocabulary_is_versioned_sorted_and_includes_other() -> None:
    assert DEFAULT_VOCABULARY.profile_version == "corpus-vocabularies-v1"
    assert "other" in DEFAULT_VOCABULARY.genres
    assert "other" in DEFAULT_VOCABULARY.audiences
    assert DEFAULT_VOCABULARY.genres == tuple(sorted(DEFAULT_VOCABULARY.genres))


def test_vocabulary_rejects_unsorted_or_repeated_values() -> None:
    payload = DEFAULT_VOCABULARY.model_dump(mode="python")
    payload["genres"] = ("novel", "essay", "novel")
    with pytest.raises(ValidationError, match="sorted and unique"):
        VocabularyProfile.model_validate(payload)


@pytest.mark.parametrize(
    ("date_value", "bounds"),
    [
        (DateValue(mode=DateMode.EXACT, start_year=1883), (1883, 1883)),
        (DateValue(mode=DateMode.APPROXIMATE, start_year=1883), (1883, 1883)),
        (DateValue(mode=DateMode.RANGE, start_year=1881, end_year=1883), (1881, 1883)),
        (DateValue(mode=DateMode.UNKNOWN), None),
    ],
)
def test_date_modes_preserve_supported_uncertainty(
    date_value: DateValue,
    bounds: tuple[int, int] | None,
) -> None:
    assert date_value.bounds == bounds
    assert date_value.chronology_key == bounds


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "unknown", "start_year": 1883},
        {"mode": "range", "start_year": 1883},
        {"mode": "exact"},
        {"mode": "approximate", "start_year": 1883, "end_year": 1883},
    ],
)
def test_date_modes_reject_false_or_contradictory_precision(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        DateValue.model_validate(payload)


def test_certainty_does_not_create_a_second_chronology_point() -> None:
    exact = DateValue(mode=DateMode.EXACT, start_year=1883)
    approximate = DateValue(mode=DateMode.APPROXIMATE, start_year=1883)
    assert exact.chronology_key == approximate.chronology_key


@pytest.mark.parametrize(
    "term",
    [
        _term("novel"),
        _term("custom_genre", kind=TermKind.CUSTOM),
        _term("unknown", kind=TermKind.UNKNOWN),
        _term("not_applicable", kind=TermKind.NOT_APPLICABLE),
    ],
)
def test_vocabulary_terms_preserve_controlled_custom_and_reserved_states(
    term: VocabularyTerm,
) -> None:
    assert term.label


@pytest.mark.parametrize(
    "payload",
    [
        {"value": "novel", "label": "Novel", "kind": "unknown"},
        {"value": "novel", "label": "Novel", "kind": "not_applicable"},
        {"value": "unknown", "label": "Unknown", "kind": "controlled"},
        {"value": "not_applicable", "label": "N/A", "kind": "custom"},
    ],
)
def test_vocabulary_terms_reject_implicit_reserved_meanings(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        VocabularyTerm.model_validate(payload)


def test_source_accepts_citation_or_dated_url() -> None:
    citation = SourceRecord(
        source_id="source_print",
        edition_id="edition_print",
        source_type=_term("print_edition"),
        title="Print source",
        bibliographic_citation="Publisher, 1883",
    )
    online = SourceRecord(
        source_id="source_web",
        edition_id="edition_web",
        source_type=_term("digital_library"),
        title="Digital source",
        source_url="https://example.org/text",
        accessed_on=date(2026, 7, 12),
    )
    assert citation.source_url is None
    assert str(online.source_url) == "https://example.org/text"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"source_url": "https://example.org/text"},
        {"bibliographic_citation": "Print citation", "accessed_on": "2026-07-12"},
        {"source_url": "file:///tmp/text.txt", "accessed_on": "2026-07-12"},
    ],
)
def test_source_rejects_missing_or_incoherent_evidence(payload: dict[str, str]) -> None:
    common: dict[str, Any] = {
        "source_id": "source_test",
        "edition_id": "edition_test",
        "source_type": _term("digital_library"),
        "title": "Test source",
    }
    with pytest.raises(ValidationError):
        SourceRecord.model_validate({**common, **payload})


def test_models_are_closed_and_schema_export_is_draft_2020_12() -> None:
    payload = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY).works[0].model_dump()
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        WorkRecord.model_validate(payload)
    schema = export_json_schema(
        WorkRecord,
        "https://delta.lemmata.app/schemas/work-record.schema.json",
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("work-record.schema.json")


def test_asset_rejects_duplicate_rights_dependencies() -> None:
    asset = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY).assets[0]
    payload = asset.model_dump(mode="python")
    payload["rights_asset_ids"] = (asset.asset_id, asset.asset_id)
    with pytest.raises(ValidationError, match="must be unique"):
        AssetRecord.model_validate(payload)


def test_analysis_only_rights_are_coherent_and_fail_closed_for_export() -> None:
    rights = _analysis_only_rights("asset_fixture", "source_fixture")
    assert rights.allows_analysis is True
    assert rights.allows_public_redistribution is False


def test_verified_open_rights_can_allow_raw_public_export() -> None:
    permissions = ActionPermissions(
        upload=PermissionState.PERMITTED,
        analysis=PermissionState.PERMITTED,
        export=PermissionState.PERMITTED,
        public_redistribution=PermissionState.PERMITTED,
    )
    rights = AssetRightsRecord(
        asset_id="asset_open",
        source_id="source_open",
        asset_type=AssetType.TRANSCRIPTION,
        rights_status=RightsStatus.VERIFIED_OPEN,
        license="CC0-1.0",
        permissions=permissions,
        evidence=(RightsEvidence(evidence_type="url", value="https://example.org/rights"),),
        assessed_by="Test suite",
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    assert rights.allows_analysis is True
    assert rights.allows_public_redistribution is True


def test_url_rights_evidence_accepts_only_http_or_https() -> None:
    assert RightsEvidence(evidence_type="url", value="https://example.org/rights").value
    for invalid in ("file:///tmp/rights.txt", "https://"):
        with pytest.raises(ValidationError):
            RightsEvidence(evidence_type="url", value=invalid)


def test_unknown_rights_close_analysis_and_public_export() -> None:
    rights = AssetRightsRecord(
        asset_id="asset_unknown",
        source_id="source_unknown",
        asset_type=AssetType.TRANSCRIPTION,
        rights_status=RightsStatus.UNKNOWN,
        permissions=ActionPermissions(
            upload=PermissionState.UNKNOWN,
            analysis=PermissionState.UNKNOWN,
            export=PermissionState.UNKNOWN,
            public_redistribution=PermissionState.UNKNOWN,
        ),
        assessed_by="Test suite",
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    assert rights.allows_analysis is False
    assert rights.allows_public_redistribution is False


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "assessed_at_utc": datetime(2026, 7, 12),
                "permissions": ActionPermissions(
                    upload=PermissionState.UNKNOWN,
                    analysis=PermissionState.UNKNOWN,
                    export=PermissionState.UNKNOWN,
                    public_redistribution=PermissionState.UNKNOWN,
                ),
            },
            "must be UTC",
        ),
        (
            {
                "permissions": ActionPermissions(
                    upload=PermissionState.PERMITTED,
                    analysis=PermissionState.UNKNOWN,
                    export=PermissionState.UNKNOWN,
                    public_redistribution=PermissionState.UNKNOWN,
                )
            },
            "require rights evidence",
        ),
        (
            {
                "permissions": ActionPermissions(
                    upload=PermissionState.UNKNOWN,
                    analysis=PermissionState.UNKNOWN,
                    export=PermissionState.PROHIBITED,
                    public_redistribution=PermissionState.PERMITTED,
                ),
                "evidence": (RightsEvidence(evidence_type="statement", value="Permission note"),),
            },
            "verified-open export rights",
        ),
        (
            {
                "rights_status": RightsStatus.ANALYSIS_ONLY,
                "permissions": ActionPermissions(
                    upload=PermissionState.PERMITTED,
                    analysis=PermissionState.PERMITTED,
                    export=PermissionState.UNKNOWN,
                    public_redistribution=PermissionState.PROHIBITED,
                ),
                "evidence": (RightsEvidence(evidence_type="statement", value="Permission note"),),
            },
            "analysis-only profile",
        ),
        (
            {
                "rights_status": RightsStatus.EXCLUDED,
                "permissions": ActionPermissions(
                    upload=PermissionState.PROHIBITED,
                    analysis=PermissionState.PROHIBITED,
                    export=PermissionState.PROHIBITED,
                    public_redistribution=PermissionState.UNKNOWN,
                ),
            },
            "prohibit every action",
        ),
        (
            {
                "rights_status": RightsStatus.VERIFIED_OPEN,
                "permissions": ActionPermissions(
                    upload=PermissionState.PROHIBITED,
                    analysis=PermissionState.PROHIBITED,
                    export=PermissionState.PROHIBITED,
                    public_redistribution=PermissionState.PROHIBITED,
                ),
            },
            "require a license and evidence",
        ),
    ],
)
def test_rights_reject_incoherent_states(payload: dict[str, Any], message: str) -> None:
    common: dict[str, Any] = {
        "asset_id": "asset_invalid",
        "source_id": "source_invalid",
        "asset_type": AssetType.TRANSCRIPTION,
        "rights_status": RightsStatus.UNKNOWN,
        "permissions": ActionPermissions(
            upload=PermissionState.UNKNOWN,
            analysis=PermissionState.UNKNOWN,
            export=PermissionState.UNKNOWN,
            public_redistribution=PermissionState.UNKNOWN,
        ),
        "assessed_by": "Test suite",
        "assessed_at_utc": datetime(2026, 7, 12, tzinfo=UTC),
    }
    with pytest.raises(ValidationError, match=message):
        AssetRightsRecord.model_validate({**common, **payload})


def test_excluded_rights_accept_only_the_all_prohibited_profile() -> None:
    rights = AssetRightsRecord(
        asset_id="asset_excluded",
        source_id="source_excluded",
        asset_type=AssetType.TRANSCRIPTION,
        rights_status=RightsStatus.EXCLUDED,
        permissions=ActionPermissions(
            upload=PermissionState.PROHIBITED,
            analysis=PermissionState.PROHIBITED,
            export=PermissionState.PROHIBITED,
            public_redistribution=PermissionState.PROHIBITED,
        ),
        assessed_by="Test suite",
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    assert rights.allows_analysis is False


def test_inventory_hash_is_upload_order_invariant_and_ignores_assessment_time() -> None:
    inventory = _inventory(count=3, purpose=PurposeId.TEXT_PROXIMITY)
    reordered_rights = tuple(
        record.model_copy(update={"assessed_at_utc": record.assessed_at_utc + timedelta(days=1)})
        for record in reversed(inventory.rights)
    )
    reordered = inventory.model_copy(
        update={
            "authors": tuple(reversed(inventory.authors)),
            "works": tuple(reversed(inventory.works)),
            "editions": tuple(reversed(inventory.editions)),
            "sources": tuple(reversed(inventory.sources)),
            "assets": tuple(reversed(inventory.assets)),
            "validated_files": tuple(reversed(inventory.validated_files)),
            "rights": reordered_rights,
        }
    )
    assert inventory_sha256(inventory) == inventory_sha256(reordered)
    assert canonical_inventory_payload(inventory) == canonical_inventory_payload(reordered)
    assert "assessed_at_utc" not in canonical_inventory_payload(inventory)["rights"][0]


def test_inventory_hash_sorts_nested_set_like_records() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    identifiers = (
        AuthorityIdentifier(scheme=AuthorityScheme.WIKIDATA, value="Q123"),
        AuthorityIdentifier(scheme=AuthorityScheme.VIAF, value="24602065"),
    )
    second_author = AuthorRecord(
        author_id="test_translator",
        display_name="Test Translator",
        kind=AuthorKind.PERSON,
    )
    author = inventory.authors[0].model_copy(update={"authority_identifiers": identifiers})
    contributors = (
        inventory.works[0].contributors[0],
        ContributorRecord(author_id=second_author.author_id, role=ContributorRole.TRANSLATOR),
    )
    work = inventory.works[0].model_copy(update={"contributors": contributors})
    evidence = (
        RightsEvidence(evidence_type="statement", value="B"),
        RightsEvidence(evidence_type="citation", value="A"),
    )
    rights = inventory.rights[0].model_copy(update={"evidence": evidence})
    first = inventory.model_copy(
        update={"authors": (author, second_author), "works": (work,), "rights": (rights,)}
    )
    second = first.model_copy(
        update={
            "authors": (
                second_author,
                author.model_copy(update={"authority_identifiers": tuple(reversed(identifiers))}),
            ),
            "works": (work.model_copy(update={"contributors": tuple(reversed(contributors))}),),
            "rights": (rights.model_copy(update={"evidence": tuple(reversed(evidence))}),),
        }
    )
    assert inventory_sha256(first) == inventory_sha256(second)


def test_inventory_hash_uses_full_payload_as_a_duplicate_id_tie_breaker() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    changed_work = inventory.works[0].model_copy(update={"title_original": "Second title"})
    first = inventory.model_copy(update={"works": (inventory.works[0], changed_work)})
    second = inventory.model_copy(update={"works": (changed_work, inventory.works[0])})
    assert inventory_sha256(first) == inventory_sha256(second)


def test_inventory_hash_treats_rights_dependency_order_as_non_semantic() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    asset = inventory.assets[0].model_copy(
        update={"rights_asset_ids": ("asset_work_01", "asset_underlying_work")}
    )
    dependency = _analysis_only_rights("asset_underlying_work", "source_01")
    first = inventory.model_copy(
        update={"assets": (asset,), "rights": (*inventory.rights, dependency)}
    )
    reversed_asset = asset.model_copy(
        update={"rights_asset_ids": tuple(reversed(asset.rights_asset_ids))}
    )
    second = first.model_copy(update={"assets": (reversed_asset,)})
    assert inventory_sha256(first) == inventory_sha256(second)


def test_semantic_metadata_and_rights_changes_invalidate_inventory_binding() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    binding = bind_inventory(inventory)
    assert binding.matches(inventory) is True

    changed_work = inventory.works[0].model_copy(update={"title_original": "Changed title"})
    changed_metadata = inventory.model_copy(update={"works": (changed_work,)})
    assert inventory_sha256(changed_metadata) != inventory_sha256(inventory)
    assert binding.matches(changed_metadata) is False

    changed_rights = inventory.rights[0].model_copy(update={"notes": "Reviewed note"})
    changed_rights_inventory = inventory.model_copy(update={"rights": (changed_rights,)})
    assert inventory_sha256(changed_rights_inventory) != inventory_sha256(inventory)


def test_valid_style_over_time_inventory_meets_only_the_minimum_design_rule() -> None:
    report = validate_inventory(_inventory())
    assert report.blocked is False
    assert report.issues == ()
    assert report.readiness.independent_work_count == 6
    assert report.readiness.chronology_point_count == 6
    assert report.readiness.style_over_time_minimum_met is True
    assert report.readiness.threshold_is_sufficiency_claim is False
    assert report.readiness.exploratory is False
    assert report.readiness.rights_restriction_count == 6


def test_non_temporal_purpose_has_no_temporal_threshold_label() -> None:
    report = validate_inventory(_inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY))
    assert report.blocked is False
    assert report.readiness.style_over_time_minimum_met is None
    assert report.readiness.exploratory is False


@pytest.mark.parametrize(
    ("count", "years", "expected_codes"),
    [
        (5, [1876, 1876, 1880, 1880, 1883], {IssueCode.WORK_COUNT_EXPLORATORY}),
        (
            6,
            [1876, 1876, 1876, 1883, 1883, 1883],
            {IssueCode.CHRONOLOGY_POINTS_EXPLORATORY},
        ),
        (
            5,
            [1876, 1876, 1883, 1883, 1883],
            {IssueCode.WORK_COUNT_EXPLORATORY, IssueCode.CHRONOLOGY_POINTS_EXPLORATORY},
        ),
    ],
)
def test_small_temporal_designs_are_forced_to_exploratory_status(
    count: int,
    years: list[int],
    expected_codes: set[IssueCode],
) -> None:
    report = validate_inventory(_inventory(count=count, years=years))
    assert report.blocked is False
    assert report.readiness.style_over_time_minimum_met is False
    assert report.readiness.exploratory is True
    assert {issue.code for issue in report.issues} == expected_codes


def test_blocked_temporal_inventory_cannot_report_the_minimum_as_met() -> None:
    inventory = _inventory()
    asset = inventory.assets[0].model_copy(update={"mapping_confirmed": False})
    report = validate_inventory(
        inventory.model_copy(update={"assets": (asset, *inventory.assets[1:])})
    )
    assert report.readiness.independent_work_count == 6
    assert report.readiness.chronology_point_count == 6
    assert report.readiness.style_over_time_minimum_met is False
    assert report.readiness.exploratory is True


def test_group_comparison_requires_a_group_label() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.GROUP_COMPARISON)
    work = inventory.works[0].model_copy(update={"group_label": None})
    report = validate_inventory(inventory.model_copy(update={"works": (work,)}))
    assert report.blocked is True
    assert IssueCode.GROUP_LABEL_REQUIRED in {issue.code for issue in report.issues}
    issue = report.issues[0]
    assert issue.message and issue.why_it_matters and issue.how_to_fix


def test_style_over_time_requires_work_chronology_not_edition_chronology() -> None:
    inventory = _inventory(count=1)
    work = inventory.works[0].model_copy(
        update={"first_publication": DateValue(mode=DateMode.UNKNOWN)}
    )
    codes = _codes(inventory.model_copy(update={"works": (work,)}))
    assert IssueCode.CHRONOLOGY_REQUIRED in codes
    assert IssueCode.CHRONOLOGY_POINTS_EXPLORATORY in codes


def test_overlapping_uncertain_ranges_form_one_conservative_chronology_point() -> None:
    inventory = _inventory(count=6)
    ranges = (
        (1870, 1880),
        (1875, 1885),
        (1880, 1890),
        (1885, 1895),
        (1890, 1900),
        (1895, 1905),
    )
    works = tuple(
        work.model_copy(
            update={
                "first_publication": DateValue(
                    mode=DateMode.RANGE,
                    start_year=start,
                    end_year=end,
                )
            }
        )
        for work, (start, end) in zip(inventory.works, ranges, strict=True)
    )
    report = validate_inventory(inventory.model_copy(update={"works": works}))
    assert report.readiness.chronology_point_count == 1
    assert report.readiness.style_over_time_minimum_met is False
    assert IssueCode.CHRONOLOGY_POINTS_EXPLORATORY in {issue.code for issue in report.issues}


def test_duplicate_identifiers_and_labels_are_all_reported() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    duplicated = inventory.model_copy(
        update={
            "authors": inventory.authors * 2,
            "works": inventory.works * 2,
            "editions": inventory.editions * 2,
            "sources": inventory.sources * 2,
            "assets": inventory.assets * 2,
            "rights": inventory.rights * 2,
        }
    )
    expected = {
        IssueCode.DUPLICATE_AUTHOR_ID,
        IssueCode.DUPLICATE_WORK_ID,
        IssueCode.DUPLICATE_EDITION_ID,
        IssueCode.DUPLICATE_SOURCE_ID,
        IssueCode.DUPLICATE_ASSET_ID,
        IssueCode.DUPLICATE_RIGHTS_ASSET_ID,
        IssueCode.DUPLICATE_FILE_LABEL,
    }
    assert expected <= _codes(duplicated)


def test_work_contributors_and_controlled_terms_are_validated() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    work = inventory.works[0].model_copy(
        update={
            "contributors": (
                ContributorRecord(author_id="missing_author", role=ContributorRole.EDITOR),
            ),
            "genre": _term("not_in_vocabulary"),
            "audience": _term("unknown", kind=TermKind.UNKNOWN),
            "adaptation": _term("unknown", kind=TermKind.UNKNOWN),
            "collection": _term("unknown", kind=TermKind.UNKNOWN),
        }
    )
    codes = _codes(inventory.model_copy(update={"works": (work,)}))
    assert IssueCode.AUTHOR_ROLE_REQUIRED in codes
    assert IssueCode.AUTHOR_REFERENCE_MISSING in codes
    assert IssueCode.CONTROLLED_TERM_UNKNOWN in codes
    assert IssueCode.CONFOUND_METADATA_UNKNOWN in codes


@pytest.mark.parametrize(
    ("edition", "expected"),
    [
        (
            EditionRecord(
                edition_id="edition_01",
                work_id="missing_work",
                edition_label="Missing relation",
                edition_date=DateValue(mode=DateMode.EXACT, start_year=1884),
            ),
            IssueCode.WORK_REFERENCE_MISSING,
        ),
        (
            EditionRecord(
                edition_id="edition_01",
                work_id="work_01",
                edition_label="Unknown date",
                edition_date=DateValue(mode=DateMode.UNKNOWN),
            ),
            IssueCode.EDITION_DATE_UNKNOWN,
        ),
        (
            EditionRecord(
                edition_id="edition_01",
                work_id="work_01",
                edition_label="Impossible date",
                edition_date=DateValue(mode=DateMode.EXACT, start_year=1800),
            ),
            IssueCode.EDITION_PRECEDES_PUBLICATION,
        ),
        (
            EditionRecord(
                edition_id="edition_01",
                work_id="work_01",
                edition_label="Overlapping date",
                edition_date=DateValue(mode=DateMode.RANGE, start_year=1870, end_year=1880),
            ),
            IssueCode.DATE_ORDER_UNCERTAIN,
        ),
        (
            EditionRecord(
                edition_id="edition_01",
                work_id="work_01",
                edition_label="Explicit earlier range",
                edition_date=DateValue(mode=DateMode.RANGE, start_year=1800, end_year=1810),
            ),
            IssueCode.EDITION_PRECEDES_PUBLICATION,
        ),
    ],
)
def test_edition_chronology_and_relationships_are_checked(
    edition: EditionRecord,
    expected: IssueCode,
) -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    assert expected in _codes(inventory.model_copy(update={"editions": (edition,)}))


def test_unknown_work_date_does_not_create_false_edition_order() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    work = inventory.works[0].model_copy(
        update={"first_publication": DateValue(mode=DateMode.UNKNOWN)}
    )
    report = validate_inventory(inventory.model_copy(update={"works": (work,)}))
    assert IssueCode.EDITION_PRECEDES_PUBLICATION not in {issue.code for issue in report.issues}


def test_reversed_ranges_are_semantic_blockers_and_are_never_silently_swapped() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    reversed_range = DateValue(mode=DateMode.RANGE, start_year=1884, end_year=1883)
    assert reversed_range.is_reversed is True

    work = inventory.works[0].model_copy(update={"first_publication": reversed_range})
    report = validate_inventory(inventory.model_copy(update={"works": (work,)}))
    assert IssueCode.DATE_RANGE_REVERSED in {issue.code for issue in report.issues}
    assert report.readiness.chronology_point_count == 0

    edition = inventory.editions[0].model_copy(update={"edition_date": reversed_range})
    report = validate_inventory(inventory.model_copy(update={"editions": (edition,)}))
    assert IssueCode.DATE_RANGE_REVERSED in {issue.code for issue in report.issues}


def test_approximate_date_does_not_create_a_false_chronology_blocker() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    work = inventory.works[0].model_copy(
        update={"first_publication": DateValue(mode=DateMode.APPROXIMATE, start_year=1883)}
    )
    edition = inventory.editions[0].model_copy(
        update={"edition_date": DateValue(mode=DateMode.EXACT, start_year=1882)}
    )
    report = validate_inventory(
        inventory.model_copy(update={"works": (work,), "editions": (edition,)})
    )
    codes = {issue.code for issue in report.issues}
    assert IssueCode.DATE_ORDER_UNCERTAIN in codes
    assert IssueCode.EDITION_PRECEDES_PUBLICATION not in codes


def test_source_relationship_and_source_type_are_checked() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    source = inventory.sources[0].model_copy(
        update={"edition_id": "missing_edition", "source_type": _term("invalid_source")}
    )
    codes = _codes(inventory.model_copy(update={"sources": (source,)}))
    assert IssueCode.EDITION_REFERENCE_MISSING in codes
    assert IssueCode.CONTROLLED_TERM_UNKNOWN in codes

    unknown = source.model_copy(
        update={"edition_id": "edition_01", "source_type": _term("unknown", kind=TermKind.UNKNOWN)}
    )
    assert IssueCode.CONFOUND_METADATA_UNKNOWN in _codes(
        inventory.model_copy(update={"sources": (unknown,)})
    )


def test_missing_asset_relationships_mapping_rights_and_normalization_are_blockers() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    asset = inventory.assets[0].model_copy(
        update={
            "work_id": "missing_work",
            "edition_id": "missing_edition",
            "source_id": "missing_source",
            "mapping_confirmed": False,
            "normalization_profile": "unknown",
        }
    )
    orphan = _analysis_only_rights("asset_orphan", "source_01")
    codes = _codes(inventory.model_copy(update={"assets": (asset,), "rights": (orphan,)}))
    assert {
        IssueCode.FILE_MAPPING_UNCONFIRMED,
        IssueCode.WORK_REFERENCE_MISSING,
        IssueCode.EDITION_REFERENCE_MISSING,
        IssueCode.SOURCE_REFERENCE_MISSING,
        IssueCode.RIGHTS_REFERENCE_MISSING,
        IssueCode.NORMALIZATION_PROFILE_UNKNOWN,
        IssueCode.WORK_ASSET_MISSING,
        IssueCode.ASSET_REFERENCE_MISSING,
    } <= codes


def test_asset_must_match_the_p003_catalog_by_exact_label_and_hash() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)

    wrong_hash = inventory.assets[0].model_copy(update={"content_sha256": "f" * 64})
    assert IssueCode.FILE_HASH_MISMATCH in _codes(
        inventory.model_copy(update={"assets": (wrong_hash,)})
    )

    wrong_label = inventory.assets[0].model_copy(update={"file_label": "other.txt"})
    label_codes = _codes(inventory.model_copy(update={"assets": (wrong_label,)}))
    assert IssueCode.FILE_REFERENCE_MISSING in label_codes
    assert IssueCode.UNMAPPED_VALIDATED_FILE in label_codes

    extra_file = ValidatedFileRecord(
        file_label="unmapped.txt",
        content_sha256="e" * 64,
        intake_profile="ingestion-limits-v1",
    )
    assert IssueCode.UNMAPPED_VALIDATED_FILE in _codes(
        inventory.model_copy(update={"validated_files": (*inventory.validated_files, extra_file)})
    )

    duplicate_catalog = inventory.model_copy(
        update={"validated_files": inventory.validated_files * 2}
    )
    assert IssueCode.DUPLICATE_VALIDATED_FILE in _codes(duplicate_catalog)

    stable_projection = inventory.validated_files[0].model_dump(mode="python")
    stable_projection["asset_id"] = "asset_transient_p003_id"
    with pytest.raises(ValidationError):
        ValidatedFileRecord.model_validate(stable_projection)


def test_duplicate_file_catalog_validation_is_order_invariant() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    correct = inventory.validated_files[0]
    wrong = correct.model_copy(update={"content_sha256": "f" * 64})
    first = inventory.model_copy(update={"validated_files": (correct, wrong)})
    second = inventory.model_copy(update={"validated_files": (wrong, correct)})
    assert inventory_sha256(first) == inventory_sha256(second)
    assert validate_inventory(first) == validate_inventory(second)
    assert {issue.code for issue in validate_inventory(first).issues} == {
        IssueCode.DUPLICATE_VALIDATED_FILE
    }


def test_asset_relationship_conflicts_are_not_silently_repaired() -> None:
    inventory = _inventory(count=2, purpose=PurposeId.TEXT_PROXIMITY)
    asset = inventory.assets[0].model_copy(
        update={"edition_id": "edition_02", "source_id": "source_01"}
    )
    rights = inventory.rights[0]
    changed = inventory.model_copy(
        update={"assets": (asset, inventory.assets[1]), "rights": (rights, inventory.rights[1])}
    )
    assert IssueCode.RELATIONSHIP_CONFLICT in _codes(changed)


def test_rights_source_permissions_and_unresolved_status_are_reported() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    rights = AssetRightsRecord(
        asset_id="asset_work_01",
        source_id="different_source",
        asset_type=AssetType.TRANSCRIPTION,
        rights_status=RightsStatus.PERMISSION_REQUIRED,
        permissions=ActionPermissions(
            upload=PermissionState.UNKNOWN,
            analysis=PermissionState.PROHIBITED,
            export=PermissionState.PROHIBITED,
            public_redistribution=PermissionState.UNKNOWN,
        ),
        assessed_by="Test suite",
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    codes = _codes(inventory.model_copy(update={"rights": (rights,)}))
    assert {
        IssueCode.RIGHTS_SOURCE_CONFLICT,
        IssueCode.UPLOAD_PERMISSION_REQUIRED,
        IssueCode.ANALYSIS_PERMISSION_REQUIRED,
        IssueCode.RIGHTS_STATUS_UNRESOLVED,
    } <= codes


def _verified_open_rights(
    asset_id: str,
    source_id: str,
    *,
    asset_type: AssetType = AssetType.TRANSCRIPTION,
) -> AssetRightsRecord:
    return AssetRightsRecord(
        asset_id=asset_id,
        source_id=source_id,
        asset_type=asset_type,
        rights_status=RightsStatus.VERIFIED_OPEN,
        license="CC0-1.0",
        permissions=ActionPermissions(
            upload=PermissionState.PERMITTED,
            analysis=PermissionState.PERMITTED,
            export=PermissionState.PERMITTED,
            public_redistribution=PermissionState.PERMITTED,
        ),
        evidence=(RightsEvidence(evidence_type="statement", value="Open fixture"),),
        assessed_by="Test suite",
        assessed_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )


def test_public_redistribution_requires_every_declared_rights_layer() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    asset = inventory.assets[0].model_copy(
        update={"rights_asset_ids": ("asset_work_01", "asset_underlying_work")}
    )
    analyzed_rights = _verified_open_rights("asset_work_01", "source_01")
    underlying_closed = _analysis_only_rights(
        "asset_underlying_work",
        "source_01",
        asset_type=AssetType.UNDERLYING_WORK,
    )
    restricted = inventory.model_copy(
        update={
            "assets": (asset,),
            "rights": (analyzed_rights, underlying_closed),
        }
    )
    assert asset_allows_public_redistribution(asset, restricted.rights) is False
    assert validate_inventory(restricted).readiness.rights_restriction_count == 1

    underlying_open = _verified_open_rights(
        "asset_underlying_work",
        "source_01",
        asset_type=AssetType.UNDERLYING_WORK,
    )
    open_inventory = restricted.model_copy(update={"rights": (analyzed_rights, underlying_open)})
    assert asset_allows_public_redistribution(asset, open_inventory.rights) is True
    assert (
        asset_allows_public_redistribution(
            asset,
            (*open_inventory.rights, analyzed_rights),
        )
        is False
    )
    assert validate_inventory(open_inventory).readiness.rights_restriction_count == 0


def test_missing_or_malformed_rights_dependency_fails_closed() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    unconfirmed = inventory.assets[0].model_copy(update={"rights_chain_confirmed": False})
    report = validate_inventory(inventory.model_copy(update={"assets": (unconfirmed,)}))
    assert IssueCode.RIGHTS_CHAIN_UNCONFIRMED in {issue.code for issue in report.issues}
    assert asset_allows_public_redistribution(unconfirmed, inventory.rights) is False

    missing_dependency_asset = inventory.assets[0].model_copy(
        update={"rights_asset_ids": ("asset_work_01", "asset_missing_layer")}
    )
    report = validate_inventory(
        inventory.model_copy(update={"assets": (missing_dependency_asset,)})
    )
    assert IssueCode.RIGHTS_DEPENDENCY_MISSING in {issue.code for issue in report.issues}
    assert report.readiness.rights_restriction_count == 1

    no_self = inventory.assets[0].model_copy(
        update={"rights_asset_ids": ("asset_underlying_work",)}
    )
    dependency = _analysis_only_rights("asset_underlying_work", "missing_source")
    report = validate_inventory(
        inventory.model_copy(update={"assets": (no_self,), "rights": (dependency,)})
    )
    codes = {issue.code for issue in report.issues}
    assert IssueCode.RIGHTS_CHAIN_SELF_MISSING in codes
    assert IssueCode.RIGHTS_SOURCE_REFERENCE_MISSING in codes
    assert asset_allows_public_redistribution(no_self, (dependency,)) is False


def test_unknown_rights_status_is_also_visible_when_actions_are_permitted() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    rights = inventory.rights[0].model_copy(update={"rights_status": RightsStatus.UNKNOWN})
    assert IssueCode.RIGHTS_STATUS_UNRESOLVED in _codes(
        inventory.model_copy(update={"rights": (rights,)})
    )


def test_custom_normalization_requires_reproducible_details() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    asset = inventory.assets[0].model_copy(
        update={"normalization_profile": "custom", "normalization_notes": None}
    )
    assert IssueCode.NORMALIZATION_DETAILS_REQUIRED in _codes(
        inventory.model_copy(update={"assets": (asset,)})
    )
    documented = asset.model_copy(update={"normalization_notes": "NFC, headers removed."})
    assert IssueCode.NORMALIZATION_DETAILS_REQUIRED not in _codes(
        inventory.model_copy(update={"assets": (documented,)})
    )


def test_one_analyzed_text_per_independent_work_is_enforced() -> None:
    inventory = _inventory(count=2, purpose=PurposeId.TEXT_PROXIMITY)
    missing = inventory.model_copy(
        update={"assets": (inventory.assets[0],), "rights": (inventory.rights[0],)}
    )
    assert IssueCode.WORK_ASSET_MISSING in _codes(missing)

    second_asset = inventory.assets[1].model_copy(
        update={
            "asset_id": "asset_second_copy",
            "file_label": "second_copy.txt",
            "work_id": "work_01",
            "edition_id": "edition_01",
            "source_id": "source_01",
        }
    )
    second_rights = _analysis_only_rights("asset_second_copy", "source_01")
    multiple = inventory.model_copy(
        update={
            "assets": (inventory.assets[0], second_asset),
            "rights": (inventory.rights[0], second_rights),
        }
    )
    assert IssueCode.MULTIPLE_ASSETS_PER_WORK in _codes(multiple)


def test_missing_rights_counts_as_one_restricted_asset_not_one_orphan_record() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.TEXT_PROXIMITY)
    orphan = _analysis_only_rights("asset_orphan", "source_01")
    report = validate_inventory(inventory.model_copy(update={"rights": (orphan,)}))
    assert report.readiness.rights_restriction_count == 1


def test_validation_issues_have_stable_order_and_optional_csv_row_location() -> None:
    inventory = _inventory(count=1, purpose=PurposeId.GROUP_COMPARISON)
    work = inventory.works[0].model_copy(update={"group_label": None})
    asset = inventory.assets[0].model_copy(update={"mapping_confirmed": False})
    report = validate_inventory(inventory.model_copy(update={"works": (work,), "assets": (asset,)}))
    keys = [
        (issue.severity.value, issue.code.value, issue.entity_type, issue.entity_id or "")
        for issue in report.issues
    ]
    assert keys == sorted(keys)
    located = report.issues[0].model_copy(update={"row_number": 2})
    assert located.row_number == 2
