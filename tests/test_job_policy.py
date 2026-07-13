from __future__ import annotations

import json
from math import inf

import pytest
from pydantic import ValidationError

from delta_lemmata.job_policy import (
    DEFAULT_JOB_POLICY,
    JobPolicy,
    WorkerLimitProfile,
    load_job_policy,
)


def test_default_job_policy_matches_p005_capacity_and_retention_contract() -> None:
    policy = DEFAULT_JOB_POLICY
    assert policy.profile_version == "job-policy-v1"
    assert (
        policy.max_running,
        policy.max_queued,
        policy.max_staged_global,
        policy.max_active_per_session,
    ) == (1, 3, 4, 1)
    assert (
        policy.staged_ttl_seconds,
        policy.result_ttl_seconds,
        policy.export_ttl_seconds,
    ) == (3600, 3600, 3600)
    assert policy.queued_ttl_seconds == 900
    assert policy.unsuccessful_payload_ttl_seconds == 900
    assert policy.event_ttl_seconds == 604800
    assert policy.tombstone_ttl_seconds == 604800
    assert policy.worker_limits.profile_version == "synthetic-worker-limits-v1"


def test_policy_loader_validates_json_data_instead_of_a_path() -> None:
    encoded = json.dumps(DEFAULT_JOB_POLICY.model_dump(mode="json"))
    assert load_job_policy(encoded) == DEFAULT_JOB_POLICY
    assert load_job_policy(encoded.encode("utf-8")) == DEFAULT_JOB_POLICY
    with pytest.raises(ValidationError):
        load_job_policy("/tmp/job-policy-v1.json")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_running", 0),
        ("max_queued", 0),
        ("max_staged_global", 0),
        ("max_active_per_session", 0),
        ("staged_ttl_seconds", 0),
        ("queued_ttl_seconds", 0),
        ("unsuccessful_payload_ttl_seconds", 0),
        ("result_ttl_seconds", 0),
        ("export_ttl_seconds", 0),
        ("event_ttl_seconds", 0),
        ("tombstone_ttl_seconds", 0),
    ],
)
def test_policy_rejects_non_positive_values(field: str, value: int) -> None:
    payload = DEFAULT_JOB_POLICY.model_dump(mode="python")
    payload[field] = value
    with pytest.raises(ValidationError):
        JobPolicy.model_validate(payload)


def test_policy_rejects_inconsistent_capacity_and_retention() -> None:
    payload = DEFAULT_JOB_POLICY.model_dump(mode="python")
    payload["max_active_per_session"] = 5
    with pytest.raises(ValidationError):
        JobPolicy.model_validate(payload)

    payload = DEFAULT_JOB_POLICY.model_dump(mode="python")
    payload["unsuccessful_payload_ttl_seconds"] = 3601
    with pytest.raises(ValidationError):
        JobPolicy.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_running", 2),
        ("max_queued", 4),
        ("max_staged_global", 5),
        ("max_active_per_session", 2),
        ("staged_ttl_seconds", 3601),
        ("queued_ttl_seconds", 901),
        ("unsuccessful_payload_ttl_seconds", 901),
        ("result_ttl_seconds", 3601),
        ("export_ttl_seconds", 3601),
        ("event_ttl_seconds", 604801),
        ("tombstone_ttl_seconds", 604801),
    ],
)
def test_v1_policy_rejects_positive_values_outside_the_versioned_contract(
    field: str, value: int
) -> None:
    payload = DEFAULT_JOB_POLICY.model_dump(mode="python")
    payload[field] = value
    with pytest.raises(ValidationError):
        JobPolicy.model_validate(payload)


@pytest.mark.parametrize(
    "mutation",
    [
        {"profile_version": "worker-limits-v1"},
        {"wall_time_seconds": 0},
        {"cpu_time_seconds": 0},
        {"memory_bytes": 0},
        {"max_processes": 0},
        {"terminate_grace_seconds": 0},
        {"wall_time_seconds": inf},
    ],
)
def test_worker_limit_profile_requires_finite_positive_complete_limits(
    mutation: dict[str, object],
) -> None:
    payload = DEFAULT_JOB_POLICY.worker_limits.model_dump(mode="python")
    payload.update(mutation)
    with pytest.raises(ValidationError):
        WorkerLimitProfile.model_validate(payload)


def test_worker_profile_version_allows_future_named_execution_engines() -> None:
    payload = DEFAULT_JOB_POLICY.worker_limits.model_dump(mode="python")
    payload["profile_version"] = "r-stylo-worker-limits-v1"
    assert WorkerLimitProfile.model_validate(payload).profile_version == payload["profile_version"]


def test_policy_models_are_closed_and_immutable() -> None:
    payload = DEFAULT_JOB_POLICY.model_dump(mode="python")
    payload["production_claim"] = True
    with pytest.raises(ValidationError):
        JobPolicy.model_validate(payload)
    with pytest.raises(ValidationError):
        WorkerLimitProfile.model_validate(
            {
                "profile_version": "synthetic-worker-limits-v1",
                "wall_time_seconds": 1,
                "cpu_time_seconds": 1,
                "memory_bytes": 1,
                "max_processes": 1,
            }
        )
    with pytest.raises(ValidationError):
        DEFAULT_JOB_POLICY.max_running = 2
