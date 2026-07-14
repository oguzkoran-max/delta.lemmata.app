from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

import delta_lemmata.prepared_corpus_service as prepared_module
from delta_lemmata.clock import FakeClock
from delta_lemmata.corpus import (
    DateMode,
    DateValue,
    GuidedWorkInput,
    PurposeId,
    RightsStatus,
    build_guided_inventory,
    project_text_receipts,
)
from delta_lemmata.corpus_health_models import CorpusHealthReadiness
from delta_lemmata.corpus_materialization import (
    CorpusMaterializationError,
    CorpusMaterializationErrorCode,
    CorpusMaterializationReceipt,
    CorpusMaterializationService,
)
from delta_lemmata.ingestion import IntakeReceipt, IntakeRole, ValidatedCorpusPayload
from delta_lemmata.inventory import CorpusInventory, inventory_sha256
from delta_lemmata.job_service import JobService
from delta_lemmata.job_store import SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceArea, WorkspaceManager
from delta_lemmata.prepared_corpus_service import (
    PREPARED_REQUEST_INDEX_COMPONENT,
    PreparedCorpusError,
    PreparedCorpusErrorCode,
    PreparedCorpusService,
)
from delta_lemmata.preprocessing import build_preprocessing_config, parse_custom_exclusions
from delta_lemmata.preprocessing_models import (
    AnalysisPreparationReceiptV1,
    AnalysisRole,
    CorpusAnalysisAnnotation,
    CorpusAnalysisAnnotationsV1,
    OcrStatus,
    ParatextStatus,
    PreparationState,
    PreprocessingConfigV1,
    TextUnit,
)
from delta_lemmata.session_identity import JobId, SessionCapability
from delta_lemmata.stylo_contracts import WorkerInputV1

NOW = datetime(2026, 7, 14, 23, 0, tzinfo=UTC)
STORE_SECRET = b"prepared-corpus-store-owner-secret-32bytes"
AUTHORITY_SECRET = b"prepared-corpus-authority-secret-32bytes"


class JobIds:
    def __init__(self) -> None:
        self.value = 40

    def __call__(self) -> JobId:
        value = self.value
        self.value += 1
        return JobId.generate(lambda size: bytes([value]) * size)


class LeaseIds:
    def __init__(self) -> None:
        self.value = 10

    def __call__(self) -> str:
        self.value += 1
        return f"{self.value:064x}"


class ReceiptIds:
    def __init__(self) -> None:
        self.value = 20

    def __call__(self) -> str:
        self.value += 1
        return f"{self.value:064x}"


@dataclass(slots=True)
class Environment:
    service: PreparedCorpusService
    materializations: CorpusMaterializationService
    workspaces: WorkspaceManager
    store: SQLiteJobStore
    clock: FakeClock
    sources: tuple[ValidatedCorpusPayload, ...]
    materialization_receipt: CorpusMaterializationReceipt
    inventory: CorpusInventory
    annotations: CorpusAnalysisAnnotationsV1
    config: PreprocessingConfigV1


def _word(prefix: str, index: int) -> str:
    suffix = ""
    value = index
    while True:
        suffix = chr(ord("a") + value % 26) + suffix
        value = value // 26 - 1
        if value < 0:
            return prefix + suffix


def _content(prefix: str, count: int = 120) -> bytes:
    return " ".join(_word(prefix, index) for index in range(count)).encode()


def _source(index: int, content: bytes) -> ValidatedCorpusPayload:
    digest = hashlib.sha256(content).hexdigest()
    return ValidatedCorpusPayload(
        receipt=IntakeReceipt(
            asset_id="asset_" + f"{index:032x}",
            role=IntakeRole.CORPUS_TEXT,
            display_label=f"work-{index}.txt",
            storage_name="asset_" + f"{index:032x}" + ".txt",
            byte_size=len(content),
            expanded_bytes=len(content),
            sha256=digest,
            line_count=1,
            token_count=max(1, len(content.split())),
            limit_profile="ingestion-limits-v1",
        ),
        content=content,
    )


def _domain_inputs(
    sources: tuple[ValidatedCorpusPayload, ...],
    *,
    rights_status: RightsStatus = RightsStatus.ANALYSIS_ONLY,
) -> tuple[CorpusInventory, CorpusAnalysisAnnotationsV1, PreprocessingConfigV1]:
    units = project_text_receipts(tuple(source.receipt for source in sources))
    guided = tuple(
        GuidedWorkInput(
            unit=unit,
            title_original=f"Test work {index}",
            primary_author_name="Test Author",
            language="it",
            first_publication=DateValue(mode=DateMode.EXACT, start_year=1880 + index),
            genre="novel",
            audience="general",
            adaptation="original",
            collection="independent_work",
            group_label=f"period-{index}",
            edition_label="Documented digital edition",
            edition_date=DateValue(mode=DateMode.UNKNOWN),
            source_type="digital_library",
            source_title="Test Library",
            source_url="https://example.org/",
            accessed_on=date(2026, 7, 14),
            rights_status=rights_status,
        )
        for index, unit in enumerate(units, start=1)
    )
    build = build_guided_inventory(
        PurposeId.TEXT_PROXIMITY,
        guided,
        assessed_by="Test researcher",
        assessed_at_utc=NOW,
    )
    digest = inventory_sha256(build.inventory)
    annotations = CorpusAnalysisAnnotationsV1(
        schema_version="corpus-analysis-annotations-v1",
        inventory_sha256=digest,
        annotations=tuple(
            CorpusAnalysisAnnotation(
                document_id=f"doc_{index:064x}",
                asset_id=asset.asset_id,
                work_id=asset.work_id,
                analysis_role=AnalysisRole.KNOWN,
                text_unit=TextUnit.INDEPENDENT_WORK,
                parent_work_id=None,
                ocr_status=OcrStatus.NOT_OCR,
                paratext_status=ParatextStatus.ABSENT,
            )
            for index, asset in enumerate(build.inventory.assets, start=1)
        ),
    )
    config = build_preprocessing_config(parse_custom_exclusions(None))
    return build.inventory, annotations, config


def _environment(
    tmp_path: Path,
    *,
    contents: tuple[bytes, ...] | None = None,
    rights_status: RightsStatus = RightsStatus.ANALYSIS_ONLY,
    receipt_id_factory=None,
    entropy_factory=None,
) -> Environment:
    database_root = tmp_path / "database"
    workspace_root = tmp_path / "workspaces"
    database_root.mkdir(mode=0o700, parents=True)
    workspace_root.mkdir(mode=0o700, parents=True)
    clock = FakeClock(NOW)
    store = SQLiteJobStore(
        database_root / "control.sqlite3",
        owner_secret=STORE_SECRET,
        job_id_factory=JobIds(),
    )
    workspaces = WorkspaceManager(workspace_root)
    jobs = JobService(store=store, workspaces=workspaces, clock=clock)
    materializations = CorpusMaterializationService(
        jobs=jobs,
        workspaces=workspaces,
        clock=clock,
        lease_id_factory=LeaseIds(),
        capability_factory=lambda: SessionCapability.generate(lambda size: b"s" * size),
    )
    service_kwargs = {
        "materializations": materializations,
        "workspaces": workspaces,
        "clock": clock,
        "authority_secret": AUTHORITY_SECRET,
        "receipt_id_factory": receipt_id_factory or ReceiptIds(),
    }
    if entropy_factory is not None:
        service_kwargs["entropy_factory"] = entropy_factory
    service = PreparedCorpusService(**service_kwargs)
    raw_contents = contents or (_content("alpha"), _content("beta"))
    sources = tuple(_source(index, content) for index, content in enumerate(raw_contents, start=1))
    inventory, annotations, config = _domain_inputs(sources, rights_status=rights_status)
    materialization_receipt = materializations.materialize(
        owner_key="browser-session",
        payloads=sources,
    )
    return Environment(
        service=service,
        materializations=materializations,
        workspaces=workspaces,
        store=store,
        clock=clock,
        sources=sources,
        materialization_receipt=materialization_receipt,
        inventory=inventory,
        annotations=annotations,
        config=config,
    )


def _prepare(environment: Environment):
    return environment.service.prepare(
        owner_key="browser-session",
        materialization_receipt=environment.materialization_receipt,
        inventory=environment.inventory,
        annotations=environment.annotations,
        config=environment.config,
    )


def _admit(environment: Environment, ready_receipt: AnalysisPreparationReceiptV1):
    return environment.service.admit_once(
        owner_key="browser-session",
        materialization_receipt=environment.materialization_receipt,
        ready_receipt=ready_receipt,
        inventory=environment.inventory,
        annotations=environment.annotations,
        config=environment.config,
    )


def _expect_error(action, code: PreparedCorpusErrorCode) -> None:
    with pytest.raises(PreparedCorpusError) as captured:
        action()
    assert captured.value.code is code
    assert str(captured.value) == code.value
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


def test_prepare_and_admit_keep_private_text_inside_the_owned_workspace(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)

    outcome = _prepare(environment)

    assert outcome.ready_receipt is not None
    assert outcome.ready_receipt.state is PreparationState.READY
    assert outcome.readiness_scope == "computational_preflight_only"
    assert outcome.health_report.readiness is CorpusHealthReadiness.READY
    assert outcome.ready_receipt.candidate_feature_count == 240
    assert (
        outcome.ready_receipt.validation_report_sha256
        == hashlib.sha256(
            prepared_module.canonical_p007_json(outcome.validation_report)
        ).hexdigest()
    )
    public_rendering = repr(outcome)
    for source in environment.sources:
        assert source.content.decode() not in public_rendering
        assert source.content.decode().split()[0] not in public_rendering

    queued = _admit(environment, outcome.ready_receipt)
    assert queued.state_id == "queued"
    assert (
        environment.service.status(
            owner_key="browser-session",
            materialization_receipt=environment.materialization_receipt,
        ).state_id
        == "queued"
    )

    layout = environment.workspaces.list_layouts()[0]
    index_bytes = (layout.work / PREPARED_REQUEST_INDEX_COMPONENT).read_bytes()
    index = json.loads(index_bytes)
    request_bytes = (layout.work / index["request_component"]).read_bytes()
    request = WorkerInputV1.model_validate_json(request_bytes)
    assert request.request_id.startswith("request_")
    assert len(request.documents) == 2
    assert len(request.candidate_features) == 240
    database_bytes = environment.store.database_file.read_bytes()
    for source in environment.sources:
        assert source.content not in database_bytes

    _expect_error(
        lambda: _admit(environment, outcome.ready_receipt),
        PreparedCorpusErrorCode.ADMISSION_REUSED,
    )


def test_health_blocker_returns_report_without_creating_ready_authority(tmp_path: Path) -> None:
    environment = _environment(tmp_path, contents=(b"Alpha", b"alpha"))

    outcome = _prepare(environment)

    assert outcome.health_report.readiness is CorpusHealthReadiness.BLOCKED
    assert outcome.health_report.blocker_count >= 1
    assert outcome.ready_receipt is None
    assert environment.workspaces.list_layouts() == ()


def test_p004_and_public_binding_failures_remove_private_materialization(tmp_path: Path) -> None:
    blocked = _environment(
        tmp_path / "blocked",
        rights_status=RightsStatus.UNKNOWN,
    )
    _expect_error(lambda: _prepare(blocked), PreparedCorpusErrorCode.P004_BLOCKED)
    assert blocked.workspaces.list_layouts() == ()

    mismatched = _environment(tmp_path / "annotations")
    changed_annotations = mismatched.annotations.model_copy(update={"inventory_sha256": "f" * 64})
    _expect_error(
        lambda: mismatched.service.prepare(
            owner_key="browser-session",
            materialization_receipt=mismatched.materialization_receipt,
            inventory=mismatched.inventory,
            annotations=changed_annotations,
            config=mismatched.config,
        ),
        PreparedCorpusErrorCode.BINDING_MISMATCH,
    )
    assert mismatched.workspaces.list_layouts() == ()

    config_mismatch = _environment(tmp_path / "config")
    changed_config = config_mismatch.config.model_copy(update={"max_candidate_features": 4000})
    _expect_error(
        lambda: config_mismatch.service.prepare(
            owner_key="browser-session",
            materialization_receipt=config_mismatch.materialization_receipt,
            inventory=config_mismatch.inventory,
            annotations=config_mismatch.annotations,
            config=changed_config,
        ),
        PreparedCorpusErrorCode.BINDING_MISMATCH,
    )
    assert config_mismatch.workspaces.list_layouts() == ()


def test_staged_source_and_ready_receipt_mutations_fail_closed(tmp_path: Path) -> None:
    source_mutation = _environment(tmp_path / "source")
    staged = next(source_mutation.workspaces.list_layouts()[0].input.iterdir())
    staged.write_bytes(b"changed private source")
    _expect_error(lambda: _prepare(source_mutation), PreparedCorpusErrorCode.INTEGRITY)
    assert source_mutation.workspaces.list_layouts() == ()

    receipt_mutation = _environment(tmp_path / "receipt")
    outcome = _prepare(receipt_mutation)
    assert outcome.ready_receipt is not None
    changed_receipt = outcome.ready_receipt.model_copy(update={"manifest_sha256": "f" * 64})
    _expect_error(
        lambda: _admit(receipt_mutation, changed_receipt),
        PreparedCorpusErrorCode.ADMISSION_REJECTED,
    )
    layout = receipt_mutation.workspaces.list_layouts()[0]
    assert tuple(layout.work.iterdir()) == ()
    assert _admit(receipt_mutation, outcome.ready_receipt).state_id == "queued"


def test_duplicate_preparation_preserves_the_first_ready_authority(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    first = _prepare(environment)
    assert first.ready_receipt is not None

    _expect_error(
        lambda: _prepare(environment),
        PreparedCorpusErrorCode.ALREADY_READY,
    )

    assert len(environment.workspaces.list_layouts()) == 1
    assert _admit(environment, first.ready_receipt).state_id == "queued"


def test_rejected_queue_admission_can_retry_the_exact_private_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment(tmp_path)
    outcome = _prepare(environment)
    assert outcome.ready_receipt is not None
    original_consume = environment.materializations.consume_ready

    def reject_once(**_kwargs):
        raise CorpusMaterializationError(CorpusMaterializationErrorCode.READY_REJECTED)

    monkeypatch.setattr(environment.materializations, "consume_ready", reject_once)
    _expect_error(
        lambda: _admit(environment, outcome.ready_receipt),
        PreparedCorpusErrorCode.ADMISSION_REJECTED,
    )
    layout = environment.workspaces.list_layouts()[0]
    before = {path.name: path.read_bytes() for path in layout.work.iterdir()}

    monkeypatch.setattr(environment.materializations, "consume_ready", original_consume)
    assert _admit(environment, outcome.ready_receipt).state_id == "queued"
    after = {path.name: path.read_bytes() for path in layout.work.iterdir()}
    assert after == before


def test_request_tampering_and_exact_expiry_remove_private_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tampered = _environment(tmp_path / "tampered")
    outcome = _prepare(tampered)
    assert outcome.ready_receipt is not None
    receipt_hmac = tampered.service._receipt_hmac(outcome.ready_receipt)
    _request_id, _key, component, _operation = tampered.service._request_identity(receipt_hmac)
    original_consume = tampered.materializations.consume_ready

    def reject_once(**_kwargs):
        raise CorpusMaterializationError(CorpusMaterializationErrorCode.READY_REJECTED)

    monkeypatch.setattr(tampered.materializations, "consume_ready", reject_once)
    _expect_error(
        lambda: _admit(tampered, outcome.ready_receipt),
        PreparedCorpusErrorCode.ADMISSION_REJECTED,
    )
    monkeypatch.setattr(tampered.materializations, "consume_ready", original_consume)
    layout = tampered.workspaces.list_layouts()[0]
    (layout.work / component).write_bytes(b"tampered request")
    _expect_error(
        lambda: _admit(tampered, outcome.ready_receipt),
        PreparedCorpusErrorCode.INTEGRITY,
    )
    assert tampered.workspaces.list_layouts() == ()

    expired = _environment(tmp_path / "expired")
    expired_outcome = _prepare(expired)
    assert expired_outcome.ready_receipt is not None
    expired.clock.advance(timedelta(hours=1))
    _expect_error(
        lambda: _admit(expired, expired_outcome.ready_receipt),
        PreparedCorpusErrorCode.EXPIRED,
    )
    assert expired.workspaces.list_layouts() == ()


def test_constructor_factories_and_custom_exclusions_fail_content_free(tmp_path: Path) -> None:
    valid = _environment(tmp_path / "valid")
    _expect_error(
        lambda: PreparedCorpusService(
            materializations=object(),  # type: ignore[arg-type]
            workspaces=valid.workspaces,
            clock=valid.clock,
            authority_secret=AUTHORITY_SECRET,
        ),
        PreparedCorpusErrorCode.INVALID_CONFIGURATION,
    )

    bad_id = _environment(tmp_path / "bad-id", receipt_id_factory=lambda: "bad")
    _expect_error(lambda: _prepare(bad_id), PreparedCorpusErrorCode.INVALID_CONFIGURATION)
    assert bad_id.workspaces.list_layouts() == ()

    bad_entropy = _environment(
        tmp_path / "bad-entropy",
        entropy_factory=lambda _size: b"short",
    )
    _expect_error(lambda: _prepare(bad_entropy), PreparedCorpusErrorCode.INVALID_CONFIGURATION)
    assert bad_entropy.workspaces.list_layouts() == ()

    exclusions = _environment(tmp_path / "exclusions")
    _expect_error(
        lambda: exclusions.service.prepare(
            owner_key="browser-session",
            materialization_receipt=exclusions.materialization_receipt,
            inventory=exclusions.inventory,
            annotations=exclusions.annotations,
            config=exclusions.config,
            custom_exclusions_bytes=b"UPPERCASE",
        ),
        PreparedCorpusErrorCode.INVALID_REQUEST,
    )
    assert exclusions.workspaces.list_layouts() == ()


def test_pure_helpers_reject_invalid_rights_and_private_bindings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment(tmp_path)
    exclusions = parse_custom_exclusions(None)
    original_validate = prepared_module.validate_inventory
    validation = original_validate(environment.inventory)
    assert prepared_module._chronology_point(DateValue(mode=DateMode.UNKNOWN)) is None

    with pytest.raises(PreparedCorpusError) as invalid_input:
        PreparedCorpusService._validate_public_inputs(
            inventory=object(),  # type: ignore[arg-type]
            annotations=environment.annotations,
            config=environment.config,
            exclusions=exclusions,
        )
    assert invalid_input.value.code is PreparedCorpusErrorCode.INVALID_REQUEST

    changed_asset = environment.inventory.assets[0].model_copy(
        update={"rights_chain_confirmed": False}
    )
    changed_inventory = environment.inventory.model_copy(
        update={"assets": (changed_asset, *environment.inventory.assets[1:])}
    )
    changed_digest = inventory_sha256(changed_inventory)
    changed_annotations = environment.annotations.model_copy(
        update={"inventory_sha256": changed_digest}
    )
    fake_validation = validation.model_copy(update={"inventory_sha256": changed_digest})
    monkeypatch.setattr(prepared_module, "validate_inventory", lambda _inventory: fake_validation)
    with pytest.raises(PreparedCorpusError) as blocked_rights:
        PreparedCorpusService._validate_public_inputs(
            inventory=changed_inventory,
            annotations=changed_annotations,
            config=environment.config,
            exclusions=exclusions,
        )
    assert blocked_rights.value.code is PreparedCorpusErrorCode.RIGHTS_BLOCKED
    monkeypatch.setattr(prepared_module, "validate_inventory", original_validate)

    with pytest.raises(PreparedCorpusError) as duplicate_payload:
        PreparedCorpusService._bundle(
            payloads=(environment.sources[0], environment.sources[0]),
            inventory=environment.inventory,
            annotations=environment.annotations,
            config=environment.config,
            exclusions=exclusions,
            validation_report=validation,
        )
    assert duplicate_payload.value.code is PreparedCorpusErrorCode.BINDING_MISMATCH

    bad_annotation = environment.annotations.annotations[0].model_copy(
        update={"asset_id": "asset_" + "f" * 32}
    )
    bad_annotations = environment.annotations.model_copy(
        update={"annotations": (bad_annotation, *environment.annotations.annotations[1:])}
    )
    with pytest.raises(PreparedCorpusError) as missing_asset:
        PreparedCorpusService._bundle(
            payloads=environment.sources,
            inventory=environment.inventory,
            annotations=bad_annotations,
            config=environment.config,
            exclusions=exclusions,
            validation_report=validation,
        )
    assert missing_asset.value.code is PreparedCorpusErrorCode.BINDING_MISMATCH

    wrong_work = environment.annotations.annotations[0].model_copy(
        update={"work_id": environment.inventory.assets[1].work_id}
    )
    wrong_work_annotations = environment.annotations.model_copy(
        update={"annotations": (wrong_work, *environment.annotations.annotations[1:])}
    )
    with pytest.raises(PreparedCorpusError) as mismatched_work:
        PreparedCorpusService._bundle(
            payloads=environment.sources,
            inventory=environment.inventory,
            annotations=wrong_work_annotations,
            config=environment.config,
            exclusions=exclusions,
            validation_report=validation,
        )
    assert mismatched_work.value.code is PreparedCorpusErrorCode.BINDING_MISMATCH

    bad_receipt = environment.sources[0].receipt.model_copy(
        update={"limit_profile": "different-profile"}
    )
    bad_source = replace(environment.sources[0], receipt=bad_receipt)
    with pytest.raises(PreparedCorpusError) as bad_payload:
        PreparedCorpusService._bundle(
            payloads=(bad_source, *environment.sources[1:]),
            inventory=environment.inventory,
            annotations=environment.annotations,
            config=environment.config,
            exclusions=exclusions,
            validation_report=validation,
        )
    assert bad_payload.value.code is PreparedCorpusErrorCode.BINDING_MISMATCH

    bundle = PreparedCorpusService._bundle(
        payloads=environment.sources,
        inventory=environment.inventory,
        annotations=environment.annotations,
        config=environment.config,
        exclusions=exclusions,
        validation_report=validation,
    )
    outcome = _prepare(environment)
    assert outcome.ready_receipt is not None
    changed_validation = outcome.ready_receipt.model_copy(
        update={"validation_report_sha256": "f" * 64}
    )
    with pytest.raises(PreparedCorpusError) as changed_receipt:
        environment.service._verify_receipt(
            receipt=changed_validation,
            inventory=environment.inventory,
            annotations=environment.annotations,
            config=environment.config,
            bundle=bundle,
        )
    assert changed_receipt.value.code is PreparedCorpusErrorCode.BINDING_MISMATCH


def test_prepare_translates_clock_binding_and_unexpected_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_receipt = _environment(tmp_path / "invalid-receipt")
    _expect_error(
        lambda: invalid_receipt.service.prepare(
            owner_key="browser-session",
            materialization_receipt=object(),  # type: ignore[arg-type]
            inventory=invalid_receipt.inventory,
            annotations=invalid_receipt.annotations,
            config=invalid_receipt.config,
        ),
        PreparedCorpusErrorCode.INVALID_REQUEST,
    )
    invalid_receipt.materializations.cleanup(
        owner_key="browser-session",
        receipt=invalid_receipt.materialization_receipt,
    )

    broken_clock = _environment(tmp_path / "clock")

    class BrokenClock:
        def now(self) -> datetime:
            raise RuntimeError("private clock")

    monkeypatch.setattr(broken_clock.service, "_clock", BrokenClock())
    _expect_error(lambda: _prepare(broken_clock), PreparedCorpusErrorCode.INVALID_CONFIGURATION)
    assert broken_clock.workspaces.list_layouts() == ()

    factory_failure = _environment(
        tmp_path / "receipt-factory",
        receipt_id_factory=lambda: (_ for _ in ()).throw(RuntimeError("private factory")),
    )
    _expect_error(
        lambda: _prepare(factory_failure),
        PreparedCorpusErrorCode.INVALID_CONFIGURATION,
    )
    assert factory_failure.workspaces.list_layouts() == ()

    entropy_failure = _environment(
        tmp_path / "entropy-factory",
        entropy_factory=lambda _size: (_ for _ in ()).throw(RuntimeError("private entropy")),
    )
    _expect_error(
        lambda: _prepare(entropy_failure),
        PreparedCorpusErrorCode.INVALID_CONFIGURATION,
    )
    assert entropy_failure.workspaces.list_layouts() == ()

    expired_during_prepare = _environment(tmp_path / "expiry")
    original_visit = expired_during_prepare.materializations.visit

    def visit_then_expire(**kwargs):
        result = original_visit(**kwargs)
        expired_during_prepare.clock.advance(timedelta(hours=1))
        return result

    monkeypatch.setattr(expired_during_prepare.materializations, "visit", visit_then_expire)
    _expect_error(
        lambda: _prepare(expired_during_prepare),
        PreparedCorpusErrorCode.EXPIRED,
    )
    assert expired_during_prepare.workspaces.list_layouts() == ()

    bind_failure = _environment(tmp_path / "bind")

    def reject_bind(**_kwargs):
        raise CorpusMaterializationError(CorpusMaterializationErrorCode.READY_REJECTED)

    monkeypatch.setattr(bind_failure.materializations, "bind_ready", reject_bind)
    _expect_error(
        lambda: _prepare(bind_failure),
        PreparedCorpusErrorCode.ADMISSION_REJECTED,
    )
    assert bind_failure.workspaces.list_layouts() == ()

    expired_bind = _environment(tmp_path / "expired-bind")

    def expire_bind(**kwargs):
        expired_bind.materializations.cleanup(
            owner_key=kwargs["owner_key"],
            receipt=kwargs["receipt"],
        )
        raise CorpusMaterializationError(CorpusMaterializationErrorCode.EXPIRED)

    monkeypatch.setattr(expired_bind.materializations, "bind_ready", expire_bind)
    _expect_error(
        lambda: _prepare(expired_bind),
        PreparedCorpusErrorCode.EXPIRED,
    )
    assert expired_bind.workspaces.list_layouts() == ()

    unexpected = _environment(tmp_path / "unexpected")

    def break_hmac(_receipt):
        raise RuntimeError("private hmac")

    monkeypatch.setattr(unexpected.service, "_receipt_hmac", break_hmac)
    _expect_error(
        lambda: _prepare(unexpected),
        PreparedCorpusErrorCode.OPERATION_FAILED,
    )
    assert unexpected.workspaces.list_layouts() == ()


def test_cleanup_status_and_public_exception_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cleanup_failure = _environment(tmp_path / "cleanup")

    def broken_cleanup(**_kwargs):
        raise RuntimeError("private cleanup")

    monkeypatch.setattr(cleanup_failure.materializations, "cleanup", broken_cleanup)
    changed = cleanup_failure.annotations.model_copy(update={"inventory_sha256": "f" * 64})
    _expect_error(
        lambda: cleanup_failure.service.prepare(
            owner_key="browser-session",
            materialization_receipt=cleanup_failure.materialization_receipt,
            inventory=cleanup_failure.inventory,
            annotations=changed,
            config=cleanup_failure.config,
        ),
        PreparedCorpusErrorCode.CLEANUP_FAILED,
    )

    status_mapping = _environment(tmp_path / "status")
    _expect_error(
        lambda: status_mapping.service.status(
            owner_key="wrong-session",
            materialization_receipt=status_mapping.materialization_receipt,
        ),
        PreparedCorpusErrorCode.NOT_AVAILABLE,
    )

    def unexpected_status(**_kwargs):
        raise RuntimeError("private status")

    monkeypatch.setattr(status_mapping.materializations, "status", unexpected_status)
    _expect_error(
        lambda: status_mapping.service.status(
            owner_key="browser-session",
            materialization_receipt=status_mapping.materialization_receipt,
        ),
        PreparedCorpusErrorCode.OPERATION_FAILED,
    )
    status_mapping.materializations.cleanup(
        owner_key="browser-session",
        receipt=status_mapping.materialization_receipt,
    )


def test_admission_validates_types_and_request_index_integrity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = _environment(tmp_path / "invalid")
    outcome = _prepare(invalid)
    assert outcome.ready_receipt is not None
    _expect_error(
        lambda: invalid.service.admit_once(
            owner_key="browser-session",
            materialization_receipt=invalid.materialization_receipt,
            ready_receipt=object(),  # type: ignore[arg-type]
            inventory=invalid.inventory,
            annotations=invalid.annotations,
            config=invalid.config,
        ),
        PreparedCorpusErrorCode.INVALID_REQUEST,
    )
    invalid.materializations.cleanup(
        owner_key="browser-session",
        receipt=invalid.materialization_receipt,
    )

    malformed_index = _environment(tmp_path / "index")
    malformed_outcome = _prepare(malformed_index)
    assert malformed_outcome.ready_receipt is not None
    original_consume = malformed_index.materializations.consume_ready

    def reject_once(**_kwargs):
        raise CorpusMaterializationError(CorpusMaterializationErrorCode.READY_REJECTED)

    monkeypatch.setattr(malformed_index.materializations, "consume_ready", reject_once)
    _expect_error(
        lambda: _admit(malformed_index, malformed_outcome.ready_receipt),
        PreparedCorpusErrorCode.ADMISSION_REJECTED,
    )
    monkeypatch.setattr(malformed_index.materializations, "consume_ready", original_consume)
    layout = malformed_index.workspaces.list_layouts()[0]
    (layout.work / PREPARED_REQUEST_INDEX_COMPONENT).write_bytes(b"not-json")
    _expect_error(
        lambda: _admit(malformed_index, malformed_outcome.ready_receipt),
        PreparedCorpusErrorCode.INTEGRITY,
    )
    assert malformed_index.workspaces.list_layouts() == ()

    orphan = _environment(tmp_path / "orphan")
    orphan_outcome = _prepare(orphan)
    assert orphan_outcome.ready_receipt is not None
    receipt_hmac = orphan.service._receipt_hmac(orphan_outcome.ready_receipt)
    _request_id, _key, component, _operation = orphan.service._request_identity(receipt_hmac)
    orphan_layout = orphan.workspaces.list_layouts()[0]
    orphan.workspaces.create_file(
        orphan_layout,
        WorkspaceArea.WORK,
        component,
        b"orphan request",
    )
    _expect_error(
        lambda: _admit(orphan, orphan_outcome.ready_receipt),
        PreparedCorpusErrorCode.INTEGRITY,
    )
    assert orphan.workspaces.list_layouts() == ()
