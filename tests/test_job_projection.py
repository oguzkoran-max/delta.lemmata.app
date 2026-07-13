from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from delta_lemmata.job_models import (
    ArtifactKind,
    CancellationState,
    CleanupState,
    ExecutionState,
    JobRecord,
    TerminalOutcome,
    new_staged_job,
    publish_export,
    request_cancellation,
    transition_artifact,
    transition_execution,
)
from delta_lemmata.job_projection import display_state_for, project_job_record
from delta_lemmata.job_ui import JobDisplayState

NOW = datetime(2026, 7, 12, 21, tzinfo=UTC)


def operation(number: int) -> str:
    return "op_" + f"{number:064x}"


def staged() -> JobRecord:
    return new_staged_job(
        job_id="A" * 43,
        owner_digest="2" * 64,
        policy_version="job-policy-v1",
        at_utc=NOW,
        staged_ttl_seconds=3600,
        event_ttl_seconds=604800,
    )


def queued() -> JobRecord:
    job = staged()
    return transition_execution(
        job,
        target=ExecutionState.QUEUED,
        at_utc=NOW + timedelta(seconds=1),
        deadline_at_utc=NOW + timedelta(minutes=15),
        expected_version=job.version,
        operation_id=operation(1),
    )


def running() -> JobRecord:
    job = queued()
    return transition_execution(
        job,
        target=ExecutionState.RUNNING,
        at_utc=NOW + timedelta(seconds=2),
        expected_version=job.version,
        operation_id=operation(2),
    )


def terminal(outcome: TerminalOutcome) -> JobRecord:
    job = queued() if outcome is TerminalOutcome.EXPIRED else running()
    next_operation = 3
    if outcome is TerminalOutcome.CANCELLED:
        job = request_cancellation(
            job,
            at_utc=NOW + timedelta(seconds=3),
            expected_version=job.version,
            operation_id=operation(next_operation),
        )
        next_operation += 1
    return transition_execution(
        job,
        target=ExecutionState.TERMINAL,
        outcome=outcome,
        at_utc=NOW + timedelta(seconds=4),
        tombstone_expires_at_utc=NOW + timedelta(days=7),
        expected_version=job.version,
        operation_id=operation(next_operation),
    )


def test_staged_queued_and_running_states_project_directly() -> None:
    assert display_state_for(staged()) is JobDisplayState.STAGED
    assert display_state_for(queued()) is JobDisplayState.QUEUED
    assert display_state_for(running()) is JobDisplayState.RUNNING


@pytest.mark.parametrize("source", [queued, running])
def test_requested_cancellation_projects_as_cancelling(source: object) -> None:
    job = source()  # type: ignore[operator]
    requested = request_cancellation(
        job,
        at_utc=NOW + timedelta(seconds=3),
        expected_version=job.version,
        operation_id=operation(10),
    )
    assert requested.cancellation.state is CancellationState.REQUESTED
    assert display_state_for(requested) is JobDisplayState.CANCELLING


@pytest.mark.parametrize(
    ("outcome", "state"),
    [
        (TerminalOutcome.FAILED, JobDisplayState.FAILED),
        (TerminalOutcome.CANCELLED, JobDisplayState.CANCELLED),
        (TerminalOutcome.TIMED_OUT, JobDisplayState.TIMED_OUT),
        (TerminalOutcome.CRASHED, JobDisplayState.CRASHED),
        (TerminalOutcome.ABANDONED, JobDisplayState.ABANDONED),
        (TerminalOutcome.EXPIRED, JobDisplayState.EXPIRED),
    ],
)
def test_terminal_outcomes_have_distinct_honest_display_states(
    outcome: TerminalOutcome, state: JobDisplayState
) -> None:
    job = terminal(outcome)
    assert display_state_for(job) is JobDisplayState.CLEANING
    for index, kind in enumerate(ArtifactKind, start=20):
        job = transition_artifact(
            job,
            kind=kind,
            target=CleanupState.VERIFIED_ABSENT,
            at_utc=NOW + timedelta(seconds=index),
            expected_version=job.version,
            operation_id=operation(index),
        )
    assert display_state_for(job) is state


def test_expired_job_never_claims_removal_until_cleanup_is_verified() -> None:
    expired = terminal(TerminalOutcome.EXPIRED)
    presentation = project_job_record(expired)
    assert presentation.state_id == JobDisplayState.CLEANING.value
    assert "removed" not in presentation.body.casefold()

    in_progress = transition_artifact(
        expired,
        kind=ArtifactKind.INPUT,
        target=CleanupState.IN_PROGRESS,
        at_utc=NOW + timedelta(seconds=5),
        delete_by_utc=expired.artifacts.input.delete_by_utc,
        expected_version=expired.version,
        operation_id=operation(40),
    )
    failed = transition_artifact(
        in_progress,
        kind=ArtifactKind.INPUT,
        target=CleanupState.FAILED,
        at_utc=NOW + timedelta(seconds=6),
        delete_by_utc=in_progress.artifacts.input.delete_by_utc,
        expected_version=in_progress.version,
        operation_id=operation(41),
    )
    failed_presentation = project_job_record(failed)
    assert failed_presentation.state_id == JobDisplayState.CLEANUP_FAILED.value
    assert "could not be confirmed" in failed_presentation.body
    assert "removed" not in failed_presentation.body.casefold()


def test_success_remains_finalizing_until_cleanup_and_export_publication() -> None:
    job = terminal(TerminalOutcome.SUCCEEDED)
    assert display_state_for(job) is JobDisplayState.FINALIZING

    input_absent = transition_artifact(
        job,
        kind=ArtifactKind.INPUT,
        target=CleanupState.VERIFIED_ABSENT,
        at_utc=NOW + timedelta(seconds=5),
        expected_version=job.version,
        operation_id=operation(10),
    )
    work_absent = transition_artifact(
        input_absent,
        kind=ArtifactKind.WORK,
        target=CleanupState.VERIFIED_ABSENT,
        at_utc=NOW + timedelta(seconds=6),
        expected_version=input_absent.version,
        operation_id=operation(11),
    )
    export_present = transition_artifact(
        work_absent,
        kind=ArtifactKind.EXPORT,
        target=CleanupState.PRESENT,
        at_utc=NOW + timedelta(seconds=7),
        delete_by_utc=NOW + timedelta(hours=1),
        expected_version=work_absent.version,
        operation_id=operation(12),
    )
    published = publish_export(
        export_present,
        expected_version=export_present.version,
        operation_id=operation(13),
    )

    assert display_state_for(published) is JobDisplayState.SUCCEEDED
    presentation = project_job_record(published)
    assert presentation.title == "Analysis complete"
    assert presentation.support_reference is not None
    assert presentation.support_reference.startswith("SUP-")
    assert published.job_id not in " ".join(
        (presentation.label, presentation.title, presentation.body)
    )


def test_impossible_terminal_record_fails_closed() -> None:
    impossible = running().model_copy(
        update={
            "execution": running().execution.model_copy(update={"state": ExecutionState.TERMINAL}),
            "outcome": None,
        }
    )
    with pytest.raises(ValueError, match="requires an outcome"):
        display_state_for(impossible)
