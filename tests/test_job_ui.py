from __future__ import annotations

import re
from dataclasses import FrozenInstanceError

import pytest

from delta_lemmata.job_ui import (
    DisabledActionReason,
    JobAction,
    JobDisplayState,
    JobPresentation,
    PresentationRole,
    project_job_state,
)

JobState = JobDisplayState


def projection(state: JobDisplayState, **kwargs: bool | str | None) -> JobPresentation:
    if state is JobDisplayState.SUCCEEDED:
        kwargs["cleanup_confirmed"] = True
    return project_job_state(state, **kwargs)  # type: ignore[arg-type]


def all_copy(item: JobPresentation) -> str:
    reasons = " ".join(reason.reason for reason in item.disabled_action_reasons)
    return " ".join((item.label, item.title, item.body, reasons))


def test_every_state_has_a_stable_complete_projection() -> None:
    expected = {
        JobDisplayState.SUBMITTING: ("Submitting", PresentationRole.STATUS, "loader-circle"),
        JobDisplayState.STAGED: ("Staged", PresentationRole.STATUS, "layers"),
        JobDisplayState.QUEUED: ("Queued", PresentationRole.STATUS, "clock-3"),
        JobDisplayState.RUNNING: ("Running", PresentationRole.STATUS, "activity"),
        JobDisplayState.CANCELLING: ("Cancelling", PresentationRole.STATUS, "circle-slash-2"),
        JobDisplayState.SUCCEEDED: ("Succeeded", PresentationRole.STATUS, "circle-check"),
        JobDisplayState.FAILED: ("Failed", PresentationRole.ALERT, "triangle-alert"),
        JobDisplayState.CANCELLED: ("Cancelled", PresentationRole.STATUS, "ban"),
        JobDisplayState.TIMED_OUT: ("Timed out", PresentationRole.ALERT, "timer-off"),
        JobDisplayState.CRASHED: ("Crashed", PresentationRole.ALERT, "server-crash"),
        JobDisplayState.EXPIRED: ("Expired", PresentationRole.ALERT, "archive-x"),
        JobDisplayState.BUSY: ("Busy", PresentationRole.ALERT, "lock-keyhole"),
    }
    assert set(expected) == set(JobDisplayState)

    for state, (label, role, icon_token) in expected.items():
        item = projection(state)
        assert item.state_id == state.value
        assert item.label == label
        assert item.role is role
        assert item.icon_token == icon_token
        assert item.title
        assert item.body
        assert item.support_reference is None


def test_copy_is_conservative_and_contains_required_explanations() -> None:
    denylist = (
        r"\beta\b",
        r"\bpercent\b",
        r"\bpid\b",
        r"\br\b",
        r"\boom\b",
        r"\bttl\b",
        r"\bjanitor\b",
        r"full job id",
        r"\bconfidence\b",
        r"\bauthorship\b",
        r"scientific result",
    )
    for state in JobDisplayState:
        copy = all_copy(projection(state)).casefold()
        assert all(re.search(term, copy) is None for term in denylist)

    queued = projection(JobState.QUEUED).body.casefold()
    assert "one at a time" in queued
    cancelling = projection(JobState.CANCELLING).body.casefold()
    assert "remains active" in cancelling
    assert "cancelled" not in cancelling
    assert "deleted" not in cancelling
    assert "server copy" in projection(JobState.EXPIRED).body.casefold()
    busy = projection(JobState.BUSY).body.casefold()
    assert "no analysis was started or stored" in busy


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (JobState.SUBMITTING, ()),
        (JobState.STAGED, ()),
        (JobState.QUEUED, (JobAction.CANCEL,)),
        (JobState.RUNNING, (JobAction.CANCEL,)),
        (JobState.CANCELLING, ()),
        (JobState.SUCCEEDED, (JobAction.START_OVER,)),
        (JobState.FAILED, (JobAction.START_OVER,)),
        (JobState.CANCELLED, (JobAction.START_OVER,)),
        (JobState.TIMED_OUT, (JobAction.START_OVER,)),
        (JobState.CRASHED, (JobAction.START_OVER,)),
        (JobState.EXPIRED, (JobAction.START_OVER,)),
        (JobState.BUSY, ()),
    ],
)
def test_default_action_matrix(state: JobState, expected: tuple[JobAction, ...]) -> None:
    item = projection(state)
    assert item.enabled_actions == expected
    disabled = {reason.action: reason.reason for reason in item.disabled_action_reasons}
    assert set(item.enabled_actions).isdisjoint(disabled)
    assert set(item.enabled_actions) | set(disabled) == set(JobAction)
    assert all(disabled.values())


@pytest.mark.parametrize("state", [JobState.FAILED, JobState.TIMED_OUT, JobState.CRASHED])
def test_retry_requires_a_retryable_failure_and_valid_input_lease(state: JobState) -> None:
    not_retryable = projection(state, retryable_failure=False, input_lease_valid=True)
    assert JobAction.RETRY not in not_retryable.enabled_actions
    assert "cannot be retried" in next(
        reason.reason
        for reason in not_retryable.disabled_action_reasons
        if reason.action is JobAction.RETRY
    )

    lease_invalid = projection(state, retryable_failure=True, input_lease_valid=False)
    assert JobAction.RETRY not in lease_invalid.enabled_actions
    assert "no longer available" in next(
        reason.reason
        for reason in lease_invalid.disabled_action_reasons
        if reason.action is JobAction.RETRY
    )

    retryable = projection(state, retryable_failure=True, input_lease_valid=True)
    assert JobAction.RETRY in retryable.enabled_actions


def test_retry_flags_do_not_enable_retry_for_a_non_failure() -> None:
    item = projection(
        JobState.CANCELLED,
        retryable_failure=True,
        input_lease_valid=True,
    )
    assert JobAction.RETRY not in item.enabled_actions
    retry_reason = next(
        reason.reason for reason in item.disabled_action_reasons if reason.action is JobAction.RETRY
    )
    assert "only after a retryable failure" in retry_reason


def test_cancelling_has_specific_cancel_reason_and_start_over_is_blocked_when_active() -> None:
    cancelling = projection(JobState.CANCELLING)
    cancel_reason = next(
        reason.reason
        for reason in cancelling.disabled_action_reasons
        if reason.action is JobAction.CANCEL
    )
    assert cancel_reason == "A cancellation request is already in progress."

    for state in (
        JobState.SUBMITTING,
        JobState.STAGED,
        JobState.QUEUED,
        JobState.RUNNING,
        JobState.CANCELLING,
        JobState.BUSY,
    ):
        item = projection(state)
        assert JobAction.START_OVER not in item.enabled_actions


def test_model_and_nested_action_reasons_are_frozen() -> None:
    item = projection(JobState.FAILED)
    with pytest.raises(FrozenInstanceError):
        item.title = "Changed"
    with pytest.raises(FrozenInstanceError):
        item.disabled_action_reasons[0].reason = "Changed"
    assert isinstance(item.enabled_actions, tuple)
    assert isinstance(item.disabled_action_reasons, tuple)
    assert isinstance(item.disabled_action_reasons[0], DisabledActionReason)


@pytest.mark.parametrize("support_reference", ["SUP-AbCd12_-Ef34", "SUP-ABCDEFGHIJKL"])
def test_short_support_reference_is_preserved(support_reference: str) -> None:
    item = project_job_state(JobState.FAILED, support_reference=support_reference)
    assert item.support_reference == support_reference


@pytest.mark.parametrize(
    "support_reference",
    ["", "ABC123", "SUP-ABC12", "SUP-ABC!23DEFGHI", "SUP-" + "A" * 13],
)
def test_invalid_or_full_support_reference_is_rejected(support_reference: str) -> None:
    with pytest.raises(ValueError, match="support_reference"):
        project_job_state(JobState.FAILED, support_reference=support_reference)


def test_success_requires_cleanup_confirmation() -> None:
    with pytest.raises(ValueError, match="confirmed cleanup"):
        project_job_state(JobState.SUCCEEDED)

    succeeded = project_job_state(JobState.SUCCEEDED, cleanup_confirmed=True)
    assert succeeded.state_id == JobState.SUCCEEDED
    assert "temporary inputs were removed" in succeeded.body


def test_only_confirmed_terminal_states_claim_success_or_cancellation() -> None:
    for state in JobState:
        item = projection(state)
        copy = " ".join((item.label, item.title, item.body)).casefold()
        if state is JobState.SUCCEEDED:
            assert "completed" in copy
        else:
            assert "completed" not in copy
        if state is JobState.CANCELLED:
            assert "cancelled" in copy
        else:
            assert "cancelled" not in copy
