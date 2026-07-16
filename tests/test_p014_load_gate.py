from __future__ import annotations

import copy
import importlib.util
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "scripts" / "p014_load_gate.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("p014_load_gate", GATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _utc(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _health(p95: float) -> dict[str, Any]:
    return {
        "samples": 20,
        "successes": 20,
        "body_ok": 20,
        "median_ms": 80.0,
        "p95_ms": p95,
        "max_ms": p95,
    }


def _summary(requests: int, p95: float) -> dict[str, Any]:
    return {
        "requests": requests,
        "status_counts": {"200": requests},
        "body_ok": requests,
        "median_ms": min(80.0, p95),
        "p95_ms": p95,
        "max_ms": p95,
    }


def _identity(value: str = "a") -> dict[str, str]:
    return {
        "machine_id_sha256": value * 64,
        "boot_id_sha256": "b" * 64,
        "kernel_release": "6.17.0-test",
    }


def _limits(role: str) -> dict[str, int]:
    return {
        "cpu_nano": GATE.CPU_NANO_LIMITS[role],
        "memory_bytes": GATE.MEMORY_LIMITS[role],
        "pids": GATE.PID_LIMITS[role],
    }


def _state(role: str) -> dict[str, Any]:
    identifier = "c" if role == "gateway" else "a"
    image = "d" if role == "gateway" else "b"
    return {
        "id": identifier * 64,
        "running": True,
        "oom_killed": False,
        "restart_count": 0,
        "image_id": "sha256:" + image * 64,
        "configured_limits": _limits(role),
    }


def _service() -> dict[str, Any]:
    return {
        "active_state": "active",
        "sub_state": "running",
        "restart_count": 0,
        "memory_bytes": 500_000_000,
        "start_monotonic_us": 100,
    }


def _baseline_listeners() -> list[dict[str, Any]]:
    return [
        {"address": "0.0.0.0", "port": 80},
        {"address": "127.0.0.1", "port": 8501},
    ]


def _current_listeners() -> list[dict[str, Any]]:
    return [
        *_baseline_listeners(),
        {"address": "127.0.0.1", "port": 8502},
    ]


def _evidence() -> dict[str, Any]:
    ended = datetime.now(UTC).replace(microsecond=0)
    started = ended - timedelta(seconds=60)
    baseline = started - timedelta(seconds=60)
    return {
        "schema_version": "1.2.0",
        "capture_mode": "live",
        "profile": "bounded-synthetic-stylo-coexistence-v3",
        "scope": {
            "load_class": "bounded-synthetic-analysis-coexistence",
            "scientific_validation": False,
            "maximum_capacity_validation": False,
            "content_free_aggregates_only": True,
        },
        "started_at_utc": _utc(started),
        "ended_at_utc": _utc(ended),
        "requested_duration_seconds": 60,
        "observed_duration_seconds": 60.0,
        "concurrency": 4,
        "request_interval_seconds": 0.2,
        "host_binding": {
            "host_gate_schema_version": "1.3.0",
            "baseline_phase": "pre-docker",
            "baseline_gate_passed": True,
            "baseline_captured_at_utc": _utc(baseline),
            "baseline_identity": _identity(),
            "identity_before": _identity(),
            "identity_after": _identity(),
            "baseline_listeners": _baseline_listeners(),
        },
        "analysis_workload": {
            "mechanism": GATE.ANALYSIS_MECHANISM,
            "fixture_id": GATE.FIXTURE_ID,
            "fixture_sha256": GATE.FIXTURE_SHA256,
            "fixture_byte_count": len(GATE.FIXTURE_PATH.read_bytes()),
            "admission_slot_exercised": True,
            "real_stylo_worker_exercised": True,
            "production_state_isolated": True,
            "scientific_validation": False,
            "content_retained": False,
            "outcome": "completed",
            "exit_code": 0,
            "duration_ms": 60_000.0,
            "success_marker_count": 2,
        },
        "delta_load": _summary(1200, 10.0),
        "lemmata": {
            "baseline": _health(100.0),
            "during_load": _summary(60, 120.0),
            "service_before": _service(),
            "service_after": _service(),
            "error_markers_during_load": 0,
        },
        "host": {
            "samples": 60,
            "minimum_available_mib": 512,
            "maximum_memory_full_avg10": 0.99,
            "oom_markers_before": 0,
            "oom_markers_after": 0,
            "listener_observation_count": 60,
            "listener_mismatch_count": 0,
            "listeners_after": _current_listeners(),
        },
        "containers": {
            "app": {
                "state_before": _state("app"),
                "state_after": _state("app"),
                "peaks": {
                    "cpu_percent": 150.0,
                    "memory_bytes": GATE.MEMORY_LIMITS["app"],
                    "pids": GATE.PID_LIMITS["app"],
                },
            },
            "gateway": {
                "state_before": _state("gateway"),
                "state_after": _state("gateway"),
                "peaks": {
                    "cpu_percent": 25.0,
                    "memory_bytes": GATE.MEMORY_LIMITS["gateway"],
                    "pids": GATE.PID_LIMITS["gateway"],
                },
            },
        },
        "delta_service_before": "active",
        "delta_service_after": "active",
    }


def test_bounded_analysis_gate_accepts_exact_frozen_boundaries() -> None:
    assert GATE.REQUIRED_HOST_GATE_SCHEMA_VERSION == "1.3.0"
    assert GATE.evaluate_evidence(_evidence()) == []


def test_gate_rejects_latency_capacity_listener_oom_and_runtime_regressions() -> None:
    value = copy.deepcopy(_evidence())
    value["lemmata"]["during_load"]["p95_ms"] = 120.001
    value["lemmata"]["during_load"]["max_ms"] = 120.001
    value["host"]["minimum_available_mib"] = 511
    value["host"]["maximum_memory_full_avg10"] = 1.0
    value["host"]["oom_markers_after"] = 1
    value["host"]["listener_mismatch_count"] = 1
    value["containers"]["app"]["state_after"]["restart_count"] = 1
    value["containers"]["gateway"]["peaks"]["pids"] = 65
    failures = GATE.evaluate_evidence(value)
    assert "P014_LOAD_LEMMATA_P95_BUDGET_EXCEEDED" in failures
    assert "P014_LOAD_HOST_CAPACITY_FAILED" in failures
    assert "P014_LOAD_HOST_OOM_OBSERVED" in failures
    assert "P014_LOAD_LISTENER_SET_INVALID" in failures
    assert "P014_LOAD_APP_STATE_FAILED" in failures
    assert "P014_LOAD_GATEWAY_LIMIT_FAILED" in failures


def test_gate_rejects_partial_observation_and_failed_requests() -> None:
    value = copy.deepcopy(_evidence())
    value["delta_load"]["requests"] = 10
    value["delta_load"]["status_counts"] = {"200": 9, "network-error": 1}
    value["delta_load"]["body_ok"] = 9
    value["lemmata"]["during_load"] = _summary(9, 100.0)
    value["host"]["samples"] = 9
    value["host"]["listener_observation_count"] = 9
    failures = GATE.evaluate_evidence(value)
    assert "P014_LOAD_DELTA_REQUEST_FAILED" in failures
    assert "P014_LOAD_DELTA_BODY_FAILED" in failures
    assert "P014_LOAD_LEMMATA_HEALTH_FAILED" in failures
    assert "P014_LOAD_OBSERVATION_INCOMPLETE" in failures


def test_gate_rejects_stale_or_different_host_and_boot() -> None:
    stale = copy.deepcopy(_evidence())
    ended = datetime.fromisoformat(stale["ended_at_utc"].replace("Z", "+00:00"))
    stale["host_binding"]["baseline_captured_at_utc"] = _utc(
        ended - timedelta(hours=2, microseconds=1)
    )
    assert "P014_LOAD_BASELINE_STALE" in GATE.evaluate_evidence(stale)

    changed = copy.deepcopy(_evidence())
    changed["host_binding"]["identity_after"] = _identity("e")
    assert "P014_LOAD_HOST_OR_BOOT_CHANGED" in GATE.evaluate_evidence(changed)


def test_gate_requires_exact_listener_set_including_no_disappearance() -> None:
    value = copy.deepcopy(_evidence())
    value["host"]["listeners_after"] = [
        item for item in value["host"]["listeners_after"] if item["port"] != 80
    ]
    assert "P014_LOAD_LISTENER_SET_INVALID" in GATE.evaluate_evidence(value)


def test_gate_enforces_configured_and_observed_cpu_limits() -> None:
    observed = copy.deepcopy(_evidence())
    observed["containers"]["app"]["peaks"]["cpu_percent"] = 150.001
    observed["containers"]["gateway"]["peaks"]["cpu_percent"] = 25.001
    failures = GATE.evaluate_evidence(observed)
    assert "P014_LOAD_APP_LIMIT_FAILED" in failures
    assert "P014_LOAD_GATEWAY_LIMIT_FAILED" in failures

    configured = copy.deepcopy(_evidence())
    configured["containers"]["app"]["state_before"]["configured_limits"]["cpu_nano"] += 1
    failures = GATE.evaluate_evidence(configured)
    assert "P014_LOAD_APP_LIMIT_CONFIGURATION_FAILED" in failures


@pytest.mark.parametrize(
    "location",
    ("root", "scope", "workload", "service", "container", "limits", "host"),
)
def test_closed_schema_rejects_unknown_fields_at_every_level(location: str) -> None:
    value = copy.deepcopy(_evidence())
    targets = {
        "root": value,
        "scope": value["scope"],
        "workload": value["analysis_workload"],
        "service": value["lemmata"]["service_before"],
        "container": value["containers"]["app"],
        "limits": value["containers"]["app"]["state_before"]["configured_limits"],
        "host": value["host"],
    }
    targets[location]["unexpected"] = 1
    assert GATE.evaluate_evidence(value) == ["P014_LOAD_EVIDENCE_INVALID"]


def test_emitted_gate_section_is_closed_and_consistent() -> None:
    value = _evidence()
    value["gate"] = {"passed": True, "failures": []}
    GATE._validate_evidence_shape(value, require_gate=True)

    invalid = copy.deepcopy(value)
    invalid["gate"]["unexpected"] = True
    with pytest.raises(GATE.LoadGateError, match="P014_LOAD_EVIDENCE_INVALID:gate"):
        GATE._validate_evidence_shape(invalid, require_gate=True)


def test_zero_sample_summaries_are_rejected_before_evaluation() -> None:
    value = copy.deepcopy(_evidence())
    value["lemmata"]["baseline"] = {
        "samples": 0,
        "successes": 0,
        "body_ok": 0,
        "median_ms": None,
        "p95_ms": None,
        "max_ms": None,
    }
    assert GATE.evaluate_evidence(value) == ["P014_LOAD_EVIDENCE_INVALID"]


@pytest.mark.parametrize("non_finite", (float("nan"), float("inf"), float("-inf")))
@pytest.mark.parametrize(
    "location",
    ("timing", "latency", "pressure", "cpu", "analysis"),
)
def test_all_non_finite_telemetry_is_rejected(location: str, non_finite: float) -> None:
    value = copy.deepcopy(_evidence())
    targets = {
        "timing": (value, "observed_duration_seconds"),
        "latency": (value["lemmata"]["during_load"], "p95_ms"),
        "pressure": (value["host"], "maximum_memory_full_avg10"),
        "cpu": (value["containers"]["app"]["peaks"], "cpu_percent"),
        "analysis": (value["analysis_workload"], "duration_ms"),
    }
    target, key = targets[location]
    target[key] = non_finite
    assert GATE.evaluate_evidence(value) == ["P014_LOAD_EVIDENCE_INVALID"]


@pytest.mark.parametrize(
    ("location", "key"),
    (
        ("host", "samples"),
        ("host", "minimum_available_mib"),
        ("workload", "success_marker_count"),
        ("service", "memory_bytes"),
        ("peaks", "pids"),
    ),
)
def test_negative_telemetry_is_rejected(location: str, key: str) -> None:
    value = copy.deepcopy(_evidence())
    targets = {
        "host": value["host"],
        "workload": value["analysis_workload"],
        "service": value["lemmata"]["service_before"],
        "peaks": value["containers"]["app"]["peaks"],
    }
    targets[location][key] = -1
    assert GATE.evaluate_evidence(value) == ["P014_LOAD_EVIDENCE_INVALID"]


def test_gate_rejects_worker_failure_or_overclaimed_scope() -> None:
    value = copy.deepcopy(_evidence())
    value["analysis_workload"]["outcome"] = "worker-failed"
    value["analysis_workload"]["exit_code"] = 23
    value["analysis_workload"]["admission_slot_exercised"] = False
    value["analysis_workload"]["real_stylo_worker_exercised"] = False
    assert "P014_LOAD_BOUNDED_ANALYSIS_FAILED" in GATE.evaluate_evidence(value)

    overclaimed = copy.deepcopy(_evidence())
    overclaimed["scope"]["scientific_validation"] = True
    assert "P014_LOAD_SCOPE_INVALID" in GATE.evaluate_evidence(overclaimed)


def test_gate_rejects_real_stylo_workload_shorter_than_observation_window() -> None:
    value = copy.deepcopy(_evidence())
    value["analysis_workload"]["duration_ms"] = 4_000.0
    value["analysis_workload"]["success_marker_count"] = 1
    assert "P014_LOAD_BOUNDED_ANALYSIS_FAILED" in GATE.evaluate_evidence(value)


def test_synthetic_workload_uses_fixed_fixture_and_real_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        captured["command"] = command
        captured["input"] = kwargs["input"]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(GATE.ANALYSIS_SUCCESS_MARKER + "\n").encode("ascii"),
            stderr=b"",
        )

    monkeypatch.setattr(GATE.subprocess, "run", fake_run)
    fixture = GATE._load_synthetic_fixture()
    result = GATE._run_synthetic_analysis_once("a" * 64, fixture)
    assert result["outcome"] == "completed"
    assert result["success_marker_count"] == 1
    assert captured["input"] == fixture
    assert "docker" == captured["command"][0]
    assert "/usr/bin/timeout" in captured["command"]
    assert "65s" in captured["command"]
    assert "scripts.validate_p006_scientific_handoff" in captured["command"][-1]


def test_synthetic_workload_repeats_real_handoff_for_the_full_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter((0, 20_000_000_000, 40_000_000_000, 60_000_000_000, 60_000_000_000))
    calls = 0

    def fake_clock() -> int:
        return next(clock)

    def fake_run(_container: str, _fixture: bytes) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {
            "outcome": "completed",
            "exit_code": 0,
            "duration_ms": 20_000.0,
            "success_marker_count": 1,
        }

    monkeypatch.setattr(GATE.time, "monotonic_ns", fake_clock)
    monkeypatch.setattr(GATE, "_run_synthetic_analysis_once", fake_run)
    fixture = GATE._load_synthetic_fixture()
    result = GATE._run_synthetic_analysis(
        "a" * 64,
        fixture,
        minimum_duration_seconds=60,
    )

    assert calls == 3
    assert result["outcome"] == "completed"
    assert result["success_marker_count"] == 3
    assert result["duration_ms"] == 60_000.0
    assert result["admission_slot_exercised"] is True
    assert result["real_stylo_worker_exercised"] is True
    assert result["scientific_validation"] is False
    assert result["content_retained"] is False
    assert result["fixture_sha256"] == GATE.FIXTURE_SHA256


def test_fixture_digest_is_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(GATE, "FIXTURE_SHA256", "0" * 64)
    with pytest.raises(GATE.LoadGateError, match="P014_LOAD_SYNTHETIC_FIXTURE_INVALID"):
        GATE._load_synthetic_fixture()


def test_cli_exposes_only_bounded_live_collection() -> None:
    completed = subprocess.run(
        [sys.executable, str(GATE_PATH), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "--duration-seconds" in completed.stdout
    assert "--snapshot" not in completed.stdout
    assert "--evidence" not in completed.stdout
    rejected = subprocess.run(
        [
            sys.executable,
            str(GATE_PATH),
            "--host-baseline",
            "/tmp/pre.json",
            "--app",
            "a" * 64,
            "--gateway",
            "b" * 64,
            "--output",
            "/tmp/load.json",
            "--duration-seconds",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode == 2
    assert "--duration-seconds must be between 30 and 300" in rejected.stderr
