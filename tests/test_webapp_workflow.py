from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pyarrow as pa
import pytest
from streamlit.testing.v1 import AppTest

from delta_lemmata import webapp as webapp_module
from delta_lemmata.corpus import (
    CorpusInventory,
    DateMode,
    DateValue,
    IssueSeverity,
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
    inventory_sha256,
    metadata_csv_template,
    validate_inventory,
)
from delta_lemmata.corpus_health_models import (
    CorpusHealthFinding,
    CorpusHealthFindingCode,
    HealthSeverity,
)
from delta_lemmata.corpus_health_projection import (
    ConfoundDatum,
    CorpusHealthProjectionError,
    CorpusHealthProjectionErrorCode,
    OverlapDatum,
)
from delta_lemmata.prepared_corpus_service import (
    PreparedCorpusError,
    PreparedCorpusErrorCode,
)
from delta_lemmata.preprocessing_models import (
    AnalysisRole,
    OcrStatus,
    ParatextStatus,
)
from delta_lemmata.result_view import (
    BOUNDARIES,
    ResultCellStatus,
    ResultCellV1,
    ResultDocumentV1,
    ResultMatrixV1,
    ResultViewV1,
    classical_mds,
)
from delta_lemmata.stylo_contracts import DistanceMeasure, DocumentRole
from delta_lemmata.web_runtime import WebRuntimeError, WebRuntimeErrorCode
from delta_lemmata.workflow_models import AnalysisScope

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "p004"


def run_app() -> AppTest:
    webapp_module._runtime.clear()
    return AppTest.from_file(str(APP), default_timeout=20).run()


def _by_label(elements: Iterable[Any], label: str) -> Any:
    return next(element for element in elements if element.label == label)


def _all_by_label(elements: Iterable[Any], label: str) -> list[Any]:
    return [element for element in elements if element.label == label]


def _page_title(app: AppTest) -> str:
    if app.title:
        return app.title[0].value
    return app.header[0].value


def _zip_payload(entries: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return output.getvalue()


def _contrast_ratio(foreground: str, background: str) -> float:
    def luminance(value: str) -> float:
        channels = tuple(int(value[index : index + 2], 16) / 255 for index in (1, 3, 5))
        linear = tuple(
            channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        )
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _public_result_view() -> ResultViewV1:
    documents = (
        ResultDocumentV1(key="D01", title="Early work", role=DocumentRole.KNOWN),
        ResultDocumentV1(key="D02", title="Late work", role=DocumentRole.KNOWN),
    )
    cells = tuple(
        ResultCellV1(
            mfw=mfw,
            culling_percent=0,
            distance=DistanceMeasure.CLASSIC_DELTA,
            is_reference=mfw == 500,
            status=ResultCellStatus.COMPLETE,
            error_code=None,
            matrix=ResultMatrixV1(
                document_keys=("D01", "D02"),
                values=((0.0, float(index)), (float(index), 0.0)),
            ),
        )
        for index, mfw in enumerate((100, 300, 500, 1000), start=1)
    )
    return ResultViewV1(
        schema_version="result-view-v1",
        purpose=PurposeId.TEXT_PROXIMITY,
        analysis_scope=AnalysisScope.TRANSDUCTIVE_EXPLORATORY,
        parameter_profile="guided-grid-v1",
        workflow_config_sha256="a" * 64,
        source_result_sha256="b" * 64,
        source_result_outcome="complete",
        analysis_unit="whole_text",
        distance_measure=DistanceMeasure.CLASSIC_DELTA,
        reference_mfw=500,
        visualization_method="classical-mds-v1",
        documents=documents,
        cells=cells,
        interpretation=BOUNDARIES,
    )


def _advance_to_describe(app: AppTest, payload: bytes = b"one text") -> AppTest:
    app.file_uploader[0].upload("one.txt", payload, "text/plain").run()
    app.button(key="corpus_continue").click().run()
    return app.run()


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


def test_review_readiness_detail_uses_the_general_ready_boundary() -> None:
    inventory = SimpleNamespace(purpose=PurposeId.STYLE_OVER_TIME)
    report = SimpleNamespace(
        readiness=SimpleNamespace(
            independent_work_count=6,
            chronology_point_count=3,
            exploratory=False,
        )
    )

    detail = webapp_module._review_readiness_detail(inventory, report)

    assert "Corpus documentation has no blockers" in detail
    assert "Readiness applies only to the selected purpose" in detail
    assert "requires at least six" not in detail


def test_style_over_time_readiness_remains_available_but_explicitly_exploratory() -> None:
    inventory = _fixture_inventory().model_copy(update={"purpose": PurposeId.STYLE_OVER_TIME})
    app = _inject_review(run_app(), inventory)

    rendered = "\n".join(item.value for item in app.markdown)
    assert "Exploratory for Trace Style Over Time" in rendered
    assert 'class="delta-readiness-band is-exploratory"' in rendered
    assert "Delta can continue with this chronology only as exploratory analysis" in rendered
    assert "1 independent work and 1 chronology point" in rendered
    assert "Meeting that rule would still not prove scientific sufficiency" in rendered
    assert "would not yet be supported" not in rendered
    assert app.checkbox[0].disabled is False


def test_style_over_time_marks_three_documented_chronology_points_as_documented() -> None:
    inventory = _three_work_chronology_inventory().model_copy(
        update={"purpose": PurposeId.STYLE_OVER_TIME}
    )
    app = _inject_review(run_app(), inventory)

    rendered = "\n".join(item.value for item in app.markdown)
    assert "3 chronology points" in rendered
    assert "Documented" in rendered
    assert "3 needed for Style Over Time" not in rendered


def test_review_warning_type_count_excludes_blockers_and_information() -> None:
    report = SimpleNamespace(
        issues=(
            SimpleNamespace(code="same-warning", severity=IssueSeverity.WARNING),
            SimpleNamespace(code="same-warning", severity=IssueSeverity.WARNING),
            SimpleNamespace(code="blocker", severity=IssueSeverity.BLOCKER),
            SimpleNamespace(code="information", severity=IssueSeverity.INFORMATION),
        )
    )

    assert webapp_module._review_issue_type_count(report) == 1


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


def _open_two_work_prepare() -> AppTest:
    app = run_app()
    _by_label(app.radio, "Corpus input format").set_value("zip_archive").run()
    app.file_uploader[0].upload(
        "corpus.zip",
        _zip_payload(
            [
                ("early.txt", b"alpha beta gamma delta epsilon"),
                ("late.txt", b"alpha beta gamma zeta eta"),
            ]
        ),
        "application/zip",
    ).run()
    app.button(key="corpus_continue").click().run()
    app.run()
    for author in _all_by_label(app.text_input, "Primary author name"):
        author.input("Carlo Collodi")
    for source in _all_by_label(app.text_input, "Source URL"):
        source.input("https://www.liberliber.it/")
    app.run()
    for rights in _all_by_label(app.selectbox, "Documented rights state"):
        rights.set_value("analysis_only")
    app.run()
    app.button(key="guided_build_review").click().run()
    _by_label(
        app.checkbox,
        "I reviewed the file-to-work mappings and the documented rights records.",
    ).check().run()
    app.button(key="review_continue_prepare").click().run()
    return app


def _open_guided_parameters() -> AppTest:
    app = _open_two_work_prepare()
    app.button(key="prepare_run_check").click().run()
    app.button(key="prepare_continue_parameters").click().run()
    return app.run()


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


def _three_work_chronology_inventory() -> CorpusInventory:
    inventory = _two_work_inventory()
    third_work = inventory.works[0].model_copy(
        update={
            "work_id": "latest_work",
            "title_original": "Latest work",
            "first_publication": DateValue(mode=DateMode.EXACT, start_year=1910),
        }
    )
    third_edition = inventory.editions[0].model_copy(
        update={
            "edition_id": "latest_edition",
            "work_id": "latest_work",
            "edition_date": DateValue(mode=DateMode.EXACT, start_year=1911),
        }
    )
    third_source = inventory.sources[0].model_copy(
        update={"source_id": "latest_source", "edition_id": "latest_edition"}
    )
    third_asset = inventory.assets[0].model_copy(
        update={
            "asset_id": "asset_latest",
            "file_label": "latest.txt",
            "content_sha256": "3" * 64,
            "work_id": "latest_work",
            "edition_id": "latest_edition",
            "source_id": "latest_source",
            "rights_asset_ids": ("asset_latest",),
        }
    )
    third_file = inventory.validated_files[0].model_copy(
        update={"file_label": "latest.txt", "content_sha256": "3" * 64}
    )
    third_rights = inventory.rights[0].model_copy(
        update={"asset_id": "asset_latest", "source_id": "latest_source"}
    )
    return inventory.model_copy(
        update={
            "works": (*inventory.works, third_work),
            "editions": (*inventory.editions, third_edition),
            "sources": (*inventory.sources, third_source),
            "assets": (*inventory.assets, third_asset),
            "validated_files": (*inventory.validated_files, third_file),
            "rights": (*inventory.rights, third_rights),
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

    app.session_state[webapp_module._FLOW_STAGE_KEY] = webapp_module.CorpusSubstage.PREPARE.value
    app.run()
    assert [heading.value for heading in app.header][0] == "Upload the research corpus"

    app.session_state[webapp_module._FLOW_STAGE_KEY] = webapp_module.CorpusSubstage.PARAMETERS.value
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
    _by_label(app.radio, "What do you want to investigate?").set_value(
        PurposeId.GROUP_COMPARISON.value
    ).run()
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
    assert _page_title(app) == "Describe what each text represents"
    assert [message.value for message in app.warning] == [
        "The CSV passed file-safety checks but cannot yet produce a complete inventory."
    ]
    assert not any(button.label == "Review imported metadata" for button in app.button)


def test_valid_import_opens_review_and_supports_edit_and_full_reset() -> None:
    app = _inject_imported_describe(run_app(), PurposeId.TEXT_PROXIMITY)
    app.session_state["review_confirmation_stale"] = True
    _by_label(app.button, "Review imported metadata").click().run()
    assert _page_title(app) == "Review the documented corpus"
    assert "review_confirmation_stale" not in app.session_state.filtered_state
    assert [message.value for message in app.success][-1] == (
        "No corpus-documentation issues were reported."
    )

    _by_label(app.button, "Edit metadata").click().run()
    assert _page_title(app) == "Describe what each text represents"

    app = _inject_imported_describe(run_app(), PurposeId.TEXT_PROXIMITY)
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
    assert _page_title(app) == "Review the documented corpus"
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
    _by_label(app.radio, "Corpus input format").set_value("zip_archive").run()
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
    app.run()

    persisted_mode = _by_label(app.radio, "Corpus input format")
    assert persisted_mode.value == "zip_archive"
    assert persisted_mode.disabled is True

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

    assert _page_title(app) == "Review the documented corpus"
    assert len(_by_label(app.radio, "Select a documented work on the chronology").options) == 2
    rendered = "\n".join(item.value for item in app.markdown)
    assert "<span>Independent works</span><strong>2</strong>" in rendered
    assert rendered.count('data-row-key="work_') >= 2
    state = repr(app.session_state.filtered_state)
    assert "ZIP_CANARY_EARLY" not in state
    assert "ZIP_CANARY_LATE" not in state
    assert "storage_name" not in state


def test_confirmed_corpus_opens_beginner_facing_preparation_decisions() -> None:
    app = _open_two_work_prepare()
    assert _page_title(app) == "Prepare and check the corpus"
    assert [heading.value for heading in app.header] == ["Method boundary"]
    assert len(_all_by_label(app.selectbox, "Analysis role")) == 2
    assert len(_all_by_label(app.selectbox, "OCR status")) == 2
    assert len(_all_by_label(app.selectbox, "Paratext status")) == 2
    assert all(
        control.options == ["Known reference text", "Unknown or focal text"]
        for control in _all_by_label(app.selectbox, "Analysis role")
    )
    captions = "\n".join(item.value for item in app.caption)
    assert "Fixed alpha profile" in "\n".join(item.value for item in app.info)
    assert "Analysis unit: one independent work" in captions
    assert all(
        "OCR means text produced by optical character recognition" in control.help
        for control in _all_by_label(app.selectbox, "OCR status")
    )
    assert "no lemmatization or stemming" in "\n".join(item.value for item in app.info)
    state = repr(app.session_state.filtered_state)
    assert "alpha beta gamma" not in state
    assert "SessionCapability" not in state


def test_preparation_runs_real_health_checks_and_exports_payload_free_evidence() -> None:
    app = _open_two_work_prepare()
    app.button(key="prepare_run_check").click().run()
    assert len(app.exception) == 0
    assert [message.value for message in app.success] == [
        "Computational preflight passed. The prepared corpus can continue to bounded "
        "parameter review."
    ]
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Independent works"] == "2"
    assert metrics["Known references"] == "2"
    assert metrics["Candidate features"] == "7"
    assert metrics["Blockers"] == "0"
    assert [item.label for item in app.download_button] == [
        "Download work-preparation CSV",
        "Download confound-matrix CSV",
        "Download health-findings CSV",
        "Download feature-capacity CSV",
        "Download corpus-health report",
        "Download preparation settings",
        "Download preparation manifest",
        "Download READY receipt",
    ]
    rendered = "\n".join(item.value for item in app.markdown)
    subheaders = [heading.value for heading in app.subheader]
    assert "See what the fixed profile changed" in subheaders
    assert "Review factors that may travel with style" in subheaders
    assert "Check independence and repeated material" in subheaders
    assert "Which MFW settings can this corpus support?" in subheaders
    captions = "\n".join(item.value for item in app.caption)
    assert "This is a computational preflight only" in captions
    assert captions.count("What this does not establish") == 5
    assert "**Flagged pairs**" in rendered
    assert "Preparation completed deterministically" in rendered
    state = repr(app.session_state.filtered_state)
    assert "PreparationOutcome" in state
    assert "AnalysisPreparationReceiptV1" in state
    assert "alpha beta gamma" not in state
    assert "SessionCapability" not in state
    assert "control.sqlite3" not in state


def test_guided_parameter_review_explains_the_complete_fixed_grid() -> None:
    app = _open_guided_parameters()
    assert len(app.exception) == 0
    assert _page_title(app) == "Review what Delta will calculate"
    assert [heading.value for heading in app.header] == ["Method boundary"]
    assert [
        (control.label, control.options, control.value) for control in app.segmented_control
    ] == [("Parameter mode", ["Guided", "Research"], "guided")]
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics == {
        "Comparisons": "4",
        "Display reference": "500 MFW",
        "Culling": "0%",
        "Analysis unit": "Whole text",
    }
    rendered = "\n".join(item.value for item in app.markdown)
    assert "Guided parameter comparison grid" in rendered
    assert all(f'<th scope="row">{mfw}</th>' in rendered for mfw in (100, 300, 500, 1000))
    assert rendered.count("<td>Classic Delta</td>") == 4
    assert rendered.count("<td>Sensitivity check</td>") == 3
    assert rendered.count("<td>Display reference</td>") == 1
    assert rendered.count('<tr data-reference="true">') == 1
    assert [expander.label for expander in app.expander] == ["Understand these settings"]
    captions = "\n".join(item.value for item in app.caption)
    assert "A larger number includes more vocabulary" in captions
    assert "it does not prove authorship" in captions
    assert "not a claim that it is the best result" in captions
    assert [item.label for item in app.download_button] == ["Download resolved parameter record"]
    run_button = app.button(key="parameters_run_analysis")
    assert run_button.disabled is True
    assert "alpha beta gamma" not in repr(app.session_state.filtered_state)


def test_succeeded_analysis_renders_all_cells_and_accessible_result_views(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_guided_parameters()
    result_view = _public_result_view()
    app.session_state[webapp_module._FLOW_JOB_PRESENTATION_KEY] = SimpleNamespace(
        state_id="succeeded",
        title="Analysis complete",
        body="The bounded result is ready.",
    )
    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(
            prepared_corpora=SimpleNamespace(result_view=lambda **_kwargs: result_view)
        ),
    )
    app.run(timeout=40)

    assert len(app.exception) == 0
    assert _page_title(app) == "Explore the relative distances"
    assert [heading.value for heading in app.subheader][-4:] == [
        "Distance heatmap",
        "Distance matrix",
        "Nearest neighbours, including ties",
        "Two-dimensional proximity map",
    ]
    selector = _by_label(app.radio, "View one completed comparison")
    assert selector.value == 500
    assert selector.options == [
        "100 MFW",
        "300 MFW",
        "500 MFW",
        "1000 MFW",
    ]
    rendered = "\n".join(item.value for item in app.markdown)
    assert rendered.count('class="delta-result-cell delta-result-cell-complete"') == 4
    assert all(f'data-mfw="{mfw}"' in rendered for mfw in (100, 300, 500, 1000))
    assert "Classic Delta distance matrix" in rendered
    assert "Nearest-neighbour table with tolerance-aware ties" in rendered
    assert "MDS coordinate table" in rendered
    assert "Method key" in rendered
    assert "How to read this map" in rendered
    assert rendered.count("What this does not show") == 1
    charts = app.get("vega_lite_chart")
    assert len(charts) == 2
    heatmap = json.loads(charts[0].proto.spec)
    heatmap_color = heatmap["layer"][0]["encoding"]["color"]
    assert heatmap_color["condition"] == {
        "test": "datum.reference === datum.compared",
        "value": "#ffffff",
    }
    assert heatmap_color["value"] == "#a9dcc7"
    assert "scale" not in heatmap_color
    mds = json.loads(charts[1].proto.spec)
    point_encoding = mds["layer"][0]["encoding"]
    assert point_encoding["x"]["scale"]["domain"] == point_encoding["y"]["scale"]["domain"]
    assert point_encoding["color"]["field"] == "role"
    assert point_encoding["color"]["legend"] is None
    assert point_encoding["shape"]["field"] == "role"
    assert point_encoding["shape"]["scale"]["range"] == ["circle", "diamond"]
    assert mds["width"] == mds["height"] == 360
    assert "Known reference text" in rendered
    assert "Unknown holdout" in rendered
    assert [button.label for button in app.download_button][-1] == (
        "Download canonical result record"
    )
    state = repr(app.session_state.filtered_state)
    assert "ResultViewV1" not in state
    assert "feature-" not in state


def test_partial_result_marks_unavailable_cell_without_hiding_completed_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_guided_parameters()
    complete = _public_result_view()
    unavailable = complete.cells[-1].model_copy(
        update={
            "status": ResultCellStatus.FAILED,
            "error_code": "fit_unavailable",
            "matrix": None,
        }
    )
    partial = ResultViewV1.model_validate(
        {
            **complete.model_dump(mode="python"),
            "source_result_outcome": "partial",
            "cells": (*complete.cells[:-1], unavailable),
        }
    )
    app.session_state[webapp_module._FLOW_JOB_PRESENTATION_KEY] = SimpleNamespace(
        state_id="succeeded",
        title="Analysis complete",
        body="The bounded result is ready.",
    )
    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(
            prepared_corpora=SimpleNamespace(result_view=lambda **_kwargs: partial)
        ),
    )
    app.run(timeout=40)

    assert len(app.exception) == 0
    assert "At least one comparison could not be completed" in "\n".join(
        message.value for message in app.warning
    )
    selector = _by_label(app.radio, "View one completed comparison")
    assert selector.options == [
        "100 MFW",
        "300 MFW",
        "500 MFW",
    ]
    rendered = "\n".join(item.value for item in app.markdown)
    assert rendered.count('class="delta-result-cell ') == 4
    assert 'class="delta-result-cell delta-result-cell-failed"' in rendered
    assert 'data-mfw="1000" data-status="failed"' in rendered
    assert [expander.label for expander in app.expander if "run details" in expander.label] == [
        "Run finished · 3 of 4 comparisons produced matrices · run details"
    ]


@pytest.mark.parametrize(
    ("status", "error_code"),
    (
        (ResultCellStatus.FAILED, "fit_unavailable"),
        (ResultCellStatus.NOT_ENOUGH_FEATURES, "not_enough_features"),
    ),
)
def test_unavailable_reference_opens_first_completed_cell_with_an_explicit_notice(
    monkeypatch: pytest.MonkeyPatch,
    status: ResultCellStatus,
    error_code: str,
) -> None:
    app = _open_guided_parameters()
    complete = _public_result_view()
    unavailable_reference = complete.cells[2].model_copy(
        update={"status": status, "error_code": error_code, "matrix": None}
    )
    cells = (*complete.cells[:2], unavailable_reference, complete.cells[3])
    partial = ResultViewV1.model_validate(
        {
            **complete.model_dump(mode="python"),
            "source_result_outcome": "partial",
            "cells": cells,
        }
    )
    app.session_state[webapp_module._FLOW_JOB_PRESENTATION_KEY] = SimpleNamespace(
        state_id="succeeded",
        title="Analysis complete",
        body="The bounded result is ready.",
    )
    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(
            prepared_corpora=SimpleNamespace(result_view=lambda **_kwargs: partial)
        ),
    )

    app.run(timeout=40)

    selector = _by_label(app.radio, "View one completed comparison")
    assert selector.value == 100
    messages = "\n".join(message.value for message in app.info)
    assert "500 MFW was unavailable" in messages
    assert "display fallback, not a best-result selection" in messages
    assert "500 MFW opens first" not in messages


def test_succeeded_result_readback_failure_is_visible_and_content_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_guided_parameters()
    app.session_state[webapp_module._FLOW_JOB_PRESENTATION_KEY] = SimpleNamespace(
        state_id="succeeded",
        title="Analysis complete",
        body="The bounded result is ready.",
    )

    def unavailable(**_kwargs: object) -> object:
        raise PreparedCorpusError(PreparedCorpusErrorCode.RESULT_NOT_AVAILABLE)

    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(prepared_corpora=SimpleNamespace(result_view=unavailable)),
    )
    app.run()

    assert len(app.exception) == 0
    assert "The verified result view is not available." in "\n".join(
        message.value for message in app.error
    )


def test_result_helpers_reject_missing_ready_bindings_and_unavailable_matrices() -> None:
    inventory = _fixture_inventory()
    with pytest.raises(ValueError, match="READY receipt"):
        webapp_module._result_descriptors(
            inventory,
            SimpleNamespace(ready_receipt=None),  # type: ignore[arg-type]
        )
    missing_work = SimpleNamespace(
        ready_receipt=SimpleNamespace(
            ordered_documents=(
                SimpleNamespace(
                    document_id="doc_" + "a" * 64,
                    work_id="work_" + "f" * 64,
                    analysis_role=AnalysisRole.KNOWN,
                ),
            )
        )
    )
    with pytest.raises(ValueError, match="descriptor binding failed"):
        webapp_module._result_descriptors(
            inventory,
            missing_work,  # type: ignore[arg-type]
        )

    unavailable = ResultCellV1(
        mfw=100,
        culling_percent=0,
        distance=DistanceMeasure.CLASSIC_DELTA,
        is_reference=False,
        status=ResultCellStatus.FAILED,
        error_code="fit_unavailable",
        matrix=None,
    )
    view = _public_result_view()
    with pytest.raises(ValueError, match="distance matrix is unavailable"):
        webapp_module._render_distance_matrix(unavailable, view)
    with pytest.raises(ValueError, match="distance matrix is unavailable"):
        webapp_module._render_heatmap(unavailable, view)


def test_result_charts_bypass_pandas_string_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        webapp_module.st,
        "vega_lite_chart",
        lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(webapp_module.st, "markdown", lambda *_args, **_kwargs: None)
    view = _public_result_view()
    cell = view.cells[0]

    webapp_module._render_heatmap(cell, view)
    webapp_module._render_mds(cell, view)

    assert len(calls) == 2
    tables = [call["spec"]["data"]["values"] for call in calls]  # type: ignore[index]
    assert all(isinstance(table, pa.Table) for table in tables)
    assert tables[0].column_names == [
        "reference",
        "reference_title",
        "compared",
        "compared_title",
        "distance",
        "distance_label",
    ]
    assert tables[1].column_names == ["key", "title", "role", "x", "y"]
    expected_heatmap = [
        {
            "reference": row_key,
            "reference_title": next(
                document.title for document in view.documents if document.key == row_key
            ),
            "compared": column_key,
            "compared_title": next(
                document.title for document in view.documents if document.key == column_key
            ),
            "distance": float(distance),
            "distance_label": f"{float(distance):.6f}",
        }
        for row_key, row in zip(cell.matrix.document_keys, cell.matrix.values, strict=True)
        for column_key, distance in zip(cell.matrix.document_keys, row, strict=True)
    ]
    assert tables[0].to_pylist() == expected_heatmap
    documents = {document.key: document for document in view.documents}
    assert tables[1].to_pylist() == [
        {
            "key": point.document_key,
            "title": documents[point.document_key].title,
            "role": documents[point.document_key].role.value,
            "x": point.x,
            "y": point.y,
        }
        for point in classical_mds(cell)
    ]


def test_review_labels_cover_nested_fields_and_all_issue_entity_types() -> None:
    assert webapp_module._field_label("") == ""
    assert webapp_module._field_label("works[0].date.start_year") == "Date: Start Year"

    inventory = _fixture_inventory()
    author = inventory.authors[0]
    work = inventory.works[0]
    edition = inventory.editions[0]
    source = inventory.sources[0]
    asset = inventory.assets[0]

    def issue(entity_type: object, entity_id: str | None) -> SimpleNamespace:
        return SimpleNamespace(entity_type=entity_type, entity_id=entity_id)

    assert webapp_module._issue_affected_label(issue("work", None), inventory) == "Work"
    assert (
        webapp_module._issue_affected_label(
            issue(SimpleNamespace(value="author"), author.author_id), inventory
        )
        == author.display_name
    )
    assert webapp_module._issue_affected_label(issue("author", "missing"), inventory) == ("missing")
    assert webapp_module._issue_affected_label(issue("work", work.work_id), inventory) == (
        work.title_original
    )
    assert webapp_module._issue_affected_label(issue("work", "missing"), inventory) == ("missing")
    assert (
        webapp_module._issue_affected_label(issue("edition", edition.edition_id), inventory)
        == f"{work.title_original} · {edition.edition_label}"
    )
    assert webapp_module._issue_affected_label(issue("edition", "missing"), inventory) == (
        "missing"
    )
    assert webapp_module._issue_affected_label(issue("source", source.source_id), inventory) == (
        source.title
    )
    assert webapp_module._issue_affected_label(issue("source", "missing"), inventory) == ("missing")
    assert webapp_module._issue_affected_label(issue("asset", asset.asset_id), inventory) == (
        asset.file_label
    )
    assert webapp_module._issue_affected_label(issue("rights", "missing"), inventory) == ("missing")
    assert webapp_module._issue_affected_label(issue("field", "custom"), inventory) == "custom"

    orphan_inventory = SimpleNamespace(
        authors=(),
        works=(),
        editions=(
            SimpleNamespace(
                edition_id="orphan-edition",
                work_id="orphan-work",
                edition_label="Unknown edition",
            ),
        ),
        sources=(),
        assets=(),
    )
    assert (
        webapp_module._issue_affected_label(issue("edition", "orphan-edition"), orphan_inventory)
        == "orphan-work · Unknown edition"
    )


def test_result_renderers_cover_variable_scale_ties_and_zero_mds_extent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    charts: list[dict[str, object]] = []
    markup: list[str] = []
    monkeypatch.setattr(
        webapp_module.st,
        "vega_lite_chart",
        lambda **kwargs: charts.append(kwargs),
    )
    monkeypatch.setattr(
        webapp_module.st,
        "markdown",
        lambda value, *_args, **_kwargs: markup.append(value),
    )
    documents = (
        ResultDocumentV1(key="D01", title="First", role=DocumentRole.KNOWN),
        ResultDocumentV1(key="D02", title="Second", role=DocumentRole.KNOWN),
        ResultDocumentV1(key="D03", title="Third", role=DocumentRole.UNKNOWN),
    )
    varied = ResultCellV1(
        mfw=100,
        culling_percent=0,
        distance=DistanceMeasure.CLASSIC_DELTA,
        is_reference=False,
        status=ResultCellStatus.COMPLETE,
        error_code=None,
        matrix=ResultMatrixV1(
            document_keys=("D01", "D02", "D03"),
            values=((0.0, 1.0, 1.0), (1.0, 0.0, 2.0), (1.0, 2.0, 0.0)),
        ),
    )
    view = SimpleNamespace(documents=documents)
    webapp_module._render_heatmap(varied, view)
    webapp_module._render_nearest_neighbours(varied, view)

    heatmap = charts[0]["spec"]
    heatmap_color = heatmap["layer"][0]["encoding"]["color"]
    heatmap_stroke = heatmap["layer"][0]["encoding"]["stroke"]
    heatmap_stroke_width = heatmap["layer"][0]["encoding"]["strokeWidth"]
    assert heatmap_color["scale"]["domain"] == [1.0, 2.0]
    assert heatmap_color["scale"]["type"] == "quantize"
    assert heatmap_color["scale"]["range"] == [
        "#f4faf7",
        "#d7efe5",
        "#a9dcc7",
        "#6fbf9f",
        "#297658",
        "#0a5443",
    ]
    assert heatmap_stroke == {
        "condition": {
            "test": "datum.reference === datum.compared",
            "value": "#596762",
        },
        "value": "#d5ddda",
    }
    assert heatmap_stroke_width == {
        "condition": {
            "test": "datum.reference === datum.compared",
            "value": 1.5,
        },
        "value": 0.5,
    }
    contrast_condition = heatmap["layer"][1]["encoding"]["color"]["condition"][1]
    assert float(contrast_condition["test"].removeprefix("datum.distance >= ")) == pytest.approx(
        1.0 + (4 / 6)
    )
    assert "<td>2 texts</td>" in "\n".join(markup)

    diagonal_residue = varied.model_copy(
        update={
            "matrix": ResultMatrixV1(
                document_keys=("D01", "D02", "D03"),
                values=(
                    (5e-13, 0.0, 2.0),
                    (0.0, 0.0, 1.0),
                    (2.0, 1.0, 0.0),
                ),
            )
        }
    )
    webapp_module._render_heatmap(diagonal_residue, view)
    residue_color = charts[-1]["spec"]["layer"][0]["encoding"]["color"]
    assert residue_color["scale"]["domain"] == [0.0, 2.0]

    constant_distances = varied.model_copy(
        update={
            "matrix": ResultMatrixV1(
                document_keys=("D01", "D02", "D03"),
                values=((0.0, 1.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 0.0)),
            )
        }
    )
    webapp_module._render_heatmap(constant_distances, view)
    constant_color = charts[-1]["spec"]["layer"][0]["encoding"]["color"]
    assert constant_color == {
        "condition": {
            "test": "datum.reference === datum.compared",
            "value": "#ffffff",
        },
        "value": "#a9dcc7",
    }
    assert charts[-1]["spec"]["layer"][1]["encoding"]["color"]["condition"][1] == {
        "test": "false",
        "value": "#ffffff",
    }

    zero_extent = ResultCellV1(
        mfw=100,
        culling_percent=0,
        distance=DistanceMeasure.CLASSIC_DELTA,
        is_reference=False,
        status=ResultCellStatus.COMPLETE,
        error_code=None,
        matrix=ResultMatrixV1(
            document_keys=("D01", "D02"),
            values=((0.0, 0.0), (0.0, 0.0)),
        ),
    )
    webapp_module._render_mds(zero_extent, SimpleNamespace(documents=documents[:2]))
    mds = charts[-1]["spec"]
    x_domain = mds["layer"][0]["encoding"]["x"]["scale"]["domain"]
    y_domain = mds["layer"][0]["encoding"]["y"]["scale"]["domain"]
    assert x_domain == y_domain == [-1.08, 1.08]


def test_heatmap_labels_are_contrasted_and_hidden_below_the_a51_cell_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ramp = ("#f4faf7", "#d7efe5", "#a9dcc7", "#6fbf9f", "#297658", "#0a5443")
    text_colors = (
        "#1a1a1a",
        "#1a1a1a",
        "#1a1a1a",
        "#1a1a1a",
        "#ffffff",
        "#ffffff",
    )
    assert all(
        _contrast_ratio(text_color, fill) >= 4.5
        for text_color, fill in zip(text_colors, ramp, strict=True)
    )

    charts: list[dict[str, object]] = []
    monkeypatch.setattr(
        webapp_module.st,
        "vega_lite_chart",
        lambda **kwargs: charts.append(kwargs),
    )
    document_count = webapp_module._HEATMAP_TEXT_MAX_DOCUMENTS + 1
    keys = tuple(f"D{index:02d}" for index in range(1, document_count + 1))
    documents = tuple(
        ResultDocumentV1(key=key, title=f"Text {index}", role=DocumentRole.KNOWN)
        for index, key in enumerate(keys, start=1)
    )
    values = tuple(
        tuple(
            0.0 if row == column else float(abs(row - column) + 1)
            for column in range(document_count)
        )
        for row in range(document_count)
    )
    cell = ResultCellV1(
        mfw=100,
        culling_percent=0,
        distance=DistanceMeasure.CLASSIC_DELTA,
        is_reference=False,
        status=ResultCellStatus.COMPLETE,
        error_code=None,
        matrix=ResultMatrixV1(document_keys=keys, values=values),
    )

    webapp_module._render_heatmap(cell, SimpleNamespace(documents=documents))

    spec = charts[0]["spec"]
    assert len(spec["layer"]) == 1
    assert spec["layer"][0]["encoding"]["tooltip"][-1]["field"] == "distance_label"
    assert spec["layer"][0]["encoding"]["stroke"]["condition"]["value"] == "#596762"


def test_research_parameter_mode_is_visibly_locked() -> None:
    app = _open_guided_parameters()
    _by_label(app.segmented_control, "Parameter mode").set_value("research").run()
    assert [message.value for message in app.warning] == [
        "Research Mode is not available in this public alpha."
    ]
    assert not any(button.label == "Run the four comparisons" for button in app.button)
    assert [button.label for button in app.button] == ["Back to corpus preparation"]
    app.button(key="p008_back_prepare_research").click().run()
    app.run()
    assert _page_title(app) == "Prepare and check the corpus"


def test_guided_parameter_review_can_return_to_preparation() -> None:
    app = _open_guided_parameters()
    app.button(key="p008_back_prepare").click().run()
    app.run()
    assert _page_title(app) == "Prepare and check the corpus"


def test_invalid_parameter_binding_fails_closed_and_returns_to_preparation() -> None:
    app = _open_guided_parameters()
    annotations = app.session_state[webapp_module._FLOW_ANNOTATIONS_KEY]
    invalid_annotations = annotations.model_copy(
        update={
            "annotations": tuple(
                annotation.model_copy(update={"analysis_role": AnalysisRole.UNKNOWN})
                for annotation in annotations.annotations
            )
        }
    )
    app.session_state[webapp_module._FLOW_ANNOTATIONS_KEY] = invalid_annotations
    app.run()
    assert [message.value for message in app.error] == [
        "The resolved parameter record no longer matches this documented corpus. Return to "
        "preparation and try again."
    ]
    assert [title.value for title in app.title] == ["Review what Delta will calculate"]
    app.button(key="p008_back_prepare_invalid").click().run()
    app.run()
    assert _page_title(app) == "Prepare and check the corpus"


@pytest.mark.parametrize(
    ("state_id", "title", "role"),
    [
        ("queued", "Analysis queued", "status"),
        ("failed", "Analysis failed", "alert"),
        ("timed_out", "Analysis timed out", "alert"),
        ("crashed", "Analysis stopped unexpectedly", "alert"),
    ],
)
def test_parameter_review_presents_active_and_failed_job_states(
    state_id: str,
    title: str,
    role: str,
) -> None:
    app = _open_guided_parameters()
    app.session_state[webapp_module._FLOW_JOB_PRESENTATION_KEY] = SimpleNamespace(
        state_id=state_id,
        title=title,
        body="Content-free lifecycle detail.",
    )
    app.run()
    markup = "\n".join(item.value for item in app.markdown)
    assert title in markup
    assert f'role="{role}"' in markup
    assert 'aria-atomic="true"' in markup
    if state_id in webapp_module._RECOVERABLE_JOB_STATES:
        assert "create a new private corpus preparation" in markup
        assert app.button(key="analysis_start_over").label == (
            "Start over with this research purpose"
        )
    else:
        assert "Content-free lifecycle detail." in markup
    assert not any(button.label == "Run the four comparisons" for button in app.button)


def test_analysis_status_markup_escapes_content_and_binds_live_region_semantics() -> None:
    markup = webapp_module._analysis_status_markup(
        title="Queue <title>",
        body="Wait & retry",
        reference='Status "reference"',
        alert=False,
    )

    assert 'role="status"' in markup
    assert 'aria-live="polite"' in markup
    assert 'aria-atomic="true"' in markup
    assert "Queue &lt;title&gt;" in markup
    assert "Wait &amp; retry" in markup
    assert "Status &quot;reference&quot;" in markup


def test_confirmed_guided_grid_is_admitted_and_run_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_guided_parameters()
    lifecycle_events: list[str] = []

    class RecordingPreparedCorpora:
        admitted: dict[str, object] | None = None
        published: object | None = None
        status_calls = 0

        def admit_once(self, **kwargs: object) -> None:
            self.admitted = dict(kwargs)

        def scientific_result(self, **_kwargs: object) -> SimpleNamespace:
            if self.admitted is None:
                raise PreparedCorpusError(PreparedCorpusErrorCode.RESULT_NOT_AVAILABLE)
            return SimpleNamespace(result=object(), sha256="a" * 64)

        def publish_result_view(self, **kwargs: object) -> None:
            self.published = kwargs["view"]
            lifecycle_events.append("publish")

        def result_view(self, **_kwargs: object) -> object:
            return self.published

        def status(self, **_kwargs: object) -> SimpleNamespace:
            self.status_calls += 1
            lifecycle_events.append("status")
            return SimpleNamespace(
                state_id="succeeded",
                title="Analysis complete",
                body="The run completed and its temporary inputs were removed.",
            )

    class RecordingAnalyses:
        run_calls = 0

        def run_until(self, *, expected_job_id: str) -> SimpleNamespace:
            self.run_calls += 1
            return SimpleNamespace(job_id=expected_job_id)

    prepared = RecordingPreparedCorpora()
    analyses = RecordingAnalyses()
    maintenance_calls = 0
    rendered: list[object] = []

    def maintain() -> None:
        nonlocal maintenance_calls
        maintenance_calls += 1
        lifecycle_events.append("maintain")

    def run_analysis_once(
        *,
        expected_job_id: str,
        admit_analysis: object,
        resume_result: object,
        finalize_result: object,
        present_result: object,
    ) -> object:
        assert resume_result() is False  # type: ignore[operator]
        admit_analysis()  # type: ignore[operator]
        analyses.run_until(expected_job_id=expected_job_id)
        finalize_result()  # type: ignore[operator]
        maintain()
        return present_result()  # type: ignore[operator]

    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(
            prepared_corpora=prepared,
            run_analysis_once=run_analysis_once,
        ),
    )
    monkeypatch.setattr(
        webapp_module,
        "project_result_view",
        lambda **_kwargs: "verified-public-view",
    )
    monkeypatch.setattr(webapp_module, "_render_result_view", rendered.append)

    app.checkbox(key="p008_parameter_confirmation").check().run()
    assert app.button(key="parameters_run_analysis").disabled is False
    app.button(key="parameters_run_analysis").click().run()

    assert analyses.run_calls == 1
    assert maintenance_calls == 1
    assert prepared.status_calls == 1
    assert prepared.published == "verified-public-view"
    assert lifecycle_events == ["publish", "maintain", "status"]
    assert rendered and set(rendered) == {"verified-public-view"}
    assert prepared.admitted is not None
    config = prepared.admitted["resolved_workflow_config"]
    assert config.known_work_count == 2
    assert config.unknown_work_count == 0
    assert [cell.mfw for cell in config.cells] == [100, 300, 500, 1000]
    assert app.session_state[webapp_module._FLOW_STAGE_KEY] == (
        webapp_module.CorpusSubstage.PARAMETERS.value
    )
    assert app.session_state[webapp_module._FLOW_JOB_PRESENTATION_KEY].state_id == "succeeded"
    state = repr(app.session_state.filtered_state)
    assert "alpha beta gamma" not in state
    assert "SessionCapability" not in state


def test_guided_run_resumes_an_existing_result_without_readmission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_guided_parameters()
    events: list[str] = []

    class ResumablePreparedCorpora:
        @staticmethod
        def admit_once(**_kwargs: object) -> None:
            events.append("unexpected-admit")

        @staticmethod
        def scientific_result(**_kwargs: object) -> SimpleNamespace:
            events.append("scientific")
            return SimpleNamespace(result=object(), sha256="a" * 64)

        @staticmethod
        def publish_result_view(**_kwargs: object) -> None:
            events.append("publish")

        @staticmethod
        def status(**_kwargs: object) -> SimpleNamespace:
            events.append("status")
            return SimpleNamespace(
                state_id="succeeded",
                title="Analysis complete",
                body="The run completed and its temporary inputs were removed.",
            )

        @staticmethod
        def result_view(**_kwargs: object) -> str:
            return "resumed-public-view"

    prepared = ResumablePreparedCorpora()

    def run_analysis_once(**callbacks: object) -> object:
        assert callbacks["resume_result"]() is True  # type: ignore[operator]
        events.append("maintain")
        return callbacks["present_result"]()  # type: ignore[operator]

    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(
            prepared_corpora=prepared,
            run_analysis_once=run_analysis_once,
        ),
    )
    monkeypatch.setattr(webapp_module, "project_result_view", lambda **_kwargs: object())

    app.checkbox(key="p008_parameter_confirmation").check().run()
    app.button(key="parameters_run_analysis").click().run()

    assert events == ["scientific", "publish", "maintain", "status"]
    assert app.session_state[webapp_module._FLOW_JOB_PRESENTATION_KEY].state_id == "succeeded"


def test_guided_run_reuses_an_already_queued_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_guided_parameters()
    events: list[str] = []

    class QueuedPreparedCorpora:
        @staticmethod
        def scientific_result(**_kwargs: object) -> None:
            events.append("scientific")
            raise PreparedCorpusError(PreparedCorpusErrorCode.RESULT_NOT_AVAILABLE)

        @staticmethod
        def admit_once(**_kwargs: object) -> None:
            events.append("reused-admission")
            raise PreparedCorpusError(PreparedCorpusErrorCode.ADMISSION_REUSED)

        @staticmethod
        def status(**_kwargs: object) -> SimpleNamespace:
            events.append("status")
            return SimpleNamespace(
                state_id="queued",
                title="Analysis queued",
                body="The same job remains queued.",
            )

    prepared = QueuedPreparedCorpora()

    def run_analysis_once(**callbacks: object) -> object:
        assert callbacks["resume_result"]() is False  # type: ignore[operator]
        queued = callbacks["admit_analysis"]()  # type: ignore[operator]
        assert queued.state_id == "queued"
        return SimpleNamespace(
            state_id="succeeded",
            title="Analysis complete",
            body="The queued job completed.",
        )

    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(
            prepared_corpora=prepared,
            run_analysis_once=run_analysis_once,
        ),
    )
    app.checkbox(key="p008_parameter_confirmation").check().run()
    app.button(key="parameters_run_analysis").click().run()

    assert events == ["scientific", "reused-admission", "status"]
    assert app.session_state[webapp_module._FLOW_JOB_PRESENTATION_KEY].state_id == "succeeded"


@pytest.mark.parametrize("terminal_state", ["failed", "timed_out", "crashed"])
def test_guided_run_offers_a_clean_start_after_reused_terminal_admission(
    monkeypatch: pytest.MonkeyPatch,
    terminal_state: str,
) -> None:
    app = _open_guided_parameters()
    events: list[str] = []

    class FailedPreparedCorpora:
        @staticmethod
        def scientific_result(**_kwargs: object) -> None:
            raise PreparedCorpusError(PreparedCorpusErrorCode.RESULT_NOT_AVAILABLE)

        @staticmethod
        def admit_once(**_kwargs: object) -> None:
            raise PreparedCorpusError(PreparedCorpusErrorCode.ADMISSION_REUSED)

        @staticmethod
        def status(**_kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(
                state_id=terminal_state,
                title="Analysis run ended",
                body="The ended run cannot be reused.",
                support_reference=None,
            )

    class Materializations:
        @staticmethod
        def cleanup(**_kwargs: object) -> None:
            events.append("cleanup")

    def run_analysis_once(**callbacks: object) -> object:
        assert callbacks["resume_result"]() is False  # type: ignore[operator]
        return callbacks["admit_analysis"]()  # type: ignore[operator]

    runtime = SimpleNamespace(
        prepared_corpora=FailedPreparedCorpora(),
        materializations=Materializations(),
        run_analysis_once=run_analysis_once,
    )
    monkeypatch.setattr(webapp_module, "_runtime", lambda: runtime)
    app.checkbox(key="p008_parameter_confirmation").check().run()
    app.button(key="parameters_run_analysis").click().run()

    markup = "\n".join(item.value for item in app.markdown)
    assert 'role="alert"' in markup
    assert "Analysis run ended" in markup
    assert "create a new private corpus preparation" in markup
    app.button(key="analysis_start_over").click().run()
    assert events == ["cleanup"]
    assert app.session_state[webapp_module._FLOW_STAGE_KEY] == "upload"
    assert webapp_module._FLOW_MATERIALIZATION_KEY not in app.session_state


def test_analysis_not_ready_explains_how_to_continue_the_same_queued_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_guided_parameters()

    def run_analysis_once(**_callbacks: object) -> object:
        raise WebRuntimeError(WebRuntimeErrorCode.ANALYSIS_NOT_READY)

    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(
            prepared_corpora=object(),
            run_analysis_once=run_analysis_once,
        ),
    )
    app.checkbox(key="p008_parameter_confirmation").check().run()
    app.button(key="parameters_run_analysis").click().run()

    markup = "\n".join(item.value for item in app.markdown)
    assert 'role="status"' in markup
    assert 'aria-live="polite"' in markup
    assert 'aria-atomic="true"' in markup
    assert "Your analysis remains in the queue." in markup
    assert "you do not need to upload the texts again" in markup
    assert "Status reference: WEB_RUNTIME_ANALYSIS_NOT_READY" in markup
    assert "Rejection reference" not in markup
    assert [message.value for message in app.error] == []
    assert app.button(key="parameters_run_analysis").disabled is False


def test_non_queue_runtime_failure_keeps_the_generic_fail_closed_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_guided_parameters()

    def run_analysis_once(**_callbacks: object) -> object:
        raise WebRuntimeError(WebRuntimeErrorCode.MAINTENANCE_FAILED)

    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(
            prepared_corpora=object(),
            run_analysis_once=run_analysis_once,
        ),
    )
    app.checkbox(key="p008_parameter_confirmation").check().run()
    app.button(key="parameters_run_analysis").click().run()

    assert [message.value for message in app.error] == [
        "Delta could not complete this bounded analysis safely. No partial result is presented."
    ]
    assert "WEB_RUNTIME_MAINTENANCE_FAILED" in "\n".join(item.value for item in app.caption)


def test_parameter_resume_failure_is_stable_and_content_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_guided_parameters()

    class RejectingPreparedCorpora:
        @staticmethod
        def scientific_result(**_kwargs: object) -> None:
            raise PreparedCorpusError(PreparedCorpusErrorCode.OPERATION_FAILED)

    def run_analysis_once(**callbacks: object) -> object:
        return callbacks["resume_result"]()  # type: ignore[operator]

    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(
            prepared_corpora=RejectingPreparedCorpora(),
            run_analysis_once=run_analysis_once,
        ),
    )
    app.checkbox(key="p008_parameter_confirmation").check().run()
    app.button(key="parameters_run_analysis").click().run()

    assert [message.value for message in app.error] == [
        "Delta could not complete this bounded analysis safely. No partial result is presented."
    ]
    captions = "\n".join(item.value for item in app.caption)
    assert "P007_PREPARED_CORPUS_OPERATION_FAILED" in captions


def test_parameter_admission_failure_is_stable_and_content_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_guided_parameters()

    class RejectingPreparedCorpora:
        @staticmethod
        def admit_once(**_kwargs: object) -> None:
            raise PreparedCorpusError(PreparedCorpusErrorCode.OPERATION_FAILED)

    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(
            prepared_corpora=RejectingPreparedCorpora(),
            run_analysis_once=lambda **kwargs: kwargs["admit_analysis"](),
        ),
    )
    app.checkbox(key="p008_parameter_confirmation").check().run()
    app.button(key="parameters_run_analysis").click().run()

    assert [message.value for message in app.error] == [
        "Delta could not complete this bounded analysis safely. No partial result is presented."
    ]
    captions = "\n".join(item.value for item in app.caption)
    assert "P007_PREPARED_CORPUS_OPERATION_FAILED" in captions
    assert "alpha beta gamma" not in captions


def test_parameter_configuration_failure_does_not_echo_exception_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_guided_parameters()

    class RejectingPreparedCorpora:
        @staticmethod
        def admit_once(**_kwargs: object) -> None:
            raise ValueError("PRIVATE_PARAMETER_CANARY")

    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(
            prepared_corpora=RejectingPreparedCorpora(),
            run_analysis_once=lambda **kwargs: kwargs["admit_analysis"](),
        ),
    )
    app.checkbox(key="p008_parameter_confirmation").check().run()
    app.button(key="parameters_run_analysis").click().run()

    assert [message.value for message in app.error] == [
        "The resolved parameter record no longer matches this documented corpus. Return to "
        "preparation and try again."
    ]
    rendered = repr(app)
    assert "PRIVATE_PARAMETER_CANARY" not in rendered


def test_one_known_work_is_blocked_with_an_explanation_and_can_restart() -> None:
    app = _open_guided_review()
    _by_label(
        app.checkbox,
        "I reviewed the file-to-work mappings and the documented rights records.",
    ).check().run()
    app.button(key="review_continue_prepare").click().run()
    app.button(key="prepare_run_check").click().run()
    assert [message.value for message in app.error] == [
        "Computational preflight found one or more blockers. No analysis request was created."
    ]
    rendered = "\n".join(item.value for item in app.markdown)
    assert "Too few known reference works" in rendered
    assert "at least two independent known works" in "\n".join(item.value for item in app.caption)
    _by_label(app.button, "Start again with revised files").click().run()
    assert [heading.value for heading in app.header][0] == "Upload the research corpus"


def test_preparation_confirmation_and_back_navigation_fail_closed() -> None:
    app = _open_two_work_prepare()
    del app.session_state[webapp_module._FLOW_CONFIRMATION_HASH_KEY]
    app.run()
    assert [message.value for message in app.warning] == [
        "Corpus documentation changed or is not confirmed. Return to Review and confirm the "
        "current inventory before preparation."
    ]
    _by_label(app.button, "Back to corpus review").click().run()
    assert _page_title(app) == "Review the documented corpus"

    app = _open_two_work_prepare()
    _by_label(app.button, "Back to corpus review").click().run()
    assert _page_title(app) == "Review the documented corpus"


def test_review_explains_when_the_private_temporary_corpus_is_missing() -> None:
    app = _inject_review(run_app(), _fixture_inventory())
    _by_label(
        app.checkbox,
        "I reviewed the file-to-work mappings and the documented rights records.",
    ).check().run()
    assert [message.value for message in app.warning] == [
        "The temporary corpus is no longer attached to this browser session. Start again "
        "with the same files; the documentation package can still be downloaded first."
    ]


def test_group_preparation_uses_known_references_only() -> None:
    app = _open_two_work_prepare()
    inventory = app.session_state[webapp_module._FLOW_INVENTORY_KEY]
    grouped = inventory.model_copy(
        update={
            "purpose": PurposeId.GROUP_COMPARISON,
            "works": tuple(
                work.model_copy(update={"group_label": f"group-{index}"})
                for index, work in enumerate(inventory.works, start=1)
            ),
        }
    )
    report = validate_inventory(grouped)
    assert report.blocked is False
    app.session_state[webapp_module._FLOW_INVENTORY_KEY] = grouped
    app.session_state[webapp_module._FLOW_REPORT_KEY] = report
    app.session_state[webapp_module._FLOW_CONFIRMATION_HASH_KEY] = inventory_sha256(grouped)
    app.run()
    assert all(
        control.options == ["Known reference text"]
        for control in _all_by_label(app.selectbox, "Analysis role")
    )


def test_finding_measure_and_measure_free_rendering_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    finding = CorpusHealthFinding(
        finding_id="finding_" + "1" * 64,
        code=CorpusHealthFindingCode.PREPARATION_SUMMARY,
        severity=HealthSeverity.NOTE,
    )
    measured = finding.model_copy(
        update={
            "observed_count": 3,
            "threshold_count": 2,
            "observed_ratio": 0.75,
            "threshold_ratio": 0.5,
        }
    )
    assert webapp_module._finding_measure(finding) is None
    assert webapp_module._finding_measure(measured) == (
        "Observed 3 · Reference threshold 2 · Observed ratio 0.75 · Reference ratio 0.50"
    )

    fake = SimpleNamespace(
        container=lambda **_kwargs: _Context(),
        markdown=lambda value: None,
        caption=lambda value: None,
    )
    monkeypatch.setattr(webapp_module, "st", fake)
    webapp_module._render_health_finding(finding)


@pytest.mark.parametrize(
    ("mode", "start", "end", "expected"),
    [
        (DateMode.EXACT, 1883, None, "1883"),
        (DateMode.APPROXIMATE, 1883, None, "About 1883"),
        (DateMode.RANGE, 1881, 1883, "1881-1883"),
        (DateMode.UNKNOWN, None, None, "Unknown"),
        (DateMode.EXACT, None, None, "Unknown"),
        (DateMode.APPROXIMATE, None, None, "Unknown"),
        (DateMode.RANGE, None, 1883, "Unknown"),
        (DateMode.RANGE, 1881, None, "Unknown"),
    ],
)
def test_confound_chronology_labels_preserve_uncertainty(
    mode: DateMode,
    start: int | None,
    end: int | None,
    expected: str,
) -> None:
    item = ConfoundDatum(
        work_id="work_one",
        display_label="Work one",
        edition_id="edition_one",
        edition_label="Edition one",
        genre="novel",
        audience="general",
        source_type="digital_library",
        adaptation="original",
        collection="independent_work",
        chronology_mode=mode,
        chronology_start_year=start,
        chronology_end_year=end,
        ocr_status="not_ocr",
        paratext_status="absent",
        curation_state="not_disclosed",
        curation_note_disclosed=False,
    )
    assert webapp_module._chronology_label(item) == expected


@pytest.mark.parametrize(
    ("code", "count", "ratio", "expected"),
    [
        (CorpusHealthFindingCode.EXACT_DUPLICATE, None, None, "Prepared hashes match"),
        (
            CorpusHealthFindingCode.SHARED_PASSAGE,
            200,
            0.25,
            "200 shared tokens · 25.00%",
        ),
        (CorpusHealthFindingCode.SHARED_PASSAGE, 200, None, "200 shared tokens"),
        (CorpusHealthFindingCode.NEAR_DUPLICATE, None, 0.91, "91.00%"),
        (CorpusHealthFindingCode.NEAR_DUPLICATE, None, None, "Threshold crossed"),
    ],
)
def test_overlap_labels_never_echo_passage_text(
    code: CorpusHealthFindingCode,
    count: int | None,
    ratio: float | None,
    expected: str,
) -> None:
    item = OverlapDatum(
        finding_id="finding_" + "a" * 64,
        code=code,
        work_ids=("work_one", "work_two"),
        display_labels=("Work one", "Work two"),
        observed_count=count,
        observed_ratio=ratio,
    )
    assert webapp_module._overlap_measure(item) == expected
    assert webapp_module._overlap_code_label(code)


def test_preparation_projection_failure_is_visible_and_content_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_two_work_prepare()

    def reject(**_kwargs: object) -> None:
        raise CorpusHealthProjectionError(CorpusHealthProjectionErrorCode.BINDING_MISMATCH)

    monkeypatch.setattr(webapp_module, "build_corpus_health_projection", reject)
    app.button(key="prepare_run_check").click().run()
    assert [message.value for message in app.error] == [
        "Delta could not bind the preparation evidence to this corpus. No review projection or "
        "analysis request was created."
    ]
    captions = "\n".join(item.value for item in app.caption)
    assert "P007_HEALTH_PROJECTION_BINDING_MISMATCH" in captions
    assert "alpha beta gamma" not in captions
    assert "Parameter review is the next step" not in "\n".join(item.value for item in app.info)


def test_missing_projection_annotations_fail_closed() -> None:
    app = _open_two_work_prepare()
    app.button(key="prepare_run_check").click().run()
    del app.session_state[webapp_module._FLOW_ANNOTATIONS_KEY]
    app.run()
    assert [message.value for message in app.error] == [
        "Delta could not bind the preparation evidence to this corpus. No review projection or "
        "analysis request was created."
    ]
    assert "Parameter review is the next step" not in "\n".join(item.value for item in app.info)


def test_preparation_rejects_bad_annotations_and_content_free_runtime_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _open_two_work_prepare()
    monkeypatch.setattr(
        webapp_module,
        "_build_preparation_annotations",
        lambda *_args: (_ for _ in ()).throw(ValueError("PRIVATE_CANARY")),
    )
    app.button(key="prepare_run_check").click().run()
    assert [message.value for message in app.error] == [
        "Review the analysis roles, OCR states, paratext states, and curation notes "
        "before retrying."
    ]
    assert "PRIVATE_CANARY" not in "\n".join(item.value for item in app.error)

    monkeypatch.undo()
    app = _open_two_work_prepare()

    class RejectingPreparation:
        @staticmethod
        def prepare(**_kwargs: object) -> None:
            raise PreparedCorpusError(PreparedCorpusErrorCode.OPERATION_FAILED)

    monkeypatch.setattr(
        webapp_module,
        "_runtime",
        lambda: SimpleNamespace(prepared_corpora=RejectingPreparation()),
    )
    app.button(key="prepare_run_check").click().run()
    assert [message.value for message in app.error] == [
        "Delta could not prepare this temporary corpus safely. No stylometric result was created."
    ]
    assert "Rejection reference: P007_PREPARED_CORPUS_OPERATION_FAILED" in [
        item.value for item in app.caption
    ]


def test_preparation_annotation_builder_is_deterministic_and_rejects_asset_mismatch() -> None:
    inventory = _fixture_inventory()
    asset = inventory.assets[0]
    selection = webapp_module.PreparationSelection(
        asset_id=asset.asset_id,
        work_id=asset.work_id,
        analysis_role=AnalysisRole.KNOWN,
        ocr_status=OcrStatus.UNKNOWN,
        paratext_status=ParatextStatus.UNKNOWN,
        curation_note=None,
    )
    first = webapp_module._build_preparation_annotations(inventory, (selection,))
    second = webapp_module._build_preparation_annotations(inventory, (selection,))
    assert first == second
    assert first.annotations[0].document_id.startswith("doc_")
    with pytest.raises(ValueError, match="do not match"):
        webapp_module._build_preparation_annotations(inventory, ())


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
    assert _page_title(app) == "Describe what each text represents"
    assert any("First Publication" in message.value for message in app.info)
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
        "Genre" in message.value and target.work_id in message.value for message in app.warning
    )
    assert all(target.field_path not in message.value for message in app.warning)
    assert not any(button.label == "Build corpus review" for button in app.button)


def test_final_confirmation_is_bound_to_inventory_hash_and_edit_invalidates_it() -> None:
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
    assert _page_title(app) == "Describe what each text represents"
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
