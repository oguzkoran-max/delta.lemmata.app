from __future__ import annotations

import hashlib
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest

from delta_lemmata.clock import FakeClock
from delta_lemmata.ingestion import IntakeReceipt, IntakeRole
from delta_lemmata.job_models import (
    ArtifactKind,
    CleanupState,
    ExecutionState,
    JobRecord,
    TerminalOutcome,
    VersionConflictError,
    publish_export,
    transition_artifact,
    transition_execution,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY
from delta_lemmata.job_service import (
    JobAdmission,
    JobService,
    JobServiceAdmissionRejectedError,
    JobServiceError,
    JobServiceErrorCode,
    JobServiceNotAvailableError,
)
from delta_lemmata.job_staging import (
    MaterializationReceipt,
    ValidatedPayload,
    materialize_validated_payloads,
)
from delta_lemmata.job_store import AnalysisAdmissionReusedError, SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceArea, WorkspaceLayout, WorkspaceManager
from delta_lemmata.session_identity import JobId, SessionCapability, workspace_component

NOW = datetime(2026, 7, 13, 18, tzinfo=UTC)
SECRET = b"job-service-owner-secret-v1-32bytes"


def capability(number: int) -> SessionCapability:
    return SessionCapability.generate(lambda size: bytes([number]) * size)


class CountingJobIds:
    def __init__(self, start: int = 20) -> None:
        self.calls = 0
        self._next = start
        self._lock = threading.Lock()

    def __call__(self) -> JobId:
        with self._lock:
            value = self._next
            self._next += 1
            self.calls += 1
        return JobId.generate(lambda size: bytes([value]) * size)


class ProcessSpy:
    def __init__(self) -> None:
        self.started: list[str] = []
        self.cancelled: list[str] = []

    def start(self, job: JobRecord, _layout: WorkspaceLayout) -> None:
        self.started.append(job.job_id)

    def cancel(self, job: JobRecord) -> None:
        self.cancelled.append(job.job_id)


def payload(number: int = 1) -> ValidatedPayload:
    content = f"validated corpus {number}".encode()
    digest = hashlib.sha256(content).hexdigest()
    receipt = IntakeReceipt(
        asset_id="asset_" + f"{number:032x}",
        role=IntakeRole.CORPUS_TEXT,
        display_label=f"private-{number}.txt",
        storage_name="asset_" + f"{number:032x}" + ".txt",
        byte_size=len(content),
        expanded_bytes=len(content),
        sha256=digest,
        line_count=1,
        token_count=3,
        limit_profile="ingestion-limits-v1",
    )
    return ValidatedPayload(receipt=receipt, content=content)


def environment(
    tmp_path: Path,
    *,
    factory: CountingJobIds | None = None,
    materializer: Any = materialize_validated_payloads,
    process: ProcessSpy | None = None,
    operation_id_factory: Any = None,
) -> tuple[JobService, SQLiteJobStore, WorkspaceManager, FakeClock, CountingJobIds]:
    database_root = tmp_path / "database"
    workspace_root = tmp_path / "workspaces"
    database_root.mkdir(mode=0o700, parents=True)
    workspace_root.mkdir(mode=0o700, parents=True)
    ids = factory or CountingJobIds()
    store = SQLiteJobStore(
        database_root / "control.sqlite3",
        owner_secret=SECRET,
        job_id_factory=ids,
    )
    workspaces = WorkspaceManager(workspace_root)
    clock = FakeClock(NOW)
    if operation_id_factory is None:
        service = JobService(
            store=store,
            workspaces=workspaces,
            clock=clock,
            materializer=materializer,
            process_gateway=process,
        )
    else:
        service = JobService(
            store=store,
            workspaces=workspaces,
            clock=clock,
            materializer=materializer,
            process_gateway=process,
            operation_id_factory=operation_id_factory,
        )
    return service, store, workspaces, clock, ids


def database_counts(store: SQLiteJobStore) -> tuple[int, int]:
    with closing(sqlite3.connect(store.database_file)) as connection:
        jobs = cast(tuple[int], connection.execute("SELECT COUNT(*) FROM jobs").fetchone())[0]
        events = cast(tuple[int], connection.execute("SELECT COUNT(*) FROM events").fetchone())[0]
    return jobs, events


def expect_service_error(
    action: Any,
    code: JobServiceErrorCode,
    error_type: type[JobServiceError] = JobServiceError,
) -> JobServiceError:
    with pytest.raises(error_type) as captured:
        assert callable(action)
        action()
    error = captured.value
    assert error.code is code
    assert str(error) == code.value
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    return error


def persist(
    store: SQLiteJobStore,
    owner: SessionCapability,
    previous: JobRecord,
    updated: JobRecord,
    at_utc: datetime,
) -> JobRecord:
    return store.compare_and_swap(
        job_id=previous.job_id,
        capability=owner,
        expected_version=previous.version,
        updated=updated,
        at_utc=at_utc,
    )


def test_cross_session_and_unknown_operations_share_one_pre_resource_denial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = ProcessSpy()

    service, _store, workspaces, _clock, _ids = environment(tmp_path, process=process)
    owner = capability(1)
    other = capability(2)
    admitted = service.admit(capability=owner, payloads=(payload(),))
    resource_calls: list[str] = []
    original_load = workspaces.load_optional
    original_cleanup = workspaces.cleanup

    def observed_load(owner_component: str, job_component: str) -> WorkspaceLayout | None:
        resource_calls.append("load")
        return original_load(owner_component, job_component)

    def observed_cleanup(layout: WorkspaceLayout) -> object:
        resource_calls.append("cleanup")
        return original_cleanup(layout)

    monkeypatch.setattr(workspaces, "load_optional", observed_load)
    monkeypatch.setattr(workspaces, "cleanup", observed_cleanup)
    unknown = JobId.generate(lambda size: b"z" * size)

    operations = (
        lambda identifier, session: service.status(job_id=identifier, capability=session),
        lambda identifier, session: service.cancel(job_id=identifier, capability=session),
        lambda identifier, session: service.result(job_id=identifier, capability=session),
        lambda identifier, session: service.export(job_id=identifier, capability=session),
        lambda identifier, session: service.cleanup(job_id=identifier, capability=session),
    )
    errors: list[JobServiceError] = []
    for operation in operations:
        errors.append(
            expect_service_error(
                lambda operation=operation: operation(admitted.job.job_id, other),
                JobServiceErrorCode.NOT_AVAILABLE,
                JobServiceNotAvailableError,
            )
        )
        errors.append(
            expect_service_error(
                lambda operation=operation: operation("malformed", owner),
                JobServiceErrorCode.NOT_AVAILABLE,
                JobServiceNotAvailableError,
            )
        )
        errors.append(
            expect_service_error(
                lambda operation=operation: operation(unknown, owner),
                JobServiceErrorCode.NOT_AVAILABLE,
                JobServiceNotAvailableError,
            )
        )

    assert {type(error) for error in errors} == {JobServiceNotAvailableError}
    assert {str(error) for error in errors} == {"JOB_NOT_AVAILABLE"}
    assert resource_calls == []
    assert process.started == []
    assert process.cancelled == []


def test_one_canary_lifecycle_stays_out_of_control_projection_and_error_surfaces(
    tmp_path: Path,
) -> None:
    canary = "P005_AC07_PRIVATE_CORPUS_CANARY"
    filename_canary = "P005_AC07_PRIVATE_FILENAME.txt"
    content = canary.encode("utf-8")
    receipt = IntakeReceipt(
        asset_id="asset_" + "f" * 32,
        role=IntakeRole.CORPUS_TEXT,
        display_label=filename_canary,
        storage_name="asset_" + "f" * 32 + ".txt",
        byte_size=len(content),
        expanded_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        line_count=1,
        token_count=1,
        limit_profile="ingestion-limits-v1",
    )
    service, store, _workspaces, _clock, _ids = environment(tmp_path)
    owner = capability(1)
    other = capability(2)
    admission = service.admit(
        capability=owner,
        payloads=(ValidatedPayload(receipt=receipt, content=content),),
    )

    presentation = service.status(job_id=admission.job.job_id, capability=owner)
    unauthorized = expect_service_error(
        lambda: service.status(job_id=admission.job.job_id, capability=other),
        JobServiceErrorCode.NOT_AVAILABLE,
        JobServiceNotAvailableError,
    )
    result_error = expect_service_error(
        lambda: service.result(job_id=admission.job.job_id, capability=owner),
        JobServiceErrorCode.ARTIFACT_NOT_AVAILABLE,
    )
    export_error = expect_service_error(
        lambda: service.export(job_id=admission.job.job_id, capability=owner),
        JobServiceErrorCode.ARTIFACT_NOT_AVAILABLE,
    )

    database_bytes = b"".join(
        path.read_bytes()
        for path in (
            store.database_file,
            Path(f"{store.database_file}-wal"),
            Path(f"{store.database_file}-shm"),
        )
        if path.exists()
    )
    safe_outputs = " ".join(
        (
            repr(admission),
            repr(presentation),
            str(unauthorized),
            str(result_error),
            str(export_error),
            repr(vars(service)),
        )
    )
    for forbidden in (canary, filename_canary):
        assert forbidden.encode("utf-8") not in database_bytes
        assert forbidden not in safe_outputs

    report = service.cleanup(job_id=admission.job.job_id, capability=owner)
    assert report.file_count == 1
    serialized_events = " ".join(event.model_dump_json() for event in store.list_deletion_events())
    for forbidden in (canary, filename_canary):
        assert forbidden not in serialized_events


def test_concurrent_stage_and_queue_rejection_allocate_only_committed_jobs(
    tmp_path: Path,
) -> None:
    stage_calls = 0
    call_lock = threading.Lock()

    def counted_materializer(
        manager: WorkspaceManager,
        layout: WorkspaceLayout,
        payloads: Any,
    ) -> MaterializationReceipt:
        nonlocal stage_calls
        with call_lock:
            stage_calls += 1
        return materialize_validated_payloads(manager, layout, payloads)

    service, store, workspaces, _clock, ids = environment(
        tmp_path / "staged",
        materializer=counted_materializer,
    )
    owners = [capability(number) for number in range(1, 9)]
    barrier = threading.Barrier(len(owners))

    def stage(index: int) -> JobAdmission | JobServiceError:
        barrier.wait()
        try:
            return service.admit(capability=owners[index], payloads=(payload(index + 1),))
        except JobServiceError as error:
            return error

    with ThreadPoolExecutor(max_workers=len(owners)) as executor:
        outcomes = list(executor.map(stage, range(len(owners))))

    accepted = [outcome for outcome in outcomes if isinstance(outcome, JobAdmission)]
    rejected = [outcome for outcome in outcomes if isinstance(outcome, JobServiceError)]
    assert len(accepted) == DEFAULT_JOB_POLICY.max_staged_global
    assert len(rejected) == len(owners) - DEFAULT_JOB_POLICY.max_staged_global
    assert all(isinstance(error, JobServiceAdmissionRejectedError) for error in rejected)
    assert ids.calls == stage_calls == DEFAULT_JOB_POLICY.max_staged_global
    assert database_counts(store) == (4, 4)
    assert len(tuple(workspaces.root.glob("*/*/input"))) == 4

    before = (ids.calls, stage_calls, database_counts(store))
    expect_service_error(
        lambda: service.admit(capability=owners[0], payloads=(payload(20),)),
        JobServiceErrorCode.ADMISSION_REJECTED,
        JobServiceAdmissionRejectedError,
    )
    assert (ids.calls, stage_calls, database_counts(store)) == before

    queued_service, queued_store, queued_workspaces, _clock, queued_ids = environment(
        tmp_path / "queued",
        materializer=counted_materializer,
    )
    queued_owners = [capability(number) for number in range(20, 27)]
    queue_barrier = threading.Barrier(len(queued_owners))

    def queue(index: int) -> JobAdmission | JobServiceError:
        queue_barrier.wait()
        try:
            return queued_service.admit(
                capability=queued_owners[index],
                payloads=(payload(index + 30),),
                queued=True,
            )
        except JobServiceError as error:
            return error

    materializations_before_queue = stage_calls
    with ThreadPoolExecutor(max_workers=len(queued_owners)) as executor:
        queue_outcomes = list(executor.map(queue, range(len(queued_owners))))
    queued = [outcome for outcome in queue_outcomes if isinstance(outcome, JobAdmission)]
    assert len(queued) == DEFAULT_JOB_POLICY.max_queued
    assert all(item.job.execution.state is ExecutionState.QUEUED for item in queued)
    assert queued_ids.calls == DEFAULT_JOB_POLICY.max_queued
    assert stage_calls - materializations_before_queue == DEFAULT_JOB_POLICY.max_queued
    assert database_counts(queued_store) == (3, 6)
    assert len(tuple(queued_workspaces.root.glob("*/*/input"))) == 3

    owner_service, owner_store, owner_workspaces, _clock, owner_ids = environment(
        tmp_path / "same-owner",
        materializer=counted_materializer,
    )
    shared_owner = capability(90)
    owner_barrier = threading.Barrier(5)

    def same_owner(index: int) -> JobAdmission | JobServiceError:
        owner_barrier.wait()
        try:
            return owner_service.admit(
                capability=shared_owner,
                payloads=(payload(index + 70),),
            )
        except JobServiceError as error:
            return error

    with ThreadPoolExecutor(max_workers=5) as executor:
        owner_outcomes = list(executor.map(same_owner, range(5)))
    assert sum(isinstance(item, JobAdmission) for item in owner_outcomes) == 1
    assert (
        sum(isinstance(item, JobServiceAdmissionRejectedError) for item in owner_outcomes) == 4
    ), "\n".join(f"{type(item).__name__}:{getattr(item, 'code', None)}" for item in owner_outcomes)
    assert owner_ids.calls == 1
    assert database_counts(owner_store) == (1, 1)
    assert len(tuple(owner_workspaces.root.glob("*/*/input"))) == 1


def test_post_reservation_failure_removes_workspace_and_rolls_back_store(
    tmp_path: Path,
) -> None:
    canary = b"CANARY_POST_RESERVATION"

    def fail_after_write(
        manager: WorkspaceManager,
        layout: WorkspaceLayout,
        _payloads: Any,
    ) -> MaterializationReceipt:
        manager.create_file(layout, WorkspaceArea.INPUT, "f" * 64, canary)
        raise RuntimeError("private payload path and traceback")

    service, store, workspaces, _clock, ids = environment(
        tmp_path,
        materializer=fail_after_write,
    )
    error = expect_service_error(
        lambda: service.admit(
            capability=capability(1),
            payloads=(payload(),),
            queued=True,
        ),
        JobServiceErrorCode.OPERATION_FAILED,
    )

    assert "private" not in str(error)
    assert ids.calls == 1
    assert database_counts(store) == (0, 0)
    assert tuple(workspaces.root.iterdir()) == ()
    assert canary not in store.database_file.read_bytes()


def test_store_finalization_failure_removes_materialized_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, store, workspaces, _clock, _ids = environment(tmp_path)

    def fail_event(*_args: Any, **_kwargs: Any) -> int:
        raise sqlite3.OperationalError("CANARY_STORE_FINALIZATION")

    monkeypatch.setattr(store, "_insert_event", fail_event)
    error = expect_service_error(
        lambda: service.admit(capability=capability(1), payloads=(payload(),), queued=True),
        JobServiceErrorCode.OPERATION_FAILED,
    )
    assert "CANARY" not in str(error)
    assert database_counts(store) == (0, 0)
    assert tuple(workspaces.root.iterdir()) == ()


def test_workspace_creation_failure_rolls_back_without_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, store, workspaces, _clock, _ids = environment(tmp_path)
    cleanup = Mock()
    monkeypatch.setattr(workspaces, "create", Mock(side_effect=RuntimeError("CANARY_CREATE")))
    monkeypatch.setattr(workspaces, "cleanup", cleanup)

    error = expect_service_error(
        lambda: service.admit(capability=capability(1), payloads=(payload(),)),
        JobServiceErrorCode.OPERATION_FAILED,
    )
    assert "CANARY" not in str(error)
    assert database_counts(store) == (0, 0)
    cleanup.assert_not_called()


def test_post_reservation_cleanup_failure_is_also_content_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_materialization(
        _manager: WorkspaceManager,
        _layout: WorkspaceLayout,
        _payloads: Any,
    ) -> MaterializationReceipt:
        raise RuntimeError("CANARY_MATERIALIZATION_DETAIL")

    service, store, workspaces, _clock, ids = environment(
        tmp_path,
        materializer=fail_materialization,
    )

    original_cleanup = workspaces.cleanup

    def fail_cleanup(_layout: WorkspaceLayout) -> object:
        raise RuntimeError("CANARY_CLEANUP_DETAIL")

    monkeypatch.setattr(workspaces, "cleanup", fail_cleanup)
    error = expect_service_error(
        lambda: service.admit(capability=capability(1), payloads=(payload(),)),
        JobServiceErrorCode.OPERATION_FAILED,
    )
    assert "CANARY" not in str(error)
    assert database_counts(store) == (1, 2)
    tracked = store.list_jobs_for_maintenance()
    assert len(tracked) == 1
    assert tracked[0].execution.state is ExecutionState.TERMINAL
    assert tracked[0].outcome is not None
    assert tracked[0].outcome.kind is TerminalOutcome.ABANDONED
    assert next(workspaces.root.glob("*/*")).is_dir()
    expect_service_error(
        lambda: service.admit(capability=capability(1), payloads=(payload(2),)),
        JobServiceErrorCode.ADMISSION_REJECTED,
        JobServiceAdmissionRejectedError,
    )
    assert ids.calls == 1

    monkeypatch.setattr(workspaces, "cleanup", original_cleanup)
    report = service.cleanup(job_id=tracked[0].job_id, capability=capability(1))
    assert report.verified_absent
    assert tuple(workspaces.root.iterdir()) == ()


def test_unresolved_cleanup_workspaces_are_globally_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_materialization(
        _manager: WorkspaceManager,
        _layout: WorkspaceLayout,
        _payloads: Any,
    ) -> MaterializationReceipt:
        raise RuntimeError("CANARY_MATERIALIZATION")

    service, store, workspaces, _clock, ids = environment(
        tmp_path,
        materializer=fail_materialization,
    )
    monkeypatch.setattr(
        workspaces,
        "cleanup",
        Mock(side_effect=RuntimeError("CANARY_CLEANUP")),
    )
    for number in range(1, DEFAULT_JOB_POLICY.max_staged_global + 1):
        expect_service_error(
            lambda number=number: service.admit(
                capability=capability(number),
                payloads=(payload(number),),
            ),
            JobServiceErrorCode.OPERATION_FAILED,
        )
    expect_service_error(
        lambda: service.admit(capability=capability(20), payloads=(payload(20),)),
        JobServiceErrorCode.ADMISSION_REJECTED,
        JobServiceAdmissionRejectedError,
    )
    assert ids.calls == DEFAULT_JOB_POLICY.max_staged_global
    assert len(store.list_jobs_for_maintenance()) == DEFAULT_JOB_POLICY.max_staged_global


def test_authorized_status_cancel_artifacts_cleanup_and_running_saturation(
    tmp_path: Path,
) -> None:
    process = ProcessSpy()
    service, store, workspaces, clock, _ids = environment(tmp_path, process=process)
    owners = (capability(1), capability(2), capability(3))
    admitted = [
        service.admit(capability=owner, payloads=(payload(index),), queued=True)
        for index, owner in enumerate(owners, start=1)
    ]
    assert service.status(job_id=admitted[0].job.job_id, capability=owners[0]).state_id == "queued"

    first_started = service.start_next()
    assert first_started is not None and first_started.state_id == "running"
    assert process.started == [admitted[0].job.job_id]
    assert service.start_next() is None
    assert process.started == [admitted[0].job.job_id]

    expect_service_error(
        lambda: service.cleanup(job_id=admitted[2].job.job_id, capability=owners[2]),
        JobServiceErrorCode.INVALID_STATE,
    )

    clock.advance(timedelta(seconds=1))
    cancelling = service.cancel(job_id=admitted[0].job.job_id, capability=owners[0])
    assert cancelling.state_id == "cancelling"
    assert process.cancelled == [admitted[0].job.job_id]
    assert (
        service.cancel(
            job_id=admitted[0].job.job_id,
            capability=owners[0],
        ).state_id
        == "cancelling"
    )
    assert process.cancelled == [admitted[0].job.job_id, admitted[0].job.job_id]
    queued_cancel = service.cancel(job_id=admitted[1].job.job_id, capability=owners[1])
    assert queued_cancel.state_id == "cancelling"
    assert process.cancelled == [admitted[0].job.job_id, admitted[0].job.job_id]

    running = store.get_job(job_id=admitted[0].job.job_id, capability=owners[0])
    terminal_at = clock.now() + timedelta(seconds=1)
    terminal = transition_execution(
        running,
        target=ExecutionState.TERMINAL,
        outcome=TerminalOutcome.SUCCEEDED,
        at_utc=terminal_at,
        tombstone_expires_at_utc=terminal_at
        + timedelta(seconds=DEFAULT_JOB_POLICY.tombstone_ttl_seconds),
        expected_version=running.version,
        operation_id="op_" + "a" * 64,
    )
    current = persist(store, owners[0], running, terminal, terminal_at)
    for number, kind in enumerate(
        (ArtifactKind.INPUT, ArtifactKind.WORK, ArtifactKind.RESULT, ArtifactKind.EXPORT),
        start=1,
    ):
        target = (
            CleanupState.VERIFIED_ABSENT
            if kind in {ArtifactKind.INPUT, ArtifactKind.WORK}
            else CleanupState.PRESENT
        )
        updated = transition_artifact(
            current,
            kind=kind,
            target=target,
            at_utc=terminal_at,
            delete_by_utc=(
                terminal_at + timedelta(hours=1) if target is CleanupState.PRESENT else None
            ),
            expected_version=current.version,
            operation_id="op_" + f"{number:064x}",
        )
        current = persist(store, owners[0], current, updated, terminal_at)
    published = publish_export(
        current,
        expected_version=current.version,
        operation_id="op_" + "b" * 64,
    )
    persist(store, owners[0], current, published, terminal_at)

    expect_service_error(
        lambda: service.result(job_id=current.job_id, capability=owners[0]),
        JobServiceErrorCode.ARTIFACT_NOT_AVAILABLE,
    )
    expect_service_error(
        lambda: service.export(job_id=current.job_id, capability=owners[0]),
        JobServiceErrorCode.ARTIFACT_NOT_AVAILABLE,
    )
    existing_layout = workspaces.load(
        current.owner_digest,
        workspace_component(JobId.from_urlsafe(current.job_id)),
    )
    workspaces.cleanup(existing_layout)
    expect_service_error(
        lambda: service.result(job_id=current.job_id, capability=owners[0]),
        JobServiceErrorCode.ARTIFACT_NOT_AVAILABLE,
    )
    clock.advance(timedelta(seconds=1))
    cleanup_report = service.cleanup(job_id=current.job_id, capability=owners[0])
    assert cleanup_report.already_absent
    expect_service_error(
        lambda: service.result(job_id=current.job_id, capability=owners[0]),
        JobServiceErrorCode.ARTIFACT_NOT_AVAILABLE,
    )

    staged_root = tmp_path / "cleanup"
    cleanup_service, cleanup_store, _manager, _cleanup_clock, _cleanup_ids = environment(
        staged_root
    )
    cleanup_owner = capability(9)
    staged = cleanup_service.admit(capability=cleanup_owner, payloads=(payload(9),))
    report = cleanup_service.cleanup(job_id=staged.job.job_id, capability=cleanup_owner)
    cleaned = cleanup_store.get_job(job_id=staged.job.job_id, capability=cleanup_owner)
    assert report.file_count == 1
    assert cleaned.execution.state is ExecutionState.TERMINAL
    assert cleaned.outcome is not None and cleaned.outcome.kind is TerminalOutcome.ABANDONED
    assert all(
        cleaned.artifacts.for_kind(kind).state is CleanupState.VERIFIED_ABSENT
        for kind in ArtifactKind
    )
    assert cleanup_store.list_deletion_events()[0].reason.value == "owner_request"
    assert cleanup_service.cleanup(
        job_id=staged.job.job_id,
        capability=cleanup_owner,
    ).already_absent

    absent_service, absent_store, absent_workspaces, _absent_clock, _absent_ids = environment(
        tmp_path / "absent"
    )
    absent_owner = capability(10)
    absent = absent_service.admit(capability=absent_owner, payloads=(payload(10),))
    absent_layout = next(absent_workspaces.root.glob("*/*"))
    loaded = absent_workspaces.load(absent_layout.parent.name, absent_layout.name)
    absent_workspaces.cleanup(loaded)
    absent_report = absent_service.cleanup(job_id=absent.job.job_id, capability=absent_owner)
    assert absent_report.already_absent
    assert (
        absent_store.get_job(job_id=absent.job.job_id, capability=absent_owner).execution.state
        is ExecutionState.TERMINAL
    )


def test_service_configuration_and_artifact_errors_are_content_free(tmp_path: Path) -> None:
    _service, store, workspaces, clock, _ids = environment(tmp_path / "valid")
    expect_service_error(
        lambda: JobService(
            store=cast(Any, object()),
            workspaces=workspaces,
            clock=clock,
        ),
        JobServiceErrorCode.INVALID_CONFIGURATION,
    )
    no_process = JobService(store=store, workspaces=workspaces, clock=clock)
    expect_service_error(
        no_process.start_next,
        JobServiceErrorCode.INVALID_CONFIGURATION,
    )
    owner = capability(1)
    staged = no_process.admit(capability=owner, payloads=(payload(),))
    expect_service_error(
        lambda: no_process.result(job_id=staged.job.job_id, capability=owner),
        JobServiceErrorCode.ARTIFACT_NOT_AVAILABLE,
    )
    expect_service_error(
        lambda: no_process.export(job_id=staged.job.job_id, capability=owner),
        JobServiceErrorCode.ARTIFACT_NOT_AVAILABLE,
    )
    expect_service_error(
        lambda: no_process.cancel(job_id=staged.job.job_id, capability=owner),
        JobServiceErrorCode.OPERATION_FAILED,
    )

    invalid_operation_service = JobService(
        store=store,
        workspaces=workspaces,
        clock=clock,
        operation_id_factory=cast(Any, lambda: None),
    )
    expect_service_error(
        lambda: invalid_operation_service.cleanup(
            job_id=staged.job.job_id,
            capability=owner,
        ),
        JobServiceErrorCode.OPERATION_FAILED,
    )


def test_start_next_missing_workspace_terminalizes_claim_before_rejecting(tmp_path: Path) -> None:
    process = ProcessSpy()
    service, store, workspaces, _clock, _ids = environment(tmp_path, process=process)
    owner = capability(1)
    admitted = service.admit(capability=owner, payloads=(payload(),), queued=True)
    job_path = next(workspaces.root.glob("*/*"))
    workspaces.cleanup(workspaces.load(job_path.parent.name, job_path.name))

    expect_service_error(service.start_next, JobServiceErrorCode.OPERATION_FAILED)
    assert process.started == []
    assert admitted.job.execution.state is ExecutionState.QUEUED
    failed = store.get_job(job_id=admitted.job.job_id, capability=owner)
    assert failed.execution.state is ExecutionState.TERMINAL
    assert failed.outcome is not None and failed.outcome.kind is TerminalOutcome.CRASHED


def test_start_next_invalid_workspace_terminalizes_claim_without_launch(tmp_path: Path) -> None:
    process = ProcessSpy()
    service, store, workspaces, _clock, _ids = environment(tmp_path, process=process)
    owner = capability(1)
    admitted = service.admit(capability=owner, payloads=(payload(),), queued=True)
    layout = workspaces.load(
        admitted.job.owner_digest,
        workspace_component(JobId.from_urlsafe(admitted.job.job_id)),
    )
    layout.input.chmod(0o755)

    expect_service_error(service.start_next, JobServiceErrorCode.OPERATION_FAILED)
    failed = store.get_job(job_id=admitted.job.job_id, capability=owner)
    assert process.started == []
    assert failed.execution.state is ExecutionState.TERMINAL
    assert failed.outcome is not None and failed.outcome.kind is TerminalOutcome.CRASHED


def test_start_next_gateway_failure_releases_running_slot(tmp_path: Path) -> None:
    class FailFirstStart(ProcessSpy):
        def start(self, job: JobRecord, layout: WorkspaceLayout) -> None:
            super().start(job, layout)
            if len(self.started) == 1:
                raise RuntimeError("CANARY_GATEWAY_START")

    process = FailFirstStart()
    service, store, _workspaces, _clock, _ids = environment(
        tmp_path,
        process=cast(Any, process),
    )
    first_owner = capability(1)
    second_owner = capability(2)
    first = service.admit(capability=first_owner, payloads=(payload(1),), queued=True)
    second = service.admit(capability=second_owner, payloads=(payload(2),), queued=True)

    error = expect_service_error(service.start_next, JobServiceErrorCode.OPERATION_FAILED)
    assert "CANARY" not in str(error)
    failed = store.get_job(job_id=first.job.job_id, capability=first_owner)
    assert failed.execution.state is ExecutionState.TERMINAL
    assert failed.outcome is not None and failed.outcome.kind is TerminalOutcome.CRASHED

    started = service.start_next()
    assert started is not None and started.state_id == "running"
    assert process.started == [first.job.job_id, second.job.job_id]
    assert process.cancelled == [first.job.job_id]


def test_start_failure_with_failed_reap_stays_running_and_retryable(tmp_path: Path) -> None:
    class FailStartAndFirstCancel(ProcessSpy):
        def start(self, job: JobRecord, layout: WorkspaceLayout) -> None:
            super().start(job, layout)
            raise RuntimeError("CANARY_START")

        def cancel(self, job: JobRecord) -> None:
            super().cancel(job)
            if len(self.cancelled) == 1:
                raise RuntimeError("CANARY_REAP")

    process = FailStartAndFirstCancel()
    service, store, _workspaces, _clock, _ids = environment(
        tmp_path,
        process=cast(Any, process),
    )
    owner = capability(1)
    admitted = service.admit(capability=owner, payloads=(payload(),), queued=True)

    error = expect_service_error(service.start_next, JobServiceErrorCode.OPERATION_FAILED)
    assert "CANARY" not in str(error)
    retryable = store.get_job(job_id=admitted.job.job_id, capability=owner)
    assert retryable.execution.state is ExecutionState.RUNNING
    assert retryable.cancellation.state.value == "requested"

    assert service.cancel(job_id=admitted.job.job_id, capability=owner).state_id == "cancelling"
    assert process.cancelled == [admitted.job.job_id, admitted.job.job_id]


def test_cancel_retries_are_idempotent_under_concurrency(tmp_path: Path) -> None:
    process = ProcessSpy()
    service, _store, _workspaces, _clock, _ids = environment(tmp_path, process=process)
    owner = capability(1)
    admitted = service.admit(capability=owner, payloads=(payload(),), queued=True)
    assert service.start_next() is not None
    barrier = threading.Barrier(2)

    def cancel_once() -> str:
        barrier.wait()
        return service.cancel(job_id=admitted.job.job_id, capability=owner).state_id

    with ThreadPoolExecutor(max_workers=2) as executor:
        states = list(executor.map(lambda _index: cancel_once(), range(2)))

    assert states == ["cancelling", "cancelling"]
    assert process.cancelled
    assert set(process.cancelled) == {admitted.job.job_id}


def test_cancel_version_conflict_reloads_only_a_persisted_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = ProcessSpy()
    service, store, _workspaces, _clock, _ids = environment(tmp_path, process=process)
    owner = capability(1)
    admitted = service.admit(capability=owner, payloads=(payload(),), queued=True)
    assert service.start_next() is not None
    original_compare_and_swap = store.compare_and_swap

    def persist_then_report_conflict(**kwargs: Any) -> JobRecord:
        original_compare_and_swap(**kwargs)
        raise VersionConflictError

    monkeypatch.setattr(store, "compare_and_swap", persist_then_report_conflict)
    assert service.cancel(job_id=admitted.job.job_id, capability=owner).state_id == "cancelling"
    assert process.cancelled == [admitted.job.job_id]

    second_service, second_store, _manager, _clock, _ids = environment(
        tmp_path / "unresolved",
        process=ProcessSpy(),
    )
    second_owner = capability(2)
    second = second_service.admit(
        capability=second_owner,
        payloads=(payload(2),),
        queued=True,
    )
    monkeypatch.setattr(
        second_store,
        "compare_and_swap",
        Mock(side_effect=VersionConflictError),
    )
    expect_service_error(
        lambda: second_service.cancel(job_id=second.job.job_id, capability=second_owner),
        JobServiceErrorCode.OPERATION_FAILED,
    )


def test_cancelled_queued_job_is_terminalized_without_launch(tmp_path: Path) -> None:
    process = ProcessSpy()
    service, store, _workspaces, _clock, _ids = environment(tmp_path, process=process)
    first_owner = capability(1)
    second_owner = capability(2)
    first = service.admit(capability=first_owner, payloads=(payload(1),), queued=True)
    second = service.admit(capability=second_owner, payloads=(payload(2),), queued=True)
    assert service.cancel(job_id=first.job.job_id, capability=first_owner).state_id == "cancelling"

    started = service.start_next()
    assert started is not None and started.state_id == "running"
    assert process.started == [second.job.job_id]
    cancelled = store.get_job(job_id=first.job.job_id, capability=first_owner)
    assert cancelled.execution.state is ExecutionState.TERMINAL
    assert cancelled.outcome is not None
    assert cancelled.outcome.kind is TerminalOutcome.CANCELLED


def test_running_cancel_delivery_is_retried_after_gateway_failure(tmp_path: Path) -> None:
    class FailFirstCancel(ProcessSpy):
        def cancel(self, job: JobRecord) -> None:
            super().cancel(job)
            if len(self.cancelled) == 1:
                raise RuntimeError("CANARY_CANCEL_DELIVERY")

    process = FailFirstCancel()
    service, _store, _workspaces, _clock, _ids = environment(
        tmp_path,
        process=cast(Any, process),
    )
    owner = capability(1)
    admitted = service.admit(capability=owner, payloads=(payload(),), queued=True)
    assert service.start_next() is not None
    error = expect_service_error(
        lambda: service.cancel(job_id=admitted.job.job_id, capability=owner),
        JobServiceErrorCode.OPERATION_FAILED,
    )
    assert "CANARY" not in str(error)

    assert service.cancel(job_id=admitted.job.job_id, capability=owner).state_id == "cancelling"
    assert process.cancelled == [admitted.job.job_id, admitted.job.job_id]


def test_analysis_admission_reuse_is_projected_content_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, store, _workspaces, _clock, _ids = environment(tmp_path)
    owner = capability(1)
    admitted = service.admit(capability=owner, payloads=(payload(),), queued=False)

    def reused(**_kwargs):
        raise AnalysisAdmissionReusedError

    monkeypatch.setattr(store, "consume_analysis_admission", reused)
    expect_service_error(
        lambda: service.consume_analysis_admission(
            receipt_hmac="a" * 64,
            job_id=admitted.job.job_id,
            capability=owner,
            at_utc=NOW,
            operation_id="op_" + "b" * 64,
        ),
        JobServiceErrorCode.ANALYSIS_ADMISSION_REUSED,
    )
