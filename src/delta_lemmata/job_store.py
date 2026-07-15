"""Payload-free SQLite persistence and atomic admission for ephemeral jobs."""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from functools import wraps
from pathlib import Path
from typing import NoReturn, cast

from pydantic import ValidationError

from delta_lemmata.clock import require_utc
from delta_lemmata.job_events import DeletionEvent
from delta_lemmata.job_models import (
    ArtifactKind,
    CancellationState,
    CleanupState,
    ExecutionState,
    JobModelError,
    JobRecord,
    ScientificResultReceipt,
    TerminalOutcome,
    VersionConflictError,
    commit_result_view,
    confirm_scientific_result,
    new_staged_job,
    publish_export,
    request_cancellation,
    retire_export,
    terminal_operation_version,
    transition_artifact,
    transition_execution,
    transition_scientific_execution_claim,
    transition_scientific_success,
    withdraw_export,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY, JobPolicy
from delta_lemmata.session_identity import (
    MINIMUM_OWNER_SECRET_BYTES,
    JobId,
    SessionCapability,
    SessionIdentityError,
    owner_digest,
    verify_owner_digest,
    workspace_component,
)

JobIdFactory = Callable[[], JobId]

_DATABASE_MODE = 0o600
_BUSY_TIMEOUT_MILLISECONDS = 30_000
_SCHEMA_VERSION = 3
_ZERO_DIGEST = bytes(32)
_OPERATION_REFERENCE = re.compile(r"^op_[0-9a-f]{64}$", flags=re.ASCII)
_RECEIPT_HMAC = re.compile(r"^[0-9a-f]{64}$", flags=re.ASCII)
_ADMISSION_OPERATION_DOMAIN = b"delta-lemmata\x00queued-admission\x00v1\x00"
_ADMISSION_ABANDONMENT_DOMAIN = b"delta-lemmata\x00admission-abandonment\x00v1\x00"
_QUEUE_CANCELLATION_DOMAIN = b"delta-lemmata\x00queue-cancellation\x00v1\x00"

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

CREATE TABLE IF NOT EXISTS deletion_events (
    sequence INTEGER PRIMARY KEY,
    event_code TEXT NOT NULL CHECK (event_code = 'JOB_ARTIFACTS_DELETED'),
    job_reference_digest TEXT NOT NULL CHECK (length(job_reference_digest) = 64),
    occurred_at_utc TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (
        reason IN (
            'staged_expired', 'queue_expired', 'successful_terminal',
            'unsuccessful_terminal', 'result_expired', 'export_expired',
            'owner_request', 'startup_recovery'
        )
    ),
    file_count INTEGER NOT NULL CHECK (file_count >= 0),
    byte_count INTEGER NOT NULL CHECK (byte_count >= 0),
    policy_version TEXT NOT NULL CHECK (policy_version = 'job-policy-v1'),
    expires_at_utc TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS analysis_admissions (
    receipt_hmac TEXT PRIMARY KEY CHECK (length(receipt_hmac) = 64),
    job_id TEXT NOT NULL UNIQUE REFERENCES jobs(job_id) ON DELETE CASCADE,
    owner_digest TEXT NOT NULL CHECK (length(owner_digest) = 64),
    expected_job_version INTEGER NOT NULL CHECK (expected_job_version >= 0),
    expires_at_utc TEXT NOT NULL,
    consumed_at_utc TEXT,
    version INTEGER NOT NULL CHECK (version >= 0),
    CHECK (consumed_at_utc IS NULL OR consumed_at_utc < expires_at_utc)
) STRICT;

CREATE INDEX IF NOT EXISTS jobs_execution_queue_idx
ON jobs (execution_state, queue_sequence);

CREATE INDEX IF NOT EXISTS events_expiry_idx
ON events (expires_at_utc);

CREATE INDEX IF NOT EXISTS deletion_events_expiry_idx
ON deletion_events (expires_at_utc);

CREATE UNIQUE INDEX IF NOT EXISTS deletion_events_identity_idx
ON deletion_events (job_reference_digest, occurred_at_utc, reason);

CREATE INDEX IF NOT EXISTS analysis_admissions_expiry_idx
ON analysis_admissions (expires_at_utc);
"""


@dataclass(frozen=True, slots=True)
class StorePurgeReport:
    """Content-free counts from one bounded control-store purge."""

    operational_events_deleted: int
    deletion_events_deleted: int
    tombstones_deleted: int
    tombstones_blocked: int


class JobStoreErrorCode(StrEnum):
    """Stable, content-free control-store failure codes."""

    INVALID_DATABASE = "JOB_STORE_INVALID_DATABASE"
    DATABASE_FAILURE = "JOB_STORE_DATABASE_FAILURE"
    CORRUPT_RECORD = "JOB_STORE_CORRUPT_RECORD"
    INVALID_CONFIGURATION = "JOB_STORE_INVALID_CONFIGURATION"
    IDENTIFIER_GENERATION_FAILED = "JOB_IDENTIFIER_GENERATION_FAILED"
    ADMISSION_REJECTED = "JOB_ADMISSION_REJECTED"
    ADMISSION_CLEANUP_UNRESOLVED = "JOB_ADMISSION_CLEANUP_UNRESOLVED"
    NOT_AVAILABLE = "JOB_NOT_AVAILABLE"
    INVALID_UPDATE = "JOB_STORE_INVALID_UPDATE"
    ANALYSIS_ADMISSION_REJECTED = "ANALYSIS_ADMISSION_REJECTED"
    ANALYSIS_ADMISSION_REUSED = "ANALYSIS_ADMISSION_REUSED"


class JobStoreError(RuntimeError):
    """A store rejection that never contains database or research content."""

    def __init__(self, code: JobStoreErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class JobAdmissionRejectedError(JobStoreError):
    """A capacity or immutable-deadline admission rejection."""

    def __init__(self) -> None:
        super().__init__(JobStoreErrorCode.ADMISSION_REJECTED)


class JobAdmissionCleanupUnresolvedError(JobStoreError):
    """Request an atomically tracked terminal record for an uncleared workspace."""

    def __init__(self) -> None:
        super().__init__(JobStoreErrorCode.ADMISSION_CLEANUP_UNRESOLVED)


class JobNotAvailableError(JobStoreError):
    """The common response for both unknown and unauthorized job access."""

    def __init__(self) -> None:
        super().__init__(JobStoreErrorCode.NOT_AVAILABLE)


class AnalysisAdmissionRejectedError(JobStoreError):
    """A READY binding or queue transition failed closed."""

    def __init__(self) -> None:
        super().__init__(JobStoreErrorCode.ANALYSIS_ADMISSION_REJECTED)


class AnalysisAdmissionReusedError(JobStoreError):
    """An authorized one-time READY receipt was already consumed."""

    def __init__(self) -> None:
        super().__init__(JobStoreErrorCode.ANALYSIS_ADMISSION_REUSED)


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


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD)
    try:
        parsed = require_utc(
            datetime.fromisoformat(value[:-1] + "+00:00"),
            field_name="stored timestamp",
        )
    except Exception:
        raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD) from None
    if _timestamp(parsed) != value:
        raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD)
    return parsed


def _admission_operation_id(job: JobRecord) -> str:
    material = _ADMISSION_OPERATION_DOMAIN + job.job_id.encode("ascii")
    return "op_" + hashlib.sha256(material).hexdigest()


def _admission_abandonment_operation_id(job: JobRecord) -> str:
    material = _ADMISSION_ABANDONMENT_DOMAIN + job.job_id.encode("ascii")
    return "op_" + hashlib.sha256(material).hexdigest()


def _queue_cancellation_operation_id(job: JobRecord) -> str:
    material = _QUEUE_CANCELLATION_DOMAIN + job.job_id.encode("ascii")
    return "op_" + hashlib.sha256(material).hexdigest()


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

    def _harden_file(
        self,
        path: Path,
        *,
        create: bool,
        allow_unlinked: bool = False,
    ) -> None:
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
            valid_link_count = info.st_nlink == 1 or (allow_unlinked and info.st_nlink == 0)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or not valid_link_count:
                raise JobStoreError(JobStoreErrorCode.INVALID_DATABASE)
            if info.st_nlink == 1:
                os.fchmod(descriptor, _DATABASE_MODE)
        finally:
            os.close(descriptor)

    def _harden_database_files(self) -> None:
        self._verify_database_directory()
        self._harden_file(self.database_file, create=False)
        self._harden_file(
            Path(f"{self.database_file}-wal"),
            create=False,
            allow_unlinked=True,
        )
        self._harden_file(
            Path(f"{self.database_file}-shm"),
            create=False,
            allow_unlinked=True,
        )

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
            if version_row[0] not in {0, 1, 2, _SCHEMA_VERSION}:
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
            JobId.from_urlsafe(job.job_id)
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

    def _load_system(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: JobId | str,
    ) -> tuple[JobRecord, int | None]:
        parsed_id = self._coerce_job_id(job_id)
        row = connection.execute(_SELECT_JOB, (parsed_id.to_urlsafe(),)).fetchone()
        if row is None:
            raise JobNotAvailableError
        return self._decode(row), cast(int | None, row["queue_sequence"])

    @staticmethod
    def _decode_deletion_event(row: sqlite3.Row) -> DeletionEvent:
        try:
            return DeletionEvent.model_validate(
                {
                    "event_code": row["event_code"],
                    "job_reference_digest": row["job_reference_digest"],
                    "occurred_at_utc": row["occurred_at_utc"],
                    "reason": row["reason"],
                    "file_count": row["file_count"],
                    "byte_count": row["byte_count"],
                    "policy_version": row["policy_version"],
                    "expires_at_utc": row["expires_at_utc"],
                }
            )
        except (IndexError, TypeError, ValueError, ValidationError):
            raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD) from None

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

    def _insert_deletion_event(
        self,
        connection: sqlite3.Connection,
        *,
        job: JobRecord,
        event: DeletionEvent,
        at_utc: datetime,
    ) -> bool:
        parsed_id = JobId.from_urlsafe(job.job_id)
        if (
            event.job_reference_digest != workspace_component(parsed_id)
            or event.policy_version != job.policy_version
            or event.occurred_at_utc != at_utc
            or event.expires_at_utc != at_utc + timedelta(seconds=self._policy.event_ttl_seconds)
        ):
            _invalid_update()
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO deletion_events (
                event_code, job_reference_digest, occurred_at_utc, reason,
                file_count, byte_count, policy_version, expires_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_code,
                event.job_reference_digest,
                _timestamp(event.occurred_at_utc),
                event.reason.value,
                event.file_count,
                event.byte_count,
                event.policy_version,
                _timestamp(event.expires_at_utc),
            ),
        )
        return cursor.rowcount == 1

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
            if action == "scientific:execution:claimed":
                expected = transition_scientific_execution_claim(
                    previous,
                    expected_version=previous.version,
                    operation_id=operation.operation_id,
                )
            elif action.startswith("execution:"):
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
            elif action.startswith("scientific:terminal:succeeded:"):
                tombstone_expires_at_utc = updated.tombstone_expires_at_utc
                if (
                    updated.execution.state is not ExecutionState.TERMINAL
                    or updated.outcome is None
                    or updated.scientific_result is None
                    or tombstone_expires_at_utc is None
                ):
                    _invalid_update()
                expected = transition_scientific_success(
                    previous,
                    receipt=updated.scientific_result,
                    at_utc=updated.execution.entered_at_utc,
                    expected_version=previous.version,
                    operation_id=operation.operation_id,
                    tombstone_expires_at_utc=tombstone_expires_at_utc,
                )
            elif action.startswith("scientific:guardian:confirmed:"):
                expected = confirm_scientific_result(
                    previous,
                    expected_version=previous.version,
                    operation_id=operation.operation_id,
                )
            elif action.startswith("result_view:staged:"):
                if updated.result_view is None:
                    _invalid_update()
                expected = commit_result_view(
                    previous,
                    receipt=updated.result_view,
                    at_utc=previous.execution.entered_at_utc,
                    expected_version=previous.version,
                    operation_id=operation.operation_id,
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
            elif action == "export:retire":
                verified_at = updated.artifacts.export.verified_at_utc
                if verified_at is None:
                    _invalid_update()
                expected = retire_export(
                    previous,
                    at_utc=verified_at,
                    expected_version=previous.version,
                    operation_id=operation.operation_id,
                )
            elif action == "export:withdraw":
                verified_at = updated.artifacts.export.verified_at_utc
                if verified_at is None:
                    _invalid_update()
                expected = withdraw_export(
                    previous,
                    at_utc=verified_at,
                    expected_version=previous.version,
                    operation_id=operation.operation_id,
                )
            else:
                _invalid_update()
        except (JobModelError, ValueError):
            _invalid_update()
        if expected != updated:
            _invalid_update()

    @contextmanager
    def reserve_admission(
        self,
        *,
        capability: SessionCapability,
        at_utc: datetime,
        queued: bool = False,
    ) -> Iterator[JobRecord]:
        """Reserve admission while callers finish allocation-prone setup.

        The writer transaction is intentionally held across the yielded block. A
        capacity denial therefore occurs before identifier generation, while any
        exception from workspace creation or materialization rolls back the job and
        its operational events.
        """

        try:
            at_utc = require_utc(at_utc, field_name="at_utc")
            if not isinstance(capability, SessionCapability):
                raise JobAdmissionRejectedError
            if not isinstance(queued, bool):
                _invalid_update()
            with self._immediate() as connection:
                rows = connection.execute(
                    """
                    SELECT job_id, owner_digest, execution_state, deadline_at_utc,
                           queue_sequence, version, model_json
                    FROM jobs
                    """
                ).fetchall()
                staged_count = 0
                queued_count = 0
                retained_unsuccessful_count = 0
                owned_count = 0
                for row in rows:
                    existing = self._decode(row)
                    if existing.execution.state is ExecutionState.STAGED:
                        staged_count += 1
                    if existing.execution.state is ExecutionState.QUEUED:
                        queued_count += 1
                    retained_unsuccessful = bool(
                        existing.execution.state is ExecutionState.TERMINAL
                        and existing.outcome is not None
                        and existing.outcome.kind is not TerminalOutcome.SUCCEEDED
                        and any(
                            existing.artifacts.for_kind(kind).state
                            not in {CleanupState.NOT_CREATED, CleanupState.VERIFIED_ABSENT}
                            for kind in ArtifactKind
                        )
                    )
                    if retained_unsuccessful:
                        retained_unsuccessful_count += 1
                    active_for_owner = (
                        existing.execution.state is not ExecutionState.TERMINAL
                        or retained_unsuccessful
                    )
                    if active_for_owner and self._owner_matches(
                        job_id=row["job_id"],
                        stored_digest=row["owner_digest"],
                        capability=capability,
                    ):
                        owned_count += 1
                capacity_reached = (
                    queued_count >= self._policy.max_queued
                    if queued
                    else staged_count >= self._policy.max_staged_global
                )
                if (
                    owned_count >= self._policy.max_active_per_session
                    or capacity_reached
                    or retained_unsuccessful_count >= self._policy.max_staged_global
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
                cleanup_unresolved: JobAdmissionCleanupUnresolvedError | None = None
                try:
                    yield job
                except JobAdmissionCleanupUnresolvedError as error:
                    cleanup_unresolved = error
                self._insert_event(
                    connection,
                    job=job,
                    event_code="JOB_STAGED",
                    at_utc=at_utc,
                )
                if cleanup_unresolved is not None:
                    abandoned = transition_execution(
                        job,
                        target=ExecutionState.TERMINAL,
                        outcome=TerminalOutcome.ABANDONED,
                        at_utc=at_utc,
                        tombstone_expires_at_utc=at_utc
                        + timedelta(seconds=self._policy.tombstone_ttl_seconds),
                        expected_version=job.version,
                        operation_id=_admission_abandonment_operation_id(job),
                    )
                    self._insert_event(
                        connection,
                        job=abandoned,
                        event_code="JOB_UPDATED",
                        at_utc=at_utc,
                    )
                    self._write_job(
                        connection,
                        previous=job,
                        updated=abandoned,
                        queue_sequence=None,
                    )
                elif queued:
                    updated = transition_execution(
                        job,
                        target=ExecutionState.QUEUED,
                        at_utc=at_utc,
                        deadline_at_utc=at_utc + timedelta(seconds=self._policy.queued_ttl_seconds),
                        expected_version=job.version,
                        operation_id=_admission_operation_id(job),
                    )
                    queue_sequence = self._insert_event(
                        connection,
                        job=updated,
                        event_code="JOB_QUEUED",
                        at_utc=at_utc,
                    )
                    self._write_job(
                        connection,
                        previous=job,
                        updated=updated,
                        queue_sequence=queue_sequence,
                    )
            if cleanup_unresolved is not None:
                raise cleanup_unresolved
        except JobStoreError as error:
            rejection = error
        except (OSError, sqlite3.Error):
            rejection = JobStoreError(JobStoreErrorCode.DATABASE_FAILURE)
        else:
            return
        _detach(rejection)
        raise rejection

    @_content_free
    def stage_job(self, *, capability: SessionCapability, at_utc: datetime) -> JobRecord:
        """Atomically admit one staged lease without allocating on rejection."""

        with self.reserve_admission(capability=capability, at_utc=at_utc) as job:
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
    def bind_analysis_admission(
        self,
        *,
        receipt_hmac: str,
        job_id: JobId | str,
        capability: SessionCapability,
        at_utc: datetime,
        expires_at_utc: datetime,
        expected_job_version: int,
    ) -> None:
        """Bind one content-free READY authority to an owned staged job."""

        if not isinstance(receipt_hmac, str) or _RECEIPT_HMAC.fullmatch(receipt_hmac) is None:
            raise JobNotAvailableError
        try:
            at_utc = require_utc(at_utc, field_name="at_utc")
            expires_at_utc = require_utc(expires_at_utc, field_name="expires_at_utc")
        except Exception:
            raise AnalysisAdmissionRejectedError from None
        if (
            isinstance(expected_job_version, bool)
            or not isinstance(expected_job_version, int)
            or expected_job_version < 0
        ):
            raise AnalysisAdmissionRejectedError
        with self._immediate() as connection:
            job, _queue_sequence = self._load_authorized(
                connection,
                job_id=job_id,
                capability=capability,
            )
            deadline = job.execution.deadline_at_utc
            if (
                job.execution.state is not ExecutionState.STAGED
                or job.version != expected_job_version
                or deadline is None
                or at_utc >= expires_at_utc
                or expires_at_utc > deadline
            ):
                raise AnalysisAdmissionRejectedError
            expiry = _timestamp(expires_at_utc)
            existing = connection.execute(
                """
                SELECT receipt_hmac, job_id, owner_digest, expected_job_version,
                       expires_at_utc, consumed_at_utc, version
                FROM analysis_admissions
                WHERE receipt_hmac = ? OR job_id = ?
                """,
                (receipt_hmac, job.job_id),
            ).fetchone()
            if existing is not None:
                if (
                    existing["receipt_hmac"] != receipt_hmac
                    or existing["job_id"] != job.job_id
                    or existing["owner_digest"] != job.owner_digest
                    or existing["expected_job_version"] != expected_job_version
                    or existing["expires_at_utc"] != expiry
                    or existing["version"] != 0
                ):
                    raise AnalysisAdmissionRejectedError
                _parse_timestamp(existing["expires_at_utc"])
                return
            connection.execute(
                """
                INSERT INTO analysis_admissions (
                    receipt_hmac, job_id, owner_digest, expected_job_version,
                    expires_at_utc, consumed_at_utc, version
                ) VALUES (?, ?, ?, ?, ?, NULL, 0)
                """,
                (
                    receipt_hmac,
                    job.job_id,
                    job.owner_digest,
                    expected_job_version,
                    expiry,
                ),
            )

    @_content_free
    def consume_analysis_admission(
        self,
        *,
        receipt_hmac: str,
        job_id: JobId | str,
        capability: SessionCapability,
        at_utc: datetime,
        operation_id: str,
    ) -> JobRecord:
        """Consume one READY authority and enqueue its job in one transaction."""

        if not isinstance(receipt_hmac, str) or _RECEIPT_HMAC.fullmatch(receipt_hmac) is None:
            raise JobNotAvailableError
        try:
            at_utc = require_utc(at_utc, field_name="at_utc")
        except Exception:
            raise AnalysisAdmissionRejectedError from None
        if (
            not isinstance(operation_id, str)
            or _OPERATION_REFERENCE.fullmatch(operation_id) is None
        ):
            raise AnalysisAdmissionRejectedError
        with self._immediate() as connection:
            previous, _queue_sequence = self._load_authorized(
                connection,
                job_id=job_id,
                capability=capability,
            )
            row = connection.execute(
                """
                SELECT receipt_hmac, job_id, owner_digest, expected_job_version,
                       expires_at_utc, consumed_at_utc, version
                FROM analysis_admissions
                WHERE receipt_hmac = ?
                """,
                (receipt_hmac,),
            ).fetchone()
            if (
                row is None
                or row["job_id"] != previous.job_id
                or row["owner_digest"] != previous.owner_digest
            ):
                raise JobNotAvailableError
            if (
                not isinstance(row["expected_job_version"], int)
                or isinstance(row["expected_job_version"], bool)
                or row["expected_job_version"] < 0
                or row["version"] not in {0, 1}
                or (row["consumed_at_utc"] is None) != (row["version"] == 0)
            ):
                raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD)
            expires_at = _parse_timestamp(row["expires_at_utc"])
            if row["consumed_at_utc"] is not None:
                consumed_at = _parse_timestamp(row["consumed_at_utc"])
                if consumed_at >= expires_at:
                    raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD)
                raise AnalysisAdmissionReusedError
            deadline = previous.execution.deadline_at_utc
            if (
                previous.execution.state is not ExecutionState.STAGED
                or previous.version != row["expected_job_version"]
                or deadline is None
                or expires_at > deadline
                or at_utc >= expires_at
                or at_utc >= deadline
            ):
                raise AnalysisAdmissionRejectedError
            count_row = cast(
                sqlite3.Row,
                connection.execute(
                    "SELECT COUNT(*) FROM jobs WHERE execution_state = 'queued'"
                ).fetchone(),
            )
            if int(count_row[0]) >= self._policy.max_queued:
                raise AnalysisAdmissionRejectedError
            try:
                updated = transition_execution(
                    previous,
                    target=ExecutionState.QUEUED,
                    at_utc=at_utc,
                    deadline_at_utc=at_utc + timedelta(seconds=self._policy.queued_ttl_seconds),
                    expected_version=previous.version,
                    operation_id=operation_id,
                )
            except (JobModelError, ValueError):
                raise AnalysisAdmissionRejectedError from None
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
            changed = connection.execute(
                """
                UPDATE analysis_admissions
                SET consumed_at_utc = ?, version = 1
                WHERE receipt_hmac = ? AND consumed_at_utc IS NULL AND version = 0
                """,
                (_timestamp(at_utc), receipt_hmac),
            ).rowcount
            if changed != 1:  # pragma: no cover - protected by BEGIN IMMEDIATE
                raise JobStoreError(JobStoreErrorCode.CORRUPT_RECORD)
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
            while True:
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
                if previous.cancellation.state is not CancellationState.REQUESTED:
                    break
                cancelled = transition_execution(
                    previous,
                    target=ExecutionState.TERMINAL,
                    outcome=TerminalOutcome.CANCELLED,
                    at_utc=at_utc,
                    tombstone_expires_at_utc=at_utc
                    + timedelta(seconds=self._policy.tombstone_ttl_seconds),
                    expected_version=previous.version,
                    operation_id=_queue_cancellation_operation_id(previous),
                )
                self._insert_event(
                    connection,
                    job=cancelled,
                    event_code="JOB_UPDATED",
                    at_utc=at_utc,
                )
                self._write_job(
                    connection,
                    previous=previous,
                    updated=cancelled,
                    queue_sequence=None,
                )
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

    @_content_free
    def terminal_transition_matches(
        self,
        *,
        job_id: JobId | str,
        execution_reference: str,
        expected_version: int,
        expected_outcome: TerminalOutcome,
        expected_result: ScientificResultReceipt | None = None,
    ) -> bool:
        """Verify a durable terminal row before the app releases its guardian."""

        if (
            not isinstance(execution_reference, str)
            or _OPERATION_REFERENCE.fullmatch(execution_reference) is None
            or not isinstance(expected_version, int)
            or expected_version < 0
            or not isinstance(expected_outcome, TerminalOutcome)
            or (
                expected_result is not None
                and not isinstance(expected_result, ScientificResultReceipt)
            )
        ):
            _invalid_update()
        with self._read_connection() as connection:
            job, _queue_sequence = self._load_system(connection, job_id=job_id)
        return bool(
            terminal_operation_version(job) == expected_version
            and job.execution.state is ExecutionState.TERMINAL
            and job.outcome is not None
            and job.outcome.kind is expected_outcome
            and job.scientific_result == expected_result
            and (expected_result is None or job.artifacts.result.state is CleanupState.PRESENT)
            and any(
                operation.operation_id == execution_reference
                and operation.action == "execution:running:none"
                for operation in job.operations
            )
        )

    @_content_free
    def confirm_scientific_result_after_guardian(
        self,
        *,
        job_id: JobId | str,
        expected_terminal_version: int,
        expected_result: ScientificResultReceipt,
        operation_id: str,
        at_utc: datetime,
    ) -> JobRecord:
        """Atomically confirm an exact guardian-accepted scientific result."""

        at_utc = require_utc(at_utc, field_name="at_utc")
        if (
            not isinstance(expected_terminal_version, int)
            or isinstance(expected_terminal_version, bool)
            or expected_terminal_version < 0
            or not isinstance(expected_result, ScientificResultReceipt)
            or not isinstance(operation_id, str)
            or _OPERATION_REFERENCE.fullmatch(operation_id) is None
        ):
            _invalid_update()
        with self._immediate() as connection:
            previous, queue_sequence = self._load_system(connection, job_id=job_id)
            if (
                terminal_operation_version(previous) != expected_terminal_version
                or previous.scientific_result != expected_result
            ):
                _invalid_update()
            if previous.scientific_result_confirmed:
                return previous
            if previous.artifacts.result.state is not CleanupState.PRESENT:
                _invalid_update()
            updated = confirm_scientific_result(
                previous,
                expected_version=previous.version,
                operation_id=operation_id,
            )
            self._validate_successor(previous, updated)
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
                queue_sequence=queue_sequence,
            )
            return updated

    @_content_free
    def list_jobs_for_maintenance(self) -> tuple[JobRecord, ...]:
        """Return payload-free snapshots for the trusted local janitor only."""

        with self._read_connection() as connection:
            rows = connection.execute(
                """
                SELECT job_id, owner_digest, execution_state, deadline_at_utc,
                       queue_sequence, version, model_json
                FROM jobs
                ORDER BY job_id ASC
                """
            ).fetchall()
            return tuple(self._decode(row) for row in rows)

    @_content_free
    def maintenance_compare_and_swap(
        self,
        *,
        job_id: JobId | str,
        expected_version: int,
        updated: JobRecord,
        at_utc: datetime,
        deletion_event: DeletionEvent | None = None,
    ) -> JobRecord:
        """Persist one validated janitor transition without a retained capability."""

        at_utc = require_utc(at_utc, field_name="at_utc")
        if not isinstance(updated, JobRecord) or (
            deletion_event is not None and not isinstance(deletion_event, DeletionEvent)
        ):
            _invalid_update()
        with self._immediate() as connection:
            previous, queue_sequence = self._load_system(connection, job_id=job_id)
            if updated == previous:
                if deletion_event is not None:
                    _invalid_update()
                return previous
            if previous.version != expected_version:
                raise VersionConflictError
            self._validate_successor(previous, updated)
            if deletion_event is not None:
                self._insert_deletion_event(
                    connection,
                    job=previous,
                    event=deletion_event,
                    at_utc=at_utc,
                )
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

    @_content_free
    def list_deletion_events(self) -> tuple[DeletionEvent, ...]:
        """Read the bounded content-free deletion ledger for local evidence."""

        with self._read_connection() as connection:
            rows = connection.execute(
                """
                SELECT event_code, job_reference_digest, occurred_at_utc, reason,
                       file_count, byte_count, policy_version, expires_at_utc
                FROM deletion_events
                ORDER BY sequence ASC
                """
            ).fetchall()
            return tuple(self._decode_deletion_event(row) for row in rows)

    @_content_free
    def record_deletion_event(
        self,
        *,
        job_id: JobId | str,
        event: DeletionEvent,
        at_utc: datetime,
    ) -> bool:
        """Idempotently append a verified deletion fact without changing job state."""

        at_utc = require_utc(at_utc, field_name="at_utc")
        if not isinstance(event, DeletionEvent):
            _invalid_update()
        with self._immediate() as connection:
            job, _queue_sequence = self._load_system(connection, job_id=job_id)
            return self._insert_deletion_event(
                connection,
                job=job,
                event=event,
                at_utc=at_utc,
            )

    @_content_free
    def purge_expired(
        self,
        *,
        at_utc: datetime,
        workspace_absent_job_ids: frozenset[str],
    ) -> StorePurgeReport:
        """Purge expired events and fully cleaned terminal tombstones atomically."""

        at_utc = require_utc(at_utc, field_name="at_utc")
        if not isinstance(workspace_absent_job_ids, frozenset):
            _invalid_update()
        timestamp = _timestamp(at_utc)
        with self._immediate() as connection:
            operational = connection.execute(
                "DELETE FROM events WHERE expires_at_utc <= ?",
                (timestamp,),
            ).rowcount
            deletion = connection.execute(
                "DELETE FROM deletion_events WHERE expires_at_utc <= ?",
                (timestamp,),
            ).rowcount
            rows = connection.execute(
                """
                SELECT job_id, owner_digest, execution_state, deadline_at_utc,
                       queue_sequence, version, model_json
                FROM jobs
                WHERE execution_state = 'terminal'
                ORDER BY job_id ASC
                """
            ).fetchall()
            deletable: list[str] = []
            blocked = 0
            for row in rows:
                job = self._decode(row)
                if job.tombstone_expires_at_utc is None or job.tombstone_expires_at_utc > at_utc:
                    continue
                states = tuple(job.artifacts.for_kind(kind).state for kind in ArtifactKind)
                if (
                    job.job_id not in workspace_absent_job_ids
                    or job.export_available
                    or any(
                        state not in {CleanupState.NOT_CREATED, CleanupState.VERIFIED_ABSENT}
                        for state in states
                    )
                ):
                    blocked += 1
                    continue
                deletable.append(job.job_id)
            tombstones = 0
            for identifier in deletable:
                tombstones += connection.execute(
                    "DELETE FROM jobs WHERE job_id = ?",
                    (identifier,),
                ).rowcount
            return StorePurgeReport(
                operational_events_deleted=operational,
                deletion_events_deleted=deletion,
                tombstones_deleted=tombstones,
                tombstones_blocked=blocked,
            )


__all__ = [
    "AnalysisAdmissionRejectedError",
    "AnalysisAdmissionReusedError",
    "JobAdmissionCleanupUnresolvedError",
    "JobAdmissionRejectedError",
    "JobIdFactory",
    "JobNotAvailableError",
    "JobStoreError",
    "JobStoreErrorCode",
    "SQLiteJobStore",
    "StorePurgeReport",
]
