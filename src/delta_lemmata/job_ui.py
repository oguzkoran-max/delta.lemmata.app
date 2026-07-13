"""Pure, payload-free presentation model for the analysis job lifecycle."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from enum import StrEnum


class JobDisplayState(StrEnum):
    """Stable lifecycle states exposed to the presentation boundary."""

    SUBMITTING = "submitting"
    STAGED = "staged"
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    FINALIZING = "finalizing"
    CLEANING = "cleaning"
    CLEANUP_FAILED = "cleanup_failed"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    CRASHED = "crashed"
    ABANDONED = "abandoned"
    EXPIRED = "expired"
    BUSY = "busy"


class PresentationRole(StrEnum):
    """Accessible live-region role for a job projection."""

    STATUS = "status"
    ALERT = "alert"


class JobAction(StrEnum):
    """Commands the job surface can offer."""

    CANCEL = "cancel"
    RETRY = "retry"
    START_OVER = "start_over"


@dataclass(frozen=True, slots=True)
class DisabledActionReason:
    """An unavailable action and the stable reason shown for it."""

    action: JobAction
    reason: str


@dataclass(frozen=True, slots=True)
class JobPresentation:
    """Immutable English copy and controls for one lifecycle state."""

    state_id: str
    label: str
    title: str
    body: str
    role: PresentationRole
    icon_token: str
    enabled_actions: tuple[JobAction, ...]
    disabled_action_reasons: tuple[DisabledActionReason, ...]
    support_reference: str | None = None


@dataclass(frozen=True, slots=True)
class _StateCopy:
    label: str
    title: str
    body: str
    role: PresentationRole
    icon_token: str


_STATE_COPY = {
    JobDisplayState.SUBMITTING: _StateCopy(
        label="Submitting",
        title="Submitting analysis",
        body="The analysis request is being checked before it enters the queue.",
        role=PresentationRole.STATUS,
        icon_token="loader-circle",
    ),
    JobDisplayState.STAGED: _StateCopy(
        label="Staged",
        title="Analysis staged",
        body="The validated request is being prepared for the analysis queue.",
        role=PresentationRole.STATUS,
        icon_token="layers",
    ),
    JobDisplayState.QUEUED: _StateCopy(
        label="Queued",
        title="Analysis queued",
        body=(
            "Analyses run one at a time. This analysis will start after the active "
            "analysis finishes."
        ),
        role=PresentationRole.STATUS,
        icon_token="clock-3",
    ),
    JobDisplayState.RUNNING: _StateCopy(
        label="Running",
        title="Analysis running",
        body="The analysis is running.",
        role=PresentationRole.STATUS,
        icon_token="activity",
    ),
    JobDisplayState.CANCELLING: _StateCopy(
        label="Cancelling",
        title="Cancellation requested",
        body=(
            "The cancellation request is being processed. The analysis remains active "
            "until cancellation is confirmed."
        ),
        role=PresentationRole.STATUS,
        icon_token="circle-slash-2",
    ),
    JobDisplayState.FINALIZING: _StateCopy(
        label="Finalizing",
        title="Finalizing analysis",
        body=(
            "The run finished. Temporary inputs are being removed before results become available."
        ),
        role=PresentationRole.STATUS,
        icon_token="shield-check",
    ),
    JobDisplayState.CLEANING: _StateCopy(
        label="Cleaning up",
        title="Removing temporary files",
        body="The run ended. Temporary server-file cleanup is still in progress.",
        role=PresentationRole.STATUS,
        icon_token="loader-circle",
    ),
    JobDisplayState.CLEANUP_FAILED: _StateCopy(
        label="Cleanup needs attention",
        title="Temporary-file removal is not confirmed",
        body=(
            "The run ended, but removal of its temporary server files could not be "
            "confirmed. Use the support reference if this message persists."
        ),
        role=PresentationRole.ALERT,
        icon_token="shield-alert",
    ),
    JobDisplayState.SUCCEEDED: _StateCopy(
        label="Succeeded",
        title="Analysis complete",
        body="The run completed and its temporary inputs were removed.",
        role=PresentationRole.STATUS,
        icon_token="circle-check",
    ),
    JobDisplayState.FAILED: _StateCopy(
        label="Failed",
        title="Analysis failed",
        body="The run ended before completion.",
        role=PresentationRole.ALERT,
        icon_token="triangle-alert",
    ),
    JobDisplayState.CANCELLED: _StateCopy(
        label="Cancelled",
        title="Analysis cancelled",
        body="Cancellation was confirmed. The run is no longer active.",
        role=PresentationRole.STATUS,
        icon_token="ban",
    ),
    JobDisplayState.TIMED_OUT: _StateCopy(
        label="Timed out",
        title="Analysis timed out",
        body="The run stopped because its execution window ended.",
        role=PresentationRole.ALERT,
        icon_token="timer-off",
    ),
    JobDisplayState.CRASHED: _StateCopy(
        label="Crashed",
        title="Analysis stopped unexpectedly",
        body="The run stopped after an internal execution error.",
        role=PresentationRole.ALERT,
        icon_token="server-crash",
    ),
    JobDisplayState.ABANDONED: _StateCopy(
        label="Ended",
        title="Analysis ended",
        body="The run ended before it could complete.",
        role=PresentationRole.ALERT,
        icon_token="circle-stop",
    ),
    JobDisplayState.EXPIRED: _StateCopy(
        label="Expired",
        title="Analysis expired",
        body="The server copy of this analysis was removed.",
        role=PresentationRole.ALERT,
        icon_token="archive-x",
    ),
    JobDisplayState.BUSY: _StateCopy(
        label="Busy",
        title="Another analysis is active",
        body="No analysis was started or stored. Another analysis is already active.",
        role=PresentationRole.ALERT,
        icon_token="lock-keyhole",
    ),
}

_ACTIVE_STATES = frozenset(
    {
        JobDisplayState.SUBMITTING,
        JobDisplayState.STAGED,
        JobDisplayState.QUEUED,
        JobDisplayState.RUNNING,
        JobDisplayState.CANCELLING,
        JobDisplayState.FINALIZING,
        JobDisplayState.CLEANING,
        JobDisplayState.CLEANUP_FAILED,
        JobDisplayState.BUSY,
    }
)
_CANCELLABLE_STATES = frozenset({JobDisplayState.QUEUED, JobDisplayState.RUNNING})
_RETRYABLE_FAILURE_STATES = frozenset(
    {JobDisplayState.FAILED, JobDisplayState.TIMED_OUT, JobDisplayState.CRASHED}
)
_SUPPORT_REFERENCE_PATTERN = re.compile(r"SUP-[A-Za-z0-9_-]{12}", flags=re.ASCII)


def _disabled_reason(
    action: JobAction,
    state: JobDisplayState,
    *,
    retryable_failure: bool,
) -> str:
    if action is JobAction.CANCEL:
        if state is JobDisplayState.CANCELLING:
            return "A cancellation request is already in progress."
        return "Cancellation is unavailable for this state."
    if action is JobAction.RETRY:
        if state in _RETRYABLE_FAILURE_STATES and retryable_failure:
            return "The source inputs are no longer available for retry."
        if state in _RETRYABLE_FAILURE_STATES:
            return "This failure cannot be retried."
        return "Retry is available only after a retryable failure."
    return "Start over is unavailable while an analysis is active."


def project_job_state(
    state: JobDisplayState,
    *,
    cleanup_confirmed: bool = False,
    retryable_failure: bool = False,
    input_lease_valid: bool = False,
    support_reference: str | None = None,
) -> JobPresentation:
    """Project trusted lifecycle facts into immutable, conservative UI content."""

    if state is JobDisplayState.SUCCEEDED and not cleanup_confirmed:
        raise ValueError("succeeded requires confirmed cleanup")
    if (
        support_reference is not None
        and _SUPPORT_REFERENCE_PATTERN.fullmatch(support_reference) is None
    ):
        raise ValueError("support_reference must be a canonical SUP reference")

    action_enabled = {
        JobAction.CANCEL: state in _CANCELLABLE_STATES,
        JobAction.RETRY: (
            state in _RETRYABLE_FAILURE_STATES and retryable_failure and input_lease_valid
        ),
        JobAction.START_OVER: state not in _ACTIVE_STATES,
    }
    enabled_actions = tuple(action for action in JobAction if action_enabled[action])
    disabled_action_reasons = tuple(
        DisabledActionReason(
            action=action,
            reason=_disabled_reason(
                action,
                state,
                retryable_failure=retryable_failure,
            ),
        )
        for action in JobAction
        if not action_enabled[action]
    )
    copy = _STATE_COPY[state]
    return JobPresentation(
        state_id=state.value,
        label=copy.label,
        title=copy.title,
        body=copy.body,
        role=copy.role,
        icon_token=copy.icon_token,
        enabled_actions=enabled_actions,
        disabled_action_reasons=disabled_action_reasons,
        support_reference=support_reference,
    )


def render_job_presentation_html(presentation: JobPresentation) -> str:
    """Render one payload-free lifecycle projection as an accessible status region."""

    live = "assertive" if presentation.role is PresentationRole.ALERT else "polite"
    support = ""
    if presentation.support_reference is not None:
        support = (
            '<p class="delta-job-support">Support reference: '
            f"<code>{html.escape(presentation.support_reference)}</code></p>"
        )
    return (
        f'<section class="delta-job-status" role="{presentation.role.value}" '
        f'aria-live="{live}" aria-atomic="true" '
        f'data-job-state="{html.escape(presentation.state_id)}">'
        f'<p class="delta-job-label">{html.escape(presentation.label)}</p>'
        f"<h2>{html.escape(presentation.title)}</h2>"
        f'<p class="delta-job-body">{html.escape(presentation.body)}</p>'
        f"{support}</section>"
    )


__all__ = [
    "DisabledActionReason",
    "JobAction",
    "JobDisplayState",
    "JobPresentation",
    "PresentationRole",
    "project_job_state",
    "render_job_presentation_html",
]
