"""Immutable, content-free job lifecycle models and transition helpers."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from delta_lemmata.clock import require_utc
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY

JobIdText = Annotated[
    str,
    Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]{43}$"),
]
OwnerDigest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
OperationId = Annotated[str, Field(pattern=r"^op_[0-9a-f]{64}$")]
Sha256Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ScientificRequestId = Annotated[str, Field(pattern=r"^request_[0-9a-f]{64}$")]


class FrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        hide_input_in_errors=True,
    )


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


class ScientificResultReceipt(FrozenModel):
    """Content-free commitment to one validated P006 result artifact."""

    schema_version: Literal["scientific-result-receipt-v1"]
    request_id: ScientificRequestId
    request_sha256: Sha256Digest
    worker_version: Literal["stylo-worker-v1"]
    result_schema_version: Literal["stylo-worker-result-v1"]
    analysis_outcome: Literal["complete", "partial"]
    artifact_component: Literal["053bf21e22c557bd2e9cc53b858b02603c19200680fe1cc2d885bd1b11d6987b"]
    byte_size: int = Field(strict=True, ge=1, le=32 * 1024 * 1024)
    sha256: Sha256Digest


class ResultViewReceipt(FrozenModel):
    """Content-free commitment to one bounded P009 public result view."""

    schema_version: Literal["result-view-receipt-v1"]
    source_result_sha256: Sha256Digest
    workflow_config_sha256: Sha256Digest
    view_schema_version: Literal["result-view-v1"]
    artifact_component: Literal["5a6b1a66f34ffa5cb516349bc4f2fe62083a8c4803fa23b2793f57a5ece0621a"]
    byte_size: int = Field(strict=True, ge=1, le=4 * 1024 * 1024)
    sha256: Sha256Digest


def _scientific_result_commitment(receipt: ScientificResultReceipt) -> str:
    fields = (
        receipt.schema_version,
        receipt.request_id,
        receipt.request_sha256,
        receipt.worker_version,
        receipt.result_schema_version,
        receipt.analysis_outcome,
        receipt.artifact_component,
        str(receipt.byte_size),
        receipt.sha256,
    )
    return hashlib.sha256("\0".join(fields).encode("ascii")).hexdigest()


def _scientific_result_action(receipt: ScientificResultReceipt) -> str:
    return f"scientific:terminal:succeeded:{_scientific_result_commitment(receipt)}"


def _scientific_confirmation_action(receipt: ScientificResultReceipt) -> str:
    return f"scientific:guardian:confirmed:{_scientific_result_commitment(receipt)}"


def _result_view_commitment(receipt: ResultViewReceipt) -> str:
    fields = (
        receipt.schema_version,
        receipt.source_result_sha256,
        receipt.workflow_config_sha256,
        receipt.view_schema_version,
        receipt.artifact_component,
        str(receipt.byte_size),
        receipt.sha256,
    )
    return hashlib.sha256("\0".join(fields).encode("ascii")).hexdigest()


def _result_view_action(receipt: ResultViewReceipt) -> str:
    return f"result_view:staged:{_result_view_commitment(receipt)}"


class JobRecord(FrozenModel):
    job_id: JobIdText
    owner_digest: OwnerDigest
    policy_version: str = Field(pattern=r"^job-policy-v[0-9]+$")
    execution: ExecutionStatus
    outcome: Outcome | None = None
    cancellation: Cancellation = Cancellation()
    artifacts: ArtifactLifecycle
    scientific_result: ScientificResultReceipt | None = None
    scientific_result_confirmed: bool = Field(default=False, strict=True)
    result_view: ResultViewReceipt | None = None
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
        policy = DEFAULT_JOB_POLICY
        if self.policy_version != policy.profile_version:
            raise ValueError("unsupported job policy version")
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
        scientific_claims = tuple(
            operation.action
            for operation in self.operations
            if operation.action == "scientific:execution:claimed"
        )
        running_operations = tuple(
            operation.action
            for operation in self.operations
            if operation.action == "execution:running:none"
        )
        if scientific_claims and (
            scientific_claims != ("scientific:execution:claimed",)
            or running_operations != ("execution:running:none",)
            or self.execution.state not in {ExecutionState.RUNNING, ExecutionState.TERMINAL}
        ):
            raise ValueError("scientific execution claim requires one running execution")
        if (
            scientific_claims
            and self.outcome is not None
            and self.outcome.kind is TerminalOutcome.SUCCEEDED
            and self.scientific_result is None
        ):
            raise ValueError("scientific execution cannot succeed without a result receipt")
        confirmation_actions = tuple(
            operation.action
            for operation in self.operations
            if operation.action.startswith("scientific:guardian:confirmed:")
        )
        if self.scientific_result is not None:
            scientific_actions = tuple(
                operation.action
                for operation in self.operations
                if operation.action.startswith("scientific:terminal:succeeded:")
            )
            if (
                self.outcome is None
                or self.outcome.kind is not TerminalOutcome.SUCCEEDED
                or self.execution.state is not ExecutionState.TERMINAL
                or self.artifacts.result.state is CleanupState.NOT_CREATED
                or scientific_claims != ("scientific:execution:claimed",)
                or scientific_actions != (_scientific_result_action(self.scientific_result),)
            ):
                raise ValueError(
                    "scientific result requires a committed successful scientific transition"
                )
            expected_confirmation = _scientific_confirmation_action(self.scientific_result)
            if self.scientific_result_confirmed:
                if confirmation_actions != (expected_confirmation,):
                    raise ValueError(
                        "confirmed scientific result requires its exact guardian commitment"
                    )
            elif confirmation_actions:
                raise ValueError("guardian confirmation requires a confirmed scientific result")
        elif any(
            operation.action.startswith("scientific:terminal:succeeded:")
            for operation in self.operations
        ):
            raise ValueError("scientific transition requires a result receipt")
        elif self.scientific_result_confirmed or confirmation_actions:
            raise ValueError("scientific confirmation requires a result receipt")
        result_view_actions = tuple(
            operation.action
            for operation in self.operations
            if operation.action.startswith("result_view:staged:")
        )
        if self.result_view is not None:
            if (
                self.scientific_result is None
                or not self.scientific_result_confirmed
                or self.result_view.source_result_sha256 != self.scientific_result.sha256
                or result_view_actions != (_result_view_action(self.result_view),)
                or self.outcome is None
                or self.outcome.kind is not TerminalOutcome.SUCCEEDED
            ):
                raise ValueError("result view requires one confirmed scientific source")
        elif result_view_actions:
            raise ValueError("result view transition requires a result view receipt")
        execution_deadline_cap = {
            ExecutionState.STAGED: self.execution.entered_at_utc
            + timedelta(seconds=policy.staged_ttl_seconds),
            ExecutionState.QUEUED: self.execution.entered_at_utc
            + timedelta(seconds=policy.queued_ttl_seconds),
        }.get(self.execution.state)
        if (
            execution_deadline_cap is not None
            and self.execution.deadline_at_utc is not None
            and self.execution.deadline_at_utc > execution_deadline_cap
        ):
            raise ValueError("execution deadline exceeds the job policy")
        if self.event_expires_at_utc > self.execution.entered_at_utc + timedelta(
            seconds=policy.event_ttl_seconds
        ):
            raise ValueError("event deadline exceeds the job policy")
        if (
            self.outcome is not None
            and self.tombstone_expires_at_utc is not None
            and self.tombstone_expires_at_utc
            > self.outcome.occurred_at_utc + timedelta(seconds=policy.tombstone_ttl_seconds)
        ):
            raise ValueError("tombstone deadline exceeds the job policy")
        for kind in ArtifactKind:
            artifact = self.artifacts.for_kind(kind)
            if artifact.delete_by_utc is None:
                continue
            if artifact.delete_by_utc > _artifact_deadline_cap(self, kind):
                raise ValueError("artifact deadline exceeds the job policy")
        return self

    @property
    def can_publish_export(self) -> bool:
        return (
            self.outcome is not None
            and self.outcome.kind is TerminalOutcome.SUCCEEDED
            and self.artifacts.input.state is CleanupState.VERIFIED_ABSENT
            and self.artifacts.work.state is CleanupState.VERIFIED_ABSENT
            and self.artifacts.export.state is CleanupState.PRESENT
            and (
                self.scientific_result is None
                or (self.scientific_result_confirmed and self.result_view is not None)
            )
        )


def terminal_operation_version(job: JobRecord) -> int | None:
    """Return the immutable operation version that committed a terminal outcome."""

    if job.execution.state is not ExecutionState.TERMINAL or job.outcome is None:
        return None
    expected_action = (
        _scientific_result_action(job.scientific_result)
        if job.scientific_result is not None
        else f"execution:terminal:{job.outcome.kind.value}"
    )
    versions = tuple(
        index
        for index, operation in enumerate(job.operations, start=1)
        if operation.action == expected_action
    )
    return versions[0] if len(versions) == 1 else None


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


def _artifact_deadline_cap(job: JobRecord, kind: ArtifactKind) -> datetime:
    policy = DEFAULT_JOB_POLICY
    state = job.execution.state
    if state is ExecutionState.STAGED:
        return job.execution.entered_at_utc + timedelta(seconds=policy.staged_ttl_seconds)
    if state is ExecutionState.QUEUED:
        return cast(datetime, job.execution.deadline_at_utc)
    if state is ExecutionState.RUNNING:
        return job.execution.entered_at_utc + timedelta(
            seconds=(
                policy.worker_limits.wall_time_seconds + policy.unsuccessful_payload_ttl_seconds
            )
        )
    outcome = cast(Outcome, job.outcome)
    seconds: int
    if outcome.kind is TerminalOutcome.SUCCEEDED:
        if kind is ArtifactKind.RESULT:
            seconds = policy.result_ttl_seconds
        elif kind is ArtifactKind.EXPORT:
            seconds = policy.export_ttl_seconds
        else:
            seconds = policy.unsuccessful_payload_ttl_seconds
    else:
        seconds = policy.unsuccessful_payload_ttl_seconds
    return outcome.occurred_at_utc + timedelta(seconds=seconds)


def _retime_artifacts(
    artifacts: ArtifactLifecycle,
    caps: dict[ArtifactKind, datetime],
) -> ArtifactLifecycle:
    payload = artifacts.model_dump(mode="python")
    for kind, cap in caps.items():
        current = artifacts.for_kind(kind)
        if current.delete_by_utc is None or current.delete_by_utc <= cap:
            continue
        payload[kind.value] = ArtifactStatus(
            state=current.state,
            delete_by_utc=cap,
            verified_at_utc=current.verified_at_utc,
        )
    return ArtifactLifecycle.model_validate(payload)


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
        if outcome is TerminalOutcome.SUCCEEDED and any(
            operation.action == "scientific:execution:claimed" for operation in job.operations
        ):
            raise IllegalTransitionError
        if (
            outcome is TerminalOutcome.CANCELLED
            and job.cancellation.state is not CancellationState.REQUESTED
        ):
            raise IllegalTransitionError
        tombstone_expires_at_utc = require_utc(
            tombstone_expires_at_utc, field_name="tombstone_expires_at_utc"
        )
        if (
            tombstone_expires_at_utc <= at_utc
            or tombstone_expires_at_utc
            > at_utc + timedelta(seconds=DEFAULT_JOB_POLICY.tombstone_ttl_seconds)
            or deadline_at_utc is not None
        ):
            raise IllegalTransitionError
        next_outcome = Outcome(kind=outcome, occurred_at_utc=at_utc)
    else:
        if outcome is not None or tombstone_expires_at_utc is not None:
            raise IllegalTransitionError
        if deadline_at_utc is not None:
            try:
                deadline_at_utc = require_utc(deadline_at_utc, field_name="deadline_at_utc")
            except ValueError as error:
                raise IllegalTransitionError from error
        if (
            target is ExecutionState.QUEUED
            and deadline_at_utc is not None
            and deadline_at_utc > at_utc + timedelta(seconds=DEFAULT_JOB_POLICY.queued_ttl_seconds)
        ):
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
    artifact_cap_anchor = job.model_copy(
        update={
            "execution": execution,
            "outcome": next_outcome,
            "tombstone_expires_at_utc": tombstone_expires_at_utc,
        }
    )
    if target is ExecutionState.QUEUED:
        queue_deadline = cast(datetime, deadline_at_utc)
        caps = {kind: queue_deadline for kind in ArtifactKind}
    else:
        caps = {kind: _artifact_deadline_cap(artifact_cap_anchor, kind) for kind in ArtifactKind}
    artifacts = _retime_artifacts(job.artifacts, caps)
    return _updated(
        job,
        operation_id=operation_id,
        action=action,
        updates={
            "execution": execution,
            "outcome": next_outcome,
            "tombstone_expires_at_utc": tombstone_expires_at_utc,
            "artifacts": artifacts,
        },
    )


def transition_scientific_success(
    job: JobRecord,
    *,
    receipt: ScientificResultReceipt,
    at_utc: datetime,
    tombstone_expires_at_utc: datetime,
    expected_version: int,
    operation_id: str,
) -> JobRecord:
    """Atomically bind one accepted result to its successful terminal state."""

    if not isinstance(receipt, ScientificResultReceipt):
        raise IllegalTransitionError
    action = _scientific_result_action(receipt)
    if _check_operation(job, operation_id, action):
        return job
    _check_version(job, expected_version)
    at_utc = require_utc(at_utc, field_name="at_utc")
    tombstone_expires_at_utc = require_utc(
        tombstone_expires_at_utc,
        field_name="tombstone_expires_at_utc",
    )
    if (
        job.execution.state is not ExecutionState.RUNNING
        or tuple(
            operation.action
            for operation in job.operations
            if operation.action == "scientific:execution:claimed"
        )
        != ("scientific:execution:claimed",)
        or job.scientific_result is not None
        or job.artifacts.result.state is not CleanupState.NOT_CREATED
        or at_utc < job.execution.entered_at_utc
        or tombstone_expires_at_utc <= at_utc
        or tombstone_expires_at_utc
        > at_utc + timedelta(seconds=DEFAULT_JOB_POLICY.tombstone_ttl_seconds)
    ):
        raise IllegalTransitionError
    execution = ExecutionStatus(
        state=ExecutionState.TERMINAL,
        entered_at_utc=at_utc,
    )
    outcome = Outcome(kind=TerminalOutcome.SUCCEEDED, occurred_at_utc=at_utc)
    anchor = job.model_copy(
        update={
            "execution": execution,
            "outcome": outcome,
            "tombstone_expires_at_utc": tombstone_expires_at_utc,
        }
    )
    caps = {kind: _artifact_deadline_cap(anchor, kind) for kind in ArtifactKind}
    artifacts = _retime_artifacts(job.artifacts, caps)
    artifact_payload = artifacts.model_dump(mode="python")
    artifact_payload[ArtifactKind.RESULT.value] = ArtifactStatus(
        state=CleanupState.PRESENT,
        delete_by_utc=caps[ArtifactKind.RESULT],
    )
    return _updated(
        job,
        operation_id=operation_id,
        action=action,
        updates={
            "execution": execution,
            "outcome": outcome,
            "tombstone_expires_at_utc": tombstone_expires_at_utc,
            "artifacts": ArtifactLifecycle.model_validate(artifact_payload),
            "scientific_result": receipt,
        },
    )


def transition_scientific_execution_claim(
    job: JobRecord,
    *,
    expected_version: int,
    operation_id: str,
) -> JobRecord:
    """Claim one running row before any scientific filesystem side effect."""

    action = "scientific:execution:claimed"
    if _check_operation(job, operation_id, action):
        return job
    _check_version(job, expected_version)
    if (
        job.execution.state is not ExecutionState.RUNNING
        or job.scientific_result is not None
        or job.scientific_result_confirmed
        or job.artifacts.result.state is not CleanupState.NOT_CREATED
        or any(operation.action == action for operation in job.operations)
    ):
        raise IllegalTransitionError
    return _updated(
        job,
        operation_id=operation_id,
        action=action,
        updates={},
    )


def confirm_scientific_result(
    job: JobRecord,
    *,
    expected_version: int,
    operation_id: str,
) -> JobRecord:
    """Persist guardian acceptance for one exact pending scientific result."""

    receipt = job.scientific_result
    if receipt is None:
        raise IllegalTransitionError
    action = _scientific_confirmation_action(receipt)
    if _check_operation(job, operation_id, action):
        return job
    _check_version(job, expected_version)
    if (
        job.execution.state is not ExecutionState.TERMINAL
        or job.outcome is None
        or job.outcome.kind is not TerminalOutcome.SUCCEEDED
        or job.scientific_result_confirmed
        or job.artifacts.result.state is not CleanupState.PRESENT
    ):
        raise IllegalTransitionError
    return _updated(
        job,
        operation_id=operation_id,
        action=action,
        updates={"scientific_result_confirmed": True},
    )


def commit_result_view(
    job: JobRecord,
    *,
    receipt: ResultViewReceipt,
    at_utc: datetime,
    expected_version: int,
    operation_id: str,
) -> JobRecord:
    """Atomically bind one public view receipt and its export lifecycle."""

    if not isinstance(receipt, ResultViewReceipt):
        raise IllegalTransitionError
    action = _result_view_action(receipt)
    if _check_operation(job, operation_id, action):
        return job
    _check_version(job, expected_version)
    at_utc = require_utc(at_utc, field_name="at_utc")
    export_deadline = _artifact_deadline_cap(job, ArtifactKind.EXPORT)
    if (
        job.execution.state is not ExecutionState.TERMINAL
        or job.outcome is None
        or job.outcome.kind is not TerminalOutcome.SUCCEEDED
        or job.scientific_result is None
        or not job.scientific_result_confirmed
        or receipt.source_result_sha256 != job.scientific_result.sha256
        or job.result_view is not None
        or job.export_available
        or job.artifacts.result.state is not CleanupState.PRESENT
        or job.artifacts.export.state is not CleanupState.NOT_CREATED
        or at_utc < job.execution.entered_at_utc
        or at_utc >= export_deadline
    ):
        raise IllegalTransitionError
    artifact_payload = job.artifacts.model_dump(mode="python")
    artifact_payload[ArtifactKind.EXPORT.value] = ArtifactStatus(
        state=CleanupState.PRESENT,
        delete_by_utc=export_deadline,
    )
    return _updated(
        job,
        operation_id=operation_id,
        action=action,
        updates={
            "artifacts": ArtifactLifecycle.model_validate(artifact_payload),
            "result_view": receipt,
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
        if delete_by_utc <= at_utc and delete_by_utc != current.delete_by_utc:
            raise IllegalTransitionError
        if current.delete_by_utc is not None and delete_by_utc > current.delete_by_utc:
            raise IllegalTransitionError
        if delete_by_utc > _artifact_deadline_cap(job, kind):
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


def retire_export(
    job: JobRecord,
    *,
    at_utc: datetime,
    expected_version: int,
    operation_id: str,
) -> JobRecord:
    """Expire one published export while preserving the successful outcome."""

    action = "export:retire"
    if _check_operation(job, operation_id, action):
        return job
    _check_version(job, expected_version)
    at_utc = require_utc(at_utc, field_name="at_utc")
    current = job.artifacts.export
    if (
        not job.export_available
        or current.state is not CleanupState.PRESENT
        or current.delete_by_utc is None
        or at_utc < current.delete_by_utc
    ):
        raise IllegalTransitionError
    artifact_payload = job.artifacts.model_dump(mode="python")
    artifact_payload[ArtifactKind.EXPORT.value] = ArtifactStatus(
        state=CleanupState.VERIFIED_ABSENT,
        verified_at_utc=at_utc,
    )
    return _updated(
        job,
        operation_id=operation_id,
        action=action,
        updates={
            "artifacts": ArtifactLifecycle.model_validate(artifact_payload),
            "export_available": False,
        },
    )


def withdraw_export(
    job: JobRecord,
    *,
    at_utc: datetime,
    expected_version: int,
    operation_id: str,
) -> JobRecord:
    """Remove an owned published export before its scheduled expiry."""

    action = "export:withdraw"
    if _check_operation(job, operation_id, action):
        return job
    _check_version(job, expected_version)
    at_utc = require_utc(at_utc, field_name="at_utc")
    current = job.artifacts.export
    if (
        not job.export_available
        or current.state is not CleanupState.PRESENT
        or at_utc < job.execution.entered_at_utc
    ):
        raise IllegalTransitionError
    artifact_payload = job.artifacts.model_dump(mode="python")
    artifact_payload[ArtifactKind.EXPORT.value] = ArtifactStatus(
        state=CleanupState.VERIFIED_ABSENT,
        verified_at_utc=at_utc,
    )
    return _updated(
        job,
        operation_id=operation_id,
        action=action,
        updates={
            "artifacts": ArtifactLifecycle.model_validate(artifact_payload),
            "export_available": False,
        },
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
    if policy_version != DEFAULT_JOB_POLICY.profile_version:
        raise ValueError("unsupported job policy version")
    if (
        staged_ttl_seconds <= 0
        or staged_ttl_seconds > DEFAULT_JOB_POLICY.staged_ttl_seconds
        or event_ttl_seconds <= 0
        or event_ttl_seconds > DEFAULT_JOB_POLICY.event_ttl_seconds
    ):
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
    "ResultViewReceipt",
    "ScientificResultReceipt",
    "TerminalOutcome",
    "VersionConflictError",
    "commit_result_view",
    "confirm_scientific_result",
    "new_staged_job",
    "publish_export",
    "retire_export",
    "request_cancellation",
    "terminal_operation_version",
    "transition_artifact",
    "transition_execution",
    "transition_scientific_execution_claim",
    "transition_scientific_success",
    "withdraw_export",
]
