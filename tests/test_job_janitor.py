from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NoReturn, cast

import pytest

from delta_lemmata.clock import FakeClock
from delta_lemmata.job_events import DeletionReason
from delta_lemmata.job_janitor import JanitorRunReport, JobJanitor
from delta_lemmata.job_models import (
    ArtifactKind,
    CleanupState,
    ExecutionState,
    JobRecord,
    ScientificResultReceipt,
    TerminalOutcome,
    VersionConflictError,
    request_cancellation,
    transition_artifact,
    transition_execution,
    transition_scientific_execution_claim,
    transition_scientific_success,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY
from delta_lemmata.job_store import SQLiteJobStore, StorePurgeReport
from delta_lemmata.job_workspace import (
    CleanupReport,
    WorkspaceArea,
    WorkspaceError,
    WorkspaceErrorCode,
    WorkspaceLayout,
    WorkspaceManager,
)
from delta_lemmata.recovery_receipt import (
    RecoveryReceiptStore,
    new_acceptance_receipt,
    new_recovery_receipt,
)
from delta_lemmata.session_identity import JobId, SessionCapability, workspace_component

NOW = datetime(2026, 7, 13, 15, tzinfo=UTC)
SECRET = b"janitor-owner-secret-v1-32-bytes!!"
RECEIPT_SECRET = b"janitor-receipt-secret-v1-32bytes"


def operation(number: int) -> str:
    return "op_" + f"{number:064x}"


def scientific_receipt() -> ScientificResultReceipt:
    return ScientificResultReceipt(
        schema_version="scientific-result-receipt-v1",
        request_id="request_" + "1" * 64,
        request_sha256="2" * 64,
        worker_version="stylo-worker-v1",
        result_schema_version="stylo-worker-result-v1",
        analysis_outcome="complete",
        artifact_component="053bf21e22c557bd2e9cc53b858b02603c19200680fe1cc2d885bd1b11d6987b",
        byte_size=4096,
        sha256="3" * 64,
    )


def capability(number: int = 1) -> SessionCapability:
    return SessionCapability.generate(lambda size: bytes([number]) * size)


class JobIds:
    def __init__(self) -> None:
        self._next = 120

    def __call__(self) -> JobId:
        value = self._next
        self._next += 1
        return JobId.generate(lambda size: bytes([value]) * size)


def environment(
    tmp_path: Path,
) -> tuple[SQLiteJobStore, WorkspaceManager, FakeClock, JobJanitor]:
    database_root = tmp_path / "database"
    workspace_root = tmp_path / "workspaces"
    database_root.mkdir(mode=0o700, parents=True)
    workspace_root.mkdir(mode=0o700, parents=True)
    store = SQLiteJobStore(
        database_root / "control.sqlite3",
        owner_secret=SECRET,
        job_id_factory=JobIds(),
    )
    workspaces = WorkspaceManager(workspace_root)
    clock = FakeClock(NOW)
    janitor = JobJanitor(store=store, workspaces=workspaces, clock=clock)
    return store, workspaces, clock, janitor


def layout_for(workspaces: WorkspaceManager, job: JobRecord) -> WorkspaceLayout:
    return workspaces.create(
        job.owner_digest,
        workspace_component(JobId.from_urlsafe(job.job_id)),
    )


def receipt_store(tmp_path: Path) -> RecoveryReceiptStore:
    root = tmp_path / "receipts"
    root.mkdir(mode=0o700, parents=True)
    return RecoveryReceiptStore(root, signing_secret=RECEIPT_SECRET)


def scientific_running_reference(job: JobRecord) -> str:
    references = tuple(
        operation.operation_id
        for operation in job.operations
        if operation.action == "execution:running:none"
    )
    assert len(references) == 1
    return references[0]


def bind_scientific_janitor(
    store: SQLiteJobStore,
    workspaces: WorkspaceManager,
    clock: FakeClock,
    receipts: RecoveryReceiptStore,
) -> JobJanitor:
    return JobJanitor(
        store=store,
        workspaces=workspaces,
        clock=clock,
        recovery_receipts=receipts,
    )


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


def running_job(
    store: SQLiteJobStore,
    owner: SessionCapability,
    *,
    base_operation: int = 1,
) -> JobRecord:
    staged = store.stage_job(capability=owner, at_utc=NOW)
    queued = store.enqueue_job(
        job_id=staged.job_id,
        capability=owner,
        at_utc=NOW + timedelta(seconds=1),
        expected_version=staged.version,
        operation_id=operation(base_operation),
    )
    running = store.claim_next(
        at_utc=NOW + timedelta(seconds=2),
        operation_id=operation(base_operation + 1),
    )
    assert running is not None and running.job_id == queued.job_id
    return running


def terminal_job(
    store: SQLiteJobStore,
    owner: SessionCapability,
    outcome: TerminalOutcome,
    *,
    base_operation: int = 1,
) -> JobRecord:
    running = running_job(store, owner, base_operation=base_operation)
    current = running
    terminal_at = NOW + timedelta(seconds=3)
    terminal_operation = base_operation + 2
    if outcome is TerminalOutcome.CANCELLED:
        requested = request_cancellation(
            current,
            at_utc=NOW + timedelta(seconds=2, microseconds=1),
            expected_version=current.version,
            operation_id=operation(terminal_operation),
        )
        current = persist(
            store,
            owner,
            current,
            requested,
            NOW + timedelta(seconds=2, microseconds=1),
        )
        terminal_operation += 1
    terminal = transition_execution(
        current,
        target=ExecutionState.TERMINAL,
        outcome=outcome,
        at_utc=terminal_at,
        tombstone_expires_at_utc=terminal_at
        + timedelta(seconds=DEFAULT_JOB_POLICY.tombstone_ttl_seconds),
        expected_version=current.version,
        operation_id=operation(terminal_operation),
    )
    return persist(store, owner, current, terminal, terminal_at)


def scientific_terminal_job(
    store: SQLiteJobStore,
    owner: SessionCapability,
    *,
    base_operation: int = 70,
) -> JobRecord:
    running = running_job(store, owner, base_operation=base_operation)
    claim = transition_scientific_execution_claim(
        running,
        expected_version=running.version,
        operation_id=operation(base_operation + 2),
    )
    claimed = persist(
        store,
        owner,
        running,
        claim,
        NOW + timedelta(seconds=2, microseconds=1),
    )
    terminal_at = NOW + timedelta(seconds=3)
    scientific = transition_scientific_success(
        claimed,
        receipt=scientific_receipt(),
        at_utc=terminal_at,
        tombstone_expires_at_utc=terminal_at
        + timedelta(seconds=DEFAULT_JOB_POLICY.tombstone_ttl_seconds),
        expected_version=claimed.version,
        operation_id=operation(base_operation + 3),
    )
    return persist(store, owner, claimed, scientific, terminal_at)


def add_artifact(
    store: SQLiteJobStore,
    owner: SessionCapability,
    job: JobRecord,
    kind: ArtifactKind,
    *,
    deadline: datetime,
    operation_number: int,
) -> JobRecord:
    updated = transition_artifact(
        job,
        kind=kind,
        target=CleanupState.PRESENT,
        at_utc=NOW + timedelta(seconds=3),
        delete_by_utc=deadline,
        expected_version=job.version,
        operation_id=operation(operation_number),
    )
    return persist(store, owner, job, updated, NOW + timedelta(seconds=3))


def test_staged_deadline_is_closed_and_tombstone_purges_only_after_workspace_absence(
    tmp_path: Path,
) -> None:
    store, workspaces, clock, janitor = environment(tmp_path)
    owner = capability()
    staged = store.stage_job(capability=owner, at_utc=NOW)
    layout = layout_for(workspaces, staged)
    workspaces.create_file(layout, WorkspaceArea.INPUT, "a" * 64, b"private corpus")
    deadline = cast(datetime, staged.execution.deadline_at_utc)

    clock.set(deadline - timedelta(microseconds=1))
    before = janitor.run_once()
    assert before.waiting_jobs_expired == 0
    assert store.get_job(job_id=staged.job_id, capability=owner) == staged
    assert layout.job.exists()

    clock.set(deadline)
    at_deadline = janitor.run_once()
    expired = store.get_job(job_id=staged.job_id, capability=owner)
    assert at_deadline.waiting_jobs_expired == 1
    assert at_deadline.cleanup_attempts == 1
    assert at_deadline.artifacts_verified_absent == 4
    assert expired.outcome is not None
    assert expired.outcome.kind is TerminalOutcome.EXPIRED
    assert all(
        expired.artifacts.for_kind(kind).state is CleanupState.VERIFIED_ABSENT
        for kind in ArtifactKind
    )
    assert not layout.job.exists()
    assert store.list_deletion_events()[0].reason is DeletionReason.STAGED_EXPIRED
    duplicate_counters = {"deletion_events_recorded": 0}
    janitor._record_deletion(
        expired,
        CleanupReport(1, 14, False),
        DeletionReason.STAGED_EXPIRED,
        deadline,
        duplicate_counters,
    )
    assert duplicate_counters["deletion_events_recorded"] == 0

    clock.advance(timedelta(seconds=DEFAULT_JOB_POLICY.tombstone_ttl_seconds - 1))
    assert janitor.run_once().purge.tombstones_deleted == 0
    clock.advance(timedelta(seconds=1))
    final = janitor.run_once()
    assert final.purge.tombstones_deleted == 1
    assert final.purge.deletion_events_deleted == 1
    assert store.list_jobs_for_maintenance() == ()


def test_queue_deadline_uses_queue_reason_and_preserves_fifo_history(tmp_path: Path) -> None:
    store, workspaces, clock, janitor = environment(tmp_path)
    owner = capability()
    staged = store.stage_job(capability=owner, at_utc=NOW)
    queued = store.enqueue_job(
        job_id=staged.job_id,
        capability=owner,
        at_utc=NOW + timedelta(seconds=1),
        expected_version=staged.version,
        operation_id=operation(1),
    )
    layout = layout_for(workspaces, queued)
    workspaces.create_file(layout, WorkspaceArea.INPUT, "a" * 64, b"queued")
    deadline = cast(datetime, queued.execution.deadline_at_utc)
    clock.set(deadline)

    report = janitor.run_once()
    expired = store.get_job(job_id=queued.job_id, capability=owner)
    assert report.waiting_jobs_expired == 1
    assert expired.outcome is not None and expired.outcome.kind is TerminalOutcome.EXPIRED
    assert store.list_deletion_events()[0].reason is DeletionReason.QUEUE_EXPIRED


def test_failed_cleanup_is_retried_without_changing_the_terminal_outcome(tmp_path: Path) -> None:
    store, workspaces, clock, janitor = environment(tmp_path)
    owner = capability()
    failed = terminal_job(store, owner, TerminalOutcome.FAILED)
    pending = transition_artifact(
        failed,
        kind=ArtifactKind.INPUT,
        target=CleanupState.PENDING,
        at_utc=NOW + timedelta(seconds=3),
        delete_by_utc=NOW + timedelta(seconds=5),
        expected_version=failed.version,
        operation_id=operation(20),
    )
    failed = persist(store, owner, failed, pending, NOW + timedelta(seconds=3))
    layout = layout_for(workspaces, failed)
    canary = tmp_path / "external-canary"
    canary.write_bytes(b"preserve")
    (layout.input / ("a" * 64)).symlink_to(canary)
    clock.set(NOW + timedelta(seconds=4))

    first = janitor.run_once()
    assert first.cleanup_failures == 1
    assert store.get_job(job_id=failed.job_id, capability=owner) == failed
    assert canary.read_bytes() == b"preserve"

    (layout.input / ("a" * 64)).unlink()
    workspaces.create_file(layout, WorkspaceArea.INPUT, "b" * 64, b"retry")
    second = janitor.run_once()
    cleaned = store.get_job(job_id=failed.job_id, capability=owner)
    assert second.cleanup_failures == 0
    assert cleaned.outcome == failed.outcome
    assert all(
        cleaned.artifacts.for_kind(kind).state is CleanupState.VERIFIED_ABSENT
        for kind in ArtifactKind
    )
    assert not layout.job.exists()


@pytest.mark.parametrize(
    "outcome",
    [
        TerminalOutcome.FAILED,
        TerminalOutcome.CANCELLED,
        TerminalOutcome.TIMED_OUT,
        TerminalOutcome.CRASHED,
        TerminalOutcome.ABANDONED,
    ],
)
def test_every_unsuccessful_running_outcome_is_cleaned_immediately(
    tmp_path: Path,
    outcome: TerminalOutcome,
) -> None:
    store, workspaces, clock, janitor = environment(tmp_path)
    owner = capability()
    terminal = terminal_job(store, owner, outcome)
    assert terminal.outcome is not None
    tombstone_deadline = terminal.tombstone_expires_at_utc
    layout = layout_for(workspaces, terminal)
    workspaces.create_file(layout, WorkspaceArea.INPUT, "a" * 64, b"private input")
    workspaces.create_file(layout, WorkspaceArea.WORK, "b" * 64, b"private work")
    clock.set(NOW + timedelta(seconds=4))

    report = janitor.run_once()
    cleaned = store.get_job(job_id=terminal.job_id, capability=owner)

    assert report.cleanup_attempts == 1
    assert report.cleanup_failures == 0
    assert report.artifacts_verified_absent == 4
    assert report.deletion_events_recorded == 1
    assert cleaned.outcome == terminal.outcome
    assert cleaned.tombstone_expires_at_utc == tombstone_deadline
    assert all(
        cleaned.artifacts.for_kind(kind).state is CleanupState.VERIFIED_ABSENT
        for kind in ArtifactKind
    )
    assert not layout.job.exists()
    events = store.list_deletion_events()
    assert len(events) == 1
    assert events[0].reason is DeletionReason.UNSUCCESSFUL_TERMINAL


def test_success_publishes_only_after_input_work_cleanup_then_expires_outputs(
    tmp_path: Path,
) -> None:
    store, workspaces, clock, janitor = environment(tmp_path)
    owner = capability()
    job = terminal_job(store, owner, TerminalOutcome.SUCCEEDED)
    for number, kind in enumerate(
        (ArtifactKind.WORK, ArtifactKind.RESULT, ArtifactKind.EXPORT), start=10
    ):
        deadline = NOW + timedelta(minutes=15 if kind is ArtifactKind.WORK else 60)
        job = add_artifact(
            store,
            owner,
            job,
            kind,
            deadline=deadline,
            operation_number=number,
        )
    layout = layout_for(workspaces, job)
    workspaces.create_file(layout, WorkspaceArea.INPUT, "a" * 64, b"input")
    workspaces.create_file(layout, WorkspaceArea.WORK, "b" * 64, b"normalized")
    workspaces.create_file(layout, WorkspaceArea.RESULT, "c" * 64, b"result")
    workspaces.create_file(layout, WorkspaceArea.EXPORT, "d" * 64, b"export")
    workspaces.create_file(layout, WorkspaceArea.CONTROL, "e" * 64, b"receipt")
    clock.set(NOW + timedelta(seconds=4))

    first = janitor.run_once()
    published = store.get_job(job_id=job.job_id, capability=owner)
    assert first.exports_published == 1
    assert published.export_available is True
    assert published.artifacts.input.state is CleanupState.VERIFIED_ABSENT
    assert published.artifacts.work.state is CleanupState.VERIFIED_ABSENT
    assert not tuple(layout.input.iterdir())
    assert not tuple(layout.work.iterdir())
    assert (layout.result / ("c" * 64)).read_bytes() == b"result"
    assert (layout.export / ("d" * 64)).read_bytes() == b"export"

    clock.set(deadline - timedelta(microseconds=1))
    assert janitor.run_once().artifacts_verified_absent == 0
    assert store.get_job(job_id=job.job_id, capability=owner).export_available is True

    clock.set(deadline)
    expired_report = janitor.run_once()
    expired = store.get_job(job_id=job.job_id, capability=owner)
    assert expired_report.artifacts_verified_absent == 2
    assert expired_report.workspaces_removed == 1
    assert expired.export_available is False
    assert expired.artifacts.result.state is CleanupState.VERIFIED_ABSENT
    assert expired.artifacts.export.state is CleanupState.VERIFIED_ABSENT
    assert not layout.job.exists()
    reasons = {event.reason for event in store.list_deletion_events()}
    assert reasons == {
        DeletionReason.SUCCESSFUL_TERMINAL,
        DeletionReason.RESULT_EXPIRED,
        DeletionReason.EXPORT_EXPIRED,
    }


def test_due_unpublished_export_is_deleted_without_transient_publication(tmp_path: Path) -> None:
    store, workspaces, clock, janitor = environment(tmp_path)
    owner = capability()
    job = terminal_job(store, owner, TerminalOutcome.SUCCEEDED)
    deadline = NOW + timedelta(seconds=4)
    job = add_artifact(
        store,
        owner,
        job,
        ArtifactKind.EXPORT,
        deadline=deadline,
        operation_number=10,
    )
    layout = layout_for(workspaces, job)
    workspaces.create_file(layout, WorkspaceArea.INPUT, "a" * 64, b"input")
    workspaces.create_file(layout, WorkspaceArea.EXPORT, "b" * 64, b"export")
    clock.set(deadline)

    report = janitor.run_once()
    cleaned = store.get_job(job_id=job.job_id, capability=owner)
    assert report.exports_published == 0
    assert cleaned.export_available is False
    assert cleaned.artifacts.export.state is CleanupState.VERIFIED_ABSENT
    assert not layout.job.exists()


def test_success_without_a_workspace_verifies_absence_without_publishing(tmp_path: Path) -> None:
    store, _workspaces, clock, janitor = environment(tmp_path)
    owner = capability()
    job = terminal_job(store, owner, TerminalOutcome.SUCCEEDED)
    clock.set(NOW + timedelta(seconds=4))

    report = janitor.run_once()
    cleaned = store.get_job(job_id=job.job_id, capability=owner)
    assert report.cleanup_attempts == 1
    assert report.workspaces_removed == 0
    assert cleaned.artifacts.input.state is CleanupState.VERIFIED_ABSENT
    assert cleaned.artifacts.work.state is CleanupState.VERIFIED_ABSENT
    assert cleaned.export_available is False


def test_startup_recovery_requires_guardian_proof_and_records_abandonment(tmp_path: Path) -> None:
    store, workspaces, clock, janitor = environment(tmp_path)
    owner = capability()
    running = running_job(store, owner)
    waiting = store.stage_job(capability=capability(2), at_utc=NOW)
    layout = layout_for(workspaces, running)
    workspaces.create_file(layout, WorkspaceArea.INPUT, "a" * 64, b"running")
    clock.set(NOW + timedelta(seconds=5))

    unresolved = janitor.recover_startup()
    assert unresolved.running_recovery_unresolved == 1
    assert store.get_job(job_id=running.job_id, capability=owner) == running
    assert waiting.execution.state is ExecutionState.STAGED
    assert layout.job.exists()

    raised = janitor.recover_startup(lambda _job: (_ for _ in ()).throw(RuntimeError()))
    assert raised.running_recovery_unresolved == 1
    assert janitor.recover_startup(lambda _job: False).running_recovery_unresolved == 1

    recovered = janitor.recover_startup(lambda _job: True)
    abandoned = store.get_job(job_id=running.job_id, capability=owner)
    assert recovered.running_jobs_recovered == 1
    assert recovered.running_recovery_unresolved == 0
    assert abandoned.outcome is not None
    assert abandoned.outcome.kind is TerminalOutcome.ABANDONED
    assert not layout.job.exists()
    assert store.list_deletion_events()[0].reason is DeletionReason.STARTUP_RECOVERY


def test_startup_recovery_proof_verifies_all_scientific_artifacts_without_losing_receipt(
    tmp_path: Path,
) -> None:
    store, workspaces, clock, _janitor = environment(tmp_path)
    owner = capability()
    scientific = scientific_terminal_job(store, owner)
    original_outcome = scientific.outcome
    original_receipt = scientific.scientific_result
    receipts = receipt_store(tmp_path)
    receipts.write(
        new_recovery_receipt(
            job_id=JobId.from_urlsafe(scientific.job_id),
            execution_reference=scientific_running_reference(scientific),
            occurred_at_utc=NOW + timedelta(seconds=3),
            workspace_verified_absent=True,
            file_count=0,
            byte_count=0,
            signing_secret=RECEIPT_SECRET,
            event_ttl_seconds=DEFAULT_JOB_POLICY.event_ttl_seconds,
        )
    )
    janitor = bind_scientific_janitor(store, workspaces, clock, receipts)
    clock.set(NOW + timedelta(seconds=4))

    report = janitor.recover_startup()
    recovered = store.get_job(job_id=scientific.job_id, capability=owner)
    assert report.scientific_results_recovered == 1
    assert report.scientific_recovery_unresolved == 0
    assert report.running_jobs_recovered == 0
    assert report.running_recovery_unresolved == 0
    assert report.cleanup_attempts == 1
    assert report.artifacts_verified_absent == len(ArtifactKind)
    assert all(
        recovered.artifacts.for_kind(kind).state is CleanupState.VERIFIED_ABSENT
        for kind in ArtifactKind
    )
    assert recovered.outcome == original_outcome
    assert recovered.scientific_result == original_receipt
    assert store.list_deletion_events()[0].reason is DeletionReason.STARTUP_RECOVERY


def test_startup_unresolved_scientific_recovery_retains_result(tmp_path: Path) -> None:
    store, workspaces, clock, _janitor = environment(tmp_path)
    owner = capability()
    scientific = scientific_terminal_job(store, owner)
    result_receipt = scientific.scientific_result
    assert result_receipt is not None
    layout = layout_for(workspaces, scientific)
    workspaces.create_file(
        layout,
        WorkspaceArea.RESULT,
        result_receipt.artifact_component,
        b"pending-result",
    )
    janitor = bind_scientific_janitor(
        store,
        workspaces,
        clock,
        receipt_store(tmp_path),
    )
    clock.set(NOW + timedelta(seconds=4))

    report = janitor.recover_startup()
    retained = store.get_job(job_id=scientific.job_id, capability=owner)
    assert report.scientific_results_recovered == 0
    assert report.scientific_recovery_unresolved == 1
    assert retained.artifacts.result == scientific.artifacts.result
    assert retained.artifacts.result.state is CleanupState.PRESENT
    assert retained.outcome == scientific.outcome
    assert retained.scientific_result == scientific.scientific_result
    assert retained.artifacts.input.state is CleanupState.VERIFIED_ABSENT
    assert retained.artifacts.work.state is CleanupState.VERIFIED_ABSENT
    assert retained.artifacts.result.state is CleanupState.PRESENT
    assert (layout.result / result_receipt.artifact_component).is_file()
    assert store.list_deletion_events()[0].reason is DeletionReason.SUCCESSFUL_TERMINAL

    result_deadline = retained.artifacts.result.delete_by_utc
    assert result_deadline is not None
    clock.set(result_deadline)
    expired_report = janitor.run_once()
    expired = store.get_job(job_id=scientific.job_id, capability=owner)
    assert expired_report.scientific_recovery_unresolved == 1
    assert expired.artifacts.result.state is CleanupState.VERIFIED_ABSENT
    assert expired.scientific_result == result_receipt
    assert not layout.job.exists()


def test_startup_without_recovery_callback_retains_scientific_result(tmp_path: Path) -> None:
    store, _workspaces, clock, janitor = environment(tmp_path)
    owner = capability()
    scientific = scientific_terminal_job(store, owner)
    clock.set(NOW + timedelta(seconds=4))

    report = janitor.recover_startup()
    retained = store.get_job(job_id=scientific.job_id, capability=owner)
    assert report.scientific_results_recovered == 0
    assert report.scientific_recovery_unresolved == 1
    assert retained.outcome == scientific.outcome
    assert retained.scientific_result == scientific.scientific_result
    assert retained.scientific_result_confirmed is False
    assert retained.artifacts.input.state is CleanupState.VERIFIED_ABSENT
    assert retained.artifacts.work.state is CleanupState.VERIFIED_ABSENT
    assert store.list_deletion_events()[0].reason is DeletionReason.SUCCESSFUL_TERMINAL


def test_startup_scientific_recovery_callback_exception_is_counted_and_retained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, workspaces, clock, _janitor = environment(tmp_path)
    owner = capability()
    scientific = scientific_terminal_job(store, owner)
    receipts = receipt_store(tmp_path)
    janitor = bind_scientific_janitor(store, workspaces, clock, receipts)
    clock.set(NOW + timedelta(seconds=4))

    def failed_proof(_job: JobRecord, *, at_utc: datetime) -> NoReturn:
        assert at_utc == clock.now()
        raise RuntimeError("private callback failure")

    monkeypatch.setattr(receipts, "scientific_disposition", failed_proof)
    report = janitor.recover_startup()
    retained = store.get_job(job_id=scientific.job_id, capability=owner)
    assert report.scientific_results_recovered == 0
    assert report.scientific_recovery_unresolved == 1
    assert report.running_recovery_unresolved == 0
    assert retained.artifacts.result == scientific.artifacts.result
    assert retained.artifacts.result.state is CleanupState.PRESENT
    assert retained.outcome == scientific.outcome
    assert retained.scientific_result == scientific.scientific_result


def test_startup_accepted_scientific_result_is_confirmed_before_cleanup(
    tmp_path: Path,
) -> None:
    store, workspaces, clock, initial_janitor = environment(tmp_path)
    owner = capability()
    scientific = scientific_terminal_job(store, owner)
    item = scientific.scientific_result
    assert item is not None
    clock.set(NOW + timedelta(seconds=4))
    assert initial_janitor.run_once().scientific_recovery_unresolved == 1
    advanced = store.get_job(job_id=scientific.job_id, capability=owner)
    assert advanced.version > scientific.version
    assert advanced.artifacts.result.state is CleanupState.PRESENT
    receipts = receipt_store(tmp_path)
    receipts.write(
        new_acceptance_receipt(
            job_id=JobId.from_urlsafe(scientific.job_id),
            execution_reference=scientific_running_reference(scientific),
            occurred_at_utc=NOW + timedelta(seconds=3),
            terminal_version=scientific.version,
            terminal_outcome=TerminalOutcome.SUCCEEDED,
            artifact_sha256=item.sha256,
            artifact_byte_size=item.byte_size,
            signing_secret=RECEIPT_SECRET,
            event_ttl_seconds=DEFAULT_JOB_POLICY.event_ttl_seconds,
        )
    )
    janitor = bind_scientific_janitor(store, workspaces, clock, receipts)

    report = janitor.recover_startup()
    confirmed = store.get_job(job_id=scientific.job_id, capability=owner)

    assert report.scientific_results_confirmed == 1
    assert report.scientific_results_recovered == 0
    assert report.scientific_recovery_unresolved == 0
    assert confirmed.scientific_result_confirmed is True
    assert confirmed.scientific_result == scientific.scientific_result
    assert confirmed.artifacts.result.state is CleanupState.PRESENT
    assert confirmed.artifacts.input.state is CleanupState.VERIFIED_ABSENT
    assert confirmed.artifacts.work.state is CleanupState.VERIFIED_ABSENT


def test_startup_recovery_removes_only_untracked_verified_workspaces(tmp_path: Path) -> None:
    store, workspaces, _clock, janitor = environment(tmp_path)
    owner = capability()
    known = store.stage_job(capability=owner, at_utc=NOW)
    known_layout = layout_for(workspaces, known)
    orphan = workspaces.create("a" * 64, "b" * 64)
    workspaces.create_file(orphan, WorkspaceArea.INPUT, "c" * 64, b"orphan corpus")

    assert {layout.job for layout in workspaces.list_layouts()} == {
        known_layout.job,
        orphan.job,
    }
    assert janitor.run_once().untracked_workspaces_removed == 0
    assert orphan.job.exists()

    recovered = janitor.recover_startup()
    assert recovered.untracked_workspaces_removed == 1
    assert recovered.cleanup_attempts == 1
    assert recovered.workspaces_removed == 1
    assert known_layout.job.exists()
    assert not orphan.job.exists()

    failed_store, failed_workspaces, _clock, failed_janitor = environment(tmp_path / "failed")
    failed_orphan = failed_workspaces.create("d" * 64, "e" * 64)

    def fail_cleanup(_layout: WorkspaceLayout) -> CleanupReport:
        raise WorkspaceError(WorkspaceErrorCode.CLEANUP_FAILED)

    failed_workspaces.cleanup = fail_cleanup  # type: ignore[method-assign]
    failed = failed_janitor.recover_startup()
    assert failed_store.list_jobs_for_maintenance() == ()
    assert failed.cleanup_attempts == 1
    assert failed.cleanup_failures == 1
    assert failed.untracked_workspaces_removed == 0
    assert failed_orphan.job.exists()


def test_janitor_configuration_loop_and_conflict_paths_are_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, workspaces, clock, janitor = environment(tmp_path)
    with pytest.raises(ValueError, match="INVALID_CONFIGURATION"):
        JobJanitor(
            store=cast(Any, object()),
            workspaces=workspaces,
            clock=clock,
        )
    with pytest.raises(ValueError, match="INVALID_RECOVERY"):
        janitor.recover_startup(cast(Any, object()))
    with pytest.raises(ValueError, match="INVALID_CONFIGURATION"):
        JobJanitor(
            store=store,
            workspaces=workspaces,
            clock=clock,
            recovery_receipts=cast(Any, object()),
        )
    with pytest.raises(ValueError, match="INVALID_LOOP"):
        janitor.run_continuously(stop_event=threading.Event(), interval_seconds=0)
    with pytest.raises(ValueError, match="INVALID_LOOP"):
        janitor.run_continuously(
            stop_event=cast(Any, object()),
            interval_seconds=1,
        )

    stopped = threading.Event()
    stopped.set()
    janitor.run_continuously(stop_event=stopped, interval_seconds=0.001)

    calls = 0
    stop_after_one = threading.Event()

    def one_run() -> JanitorRunReport:
        nonlocal calls
        calls += 1
        stop_after_one.set()
        return JanitorRunReport(
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            StorePurgeReport(0, 0, 0, 0),
        )

    monkeypatch.setattr(janitor, "run_once", one_run)
    janitor.run_continuously(stop_event=stop_after_one, interval_seconds=0.001)
    assert calls == 1

    conflict_store, conflict_workspaces, conflict_clock, conflict_janitor = environment(
        tmp_path / "conflict"
    )
    conflict_owner = capability(2)
    running = running_job(conflict_store, conflict_owner)
    layout_for(conflict_workspaces, running)

    def conflict(**_kwargs: object) -> JobRecord:
        raise VersionConflictError

    monkeypatch.setattr(conflict_store, "maintenance_compare_and_swap", conflict)
    conflict_clock.set(NOW + timedelta(seconds=5))
    report = conflict_janitor.recover_startup(lambda _job: True)
    assert report.state_conflicts == 1
    assert report.running_jobs_recovered == 0

    race_store, _race_workspaces, race_clock, race_janitor = environment(tmp_path / "race")
    race_owner = capability(3)
    terminal = terminal_job(race_store, race_owner, TerminalOutcome.FAILED)

    def terminal_conflict(
        _job: JobRecord,
        _now: datetime,
        _reason: DeletionReason | None,
        _counters: dict[str, int],
    ) -> JobRecord:
        raise VersionConflictError

    monkeypatch.setattr(race_janitor, "_maintain_terminal", terminal_conflict)
    race_clock.set(NOW + timedelta(seconds=4))
    race_report = race_janitor.run_once()
    assert race_report.state_conflicts == 1
    assert race_store.get_job(job_id=terminal.job_id, capability=race_owner) == terminal


def test_store_purge_requires_a_frozenset_workspace_proof(tmp_path: Path) -> None:
    store, _workspaces, _clock, _janitor = environment(tmp_path)
    with pytest.raises(Exception) as captured:
        store.purge_expired(
            at_utc=NOW,
            workspace_absent_job_ids=cast(Any, set()),
        )
    assert str(captured.value) == "JOB_STORE_INVALID_UPDATE"


def test_private_terminal_guard_returns_invalid_snapshot_unchanged(tmp_path: Path) -> None:
    store, _workspaces, _clock, janitor = environment(tmp_path)
    owner = capability()
    terminal = terminal_job(store, owner, TerminalOutcome.FAILED)
    invalid = terminal.model_copy(update={"outcome": None})
    counters: dict[str, int] = {}
    assert janitor._maintain_terminal(invalid, NOW, None, counters) is invalid


def test_workspace_error_during_final_absence_probe_is_counted(tmp_path: Path) -> None:
    store, workspaces, clock, janitor = environment(tmp_path)
    owner = capability()
    failed = terminal_job(store, owner, TerminalOutcome.FAILED)
    layout = layout_for(workspaces, failed)
    workspaces.cleanup(layout)
    clock.set(NOW + timedelta(seconds=4))

    original = workspaces.load_optional
    calls = 0

    def fail_second(owner_component: str, job_component: str) -> WorkspaceLayout | None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise WorkspaceError(WorkspaceErrorCode.INVALID_LAYOUT)
        return original(owner_component, job_component)

    workspaces.load_optional = fail_second  # type: ignore[method-assign]
    report = janitor.run_once()
    assert report.cleanup_failures == 1
