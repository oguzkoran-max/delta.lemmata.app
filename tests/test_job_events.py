from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from delta_lemmata.job_events import (
    MAX_EVENT_TTL_SECONDS,
    DeletionEvent,
    DeletionEventError,
    DeletionReason,
    new_deletion_event,
)
from delta_lemmata.session_identity import IDENTIFIER_BYTES, JobId

NOW = datetime(2026, 7, 12, 22, tzinfo=UTC)


def fixed_job() -> JobId:
    return JobId.generate(lambda size: b"j" * size)


def event() -> DeletionEvent:
    return new_deletion_event(
        job_id=fixed_job(),
        occurred_at_utc=NOW,
        reason=DeletionReason.STAGED_EXPIRED,
        file_count=3,
        byte_count=128,
        policy_version="job-policy-v1",
        event_ttl_seconds=MAX_EVENT_TTL_SECONDS,
    )


def test_deletion_event_is_content_free_bounded_and_immutable() -> None:
    item = event()
    encoded = item.model_dump_json()

    assert item.event_code == "JOB_ARTIFACTS_DELETED"
    assert item.expires_at_utc == NOW + timedelta(days=7)
    assert len(item.job_reference_digest) == 64
    assert fixed_job().to_urlsafe() not in encoded
    assert (b"j" * IDENTIFIER_BYTES).hex() not in encoded
    assert all(
        forbidden not in encoded.casefold()
        for forbidden in (
            "filename",
            "metadata",
            "absolute_path",
            "stdout",
            "stderr",
            "traceback",
            "corpus",
        )
    )
    with pytest.raises(ValidationError):
        item.file_count = 4


@pytest.mark.parametrize("reason", list(DeletionReason))
def test_every_deletion_reason_is_allowlisted(reason: DeletionReason) -> None:
    item = new_deletion_event(
        job_id=fixed_job(),
        occurred_at_utc=NOW,
        reason=reason,
        file_count=0,
        byte_count=0,
        policy_version="job-policy-v1",
        event_ttl_seconds=1,
    )
    assert item.reason is reason


@pytest.mark.parametrize("ttl", [0, -1, MAX_EVENT_TTL_SECONDS + 1])
def test_factory_rejects_event_retention_outside_the_closed_boundary(ttl: int) -> None:
    with pytest.raises(DeletionEventError, match="JOB_DELETION_EVENT_INVALID"):
        new_deletion_event(
            job_id=fixed_job(),
            occurred_at_utc=NOW,
            reason=DeletionReason.OWNER_REQUEST,
            file_count=0,
            byte_count=0,
            policy_version="job-policy-v1",
            event_ttl_seconds=ttl,
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"file_count": -1},
        {"byte_count": -1},
        {"policy_version": "job-policy-v2"},
        {"event_code": "JOB_DELETED"},
        {"job_reference_digest": "short"},
        {"occurred_at_utc": NOW.replace(tzinfo=None)},
        {"expires_at_utc": NOW},
        {"expires_at_utc": NOW + timedelta(days=7, seconds=1)},
        {"payload": "forbidden"},
    ],
)
def test_model_rejects_unbounded_malformed_or_payload_bearing_records(
    payload: dict[str, object],
) -> None:
    data = event().model_dump(mode="python")
    data.update(payload)
    with pytest.raises(DeletionEventError):
        DeletionEvent.model_validate(data)


def test_factory_rejects_non_utc_time() -> None:
    with pytest.raises(DeletionEventError, match="JOB_DELETION_EVENT_INVALID"):
        new_deletion_event(
            job_id=fixed_job(),
            occurred_at_utc=NOW.astimezone(timezone(timedelta(hours=3))),
            reason=DeletionReason.STARTUP_RECOVERY,
            file_count=0,
            byte_count=0,
            policy_version="job-policy-v1",
            event_ttl_seconds=1,
        )


@pytest.mark.parametrize("field", ["file_count", "byte_count", "policy_version"])
def test_malformed_factory_values_cannot_echo_canary(field: str) -> None:
    canary = "AC07_CANARY_PRIVATE_CORPUS"
    values: dict[str, object] = {
        "job_id": fixed_job(),
        "occurred_at_utc": NOW,
        "reason": DeletionReason.OWNER_REQUEST,
        "file_count": 0,
        "byte_count": 0,
        "policy_version": "job-policy-v1",
        "event_ttl_seconds": 1,
    }
    values[field] = canary
    with pytest.raises(DeletionEventError) as captured:
        new_deletion_event(**values)  # type: ignore[arg-type]
    assert str(captured.value) == "JOB_DELETION_EVENT_INVALID"
    assert canary not in str(captured.value)


def test_direct_model_validation_hides_canary_input() -> None:
    canary = "AC07_CANARY_PRIVATE_CORPUS"
    data = event().model_dump(mode="python")
    data["file_count"] = canary
    with pytest.raises(DeletionEventError) as captured:
        DeletionEvent.model_validate(data)
    assert str(captured.value) == "JOB_DELETION_EVENT_INVALID"
    assert canary not in str(captured.value)
    assert not hasattr(captured.value, "errors")
    assert not hasattr(captured.value, "json")
