from __future__ import annotations

import os
import sqlite3
import stat
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

import delta_lemmata.job_store as job_store
from delta_lemmata.job_models import (
    AppliedOperation,
    ArtifactKind,
    Cancellation,
    CleanupState,
    ExecutionState,
    JobRecord,
    TerminalOutcome,
    VersionConflictError,
    publish_export,
    request_cancellation,
    transition_artifact,
    transition_execution,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY
from delta_lemmata.job_store import (
    JobAdmissionRejectedError,
    JobNotAvailableError,
    JobStoreError,
    JobStoreErrorCode,
    SQLiteJobStore,
)
from delta_lemmata.session_identity import (
    JobId,
    SessionCapability,
    SessionIdentityError,
    SessionIdentityErrorCode,
    owner_digest,
)

NOW = datetime(2026, 7, 13, 9, tzinfo=UTC)
SECRET = b"control-owner-secret-v1-32-bytes!!"


def operation(number: int) -> str:
    return "op_" + f"{number:064x}"


def capability(number: int) -> SessionCapability:
    return SessionCapability.generate(lambda size: bytes([number]) * size)


def job_id(number: int) -> JobId:
    return JobId.generate(lambda size: bytes([number]) * size)


class CountingJobIds:
    def __init__(self, start: int = 80) -> None:
        self.calls = 0
        self._next = start
        self._lock = threading.Lock()

    def __call__(self) -> JobId:
        with self._lock:
            value = self._next
            self._next += 1
            self.calls += 1
        return job_id(value)


def make_store(
    database_file: Path,
    factory: Any | None = None,
    *,
    secret: bytes = SECRET,
) -> SQLiteJobStore:
    return SQLiteJobStore(
        database_file,
        owner_secret=secret,
        job_id_factory=CountingJobIds() if factory is None else factory,
    )


def database_counts(database_file: Path) -> tuple[int, int]:
    with closing(sqlite3.connect(database_file)) as connection:
        jobs = cast(tuple[int], connection.execute("SELECT COUNT(*) FROM jobs").fetchone())[0]
        events = cast(tuple[int], connection.execute("SELECT COUNT(*) FROM events").fetchone())[0]
    return jobs, events


def database_states(database_file: Path) -> list[str]:
    with closing(sqlite3.connect(database_file)) as connection:
        return [
            cast(str, row[0])
            for row in connection.execute("SELECT execution_state FROM jobs ORDER BY job_id")
        ]


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat(follow_symlinks=False).st_mode)


def expect_store_error(
    code: JobStoreErrorCode,
    action: Any,
    error_type: type[JobStoreError] = JobStoreError,
) -> JobStoreError:
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


def test_private_wal_schema_json_round_trip_and_canary_scan(tmp_path: Path) -> None:
    database_file = tmp_path / "control.sqlite3"
    raw_canary = b"CANARY_CORPUS_TEXT_NEVER_STORE"
    secret = raw_canary + b"::key-material"
    factory = CountingJobIds()
    store = make_store(database_file, factory, secret=secret)

    anchor = sqlite3.connect(database_file, isolation_level=None)
    try:
        assert anchor.execute("PRAGMA journal_mode").fetchone() == ("wal",)
        anchor.execute("PRAGMA wal_autocheckpoint = 0")
        anchor.execute("BEGIN")
        assert anchor.execute("SELECT COUNT(*) FROM jobs").fetchone() == (0,)

        owner = capability(1)
        staged = store.create_staged(capability=owner, at_utc=NOW)
        parsed_id = JobId.from_urlsafe(staged.job_id)
        assert (
            staged.owner_digest
            == owner_digest(
                owner_secret=secret,
                capability=owner,
                job_id=parsed_id,
            ).hex()
        )
        assert store.load_job(job_id=parsed_id, capability=owner) == staged

        wal_file = Path(f"{database_file}-wal")
        shm_file = Path(f"{database_file}-shm")
        assert database_file.exists() and wal_file.exists() and shm_file.exists()
        assert mode(database_file) == mode(wal_file) == mode(shm_file) == 0o600
        for artifact in (database_file, wal_file, shm_file):
            scanned = artifact.read_bytes()
            assert raw_canary not in scanned
            assert b"filename-canary.txt" not in scanned
            assert b"/absolute/path/canary" not in scanned
    finally:
        anchor.rollback()
        anchor.close()

    with closing(sqlite3.connect(database_file)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (2,)
        table_names = {
            cast(str, row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name"
            )
        }
        assert table_names == {"deletion_events", "events", "jobs"}
        columns = {
            table: [cast(str, row[1]) for row in connection.execute(f"PRAGMA table_info({table})")]
            for table in table_names
        }
        forbidden = {
            "payload",
            "path",
            "filename",
            "name",
            "log",
            "traceback",
            "argv",
            "stdout",
            "stderr",
        }
        assert not {
            token
            for names in columns.values()
            for column in names
            for token in forbidden
            if token in column.lower()
        }
        model_json = cast(
            tuple[str],
            connection.execute("SELECT model_json FROM jobs").fetchone(),
        )[0]
        assert JobRecord.model_validate_json(model_json) == staged
        assert connection.execute("SELECT event_code FROM events").fetchall() == [("JOB_STAGED",)]
    assert factory.calls == 1


def test_atomic_staged_limits_use_no_identifier_or_event_on_rejection(
    tmp_path: Path,
) -> None:
    global_database = tmp_path / "global.sqlite3"
    global_factory = CountingJobIds()
    stores = [make_store(global_database, global_factory) for _ in range(8)]
    owners = [capability(number) for number in range(1, 9)]
    barrier = threading.Barrier(len(stores))

    def admit(index: int) -> JobRecord | JobStoreError:
        barrier.wait()
        try:
            return stores[index].stage_job(capability=owners[index], at_utc=NOW)
        except JobStoreError as error:
            return error

    with ThreadPoolExecutor(max_workers=len(stores)) as executor:
        outcomes = list(executor.map(admit, range(len(stores))))
    accepted = [outcome for outcome in outcomes if isinstance(outcome, JobRecord)]
    rejected = [outcome for outcome in outcomes if isinstance(outcome, JobStoreError)]
    assert len(accepted) == DEFAULT_JOB_POLICY.max_staged_global
    assert len(rejected) == len(stores) - DEFAULT_JOB_POLICY.max_staged_global
    assert all(error.code is JobStoreErrorCode.ADMISSION_REJECTED for error in rejected)
    assert global_factory.calls == DEFAULT_JOB_POLICY.max_staged_global
    assert database_counts(global_database) == (4, 4)

    owner_database = tmp_path / "owner.sqlite3"
    owner_factory = CountingJobIds(100)
    owner_stores = [make_store(owner_database, owner_factory) for _ in range(4)]
    shared_owner = capability(20)
    owner_barrier = threading.Barrier(len(owner_stores))

    def admit_same_owner(store: SQLiteJobStore) -> JobRecord | JobStoreError:
        owner_barrier.wait()
        try:
            return store.stage_job(capability=shared_owner, at_utc=NOW)
        except JobStoreError as error:
            return error

    with ThreadPoolExecutor(max_workers=len(owner_stores)) as executor:
        owner_outcomes = list(executor.map(admit_same_owner, owner_stores))
    assert sum(isinstance(outcome, JobRecord) for outcome in owner_outcomes) == 1
    assert owner_factory.calls == 1
    assert database_counts(owner_database) == (1, 1)


def test_staged_admission_counts_queued_ownership_without_counting_it_as_staged(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "mixed.sqlite3"
    store = make_store(database_file)
    first_owner = capability(1)
    second_owner = capability(2)
    first = store.stage_job(capability=first_owner, at_utc=NOW)
    store.enqueue_job(
        job_id=first.job_id,
        capability=first_owner,
        at_utc=NOW + timedelta(seconds=1),
        expected_version=first.version,
        operation_id=operation(9),
    )

    second = store.stage_job(capability=second_owner, at_utc=NOW + timedelta(seconds=2))
    assert second.execution.state is ExecutionState.STAGED
    expect_store_error(
        JobStoreErrorCode.ADMISSION_REJECTED,
        lambda: store.stage_job(capability=first_owner, at_utc=NOW + timedelta(seconds=3)),
        JobAdmissionRejectedError,
    )


def test_unknown_unauthorized_and_invalid_lookups_share_one_error(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "control.sqlite3"
    store = make_store(database_file)
    owner = capability(1)
    other = capability(2)
    staged = store.stage_job(capability=owner, at_utc=NOW)

    actions = [
        lambda: store.get_job(job_id=staged.job_id, capability=other),
        lambda: store.get_job(job_id=job_id(70), capability=owner),
        lambda: store.get_job(job_id="not-a-job-id", capability=owner),
        lambda: store.get_job(job_id=staged.job_id, capability=cast(Any, object())),
    ]
    errors = [
        expect_store_error(
            JobStoreErrorCode.NOT_AVAILABLE,
            action,
            JobNotAvailableError,
        )
        for action in actions
    ]
    assert {type(error) for error in errors} == {JobNotAvailableError}
    assert {str(error) for error in errors} == {"JOB_NOT_AVAILABLE"}
    assert database_counts(database_file) == (1, 1)


def test_atomic_queue_capacity_rejects_without_state_or_event_change(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "control.sqlite3"
    factory = CountingJobIds()
    stores = [make_store(database_file, factory) for _ in range(4)]
    owners = [capability(number) for number in range(1, 5)]
    staged = [stores[index].stage_job(capability=owners[index], at_utc=NOW) for index in range(4)]
    barrier = threading.Barrier(4)

    def enqueue(index: int) -> JobRecord | JobStoreError:
        barrier.wait()
        try:
            return stores[index].enqueue_job(
                job_id=staged[index].job_id,
                capability=owners[index],
                at_utc=NOW + timedelta(seconds=1),
                expected_version=0,
                operation_id=operation(10 + index),
            )
        except JobStoreError as error:
            return error

    with ThreadPoolExecutor(max_workers=4) as executor:
        outcomes = list(executor.map(enqueue, range(4)))
    assert (
        sum(
            isinstance(outcome, JobRecord) and outcome.execution.state is ExecutionState.QUEUED
            for outcome in outcomes
        )
        == DEFAULT_JOB_POLICY.max_queued
    )
    assert sum(isinstance(outcome, JobAdmissionRejectedError) for outcome in outcomes) == 1
    assert database_states(database_file).count(ExecutionState.QUEUED.value) == 3
    assert database_states(database_file).count(ExecutionState.STAGED.value) == 1
    assert database_counts(database_file) == (4, 7)
    assert factory.calls == 4


def test_fifo_claim_and_one_running_are_atomic_across_connections(tmp_path: Path) -> None:
    database_file = tmp_path / "control.sqlite3"
    factory = CountingJobIds()
    primary = make_store(database_file, factory)
    owners = [capability(number) for number in range(1, 4)]
    staged = [primary.stage_job(capability=owner, at_utc=NOW) for owner in owners]
    enqueue_order = [1, 0, 2]
    queued: dict[int, JobRecord] = {}
    for sequence, index in enumerate(enqueue_order, start=1):
        queued[index] = primary.enqueue_job(
            job_id=staged[index].job_id,
            capability=owners[index],
            at_utc=NOW + timedelta(seconds=sequence),
            expected_version=0,
            operation_id=operation(20 + index),
        )
    first_queued = queued[1]
    assert (
        primary.enqueue_job(
            job_id=first_queued.job_id,
            capability=owners[1],
            at_utc=NOW + timedelta(seconds=20),
            expected_version=0,
            operation_id=operation(21),
        )
        == first_queued
    )
    assert database_counts(database_file) == (3, 6)

    claimers = [make_store(database_file, factory), make_store(database_file, factory)]
    barrier = threading.Barrier(2)

    def claim(store: SQLiteJobStore) -> JobRecord | None:
        barrier.wait()
        return store.claim_next(at_utc=NOW + timedelta(seconds=30), operation_id=operation(30))

    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(claim, claimers))
    claimed = [candidate for candidate in claims if candidate is not None]
    assert len(claimed) == 1
    running = claimed[0]
    assert running.job_id == staged[1].job_id
    assert running.execution.state is ExecutionState.RUNNING
    assert (
        primary.claim_next(at_utc=NOW + timedelta(seconds=31), operation_id=operation(31)) is None
    )

    terminal = transition_execution(
        running,
        target=ExecutionState.TERMINAL,
        outcome=TerminalOutcome.SUCCEEDED,
        at_utc=NOW + timedelta(seconds=32),
        tombstone_expires_at_utc=NOW + timedelta(days=7, seconds=32),
        expected_version=running.version,
        operation_id=operation(32),
    )
    assert (
        primary.compare_and_swap(
            job_id=running.job_id,
            capability=owners[1],
            expected_version=running.version,
            updated=terminal,
            at_utc=NOW + timedelta(seconds=32),
        )
        == terminal
    )
    second = primary.claim_next(at_utc=NOW + timedelta(seconds=33), operation_id=operation(33))
    assert second is not None
    assert second.job_id == staged[0].job_id
    assert database_states(database_file).count(ExecutionState.RUNNING.value) == 1


def test_expired_staging_and_queue_deadlines_fail_closed(tmp_path: Path) -> None:
    staged_database = tmp_path / "staged.sqlite3"
    store = make_store(staged_database)
    owner = capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    event_count = database_counts(staged_database)[1]
    expect_store_error(
        JobStoreErrorCode.ADMISSION_REJECTED,
        lambda: store.enqueue_job(
            job_id=staged.job_id,
            capability=owner,
            at_utc=cast(datetime, staged.execution.deadline_at_utc),
            expected_version=staged.version,
            operation_id=operation(40),
        ),
        JobAdmissionRejectedError,
    )
    assert database_counts(staged_database) == (1, event_count)

    queue_database = tmp_path / "queue.sqlite3"
    queue_store = make_store(queue_database)
    queue_owner = capability(2)
    queue_staged = queue_store.stage_job(capability=queue_owner, at_utc=NOW)
    queued = queue_store.enqueue_job(
        job_id=queue_staged.job_id,
        capability=queue_owner,
        at_utc=NOW + timedelta(seconds=1),
        expected_version=0,
        operation_id=operation(41),
    )
    assert (
        queue_store.claim_next(
            at_utc=cast(datetime, queued.execution.deadline_at_utc),
            operation_id=operation(42),
        )
        is None
    )
    assert (
        queue_store.claim_next(
            at_utc=NOW,
            operation_id=operation(43),
        )
        is None
    )
    assert database_counts(queue_database) == (1, 2)


def test_cas_is_owned_versioned_idempotent_and_serializes_model_json(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "control.sqlite3"
    store = make_store(database_file)
    owner = capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    queued = store.enqueue_job(
        job_id=staged.job_id,
        capability=owner,
        at_utc=NOW + timedelta(seconds=1),
        expected_version=0,
        operation_id=operation(50),
    )
    running = cast(
        JobRecord,
        store.claim_next(at_utc=NOW + timedelta(seconds=2), operation_id=operation(51)),
    )
    cancellation = request_cancellation(
        running,
        at_utc=NOW + timedelta(seconds=3),
        expected_version=running.version,
        operation_id=operation(52),
    )
    saved = store.save_job(
        job_id=running.job_id,
        capability=owner,
        expected_version=running.version,
        updated=cancellation,
        at_utc=NOW + timedelta(seconds=3),
    )
    event_count = database_counts(database_file)[1]
    assert (
        store.compare_and_swap(
            job_id=running.job_id,
            capability=owner,
            expected_version=running.version,
            updated=saved,
            at_utc=NOW + timedelta(seconds=4),
        )
        == saved
    )
    assert database_counts(database_file)[1] == event_count

    cancelled = transition_execution(
        saved,
        target=ExecutionState.TERMINAL,
        outcome=TerminalOutcome.CANCELLED,
        at_utc=NOW + timedelta(seconds=5),
        tombstone_expires_at_utc=NOW + timedelta(days=7, seconds=5),
        expected_version=saved.version,
        operation_id=operation(53),
    )
    with pytest.raises(VersionConflictError) as conflict:
        store.compare_and_swap(
            job_id=saved.job_id,
            capability=owner,
            expected_version=saved.version - 1,
            updated=cancelled,
            at_utc=NOW + timedelta(seconds=5),
        )
    assert str(conflict.value) == "JOB_VERSION_CONFLICT"
    assert database_counts(database_file)[1] == event_count

    terminal = store.compare_and_swap(
        job_id=saved.job_id,
        capability=owner,
        expected_version=saved.version,
        updated=cancelled,
        at_utc=NOW + timedelta(seconds=5),
    )
    assert terminal.outcome is not None
    assert terminal.outcome.kind is TerminalOutcome.CANCELLED
    assert store.get_job(job_id=staged.job_id, capability=owner) == terminal
    with closing(sqlite3.connect(database_file)) as connection:
        persisted = cast(tuple[str], connection.execute("SELECT model_json FROM jobs").fetchone())[
            0
        ]
    assert JobRecord.model_validate_json(persisted) == terminal
    assert queued.job_id == running.job_id


def test_cas_replays_artifact_terminal_and_export_helpers(tmp_path: Path) -> None:
    database_file = tmp_path / "control.sqlite3"
    store = make_store(database_file)
    owner = capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    queued = store.enqueue_job(
        job_id=staged.job_id,
        capability=owner,
        at_utc=NOW + timedelta(seconds=1),
        expected_version=0,
        operation_id=operation(60),
    )
    current = cast(
        JobRecord,
        store.claim_next(at_utc=NOW + timedelta(seconds=2), operation_id=operation(61)),
    )
    succeeded = transition_execution(
        current,
        target=ExecutionState.TERMINAL,
        outcome=TerminalOutcome.SUCCEEDED,
        at_utc=NOW + timedelta(seconds=3),
        tombstone_expires_at_utc=NOW + timedelta(days=7, seconds=3),
        expected_version=current.version,
        operation_id=operation(62),
    )
    current = store.compare_and_swap(
        job_id=current.job_id,
        capability=owner,
        expected_version=current.version,
        updated=succeeded,
        at_utc=NOW + timedelta(seconds=3),
    )
    for number, kind in enumerate((ArtifactKind.INPUT, ArtifactKind.WORK), start=63):
        absent = transition_artifact(
            current,
            kind=kind,
            target=CleanupState.VERIFIED_ABSENT,
            at_utc=NOW + timedelta(seconds=number),
            expected_version=current.version,
            operation_id=operation(number),
        )
        current = store.compare_and_swap(
            job_id=current.job_id,
            capability=owner,
            expected_version=current.version,
            updated=absent,
            at_utc=NOW + timedelta(seconds=number),
        )
    export_present = transition_artifact(
        current,
        kind=ArtifactKind.EXPORT,
        target=CleanupState.PRESENT,
        at_utc=NOW + timedelta(seconds=65),
        delete_by_utc=NOW + timedelta(hours=1),
        expected_version=current.version,
        operation_id=operation(65),
    )
    current = store.compare_and_swap(
        job_id=current.job_id,
        capability=owner,
        expected_version=current.version,
        updated=export_present,
        at_utc=NOW + timedelta(seconds=65),
    )
    published = publish_export(
        current,
        expected_version=current.version,
        operation_id=operation(66),
    )
    current = store.compare_and_swap(
        job_id=current.job_id,
        capability=owner,
        expected_version=current.version,
        updated=published,
        at_utc=NOW + timedelta(seconds=66),
    )
    assert current.export_available
    assert current.can_publish_export
    assert queued.job_id == current.job_id


def test_cas_rejects_forged_or_capacity_bypassing_successors(tmp_path: Path) -> None:
    database_file = tmp_path / "control.sqlite3"
    store = make_store(database_file)
    owner = capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)

    invalid_actions: list[Any] = [cast(Any, object())]
    structural = staged.model_copy(update={"version": staged.version + 1})
    invalid_actions.append(structural)
    unknown = staged.model_copy(
        update={
            "version": 1,
            "operations": (
                *staged.operations,
                AppliedOperation(operation_id=operation(70), action="noop"),
            ),
        }
    )
    invalid_actions.append(unknown)
    for action in ("artifact:input", "artifact:unknown:present", "artifact:input:present"):
        invalid_actions.append(
            staged.model_copy(
                update={
                    "version": 1,
                    "operations": (
                        *staged.operations,
                        AppliedOperation(operation_id=operation(71), action=action),
                    ),
                }
            )
        )
    queue_bypass = transition_execution(
        staged,
        target=ExecutionState.QUEUED,
        at_utc=NOW + timedelta(seconds=1),
        deadline_at_utc=NOW + timedelta(seconds=901),
        expected_version=0,
        operation_id=operation(72),
    )
    invalid_actions.append(queue_bypass)
    for candidate in invalid_actions:
        expect_store_error(
            JobStoreErrorCode.INVALID_UPDATE,
            lambda candidate=candidate: store.compare_and_swap(
                job_id=staged.job_id,
                capability=owner,
                expected_version=staged.version,
                updated=candidate,
                at_utc=NOW + timedelta(seconds=2),
            ),
        )

    queued = store.enqueue_job(
        job_id=staged.job_id,
        capability=owner,
        at_utc=NOW + timedelta(seconds=1),
        expected_version=0,
        operation_id=operation(73),
    )
    legitimate_cancel = request_cancellation(
        queued,
        at_utc=NOW + timedelta(seconds=2),
        expected_version=queued.version,
        operation_id=operation(74),
    )
    missing_time = legitimate_cancel.model_copy(update={"cancellation": Cancellation()})
    expect_store_error(
        JobStoreErrorCode.INVALID_UPDATE,
        lambda: store.compare_and_swap(
            job_id=queued.job_id,
            capability=owner,
            expected_version=queued.version,
            updated=missing_time,
            at_utc=NOW + timedelta(seconds=2),
        ),
    )

    expired = transition_execution(
        queued,
        target=ExecutionState.TERMINAL,
        outcome=TerminalOutcome.EXPIRED,
        at_utc=NOW + timedelta(seconds=3),
        tombstone_expires_at_utc=NOW + timedelta(days=7, seconds=3),
        expected_version=queued.version,
        operation_id=operation(75),
    )
    missing_outcome = expired.model_copy(update={"outcome": None})
    changed_expiry = expired.model_copy(
        update={"event_expires_at_utc": expired.event_expires_at_utc + timedelta(seconds=1)}
    )
    for candidate in (missing_outcome, changed_expiry):
        expect_store_error(
            JobStoreErrorCode.INVALID_UPDATE,
            lambda candidate=candidate: store.compare_and_swap(
                job_id=queued.job_id,
                capability=owner,
                expected_version=queued.version,
                updated=candidate,
                at_utc=NOW + timedelta(seconds=3),
            ),
        )
    assert database_counts(database_file) == (1, 2)


def test_configuration_file_identity_and_identifier_failures_are_content_free(
    tmp_path: Path,
) -> None:
    expect_store_error(
        JobStoreErrorCode.INVALID_DATABASE,
        lambda: SQLiteJobStore(Path("relative.sqlite3"), owner_secret=SECRET),
    )
    expect_store_error(
        JobStoreErrorCode.INVALID_DATABASE,
        lambda: SQLiteJobStore(cast(Any, str(tmp_path / "string.sqlite3")), owner_secret=SECRET),
    )
    expect_store_error(
        JobStoreErrorCode.INVALID_DATABASE,
        lambda: SQLiteJobStore(tmp_path / "missing" / "control.sqlite3", owner_secret=SECRET),
    )
    expect_store_error(
        JobStoreErrorCode.INVALID_CONFIGURATION,
        lambda: SQLiteJobStore(tmp_path / "short.sqlite3", owner_secret=b"short"),
    )
    expect_store_error(
        JobStoreErrorCode.INVALID_CONFIGURATION,
        lambda: SQLiteJobStore(
            tmp_path / "factory.sqlite3",
            owner_secret=SECRET,
            job_id_factory=cast(Any, None),
        ),
    )

    existing = tmp_path / "existing.sqlite3"
    existing.touch(mode=0o644)
    existing_store = make_store(existing)
    assert mode(existing) == 0o600
    assert existing_store.claim_next(at_utc=NOW, operation_id=operation(80)) is None

    hardlink_source = tmp_path / "hardlink-source"
    hardlink_source.touch(mode=0o600)
    hardlink = tmp_path / "hardlink.sqlite3"
    os.link(hardlink_source, hardlink)
    expect_store_error(
        JobStoreErrorCode.INVALID_DATABASE,
        lambda: make_store(hardlink),
    )

    directory = tmp_path / "directory.sqlite3"
    directory.mkdir()
    expect_store_error(
        JobStoreErrorCode.INVALID_DATABASE,
        lambda: make_store(directory),
    )
    symlink = tmp_path / "symlink.sqlite3"
    symlink.symlink_to(existing)
    expect_store_error(
        JobStoreErrorCode.INVALID_DATABASE,
        lambda: make_store(symlink),
    )

    future = tmp_path / "future.sqlite3"
    with closing(sqlite3.connect(future)) as connection:
        connection.execute("PRAGMA user_version = 3")
        connection.commit()
    expect_store_error(
        JobStoreErrorCode.INVALID_DATABASE,
        lambda: make_store(future),
    )

    raising_database = tmp_path / "raising.sqlite3"

    def raise_identifier() -> JobId:
        raise RuntimeError("CANARY_IDENTIFIER_FACTORY")

    raising = make_store(raising_database, raise_identifier)
    expect_store_error(
        JobStoreErrorCode.IDENTIFIER_GENERATION_FAILED,
        lambda: raising.stage_job(capability=capability(1), at_utc=NOW),
    )
    assert database_counts(raising_database) == (0, 0)

    invalid_database = tmp_path / "invalid-id.sqlite3"
    invalid = make_store(invalid_database, lambda: cast(Any, "not-a-job-id"))
    expect_store_error(
        JobStoreErrorCode.IDENTIFIER_GENERATION_FAILED,
        lambda: invalid.stage_job(capability=capability(1), at_utc=NOW),
    )
    assert database_counts(invalid_database) == (0, 0)


def test_database_parent_must_remain_the_same_private_real_directory(
    tmp_path: Path,
) -> None:
    public_parent = tmp_path / "public"
    public_parent.mkdir(mode=0o755)
    expect_store_error(
        JobStoreErrorCode.INVALID_DATABASE,
        lambda: make_store(public_parent / "control.sqlite3"),
    )

    private_parent = tmp_path / "private"
    private_parent.mkdir(mode=0o700)
    parent_link = tmp_path / "parent-link"
    parent_link.symlink_to(private_parent, target_is_directory=True)
    expect_store_error(
        JobStoreErrorCode.INVALID_DATABASE,
        lambda: make_store(parent_link / "control.sqlite3"),
    )

    store = make_store(private_parent / "control.sqlite3")
    owner = capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    replaced = tmp_path / "replaced"
    private_parent.rename(replaced)
    private_parent.mkdir(mode=0o700)
    expect_store_error(
        JobStoreErrorCode.INVALID_DATABASE,
        lambda: store.get_job(job_id=staged.job_id, capability=owner),
    )
    assert not (private_parent / "control.sqlite3").exists()


def test_non_wal_connections_fail_closed_and_are_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = make_store(tmp_path / "control.sqlite3")

    class Cursor:
        def fetchone(self) -> tuple[str]:
            return ("delete",)

    class Connection:
        def __init__(self) -> None:
            self.row_factory: object = None
            self.closed = False

        def execute(self, _statement: str) -> Cursor:
            return Cursor()

        def executescript(self, _script: str) -> None:
            raise AssertionError("schema must not run without WAL")

        def close(self) -> None:
            self.closed = True

    initialization = Connection()
    monkeypatch.setattr(sqlite3, "connect", lambda *_args, **_kwargs: initialization)
    with pytest.raises(JobStoreError) as initialization_error:
        store._initialize_schema()
    assert initialization_error.value.code is JobStoreErrorCode.INVALID_DATABASE
    assert initialization.closed

    connection = Connection()
    monkeypatch.setattr(sqlite3, "connect", lambda *_args, **_kwargs: connection)
    with pytest.raises(JobStoreError) as connection_error:
        store._connect()
    assert connection_error.value.code is JobStoreErrorCode.INVALID_DATABASE
    assert connection.closed


def test_invalid_capability_and_database_exceptions_are_content_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_file = tmp_path / "control.sqlite3"
    store = make_store(database_file)
    expect_store_error(
        JobStoreErrorCode.ADMISSION_REJECTED,
        lambda: store.stage_job(capability=cast(Any, object()), at_utc=NOW),
        JobAdmissionRejectedError,
    )

    def fail_connection() -> sqlite3.Connection:
        raise sqlite3.OperationalError("CANARY /absolute/database/path")

    monkeypatch.setattr(store, "_connect", fail_connection)
    error = expect_store_error(
        JobStoreErrorCode.DATABASE_FAILURE,
        lambda: store.get_job(job_id=job_id(1), capability=capability(1)),
    )
    assert "CANARY" not in str(error)
    assert "/" not in str(error)


@pytest.mark.parametrize(
    ("mutation", "action"),
    [
        ("owner_non_hex", "read"),
        ("owner_short", "read"),
        ("invalid_json", "read"),
        ("state_mismatch", "read"),
        ("invalid_job_id", "stage"),
    ],
)
def test_corrupt_rows_fail_closed(
    tmp_path: Path,
    mutation: str,
    action: str,
) -> None:
    database_file = tmp_path / f"{mutation}.sqlite3"
    store = make_store(database_file)
    owner = capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    with closing(sqlite3.connect(database_file)) as connection:
        connection.execute("PRAGMA ignore_check_constraints = ON")
        if mutation == "owner_non_hex":
            connection.execute("UPDATE jobs SET owner_digest = ?", ("zz" * 32,))
        elif mutation == "owner_short":
            connection.execute("UPDATE jobs SET owner_digest = 'aa'")
        elif mutation == "invalid_json":
            connection.execute("UPDATE jobs SET model_json = '{'")
        elif mutation == "state_mismatch":
            connection.execute(
                """
                UPDATE jobs
                SET execution_state = 'terminal', deadline_at_utc = NULL
                """
            )
        else:
            connection.execute("UPDATE jobs SET job_id = 'invalid'")
        connection.commit()

    def target() -> object:
        if action == "read":
            return store.get_job(job_id=staged.job_id, capability=owner)
        return store.stage_job(capability=capability(2), at_utc=NOW)

    expect_store_error(JobStoreErrorCode.CORRUPT_RECORD, target)


def test_identity_verifier_failure_is_a_content_free_corruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_file = tmp_path / "control.sqlite3"
    store = make_store(database_file)
    owner = capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)

    def fail_verification(**_kwargs: object) -> bool:
        raise SessionIdentityError(SessionIdentityErrorCode.INVALID_OWNER_DIGEST)

    monkeypatch.setattr(job_store, "verify_owner_digest", fail_verification)
    expect_store_error(
        JobStoreErrorCode.CORRUPT_RECORD,
        lambda: store.get_job(job_id=staged.job_id, capability=owner),
    )


def test_terminal_transition_proof_binds_version_outcome_and_running_operation(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path / "control.sqlite3", factory=lambda: job_id(1))
    owner = capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    queued = store.enqueue_job(
        job_id=staged.job_id,
        capability=owner,
        at_utc=NOW + timedelta(seconds=1),
        expected_version=staged.version,
        operation_id=operation(1),
    )
    running = store.claim_next(
        at_utc=NOW + timedelta(seconds=2),
        operation_id=operation(2),
    )
    assert running is not None
    terminal = transition_execution(
        running,
        target=ExecutionState.TERMINAL,
        outcome=TerminalOutcome.SUCCEEDED,
        at_utc=NOW + timedelta(seconds=3),
        tombstone_expires_at_utc=NOW + timedelta(days=7),
        expected_version=running.version,
        operation_id=operation(3),
    )
    saved = store.maintenance_compare_and_swap(
        job_id=running.job_id,
        expected_version=running.version,
        updated=terminal,
        at_utc=NOW + timedelta(seconds=3),
    )
    assert queued.job_id == saved.job_id
    assert store.terminal_transition_matches(
        job_id=saved.job_id,
        execution_reference=operation(2),
        expected_version=saved.version,
        expected_outcome=TerminalOutcome.SUCCEEDED,
    )
    assert not store.terminal_transition_matches(
        job_id=saved.job_id,
        execution_reference=operation(1),
        expected_version=saved.version,
        expected_outcome=TerminalOutcome.SUCCEEDED,
    )
    assert not store.terminal_transition_matches(
        job_id=saved.job_id,
        execution_reference=operation(2),
        expected_version=saved.version - 1,
        expected_outcome=TerminalOutcome.SUCCEEDED,
    )
    assert not store.terminal_transition_matches(
        job_id=saved.job_id,
        execution_reference=operation(2),
        expected_version=saved.version,
        expected_outcome=TerminalOutcome.FAILED,
    )
    expect_store_error(
        JobStoreErrorCode.INVALID_UPDATE,
        lambda: store.terminal_transition_matches(
            job_id=saved.job_id,
            execution_reference="bad",
            expected_version=saved.version,
            expected_outcome=TerminalOutcome.SUCCEEDED,
        ),
    )
    expect_store_error(
        JobStoreErrorCode.INVALID_UPDATE,
        lambda: store.purge_expired(
            at_utc=NOW,
            workspace_absent_job_ids=cast(Any, set()),
        ),
    )
