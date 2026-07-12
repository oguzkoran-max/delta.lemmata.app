from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import ValidationError

from delta_lemmata.corpus import (
    ActionPermissions,
    AuthorKind,
    CompletenessDatum,
    CompletenessGroup,
    CompletenessStatus,
    CompositionDatum,
    CompositionDimension,
    CorpusInventory,
    CorpusReviewProjection,
    DateMode,
    DateValue,
    IssueCode,
    IssueSeverity,
    PermissionState,
    ReviewProjectionError,
    ReviewProjectionErrorCode,
    RightsStatus,
    TermKind,
    ValidationIssue,
    VocabularyTerm,
    build_review_projection,
    export_completeness_csv,
    export_composition_csv,
    validate_inventory,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "p004"


def _inventory(name: str = "inventory-valid-text-proximity.json") -> CorpusInventory:
    return CorpusInventory.model_validate_json((FIXTURES / name).read_text(encoding="utf-8"))


def _rows(payload: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(payload.decode("utf-8"), newline="")))


def _projection(inventory: CorpusInventory) -> CorpusReviewProjection:
    return build_review_projection(inventory, validate_inventory(inventory))


def _cell(
    projection: CorpusReviewProjection,
    group: CompletenessGroup,
    row_key: str | None = None,
) -> CompletenessDatum:
    return next(
        item
        for item in projection.completeness
        if item.group is group and (row_key is None or item.row_key == row_key)
    )


def _issue(
    code: IssueCode,
    entity_type: Literal[
        "inventory",
        "author",
        "work",
        "edition",
        "source",
        "validated_file",
        "asset",
        "rights",
    ],
    entity_id: str | None,
    field_path: str,
    severity: IssueSeverity = IssueSeverity.BLOCKER,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        field_path=field_path,
        message_key="corpus.validation.test",
        message="Test issue.",
        why_it_matters="Test routing.",
        how_to_fix="Correct the documented field.",
    )


def _report_with(
    inventory: CorpusInventory,
    *issues: ValidationIssue,
) -> Any:
    report = validate_inventory(inventory)
    return report.model_copy(update={"issues": tuple(issues)})


def test_valid_projection_and_exports_share_one_inventory_identity() -> None:
    inventory = _inventory()
    projection = _projection(inventory)

    assert projection.corpus_work_count == 1
    assert [item.dimension for item in projection.composition] == list(CompositionDimension)
    assert [item.row_key for item in projection.timeline] == ["collodi_fixture_1883"]
    assert projection.timeline[0].work_title == "Fixture opera"
    assert projection.timeline[0].editions[0].edition_label == "Synthetic test edition"
    assert projection.timeline[0].sources[0].source_type_label == "Digital library"
    assert all(item.work_count == item.corpus_work_count == 1 for item in projection.composition)
    assert [item.status for item in projection.completeness] == [CompletenessStatus.COMPLETE] * len(
        CompletenessGroup
    )
    assert projection.corpus_issues == ()

    composition_rows = _rows(export_composition_csv(projection))
    completeness_rows = _rows(export_completeness_csv(projection))
    assert len(composition_rows) == len(CompositionDimension)
    assert len(completeness_rows) == len(CompletenessGroup)
    assert {row["inventory_sha256"] for row in composition_rows + completeness_rows} == {
        projection.inventory_sha256
    }
    assert {row["share_percent"] for row in composition_rows} == {"100.0000"}
    assert {row["status"] for row in completeness_rows} == {"complete"}
    assert all("Fixture opera" not in repr(item) for item in projection.composition)


def test_stale_or_wrong_purpose_report_is_rejected_without_content() -> None:
    inventory = _inventory()
    report = validate_inventory(inventory)
    stale = report.model_copy(update={"inventory_sha256": "0" * 64})
    with pytest.raises(ReviewProjectionError) as captured:
        build_review_projection(inventory, stale)
    assert captured.value.code is ReviewProjectionErrorCode.STALE_VALIDATION_REPORT
    assert captured.value.intake_error_code is None

    wrong_purpose = report.model_copy(update={"purpose": "group_comparison"})
    with pytest.raises(ReviewProjectionError, match="REVIEW_STALE_VALIDATION_REPORT"):
        build_review_projection(inventory, wrong_purpose)


def test_explicit_unknowns_remain_visible_without_becoming_quality_scores() -> None:
    inventory = _inventory()
    author = inventory.authors[0].model_copy(update={"kind": AuthorKind.UNKNOWN})
    work = inventory.works[0].model_copy(
        update={
            "first_publication": DateValue(mode=DateMode.UNKNOWN),
            "genre": VocabularyTerm(value="unknown", label="Unknown", kind=TermKind.UNKNOWN),
        }
    )
    edition = inventory.editions[0].model_copy(
        update={"edition_date": DateValue(mode=DateMode.UNKNOWN)}
    )
    source = inventory.sources[0].model_copy(
        update={
            "source_type": VocabularyTerm(
                value="unknown",
                label="Unknown",
                kind=TermKind.UNKNOWN,
            )
        }
    )
    asset = inventory.assets[0].model_copy(update={"normalization_profile": "unknown"})
    rights = inventory.rights[0].model_copy(
        update={
            "rights_status": RightsStatus.UNKNOWN,
            "permissions": ActionPermissions(
                upload=PermissionState.UNKNOWN,
                analysis=PermissionState.UNKNOWN,
                export=PermissionState.UNKNOWN,
                public_redistribution=PermissionState.UNKNOWN,
            ),
        }
    )
    changed = inventory.model_copy(
        update={
            "authors": (author,),
            "works": (work,),
            "editions": (edition,),
            "sources": (source,),
            "assets": (asset,),
            "rights": (rights,),
        }
    )

    projection = _projection(changed)
    assert {group: _cell(projection, group).status for group in CompletenessGroup} == {
        CompletenessGroup.IDENTITY: CompletenessStatus.WARNING,
        CompletenessGroup.CHRONOLOGY: CompletenessStatus.MISSING,
        CompletenessGroup.EDITION: CompletenessStatus.WARNING,
        CompletenessGroup.SOURCE: CompletenessStatus.WARNING,
        CompletenessGroup.CLASSIFICATION: CompletenessStatus.WARNING,
        CompletenessGroup.RIGHTS: CompletenessStatus.MISSING,
        CompletenessGroup.NORMALIZATION: CompletenessStatus.MISSING,
    }
    assert (
        next(
            item for item in projection.composition if item.dimension is CompositionDimension.GENRE
        ).category_value
        == "unknown"
    )


@pytest.mark.parametrize("mode", [DateMode.APPROXIMATE, DateMode.RANGE])
def test_uncertain_dates_are_warnings_while_reversed_ranges_are_conflicts(
    mode: DateMode,
) -> None:
    inventory = _inventory()
    date_value = (
        DateValue(mode=mode, start_year=1883, end_year=1885)
        if mode is DateMode.RANGE
        else DateValue(mode=mode, start_year=1883)
    )
    changed = inventory.model_copy(
        update={
            "works": (inventory.works[0].model_copy(update={"first_publication": date_value}),),
            "editions": (inventory.editions[0].model_copy(update={"edition_date": date_value}),),
        }
    )
    projection = _projection(changed)
    assert _cell(projection, CompletenessGroup.CHRONOLOGY).status is CompletenessStatus.WARNING
    assert _cell(projection, CompletenessGroup.EDITION).status is CompletenessStatus.WARNING

    reversed_date = DateValue(mode=DateMode.RANGE, start_year=1885, end_year=1883)
    reversed_inventory = inventory.model_copy(
        update={
            "works": (inventory.works[0].model_copy(update={"first_publication": reversed_date}),),
            "editions": (inventory.editions[0].model_copy(update={"edition_date": reversed_date}),),
        }
    )
    reversed_projection = _projection(reversed_inventory)
    assert (
        _cell(reversed_projection, CompletenessGroup.CHRONOLOGY).status
        is CompletenessStatus.CONFLICT
    )
    assert (
        _cell(reversed_projection, CompletenessGroup.EDITION).status is CompletenessStatus.CONFLICT
    )


def test_unmapped_work_remains_in_every_composition_denominator() -> None:
    inventory = _inventory()
    second_work = inventory.works[0].model_copy(
        update={
            "work_id": "unmapped_work",
            "title_original": "Unmapped work",
            "adaptation": VocabularyTerm(
                value="not_applicable",
                label="Not applicable",
                kind=TermKind.NOT_APPLICABLE,
            ),
        }
    )
    changed = inventory.model_copy(update={"works": (inventory.works[0], second_work)})
    projection = _projection(changed)

    assert projection.corpus_work_count == 2
    for dimension in CompositionDimension:
        assert (
            sum(item.work_count for item in projection.composition if item.dimension is dimension)
            == 2
        )
    assert next(
        item
        for item in projection.composition
        if item.dimension is CompositionDimension.SOURCE_TYPE and item.category_value == "missing"
    ).work_row_keys == ("unmapped_work",)
    assert (
        next(
            item
            for item in projection.composition
            if item.dimension is CompositionDimension.ADAPTATION
            and item.category_value == "not_applicable"
        ).work_count
        == 1
    )
    assert _cell(projection, CompletenessGroup.IDENTITY, "unmapped_work").status is (
        CompletenessStatus.MISSING
    )
    assert _cell(projection, CompletenessGroup.EDITION, "unmapped_work").status is (
        CompletenessStatus.MISSING
    )
    assert _cell(projection, CompletenessGroup.SOURCE, "unmapped_work").status is (
        CompletenessStatus.MISSING
    )
    assert _cell(projection, CompletenessGroup.RIGHTS, "unmapped_work").status is (
        CompletenessStatus.MISSING
    )
    assert _cell(projection, CompletenessGroup.NORMALIZATION, "unmapped_work").status is (
        CompletenessStatus.MISSING
    )
    assert projection.timeline[-1].row_key == "unmapped_work"
    assert projection.timeline[-1].editions == ()
    assert projection.timeline[-1].sources == ()


def test_timeline_order_is_chronological_and_input_order_invariant() -> None:
    inventory = _inventory()
    early = inventory.works[0].model_copy(
        update={
            "work_id": "early_work",
            "title_original": "Early work",
            "first_publication": DateValue(mode=DateMode.APPROXIMATE, start_year=1870),
        }
    )
    unknown = inventory.works[0].model_copy(
        update={
            "work_id": "unknown_work",
            "title_original": "Unknown work",
            "first_publication": DateValue(mode=DateMode.UNKNOWN),
        }
    )
    changed = inventory.model_copy(update={"works": (unknown, inventory.works[0], early)})
    reordered = changed.model_copy(update={"works": tuple(reversed(changed.works))})
    first = _projection(changed)
    second = _projection(reordered)
    assert [item.row_key for item in first.timeline] == [
        "early_work",
        "collodi_fixture_1883",
        "unknown_work",
    ]
    assert first.timeline == second.timeline


def test_multiple_source_types_become_one_conflict_category_per_work() -> None:
    inventory = _inventory()
    second_edition = inventory.editions[0].model_copy(update={"edition_id": "second_edition"})
    second_source = inventory.sources[0].model_copy(
        update={
            "source_id": "second_source",
            "edition_id": "second_edition",
            "source_type": VocabularyTerm(
                value="print_edition",
                label="Print edition",
                kind=TermKind.CONTROLLED,
            ),
        }
    )
    second_asset = inventory.assets[0].model_copy(
        update={
            "asset_id": "asset_second",
            "file_label": "second.txt",
            "content_sha256": "2" * 64,
            "edition_id": "second_edition",
            "source_id": "second_source",
            "rights_asset_ids": ("asset_second",),
        }
    )
    second_file = inventory.validated_files[0].model_copy(
        update={"file_label": "second.txt", "content_sha256": "2" * 64}
    )
    second_rights = inventory.rights[0].model_copy(
        update={"asset_id": "asset_second", "source_id": "second_source"}
    )
    changed = inventory.model_copy(
        update={
            "editions": (*inventory.editions, second_edition),
            "sources": (*inventory.sources, second_source),
            "assets": (*inventory.assets, second_asset),
            "validated_files": (*inventory.validated_files, second_file),
            "rights": (*inventory.rights, second_rights),
        }
    )
    projection = _projection(changed)
    source_rows = [
        item
        for item in projection.composition
        if item.dimension is CompositionDimension.SOURCE_TYPE
    ]
    assert [(item.category_value, item.work_count) for item in source_rows] == [("conflict", 1)]
    assert _cell(projection, CompletenessGroup.IDENTITY).status is CompletenessStatus.CONFLICT
    assert _cell(projection, CompletenessGroup.EDITION).status is CompletenessStatus.CONFLICT
    assert _cell(projection, CompletenessGroup.SOURCE).status is CompletenessStatus.CONFLICT


def test_duplicate_work_ids_receive_stable_row_keys_and_all_groups() -> None:
    inventory = _inventory()
    duplicate = inventory.works[0].model_copy(update={"title_original": "Another title"})
    changed = inventory.model_copy(update={"works": (duplicate, inventory.works[0])})
    projection = _projection(changed)
    row_keys = sorted({item.row_key for item in projection.completeness})
    assert row_keys == ["collodi_fixture_1883#1", "collodi_fixture_1883#2"]
    assert all(
        _cell(projection, CompletenessGroup.IDENTITY, row_key).status is CompletenessStatus.CONFLICT
        for row_key in row_keys
    )


@pytest.mark.parametrize(
    ("asset_updates", "file_updates", "expected"),
    [
        ({"mapping_confirmed": False}, {}, CompletenessStatus.MISSING),
        ({"file_label": "absent.txt"}, {}, CompletenessStatus.MISSING),
        ({"content_sha256": "2" * 64}, {}, CompletenessStatus.CONFLICT),
        ({}, {"content_sha256": "2" * 64}, CompletenessStatus.CONFLICT),
    ],
)
def test_identity_projection_exposes_mapping_and_hash_failures(
    asset_updates: dict[str, object],
    file_updates: dict[str, object],
    expected: CompletenessStatus,
) -> None:
    inventory = _inventory()
    changed = inventory.model_copy(
        update={
            "assets": (inventory.assets[0].model_copy(update=asset_updates),),
            "validated_files": (inventory.validated_files[0].model_copy(update=file_updates),),
        }
    )
    assert _cell(_projection(changed), CompletenessGroup.IDENTITY).status is expected


def test_unresolved_contributor_identity_is_missing() -> None:
    inventory = _inventory()
    unrelated_author = inventory.authors[0].model_copy(update={"author_id": "other_author"})
    changed = inventory.model_copy(update={"authors": (unrelated_author,)})
    assert _cell(_projection(changed), CompletenessGroup.IDENTITY).status is (
        CompletenessStatus.MISSING
    )


def test_custom_normalization_requires_notes() -> None:
    inventory = _inventory()
    undocumented = inventory.model_copy(
        update={
            "assets": (
                inventory.assets[0].model_copy(
                    update={"normalization_profile": "custom", "normalization_notes": None}
                ),
            )
        }
    )
    documented = inventory.model_copy(
        update={
            "assets": (
                inventory.assets[0].model_copy(
                    update={
                        "normalization_profile": "custom",
                        "normalization_notes": "NFC only",
                    }
                ),
            )
        }
    )
    assert _cell(_projection(undocumented), CompletenessGroup.NORMALIZATION).status is (
        CompletenessStatus.MISSING
    )
    assert _cell(_projection(documented), CompletenessGroup.NORMALIZATION).status is (
        CompletenessStatus.COMPLETE
    )


def test_excluded_rights_are_complete_documentation_not_permission() -> None:
    inventory = _inventory()
    prohibited = ActionPermissions(
        upload=PermissionState.PROHIBITED,
        analysis=PermissionState.PROHIBITED,
        export=PermissionState.PROHIBITED,
        public_redistribution=PermissionState.PROHIBITED,
    )
    changed = inventory.model_copy(
        update={
            "rights": (
                inventory.rights[0].model_copy(
                    update={"rights_status": RightsStatus.EXCLUDED, "permissions": prohibited}
                ),
            )
        }
    )
    cell = _cell(_projection(changed), CompletenessGroup.RIGHTS)
    assert cell.status is CompletenessStatus.COMPLETE
    assert IssueCode.UPLOAD_PERMISSION_REQUIRED in cell.issue_codes
    assert IssueCode.ANALYSIS_PERMISSION_REQUIRED in cell.issue_codes
    assert "permissions are reported separately" in cell.summary


def test_missing_and_conflicting_rights_chains_are_distinguished() -> None:
    inventory = _inventory()
    missing = inventory.model_copy(
        update={
            "assets": (
                inventory.assets[0].model_copy(
                    update={
                        "rights_asset_ids": ("asset_collodi_fixture", "asset_missing"),
                        "rights_chain_confirmed": False,
                    }
                ),
            )
        }
    )
    assert _cell(_projection(missing), CompletenessGroup.RIGHTS).status is (
        CompletenessStatus.MISSING
    )

    duplicate_rights = inventory.rights[0].model_copy(update={"notes": "Duplicate"})
    conflicting = inventory.model_copy(update={"rights": (inventory.rights[0], duplicate_rights)})
    assert _cell(_projection(conflicting), CompletenessGroup.RIGHTS).status is (
        CompletenessStatus.CONFLICT
    )


def test_invalid_fixture_routes_resolvable_issues_and_retains_corpus_issues() -> None:
    projection = _projection(_inventory("inventory-invalid-cross-record.json"))
    assert _cell(projection, CompletenessGroup.IDENTITY).status is CompletenessStatus.MISSING
    assert _cell(projection, CompletenessGroup.EDITION).status is CompletenessStatus.CONFLICT
    assert _cell(projection, CompletenessGroup.CLASSIFICATION).status is (
        CompletenessStatus.MISSING
    )
    assert _cell(projection, CompletenessGroup.RIGHTS).status is CompletenessStatus.CONFLICT
    assert _cell(projection, CompletenessGroup.NORMALIZATION).status is (CompletenessStatus.MISSING)
    assert projection.corpus_issues == ()


@pytest.mark.parametrize(
    ("issue", "expected_group", "expected_status"),
    [
        (
            _issue(IssueCode.DUPLICATE_AUTHOR_ID, "author", "carlo_collodi", "author_id"),
            CompletenessGroup.IDENTITY,
            CompletenessStatus.CONFLICT,
        ),
        (
            _issue(
                IssueCode.DUPLICATE_EDITION_ID, "edition", "collodi_fixture_edition", "edition_id"
            ),
            CompletenessGroup.EDITION,
            CompletenessStatus.CONFLICT,
        ),
        (
            _issue(IssueCode.DUPLICATE_SOURCE_ID, "source", "collodi_fixture_source", "source_id"),
            CompletenessGroup.SOURCE,
            CompletenessStatus.CONFLICT,
        ),
        (
            _issue(IssueCode.DUPLICATE_FILE_LABEL, "asset", "collodi_fixture.txt", "file_label"),
            CompletenessGroup.IDENTITY,
            CompletenessStatus.CONFLICT,
        ),
        (
            _issue(
                IssueCode.CHRONOLOGY_REQUIRED, "work", "collodi_fixture_1883", "first_publication"
            ),
            CompletenessGroup.CHRONOLOGY,
            CompletenessStatus.MISSING,
        ),
        (
            _issue(
                IssueCode.DATE_RANGE_REVERSED, "edition", "collodi_fixture_edition", "edition_date"
            ),
            CompletenessGroup.EDITION,
            CompletenessStatus.CONFLICT,
        ),
        (
            _issue(
                IssueCode.EDITION_DATE_UNKNOWN,
                "edition",
                "collodi_fixture_edition",
                "edition_date",
                IssueSeverity.WARNING,
            ),
            CompletenessGroup.EDITION,
            CompletenessStatus.WARNING,
        ),
        (
            _issue(
                IssueCode.EDITION_REFERENCE_MISSING,
                "source",
                "collodi_fixture_source",
                "edition_id",
            ),
            CompletenessGroup.SOURCE,
            CompletenessStatus.MISSING,
        ),
        (
            _issue(
                IssueCode.EDITION_REFERENCE_MISSING, "asset", "asset_collodi_fixture", "edition_id"
            ),
            CompletenessGroup.EDITION,
            CompletenessStatus.MISSING,
        ),
        (
            _issue(
                IssueCode.SOURCE_REFERENCE_MISSING, "asset", "asset_collodi_fixture", "source_id"
            ),
            CompletenessGroup.SOURCE,
            CompletenessStatus.MISSING,
        ),
        (
            _issue(IssueCode.RELATIONSHIP_CONFLICT, "asset", "asset_collodi_fixture", "source_id"),
            CompletenessGroup.SOURCE,
            CompletenessStatus.CONFLICT,
        ),
        (
            _issue(
                IssueCode.WORK_REFERENCE_MISSING, "edition", "collodi_fixture_edition", "work_id"
            ),
            CompletenessGroup.EDITION,
            CompletenessStatus.MISSING,
        ),
        (
            _issue(IssueCode.CONTROLLED_TERM_UNKNOWN, "work", "collodi_fixture_1883", "genre"),
            CompletenessGroup.CLASSIFICATION,
            CompletenessStatus.CONFLICT,
        ),
        (
            _issue(
                IssueCode.CONFOUND_METADATA_UNKNOWN,
                "source",
                "collodi_fixture_source",
                "source_type",
                IssueSeverity.WARNING,
            ),
            CompletenessGroup.SOURCE,
            CompletenessStatus.WARNING,
        ),
        (
            _issue(
                IssueCode.RIGHTS_STATUS_UNRESOLVED,
                "rights",
                "asset_collodi_fixture",
                "rights_status",
                IssueSeverity.WARNING,
            ),
            CompletenessGroup.RIGHTS,
            CompletenessStatus.MISSING,
        ),
        (
            _issue(
                IssueCode.NORMALIZATION_DETAILS_REQUIRED,
                "asset",
                "asset_collodi_fixture",
                "normalization_notes",
            ),
            CompletenessGroup.NORMALIZATION,
            CompletenessStatus.MISSING,
        ),
    ],
)
def test_issue_routing_uses_entity_relationships(
    issue: ValidationIssue,
    expected_group: CompletenessGroup,
    expected_status: CompletenessStatus,
) -> None:
    inventory = _inventory()
    projection = build_review_projection(inventory, _report_with(inventory, issue))
    cell = _cell(projection, expected_group)
    assert issue.code in cell.issue_codes
    assert cell.status is expected_status
    assert cell.highest_issue_severity is issue.severity


def test_unresolved_and_inventory_issues_remain_corpus_level() -> None:
    inventory = _inventory()
    issues = (
        _issue(IssueCode.STYLE_LANGUAGE_MIXED, "inventory", None, "works.language"),
        _issue(IssueCode.FILE_MAPPING_UNCONFIRMED, "asset", "asset_missing", "mapping_confirmed"),
        _issue(IssueCode.UNMAPPED_VALIDATED_FILE, "validated_file", "orphan.txt", "file_label"),
    )
    projection = build_review_projection(inventory, _report_with(inventory, *issues))
    assert projection.corpus_issues == issues


def test_review_csv_exports_fail_closed_on_unsafe_projected_cells() -> None:
    inventory = _inventory()
    unsafe_title = inventory.works[0].model_copy(update={"title_original": "=2+2"})
    unsafe_inventory = inventory.model_copy(update={"works": (unsafe_title,)})
    projection = _projection(unsafe_inventory)
    with pytest.raises(ReviewProjectionError) as captured:
        export_completeness_csv(projection)
    assert captured.value.code is ReviewProjectionErrorCode.CSV_POLICY_REJECTED
    assert captured.value.intake_error_code is not None

    unsafe_genre = inventory.works[0].model_copy(
        update={
            "genre": VocabularyTerm(
                value="novel",
                label="<script>",
                kind=TermKind.CONTROLLED,
            )
        }
    )
    genre_projection = _projection(inventory.model_copy(update={"works": (unsafe_genre,)}))
    with pytest.raises(ReviewProjectionError, match="REVIEW_CSV_POLICY_REJECTED"):
        export_composition_csv(genre_projection)


def test_projection_models_reject_internal_count_and_order_drift() -> None:
    with pytest.raises(ValidationError, match="work_count"):
        CompositionDatum(
            dimension=CompositionDimension.GENRE,
            dimension_label="Genre",
            category_value="novel",
            category_label="Novel",
            work_row_keys=("one",),
            work_count=0,
            corpus_work_count=1,
        )
    with pytest.raises(ValidationError, match="cannot exceed"):
        CompositionDatum(
            dimension=CompositionDimension.GENRE,
            dimension_label="Genre",
            category_value="novel",
            category_label="Novel",
            work_row_keys=("one", "two"),
            work_count=2,
            corpus_work_count=1,
        )
    with pytest.raises(ValidationError, match="must be sorted"):
        CompositionDatum(
            dimension=CompositionDimension.GENRE,
            dimension_label="Genre",
            category_value="novel",
            category_label="Novel",
            work_row_keys=("two", "one"),
            work_count=2,
            corpus_work_count=2,
        )

    valid_cell = _cell(_projection(_inventory()), CompletenessGroup.IDENTITY)
    with pytest.raises(ValidationError, match="field paths"):
        CompletenessDatum.model_validate({**valid_cell.model_dump(), "field_paths": ("z", "a")})
    with pytest.raises(ValidationError, match="issue codes"):
        CompletenessDatum.model_validate(
            {
                **valid_cell.model_dump(),
                "issue_codes": (
                    IssueCode.WORK_ASSET_MISSING,
                    IssueCode.AUTHOR_ROLE_REQUIRED,
                ),
            }
        )


def test_projection_model_rejects_missing_dimensions_rows_and_groups() -> None:
    projection = _projection(_inventory())
    with pytest.raises(ValidationError, match="composition dimension"):
        CorpusReviewProjection.model_validate(
            {**projection.model_dump(), "composition": projection.composition[:-1]}
        )
    with pytest.raises(ValidationError, match="one row per"):
        CorpusReviewProjection.model_validate({**projection.model_dump(), "completeness": ()})
    with pytest.raises(ValidationError, match="every completeness group"):
        CorpusReviewProjection.model_validate(
            {**projection.model_dump(), "completeness": projection.completeness[:-1]}
        )
    with pytest.raises(ValidationError, match="same corpus work rows"):
        CorpusReviewProjection.model_validate({**projection.model_dump(), "timeline": ()})

    inventory = _inventory()
    second_work = inventory.works[0].model_copy(
        update={"work_id": "second_work", "title_original": "Second work"}
    )
    two_work_projection = _projection(
        inventory.model_copy(update={"works": (*inventory.works, second_work)})
    )
    with pytest.raises(ValidationError, match="must be unique"):
        CorpusReviewProjection.model_validate(
            {
                **two_work_projection.model_dump(),
                "timeline": (
                    two_work_projection.timeline[0],
                    two_work_projection.timeline[0],
                ),
            }
        )
    with pytest.raises(ValidationError, match="chronology order"):
        CorpusReviewProjection.model_validate(
            {
                **two_work_projection.model_dump(),
                "timeline": tuple(reversed(two_work_projection.timeline)),
            }
        )
