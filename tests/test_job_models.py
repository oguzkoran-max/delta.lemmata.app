from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Literal, cast

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
    ScientificResultReceipt,
    TerminalOutcome,
    VersionConflictError,
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
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY

NOW = datetime(2026, 7, 12, 20, tzinfo=UTC)
JOB_ID = "A" * 43
OWNER_DIGEST = "2" * 64


def _operation(number: int) -> str:
    return "op_" + f"{number:064x}"


def _receipt(
    analysis_outcome: Literal["complete", "partial"] = "complete",
) -> ScientificResultReceipt:
    return ScientificResultReceipt(
        schema_version="scientific-result-receipt-v1",
        request_id="request_" + "1" * 64,
        request_sha256="2" * 64,
        worker_version="stylo-worker-v1",
        result_schema_version="stylo-worker-result-v1",
        analysis_outcome=analysis_outcome,
        artifact_component="053bf21e22c557bd2e9cc53b858b02603c19200680fe1cc2d885bd1b11d6987b",
        byte_size=4096,
        sha256="3" * 64,
    )


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


def _scientific_running() -> JobRecord:
    running = _running()
    return transition_scientific_execution_claim(
        running,
        expected_version=running.version,
        operation_id=_operation(79),
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


def test_terminal_operation_version_is_stable_across_later_operations() -> None:
    assert terminal_operation_version(_running()) is None

    terminal = _terminal()
    assert terminal_operation_version(terminal) == terminal.version
    cleaned = transition_artifact(
        terminal,
        kind=ArtifactKind.INPUT,
        target=CleanupState.VERIFIED_ABSENT,
        at_utc=NOW + timedelta(seconds=4),
        expected_version=terminal.version,
        operation_id=_operation(70),
    )
    assert terminal_operation_version(cleaned) == terminal.version

    duplicate = cleaned.model_copy(
        update={
            "operations": (
                *cleaned.operations,
                AppliedOperation(
                    operation_id=_operation(71),
                    action="execution:terminal:succeeded",
                ),
            )
        }
    )
    assert terminal_operation_version(duplicate) is None

    scientific = _scientific_running()
    scientific = transition_scientific_success(
        scientific,
        receipt=_receipt(),
        at_utc=NOW + timedelta(seconds=3),
        tombstone_expires_at_utc=NOW + timedelta(days=7),
        expected_version=scientific.version,
        operation_id=_operation(72),
    )
    assert terminal_operation_version(scientific) == scientific.version


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
    ("policy_version", "staged_ttl", "event_ttl"),
    [
        ("job-policy-v2", 3600, 604800),
        ("job-policy-v1", 3601, 604800),
        ("job-policy-v1", 3600, 604801),
    ],
)
def test_new_staged_job_rejects_values_outside_the_closed_policy(
    policy_version: str,
    staged_ttl: int,
    event_ttl: int,
) -> None:
    with pytest.raises(ValueError):
        new_staged_job(
            job_id=JOB_ID,
            owner_digest=OWNER_DIGEST,
            policy_version=policy_version,
            at_utc=NOW,
            staged_ttl_seconds=staged_ttl,
            event_ttl_seconds=event_ttl,
        )


def test_queue_deadline_is_capped_and_shortens_the_input_lease() -> None:
    job = _job()
    at_utc = NOW + timedelta(seconds=1)
    with pytest.raises(IllegalTransitionError):
        transition_execution(
            job,
            target=ExecutionState.QUEUED,
            at_utc=at_utc,
            deadline_at_utc=at_utc + timedelta(seconds=DEFAULT_JOB_POLICY.queued_ttl_seconds + 1),
            expected_version=job.version,
            operation_id=_operation(90),
        )
    queued = _queued(job)
    assert queued.artifacts.input.delete_by_utc == queued.execution.deadline_at_utc


def test_terminal_tombstone_and_artifacts_cannot_exceed_policy_caps() -> None:
    running = _running()
    terminal_at = NOW + timedelta(seconds=3)
    with pytest.raises(IllegalTransitionError):
        transition_execution(
            running,
            target=ExecutionState.TERMINAL,
            outcome=TerminalOutcome.FAILED,
            at_utc=terminal_at,
            tombstone_expires_at_utc=terminal_at
            + timedelta(seconds=DEFAULT_JOB_POLICY.tombstone_ttl_seconds + 1),
            expected_version=running.version,
            operation_id=_operation(91),
        )

    terminal = _terminal()
    for number, kind in enumerate(
        (ArtifactKind.WORK, ArtifactKind.RESULT, ArtifactKind.EXPORT), start=92
    ):
        cap_seconds = (
            DEFAULT_JOB_POLICY.unsuccessful_payload_ttl_seconds
            if kind is ArtifactKind.WORK
            else (
                DEFAULT_JOB_POLICY.result_ttl_seconds
                if kind is ArtifactKind.RESULT
                else DEFAULT_JOB_POLICY.export_ttl_seconds
            )
        )
        with pytest.raises(IllegalTransitionError):
            transition_artifact(
                terminal,
                kind=kind,
                target=CleanupState.PRESENT,
                at_utc=terminal_at + timedelta(seconds=1),
                delete_by_utc=terminal_at + timedelta(seconds=cap_seconds + 1),
                expected_version=terminal.version,
                operation_id=_operation(number),
            )


def test_direct_job_validation_rejects_overlong_event_artifact_and_tombstone() -> None:
    unsupported_payload = _job().model_dump(mode="python")
    unsupported_payload["policy_version"] = "job-policy-v2"
    with pytest.raises(ValidationError, match="unsupported job policy"):
        JobRecord.model_validate(unsupported_payload)

    queued_payload = _queued().model_dump(mode="python")
    queued_payload["execution"]["deadline_at_utc"] = queued_payload["execution"][
        "entered_at_utc"
    ] + timedelta(seconds=DEFAULT_JOB_POLICY.queued_ttl_seconds + 1)
    with pytest.raises(ValidationError, match="execution deadline"):
        JobRecord.model_validate(queued_payload)

    staged_payload = _job().model_dump(mode="python")
    staged_payload["event_expires_at_utc"] = NOW + timedelta(
        seconds=DEFAULT_JOB_POLICY.event_ttl_seconds + 1
    )
    with pytest.raises(ValidationError, match="event deadline"):
        JobRecord.model_validate(staged_payload)

    terminal = _terminal(TerminalOutcome.FAILED)
    terminal_payload = terminal.model_dump(mode="python")
    terminal_payload["tombstone_expires_at_utc"] = terminal.outcome.occurred_at_utc + timedelta(
        seconds=DEFAULT_JOB_POLICY.tombstone_ttl_seconds + 1
    )
    with pytest.raises(ValidationError, match="tombstone deadline"):
        JobRecord.model_validate(terminal_payload)

    artifact_payload = terminal.model_dump(mode="python")
    artifact_payload["artifacts"]["input"]["delete_by_utc"] = (
        terminal.outcome.occurred_at_utc
        + timedelta(seconds=DEFAULT_JOB_POLICY.unsuccessful_payload_ttl_seconds + 1)
    )
    with pytest.raises(ValidationError, match="artifact deadline"):
        JobRecord.model_validate(artifact_payload)


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


@pytest.mark.parametrize("field_name", tuple(ScientificResultReceipt.model_fields))
def test_scientific_result_receipt_requires_every_committed_field(field_name: str) -> None:
    payload = _receipt().model_dump(mode="python")
    del payload[field_name]
    with pytest.raises(ValidationError):
        ScientificResultReceipt.model_validate(payload)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("schema_version", "scientific-result-receipt-v2"),
        ("request_id", "request_short"),
        ("request_sha256", "A" * 64),
        ("worker_version", "stylo-worker-v2"),
        ("result_schema_version", "stylo-worker-result-v2"),
        ("analysis_outcome", "failed"),
        ("artifact_component", "f" * 64),
        ("byte_size", True),
        ("byte_size", "4096"),
        ("byte_size", 0),
        ("byte_size", 32 * 1024 * 1024 + 1),
        ("sha256", "short"),
        ("unexpected", "payload"),
    ],
)
def test_scientific_result_receipt_strictly_rejects_invalid_values(
    field_name: str,
    invalid_value: object,
) -> None:
    payload = _receipt().model_dump(mode="python")
    payload[field_name] = invalid_value
    with pytest.raises(ValidationError):
        ScientificResultReceipt.model_validate(payload)


def test_scientific_execution_claim_is_single_use_and_retry_idempotent() -> None:
    running = _running()
    claimed = transition_scientific_execution_claim(
        running,
        expected_version=running.version,
        operation_id=_operation(79),
    )

    assert claimed.version == running.version + 1
    assert claimed.operations[-1] == AppliedOperation(
        operation_id=_operation(79),
        action="scientific:execution:claimed",
    )
    assert (
        transition_scientific_execution_claim(
            claimed,
            expected_version=running.version,
            operation_id=_operation(79),
        )
        is claimed
    )
    with pytest.raises(IllegalTransitionError, match="JOB_ILLEGAL_TRANSITION"):
        transition_scientific_execution_claim(
            claimed,
            expected_version=claimed.version,
            operation_id=_operation(78),
        )

    duplicated = claimed.model_dump(mode="python")
    duplicated["operations"] = (
        *claimed.operations,
        AppliedOperation(
            operation_id=_operation(77),
            action="scientific:execution:claimed",
        ),
    )
    with pytest.raises(ValidationError, match="claim requires one running execution"):
        JobRecord.model_validate(duplicated)


@pytest.mark.parametrize(
    ("analysis_outcome", "commitment"),
    [
        ("complete", "4ee3ba989c2cdc8aca3e9ad4498b60e0f554a07cbae52d5bcf3a119621b587d0"),
        ("partial", "afc2c731c78cf453145c1fc61232afa6b51dfd41e65a7b74c9089db7148e4a46"),
    ],
)
def test_scientific_success_commits_the_exact_complete_or_partial_receipt(
    analysis_outcome: Literal["complete", "partial"],
    commitment: str,
) -> None:
    running = _scientific_running()
    item = _receipt(analysis_outcome)
    at_utc = NOW + timedelta(seconds=3)
    tombstone = at_utc + timedelta(days=7)
    terminal = transition_scientific_success(
        running,
        receipt=item,
        at_utc=at_utc,
        tombstone_expires_at_utc=tombstone,
        expected_version=running.version,
        operation_id=_operation(80),
    )

    assert terminal.execution.state is ExecutionState.TERMINAL
    assert terminal.outcome == Outcome(
        kind=TerminalOutcome.SUCCEEDED,
        occurred_at_utc=at_utc,
    )
    assert terminal.scientific_result == item
    assert terminal.scientific_result_confirmed is False
    assert terminal.artifacts.result.state is CleanupState.PRESENT
    assert terminal.artifacts.result.delete_by_utc == at_utc + timedelta(
        seconds=DEFAULT_JOB_POLICY.result_ttl_seconds
    )
    assert terminal.operations[-1] == AppliedOperation(
        operation_id=_operation(80),
        action=f"scientific:terminal:succeeded:{commitment}",
    )
    assert (
        transition_scientific_success(
            terminal,
            receipt=item,
            at_utc=at_utc,
            tombstone_expires_at_utc=tombstone,
            expected_version=running.version,
            operation_id=_operation(80),
        )
        is terminal
    )
    confirmed = confirm_scientific_result(
        terminal,
        expected_version=terminal.version,
        operation_id=_operation(85),
    )
    assert confirmed.scientific_result_confirmed is True
    assert confirmed.operations[-1] == AppliedOperation(
        operation_id=_operation(85),
        action=f"scientific:guardian:confirmed:{commitment}",
    )
    assert (
        confirm_scientific_result(
            confirmed,
            expected_version=terminal.version,
            operation_id=_operation(85),
        )
        is confirmed
    )
    with pytest.raises(IllegalTransitionError, match="JOB_ILLEGAL_TRANSITION"):
        confirm_scientific_result(
            confirmed,
            expected_version=confirmed.version,
            operation_id=_operation(86),
        )


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("schema_version", "scientific-result-receipt-v2"),
        ("request_id", "request_" + "9" * 64),
        ("request_sha256", "4" * 64),
        ("worker_version", "stylo-worker-v2"),
        ("result_schema_version", "stylo-worker-result-v2"),
        ("analysis_outcome", "partial"),
        ("artifact_component", "5" * 64),
        ("byte_size", 4097),
        ("sha256", "6" * 64),
    ],
)
def test_scientific_success_same_operation_rejects_any_receipt_difference(
    field_name: str,
    replacement: object,
) -> None:
    running = _scientific_running()
    item = _receipt()
    at_utc = NOW + timedelta(seconds=3)
    tombstone = at_utc + timedelta(days=7)
    terminal = transition_scientific_success(
        running,
        receipt=item,
        at_utc=at_utc,
        tombstone_expires_at_utc=tombstone,
        expected_version=running.version,
        operation_id=_operation(81),
    )
    different = item.model_copy(update={field_name: replacement})

    with pytest.raises(OperationConflictError, match="JOB_OPERATION_CONFLICT"):
        transition_scientific_success(
            terminal,
            receipt=different,
            at_utc=at_utc,
            tombstone_expires_at_utc=tombstone,
            expected_version=terminal.version,
            operation_id=_operation(81),
        )


def test_scientific_success_rejects_wrong_receipt_type_and_nonrunning_job() -> None:
    running = _scientific_running()
    at_utc = NOW + timedelta(seconds=3)
    tombstone = at_utc + timedelta(days=7)
    with pytest.raises(IllegalTransitionError, match="JOB_ILLEGAL_TRANSITION"):
        transition_scientific_success(
            running,
            receipt=cast(Any, object()),
            at_utc=at_utc,
            tombstone_expires_at_utc=tombstone,
            expected_version=running.version,
            operation_id=_operation(83),
        )
    unclaimed = _running()
    with pytest.raises(IllegalTransitionError, match="JOB_ILLEGAL_TRANSITION"):
        transition_scientific_success(
            unclaimed,
            receipt=_receipt(),
            at_utc=at_utc,
            tombstone_expires_at_utc=tombstone,
            expected_version=unclaimed.version,
            operation_id=_operation(89),
        )
    staged = _job()
    with pytest.raises(IllegalTransitionError, match="JOB_ILLEGAL_TRANSITION"):
        transition_scientific_success(
            staged,
            receipt=_receipt(),
            at_utc=at_utc,
            tombstone_expires_at_utc=tombstone,
            expected_version=staged.version,
            operation_id=_operation(84),
        )

    claimed = _scientific_running()
    with pytest.raises(IllegalTransitionError, match="JOB_ILLEGAL_TRANSITION"):
        transition_execution(
            claimed,
            target=ExecutionState.TERMINAL,
            outcome=TerminalOutcome.SUCCEEDED,
            at_utc=at_utc,
            tombstone_expires_at_utc=tombstone,
            expected_version=claimed.version,
            operation_id=_operation(90),
        )
    failed = transition_execution(
        claimed,
        target=ExecutionState.TERMINAL,
        outcome=TerminalOutcome.FAILED,
        at_utc=at_utc,
        tombstone_expires_at_utc=tombstone,
        expected_version=claimed.version,
        operation_id=_operation(91),
    )
    forged_success = failed.model_dump(mode="python")
    forged_success["outcome"]["kind"] = TerminalOutcome.SUCCEEDED
    with pytest.raises(ValidationError, match="cannot succeed without a result receipt"):
        JobRecord.model_validate(forged_success)


def test_pending_scientific_result_cannot_publish_export_before_confirmation() -> None:
    running = _scientific_running()
    terminal_at = NOW + timedelta(seconds=3)
    current = transition_scientific_success(
        running,
        receipt=_receipt(),
        at_utc=terminal_at,
        tombstone_expires_at_utc=terminal_at + timedelta(days=7),
        expected_version=running.version,
        operation_id=_operation(100),
    )
    for number, kind in enumerate((ArtifactKind.INPUT, ArtifactKind.WORK), start=101):
        current = transition_artifact(
            current,
            kind=kind,
            target=CleanupState.VERIFIED_ABSENT,
            at_utc=terminal_at + timedelta(seconds=1),
            expected_version=current.version,
            operation_id=_operation(number),
        )
    current = transition_artifact(
        current,
        kind=ArtifactKind.EXPORT,
        target=CleanupState.PRESENT,
        at_utc=terminal_at + timedelta(seconds=1),
        delete_by_utc=terminal_at + timedelta(seconds=DEFAULT_JOB_POLICY.export_ttl_seconds),
        expected_version=current.version,
        operation_id=_operation(103),
    )

    assert current.can_publish_export is False
    confirmed = confirm_scientific_result(
        current,
        expected_version=current.version,
        operation_id=_operation(104),
    )
    assert confirmed.can_publish_export is True

    with pytest.raises(IllegalTransitionError, match="JOB_ILLEGAL_TRANSITION"):
        confirm_scientific_result(
            _terminal(),
            expected_version=_terminal().version,
            operation_id=_operation(105),
        )


def test_job_record_rejects_forged_missing_or_mismatched_scientific_operations() -> None:
    running = _scientific_running()
    terminal = transition_scientific_success(
        running,
        receipt=_receipt(),
        at_utc=NOW + timedelta(seconds=3),
        tombstone_expires_at_utc=NOW + timedelta(days=7),
        expected_version=running.version,
        operation_id=_operation(82),
    )

    missing_operation = terminal.model_dump(mode="python")
    missing_operation["operations"] = terminal.operations[:-1]
    with pytest.raises(ValidationError, match="committed successful scientific transition"):
        JobRecord.model_validate(missing_operation)

    missing_claim = terminal.model_dump(mode="python")
    missing_claim["operations"] = tuple(
        operation
        for operation in terminal.operations
        if operation.action != "scientific:execution:claimed"
    )
    with pytest.raises(ValidationError, match="committed successful scientific transition"):
        JobRecord.model_validate(missing_claim)

    forged_operation = terminal.model_dump(mode="python")
    forged_operation["operations"] = (
        *terminal.operations[:-1],
        terminal.operations[-1].model_copy(
            update={"action": "scientific:terminal:succeeded:" + "f" * 64}
        ),
    )
    with pytest.raises(ValidationError, match="committed successful scientific transition"):
        JobRecord.model_validate(forged_operation)

    mismatched_receipt = terminal.model_dump(mode="python")
    mismatched_receipt["scientific_result"] = _receipt("partial")
    with pytest.raises(ValidationError, match="committed successful scientific transition"):
        JobRecord.model_validate(mismatched_receipt)

    missing_receipt = terminal.model_dump(mode="python")
    missing_receipt["scientific_result"] = None
    with pytest.raises(ValidationError, match="cannot succeed without a result receipt"):
        JobRecord.model_validate(missing_receipt)

    transition_without_receipt = _terminal().model_dump(mode="python")
    transition_without_receipt["operations"] = (
        *_terminal().operations,
        AppliedOperation(
            operation_id=_operation(106),
            action="scientific:terminal:succeeded:" + "f" * 64,
        ),
    )
    with pytest.raises(ValidationError, match="scientific transition requires"):
        JobRecord.model_validate(transition_without_receipt)

    forged_result = _terminal().model_dump(mode="python")
    forged_result["scientific_result"] = _receipt()
    with pytest.raises(ValidationError, match="committed successful scientific transition"):
        JobRecord.model_validate(forged_result)

    confirmation_without_result = _terminal().model_dump(mode="python")
    confirmation_without_result["scientific_result_confirmed"] = True
    with pytest.raises(ValidationError, match="confirmation requires a result receipt"):
        JobRecord.model_validate(confirmation_without_result)

    confirmed = confirm_scientific_result(
        terminal,
        expected_version=terminal.version,
        operation_id=_operation(87),
    )
    missing_confirmation = confirmed.model_dump(mode="python")
    missing_confirmation["operations"] = confirmed.operations[:-1]
    with pytest.raises(ValidationError, match="exact guardian commitment"):
        JobRecord.model_validate(missing_confirmation)

    forged_confirmation = terminal.model_dump(mode="python")
    forged_confirmation["operations"] = (
        *terminal.operations,
        AppliedOperation(
            operation_id=_operation(88),
            action="scientific:guardian:confirmed:" + "f" * 64,
        ),
    )
    with pytest.raises(ValidationError, match="guardian confirmation requires"):
        JobRecord.model_validate(forged_confirmation)


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
    for number, kind in enumerate((ArtifactKind.WORK, ArtifactKind.EXPORT), start=10):
        deadline = NOW + timedelta(minutes=15 if kind is ArtifactKind.WORK else 60)
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
    export_deadline = NOW + timedelta(hours=1)
    for number, kind in enumerate((ArtifactKind.WORK, ArtifactKind.EXPORT), start=10):
        deadline = NOW + timedelta(minutes=15 if kind is ArtifactKind.WORK else 60)
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
        at_utc=export_deadline,
        expected_version=published.version,
        operation_id=_operation(15),
    )
    assert retired.outcome == published.outcome
    assert retired.export_available is False
    assert retired.artifacts.export.state is CleanupState.VERIFIED_ABSENT
    assert retired.artifacts.export.verified_at_utc == export_deadline
    assert (
        retire_export(
            retired,
            at_utc=export_deadline,
            expected_version=published.version,
            operation_id=_operation(15),
        )
        is retired
    )


def test_owner_can_withdraw_a_published_export_before_expiry() -> None:
    job = _terminal()
    for number, kind in enumerate((ArtifactKind.WORK, ArtifactKind.EXPORT), start=10):
        deadline = NOW + timedelta(minutes=15 if kind is ArtifactKind.WORK else 60)
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
    published = publish_export(job, expected_version=job.version, operation_id=_operation(14))
    withdrawn = withdraw_export(
        published,
        at_utc=NOW + timedelta(seconds=20),
        expected_version=published.version,
        operation_id=_operation(15),
    )
    assert withdrawn.export_available is False
    assert withdrawn.artifacts.export.state is CleanupState.VERIFIED_ABSENT
    assert (
        withdraw_export(
            withdrawn,
            at_utc=NOW + timedelta(seconds=20),
            expected_version=published.version,
            operation_id=_operation(15),
        )
        is withdrawn
    )
    with pytest.raises(IllegalTransitionError):
        withdraw_export(
            published,
            at_utc=NOW,
            expected_version=published.version,
            operation_id=_operation(16),
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
