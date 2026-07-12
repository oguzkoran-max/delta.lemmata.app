from __future__ import annotations

import hashlib
import io
import zipfile
from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

from delta_lemmata import webapp as webapp_module
from delta_lemmata.corpus import (
    CorpusInventory,
    DateMode,
    DateValue,
    MetadataCsvExportError,
    MetadataCsvExportErrorCode,
    MetadataCsvImportResult,
    PurposeId,
    ReviewProjectionError,
    ReviewProjectionErrorCode,
    TermKind,
    ValidatedCorpusUnit,
    ValidatedFileRecord,
    VocabularyTerm,
    build_review_projection,
    metadata_csv_template,
    validate_inventory,
)

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "p004"


def run_app() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=20).run()


def _by_label(elements: Iterable[Any], label: str) -> Any:
    return next(element for element in elements if element.label == label)


def _all_by_label(elements: Iterable[Any], label: str) -> list[Any]:
    return [element for element in elements if element.label == label]


def _zip_payload(entries: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return output.getvalue()


def _advance_to_describe(app: AppTest, payload: bytes = b"one text") -> AppTest:
    app.file_uploader[0].upload("one.txt", payload, "text/plain").run()
    app.button(key="corpus_continue").click().run()
    return app


def _fixture_inventory() -> CorpusInventory:
    return CorpusInventory.model_validate_json(
        (FIXTURES / "inventory-valid-text-proximity.json").read_text(encoding="utf-8")
    )


def _fixture_import() -> tuple[ValidatedCorpusUnit, MetadataCsvImportResult]:
    inventory = _fixture_inventory()
    report = validate_inventory(inventory)
    asset = inventory.assets[0]
    unit = ValidatedCorpusUnit(
        validated_file=inventory.validated_files[0],
        line_count=asset.line_count,
        token_count=asset.token_count,
    )
    result = MetadataCsvImportResult(
        csv_sha256="0" * 64,
        row_count=1,
        blocked=report.blocked,
        issues=(),
        inventory=inventory,
        validation_report=report,
    )
    return unit, result


def _inject_imported_describe(app: AppTest, purpose: PurposeId) -> AppTest:
    unit, imported = _fixture_import()
    app.session_state[webapp_module._FLOW_STAGE_KEY] = webapp_module.CorpusSubstage.DESCRIBE.value
    app.session_state[webapp_module._FLOW_PURPOSE_KEY] = purpose.value
    app.session_state[webapp_module._FLOW_CATALOG_KEY] = (unit,)
    app.session_state[webapp_module._FLOW_IMPORT_KEY] = imported
    return app.run()


def _open_imported_review() -> AppTest:
    app = _inject_imported_describe(run_app(), PurposeId.TEXT_PROXIMITY)
    _by_label(app.button, "Review imported metadata").click().run()
    return app


def _open_guided_review() -> AppTest:
    app = _advance_to_describe(run_app())
    _by_label(app.text_input, "Primary author name").input("Carlo Collodi").run()
    _by_label(app.text_input, "Source URL").input("https://www.liberliber.it/").run()
    _by_label(app.selectbox, "Documented rights state").set_value("analysis_only").run()
    app.button(key="guided_build_review").click().run()
    return app


def _two_work_inventory() -> CorpusInventory:
    inventory = _fixture_inventory()
    second_work = inventory.works[0].model_copy(
        update={
            "work_id": "later_work",
            "title_original": "Later work",
            "first_publication": DateValue(mode=DateMode.EXACT, start_year=1900),
        }
    )
    second_edition = inventory.editions[0].model_copy(
        update={
            "edition_id": "later_edition",
            "work_id": "later_work",
            "edition_date": DateValue(mode=DateMode.EXACT, start_year=1901),
        }
    )
    second_source = inventory.sources[0].model_copy(
        update={"source_id": "later_source", "edition_id": "later_edition"}
    )
    second_asset = inventory.assets[0].model_copy(
        update={
            "asset_id": "asset_later",
            "file_label": "later.txt",
            "content_sha256": "2" * 64,
            "work_id": "later_work",
            "edition_id": "later_edition",
            "source_id": "later_source",
            "rights_asset_ids": ("asset_later",),
        }
    )
    second_file = inventory.validated_files[0].model_copy(
        update={"file_label": "later.txt", "content_sha256": "2" * 64}
    )
    second_rights = inventory.rights[0].model_copy(
        update={"asset_id": "asset_later", "source_id": "later_source"}
    )
    return inventory.model_copy(
        update={
            "works": (*inventory.works, second_work),
            "editions": (*inventory.editions, second_edition),
            "sources": (*inventory.sources, second_source),
            "assets": (*inventory.assets, second_asset),
            "validated_files": (*inventory.validated_files, second_file),
            "rights": (*inventory.rights, second_rights),
        }
    )


def _inject_review(app: AppTest, inventory: CorpusInventory) -> AppTest:
    app.session_state[webapp_module._FLOW_STAGE_KEY] = webapp_module.CorpusSubstage.REVIEW.value
    app.session_state[webapp_module._FLOW_PURPOSE_KEY] = inventory.purpose.value
    app.session_state[webapp_module._FLOW_INVENTORY_KEY] = inventory
    app.session_state[webapp_module._FLOW_REPORT_KEY] = validate_inventory(inventory)
    app.session_state[webapp_module._FLOW_ORIGIN_KEY] = webapp_module.CorpusOrigin.GUIDED.value
    return app.run()


def test_corrupt_and_incomplete_stages_recover_to_upload() -> None:
    app = run_app()
    app.session_state[webapp_module._FLOW_STAGE_KEY] = "corrupt"
    app.run()
    assert [heading.value for heading in app.header][0] == "Upload the research corpus"

    app.session_state[webapp_module._FLOW_STAGE_KEY] = webapp_module.CorpusSubstage.DESCRIBE.value
    app.run()
    assert [heading.value for heading in app.header][0] == "Upload the research corpus"

    app.session_state[webapp_module._FLOW_STAGE_KEY] = webapp_module.CorpusSubstage.REVIEW.value
    app.run()
    assert [heading.value for heading in app.header][0] == "Upload the research corpus"


def test_invalid_origin_and_correction_state_fail_back_to_safe_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_streamlit = SimpleNamespace(
        session_state={
            webapp_module._FLOW_ORIGIN_KEY: "corrupt",
            webapp_module._FLOW_CORRECTION_KEY: {"field_path": "not-a-target"},
        }
    )
    monkeypatch.setattr(webapp_module, "st", fake_streamlit)
    assert webapp_module._origin() is webapp_module.CorpusOrigin.GUIDED
    assert webapp_module._correction_target() is None


def test_describe_can_return_to_upload_without_retaining_draft_state() -> None:
    app = _advance_to_describe(run_app())
    _by_label(app.text_input, "Primary author name").input("Temporary author").run()
    _by_label(app.button, "Start again with different files").click().run()
    assert [heading.value for heading in app.header][0] == "Upload the research corpus"
    assert "Temporary author" not in repr(app.session_state.filtered_state)


def test_group_dates_and_verified_open_rights_reveal_only_relevant_fields() -> None:
    app = run_app()
    app.segmented_control[0].set_value(PurposeId.GROUP_COMPARISON.value).run()
    app = _advance_to_describe(app)
    assert _by_label(app.text_input, "Group label") is not None

    _by_label(app.selectbox, "First-publication certainty").set_value(DateMode.EXACT.value).run()
    assert _by_label(app.text_input, "First-publication year") is not None

    _by_label(app.selectbox, "Analyzed-edition date certainty").set_value(
        DateMode.RANGE.value
    ).run()
    assert _by_label(app.text_input, "Analyzed-edition year") is not None
    assert _by_label(app.text_input, "Edition end year") is not None

    _by_label(app.selectbox, "Documented rights state").set_value("verified_open").run()
    assert _by_label(app.text_input, "License or public-domain statement") is not None
    assert _by_label(app.text_input, "Jurisdiction") is not None


def test_date_parsing_preserves_uncertainty_and_rejects_invalid_years() -> None:
    exact = webapp_module._date_from_values(
        {"mode": DateMode.EXACT, "start": "1883", "end": ""},
        "publication",
    )
    ranged = webapp_module._date_from_values(
        {"mode": DateMode.RANGE, "start": "1881", "end": "1883"},
        "publication",
    )
    assert exact.start_year == 1883
    assert webapp_module._date_label(exact) == "1883 (Exact)"
    assert ranged.bounds == (1881, 1883)
    assert webapp_module._date_label(ranged) == "1881–1883 (Range)"
    with pytest.raises(ValueError, match="must be a year"):
        webapp_module._parse_year("not-a-year", "publication")
    with pytest.raises(ValueError, match="must be a year"):
        webapp_module._parse_year("10000", "publication")


def test_invalid_year_is_reported_in_describe_without_a_traceback() -> None:
    app = _advance_to_describe(run_app())
    _by_label(app.selectbox, "First-publication certainty").set_value(DateMode.EXACT.value).run()
    _by_label(app.text_input, "First-publication year").input("not-a-year").run()
    app.button(key="guided_build_review").click().run()
    assert len(app.exception) == 0
    assert [message.value for message in app.error] == [
        "Review these fields before continuing: First-publication year must be a year "
        "from 1 to 9999."
    ]


@pytest.mark.parametrize("metadata_kind", ["header", "row"])
def test_uploaded_metadata_semantics_are_reviewed_after_secure_intake(metadata_kind: str) -> None:
    payload = b"one text"
    if metadata_kind == "header":
        metadata = b"title,year\nOne,1883"
    else:
        validated = ValidatedFileRecord(
            file_label="one.txt",
            content_sha256=hashlib.sha256(payload).hexdigest(),
            intake_profile="ingestion-limits-v1",
        )
        metadata = metadata_csv_template((validated,), PurposeId.TEXT_PROXIMITY)
    app = run_app()
    app.file_uploader[0].upload("one.txt", payload, "text/plain")
    app.file_uploader[1].upload("metadata.csv", metadata, "text/csv")
    app.run()
    app.button(key="corpus_continue").click().run()
    assert len(app.exception) == 0
    assert "Advanced metadata import" in [heading.value for heading in app.subheader]
    assert any(
        "cannot yet produce a complete inventory" in message.value for message in app.warning
    )
    assert len(app.error) >= 1


def test_imported_metadata_purpose_mismatch_stays_in_describe() -> None:
    app = _inject_imported_describe(run_app(), PurposeId.STYLE_OVER_TIME)
    assert [heading.value for heading in app.header][0] == "Describe what each text represents"
    assert [message.value for message in app.warning] == [
        "The CSV passed file-safety checks but cannot yet produce a complete inventory."
    ]
    assert not any(button.label == "Review imported metadata" for button in app.button)


def test_valid_import_opens_review_and_supports_edit_and_full_reset() -> None:
    app = _inject_imported_describe(run_app(), PurposeId.TEXT_PROXIMITY)
    app.session_state["review_confirmation_stale"] = True
    _by_label(app.button, "Review imported metadata").click().run()
    assert [heading.value for heading in app.header][0] == "Review the documented corpus"
    assert "review_confirmation_stale" not in app.session_state.filtered_state
    assert [message.value for message in app.success][-1] == (
        "No corpus-documentation issues were reported."
    )

    _by_label(app.button, "Edit metadata").click().run()
    assert [heading.value for heading in app.header][0] == "Describe what each text represents"

    _by_label(app.button, "Review imported metadata").click().run()
    _by_label(app.button, "Start over").click().run()
    assert [heading.value for heading in app.header][0] == "Upload the research corpus"
    assert webapp_module._FLOW_PURPOSE_KEY not in app.session_state.filtered_state


def test_unknown_rights_produce_a_blocked_review() -> None:
    app = _advance_to_describe(run_app())
    _by_label(app.text_input, "Primary author name").input("Carlo Collodi").run()
    _by_label(app.text_input, "Source URL").input("https://www.liberliber.it/").run()
    app.button(key="guided_build_review").click().run()
    assert len(app.exception) == 0
    assert [heading.value for heading in app.header][0] == "Review the documented corpus"
    assert [message.value for message in app.error] == [
        "Corpus documentation contains blockers. Return to Describe and correct them; no "
        "analysis state has been created.",
        "Resolve every corpus blocker before final confirmation can be recorded.",
    ]
    confirmation = _by_label(
        app.checkbox,
        "I reviewed the file-to-work mappings and the documented rights records.",
    )
    assert confirmation.disabled is True


def test_guided_zip_members_build_two_work_review_without_payload_retention() -> None:
    app = run_app()
    app.segmented_control[1].set_value("zip_archive").run()
    app.file_uploader[0].upload(
        "collodi.zip",
        _zip_payload(
            [
                ("early/one.txt", b"ZIP_CANARY_EARLY"),
                ("late/two.txt", b"ZIP_CANARY_LATE"),
            ]
        ),
        "application/zip",
    ).run()
    app.button(key="corpus_continue").click().run()

    authors = _all_by_label(app.text_input, "Primary author name")
    sources = _all_by_label(app.text_input, "Source URL")
    assert len(authors) == len(sources) == 2
    for author in authors:
        author.input("Carlo Collodi")
    for source in sources:
        source.input("https://www.liberliber.it/")
    app.run()

    rights = _all_by_label(app.selectbox, "Documented rights state")
    assert len(rights) == 2
    for control in rights:
        control.set_value("analysis_only")
    app.run()
    app.button(key="guided_build_review").click().run()

    assert [heading.value for heading in app.header][0] == "Review the documented corpus"
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Independent works"] == "2"
    assert len(_by_label(app.radio, "Select a documented work on the chronology").options) == 2
    rendered = "\n".join(item.value for item in app.markdown)
    assert rendered.count('data-row-key="work_') >= 2
    state = repr(app.session_state.filtered_state)
    assert "ZIP_CANARY_EARLY" not in state
    assert "ZIP_CANARY_LATE" not in state
    assert "storage_name" not in state


def test_timeline_selection_updates_details_without_mutating_inventory() -> None:
    inventory = _two_work_inventory()
    app = _inject_review(run_app(), inventory)
    selector = _by_label(
        app.radio,
        "Select a documented work on the chronology",
    )
    assert selector.value == "collodi_fixture_1883"
    assert any(
        'data-row-key="collodi_fixture_1883"' in item.value
        and "Fixture opera" in item.value
        and "1883" in item.value
        for item in app.markdown
    )
    inventory_before = app.session_state[webapp_module._FLOW_INVENTORY_KEY]

    selector.set_value("later_work").run()

    assert any(
        'data-row-key="later_work"' in item.value
        and "Later work" in item.value
        and "1900" in item.value
        for item in app.markdown
    )
    assert app.session_state[webapp_module._FLOW_INVENTORY_KEY] == inventory_before


def test_timeline_labels_unresolved_edition_and_source_relationships_explicitly() -> None:
    inventory = _fixture_inventory()
    unmapped = inventory.works[0].model_copy(
        update={"work_id": "unmapped_work", "title_original": "Unmapped work"}
    )
    changed = inventory.model_copy(update={"works": (*inventory.works, unmapped)})
    item = next(
        value
        for value in build_review_projection(changed, validate_inventory(changed)).timeline
        if value.row_key == "unmapped_work"
    )
    assert webapp_module._timeline_edition_label(item) == "Unresolved"
    assert webapp_module._timeline_source_label(item) == "Unresolved"


def test_guided_correction_shortcut_returns_to_the_exact_work_section() -> None:
    app = _open_guided_review()
    target_picker = _by_label(app.selectbox, "Metadata field to correct")
    assert target_picker.value == 0

    _by_label(app.button, "Edit selected field").click().run()

    target = app.session_state[webapp_module._FLOW_CORRECTION_KEY]
    assert isinstance(target, webapp_module.CorrectionTarget)
    assert target.group.value == "chronology"
    assert target.field_path.endswith("first_publication")
    assert [heading.value for heading in app.header][0] == "Describe what each text represents"
    assert any(target.field_path in message.value for message in app.info)
    assert _by_label(app.text_input, "Primary author name").value == "Carlo Collodi"


def test_csv_correction_shortcut_names_the_source_field_without_false_editing() -> None:
    unit, imported = _fixture_import()
    inventory = imported.inventory
    assert inventory is not None
    changed_work = inventory.works[0].model_copy(
        update={
            "genre": VocabularyTerm(
                value="unknown",
                label="Unknown",
                kind=TermKind.UNKNOWN,
            )
        }
    )
    changed_inventory = inventory.model_copy(update={"works": (changed_work,)})
    changed_import = imported.model_copy(
        update={
            "inventory": changed_inventory,
            "validation_report": validate_inventory(changed_inventory),
        }
    )
    app = run_app()
    app.session_state[webapp_module._FLOW_STAGE_KEY] = webapp_module.CorpusSubstage.DESCRIBE.value
    app.session_state[webapp_module._FLOW_PURPOSE_KEY] = PurposeId.TEXT_PROXIMITY.value
    app.session_state[webapp_module._FLOW_CATALOG_KEY] = (unit,)
    app.session_state[webapp_module._FLOW_IMPORT_KEY] = changed_import
    app.run()
    _by_label(app.button, "Review imported metadata").click().run()

    _by_label(app.button, "Edit selected field").click().run()

    target = app.session_state[webapp_module._FLOW_CORRECTION_KEY]
    assert isinstance(target, webapp_module.CorrectionTarget)
    assert target.field_path.endswith("genre")
    assert any(
        target.field_path in message.value and target.work_id in message.value
        for message in app.warning
    )
    assert not any(button.label == "Build corpus review" for button in app.button)


def test_final_confirmation_is_bound_to_inventory_hash_and_rebuild_invalidates_it() -> None:
    app = _open_guided_review()
    confirmation = _by_label(
        app.checkbox,
        "I reviewed the file-to-work mappings and the documented rights records.",
    )
    assert confirmation.value is False

    confirmation.check().run()

    assert (
        app.session_state[webapp_module._FLOW_CONFIRMATION_HASH_KEY]
        == app.session_state[webapp_module._FLOW_REPORT_KEY].inventory_sha256
    )
    assert any(
        message.value == "Confirmation recorded for this inventory." for message in app.success
    )

    _by_label(
        app.checkbox,
        "I reviewed the file-to-work mappings and the documented rights records.",
    ).uncheck().run()
    assert webapp_module._FLOW_CONFIRMATION_HASH_KEY not in app.session_state.filtered_state

    _by_label(
        app.checkbox,
        "I reviewed the file-to-work mappings and the documented rights records.",
    ).check().run()

    _by_label(app.button, "Edit metadata").click().run()
    app.button(key="guided_build_review").click().run()

    rebuilt_confirmation = _by_label(
        app.checkbox,
        "I reviewed the file-to-work mappings and the documented rights records.",
    )
    assert rebuilt_confirmation.value is False
    assert webapp_module._FLOW_CONFIRMATION_HASH_KEY not in app.session_state.filtered_state


class _Context:
    def __enter__(self) -> _Context:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _DownloadStreamlit:
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.downloads: list[dict[str, Any]] = []

    def subheader(self, *_args: object, **_kwargs: object) -> None:
        return None

    def warning(self, value: str, **_kwargs: object) -> None:
        self.warnings.append(value)

    def columns(self, count: int) -> tuple[_Context, ...]:
        return tuple(_Context() for _ in range(count))

    def download_button(self, *_args: object, **kwargs: Any) -> None:
        self.downloads.append(kwargs)


def test_download_failure_is_visible_and_disables_only_metadata_csv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inventory = _fixture_inventory()
    report = validate_inventory(inventory)
    fake_streamlit = _DownloadStreamlit()

    def reject_export(_inventory: CorpusInventory) -> bytes:
        raise MetadataCsvExportError(MetadataCsvExportErrorCode.RELATIONSHIP_UNRESOLVED)

    monkeypatch.setattr(webapp_module, "st", fake_streamlit)
    monkeypatch.setattr(webapp_module, "export_metadata_csv", reject_export)
    projection = build_review_projection(inventory, report)
    webapp_module._render_downloads(inventory, report, projection)
    empty_result = MetadataCsvImportResult(
        csv_sha256="0" * 64,
        row_count=0,
        blocked=True,
        issues=(),
        inventory=None,
        validation_report=None,
    )
    webapp_module._render_csv_issues(empty_result)
    assert fake_streamlit.warnings == [
        "The metadata CSV cannot be generated safely from the current inventory."
    ]
    assert len(fake_streamlit.downloads) == 5
    assert fake_streamlit.downloads[2]["disabled"] is True
    assert fake_streamlit.downloads[3]["disabled"] is False
    assert fake_streamlit.downloads[4]["disabled"] is False


def test_review_csv_failure_is_visible_and_disables_both_review_exports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inventory = _fixture_inventory()
    report = validate_inventory(inventory)
    projection = build_review_projection(inventory, report)
    fake_streamlit = _DownloadStreamlit()

    def reject_export(_projection: object) -> bytes:
        raise ReviewProjectionError(ReviewProjectionErrorCode.CSV_POLICY_REJECTED)

    monkeypatch.setattr(webapp_module, "st", fake_streamlit)
    monkeypatch.setattr(webapp_module, "export_composition_csv", reject_export)
    webapp_module._render_downloads(inventory, report, projection)
    assert fake_streamlit.warnings == [
        "The review CSV files cannot be generated safely from the current projection."
    ]
    assert len(fake_streamlit.downloads) == 5
    assert fake_streamlit.downloads[2]["disabled"] is False
    assert fake_streamlit.downloads[3]["disabled"] is True
    assert fake_streamlit.downloads[4]["disabled"] is True


def test_review_fails_closed_when_validation_report_is_stale() -> None:
    app = _open_imported_review()
    report = app.session_state[webapp_module._FLOW_REPORT_KEY]
    app.session_state[webapp_module._FLOW_REPORT_KEY] = report.model_copy(
        update={"inventory_sha256": "0" * 64}
    )
    app.run()
    assert [message.value for message in app.error] == [
        "This review no longer matches the documented inventory. Return to Describe and "
        "rebuild it before continuing."
    ]
    assert any("No stylometric analysis has run" in message.value for message in app.info)
