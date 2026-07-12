"""Versioned, packaged limits for the P005 job lifecycle."""

from __future__ import annotations

from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkerLimitProfile(BaseModel):
    """Finite limits required before any synthetic worker may start."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_version: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*-worker-limits-v[0-9]+$")
    wall_time_seconds: int = Field(gt=0)
    cpu_time_seconds: int = Field(gt=0)
    memory_bytes: int = Field(gt=0)
    max_processes: int = Field(gt=0)
    terminate_grace_seconds: int = Field(gt=0)


class JobPolicy(BaseModel):
    """Closed-world queue and retention policy loaded from package data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_version: Literal["job-policy-v1"]
    max_running: Literal[1]
    max_queued: Literal[3]
    max_staged_global: Literal[4]
    max_active_per_session: Literal[1]
    staged_ttl_seconds: Literal[3600]
    queued_ttl_seconds: Literal[900]
    unsuccessful_payload_ttl_seconds: Literal[900]
    result_ttl_seconds: Literal[3600]
    export_ttl_seconds: Literal[3600]
    event_ttl_seconds: Literal[604800]
    tombstone_ttl_seconds: Literal[604800]
    worker_limits: WorkerLimitProfile


def load_job_policy(raw_json: str | bytes) -> JobPolicy:
    """Validate an explicit JSON policy without accepting a filesystem path."""

    return JobPolicy.model_validate_json(raw_json)


DEFAULT_JOB_POLICY = load_job_policy(
    files("delta_lemmata").joinpath("data/job-policy-v1.json").read_text(encoding="utf-8")
)


__all__ = ["DEFAULT_JOB_POLICY", "JobPolicy", "WorkerLimitProfile", "load_job_policy"]
