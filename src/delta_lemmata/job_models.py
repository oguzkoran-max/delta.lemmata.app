"""Immutable, content-free job lifecycle models and transition helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from delta_lemmata.clock import require_utc

JobIdText = Annotated[
    str,
    Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]{43}$"),
]
OwnerDigest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
OperationId = Annotated[str, Field(pattern=r"^op_[0-9a-f]{64}$")]


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ExecutionState(StrEnum):
    STAGED = "staged"
    QUEUED = "queued"
    RUNNING = "running"
    TERMINAL = "terminal"


class TerminalOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    CRASHED = "crashed"
    ABANDONED = "abandoned"
    EXPIRED = "expired"


class CancellationState(StrEnum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"


class ArtifactKind(StrEnum):
    INPUT = "input"
    WORK = "work"
    RESULT = "result"
    EXPORT = "export"


class CleanupState(StrEnum):
    NOT_CREATED = "not_created"
    PRESENT = "present"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED_ABSENT = "verified_absent"
    FAILED = "failed"


class JobModelError(ValueError):
    """Content-free lifecycle rejection with a stable code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class VersionConflictError(JobModelError):
    def __init__(self) -> None:
        super().__init__("JOB_VERSION_CONFLICT")


class IllegalTransitionError(JobModelError):
    def __init__(self) -> None:
        super().__init__("JOB_ILLEGAL_TRANSITION")


class OperationConflictError(JobModelError):
    def __init__(self) -> None:
        super().__init__("JOB_OPERATION_CONFLICT")


class ExecutionStatus(FrozenModel):
    state: ExecutionState
    entered_at_utc: datetime
    deadline_at_utc: datetime | None = None

    @field_validator("entered_at_utc", "deadline_at_utc")
    @classmethod
    def require_utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return require_utc(value)

    @model_validator(mode="after")
    def require_state_deadline(self) -> Self:
        if self.state in {ExecutionState.STAGED, ExecutionState.QUEUED}:
            if self.deadline_at_utc is None or self.deadline_at_utc <= self.entered_at_utc:
                raise ValueError("staged and queued states require a future absolute deadline")
        elif self.deadline_at_utc is not None:
            raise ValueError("running and terminal states do not carry a queue deadline")
        return self


class Outcome(FrozenModel):
    kind: TerminalOutcome
    occurred_at_utc: datetime

    @field_validator("occurred_at_utc")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        return require_utc(value)


class Cancellation(FrozenModel):
    state: CancellationState = CancellationState.NOT_REQUESTED
    requested_at_utc: datetime | None = None

    @field_validator("requested_at_utc")
    @classmethod
    def require_utc_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return require_utc(value)

    @model_validator(mode="after")
    def require_request_time(self) -> Self:
        if (self.state is CancellationState.REQUESTED) != (self.requested_at_utc is not None):
            raise ValueError("cancellation request state and timestamp must agree")
        return self


class ArtifactStatus(FrozenModel):
    state: CleanupState
    delete_by_utc: datetime | None = None
    verified_at_utc: datetime | None = None

    @field_validator("delete_by_utc", "verified_at_utc")
    @classmethod
    def require_utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return require_utc(value)

    @model_validator(mode="after")
    def require_consistent_timestamps(self) -> Self:
        absent = self.state in {CleanupState.NOT_CREATED, CleanupState.VERIFIED_ABSENT}
        if self.state is CleanupState.VERIFIED_ABSENT and self.verified_at_utc is None:
            raise ValueError("verified absence requires a verification timestamp")
        if self.state is not CleanupState.VERIFIED_ABSENT and self.verified_at_utc is not None:
            raise ValueError("only verified absence can carry a verification timestamp")
        if absent and self.delete_by_utc is not None:
            raise ValueError("absent artifacts cannot carry a deletion deadline")
        if not absent and self.delete_by_utc is None:
            raise ValueError("retained artifacts require an absolute deletion deadline")
        return self


class ArtifactLifecycle(FrozenModel):
    input: ArtifactStatus
    work: ArtifactStatus
    result: ArtifactStatus
    export: ArtifactStatus

    def for_kind(self, kind: ArtifactKind) -> ArtifactStatus:
        return {
            ArtifactKind.INPUT: self.input,
            ArtifactKind.WORK: self.work,
            ArtifactKind.RESULT: self.result,
            ArtifactKind.EXPORT: self.export,
        }[kind]


class AppliedOperation(FrozenModel):
    operation_id: OperationId
    action: str = Field(pattern=r"^[a-z][a-z0-9_:]*$")


class JobRecord(FrozenModel):
    job_id: JobIdText
    owner_digest: OwnerDigest
    policy_version: str = Field(pattern=r"^job-policy-v[0-9]+$")
    execution: ExecutionStatus
    outcome: Outcome | None = None
    cancellation: Cancellation = Cancellation()
    artifacts: ArtifactLifecycle
    export_available: bool = False
    event_expires_at_utc: datetime
    tombstone_expires_at_utc: datetime | None = None
    version: int = Field(ge=0)
    operations: tuple[AppliedOperation, ...] = ()

    @field_validator("event_expires_at_utc", "tombstone_expires_at_utc")
    @classmethod
    def require_utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return require_utc(value)

    @field_validator("operations")
    @classmethod
    def require_unique_operations(
        cls, value: tuple[AppliedOperation, ...]
    ) -> tuple[AppliedOperation, ...]:
        if len({operation.operation_id for operation in value}) != len(value):
            raise ValueError("operation identifiers must be unique")
        return value

    @model_validator(mode="after")
    def require_consistent_terminal_and_export_state(self) -> Self:
        terminal = self.execution.state is ExecutionState.TERMINAL
        if terminal != (self.outcome is not None):
            raise ValueError("terminal execution state and outcome must agree")
        if terminal != (self.tombstone_expires_at_utc is not None):
            raise ValueError("terminal execution state and tombstone deadline must agree")
        if self.event_expires_at_utc <= self.execution.entered_at_utc:
            raise ValueError("event expiry must follow the current execution timestamp")
        if (
            self.outcome is not None
            and self.tombstone_expires_at_utc is not None
            and self.tombstone_expires_at_utc <= self.outcome.occurred_at_utc
        ):
            raise ValueError("tombstone expiry must follow the terminal outcome")
        if (
            self.outcome is not None
            and self.outcome.kind is TerminalOutcome.CANCELLED
            and self.cancellation.state is not CancellationState.REQUESTED
        ):
            raise ValueError("cancelled outcome requires a cancellation request")
        if self.export_available and not self.can_publish_export:
            raise ValueError("export cannot be available before successful verified cleanup")
        return self

    @property
    def can_publish_export(self) -> bool:
        return (
            self.outcome is not None
            and self.outcome.kind is TerminalOutcome.SUCCEEDED
            and self.artifacts.input.state is CleanupState.VERIFIED_ABSENT
            and self.artifacts.work.state is CleanupState.VERIFIED_ABSENT
            and self.artifacts.export.state is CleanupState.PRESENT
        )


_LEGAL_EXECUTION_TRANSITIONS = {
    ExecutionState.STAGED: frozenset({ExecutionState.QUEUED, ExecutionState.TERMINAL}),
    ExecutionState.QUEUED: frozenset({ExecutionState.RUNNING, ExecutionState.TERMINAL}),
    ExecutionState.RUNNING: frozenset({ExecutionState.TERMINAL}),
    ExecutionState.TERMINAL: frozenset(),
}

_LEGAL_OUTCOMES = {
    ExecutionState.STAGED: frozenset({TerminalOutcome.ABANDONED, TerminalOutcome.EXPIRED}),
    ExecutionState.QUEUED: frozenset(
        {TerminalOutcome.CANCELLED, TerminalOutcome.ABANDONED, TerminalOutcome.EXPIRED}
    ),
    ExecutionState.RUNNING: frozenset(
        {
            TerminalOutcome.SUCCEEDED,
            TerminalOutcome.FAILED,
            TerminalOutcome.CANCELLED,
            TerminalOutcome.TIMED_OUT,
            TerminalOutcome.CRASHED,
            TerminalOutcome.ABANDONED,
        }
    ),
    ExecutionState.TERMINAL: frozenset(),
}

_LEGAL_CLEANUP_TRANSITIONS = {
    CleanupState.NOT_CREATED: frozenset({CleanupState.PRESENT, CleanupState.VERIFIED_ABSENT}),
    CleanupState.PRESENT: frozenset(
        {CleanupState.PENDING, CleanupState.IN_PROGRESS, CleanupState.VERIFIED_ABSENT}
    ),
    CleanupState.PENDING: frozenset({CleanupState.IN_PROGRESS}),
    CleanupState.IN_PROGRESS: frozenset({CleanupState.VERIFIED_ABSENT, CleanupState.FAILED}),
    CleanupState.FAILED: frozenset({CleanupState.PENDING, CleanupState.IN_PROGRESS}),
    CleanupState.VERIFIED_ABSENT: frozenset(),
}


def _check_operation(job: JobRecord, operation_id: str, action: str) -> bool:
    for operation in job.operations:
        if operation.operation_id == operation_id:
            if operation.action == action:
                return True
            raise OperationConflictError
    return False


def _check_version(job: JobRecord, expected_version: int) -> None:
    if job.version != expected_version:
        raise VersionConflictError


def _updated(
    job: JobRecord,
    *,
    operation_id: str,
    action: str,
    updates: dict[str, object],
) -> JobRecord:
    operation = AppliedOperation(operation_id=operation_id, action=action)
    payload = job.model_dump(mode="python")
    payload.update(updates)
    payload["version"] = job.version + 1
    payload["operations"] = (*job.operations, operation)
    return JobRecord.model_validate(payload)


def transition_execution(
    job: JobRecord,
    *,
    target: ExecutionState,
    at_utc: datetime,
    expected_version: int,
    operation_id: str,
    deadline_at_utc: datetime | None = None,
    outcome: TerminalOutcome | None = None,
    tombstone_expires_at_utc: datetime | None = None,
) -> JobRecord:
    """Apply one legal execution transition with CAS and retry idempotency."""

    action = f"execution:{target.value}:{outcome.value if outcome is not None else 'none'}"
    if _check_operation(job, operation_id, action):
        return job
    _check_version(job, expected_version)
    at_utc = require_utc(at_utc, field_name="at_utc")
    if at_utc < job.execution.entered_at_utc:
        raise IllegalTransitionError
    source = job.execution.state
    if target not in _LEGAL_EXECUTION_TRANSITIONS[source]:
        raise IllegalTransitionError
    if target is ExecutionState.TERMINAL:
        if outcome not in _LEGAL_OUTCOMES[source] or tombstone_expires_at_utc is None:
            raise IllegalTransitionError
        if (
            outcome is TerminalOutcome.CANCELLED
            and job.cancellation.state is not CancellationState.REQUESTED
        ):
            raise IllegalTransitionError
        tombstone_expires_at_utc = require_utc(
            tombstone_expires_at_utc, field_name="tombstone_expires_at_utc"
        )
        if tombstone_expires_at_utc <= at_utc or deadline_at_utc is not None:
            raise IllegalTransitionError
        next_outcome = Outcome(kind=outcome, occurred_at_utc=at_utc)
    else:
        if outcome is not None or tombstone_expires_at_utc is not None:
            raise IllegalTransitionError
        next_outcome = None
    try:
        execution = ExecutionStatus(
            state=target,
            entered_at_utc=at_utc,
            deadline_at_utc=deadline_at_utc,
        )
    except ValueError as error:
        raise IllegalTransitionError from error
    return _updated(
        job,
        operation_id=operation_id,
        action=action,
        updates={
            "execution": execution,
            "outcome": next_outcome,
            "tombstone_expires_at_utc": tombstone_expires_at_utc,
        },
    )


def request_cancellation(
    job: JobRecord,
    *,
    at_utc: datetime,
    expected_version: int,
    operation_id: str,
) -> JobRecord:
    """Record a cancellation request without inventing a terminal outcome."""

    action = "cancellation:requested"
    if _check_operation(job, operation_id, action):
        return job
    _check_version(job, expected_version)
    at_utc = require_utc(at_utc, field_name="at_utc")
    if (
        job.execution.state not in {ExecutionState.QUEUED, ExecutionState.RUNNING}
        or at_utc < job.execution.entered_at_utc
    ):
        raise IllegalTransitionError
    if job.cancellation.state is CancellationState.REQUESTED:
        raise IllegalTransitionError
    return _updated(
        job,
        operation_id=operation_id,
        action=action,
        updates={
            "cancellation": Cancellation(
                state=CancellationState.REQUESTED,
                requested_at_utc=at_utc,
            )
        },
    )


def transition_artifact(
    job: JobRecord,
    *,
    kind: ArtifactKind,
    target: CleanupState,
    at_utc: datetime,
    expected_version: int,
    operation_id: str,
    delete_by_utc: datetime | None = None,
) -> JobRecord:
    """Move one artifact cleanup state without changing execution outcome."""

    action = f"artifact:{kind.value}:{target.value}"
    if _check_operation(job, operation_id, action):
        return job
    _check_version(job, expected_version)
    current = job.artifacts.for_kind(kind)
    if target not in _LEGAL_CLEANUP_TRANSITIONS[current.state]:
        raise IllegalTransitionError
    at_utc = require_utc(at_utc, field_name="at_utc")
    if at_utc < job.execution.entered_at_utc:
        raise IllegalTransitionError
    if delete_by_utc is not None:
        delete_by_utc = require_utc(delete_by_utc, field_name="delete_by_utc")
        if delete_by_utc <= at_utc:
            raise IllegalTransitionError
        if current.delete_by_utc is not None and delete_by_utc > current.delete_by_utc:
            raise IllegalTransitionError
    verified_at = at_utc if target is CleanupState.VERIFIED_ABSENT else None
    try:
        artifact = ArtifactStatus(
            state=target,
            delete_by_utc=delete_by_utc,
            verified_at_utc=verified_at,
        )
    except ValueError as error:
        raise IllegalTransitionError from error
    artifact_payload = job.artifacts.model_dump(mode="python")
    artifact_payload[kind.value] = artifact
    artifacts = ArtifactLifecycle.model_validate(artifact_payload)
    return _updated(
        job,
        operation_id=operation_id,
        action=action,
        updates={"artifacts": artifacts},
    )


def publish_export(
    job: JobRecord,
    *,
    expected_version: int,
    operation_id: str,
) -> JobRecord:
    """Expose a success export only after input and work cleanup are verified."""

    action = "export:publish"
    if _check_operation(job, operation_id, action):
        return job
    _check_version(job, expected_version)
    if job.export_available or not job.can_publish_export:
        raise IllegalTransitionError
    return _updated(
        job,
        operation_id=operation_id,
        action=action,
        updates={"export_available": True},
    )


def new_staged_job(
    *,
    job_id: str,
    owner_digest: str,
    policy_version: str,
    at_utc: datetime,
    staged_ttl_seconds: int,
    event_ttl_seconds: int,
) -> JobRecord:
    """Construct the initial staged snapshot from explicit versioned durations."""

    at_utc = require_utc(at_utc, field_name="at_utc")
    if staged_ttl_seconds <= 0 or event_ttl_seconds <= 0:
        raise ValueError("retention durations must be positive")
    staged_deadline = at_utc + timedelta(seconds=staged_ttl_seconds)
    absent = ArtifactStatus(state=CleanupState.NOT_CREATED)
    return JobRecord(
        job_id=job_id,
        owner_digest=owner_digest,
        policy_version=policy_version,
        execution=ExecutionStatus(
            state=ExecutionState.STAGED,
            entered_at_utc=at_utc,
            deadline_at_utc=staged_deadline,
        ),
        artifacts=ArtifactLifecycle(
            input=ArtifactStatus(
                state=CleanupState.PRESENT,
                delete_by_utc=staged_deadline,
            ),
            work=absent,
            result=absent,
            export=absent,
        ),
        event_expires_at_utc=at_utc + timedelta(seconds=event_ttl_seconds),
        version=0,
    )


__all__ = [
    "AppliedOperation",
    "ArtifactKind",
    "ArtifactLifecycle",
    "ArtifactStatus",
    "Cancellation",
    "CancellationState",
    "CleanupState",
    "ExecutionState",
    "ExecutionStatus",
    "IllegalTransitionError",
    "JobModelError",
    "JobRecord",
    "OperationConflictError",
    "Outcome",
    "TerminalOutcome",
    "VersionConflictError",
    "new_staged_job",
    "publish_export",
    "request_cancellation",
    "transition_artifact",
    "transition_execution",
]
