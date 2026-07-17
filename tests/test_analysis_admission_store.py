from __future__ import annotations

import multiprocessing
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import delta_lemmata.job_store as job_store_module
from delta_lemmata.job_models import (
    ExecutionState,
    JobRecord,
    TerminalOutcome,
    transition_execution,
)
from delta_lemmata.job_store import (
    AnalysisAdmissionRejectedError,
    AnalysisAdmissionReusedError,
    JobNotAvailableError,
    JobStoreError,
    JobStoreErrorCode,
    SQLiteJobStore,
)
from delta_lemmata.session_identity import JobId, SessionCapability

NOW = datetime(2026, 7, 14, 22, 0, tzinfo=UTC)
OWNER_SECRET = b"analysis-admission-owner-secret-32bytes"
RECEIPT_HMAC = "a" * 64


class CountingJobIds:
    def __init__(self, start: int = 1) -> None:
        self._next = start
        self._lock = threading.Lock()

    def __call__(self) -> JobId:
        with self._lock:
            value = self._next
            self._next += 1
        return JobId.generate(lambda size: bytes([value]) * size)


def _capability(number: int) -> SessionCapability:
    return SessionCapability.generate(lambda size: bytes([number]) * size)


def _store(database: Path, factory=None) -> SQLiteJobStore:
    return SQLiteJobStore(
        database,
        owner_secret=OWNER_SECRET,
        job_id_factory=factory or CountingJobIds(),
    )


def _operation(number: int) -> str:
    return "op_" + f"{number:064x}"


def _consume_admission_in_process(
    database: str,
    job_id: str,
    capability: str,
    operation_number: int,
    start,
    results,
) -> None:
    store = _store(Path(database))
    start.wait()
    try:
        queued = store.consume_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=job_id,
            capability=SessionCapability.from_urlsafe(capability),
            at_utc=NOW + timedelta(seconds=1),
            operation_id=_operation(operation_number),
        )
    except JobStoreError as error:
        results.put(("error", error.code.value))
    else:
        results.put(("accepted", queued.job_id))


def _claim_in_process(
    database: str,
    operation_number: int,
    start,
    results,
) -> None:
    store = _store(Path(database))
    start.wait()
    claimed = store.claim_next(
        at_utc=NOW + timedelta(seconds=2),
        operation_id=_operation(operation_number),
    )
    results.put(None if claimed is None else claimed.job_id)


def _bind(
    store: SQLiteJobStore,
    job: JobRecord,
    owner: SessionCapability,
    *,
    receipt_hmac: str = RECEIPT_HMAC,
    expiry: datetime = NOW + timedelta(minutes=30),
) -> None:
    store.bind_analysis_admission(
        receipt_hmac=receipt_hmac,
        job_id=job.job_id,
        capability=owner,
        at_utc=NOW,
        expires_at_utc=expiry,
        expected_job_version=job.version,
    )


def _expect(
    error_type: type[JobStoreError],
    code: JobStoreErrorCode,
    action,
) -> None:
    with pytest.raises(error_type) as captured:
        action()
    assert captured.value.code is code
    assert str(captured.value) == code.value
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


def test_ready_binding_is_payload_free_idempotent_and_consumed_once(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite3"
    store = _store(database)
    owner = _capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)

    _bind(store, staged, owner)
    _bind(store, staged, owner)
    queued = store.consume_analysis_admission(
        receipt_hmac=RECEIPT_HMAC,
        job_id=staged.job_id,
        capability=owner,
        at_utc=NOW + timedelta(seconds=1),
        operation_id=_operation(1),
    )
    assert queued.execution.state is ExecutionState.QUEUED
    assert queued.version == staged.version + 1

    _expect(
        AnalysisAdmissionReusedError,
        JobStoreErrorCode.ANALYSIS_ADMISSION_REUSED,
        lambda: store.consume_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=staged.job_id,
            capability=owner,
            at_utc=NOW + timedelta(seconds=2),
            operation_id=_operation(2),
        ),
    )
    _expect(
        AnalysisAdmissionRejectedError,
        JobStoreErrorCode.ANALYSIS_ADMISSION_REJECTED,
        lambda: _bind(store, staged, owner),
    )

    with closing(sqlite3.connect(database)) as connection:
        row = connection.execute(
            """
            SELECT receipt_hmac, job_id, owner_digest, expected_job_version,
                   expires_at_utc, consumed_at_utc, version
            FROM analysis_admissions
            """
        ).fetchone()
        assert row is not None
        assert row[0] == RECEIPT_HMAC
        assert row[1] == staged.job_id
        assert row[2] == staged.owner_digest
        assert row[3] == staged.version
        assert row[4] == "2026-07-14T22:30:00Z"
        assert row[5] == "2026-07-14T22:00:01Z"
        assert row[6] == 1
        assert connection.execute("SELECT event_code FROM events ORDER BY sequence").fetchall() == [
            ("JOB_STAGED",),
            ("JOB_QUEUED",),
        ]

    forbidden = (
        b"CANARY_CORPUS_TEXT_NEVER_STORE",
        b"filename-canary.txt",
        b"candidate_features",
        b"prepared_bytes",
    )
    for artifact in (database, Path(f"{database}-wal"), Path(f"{database}-shm")):
        if artifact.exists():
            payload = artifact.read_bytes()
            assert all(value not in payload for value in forbidden)


def test_binding_and_consumption_fail_closed_for_invalid_authority(tmp_path: Path) -> None:
    store = _store(tmp_path / "control.sqlite3")
    owner = _capability(1)
    other = _capability(2)
    staged = store.stage_job(capability=owner, at_utc=NOW)

    _expect(
        JobNotAvailableError,
        JobStoreErrorCode.NOT_AVAILABLE,
        lambda: store.bind_analysis_admission(
            receipt_hmac="A" * 64,
            job_id=staged.job_id,
            capability=owner,
            at_utc=NOW,
            expires_at_utc=NOW + timedelta(minutes=1),
            expected_job_version=staged.version,
        ),
    )
    _expect(
        JobNotAvailableError,
        JobStoreErrorCode.NOT_AVAILABLE,
        lambda: store.bind_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=staged.job_id,
            capability=other,
            at_utc=NOW,
            expires_at_utc=NOW + timedelta(minutes=1),
            expected_job_version=staged.version,
        ),
    )
    _bind(store, staged, owner)
    _expect(
        JobNotAvailableError,
        JobStoreErrorCode.NOT_AVAILABLE,
        lambda: store.consume_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=staged.job_id,
            capability=other,
            at_utc=NOW,
            operation_id=_operation(1),
        ),
    )
    _expect(
        JobNotAvailableError,
        JobStoreErrorCode.NOT_AVAILABLE,
        lambda: store.consume_analysis_admission(
            receipt_hmac="invalid",
            job_id=staged.job_id,
            capability=owner,
            at_utc=NOW,
            operation_id=_operation(1),
        ),
    )
    _expect(
        JobNotAvailableError,
        JobStoreErrorCode.NOT_AVAILABLE,
        lambda: store.consume_analysis_admission(
            receipt_hmac="b" * 64,
            job_id=staged.job_id,
            capability=owner,
            at_utc=NOW,
            operation_id=_operation(1),
        ),
    )


def test_exact_expiry_invalid_time_and_invalid_version_are_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path / "control.sqlite3")
    owner = _capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    expiry = NOW + timedelta(minutes=1)
    _bind(store, staged, owner, expiry=expiry)

    _expect(
        AnalysisAdmissionRejectedError,
        JobStoreErrorCode.ANALYSIS_ADMISSION_REJECTED,
        lambda: store.consume_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=staged.job_id,
            capability=owner,
            at_utc=expiry,
            operation_id=_operation(1),
        ),
    )
    _expect(
        AnalysisAdmissionRejectedError,
        JobStoreErrorCode.ANALYSIS_ADMISSION_REJECTED,
        lambda: store.consume_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=staged.job_id,
            capability=owner,
            at_utc=NOW.replace(tzinfo=None),
            operation_id=_operation(1),
        ),
    )
    _expect(
        AnalysisAdmissionRejectedError,
        JobStoreErrorCode.ANALYSIS_ADMISSION_REJECTED,
        lambda: store.consume_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=staged.job_id,
            capability=owner,
            at_utc=NOW,
            operation_id="invalid",
        ),
    )

    second_database = tmp_path / "invalid-bind.sqlite3"
    second = _store(second_database)
    second_owner = _capability(3)
    second_job = second.stage_job(capability=second_owner, at_utc=NOW)
    for at_utc, expires_at, expected_version in (
        (NOW.replace(tzinfo=None), expiry, second_job.version),
        (NOW, NOW, second_job.version),
        (NOW, NOW + timedelta(hours=2), second_job.version),
        (NOW, expiry, True),
        (NOW, expiry, second_job.version + 1),
    ):
        _expect(
            AnalysisAdmissionRejectedError,
            JobStoreErrorCode.ANALYSIS_ADMISSION_REJECTED,
            lambda at_utc=at_utc, expires_at=expires_at, expected_version=expected_version: (
                second.bind_analysis_admission(
                    receipt_hmac=RECEIPT_HMAC,
                    job_id=second_job.job_id,
                    capability=second_owner,
                    at_utc=at_utc,
                    expires_at_utc=expires_at,
                    expected_job_version=expected_version,
                )
            ),
        )


def test_conflicting_ready_bindings_are_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path / "control.sqlite3", CountingJobIds())
    first_owner = _capability(1)
    second_owner = _capability(2)
    first = store.stage_job(capability=first_owner, at_utc=NOW)
    second = store.stage_job(capability=second_owner, at_utc=NOW)
    _bind(store, first, first_owner)

    _expect(
        JobNotAvailableError,
        JobStoreErrorCode.NOT_AVAILABLE,
        lambda: store.consume_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=second.job_id,
            capability=second_owner,
            at_utc=NOW,
            operation_id=_operation(1),
        ),
    )
    _expect(
        AnalysisAdmissionRejectedError,
        JobStoreErrorCode.ANALYSIS_ADMISSION_REJECTED,
        lambda: _bind(store, first, first_owner, receipt_hmac="b" * 64),
    )
    _expect(
        AnalysisAdmissionRejectedError,
        JobStoreErrorCode.ANALYSIS_ADMISSION_REJECTED,
        lambda: _bind(store, second, second_owner),
    )


def test_queue_capacity_rejection_leaves_ready_unconsumed(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite3"
    store = _store(database, CountingJobIds())
    for number in range(1, 4):
        with store.reserve_admission(
            capability=_capability(number),
            at_utc=NOW,
            queued=True,
        ):
            pass
    owner = _capability(4)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    _bind(store, staged, owner)

    _expect(
        AnalysisAdmissionRejectedError,
        JobStoreErrorCode.ANALYSIS_ADMISSION_REJECTED,
        lambda: store.consume_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=staged.job_id,
            capability=owner,
            at_utc=NOW,
            operation_id=_operation(1),
        ),
    )
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT consumed_at_utc, version FROM analysis_admissions"
        ).fetchone() == (None, 0)
        assert connection.execute(
            "SELECT COUNT(*) FROM jobs WHERE execution_state = 'queued'"
        ).fetchone() == (3,)


def test_thirty_two_concurrent_consumers_enqueue_exactly_once(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite3"
    initial = _store(database)
    owner = _capability(1)
    staged = initial.stage_job(capability=owner, at_utc=NOW)
    _bind(initial, staged, owner)
    stores = [_store(database) for _ in range(32)]
    barrier = threading.Barrier(len(stores))

    def consume(index: int) -> JobRecord | JobStoreError:
        barrier.wait()
        try:
            return stores[index].consume_analysis_admission(
                receipt_hmac=RECEIPT_HMAC,
                job_id=staged.job_id,
                capability=owner,
                at_utc=NOW + timedelta(seconds=1),
                operation_id=_operation(index + 1),
            )
        except JobStoreError as error:
            return error

    with ThreadPoolExecutor(max_workers=len(stores)) as executor:
        outcomes = list(executor.map(consume, range(len(stores))))
    accepted = [item for item in outcomes if isinstance(item, JobRecord)]
    rejected = [item for item in outcomes if isinstance(item, JobStoreError)]
    assert len(accepted) == 1
    assert accepted[0].execution.state is ExecutionState.QUEUED
    assert len(rejected) == 31
    assert all(item.code is JobStoreErrorCode.ANALYSIS_ADMISSION_REUSED for item in rejected)
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM events WHERE event_code = 'JOB_QUEUED'"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT consumed_at_utc, version FROM analysis_admissions"
        ).fetchone() == ("2026-07-14T22:00:01Z", 1)


def test_separate_processes_consume_one_analysis_admission_exactly_once(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite3"
    initial = _store(database)
    owner = _capability(1)
    staged = initial.stage_job(capability=owner, at_utc=NOW)
    _bind(initial, staged, owner)
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    results = context.Queue()
    processes = tuple(
        context.Process(
            target=_consume_admission_in_process,
            args=(
                str(database),
                staged.job_id,
                owner.to_urlsafe(),
                100 + index,
                start,
                results,
            ),
        )
        for index in range(2)
    )
    for process in processes:
        process.start()
    start.set()
    outcomes = [results.get(timeout=10) for _ in processes]
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0

    assert outcomes.count(("accepted", staged.job_id)) == 1
    assert outcomes.count(("error", JobStoreErrorCode.ANALYSIS_ADMISSION_REUSED.value)) == 1


def test_separate_processes_claim_only_one_oldest_fifo_job(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite3"
    store = _store(database, CountingJobIds())
    owners = (_capability(1), _capability(2))
    staged = tuple(store.stage_job(capability=owner, at_utc=NOW) for owner in owners)
    queued = tuple(
        store.enqueue_job(
            job_id=job.job_id,
            capability=owner,
            at_utc=NOW + timedelta(microseconds=index + 1),
            expected_version=job.version,
            operation_id=_operation(200 + index),
        )
        for index, (job, owner) in enumerate(zip(staged, owners, strict=True))
    )
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    results = context.Queue()
    processes = tuple(
        context.Process(
            target=_claim_in_process,
            args=(str(database), 210 + index, start, results),
        )
        for index in range(2)
    )
    for process in processes:
        process.start()
    start.set()
    claims = [results.get(timeout=10) for _ in processes]
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0

    assert claims.count(queued[0].job_id) == 1
    assert claims.count(None) == 1
    running = store.get_job(job_id=queued[0].job_id, capability=owners[0])
    terminal = transition_execution(
        running,
        target=ExecutionState.TERMINAL,
        outcome=TerminalOutcome.SUCCEEDED,
        at_utc=NOW + timedelta(seconds=3),
        tombstone_expires_at_utc=NOW + timedelta(days=7, seconds=3),
        expected_version=running.version,
        operation_id=_operation(220),
    )
    store.compare_and_swap(
        job_id=running.job_id,
        capability=owners[0],
        expected_version=running.version,
        updated=terminal,
        at_utc=NOW + timedelta(seconds=3),
    )
    second = store.claim_next(
        at_utc=NOW + timedelta(seconds=4),
        operation_id=_operation(221),
    )
    assert second is not None
    assert second.job_id == queued[1].job_id


def test_corrupt_control_row_and_transition_failure_roll_back(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "control.sqlite3"
    store = _store(database)
    owner = _capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    _bind(store, staged, owner)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE analysis_admissions SET expires_at_utc = 'not-a-time'")
        connection.commit()
    _expect(
        JobStoreError,
        JobStoreErrorCode.CORRUPT_RECORD,
        lambda: store.consume_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=staged.job_id,
            capability=owner,
            at_utc=NOW,
            operation_id=_operation(1),
        ),
    )

    second_database = tmp_path / "transition.sqlite3"
    second = _store(second_database)
    second_owner = _capability(2)
    second_job = second.stage_job(capability=second_owner, at_utc=NOW)
    _bind(second, second_job, second_owner)

    def fail_transition(*_args, **_kwargs):
        raise ValueError("private transition detail")

    monkeypatch.setattr(job_store_module, "transition_execution", fail_transition)
    _expect(
        AnalysisAdmissionRejectedError,
        JobStoreErrorCode.ANALYSIS_ADMISSION_REJECTED,
        lambda: second.consume_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=second_job.job_id,
            capability=second_owner,
            at_utc=NOW,
            operation_id=_operation(2),
        ),
    )
    with closing(sqlite3.connect(second_database)) as connection:
        assert connection.execute(
            "SELECT consumed_at_utc, version FROM analysis_admissions"
        ).fetchone() == (None, 0)
        assert connection.execute("SELECT execution_state FROM jobs").fetchone() == ("staged",)


@pytest.mark.parametrize(
    "mutation",
    ["parse", "noncanonical", "version", "consumed-after-expiry"],
)
def test_corrupt_analysis_admission_rows_fail_closed(tmp_path: Path, mutation: str) -> None:
    database = tmp_path / "control.sqlite3"
    store = _store(database)
    owner = _capability(1)
    staged = store.stage_job(capability=owner, at_utc=NOW)
    _bind(store, staged, owner)
    with closing(sqlite3.connect(database)) as connection:
        if mutation == "parse":
            connection.execute("UPDATE analysis_admissions SET expires_at_utc = 'not-a-timeZ'")
        elif mutation == "noncanonical":
            connection.execute(
                """
                UPDATE analysis_admissions
                SET expires_at_utc = '2026-07-14T22:30:00.000000Z'
                """
            )
        elif mutation == "version":
            connection.execute("UPDATE analysis_admissions SET version = 2")
        else:
            connection.execute("PRAGMA ignore_check_constraints = ON")
            connection.execute(
                """
                UPDATE analysis_admissions
                SET consumed_at_utc = expires_at_utc, version = 1
                """
            )
        connection.commit()

    _expect(
        JobStoreError,
        JobStoreErrorCode.CORRUPT_RECORD,
        lambda: store.consume_analysis_admission(
            receipt_hmac=RECEIPT_HMAC,
            job_id=staged.job_id,
            capability=owner,
            at_utc=NOW,
            operation_id=_operation(1),
        ),
    )


def test_schema_v2_migrates_to_v3_and_rejects_future_v4(tmp_path: Path) -> None:
    migrated = tmp_path / "migrated.sqlite3"
    with closing(sqlite3.connect(migrated)) as connection:
        connection.execute("PRAGMA user_version = 2")
        connection.commit()
    _store(migrated)
    with closing(sqlite3.connect(migrated)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (3,)
        assert connection.execute(
            "SELECT name FROM sqlite_schema WHERE name = 'analysis_admissions'"
        ).fetchone() == ("analysis_admissions",)

    future = tmp_path / "future.sqlite3"
    with closing(sqlite3.connect(future)) as connection:
        connection.execute("PRAGMA user_version = 4")
        connection.commit()
    _expect(
        JobStoreError,
        JobStoreErrorCode.INVALID_DATABASE,
        lambda: _store(future),
    )
