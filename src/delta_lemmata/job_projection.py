"""Conservative projection from trusted job records to payload-free UI states."""

from __future__ import annotations

from delta_lemmata.job_models import (
    CancellationState,
    ExecutionState,
    JobRecord,
    TerminalOutcome,
)
from delta_lemmata.job_ui import JobDisplayState, JobPresentation, project_job_state
from delta_lemmata.session_identity import support_reference

_TERMINAL_DISPLAY_STATES = {
    TerminalOutcome.FAILED: JobDisplayState.FAILED,
    TerminalOutcome.CANCELLED: JobDisplayState.CANCELLED,
    TerminalOutcome.TIMED_OUT: JobDisplayState.TIMED_OUT,
    TerminalOutcome.CRASHED: JobDisplayState.CRASHED,
    TerminalOutcome.ABANDONED: JobDisplayState.ABANDONED,
    TerminalOutcome.EXPIRED: JobDisplayState.EXPIRED,
}


def display_state_for(job: JobRecord) -> JobDisplayState:
    """Resolve lifecycle facts without claiming success before export publication."""

    if job.execution.state is ExecutionState.STAGED:
        return JobDisplayState.STAGED
    if job.execution.state is ExecutionState.QUEUED:
        if job.cancellation.state is CancellationState.REQUESTED:
            return JobDisplayState.CANCELLING
        return JobDisplayState.QUEUED
    if job.execution.state is ExecutionState.RUNNING:
        if job.cancellation.state is CancellationState.REQUESTED:
            return JobDisplayState.CANCELLING
        return JobDisplayState.RUNNING
    if job.outcome is None:
        raise ValueError("terminal job requires an outcome")
    if job.outcome.kind is TerminalOutcome.SUCCEEDED:
        if job.export_available:
            return JobDisplayState.SUCCEEDED
        return JobDisplayState.FINALIZING
    return _TERMINAL_DISPLAY_STATES[job.outcome.kind]


def project_job_record(job: JobRecord) -> JobPresentation:
    """Build an English, short-reference-only presentation for a trusted job."""

    state = display_state_for(job)
    return project_job_state(
        state,
        cleanup_confirmed=state is JobDisplayState.SUCCEEDED,
        support_reference=support_reference(bytes.fromhex(job.owner_digest)),
    )


__all__ = ["display_state_for", "project_job_record"]
