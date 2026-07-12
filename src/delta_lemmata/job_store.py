"""Payload-free SQLite persistence and atomic admission for ephemeral jobs."""

from __future__ import annotations

import os
import sqlite3
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import StrEnum
from functools import wraps
from pathlib import Path
from typing import NoReturn, cast

from pydantic import ValidationError

from delta_lemmata.clock import require_utc
from delta_lemmata.job_models import (
    ArtifactKind,
    CleanupState,
    ExecutionState,
    JobModelError,
    JobRecord,
    TerminalOutcome,
    VersionConflictError,
    new_staged_job,
    publish_export,
    request_cancellation,
    transition_artifact,
    transition_execution,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY, JobPolicy
from delta_lemmata.session_identity import (
    MINIMUM_OWNER_SECRET_BYTES,
    JobId,
    SessionCapability,
    SessionIdentityError,
    owner_digest,
    verify_owner_digest,
)

JobIdFactory = Callable[[], JobId]

_DATABASE_MODE = 0o600
_BUSY_TIMEOUT_MILLISECONDS = 30_000
_SCHEMA_VERSION = 1
_ZERO_DIGEST = bytes(32)

_SELECT_JOB = """
SELECT job_id, owner_digest, execution_state, deadline_at_utc,
       queue_sequence, version, model_json
FROM jobs
WHERE job_id = ?
"""

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY CHECK (length(job_id) = 43),
    owner_digest TEXT NOT NULL CHECK (length(owner_digest) = 64),
    execution_state TEXT NOT NULL
        CHECK (execution_state IN ('staged', 'queued', 'running', 'terminal')),
    deadline_at_utc TEXT,
    queue_sequence INTEGER UNIQUE,
    version INTEGER NOT NULL CHECK (version >= 0),
    model_json TEXT NOT NULL,
    CHECK ((execution_state IN ('staged', 'queued')) = (deadline_at_utc IS NOT NULL)),
    CHECK ((execution_state = 'queued') = (queue_sequence IS NOT NULL))
) STRICT;

CREATE TABLE IF NOT EXISTS events (
    sequence INTEGER PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    event_code TEXT NOT NULL
        CHECK (event_code IN ('JOB_STAGED', 'JOB_QUEUED', 'JOB_RUNNING', 'JOB_UPDATED')),
    occurred_at_utc TEXT NOT NULL,
    expires_at_utc TEXT NOT NULL
) STRICT;

CREATE INDEX IF NOT EXISTS jobs_execution_queue_idx
ON jobs (execution_state, queue_sequence);

CREATE INDEX IF NOT EXISTS events_expiry_idx
ON events (expires_at_utc);
"""


class JobStoreErrorCode(StrEnum):
    """Stable, content-free control-store failure codes."""

    INVALID_DATABASE = "JOB_STORE_INVALID_DATABASE"
    DATABASE_FAILURE = "JOB_STORE_DATABASE_FAILURE"
    CORRUPT_RECORD = "JOB_STORE_CORRUPT_RECORD"
    INVALID_CONFIGURATION = "JOB_STORE_INVALID_CONFIGURATION"
    IDENTIFIER_GENERATION_FAILED = "JOB_IDENTIFIER_GENERATION_FAILED"
    ADMISSION_REJECTED = "JOB_ADMISSION_REJECTED"
    NOT_AVAILABLE = "JOB_NOT_AVAILABLE"
    INVALID_UPDATE = "JOB_STORE_INVALID_UPDATE"


class JobStoreError(RuntimeError):
    """A store rejection that never contains database or research content."""

    def __init__(self, code: JobStoreErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class JobAdmissionRejectedError(JobStoreError):
    """A capacity or immutable-deadline admission rejection."""

    def __init__(self) -> None:
        super().__init__(JobStoreErrorCode.ADMISSION_REJECTED)


class JobNotAvailableError(JobStoreError):
    """The common response for both unknown and unauthorized job access."""

    def __init__(self) -> None:
        super().__init__(JobStoreErrorCode.NOT_AVAILABLE)


def _detach(error: JobStoreError) -> None:
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True


def _content_free[**P, T](method: Callable[P, T]) -> Callable[P, T]:
    @wraps(method)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return method(*args, **kwargs)
        except JobStoreError as error:
            rejection = error
        except (OSError, sqlite3.Error):
            rejection = JobStoreError(JobStoreErrorCode.DATABASE_FAILURE)
        _detach(rejection)
        raise rejection

    return wrapped


def _invalid_update() -> NoReturn:
    raise JobStoreError(JobStoreErrorCode.INVALID_UPDATE)


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


class SQLiteJobStore:
    """A process-safe, payload-free SQLite job registry using short connections."""

    @_content_free
    def __init__(
        self,
        database_file: Path,
        *,
        owner_secret: bytes,
        policy: JobPolicy = DEFAULT_JOB_POLICY,
        job_id_factory: JobIdFactory = JobId.generate,
    ) -> None:
        if (
            not isinstance(database_file, Path)
            or not database_file.is_absolute()
            or database_file != Path(os.path.abspath(database_file))
        ):
            raise JobStoreError(JobStoreErrorCode.INVALID_DATABASE)
        if (
            not isinstance(owner_secret, bytes)
            or len(owner_secret) < MINIMUM_OWNER_SECRET_BYTES
            or not isinstance(policy, JobPolicy)
            or not callable(job_id_factory)
        ):
            raise JobStoreError(JobStoreErrorCode.INVALID_CONFIGURATION)
        self.database_file = database_file
        self._owner_secret = owner_secret
        self._policy = policy
        self._job_id_factory = job_id_factory
        self._directory_identity = self._validate_database_directory(database_file.parent)
        self._harden_file(database_file, create=True)
        self._initialize_schema()
        self._harden_database_files()

    @staticmethod
    def _validate_database_directory(directory: Path) -> tuple[int, int]:
        try:
            info = os.lstat(directory)
            resolved = directory.resolve(strict=True)
            resolved_info = os.stat(resolved, follow_symlinks=False)
        except OSError:
            raise JobStoreError(JobStoreErrorCode.INVALID_DATABASE) from None
        if (
            directory != resolved
            or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or (info.st_dev, info.st_ino) != (resolved_info.st_dev, resolved_info.st_ino)
        ):
            raise JobStoreError(JobStoreErrorCode.INVALID_DATABASE)
        return info.st_dev, info.st_ino

    def _verify_database_directory(self) -> None:
        if self._validate_database_directory(self.database_file.parent) != self._directory_identity:
            raise JobStoreError(JobStoreErrorCode.INVALID_DATABASE)

    def _harden_file(self, path: Path, *, create: bool) -> None:
        flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        if create:
            flags |= os.O_CREAT
        try:
            descriptor = os.open(path, flags, _DATABASE_MODE)
        except FileNotFoundError:
            if not create:
                return
            raise JobStoreError(  # pragma: no cover - verified parent removal race
                JobStoreErrorCode.INVALID_DATABASE
            ) from None
        except OSError:
            raise JobStoreError(JobStoreErrorCode.INVALID_DATABASE) from None
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                raise JobStoreError(JobStoreErrorCode.INVALID_DATABASE)
            os.fchmod(descriptor, _DATABASE_MODE)
        finally:
            os.close(descriptor)

    def _harden_database_files(self) -> None:
        self._verify_database_directory()
        self._harden_file(self.database_file, create=False)
        self._harden_file(Path(f"{self.database_file}-wal"), create=False)
        self._harden_file(Path(f"{self.database_file}-shm"), create=False)

    def _initialize_schema(self) -> None:
        connection = sqlite3.connect(
            self.database_file,
            timeout=_BUSY_TIMEOUT_MILLISECONDS / 1000,
            isolation_level=None,
        )
        try:
            self._configure(connection)
            journal_row = cast(
                tuple[str], connection.execute("PRAGMA journal_mode = WAL").fetchone()
            )
            if journal_row[0].lower() != "wal":
                raise JobStoreError(JobStoreErrorCode.INVALID_DATABASE)
            version_row = cast(tuple[int], connection.execute("PRAGMA user_version").fetchone())
            if version_row[0] not in {0, _SCHEMA_VERSION}:
                raise JobStoreError(JobStoreErrorCode.INVALID_DATABASE)
            connection.executescript(_SCHEMA)
            connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
        finally:
            connection.close()

    @staticmethod
    def _configure(connection: sqlite3.Connection) -> None:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MILLISECONDS}")

    def _connect(self) -> sqlite3.Connection:
        self._harden_database_files()
        connection = sqlite3.connect(
            self.database_file,
            timeout=_BUSY_TIMEOUT_MILLISECONDS / 1000,
            isolation_level=None,
        )
        try:
            self._configure(connection)
            journal_row = cast(tuple[str], connection.execute("PRAGMA journal_mode").fetchone())
            if journal_row[0].lower() != "wal":
                raise JobStoreError(JobStoreErrorCode.INVALID_DATABASE)
        except Exception:
            connection.close()
            raise
        return connection

    @contextmanager
    def _read_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            try:
                connection.close()
            finally:
                self._harden_database_files()

    @contextmanager
    def _immediate(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
        finally:
            try:
                connection.close()
            finally:
                self._harden_database_files()

    @staticmethod
    def _coerce_job_id(value: JobId | str) -> JobId:
        try:
            return value if isinstance(value, JobId) else JobId.from_urlsafe(value)
        except (SessionIdentityError, TypeError):
            raise JobNotAvailableError from None

    @staticmethod
    def _digest_bytes(value: object) -> bytes:
        try:
            decoded = bytes.fromhex(cast(str, value))
        except (TypeError, ValueError):
            raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD) from None
        if len(decoded) != len(_ZERO_DIGEST):
            raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD)
        return decoded

    def _owner_matches(
        self,
        *,
        job_id: object,
        stored_digest: object,
        capability: SessionCapability,
    ) -> bool:
        try:
            parsed_id = JobId.from_urlsafe(cast(str, job_id))
            digest = self._digest_bytes(stored_digest)
            return verify_owner_digest(
                owner_secret=self._owner_secret,
                capability=capability,
                job_id=parsed_id,
                expected_digest=digest,
            )
        except SessionIdentityError:
            raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD) from None

    @staticmethod
    def _decode(row: sqlite3.Row) -> JobRecord:
        try:
            job = JobRecord.model_validate_json(cast(str, row["model_json"]))
            deadline = (
                None
                if job.execution.deadline_at_utc is None
                else _timestamp(job.execution.deadline_at_utc)
            )
            queued = job.execution.state is ExecutionState.QUEUED
            if (
                job.job_id != row["job_id"]
                or job.owner_digest != row["owner_digest"]
                or job.execution.state.value != row["execution_state"]
                or deadline != row["deadline_at_utc"]
                or job.version != row["version"]
                or queued != (row["queue_sequence"] is not None)
            ):
                raise ValueError
            return job
        except (IndexError, TypeError, ValueError, ValidationError):
            raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD) from None

    def _load_authorized(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: JobId | str,
        capability: SessionCapability,
    ) -> tuple[JobRecord, int | None]:
        parsed_id = self._coerce_job_id(job_id)
        if not isinstance(capability, SessionCapability):
            raise JobNotAvailableError
        row = connection.execute(_SELECT_JOB, (parsed_id.to_urlsafe(),)).fetchone()
        expected_digest = _ZERO_DIGEST if row is None else self._digest_bytes(row["owner_digest"])
        try:
            authorized = verify_owner_digest(
                owner_secret=self._owner_secret,
                capability=capability,
                job_id=parsed_id,
                expected_digest=expected_digest,
            )
        except SessionIdentityError:
            raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD) from None
        if row is None or not authorized:
            raise JobNotAvailableError
        return self._decode(row), cast(int | None, row["queue_sequence"])

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        *,
        job: JobRecord,
        event_code: str,
        at_utc: datetime,
    ) -> int:
        connection.execute(
            """
            INSERT INTO events (job_id, event_code, occurred_at_utc, expires_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            (
                job.job_id,
                event_code,
                _timestamp(at_utc),
                _timestamp(job.event_expires_at_utc),
            ),
        )
        row = cast(sqlite3.Row, connection.execute("SELECT last_insert_rowid()").fetchone())
        return int(row[0])

    @staticmethod
    def _insert_job(connection: sqlite3.Connection, job: JobRecord) -> None:
        connection.execute(
            """
            INSERT INTO jobs (
                job_id, owner_digest, execution_state, deadline_at_utc,
                queue_sequence, version, model_json
            )
            VALUES (?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                job.job_id,
                job.owner_digest,
                job.execution.state.value,
                _timestamp(cast(datetime, job.execution.deadline_at_utc)),
                job.version,
                job.model_dump_json(),
            ),
        )

    @staticmethod
    def _write_job(
        connection: sqlite3.Connection,
        *,
        previous: JobRecord,
        updated: JobRecord,
        queue_sequence: int | None,
    ) -> None:
        deadline = (
            None
            if updated.execution.deadline_at_utc is None
            else _timestamp(updated.execution.deadline_at_utc)
        )
        cursor = connection.execute(
            """
            UPDATE jobs
            SET owner_digest = ?, execution_state = ?, deadline_at_utc = ?,
                queue_sequence = ?, version = ?, model_json = ?
            WHERE job_id = ? AND version = ?
            """,
            (
                updated.owner_digest,
                updated.execution.state.value,
                deadline,
                queue_sequence,
                updated.version,
                updated.model_dump_json(),
                previous.job_id,
                previous.version,
            ),
        )
        if cursor.rowcount != 1:  # pragma: no cover - serialized transaction invariant
            raise VersionConflictError

    @staticmethod
    def _validate_successor(previous: JobRecord, updated: JobRecord) -> None:
        if (
            updated.job_id != previous.job_id
            or updated.owner_digest != previous.owner_digest
            or updated.policy_version != previous.policy_version
            or updated.version != previous.version + 1
            or updated.operations[:-1] != previous.operations
            or len(updated.operations) != len(previous.operations) + 1
        ):
            _invalid_update()
        operation = updated.operations[-1]
        action = operation.action
        try:
            if action.startswith("execution:"):
                if updated.execution.state is not ExecutionState.TERMINAL:
                    _invalid_update()
                outcome = cast(TerminalOutcome, updated.outcome.kind if updated.outcome else None)
                expected = transition_execution(
                    previous,
                    target=updated.execution.state,
                    at_utc=updated.execution.entered_at_utc,
                    expected_version=previous.version,
                    operation_id=operation.operation_id,
                    deadline_at_utc=updated.execution.deadline_at_utc,
                    outcome=outcome,
                    tombstone_expires_at_utc=updated.tombstone_expires_at_utc,
                )
            elif action == "cancellation:requested":
                if updated.cancellation.requested_at_utc is None:
                    _invalid_update()
                expected = request_cancellation(
                    previous,
                    at_utc=updated.cancellation.requested_at_utc,
                    expected_version=previous.version,
                    operation_id=operation.operation_id,
                )
            elif action.startswith("artifact:"):
                parts = action.split(":")
                if len(parts) != 3:
                    _invalid_update()
                kind = ArtifactKind(parts[1])
                target = CleanupState(parts[2])
                artifact = updated.artifacts.for_kind(kind)
                at_utc = artifact.verified_at_utc or previous.execution.entered_at_utc
                expected = transition_artifact(
                    previous,
                    kind=kind,
                    target=target,
                    at_utc=at_utc,
                    expected_version=previous.version,
                    operation_id=operation.operation_id,
                    delete_by_utc=artifact.delete_by_utc,
                )
            elif action == "export:publish":
                expected = publish_export(
                    previous,
                    expected_version=previous.version,
                    operation_id=operation.operation_id,
                )
            else:
                _invalid_update()
        except (JobModelError, ValueError):
            _invalid_update()
        if expected != updated:
            _invalid_update()

    @_content_free
    def stage_job(self, *, capability: SessionCapability, at_utc: datetime) -> JobRecord:
        """Atomically admit one staged lease without allocating on rejection."""

        at_utc = require_utc(at_utc, field_name="at_utc")
        if not isinstance(capability, SessionCapability):
            raise JobAdmissionRejectedError
        with self._immediate() as connection:
            rows = connection.execute(
                """
                SELECT job_id, owner_digest, execution_state
                FROM jobs
                WHERE execution_state != 'terminal'
                """
            ).fetchall()
            staged_count = 0
            owned_count = 0
            for row in rows:
                if row["execution_state"] == ExecutionState.STAGED.value:
                    staged_count += 1
                if self._owner_matches(
                    job_id=row["job_id"],
                    stored_digest=row["owner_digest"],
                    capability=capability,
                ):
                    owned_count += 1
            if (
                owned_count >= self._policy.max_active_per_session
                or staged_count >= self._policy.max_staged_global
            ):
                raise JobAdmissionRejectedError
            try:
                generated_id = self._job_id_factory()
            except Exception:
                raise JobStoreError(JobStoreErrorCode.IDENTIFIER_GENERATION_FAILED) from None
            if not isinstance(generated_id, JobId):
                raise JobStoreError(JobStoreErrorCode.IDENTIFIER_GENERATION_FAILED)
            digest = owner_digest(
                owner_secret=self._owner_secret,
                capability=capability,
                job_id=generated_id,
            ).hex()
            job = new_staged_job(
                job_id=generated_id.to_urlsafe(),
                owner_digest=digest,
                policy_version=self._policy.profile_version,
                at_utc=at_utc,
                staged_ttl_seconds=self._policy.staged_ttl_seconds,
                event_ttl_seconds=self._policy.event_ttl_seconds,
            )
            self._insert_job(connection, job)
            self._insert_event(
                connection,
                job=job,
                event_code="JOB_STAGED",
                at_utc=at_utc,
            )
            return job

    create_staged = stage_job

    @_content_free
    def get_job(
        self,
        *,
        job_id: JobId | str,
        capability: SessionCapability,
    ) -> JobRecord:
        """Return one owned snapshot without distinguishing denial from absence."""

        with self._read_connection() as connection:
            job, _queue_sequence = self._load_authorized(
                connection,
                job_id=job_id,
                capability=capability,
            )
            return job

    load_job = get_job

    @_content_free
    def enqueue_job(
        self,
        *,
        job_id: JobId | str,
        capability: SessionCapability,
        at_utc: datetime,
        expected_version: int,
        operation_id: str,
    ) -> JobRecord:
        """Atomically move an owned staged lease into the bounded FIFO queue."""

        at_utc = require_utc(at_utc, field_name="at_utc")
        with self._immediate() as connection:
            previous, _queue_sequence = self._load_authorized(
                connection,
                job_id=job_id,
                capability=capability,
            )
            updated = transition_execution(
                previous,
                target=ExecutionState.QUEUED,
                at_utc=at_utc,
                deadline_at_utc=at_utc + timedelta(seconds=self._policy.queued_ttl_seconds),
                expected_version=expected_version,
                operation_id=operation_id,
            )
            if updated == previous:
                return previous
            if (
                previous.execution.deadline_at_utc is None
                or at_utc >= previous.execution.deadline_at_utc
            ):
                raise JobAdmissionRejectedError
            count_row = cast(
                sqlite3.Row,
                connection.execute(
                    "SELECT COUNT(*) FROM jobs WHERE execution_state = 'queued'"
                ).fetchone(),
            )
            if int(count_row[0]) >= self._policy.max_queued:
                raise JobAdmissionRejectedError
            queue_sequence = self._insert_event(
                connection,
                job=updated,
                event_code="JOB_QUEUED",
                at_utc=at_utc,
            )
            self._write_job(
                connection,
                previous=previous,
                updated=updated,
                queue_sequence=queue_sequence,
            )
            return updated

    @_content_free
    def claim_next(self, *, at_utc: datetime, operation_id: str) -> JobRecord | None:
        """Claim the oldest unexpired queued job if no worker is already running."""

        at_utc = require_utc(at_utc, field_name="at_utc")
        with self._immediate() as connection:
            running_row = cast(
                sqlite3.Row,
                connection.execute(
                    "SELECT COUNT(*) FROM jobs WHERE execution_state = 'running'"
                ).fetchone(),
            )
            if int(running_row[0]) >= self._policy.max_running:
                return None
            row = connection.execute(
                """
                SELECT job_id, owner_digest, execution_state, deadline_at_utc,
                       queue_sequence, version, model_json
                FROM jobs
                WHERE execution_state = 'queued' AND deadline_at_utc > ?
                ORDER BY queue_sequence ASC
                LIMIT 1
                """,
                (_timestamp(at_utc),),
            ).fetchone()
            if row is None:
                return None
            previous = self._decode(row)
            if at_utc < previous.execution.entered_at_utc:
                return None
            updated = transition_execution(
                previous,
                target=ExecutionState.RUNNING,
                at_utc=at_utc,
                expected_version=previous.version,
                operation_id=operation_id,
            )
            self._insert_event(
                connection,
                job=updated,
                event_code="JOB_RUNNING",
                at_utc=at_utc,
            )
            self._write_job(
                connection,
                previous=previous,
                updated=updated,
                queue_sequence=None,
            )
            return updated

    claim_next_job = claim_next

    @_content_free
    def compare_and_swap(
        self,
        *,
        job_id: JobId | str,
        capability: SessionCapability,
        expected_version: int,
        updated: JobRecord,
        at_utc: datetime,
    ) -> JobRecord:
        """Persist exactly one model-helper transition with optimistic version CAS."""

        at_utc = require_utc(at_utc, field_name="at_utc")
        if not isinstance(updated, JobRecord):
            _invalid_update()
        with self._immediate() as connection:
            previous, queue_sequence = self._load_authorized(
                connection,
                job_id=job_id,
                capability=capability,
            )
            if updated == previous:
                return previous
            if previous.version != expected_version:
                raise VersionConflictError
            self._validate_successor(previous, updated)
            next_queue_sequence = (
                queue_sequence if updated.execution.state is ExecutionState.QUEUED else None
            )
            self._insert_event(
                connection,
                job=updated,
                event_code="JOB_UPDATED",
                at_utc=at_utc,
            )
            self._write_job(
                connection,
                previous=previous,
                updated=updated,
                queue_sequence=next_queue_sequence,
            )
            return updated

    save_job = compare_and_swap


__all__ = [
    "JobAdmissionRejectedError",
    "JobIdFactory",
    "JobNotAvailableError",
    "JobStoreError",
    "JobStoreErrorCode",
    "SQLiteJobStore",
]
