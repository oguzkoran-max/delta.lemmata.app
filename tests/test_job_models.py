from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from delta_lemmata.job_models import (
    AppliedOperation,
    ArtifactKind,
    ArtifactStatus,
    Cancellation,
    CancellationState,
    CleanupState,
    ExecutionState,
    ExecutionStatus,
    IllegalTransitionError,
    JobRecord,
    OperationConflictError,
    Outcome,
    TerminalOutcome,
    VersionConflictError,
    new_staged_job,
    publish_export,
    request_cancellation,
    retire_export,
    transition_artifact,
    transition_execution,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY

NOW = datetime(2026, 7, 12, 20, tzinfo=UTC)
JOB_ID = "A" * 43
OWNER_DIGEST = "2" * 64


def _operation(number: int) -> str:
    return "op_" + f"{number:064x}"


def _job() -> JobRecord:
    policy = DEFAULT_JOB_POLICY
    return new_staged_job(
        job_id=JOB_ID,
        owner_digest=OWNER_DIGEST,
        policy_version=policy.profile_version,
        at_utc=NOW,
        staged_ttl_seconds=policy.staged_ttl_seconds,
        event_ttl_seconds=policy.event_ttl_seconds,
    )


def _queued(job: JobRecord | None = None) -> JobRecord:
    source = job or _job()
    return transition_execution(
        source,
        target=ExecutionState.QUEUED,
        at_utc=NOW + timedelta(seconds=1),
        deadline_at_utc=NOW + timedelta(seconds=901),
        expected_version=source.version,
        operation_id=_operation(1),
    )


def _running() -> JobRecord:
    job = _queued()
    return transition_execution(
        job,
        target=ExecutionState.RUNNING,
        at_utc=NOW + timedelta(seconds=2),
        expected_version=job.version,
        operation_id=_operation(2),
    )


def _terminal(outcome: TerminalOutcome = TerminalOutcome.SUCCEEDED) -> JobRecord:
    job = _running()
    operation_number = 3
    if outcome is TerminalOutcome.CANCELLED:
        job = request_cancellation(
            job,
            at_utc=NOW + timedelta(seconds=2, microseconds=1),
            expected_version=job.version,
            operation_id=_operation(operation_number),
        )
        operation_number += 1
    return transition_execution(
        job,
        target=ExecutionState.TERMINAL,
        outcome=outcome,
        at_utc=NOW + timedelta(seconds=3),
        tombstone_expires_at_utc=NOW + timedelta(days=7, seconds=3),
        expected_version=job.version,
        operation_id=_operation(operation_number),
    )


def test_new_staged_job_is_content_free_immutable_and_uses_absolute_deadlines() -> None:
    job = _job()
    assert job.execution.state is ExecutionState.STAGED
    assert job.execution.deadline_at_utc == NOW + timedelta(hours=1)
    assert job.artifacts.input.delete_by_utc == job.execution.deadline_at_utc
    assert job.artifacts.work == job.artifacts.result == job.artifacts.export
    assert job.event_expires_at_utc == NOW + timedelta(days=7)
    assert job.outcome is None
    assert job.version == 0
    assert job.can_publish_export is False
    with pytest.raises(ValidationError):
        job.version = 1
    with pytest.raises(ValueError, match="retention durations must be positive"):
        new_staged_job(
            job_id=JOB_ID,
            owner_digest=OWNER_DIGEST,
            policy_version="job-policy-v1",
            at_utc=NOW,
            staged_ttl_seconds=0,
            event_ttl_seconds=1,
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"state": ExecutionState.STAGED, "entered_at_utc": NOW},
        {
            "state": ExecutionState.QUEUED,
            "entered_at_utc": NOW,
            "deadline_at_utc": NOW,
        },
        {
            "state": ExecutionState.RUNNING,
            "entered_at_utc": NOW,
            "deadline_at_utc": NOW + timedelta(seconds=1),
        },
        {
            "state": ExecutionState.TERMINAL,
            "entered_at_utc": NOW,
            "deadline_at_utc": NOW + timedelta(seconds=1),
        },
        {
            "state": ExecutionState.RUNNING,
            "entered_at_utc": NOW.replace(tzinfo=None),
        },
    ],
)
def test_execution_status_rejects_missing_false_or_non_utc_deadlines(
    payload: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        ExecutionStatus.model_validate(payload)


def test_outcome_and_cancellation_require_utc_consistent_timestamps() -> None:
    with pytest.raises(ValidationError):
        Outcome(kind=TerminalOutcome.FAILED, occurred_at_utc=NOW.replace(tzinfo=None))
    with pytest.raises(ValidationError, match="state and timestamp must agree"):
        Cancellation(state=CancellationState.REQUESTED)
    with pytest.raises(ValidationError, match="state and timestamp must agree"):
        Cancellation(requested_at_utc=NOW)
    with pytest.raises(ValidationError):
        Cancellation(
            state=CancellationState.REQUESTED,
            requested_at_utc=NOW.astimezone(timezone(timedelta(hours=3))),
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"state": CleanupState.VERIFIED_ABSENT},
        {"state": CleanupState.PRESENT, "delete_by_utc": NOW, "verified_at_utc": NOW},
        {"state": CleanupState.NOT_CREATED, "delete_by_utc": NOW},
        {"state": CleanupState.PENDING},
        {
            "state": CleanupState.PRESENT,
            "delete_by_utc": NOW.astimezone(timezone(timedelta(hours=3))),
        },
    ],
)
def test_artifact_status_rejects_inconsistent_or_non_utc_timestamps(
    payload: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        ArtifactStatus.model_validate(payload)


def test_artifact_lifecycle_returns_each_separate_state() -> None:
    job = _job()
    for kind in ArtifactKind:
        assert job.artifacts.for_kind(kind) is getattr(job.artifacts, kind.value)


def test_job_record_rejects_duplicate_operations_and_inconsistent_terminal_state() -> None:
    payload = _job().model_dump(mode="python")
    operation = AppliedOperation(operation_id=_operation(1), action="execution:queued:none")
    payload["operations"] = (operation, operation)
    with pytest.raises(ValidationError, match="must be unique"):
        JobRecord.model_validate(payload)

    payload = _job().model_dump(mode="python")
    payload["outcome"] = Outcome(kind=TerminalOutcome.FAILED, occurred_at_utc=NOW)
    with pytest.raises(ValidationError, match="terminal execution state and outcome"):
        JobRecord.model_validate(payload)

    payload = _job().model_dump(mode="python")
    payload["tombstone_expires_at_utc"] = NOW + timedelta(days=7)
    with pytest.raises(ValidationError, match="tombstone deadline"):
        JobRecord.model_validate(payload)

    payload = _terminal().model_dump(mode="python")
    payload["tombstone_expires_at_utc"] = None
    with pytest.raises(ValidationError, match="tombstone deadline"):
        JobRecord.model_validate(payload)

    payload = _job().model_dump(mode="python")
    payload["event_expires_at_utc"] = NOW
    with pytest.raises(ValidationError, match="event expiry"):
        JobRecord.model_validate(payload)

    payload = _terminal().model_dump(mode="python")
    payload["tombstone_expires_at_utc"] = NOW + timedelta(seconds=3)
    with pytest.raises(ValidationError, match="tombstone expiry"):
        JobRecord.model_validate(payload)

    payload = _terminal(TerminalOutcome.CANCELLED).model_dump(mode="python")
    payload["cancellation"] = Cancellation()
    with pytest.raises(ValidationError, match="requires a cancellation request"):
        JobRecord.model_validate(payload)


def test_execution_legal_path_increments_version_and_is_idempotent() -> None:
    staged = _job()
    queued = _queued(staged)
    assert queued.version == 1
    assert queued.execution.state is ExecutionState.QUEUED
    assert queued.execution.deadline_at_utc == NOW + timedelta(seconds=901)
    assert (
        transition_execution(
            queued,
            target=ExecutionState.QUEUED,
            at_utc=NOW + timedelta(seconds=1),
            deadline_at_utc=NOW + timedelta(seconds=901),
            expected_version=0,
            operation_id=_operation(1),
        )
        is queued
    )

    running = transition_execution(
        queued,
        target=ExecutionState.RUNNING,
        at_utc=NOW + timedelta(seconds=2),
        expected_version=1,
        operation_id=_operation(2),
    )
    terminal = transition_execution(
        running,
        target=ExecutionState.TERMINAL,
        outcome=TerminalOutcome.SUCCEEDED,
        at_utc=NOW + timedelta(seconds=3),
        tombstone_expires_at_utc=NOW + timedelta(days=7),
        expected_version=2,
        operation_id=_operation(3),
    )
    assert terminal.version == 3
    assert terminal.outcome == Outcome(
        kind=TerminalOutcome.SUCCEEDED,
        occurred_at_utc=NOW + timedelta(seconds=3),
    )


@pytest.mark.parametrize(
    "outcome",
    [
        TerminalOutcome.SUCCEEDED,
        TerminalOutcome.FAILED,
        TerminalOutcome.CANCELLED,
        TerminalOutcome.TIMED_OUT,
        TerminalOutcome.CRASHED,
        TerminalOutcome.ABANDONED,
    ],
)
def test_running_accepts_each_single_terminal_outcome(outcome: TerminalOutcome) -> None:
    terminal = _terminal(outcome)
    assert terminal.outcome is not None
    assert terminal.outcome.kind is outcome


def test_cancelled_outcome_requires_a_separate_request() -> None:
    job = _running()
    with pytest.raises(IllegalTransitionError):
        transition_execution(
            job,
            target=ExecutionState.TERMINAL,
            outcome=TerminalOutcome.CANCELLED,
            at_utc=NOW + timedelta(seconds=3),
            tombstone_expires_at_utc=NOW + timedelta(days=7),
            expected_version=job.version,
            operation_id=_operation(3),
        )


@pytest.mark.parametrize("source", [ExecutionState.STAGED, ExecutionState.QUEUED])
@pytest.mark.parametrize("outcome", [TerminalOutcome.ABANDONED, TerminalOutcome.EXPIRED])
def test_pre_run_work_can_only_end_as_abandoned_or_expired(
    source: ExecutionState, outcome: TerminalOutcome
) -> None:
    job = _job() if source is ExecutionState.STAGED else _queued()
    terminal = transition_execution(
        job,
        target=ExecutionState.TERMINAL,
        outcome=outcome,
        at_utc=NOW + timedelta(seconds=5),
        tombstone_expires_at_utc=NOW + timedelta(days=7),
        expected_version=job.version,
        operation_id=_operation(20 + job.version),
    )
    assert terminal.outcome is not None
    assert terminal.outcome.kind is outcome


def test_execution_rejects_stale_conflicting_and_illegal_operations() -> None:
    job = _job()
    with pytest.raises(VersionConflictError, match="JOB_VERSION_CONFLICT"):
        transition_execution(
            job,
            target=ExecutionState.QUEUED,
            at_utc=NOW + timedelta(seconds=1),
            deadline_at_utc=NOW + timedelta(minutes=15),
            expected_version=1,
            operation_id=_operation(1),
        )
    queued = _queued(job)
    with pytest.raises(OperationConflictError, match="JOB_OPERATION_CONFLICT"):
        transition_execution(
            queued,
            target=ExecutionState.RUNNING,
            at_utc=NOW + timedelta(seconds=2),
            expected_version=queued.version,
            operation_id=_operation(1),
        )
    with pytest.raises(IllegalTransitionError, match="JOB_ILLEGAL_TRANSITION"):
        transition_execution(
            queued,
            target=ExecutionState.STAGED,
            at_utc=NOW + timedelta(seconds=2),
            expected_version=queued.version,
            operation_id=_operation(4),
        )
    with pytest.raises(IllegalTransitionError):
        transition_execution(
            queued,
            target=ExecutionState.RUNNING,
            at_utc=NOW,
            expected_version=queued.version,
            operation_id=_operation(5),
        )


@pytest.mark.parametrize(
    ("outcome", "tombstone_delta", "deadline_delta"),
    [
        (None, None, None),
        (TerminalOutcome.FAILED, None, None),
        (TerminalOutcome.SUCCEEDED, timedelta(days=7), None),
        (TerminalOutcome.ABANDONED, timedelta(seconds=-1), None),
        (TerminalOutcome.ABANDONED, timedelta(days=7), timedelta(minutes=1)),
    ],
)
def test_terminal_transition_requires_legal_outcome_and_future_tombstone(
    outcome: TerminalOutcome | None,
    tombstone_delta: timedelta | None,
    deadline_delta: timedelta | None,
) -> None:
    job = _queued()
    with pytest.raises(IllegalTransitionError):
        transition_execution(
            job,
            target=ExecutionState.TERMINAL,
            at_utc=NOW + timedelta(seconds=3),
            tombstone_expires_at_utc=(
                NOW + timedelta(seconds=3) + tombstone_delta
                if isinstance(tombstone_delta, timedelta)
                else None
            ),
            deadline_at_utc=(
                NOW + timedelta(seconds=3) + deadline_delta
                if isinstance(deadline_delta, timedelta)
                else None
            ),
            expected_version=job.version,
            operation_id=_operation(40),
            outcome=outcome,
        )


def test_nonterminal_transition_rejects_terminal_fields_or_bad_deadline() -> None:
    cases: list[dict[str, Any]] = [
        {"outcome": TerminalOutcome.FAILED},
        {"tombstone_expires_at_utc": NOW + timedelta(days=7)},
        {"deadline_at_utc": NOW},
        {"deadline_at_utc": NOW.replace(tzinfo=None)},
    ]
    for number, kwargs in enumerate(
        cases,
        start=50,
    ):
        with pytest.raises(IllegalTransitionError):
            transition_execution(
                _job(),
                target=ExecutionState.QUEUED,
                at_utc=NOW + timedelta(seconds=1),
                expected_version=0,
                operation_id=_operation(number),
                **kwargs,
            )


def test_second_terminal_outcome_fails_closed() -> None:
    terminal = _terminal()
    with pytest.raises(IllegalTransitionError):
        transition_execution(
            terminal,
            target=ExecutionState.TERMINAL,
            outcome=TerminalOutcome.FAILED,
            at_utc=NOW + timedelta(seconds=4),
            tombstone_expires_at_utc=NOW + timedelta(days=7),
            expected_version=terminal.version,
            operation_id=_operation(4),
        )


def test_cancellation_request_is_separate_idempotent_and_cas_guarded() -> None:
    job = _running()
    requested = request_cancellation(
        job,
        at_utc=NOW + timedelta(seconds=3),
        expected_version=job.version,
        operation_id=_operation(10),
    )
    assert requested.cancellation.state is CancellationState.REQUESTED
    assert requested.outcome is None
    assert (
        request_cancellation(
            requested,
            at_utc=NOW + timedelta(seconds=3),
            expected_version=job.version,
            operation_id=_operation(10),
        )
        is requested
    )
    with pytest.raises(VersionConflictError):
        request_cancellation(
            job,
            at_utc=NOW + timedelta(seconds=3),
            expected_version=0,
            operation_id=_operation(11),
        )
    with pytest.raises(IllegalTransitionError):
        request_cancellation(
            requested,
            at_utc=NOW + timedelta(seconds=4),
            expected_version=requested.version,
            operation_id=_operation(11),
        )
    with pytest.raises(IllegalTransitionError):
        request_cancellation(
            _terminal(),
            at_utc=NOW + timedelta(seconds=4),
            expected_version=3,
            operation_id=_operation(11),
        )
    with pytest.raises(IllegalTransitionError):
        request_cancellation(
            _running(),
            at_utc=NOW,
            expected_version=2,
            operation_id=_operation(11),
        )


def test_queued_job_can_be_cancelled_but_staged_job_cannot_request_cancellation() -> None:
    queued = _queued()
    requested = request_cancellation(
        queued,
        at_utc=NOW + timedelta(seconds=2),
        expected_version=queued.version,
        operation_id=_operation(20),
    )
    cancelled = transition_execution(
        requested,
        target=ExecutionState.TERMINAL,
        outcome=TerminalOutcome.CANCELLED,
        at_utc=NOW + timedelta(seconds=3),
        tombstone_expires_at_utc=NOW + timedelta(days=7, seconds=3),
        expected_version=requested.version,
        operation_id=_operation(21),
    )
    assert cancelled.outcome is not None
    assert cancelled.outcome.kind is TerminalOutcome.CANCELLED

    with pytest.raises(IllegalTransitionError):
        request_cancellation(
            _job(),
            at_utc=NOW + timedelta(seconds=1),
            expected_version=0,
            operation_id=_operation(22),
        )


def test_transition_revalidates_a_model_copy_that_bypassed_pydantic_validation() -> None:
    queued = _queued()
    invalid = queued.model_copy(update={"event_expires_at_utc": queued.execution.entered_at_utc})

    with pytest.raises(ValidationError, match="event expiry"):
        request_cancellation(
            invalid,
            at_utc=NOW + timedelta(seconds=2),
            expected_version=invalid.version,
            operation_id=_operation(23),
        )


def test_artifact_cleanup_legal_retry_path_preserves_outcome() -> None:
    job = _terminal(TerminalOutcome.FAILED)
    deadline = NOW + timedelta(minutes=15)
    pending = transition_artifact(
        job,
        kind=ArtifactKind.INPUT,
        target=CleanupState.PENDING,
        at_utc=NOW + timedelta(seconds=4),
        delete_by_utc=deadline,
        expected_version=job.version,
        operation_id=_operation(10),
    )
    in_progress = transition_artifact(
        pending,
        kind=ArtifactKind.INPUT,
        target=CleanupState.IN_PROGRESS,
        at_utc=NOW + timedelta(seconds=5),
        delete_by_utc=deadline,
        expected_version=pending.version,
        operation_id=_operation(11),
    )
    failed = transition_artifact(
        in_progress,
        kind=ArtifactKind.INPUT,
        target=CleanupState.FAILED,
        at_utc=NOW + timedelta(seconds=6),
        delete_by_utc=deadline,
        expected_version=in_progress.version,
        operation_id=_operation(12),
    )
    retry = transition_artifact(
        failed,
        kind=ArtifactKind.INPUT,
        target=CleanupState.IN_PROGRESS,
        at_utc=NOW + timedelta(seconds=7),
        delete_by_utc=deadline,
        expected_version=failed.version,
        operation_id=_operation(13),
    )
    absent = transition_artifact(
        retry,
        kind=ArtifactKind.INPUT,
        target=CleanupState.VERIFIED_ABSENT,
        at_utc=NOW + timedelta(seconds=8),
        expected_version=retry.version,
        operation_id=_operation(14),
    )
    assert absent.artifacts.input.verified_at_utc == NOW + timedelta(seconds=8)
    assert absent.outcome == job.outcome
    assert (
        transition_artifact(
            absent,
            kind=ArtifactKind.INPUT,
            target=CleanupState.VERIFIED_ABSENT,
            at_utc=NOW + timedelta(seconds=8),
            expected_version=retry.version,
            operation_id=_operation(14),
        )
        is absent
    )


def test_artifact_creation_direct_cleanup_and_retry_from_failed_to_pending() -> None:
    job = _job()
    deadline = NOW + timedelta(hours=1)
    created = transition_artifact(
        job,
        kind=ArtifactKind.RESULT,
        target=CleanupState.PRESENT,
        at_utc=NOW + timedelta(seconds=1),
        delete_by_utc=deadline,
        expected_version=0,
        operation_id=_operation(20),
    )
    absent = transition_artifact(
        created,
        kind=ArtifactKind.RESULT,
        target=CleanupState.VERIFIED_ABSENT,
        at_utc=NOW + timedelta(seconds=2),
        expected_version=1,
        operation_id=_operation(21),
    )
    assert absent.artifacts.result.state is CleanupState.VERIFIED_ABSENT

    working = transition_artifact(
        job,
        kind=ArtifactKind.INPUT,
        target=CleanupState.IN_PROGRESS,
        at_utc=NOW + timedelta(seconds=1),
        delete_by_utc=deadline,
        expected_version=0,
        operation_id=_operation(22),
    )
    failed = transition_artifact(
        working,
        kind=ArtifactKind.INPUT,
        target=CleanupState.FAILED,
        at_utc=NOW + timedelta(seconds=2),
        delete_by_utc=deadline,
        expected_version=1,
        operation_id=_operation(23),
    )
    pending = transition_artifact(
        failed,
        kind=ArtifactKind.INPUT,
        target=CleanupState.PENDING,
        at_utc=NOW + timedelta(seconds=3),
        delete_by_utc=deadline,
        expected_version=2,
        operation_id=_operation(24),
    )
    assert pending.artifacts.input.state is CleanupState.PENDING


def test_cleanup_retry_preserves_an_expired_absolute_deadline() -> None:
    job = _terminal(TerminalOutcome.FAILED)
    deadline = NOW + timedelta(seconds=5)
    in_progress = transition_artifact(
        job,
        kind=ArtifactKind.INPUT,
        target=CleanupState.IN_PROGRESS,
        at_utc=NOW + timedelta(seconds=4),
        delete_by_utc=deadline,
        expected_version=job.version,
        operation_id=_operation(25),
    )
    failed = transition_artifact(
        in_progress,
        kind=ArtifactKind.INPUT,
        target=CleanupState.FAILED,
        at_utc=deadline,
        delete_by_utc=deadline,
        expected_version=in_progress.version,
        operation_id=_operation(26),
    )
    retry = transition_artifact(
        failed,
        kind=ArtifactKind.INPUT,
        target=CleanupState.IN_PROGRESS,
        at_utc=deadline + timedelta(seconds=1),
        delete_by_utc=deadline,
        expected_version=failed.version,
        operation_id=_operation(27),
    )
    absent = transition_artifact(
        retry,
        kind=ArtifactKind.INPUT,
        target=CleanupState.VERIFIED_ABSENT,
        at_utc=deadline + timedelta(seconds=1),
        expected_version=retry.version,
        operation_id=_operation(28),
    )
    assert absent.artifacts.input.state is CleanupState.VERIFIED_ABSENT


def test_artifact_transition_rejects_stale_illegal_and_invalid_deadlines() -> None:
    job = _job()
    with pytest.raises(VersionConflictError):
        transition_artifact(
            job,
            kind=ArtifactKind.INPUT,
            target=CleanupState.PENDING,
            at_utc=NOW + timedelta(seconds=1),
            delete_by_utc=NOW + timedelta(minutes=15),
            expected_version=1,
            operation_id=_operation(30),
        )
    with pytest.raises(IllegalTransitionError):
        transition_artifact(
            job,
            kind=ArtifactKind.WORK,
            target=CleanupState.PENDING,
            at_utc=NOW + timedelta(seconds=1),
            delete_by_utc=NOW + timedelta(minutes=15),
            expected_version=0,
            operation_id=_operation(30),
        )
    with pytest.raises(IllegalTransitionError):
        transition_artifact(
            job,
            kind=ArtifactKind.INPUT,
            target=CleanupState.PENDING,
            at_utc=NOW + timedelta(seconds=1),
            delete_by_utc=NOW,
            expected_version=0,
            operation_id=_operation(31),
        )
    with pytest.raises(IllegalTransitionError):
        transition_artifact(
            job,
            kind=ArtifactKind.INPUT,
            target=CleanupState.PENDING,
            at_utc=NOW + timedelta(seconds=1),
            expected_version=0,
            operation_id=_operation(32),
        )
    with pytest.raises(IllegalTransitionError):
        transition_artifact(
            _running(),
            kind=ArtifactKind.INPUT,
            target=CleanupState.PENDING,
            at_utc=NOW + timedelta(seconds=1),
            delete_by_utc=NOW + timedelta(minutes=15),
            expected_version=2,
            operation_id=_operation(33),
        )
    with pytest.raises(IllegalTransitionError):
        transition_artifact(
            job,
            kind=ArtifactKind.INPUT,
            target=CleanupState.PENDING,
            at_utc=NOW + timedelta(seconds=1),
            delete_by_utc=NOW + timedelta(hours=2),
            expected_version=0,
            operation_id=_operation(34),
        )


def test_success_export_requires_verified_input_and_work_cleanup() -> None:
    job = _terminal()
    deadline = NOW + timedelta(hours=1)
    for number, kind in enumerate((ArtifactKind.WORK, ArtifactKind.EXPORT), start=10):
        job = transition_artifact(
            job,
            kind=kind,
            target=CleanupState.PRESENT,
            at_utc=NOW + timedelta(seconds=number),
            delete_by_utc=deadline,
            expected_version=job.version,
            operation_id=_operation(number),
        )
    for number, kind in enumerate((ArtifactKind.INPUT, ArtifactKind.WORK), start=12):
        job = transition_artifact(
            job,
            kind=kind,
            target=CleanupState.VERIFIED_ABSENT,
            at_utc=NOW + timedelta(seconds=number),
            expected_version=job.version,
            operation_id=_operation(number),
        )
    assert job.can_publish_export is True
    published = publish_export(
        job,
        expected_version=job.version,
        operation_id=_operation(14),
    )
    assert published.export_available is True
    assert (
        publish_export(
            published,
            expected_version=job.version,
            operation_id=_operation(14),
        )
        is published
    )


def test_published_export_retires_only_at_its_deadline_and_is_idempotent() -> None:
    job = _terminal()
    deadline = NOW + timedelta(hours=1)
    for number, kind in enumerate((ArtifactKind.WORK, ArtifactKind.EXPORT), start=10):
        job = transition_artifact(
            job,
            kind=kind,
            target=CleanupState.PRESENT,
            at_utc=NOW + timedelta(seconds=number),
            delete_by_utc=deadline,
            expected_version=job.version,
            operation_id=_operation(number),
        )
    for number, kind in enumerate((ArtifactKind.INPUT, ArtifactKind.WORK), start=12):
        job = transition_artifact(
            job,
            kind=kind,
            target=CleanupState.VERIFIED_ABSENT,
            at_utc=NOW + timedelta(seconds=number),
            expected_version=job.version,
            operation_id=_operation(number),
        )
    published = publish_export(
        job,
        expected_version=job.version,
        operation_id=_operation(14),
    )
    retired = retire_export(
        published,
        at_utc=deadline,
        expected_version=published.version,
        operation_id=_operation(15),
    )
    assert retired.outcome == published.outcome
    assert retired.export_available is False
    assert retired.artifacts.export.state is CleanupState.VERIFIED_ABSENT
    assert retired.artifacts.export.verified_at_utc == deadline
    assert (
        retire_export(
            retired,
            at_utc=deadline,
            expected_version=published.version,
            operation_id=_operation(15),
        )
        is retired
    )


def test_export_retirement_rejects_stale_early_unpublished_or_missing_deadline() -> None:
    job = _terminal()
    with pytest.raises(VersionConflictError):
        retire_export(
            job,
            at_utc=NOW + timedelta(hours=1),
            expected_version=0,
            operation_id=_operation(15),
        )
    with pytest.raises(IllegalTransitionError):
        retire_export(
            job,
            at_utc=NOW + timedelta(hours=1),
            expected_version=job.version,
            operation_id=_operation(15),
        )

    deadline = NOW + timedelta(hours=1)
    payload = job.model_dump(mode="python")
    payload["export_available"] = True
    payload["artifacts"]["input"] = ArtifactStatus(
        state=CleanupState.VERIFIED_ABSENT,
        verified_at_utc=NOW + timedelta(seconds=4),
    )
    payload["artifacts"]["work"] = ArtifactStatus(
        state=CleanupState.VERIFIED_ABSENT,
        verified_at_utc=NOW + timedelta(seconds=4),
    )
    payload["artifacts"]["export"] = ArtifactStatus(
        state=CleanupState.PRESENT,
        delete_by_utc=deadline,
    )
    published = JobRecord.model_validate(payload)
    with pytest.raises(IllegalTransitionError):
        retire_export(
            published,
            at_utc=deadline - timedelta(microseconds=1),
            expected_version=published.version,
            operation_id=_operation(16),
        )
    invalid_export = published.artifacts.export.model_copy(update={"delete_by_utc": None})
    invalid_artifacts = published.artifacts.model_copy(update={"export": invalid_export})
    invalid_published = published.model_copy(update={"artifacts": invalid_artifacts})
    with pytest.raises(IllegalTransitionError):
        retire_export(
            invalid_published,
            at_utc=deadline,
            expected_version=published.version,
            operation_id=_operation(17),
        )


def test_export_publication_fails_closed_for_stale_unready_or_already_available() -> None:
    job = _terminal()
    with pytest.raises(VersionConflictError):
        publish_export(job, expected_version=0, operation_id=_operation(10))
    with pytest.raises(IllegalTransitionError):
        publish_export(job, expected_version=job.version, operation_id=_operation(10))

    payload = job.model_dump(mode="python")
    payload["export_available"] = True
    with pytest.raises(ValidationError, match="export cannot be available"):
        JobRecord.model_validate(payload)


def test_models_reject_malformed_ids_extra_fields_and_non_utc_job_deadlines() -> None:
    payload = _job().model_dump(mode="python")
    payload["job_id"] = "job_short"
    with pytest.raises(ValidationError):
        JobRecord.model_validate(payload)
    payload = _job().model_dump(mode="python")
    payload["owner_digest"] = "not-a-digest"
    with pytest.raises(ValidationError):
        JobRecord.model_validate(payload)
    payload = _job().model_dump(mode="python")
    payload["event_expires_at_utc"] = NOW.replace(tzinfo=None)
    with pytest.raises(ValidationError):
        JobRecord.model_validate(payload)
    with pytest.raises(ValidationError):
        AppliedOperation(operation_id="bad", action="execution:queued:none")
    with pytest.raises(ValidationError):
        AppliedOperation(operation_id=_operation(1), action="Contains payload")
    with pytest.raises(ValidationError):
        ArtifactStatus(state=CleanupState.NOT_CREATED, unexpected=True)  # type: ignore[call-arg]
