from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from delta_lemmata.job_events import DeletionEvent, DeletionReason, new_deletion_event
from delta_lemmata.job_models import (
    ArtifactKind,
    CleanupState,
    ExecutionState,
    JobRecord,
    ScientificResultReceipt,
    TerminalOutcome,
    confirm_scientific_result,
    publish_export,
    retire_export,
    transition_artifact,
    transition_execution,
    transition_scientific_execution_claim,
    transition_scientific_success,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY
from delta_lemmata.job_store import (
    JobNotAvailableError,
    JobStoreError,
    JobStoreErrorCode,
    SQLiteJobStore,
    StorePurgeReport,
)
from delta_lemmata.session_identity import JobId, SessionCapability

NOW = datetime(2026, 7, 13, 12, tzinfo=UTC)
SECRET = b"retention-owner-secret-v1-32-bytes"


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


def capability(number: int) -> SessionCapability:
    return SessionCapability.generate(lambda size: bytes([number]) * size)


class JobIds:
    def __init__(self) -> None:
        self._next = 100

    def __call__(self) -> JobId:
        value = self._next
        self._next += 1
        return JobId.generate(lambda size: bytes([value]) * size)


def make_store(path: Path) -> SQLiteJobStore:
    return SQLiteJobStore(path, owner_secret=SECRET, job_id_factory=JobIds())


def persist_owned(
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


def terminal_staged(
    store: SQLiteJobStore,
    owner: SessionCapability,
    *,
    outcome: TerminalOutcome = TerminalOutcome.EXPIRED,
    operation_number: int = 1,
) -> tuple[JobRecord, datetime]:
    staged = store.stage_job(capability=owner, at_utc=NOW)
    terminal_at = cast(datetime, staged.execution.deadline_at_utc)
    terminal = transition_execution(
        staged,
        target=ExecutionState.TERMINAL,
        outcome=outcome,
        at_utc=terminal_at,
        tombstone_expires_at_utc=terminal_at
        + timedelta(seconds=DEFAULT_JOB_POLICY.tombstone_ttl_seconds),
        expected_version=staged.version,
        operation_id=operation(operation_number),
    )
    return (
        store.maintenance_compare_and_swap(
            job_id=staged.job_id,
            expected_version=staged.version,
            updated=terminal,
            at_utc=terminal_at,
        ),
        terminal_at,
    )


def deletion_for(
    job: JobRecord,
    *,
    at_utc: datetime,
    reason: DeletionReason,
    file_count: int = 1,
    byte_count: int = 32,
) -> DeletionEvent:
    return new_deletion_event(
        job_id=JobId.from_urlsafe(job.job_id),
        occurred_at_utc=at_utc,
        reason=reason,
        file_count=file_count,
        byte_count=byte_count,
        policy_version="job-policy-v1",
        event_ttl_seconds=DEFAULT_JOB_POLICY.event_ttl_seconds,
    )


def test_schema_v1_is_upgraded_to_payload_free_deletion_ledger(tmp_path: Path) -> None:
    database_file = tmp_path / "migration.sqlite3"
    with closing(sqlite3.connect(database_file)) as connection:
        connection.execute("PRAGMA user_version = 1")
        connection.commit()

    store = make_store(database_file)
    assert store.list_jobs_for_maintenance() == ()
    with closing(sqlite3.connect(database_file)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (3,)
        tables = {
            cast(str, row[0])
            for row in connection.execute("SELECT name FROM sqlite_schema WHERE type = 'table'")
        }
    assert tables == {"analysis_admissions", "jobs", "events", "deletion_events"}


def test_maintenance_transition_and_deletion_event_are_atomic_and_content_free(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "control.sqlite3"
    store = make_store(database_file)
    owner = capability(1)
    terminal, terminal_at = terminal_staged(store, owner)
    assert store.list_jobs_for_maintenance() == (terminal,)

    absent = transition_artifact(
        terminal,
        kind=ArtifactKind.INPUT,
        target=CleanupState.VERIFIED_ABSENT,
        at_utc=terminal_at,
        expected_version=terminal.version,
        operation_id=operation(2),
    )
    event = deletion_for(
        terminal,
        at_utc=terminal_at,
        reason=DeletionReason.STAGED_EXPIRED,
    )
    invalid_events = (
        event.model_copy(update={"job_reference_digest": "f" * 64}),
        event.model_copy(update={"policy_version": "job-policy-v2"}),
        event.model_copy(update={"occurred_at_utc": terminal_at + timedelta(seconds=1)}),
        event.model_copy(update={"expires_at_utc": event.expires_at_utc + timedelta(seconds=1)}),
    )
    for invalid_event in invalid_events:
        with pytest.raises(JobStoreError) as captured:
            store.maintenance_compare_and_swap(
                job_id=terminal.job_id,
                expected_version=terminal.version,
                updated=absent,
                at_utc=terminal_at,
                deletion_event=invalid_event,
            )
        assert captured.value.code is JobStoreErrorCode.INVALID_UPDATE
        assert store.list_jobs_for_maintenance() == (terminal,)
        assert store.list_deletion_events() == ()

    stored = store.maintenance_compare_and_swap(
        job_id=terminal.job_id,
        expected_version=terminal.version,
        updated=absent,
        at_utc=terminal_at,
        deletion_event=event,
    )
    assert stored == absent
    assert store.list_deletion_events() == (event,)
    assert (
        store.record_deletion_event(
            job_id=stored.job_id,
            event=event,
            at_utc=terminal_at,
        )
        is False
    )
    encoded = b"".join(
        path.read_bytes()
        for path in (
            database_file,
            Path(f"{database_file}-wal"),
            Path(f"{database_file}-shm"),
        )
        if path.exists()
    ).lower()
    for canary in (
        b"canary corpus text",
        b"filename-canary.txt",
        b"/absolute/path",
        b"stdout",
        b"stderr",
        b"traceback",
    ):
        assert canary not in encoded

    with pytest.raises(JobStoreError) as repeated:
        store.maintenance_compare_and_swap(
            job_id=stored.job_id,
            expected_version=stored.version,
            updated=stored,
            at_utc=terminal_at,
            deletion_event=event,
        )
    assert repeated.value.code is JobStoreErrorCode.INVALID_UPDATE
    assert (
        store.maintenance_compare_and_swap(
            job_id=stored.job_id,
            expected_version=stored.version,
            updated=stored,
            at_utc=terminal_at,
        )
        == stored
    )


def test_scientific_result_cleanup_retains_terminal_outcome_and_receipt(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path / "scientific-retention.sqlite3")
    owner = capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    store.enqueue_job(
        job_id=staged.job_id,
        capability=owner,
        at_utc=NOW + timedelta(seconds=1),
        expected_version=staged.version,
        operation_id=operation(40),
    )
    running = store.claim_next(
        at_utc=NOW + timedelta(seconds=2),
        operation_id=operation(41),
    )
    assert running is not None
    claim = transition_scientific_execution_claim(
        running,
        expected_version=running.version,
        operation_id=operation(42),
    )
    claimed = persist_owned(
        store,
        owner,
        running,
        claim,
        NOW + timedelta(seconds=2, microseconds=1),
    )
    item = scientific_receipt()
    terminal_at = NOW + timedelta(seconds=3)
    scientific = transition_scientific_success(
        claimed,
        receipt=item,
        at_utc=terminal_at,
        tombstone_expires_at_utc=terminal_at + timedelta(days=7),
        expected_version=claimed.version,
        operation_id=operation(43),
    )
    scientific = persist_owned(store, owner, claimed, scientific, terminal_at)
    confirmation = confirm_scientific_result(
        scientific,
        expected_version=scientific.version,
        operation_id=operation(44),
    )
    scientific = persist_owned(
        store,
        owner,
        scientific,
        confirmation,
        terminal_at + timedelta(microseconds=1),
    )
    result_deadline = cast(datetime, scientific.artifacts.result.delete_by_utc)
    cleaned = transition_artifact(
        scientific,
        kind=ArtifactKind.RESULT,
        target=CleanupState.VERIFIED_ABSENT,
        at_utc=result_deadline,
        expected_version=scientific.version,
        operation_id=operation(45),
    )
    event = deletion_for(
        scientific,
        at_utc=result_deadline,
        reason=DeletionReason.RESULT_EXPIRED,
        byte_count=item.byte_size,
    )

    stored = store.maintenance_compare_and_swap(
        job_id=scientific.job_id,
        expected_version=scientific.version,
        updated=cleaned,
        at_utc=result_deadline,
        deletion_event=event,
    )
    assert stored.artifacts.result.state is CleanupState.VERIFIED_ABSENT
    assert stored.outcome == scientific.outcome
    assert stored.scientific_result == item
    assert stored.scientific_result_confirmed is True
    assert (
        sum(
            operation.action.startswith("scientific:terminal:succeeded:")
            for operation in stored.operations
        )
        == 1
    )
    assert store.list_jobs_for_maintenance() == (stored,)
    assert store.list_deletion_events() == (event,)


def test_maintenance_api_rejects_unknown_stale_and_untyped_updates(tmp_path: Path) -> None:
    store = make_store(tmp_path / "control.sqlite3")
    terminal, terminal_at = terminal_staged(store, capability(1))
    absent = transition_artifact(
        terminal,
        kind=ArtifactKind.INPUT,
        target=CleanupState.VERIFIED_ABSENT,
        at_utc=terminal_at,
        expected_version=terminal.version,
        operation_id=operation(2),
    )

    with pytest.raises(JobNotAvailableError):
        store.maintenance_compare_and_swap(
            job_id=JobId.generate(lambda size: b"x" * size),
            expected_version=terminal.version,
            updated=absent,
            at_utc=terminal_at,
        )
    with pytest.raises(JobStoreError) as invalid:
        store.maintenance_compare_and_swap(
            job_id=terminal.job_id,
            expected_version=terminal.version,
            updated=cast(Any, object()),
            at_utc=terminal_at,
        )
    assert invalid.value.code is JobStoreErrorCode.INVALID_UPDATE
    with pytest.raises(JobStoreError) as invalid_event:
        store.maintenance_compare_and_swap(
            job_id=terminal.job_id,
            expected_version=terminal.version,
            updated=absent,
            at_utc=terminal_at,
            deletion_event=cast(Any, object()),
        )
    assert invalid_event.value.code is JobStoreErrorCode.INVALID_UPDATE
    with pytest.raises(JobStoreError) as invalid_ledger_event:
        store.record_deletion_event(
            job_id=terminal.job_id,
            event=cast(Any, object()),
            at_utc=terminal_at,
        )
    assert invalid_ledger_event.value.code is JobStoreErrorCode.INVALID_UPDATE
    with pytest.raises(Exception) as stale:
        store.maintenance_compare_and_swap(
            job_id=terminal.job_id,
            expected_version=terminal.version + 1,
            updated=absent,
            at_utc=terminal_at,
        )
    assert str(stale.value) == "JOB_VERSION_CONFLICT"


def test_published_export_retirement_is_persisted_with_deletion_evidence(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path / "control.sqlite3")
    owner = capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    queued_at = NOW + timedelta(seconds=1)
    queued = store.enqueue_job(
        job_id=staged.job_id,
        capability=owner,
        at_utc=queued_at,
        expected_version=staged.version,
        operation_id=operation(10),
    )
    running_at = NOW + timedelta(seconds=2)
    running = store.claim_next(at_utc=running_at, operation_id=operation(11))
    assert running is not None and running.job_id == queued.job_id
    terminal_at = NOW + timedelta(seconds=3)
    job = transition_execution(
        running,
        target=ExecutionState.TERMINAL,
        outcome=TerminalOutcome.SUCCEEDED,
        at_utc=terminal_at,
        tombstone_expires_at_utc=terminal_at
        + timedelta(seconds=DEFAULT_JOB_POLICY.tombstone_ttl_seconds),
        expected_version=running.version,
        operation_id=operation(12),
    )
    job = persist_owned(store, owner, running, job, terminal_at)
    for number, kind in enumerate((ArtifactKind.WORK, ArtifactKind.EXPORT), start=13):
        export_deadline = NOW + timedelta(minutes=15 if kind is ArtifactKind.WORK else 60)
        updated = transition_artifact(
            job,
            kind=kind,
            target=CleanupState.PRESENT,
            at_utc=terminal_at,
            delete_by_utc=export_deadline,
            expected_version=job.version,
            operation_id=operation(number),
        )
        job = persist_owned(store, owner, job, updated, terminal_at)
    for number, kind in enumerate((ArtifactKind.INPUT, ArtifactKind.WORK), start=15):
        updated = transition_artifact(
            job,
            kind=kind,
            target=CleanupState.VERIFIED_ABSENT,
            at_utc=terminal_at,
            expected_version=job.version,
            operation_id=operation(number),
        )
        job = persist_owned(store, owner, job, updated, terminal_at)
    published = publish_export(
        job,
        expected_version=job.version,
        operation_id=operation(17),
    )
    job = persist_owned(store, owner, job, published, terminal_at)
    retired = retire_export(
        job,
        at_utc=export_deadline,
        expected_version=job.version,
        operation_id=operation(18),
    )
    event = deletion_for(
        job,
        at_utc=export_deadline,
        reason=DeletionReason.EXPORT_EXPIRED,
    )
    malformed_export = retired.artifacts.export.model_copy(update={"verified_at_utc": None})
    malformed_artifacts = retired.artifacts.model_copy(update={"export": malformed_export})
    malformed_retired = retired.model_copy(update={"artifacts": malformed_artifacts})
    with pytest.raises(JobStoreError) as malformed:
        store.maintenance_compare_and_swap(
            job_id=job.job_id,
            expected_version=job.version,
            updated=malformed_retired,
            at_utc=export_deadline,
        )
    assert malformed.value.code is JobStoreErrorCode.INVALID_UPDATE
    assert (
        store.maintenance_compare_and_swap(
            job_id=job.job_id,
            expected_version=job.version,
            updated=retired,
            at_utc=export_deadline,
            deletion_event=event,
        )
        == retired
    )
    assert store.list_deletion_events() == (event,)


def test_purge_removes_expired_ledgers_and_clean_tombstones_but_blocks_retained_data(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path / "control.sqlite3")
    clean, terminal_at = terminal_staged(store, capability(1), operation_number=30)
    clean_absent = transition_artifact(
        clean,
        kind=ArtifactKind.INPUT,
        target=CleanupState.VERIFIED_ABSENT,
        at_utc=terminal_at,
        expected_version=clean.version,
        operation_id=operation(31),
    )
    event = deletion_for(
        clean,
        at_utc=terminal_at,
        reason=DeletionReason.STAGED_EXPIRED,
    )
    store.maintenance_compare_and_swap(
        job_id=clean.job_id,
        expected_version=clean.version,
        updated=clean_absent,
        at_utc=terminal_at,
        deletion_event=event,
    )
    retained, _ = terminal_staged(
        store,
        capability(2),
        operation_number=32,
    )
    early = store.purge_expired(
        at_utc=terminal_at + timedelta(seconds=DEFAULT_JOB_POLICY.tombstone_ttl_seconds - 1),
        workspace_absent_job_ids=frozenset({clean.job_id}),
    )
    assert early == StorePurgeReport(5, 0, 0, 0)
    purge_at = terminal_at + timedelta(seconds=DEFAULT_JOB_POLICY.event_ttl_seconds)
    report = store.purge_expired(
        at_utc=purge_at,
        workspace_absent_job_ids=frozenset({clean.job_id}),
    )
    assert report == StorePurgeReport(
        operational_events_deleted=0,
        deletion_events_deleted=1,
        tombstones_deleted=1,
        tombstones_blocked=1,
    )
    assert store.list_jobs_for_maintenance() == (retained,)
    assert store.list_deletion_events() == ()


def test_corrupt_deletion_ledger_fails_closed(tmp_path: Path) -> None:
    database_file = tmp_path / "control.sqlite3"
    store = make_store(database_file)
    terminal, terminal_at = terminal_staged(store, capability(1))
    absent = transition_artifact(
        terminal,
        kind=ArtifactKind.INPUT,
        target=CleanupState.VERIFIED_ABSENT,
        at_utc=terminal_at,
        expected_version=terminal.version,
        operation_id=operation(2),
    )
    event = deletion_for(
        terminal,
        at_utc=terminal_at,
        reason=DeletionReason.STAGED_EXPIRED,
    )
    store.maintenance_compare_and_swap(
        job_id=terminal.job_id,
        expected_version=terminal.version,
        updated=absent,
        at_utc=terminal_at,
        deletion_event=event,
    )
    with closing(sqlite3.connect(database_file)) as connection:
        connection.execute("PRAGMA ignore_check_constraints = ON")
        connection.execute("UPDATE deletion_events SET reason = 'payload-canary'")
        connection.commit()
    with pytest.raises(JobStoreError) as captured:
        store.list_deletion_events()
    assert captured.value.code is JobStoreErrorCode.CORRUPT_RECORD
