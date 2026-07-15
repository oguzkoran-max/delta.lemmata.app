from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import delta_lemmata.result_service as result_module
from delta_lemmata.clock import FakeClock
from delta_lemmata.corpus_models import PurposeId
from delta_lemmata.job_janitor import JobJanitor
from delta_lemmata.job_models import (
    ResultViewReceipt,
    ScientificResultReceipt,
    VersionConflictError,
    confirm_scientific_result,
    transition_scientific_execution_claim,
    transition_scientific_success,
)
from delta_lemmata.job_store import SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceArea, WorkspaceLayout, WorkspaceManager
from delta_lemmata.prepared_corpus_service import (
    PREPARED_REQUEST_INDEX_COMPONENT,
    PreparedRequestIndexV2,
    canonical_prepared_request_index,
)
from delta_lemmata.result_service import (
    ResultPackageError,
    ResultPackageErrorCode,
    ResultPackageService,
)
from delta_lemmata.result_view import (
    RESULT_VIEW_COMPONENT,
    ResultDocumentDescriptor,
    ResultViewV1,
    canonical_result_view,
    project_result_view,
)
from delta_lemmata.session_identity import JobId, SessionCapability, workspace_component
from delta_lemmata.stylo_contracts import (
    AnalysisOutcome,
    CellComplete,
    CellRequest,
    DistanceMatrix,
    DistanceMeasure,
    DocumentCounts,
    DocumentRole,
    FitComplete,
    FitRequest,
    FittingBasis,
    RSessionInfoV1,
    WorkerInputV1,
    WorkerResultV1,
    _fit_statistics,
    _ranked_features,
    canonical_worker_json,
)
from delta_lemmata.stylo_worker import RESULT_COMPONENT
from delta_lemmata.workflow_models import (
    ResolvedWorkflowConfigV1,
    canonical_p008_json,
    resolve_guided_workflow,
    workflow_config_sha256,
)

NOW = datetime(2026, 7, 15, 9, tzinfo=UTC)


def _opaque(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode()).hexdigest()}"


def _operation(number: int) -> str:
    return "op_" + f"{number:064x}"


def _session() -> RSessionInfoV1:
    return RSessionInfoV1(
        r_version="4.5.2",
        stylo_version="0.7.71",
        jsonlite_version="2.0.0",
        platform="x86_64-pc-linux-gnu",
        operating_system="Ubuntu 24.04",
        lang="C.UTF-8",
        lc_collate="C.UTF-8",
        lc_ctype="C.UTF-8",
        lc_numeric="C",
        timezone="UTC",
        unicode_normalization="NFC",
        rng_generator="Mersenne-Twister",
        rng_normal_generator="Inversion",
        rng_sample_kind="Rejection",
        seed=20260713,
        blas="Reference BLAS",
        lapack="Reference LAPACK",
    )


def _scientific_records() -> tuple[
    WorkerInputV1,
    WorkerResultV1,
    ResolvedWorkflowConfigV1,
    tuple[ResultDocumentDescriptor, ...],
]:
    config = resolve_guided_workflow(
        purpose=PurposeId.TEXT_PROXIMITY,
        known_work_count=2,
        unknown_work_count=0,
    )
    features = tuple(f"feature-{index:04d}" for index in range(1000))
    document_ids = (_opaque("doc", "one"), _opaque("doc", "two"))
    documents = (
        DocumentCounts(
            document_id=document_ids[0],
            asset_ref=_opaque("asset", "one"),
            work_ref=_opaque("work", "one"),
            role=DocumentRole.KNOWN,
            token_total=2000,
            counts=tuple(1 if index % 2 == 0 else 2 for index in range(1000)),
        ),
        DocumentCounts(
            document_id=document_ids[1],
            asset_ref=_opaque("asset", "two"),
            work_ref=_opaque("work", "two"),
            role=DocumentRole.KNOWN,
            token_total=2000,
            counts=tuple(2 if index % 2 == 0 else 1 for index in range(1000)),
        ),
    )
    fit_requests = tuple(
        FitRequest(
            fit_id=_opaque("fit", str(index)),
            mfw=cell.mfw,
            culling_percent=cell.culling_percent,
        )
        for index, cell in enumerate(config.cells)
    )
    cell_requests = tuple(
        CellRequest(
            cell_id=_opaque("cell", str(index)),
            fit_id=fit.fit_id,
            distance=DistanceMeasure.CLASSIC_DELTA,
        )
        for index, fit in enumerate(fit_requests)
    )
    request = WorkerInputV1(
        schema_version="stylo-worker-input-v1",
        request_id=_opaque("request", "service"),
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        candidate_features=features,
        documents=documents,
        fits=fit_requests,
        cells=cell_requests,
    )
    ranked = _ranked_features(request)
    fits = []
    cells = []
    for index, (fit_request, cell_request) in enumerate(
        zip(fit_requests, cell_requests, strict=True)
    ):
        selected = tuple(item.feature for item in ranked[: fit_request.mfw])
        means, deviations = _fit_statistics(request, selected)
        fits.append(
            FitComplete(
                fit_id=fit_request.fit_id,
                mfw=fit_request.mfw,
                culling_percent=fit_request.culling_percent,
                status="complete",
                eligible_feature_count=len(ranked),
                selected_features=selected,
                means=means,
                standard_deviations=deviations,
            )
        )
        distance = float(index + 1)
        cells.append(
            CellComplete(
                cell_id=cell_request.cell_id,
                fit_id=cell_request.fit_id,
                distance=cell_request.distance,
                status="complete",
                matrix=DistanceMatrix(
                    document_ids=document_ids,
                    values=((0.0, distance), (distance, 0.0)),
                ),
            )
        )
    result = WorkerResultV1(
        schema_version="stylo-worker-result-v1",
        request_id=request.request_id,
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        worker_version="stylo-worker-v1",
        outcome=AnalysisOutcome.COMPLETE,
        fitting_basis=FittingBasis(
            known_document_ids=document_ids,
            ranked_features=ranked,
        ),
        fits=tuple(fits),
        cells=tuple(cells),
        session=_session(),
    )
    descriptors = (
        ResultDocumentDescriptor(
            document_id=document_ids[0],
            title="Early work",
            role=DocumentRole.KNOWN,
        ),
        ResultDocumentDescriptor(
            document_id=document_ids[1],
            title="Late work",
            role=DocumentRole.KNOWN,
        ),
    )
    return request, result, config, descriptors


@dataclass(frozen=True, slots=True)
class _Environment:
    service: ResultPackageService
    store: SQLiteJobStore
    workspaces: WorkspaceManager
    layout: WorkspaceLayout
    clock: FakeClock
    capability: SessionCapability
    other_capability: SessionCapability
    job_id: str
    request: WorkerInputV1
    result: WorkerResultV1
    result_sha256: str
    config: ResolvedWorkflowConfigV1
    descriptors: tuple[ResultDocumentDescriptor, ...]

    def view(self) -> ResultViewV1:
        return project_result_view(
            config=self.config,
            result=self.result,
            source_result_sha256=self.result_sha256,
            documents=self.descriptors,
        )


def _private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    return path


def _environment(
    tmp_path: Path,
    *,
    result_payload_transform: Callable[[bytes], bytes] | None = None,
) -> _Environment:
    tmp_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(tmp_path, 0o700)
    database_root = _private_directory(tmp_path / "database")
    workspace_root = _private_directory(tmp_path / "workspaces")
    fixed_job_id = JobId.generate(lambda _size: b"j" * 32)
    capability = SessionCapability.generate(lambda _size: b"c" * 32)
    store = SQLiteJobStore(
        database_root / "jobs.sqlite3",
        owner_secret=b"s" * 32,
        job_id_factory=lambda: fixed_job_id,
    )
    workspaces = WorkspaceManager(workspace_root)
    clock = FakeClock(NOW)
    staged = store.stage_job(capability=capability, at_utc=NOW)
    layout = workspaces.create(
        staged.owner_digest,
        workspace_component(fixed_job_id),
    )
    queued = store.enqueue_job(
        job_id=fixed_job_id,
        capability=capability,
        at_utc=NOW + timedelta(seconds=1),
        expected_version=staged.version,
        operation_id=_operation(1),
    )
    running = store.claim_next(at_utc=NOW + timedelta(seconds=2), operation_id=_operation(2))
    assert running is not None and running.job_id == queued.job_id
    claimed = transition_scientific_execution_claim(
        running,
        expected_version=running.version,
        operation_id=_operation(3),
    )
    claimed = store.compare_and_swap(
        job_id=fixed_job_id,
        capability=capability,
        expected_version=running.version,
        updated=claimed,
        at_utc=NOW + timedelta(seconds=2),
    )

    request, result, config, descriptors = _scientific_records()
    request_payload = canonical_worker_json(request)
    result_payload = canonical_worker_json(result)
    if result_payload_transform is not None:
        result_payload = result_payload_transform(result_payload)
    config_payload = canonical_p008_json(config)
    request_component = hashlib.sha256(b"request-component").hexdigest()
    config_component = hashlib.sha256(b"config-component").hexdigest()
    index = PreparedRequestIndexV2(
        schema_version="prepared-stylo-request-index-v2",
        request_component=request_component,
        request_byte_count=len(request_payload),
        request_sha256=hashlib.sha256(request_payload).hexdigest(),
        workflow_config_component=config_component,
        workflow_config_byte_count=len(config_payload),
        workflow_config_sha256=hashlib.sha256(config_payload).hexdigest(),
    )
    for component, payload in (
        (request_component, request_payload),
        (config_component, config_payload),
        (PREPARED_REQUEST_INDEX_COMPONENT, canonical_prepared_request_index(index)),
    ):
        workspaces.create_file(layout, WorkspaceArea.WORK, component, payload)
    workspaces.create_file(layout, WorkspaceArea.RESULT, RESULT_COMPONENT, result_payload)

    scientific_receipt = ScientificResultReceipt(
        schema_version="scientific-result-receipt-v1",
        request_id=request.request_id,
        request_sha256=hashlib.sha256(request_payload).hexdigest(),
        worker_version="stylo-worker-v1",
        result_schema_version="stylo-worker-result-v1",
        analysis_outcome="complete",
        artifact_component=RESULT_COMPONENT,
        byte_size=len(result_payload),
        sha256=hashlib.sha256(result_payload).hexdigest(),
    )
    terminal = transition_scientific_success(
        claimed,
        receipt=scientific_receipt,
        at_utc=NOW + timedelta(seconds=3),
        tombstone_expires_at_utc=NOW + timedelta(days=7),
        expected_version=claimed.version,
        operation_id=_operation(4),
    )
    terminal = store.compare_and_swap(
        job_id=fixed_job_id,
        capability=capability,
        expected_version=claimed.version,
        updated=terminal,
        at_utc=NOW + timedelta(seconds=3),
    )
    confirmed = confirm_scientific_result(
        terminal,
        expected_version=terminal.version,
        operation_id=_operation(5),
    )
    store.compare_and_swap(
        job_id=fixed_job_id,
        capability=capability,
        expected_version=terminal.version,
        updated=confirmed,
        at_utc=NOW + timedelta(seconds=3),
    )
    clock.set(NOW + timedelta(seconds=4))
    return _Environment(
        service=ResultPackageService(store=store, workspaces=workspaces, clock=clock),
        store=store,
        workspaces=workspaces,
        layout=layout,
        clock=clock,
        capability=capability,
        other_capability=SessionCapability.generate(lambda _size: b"x" * 32),
        job_id=fixed_job_id.to_urlsafe(),
        request=request,
        result=result,
        result_sha256=hashlib.sha256(result_payload).hexdigest(),
        config=config,
        descriptors=descriptors,
    )


def _expect_error(code: ResultPackageErrorCode, action: Callable[[], object]) -> None:
    with pytest.raises(ResultPackageError) as captured:
        action()
    assert captured.value.code is code
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


def _expect_private_error(code: ResultPackageErrorCode, action: Callable[[], object]) -> None:
    with pytest.raises(ResultPackageError) as captured:
        action()
    assert captured.value.code is code


def test_verified_result_view_lifecycle_is_capability_bound_and_idempotent(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    verified = environment.service.read_scientific_result(
        job_id=environment.job_id,
        capability=environment.capability,
    )
    assert verified.result == environment.result
    assert verified.sha256 == hashlib.sha256(canonical_worker_json(environment.result)).hexdigest()

    view = environment.view()
    receipt = environment.service.publish_view(
        job_id=environment.job_id,
        capability=environment.capability,
        view=view,
    )
    assert receipt == ResultViewReceipt(
        schema_version="result-view-receipt-v1",
        source_result_sha256=view.source_result_sha256,
        workflow_config_sha256=workflow_config_sha256(environment.config),
        view_schema_version="result-view-v1",
        artifact_component=RESULT_VIEW_COMPONENT,
        byte_size=len(canonical_result_view(view)),
        sha256=hashlib.sha256(canonical_result_view(view)).hexdigest(),
    )
    assert (
        environment.service.publish_view(
            job_id=environment.job_id,
            capability=environment.capability,
            view=view,
        )
        == receipt
    )
    _expect_error(
        ResultPackageErrorCode.NOT_AVAILABLE,
        lambda: environment.service.read_view(
            job_id=environment.job_id,
            capability=environment.capability,
        ),
    )

    janitor = JobJanitor(
        store=environment.store,
        workspaces=environment.workspaces,
        clock=environment.clock,
    )
    report = janitor.run_once()
    assert report.exports_published == 1
    assert (
        environment.service.read_view(
            job_id=environment.job_id,
            capability=environment.capability,
        )
        == view
    )
    exported = environment.workspaces.read_file(
        environment.layout,
        WorkspaceArea.EXPORT,
        RESULT_VIEW_COMPONENT,
        maximum_bytes=4 * 1024 * 1024,
    )
    assert exported == canonical_result_view(view)
    assert b"feature-" not in exported

    for operation in (
        lambda: environment.service.read_scientific_result(
            job_id=environment.job_id,
            capability=environment.other_capability,
        ),
        lambda: environment.service.publish_view(
            job_id=environment.job_id,
            capability=environment.other_capability,
            view=view,
        ),
        lambda: environment.service.read_view(
            job_id=environment.job_id,
            capability=environment.other_capability,
        ),
    ):
        _expect_error(ResultPackageErrorCode.NOT_AVAILABLE, operation)


def test_scientific_readback_accepts_valid_r_numeric_lexemes(tmp_path: Path) -> None:
    def r_numeric_lexeme(payload: bytes) -> bytes:
        transformed = payload.replace(b'"values":[[0.0,', b'"values":[[0,', 1)
        assert transformed != payload
        return transformed

    environment = _environment(
        tmp_path,
        result_payload_transform=r_numeric_lexeme,
    )
    retained = (environment.layout.result / RESULT_COMPONENT).read_bytes()
    assert retained != canonical_worker_json(environment.result)

    verified = environment.service.read_scientific_result(
        job_id=environment.job_id,
        capability=environment.capability,
    )

    assert verified.result == environment.result
    assert verified.sha256 == hashlib.sha256(retained).hexdigest()
    view = environment.view()
    receipt = environment.service.publish_view(
        job_id=environment.job_id,
        capability=environment.capability,
        view=view,
    )
    assert receipt.source_result_sha256 == verified.sha256


def test_result_publication_rejects_matrix_config_and_source_drift(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    view = environment.view()
    variants = []
    payload = view.model_dump(mode="python")
    payload["cells"][0]["matrix"]["values"] = ((0.0, 99.0), (99.0, 0.0))
    variants.append(ResultViewV1.model_validate(payload))
    payload = view.model_dump(mode="python")
    payload["workflow_config_sha256"] = "e" * 64
    variants.append(ResultViewV1.model_validate(payload))
    payload = view.model_dump(mode="python")
    payload["source_result_sha256"] = "f" * 64
    variants.append(ResultViewV1.model_validate(payload))

    for variant in variants:

        def publish_variant(variant: ResultViewV1 = variant) -> object:
            return environment.service.publish_view(
                job_id=environment.job_id,
                capability=environment.capability,
                view=variant,
            )

        _expect_error(
            ResultPackageErrorCode.BINDING_MISMATCH,
            publish_variant,
        )


def test_result_readback_rejects_tampered_result_index_and_export(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    result_path = environment.layout.result / RESULT_COMPONENT
    result_path.write_bytes(result_path.read_bytes() + b" ")
    _expect_error(
        ResultPackageErrorCode.INTEGRITY,
        lambda: environment.service.read_scientific_result(
            job_id=environment.job_id,
            capability=environment.capability,
        ),
    )

    second = _environment(tmp_path / "second")
    index_path = second.layout.work / PREPARED_REQUEST_INDEX_COMPONENT
    index_path.write_bytes(index_path.read_bytes() + b" ")
    _expect_error(
        ResultPackageErrorCode.INTEGRITY,
        lambda: second.service.read_scientific_result(
            job_id=second.job_id,
            capability=second.capability,
        ),
    )

    third = _environment(tmp_path / "third")
    view = third.view()
    third.service.publish_view(
        job_id=third.job_id,
        capability=third.capability,
        view=view,
    )
    JobJanitor(
        store=third.store,
        workspaces=third.workspaces,
        clock=third.clock,
    ).run_once()
    export_path = third.layout.export / RESULT_VIEW_COMPONENT
    export_path.write_bytes(export_path.read_bytes() + b" ")
    _expect_error(
        ResultPackageErrorCode.INTEGRITY,
        lambda: third.service.read_view(
            job_id=third.job_id,
            capability=third.capability,
        ),
    )


def test_result_readback_rejects_expiry_and_invalid_public_calls(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    environment.clock.set(NOW + timedelta(days=2))
    _expect_error(
        ResultPackageErrorCode.EXPIRED,
        lambda: environment.service.read_scientific_result(
            job_id=environment.job_id,
            capability=environment.capability,
        ),
    )
    _expect_error(
        ResultPackageErrorCode.INVALID_REQUEST,
        lambda: environment.service.publish_view(
            job_id=environment.job_id,
            capability=environment.capability,
            view=object(),  # type: ignore[arg-type]
        ),
    )
    _expect_error(
        ResultPackageErrorCode.NOT_AVAILABLE,
        lambda: environment.service.read_view(
            job_id="short",
            capability=environment.capability,
        ),
    )


def test_result_service_rejects_invalid_configuration() -> None:
    _expect_error(
        ResultPackageErrorCode.INVALID_CONFIGURATION,
        lambda: ResultPackageService(
            store=object(),  # type: ignore[arg-type]
            workspaces=object(),  # type: ignore[arg-type]
            clock=object(),  # type: ignore[arg-type]
        ),
    )


def test_result_boundary_detaches_unexpected_failures_and_rejects_invalid_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment(tmp_path)

    def fail_context(**_kwargs):
        raise RuntimeError("private result payload")

    monkeypatch.setattr(environment.service, "_verified_context", fail_context)
    _expect_error(
        ResultPackageErrorCode.OPERATION_FAILED,
        lambda: environment.service.read_scientific_result(
            job_id=environment.job_id,
            capability=environment.capability,
        ),
    )
    monkeypatch.undo()

    _expect_error(
        ResultPackageErrorCode.INVALID_REQUEST,
        lambda: environment.service.read_scientific_result(
            job_id=object(),  # type: ignore[arg-type]
            capability=environment.capability,
        ),
    )
    monkeypatch.setattr(environment.workspaces, "load_optional", lambda *_args: None)
    _expect_error(
        ResultPackageErrorCode.NOT_AVAILABLE,
        lambda: environment.service.read_scientific_result(
            job_id=environment.job_id,
            capability=environment.capability,
        ),
    )


def test_result_boundary_rejects_broken_clock_and_missing_or_drifted_work_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken_clock = _environment(tmp_path / "clock")

    class BrokenClock:
        def now(self) -> datetime:
            raise RuntimeError("private clock detail")

    monkeypatch.setattr(broken_clock.service, "_clock", BrokenClock())
    _expect_error(
        ResultPackageErrorCode.INVALID_CONFIGURATION,
        lambda: broken_clock.service.read_scientific_result(
            job_id=broken_clock.job_id,
            capability=broken_clock.capability,
        ),
    )

    missing = _environment(tmp_path / "missing")
    (missing.layout.work / PREPARED_REQUEST_INDEX_COMPONENT).unlink()
    _expect_error(
        ResultPackageErrorCode.INTEGRITY,
        lambda: missing.service.read_scientific_result(
            job_id=missing.job_id,
            capability=missing.capability,
        ),
    )

    drifted = _environment(tmp_path / "drifted")
    index = PreparedRequestIndexV2.model_validate_json(
        (drifted.layout.work / PREPARED_REQUEST_INDEX_COMPONENT).read_bytes()
    )
    request_path = drifted.layout.work / index.request_component
    request_path.write_bytes(request_path.read_bytes() + b" ")
    _expect_error(
        ResultPackageErrorCode.INTEGRITY,
        lambda: drifted.service.read_scientific_result(
            job_id=drifted.job_id,
            capability=drifted.capability,
        ),
    )

    noncanonical = _environment(tmp_path / "noncanonical")
    monkeypatch.setattr(result_module, "canonical_worker_json", lambda _value: b"drift")
    _expect_error(
        ResultPackageErrorCode.INTEGRITY,
        lambda: noncanonical.service.read_scientific_result(
            job_id=noncanonical.job_id,
            capability=noncanonical.capability,
        ),
    )


def test_scientific_readback_requires_available_state_and_exact_receipt_metadata(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    job = environment.store.get_job(
        job_id=JobId.from_urlsafe(environment.job_id),
        capability=environment.capability,
    )
    unavailable = job.model_copy(update={"scientific_result_confirmed": False})
    _expect_error(
        ResultPackageErrorCode.NOT_AVAILABLE,
        lambda: environment.service._read_scientific(
            job=unavailable,
            layout=environment.layout,
            request=environment.request,
        ),
    )

    assert job.scientific_result is not None
    altered_receipt = job.scientific_result.model_copy(update={"worker_version": "other-worker"})
    altered = job.model_copy(update={"scientific_result": altered_receipt})
    _expect_private_error(
        ResultPackageErrorCode.INTEGRITY,
        lambda: environment.service._read_scientific(
            job=altered,
            layout=environment.layout,
            request=environment.request,
        ),
    )


def test_result_view_file_creation_is_idempotent_and_conflict_detecting(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    payload = canonical_result_view(environment.view())
    environment.workspaces.create_file(
        environment.layout,
        WorkspaceArea.EXPORT,
        RESULT_VIEW_COMPONENT,
        payload,
    )
    environment.service._create_or_verify_view(layout=environment.layout, payload=payload)
    _expect_error(
        ResultPackageErrorCode.CONFLICT,
        lambda: environment.service._create_or_verify_view(
            layout=environment.layout,
            payload=payload + b" ",
        ),
    )


def test_result_view_file_conflict_survives_an_unreadable_existing_export(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment(tmp_path)
    payload = canonical_result_view(environment.view())
    environment.workspaces.create_file(
        environment.layout,
        WorkspaceArea.EXPORT,
        RESULT_VIEW_COMPONENT,
        b"occupied",
    )

    def fail_read(*_args, **_kwargs):
        raise RuntimeError("private export detail")

    monkeypatch.setattr(environment.workspaces, "read_file", fail_read)
    _expect_error(
        ResultPackageErrorCode.CONFLICT,
        lambda: environment.service._create_or_verify_view(
            layout=environment.layout,
            payload=payload,
        ),
    )


def test_published_view_rejects_expiry_inner_binding_drift_and_nested_service_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment(tmp_path)
    view = environment.view()
    environment.service.publish_view(
        job_id=environment.job_id,
        capability=environment.capability,
        view=view,
    )
    JobJanitor(
        store=environment.store,
        workspaces=environment.workspaces,
        clock=environment.clock,
    ).run_once()
    environment.clock.set(NOW + timedelta(days=2))
    _expect_error(
        ResultPackageErrorCode.EXPIRED,
        lambda: environment.service.read_view(
            job_id=environment.job_id,
            capability=environment.capability,
        ),
    )
    binding = _environment(tmp_path / "binding")
    binding_view = binding.view()
    binding.service.publish_view(
        job_id=binding.job_id,
        capability=binding.capability,
        view=binding_view,
    )
    JobJanitor(
        store=binding.store,
        workspaces=binding.workspaces,
        clock=binding.clock,
    ).run_once()
    binding_job = binding.store.get_job(
        job_id=JobId.from_urlsafe(binding.job_id),
        capability=binding.capability,
    )
    drifted = binding_view.model_copy(update={"source_result_sha256": "f" * 64})
    drifted_payload = canonical_result_view(drifted)
    (binding.layout.export / RESULT_VIEW_COMPONENT).write_bytes(drifted_payload)
    forged_job = binding_job.model_copy(
        update={"result_view": binding.service._receipt(drifted, drifted_payload)}
    )
    _expect_private_error(
        ResultPackageErrorCode.INTEGRITY,
        lambda: binding.service._verify_view_file(
            job=forged_job,
            layout=binding.layout,
            require_published=True,
        ),
    )

    def reject_read(*_args, **_kwargs):
        raise ResultPackageError(ResultPackageErrorCode.CONFLICT)

    monkeypatch.setattr(binding.workspaces, "read_file", reject_read)
    _expect_error(
        ResultPackageErrorCode.CONFLICT,
        lambda: binding.service._verify_view_file(
            job=binding_job,
            layout=binding.layout,
            require_published=True,
        ),
    )


def test_result_publication_rejects_existing_receipt_drift_and_store_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = _environment(tmp_path / "existing")
    view = existing.view()
    existing.service.publish_view(
        job_id=existing.job_id,
        capability=existing.capability,
        view=view,
    )
    altered = view.model_copy(
        update={
            "documents": (
                view.documents[0].model_copy(update={"title": "Changed title"}),
                *view.documents[1:],
            )
        }
    )
    _expect_error(
        ResultPackageErrorCode.CONFLICT,
        lambda: existing.service.publish_view(
            job_id=existing.job_id,
            capability=existing.capability,
            view=altered,
        ),
    )

    store_failure = _environment(tmp_path / "store-failure")

    def fail_store(**_kwargs):
        raise RuntimeError("private store detail")

    monkeypatch.setattr(store_failure.store, "compare_and_swap", fail_store)
    _expect_error(
        ResultPackageErrorCode.CONFLICT,
        lambda: store_failure.service.publish_view(
            job_id=store_failure.job_id,
            capability=store_failure.capability,
            view=store_failure.view(),
        ),
    )

    exhausted = _environment(tmp_path / "exhausted")

    def conflict_store(**_kwargs):
        raise VersionConflictError

    monkeypatch.setattr(exhausted.store, "compare_and_swap", conflict_store)
    _expect_error(
        ResultPackageErrorCode.CONFLICT,
        lambda: exhausted.service.publish_view(
            job_id=exhausted.job_id,
            capability=exhausted.capability,
            view=exhausted.view(),
        ),
    )


def test_result_publication_recovers_when_same_receipt_wins_concurrently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment(tmp_path)
    original_compare_and_swap = environment.store.compare_and_swap
    first = True

    def concurrent_commit(**kwargs):
        nonlocal first
        committed = original_compare_and_swap(**kwargs)
        if first:
            first = False
            raise VersionConflictError
        return committed

    monkeypatch.setattr(environment.store, "compare_and_swap", concurrent_commit)
    receipt = environment.service.publish_view(
        job_id=environment.job_id,
        capability=environment.capability,
        view=environment.view(),
    )
    assert receipt.sha256 == hashlib.sha256(canonical_result_view(environment.view())).hexdigest()


def test_result_publication_rejects_a_different_concurrent_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment(tmp_path)
    original_load = environment.service._load_job
    calls = 0
    different = ResultViewReceipt(
        schema_version="result-view-receipt-v1",
        source_result_sha256="f" * 64,
        workflow_config_sha256="e" * 64,
        view_schema_version="result-view-v1",
        artifact_component=RESULT_VIEW_COMPONENT,
        byte_size=1,
        sha256="d" * 64,
    )

    def load_with_concurrent_receipt(**kwargs):
        nonlocal calls
        calls += 1
        job, layout = original_load(**kwargs)
        if calls >= 3:
            job = job.model_copy(update={"result_view": different})
        return job, layout

    def conflict_store(**_kwargs):
        raise VersionConflictError

    monkeypatch.setattr(environment.service, "_load_job", load_with_concurrent_receipt)
    monkeypatch.setattr(environment.store, "compare_and_swap", conflict_store)
    _expect_error(
        ResultPackageErrorCode.CONFLICT,
        lambda: environment.service.publish_view(
            job_id=environment.job_id,
            capability=environment.capability,
            view=environment.view(),
        ),
    )


def test_result_publication_preserves_nested_content_free_service_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment(tmp_path)

    def reject_store(**_kwargs):
        raise ResultPackageError(ResultPackageErrorCode.INTEGRITY)

    monkeypatch.setattr(environment.store, "compare_and_swap", reject_store)
    _expect_error(
        ResultPackageErrorCode.INTEGRITY,
        lambda: environment.service.publish_view(
            job_id=environment.job_id,
            capability=environment.capability,
            view=environment.view(),
        ),
    )
