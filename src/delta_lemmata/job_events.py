"""Allowlisted, content-free operational evidence for ephemeral jobs."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from delta_lemmata.clock import require_utc
from delta_lemmata.session_identity import JobId, workspace_component

MAX_EVENT_TTL_SECONDS = 7 * 24 * 60 * 60
JobReferenceDigest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class DeletionReason(StrEnum):
    STAGED_EXPIRED = "staged_expired"
    QUEUE_EXPIRED = "queue_expired"
    SUCCESSFUL_TERMINAL = "successful_terminal"
    UNSUCCESSFUL_TERMINAL = "unsuccessful_terminal"
    RESULT_EXPIRED = "result_expired"
    EXPORT_EXPIRED = "export_expired"
    OWNER_REQUEST = "owner_request"
    STARTUP_RECOVERY = "startup_recovery"


class DeletionEvent(BaseModel):
    """A bounded deletion fact that cannot carry scholarly or runtime payloads."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    event_code: Literal["JOB_ARTIFACTS_DELETED"] = "JOB_ARTIFACTS_DELETED"
    job_reference_digest: JobReferenceDigest
    occurred_at_utc: datetime
    reason: DeletionReason
    file_count: int = Field(ge=0)
    byte_count: int = Field(ge=0)
    policy_version: Literal["job-policy-v1"]
    expires_at_utc: datetime

    @field_validator("occurred_at_utc", "expires_at_utc")
    @classmethod
    def require_utc_timestamps(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def require_bounded_expiry(self) -> Self:
        lifetime = self.expires_at_utc - self.occurred_at_utc
        if lifetime <= timedelta(0) or lifetime > timedelta(seconds=MAX_EVENT_TTL_SECONDS):
            raise ValueError("deletion evidence must expire within seven days")
        return self


def new_deletion_event(
    *,
    job_id: JobId,
    occurred_at_utc: datetime,
    reason: DeletionReason,
    file_count: int,
    byte_count: int,
    policy_version: Literal["job-policy-v1"],
    event_ttl_seconds: int,
) -> DeletionEvent:
    """Create one deletion fact from typed, content-free values only."""

    occurred_at_utc = require_utc(occurred_at_utc, field_name="occurred_at_utc")
    if event_ttl_seconds <= 0 or event_ttl_seconds > MAX_EVENT_TTL_SECONDS:
        raise ValueError("event_ttl_seconds must be between one second and seven days")
    return DeletionEvent(
        job_reference_digest=workspace_component(job_id),
        occurred_at_utc=occurred_at_utc,
        reason=reason,
        file_count=file_count,
        byte_count=byte_count,
        policy_version=policy_version,
        expires_at_utc=occurred_at_utc + timedelta(seconds=event_ttl_seconds),
    )


__all__ = [
    "MAX_EVENT_TTL_SECONDS",
    "DeletionEvent",
    "DeletionReason",
    "new_deletion_event",
]
