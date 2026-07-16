#!/usr/bin/env python3
"""Run a bounded synthetic stylo coexistence load and emit content-free evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

SCHEMA_VERSION = "1.2.0"
REQUIRED_HOST_GATE_SCHEMA_VERSION = "1.3.0"
PROFILE = "bounded-synthetic-stylo-coexistence-v3"
DELTA_URL = "http://127.0.0.1:8502/_stcore/health"
DELTA_HOST = "delta.lemmata.app"
CONTAINER_RE = re.compile(r"^[0-9a-f]{12,64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HTTP_STATUS_RE = re.compile(r"^(?:[1-5][0-9]{2}|network-error)$")
MEMORY_LIMITS = {"app": 1536 * 1024 * 1024, "gateway": 128 * 1024 * 1024}
PID_LIMITS = {"app": 128, "gateway": 64}
CPU_NANO_LIMITS = {"app": 1_500_000_000, "gateway": 250_000_000}
CPU_PERCENT_LIMITS = {"app": 150.0, "gateway": 25.0}
BASELINE_MAX_AGE_SECONDS = 2 * 60 * 60
ANALYSIS_TIMEOUT_SECONDS = 70
ANALYSIS_SUCCESS_MARKER = "p014-bounded-stylo-analysis-ok"
ANALYSIS_MECHANISM = "isolated-p006-scientific-handoff-loop-v1"
FIXTURE_ID = "p006-whole-text-v2/normalization-base"
FIXTURE_SHA256 = "3d2f24d47dbfdab20cbaa0fb767503039cbd4bd642f7a2f4e95f275e932ce8cf"
FIXTURE_BYTE_COUNT = 5003
FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "stylo"
    / "p006-whole-text-v2"
    / "normalization-base.input.json"
)
EXPECTED_DELTA_LISTENER = ("127.0.0.1", 8502)
ANALYSIS_HARNESS = r"""
import os
import sys
import tempfile
from pathlib import Path

import scripts.validate_p006_scientific_handoff as handoff

descriptor, raw_path = tempfile.mkstemp(
    prefix="p014-bounded-stylo-",
    suffix=".input.json",
    dir="/tmp",
)
path = Path(raw_path)
try:
    with os.fdopen(descriptor, "wb") as handle:
        payload = sys.stdin.buffer.read(1_000_001)
        if not payload or len(payload) > 1_000_000:
            raise ValueError("P014_SYNTHETIC_FIXTURE_SIZE_INVALID")
        handle.write(payload)
    os.chmod(path, 0o600)
    handoff.REQUEST_PATH = path
    handoff.validate_scientific_handoff()
except Exception:
    print("p014-bounded-stylo-analysis-failed", file=sys.stderr)
    raise SystemExit(23) from None
finally:
    path.unlink(missing_ok=True)
print("p014-bounded-stylo-analysis-ok")
""".strip()


class LoadGateError(RuntimeError):
    """Raised when bounded live measurement cannot be completed safely."""


def _load_host_gate():
    path = Path(__file__).with_name("p014_host_gate.py")
    spec = importlib.util.spec_from_file_location("p014_host_gate", path)
    if spec is None or spec.loader is None:
        raise LoadGateError("P014_LOAD_HOST_GATE_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HOST_GATE = _load_host_gate()


def _run(command: list[str], *, timeout: float = 20.0) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["LC_ALL"] = "C"
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LoadGateError(f"P014_LOAD_COMMAND_FAILED:{command[0]}") from exc


def _required_stdout(command: list[str], *, timeout: float = 20.0) -> str:
    completed = _run(command, timeout=timeout)
    if completed.returncode != 0:
        raise LoadGateError(f"P014_LOAD_COMMAND_NONZERO:{command[0]}")
    return completed.stdout.strip()


def _request_once(url: str, *, host: str | None) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={} if host is None else {"Host": host})
    started = time.monotonic_ns()
    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            payload = response.read(16)
            status: int | None = response.status
    except (urllib.error.URLError, TimeoutError, OSError):
        payload = b""
        status = None
    return {
        "status": status,
        "body_ok": payload.strip() == b"ok",
        "duration_ms": round((time.monotonic_ns() - started) / 1_000_000, 3),
    }


def _summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    durations = sorted(float(item["duration_ms"]) for item in samples)
    p95_index = max(0, math.ceil(0.95 * len(durations)) - 1) if durations else 0
    status_counts: dict[str, int] = {}
    for item in samples:
        key = "network-error" if item["status"] is None else str(item["status"])
        status_counts[key] = status_counts.get(key, 0) + 1
    return {
        "requests": len(samples),
        "status_counts": dict(sorted(status_counts.items())),
        "body_ok": sum(bool(item["body_ok"]) for item in samples),
        "median_ms": round(statistics.median(durations), 3) if durations else None,
        "p95_ms": round(durations[p95_index], 3) if durations else None,
        "max_ms": round(max(durations), 3) if durations else None,
    }


def _parse_size(value: str) -> int:
    token = value.strip().split()[0]
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([A-Za-z]+)", token)
    if match is None:
        raise LoadGateError("P014_LOAD_DOCKER_SIZE_INVALID")
    amount = float(match.group(1))
    factors = {
        "B": 1,
        "kB": 1000,
        "KB": 1000,
        "KiB": 1024,
        "MB": 1000**2,
        "MiB": 1024**2,
        "GB": 1000**3,
        "GiB": 1024**3,
    }
    try:
        result = amount * factors[match.group(2)]
    except KeyError as exc:
        raise LoadGateError("P014_LOAD_DOCKER_SIZE_INVALID") from exc
    if not math.isfinite(result):
        raise LoadGateError("P014_LOAD_DOCKER_SIZE_INVALID")
    return int(result)


def _container_state(container: str) -> dict[str, Any]:
    output = _required_stdout(
        [
            "docker",
            "inspect",
            "--format",
            (
                "{{.Id}}\t{{.State.Running}}\t{{.State.OOMKilled}}\t"
                "{{.RestartCount}}\t{{.Image}}\t{{.HostConfig.NanoCpus}}\t"
                "{{.HostConfig.Memory}}\t{{.HostConfig.PidsLimit}}"
            ),
            container,
        ]
    )
    fields = output.split("\t")
    if (
        len(fields) != 8
        or CONTAINER_RE.fullmatch(fields[0]) is None
        or not fields[0].startswith(container)
    ):
        raise LoadGateError("P014_LOAD_CONTAINER_STATE_INVALID")
    return {
        "id": fields[0],
        "running": fields[1] == "true",
        "oom_killed": fields[2] == "true",
        "restart_count": int(fields[3]),
        "image_id": fields[4],
        "configured_limits": {
            "cpu_nano": int(fields[5]),
            "memory_bytes": int(fields[6]),
            "pids": int(fields[7]),
        },
    }


def _container_stats(containers: dict[str, str]) -> dict[str, dict[str, float | int]]:
    output = _required_stdout(
        [
            "docker",
            "stats",
            "--no-stream",
            "--format",
            "{{json .}}",
            containers["app"],
            containers["gateway"],
        ],
        timeout=30.0,
    )
    result: dict[str, dict[str, float | int]] = {}
    for line in output.splitlines():
        value = json.loads(
            line,
            parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
        )
        identifier = str(value["ID"])
        matches = [name for name, expected in containers.items() if expected.startswith(identifier)]
        if len(matches) != 1:
            raise LoadGateError("P014_LOAD_CONTAINER_STATS_UNEXPECTED")
        role = matches[0]
        cpu_percent = float(str(value["CPUPerc"]).rstrip("%"))
        if not math.isfinite(cpu_percent) or cpu_percent < 0:
            raise LoadGateError("P014_LOAD_CONTAINER_STATS_INVALID")
        result[role] = {
            "cpu_percent": cpu_percent,
            "memory_bytes": _parse_size(str(value["MemUsage"]).split("/", maxsplit=1)[0]),
            "pids": int(value["PIDs"]),
        }
    if set(result) != {"app", "gateway"}:
        raise LoadGateError("P014_LOAD_CONTAINER_STATS_INCOMPLETE")
    return result


def _service_error_count(since: str) -> int:
    output = _required_stdout(
        ["journalctl", "-u", "lemmata", "--since", since, "--no-pager", "--quiet"]
    )
    markers = ("error", "traceback", "exception", "failed")
    return sum(1 for line in output.lower().splitlines() if any(item in line for item in markers))


def _load_synthetic_fixture() -> bytes:
    try:
        resolved = FIXTURE_PATH.resolve(strict=True)
        payload = resolved.read_bytes()
    except OSError as exc:
        raise LoadGateError("P014_LOAD_SYNTHETIC_FIXTURE_UNAVAILABLE") from exc
    if (
        resolved != FIXTURE_PATH
        or len(payload) != FIXTURE_BYTE_COUNT
        or hashlib.sha256(payload).hexdigest() != FIXTURE_SHA256
    ):
        raise LoadGateError("P014_LOAD_SYNTHETIC_FIXTURE_INVALID")
    return payload


def _run_synthetic_analysis_once(container: str, fixture: bytes) -> dict[str, Any]:
    command = [
        "docker",
        "exec",
        "--interactive",
        "--user",
        "10001:10001",
        "--workdir",
        "/opt/delta",
        container,
        "/usr/bin/timeout",
        "--signal=TERM",
        "--kill-after=5s",
        "65s",
        "/opt/delta/.venv/bin/python",
        "-c",
        ANALYSIS_HARNESS,
    ]
    environment = dict(os.environ)
    environment["LC_ALL"] = "C"
    started = time.monotonic_ns()
    try:
        completed = subprocess.run(
            command,
            input=fixture,
            check=False,
            capture_output=True,
            timeout=ANALYSIS_TIMEOUT_SECONDS,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        outcome = "timeout"
        exit_code = -1
        marker_count = 0
    except OSError:
        outcome = "command-error"
        exit_code = -1
        marker_count = 0
    else:
        marker = ANALYSIS_SUCCESS_MARKER.encode("ascii")
        lines = completed.stdout.strip().splitlines()
        marker_count = sum(line == marker for line in lines)
        exit_code = completed.returncode
        outcome = (
            "completed" if completed.returncode == 0 and lines == [marker] else "worker-failed"
        )
    duration_ms = max(round((time.monotonic_ns() - started) / 1_000_000, 3), 0.001)
    return {
        "outcome": outcome,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "success_marker_count": marker_count,
    }


def _run_synthetic_analysis(
    container: str,
    fixture: bytes,
    *,
    minimum_duration_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic_ns()
    deadline = started + minimum_duration_seconds * 1_000_000_000
    runs: list[dict[str, Any]] = []
    while not runs or time.monotonic_ns() < deadline:
        run = _run_synthetic_analysis_once(container, fixture)
        runs.append(run)
        if run["outcome"] != "completed":
            break

    duration_ms = max(round((time.monotonic_ns() - started) / 1_000_000, 3), 0.001)
    marker_count = sum(int(run["success_marker_count"]) for run in runs)
    completed_ok = (
        all(run["outcome"] == "completed" for run in runs)
        and duration_ms >= minimum_duration_seconds * 1000
        and marker_count == len(runs)
    )
    return {
        "mechanism": ANALYSIS_MECHANISM,
        "fixture_id": FIXTURE_ID,
        "fixture_sha256": hashlib.sha256(fixture).hexdigest(),
        "fixture_byte_count": len(fixture),
        "admission_slot_exercised": completed_ok,
        "real_stylo_worker_exercised": completed_ok,
        "production_state_isolated": True,
        "scientific_validation": False,
        "content_retained": False,
        "outcome": "completed" if completed_ok else str(runs[-1]["outcome"]),
        "exit_code": 0 if completed_ok else int(runs[-1]["exit_code"]),
        "duration_ms": duration_ms,
        "success_marker_count": marker_count,
    }


def _gateway_worker(
    *,
    deadline: float,
    interval: float,
    samples: list[dict[str, Any]],
    lock: threading.Lock,
) -> None:
    while time.monotonic() < deadline:
        started = time.monotonic()
        sample = _request_once(DELTA_URL, host=DELTA_HOST)
        with lock:
            samples.append(sample)
        remaining = interval - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)


def _observe(
    *,
    deadline: float,
    containers: dict[str, str],
    expected_listeners: set[tuple[str, int]],
    lemmata_samples: list[dict[str, Any]],
    host_samples: list[dict[str, Any]],
    container_samples: list[dict[str, Any]],
) -> None:
    while time.monotonic() < deadline:
        started = time.monotonic()
        lemmata_samples.append(_request_once(HOST_GATE.LEMMATA_URL, host=None))
        observed_listeners = {
            (str(item["address"]), int(item["port"])) for item in HOST_GATE._listeners()
        }
        host_samples.append(
            {
                "memory": HOST_GATE._read_meminfo(),
                "pressure": HOST_GATE._read_pressure(),
                "listeners_match": observed_listeners == expected_listeners,
            }
        )
        container_samples.append(_container_stats(containers))
        remaining = 1.0 - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)


def _isoformat(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _timestamp(value: Any, path: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise LoadGateError(f"P014_LOAD_EVIDENCE_INVALID:{path}")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LoadGateError(f"P014_LOAD_EVIDENCE_INVALID:{path}") from exc
    if parsed.tzinfo != UTC:
        raise LoadGateError(f"P014_LOAD_EVIDENCE_INVALID:{path}")
    return parsed


def _identity_copy(value: dict[str, Any]) -> dict[str, str]:
    return {
        "machine_id_sha256": str(value["machine_id_sha256"]),
        "boot_id_sha256": str(value["boot_id_sha256"]),
        "kernel_release": str(value["kernel_release"]),
    }


def _listener_rows(value: set[tuple[str, int]]) -> list[dict[str, str | int]]:
    return [{"address": address, "port": port} for address, port in sorted(value)]


def _preflight_host_binding(
    baseline: dict[str, Any],
) -> tuple[dict[str, Any], set[tuple[str, int]]]:
    if HOST_GATE.SCHEMA_VERSION != REQUIRED_HOST_GATE_SCHEMA_VERSION:
        raise LoadGateError("P014_LOAD_HOST_GATE_SCHEMA_UNSUPPORTED")
    HOST_GATE._validate_snapshot_shape(baseline, require_gate=True)
    identity = _identity_copy(HOST_GATE._identity())
    started = datetime.now(UTC)
    baseline_time = _timestamp(baseline["captured_at_utc"], "host_binding.baseline_captured_at_utc")
    age = (started - baseline_time).total_seconds()
    if (
        baseline["phase"] != "pre-docker"
        or baseline["gate"]["passed"] is not True
        or baseline["host"]["identity"] != identity
        or age < 0
        or age > BASELINE_MAX_AGE_SECONDS
    ):
        raise LoadGateError("P014_LOAD_BASELINE_BINDING_FAILED")
    baseline_listeners = HOST_GATE._listener_set(baseline)
    expected_listeners = set(baseline_listeners)
    expected_listeners.add(EXPECTED_DELTA_LISTENER)
    current_listeners = {
        (str(item["address"]), int(item["port"])) for item in HOST_GATE._listeners()
    }
    if current_listeners != expected_listeners:
        raise LoadGateError("P014_LOAD_LISTENER_PREFLIGHT_FAILED")
    return (
        {
            "host_gate_schema_version": REQUIRED_HOST_GATE_SCHEMA_VERSION,
            "baseline_phase": "pre-docker",
            "baseline_gate_passed": True,
            "baseline_captured_at_utc": baseline["captured_at_utc"],
            "baseline_identity": _identity_copy(baseline["host"]["identity"]),
            "identity_before": identity,
            "identity_after": identity,
            "baseline_listeners": _listener_rows(baseline_listeners),
        },
        expected_listeners,
    )


def collect_evidence(
    *,
    baseline: dict[str, Any],
    containers: dict[str, str],
    duration_seconds: int,
    concurrency: int,
    request_interval_seconds: float,
) -> dict[str, Any]:
    host_binding, expected_listeners = _preflight_host_binding(baseline)
    fixture = _load_synthetic_fixture()
    started_at = datetime.now(UTC)
    started_text = _isoformat(started_at)
    lemmata_before = HOST_GATE._lemmata_properties()
    delta_service_before = HOST_GATE._service_state("delta-public-alpha")
    delta_state_before = {name: _container_state(value) for name, value in containers.items()}
    oom_before = HOST_GATE._kernel_oom_count()
    baseline_health = HOST_GATE._http_probe(
        HOST_GATE.LEMMATA_URL,
        host=None,
        samples=20,
    )
    if not HOST_GATE._complete_health(baseline_health):
        raise LoadGateError("P014_LOAD_BASELINE_HEALTH_FAILED")

    delta_samples: list[dict[str, Any]] = []
    lemmata_samples: list[dict[str, Any]] = []
    host_samples: list[dict[str, Any]] = []
    container_samples: list[dict[str, Any]] = []
    lock = threading.Lock()
    deadline = time.monotonic() + duration_seconds
    with ThreadPoolExecutor(max_workers=concurrency + 2) as executor:
        gateway_futures = [
            executor.submit(
                _gateway_worker,
                deadline=deadline,
                interval=request_interval_seconds,
                samples=delta_samples,
                lock=lock,
            )
            for _ in range(concurrency)
        ]
        observer_future = executor.submit(
            _observe,
            deadline=deadline,
            containers=containers,
            expected_listeners=expected_listeners,
            lemmata_samples=lemmata_samples,
            host_samples=host_samples,
            container_samples=container_samples,
        )
        analysis_future = executor.submit(
            _run_synthetic_analysis,
            containers["app"],
            fixture,
            minimum_duration_seconds=duration_seconds,
        )
        analysis_workload = analysis_future.result()
        for future in gateway_futures:
            future.result()
        observer_future.result()

    ended_at = datetime.now(UTC)
    lemmata_after = HOST_GATE._lemmata_properties()
    delta_service_after = HOST_GATE._service_state("delta-public-alpha")
    delta_state_after = {name: _container_state(value) for name, value in containers.items()}
    oom_after = HOST_GATE._kernel_oom_count()
    listeners_after = {(str(item["address"]), int(item["port"])) for item in HOST_GATE._listeners()}
    host_binding["identity_after"] = _identity_copy(HOST_GATE._identity())
    peaks: dict[str, dict[str, float | int]] = {}
    if not container_samples or not host_samples:
        raise LoadGateError("P014_LOAD_OBSERVATION_EMPTY")
    for role in ("app", "gateway"):
        rows = [sample[role] for sample in container_samples]
        peaks[role] = {
            "cpu_percent": max(float(row["cpu_percent"]) for row in rows),
            "memory_bytes": max(int(row["memory_bytes"]) for row in rows),
            "pids": max(int(row["pids"]) for row in rows),
        }
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "capture_mode": "live",
        "profile": PROFILE,
        "scope": {
            "load_class": "bounded-synthetic-analysis-coexistence",
            "scientific_validation": False,
            "maximum_capacity_validation": False,
            "content_free_aggregates_only": True,
        },
        "started_at_utc": started_text,
        "ended_at_utc": _isoformat(ended_at),
        "requested_duration_seconds": duration_seconds,
        "observed_duration_seconds": round((ended_at - started_at).total_seconds(), 3),
        "concurrency": concurrency,
        "request_interval_seconds": request_interval_seconds,
        "host_binding": host_binding,
        "analysis_workload": analysis_workload,
        "delta_load": _summary(delta_samples),
        "lemmata": {
            "baseline": baseline_health,
            "during_load": _summary(lemmata_samples),
            "service_before": lemmata_before,
            "service_after": lemmata_after,
            "error_markers_during_load": _service_error_count(started_text),
        },
        "host": {
            "samples": len(host_samples),
            "minimum_available_mib": min(
                int(sample["memory"]["available_mib"]) for sample in host_samples
            ),
            "maximum_memory_full_avg10": max(
                float(sample["pressure"]["full_avg10"]) for sample in host_samples
            ),
            "oom_markers_before": oom_before,
            "oom_markers_after": oom_after,
            "listener_observation_count": len(host_samples),
            "listener_mismatch_count": sum(
                not bool(sample["listeners_match"]) for sample in host_samples
            ),
            "listeners_after": _listener_rows(listeners_after),
        },
        "containers": {
            role: {
                "state_before": delta_state_before[role],
                "state_after": delta_state_after[role],
                "peaks": peaks[role],
            }
            for role in ("app", "gateway")
        },
        "delta_service_before": delta_service_before,
        "delta_service_after": delta_service_after,
    }
    return evidence


def _invalid(path: str) -> NoReturn:
    raise LoadGateError(f"P014_LOAD_EVIDENCE_INVALID:{path}")


def _reject_non_finite(value: Any, path: str = "root") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _invalid(path)
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                _invalid(path)
            _reject_non_finite(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_non_finite(item, f"{path}[{index}]")


def _exact_mapping(value: Any, keys: set[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        _invalid(path)
    return value


def _integer(value: Any, path: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _invalid(path)
    if minimum is not None and value < minimum:
        _invalid(path)
    return value


def _number(value: Any, path: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _invalid(path)
    parsed = float(value)
    if not math.isfinite(parsed) or (minimum is not None and parsed < minimum):
        _invalid(path)
    return parsed


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        _invalid(path)
    return value


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _invalid(path)
    return value


def _validate_identity(value: Any, path: str) -> None:
    identity = _exact_mapping(
        value,
        {"machine_id_sha256", "boot_id_sha256", "kernel_release"},
        path,
    )
    for key in ("machine_id_sha256", "boot_id_sha256"):
        if not isinstance(identity[key], str) or SHA256_RE.fullmatch(identity[key]) is None:
            _invalid(f"{path}.{key}")
    _string(identity["kernel_release"], f"{path}.kernel_release")


def _validate_listeners(value: Any, path: str) -> set[tuple[str, int]]:
    if not isinstance(value, list):
        _invalid(path)
    result: set[tuple[str, int]] = set()
    for index, item in enumerate(value):
        listener = _exact_mapping(item, {"address", "port"}, f"{path}[{index}]")
        address = _string(listener["address"], f"{path}[{index}].address")
        port = _integer(listener["port"], f"{path}[{index}].port", minimum=1)
        if port > 65535 or (address, port) in result:
            _invalid(f"{path}[{index}]")
        result.add((address, port))
    if value != _listener_rows(result):
        _invalid(path)
    return result


def _validate_timing_summary(value: Any, path: str, *, health: bool) -> None:
    count_key = "samples" if health else "requests"
    keys = {
        count_key,
        "body_ok",
        "median_ms",
        "p95_ms",
        "max_ms",
    }
    if health:
        keys.add("successes")
    else:
        keys.add("status_counts")
    summary = _exact_mapping(value, keys, path)
    count = _integer(summary[count_key], f"{path}.{count_key}", minimum=1)
    body_ok = _integer(summary["body_ok"], f"{path}.body_ok", minimum=0)
    if body_ok > count:
        _invalid(f"{path}.body_ok")
    if health:
        successes = _integer(summary["successes"], f"{path}.successes", minimum=0)
        if successes > count:
            _invalid(f"{path}.successes")
    else:
        status_counts = summary["status_counts"]
        if not isinstance(status_counts, dict):
            _invalid(f"{path}.status_counts")
        total = 0
        for key, raw_count in status_counts.items():
            if not isinstance(key, str) or HTTP_STATUS_RE.fullmatch(key) is None:
                _invalid(f"{path}.status_counts")
            total += _integer(raw_count, f"{path}.status_counts.{key}", minimum=0)
        if total != count:
            _invalid(f"{path}.status_counts")
    timings = [summary[key] for key in ("median_ms", "p95_ms", "max_ms")]
    if any(item is None for item in timings):
        _invalid(path)
    median, p95, maximum = (
        _number(item, f"{path}.{key}", minimum=0)
        for item, key in zip(timings, ("median_ms", "p95_ms", "max_ms"), strict=True)
    )
    if median > maximum or p95 > maximum:
        _invalid(path)


def _validate_service(value: Any, path: str) -> None:
    service = _exact_mapping(
        value,
        {"active_state", "sub_state", "restart_count", "memory_bytes", "start_monotonic_us"},
        path,
    )
    _string(service["active_state"], f"{path}.active_state")
    _string(service["sub_state"], f"{path}.sub_state")
    for key in ("restart_count", "memory_bytes", "start_monotonic_us"):
        _integer(service[key], f"{path}.{key}", minimum=0)


def _validate_container_state(value: Any, path: str) -> None:
    state = _exact_mapping(
        value,
        {
            "id",
            "running",
            "oom_killed",
            "restart_count",
            "image_id",
            "configured_limits",
        },
        path,
    )
    if not isinstance(state["id"], str) or CONTAINER_RE.fullmatch(state["id"]) is None:
        _invalid(f"{path}.id")
    if (
        not isinstance(state["image_id"], str)
        or not state["image_id"].startswith("sha256:")
        or SHA256_RE.fullmatch(state["image_id"][7:]) is None
    ):
        _invalid(f"{path}.image_id")
    _boolean(state["running"], f"{path}.running")
    _boolean(state["oom_killed"], f"{path}.oom_killed")
    _integer(state["restart_count"], f"{path}.restart_count", minimum=0)
    limits = _exact_mapping(
        state["configured_limits"],
        {"cpu_nano", "memory_bytes", "pids"},
        f"{path}.configured_limits",
    )
    for key in limits:
        _integer(limits[key], f"{path}.configured_limits.{key}", minimum=1)


def _validate_evidence_shape(evidence: Any, *, require_gate: bool | None = None) -> None:
    _reject_non_finite(evidence)
    root_keys = {
        "schema_version",
        "capture_mode",
        "profile",
        "scope",
        "started_at_utc",
        "ended_at_utc",
        "requested_duration_seconds",
        "observed_duration_seconds",
        "concurrency",
        "request_interval_seconds",
        "host_binding",
        "analysis_workload",
        "delta_load",
        "lemmata",
        "host",
        "containers",
        "delta_service_before",
        "delta_service_after",
    }
    if not isinstance(evidence, dict):
        _invalid("root")
    has_gate = "gate" in evidence
    if require_gate is True and not has_gate:
        _invalid("gate")
    if require_gate is False and has_gate:
        _invalid("gate")
    root = _exact_mapping(evidence, root_keys | ({"gate"} if has_gate else set()), "root")
    if (
        root["schema_version"] != SCHEMA_VERSION
        or root["capture_mode"] != "live"
        or root["profile"] != PROFILE
    ):
        _invalid("profile")
    scope = _exact_mapping(
        root["scope"],
        {
            "load_class",
            "scientific_validation",
            "maximum_capacity_validation",
            "content_free_aggregates_only",
        },
        "scope",
    )
    if scope["load_class"] != "bounded-synthetic-analysis-coexistence":
        _invalid("scope.load_class")
    for key in (
        "scientific_validation",
        "maximum_capacity_validation",
        "content_free_aggregates_only",
    ):
        _boolean(scope[key], f"scope.{key}")
    started = _timestamp(root["started_at_utc"], "started_at_utc")
    ended = _timestamp(root["ended_at_utc"], "ended_at_utc")
    if ended < started:
        _invalid("ended_at_utc")
    _integer(root["requested_duration_seconds"], "requested_duration_seconds", minimum=1)
    observed = _number(root["observed_duration_seconds"], "observed_duration_seconds", minimum=0)
    if abs((ended - started).total_seconds() - observed) > 5.0:
        _invalid("observed_duration_seconds")
    _integer(root["concurrency"], "concurrency", minimum=1)
    _number(root["request_interval_seconds"], "request_interval_seconds", minimum=0)

    binding = _exact_mapping(
        root["host_binding"],
        {
            "host_gate_schema_version",
            "baseline_phase",
            "baseline_gate_passed",
            "baseline_captured_at_utc",
            "baseline_identity",
            "identity_before",
            "identity_after",
            "baseline_listeners",
        },
        "host_binding",
    )
    _string(binding["host_gate_schema_version"], "host_binding.host_gate_schema_version")
    _string(binding["baseline_phase"], "host_binding.baseline_phase")
    _boolean(binding["baseline_gate_passed"], "host_binding.baseline_gate_passed")
    _timestamp(binding["baseline_captured_at_utc"], "host_binding.baseline_captured_at_utc")
    for key in ("baseline_identity", "identity_before", "identity_after"):
        _validate_identity(binding[key], f"host_binding.{key}")
    _validate_listeners(binding["baseline_listeners"], "host_binding.baseline_listeners")

    workload = _exact_mapping(
        root["analysis_workload"],
        {
            "mechanism",
            "fixture_id",
            "fixture_sha256",
            "fixture_byte_count",
            "admission_slot_exercised",
            "real_stylo_worker_exercised",
            "production_state_isolated",
            "scientific_validation",
            "content_retained",
            "outcome",
            "exit_code",
            "duration_ms",
            "success_marker_count",
        },
        "analysis_workload",
    )
    for key in ("mechanism", "fixture_id", "outcome"):
        _string(workload[key], f"analysis_workload.{key}")
    if (
        not isinstance(workload["fixture_sha256"], str)
        or SHA256_RE.fullmatch(workload["fixture_sha256"]) is None
    ):
        _invalid("analysis_workload.fixture_sha256")
    _integer(workload["fixture_byte_count"], "analysis_workload.fixture_byte_count", minimum=1)
    for key in (
        "admission_slot_exercised",
        "real_stylo_worker_exercised",
        "production_state_isolated",
        "scientific_validation",
        "content_retained",
    ):
        _boolean(workload[key], f"analysis_workload.{key}")
    _integer(workload["exit_code"], "analysis_workload.exit_code")
    _number(workload["duration_ms"], "analysis_workload.duration_ms", minimum=0)
    _integer(
        workload["success_marker_count"],
        "analysis_workload.success_marker_count",
        minimum=0,
    )

    _validate_timing_summary(root["delta_load"], "delta_load", health=False)
    lemmata = _exact_mapping(
        root["lemmata"],
        {
            "baseline",
            "during_load",
            "service_before",
            "service_after",
            "error_markers_during_load",
        },
        "lemmata",
    )
    _validate_timing_summary(lemmata["baseline"], "lemmata.baseline", health=True)
    _validate_timing_summary(lemmata["during_load"], "lemmata.during_load", health=False)
    _validate_service(lemmata["service_before"], "lemmata.service_before")
    _validate_service(lemmata["service_after"], "lemmata.service_after")
    _integer(
        lemmata["error_markers_during_load"],
        "lemmata.error_markers_during_load",
        minimum=0,
    )

    host = _exact_mapping(
        root["host"],
        {
            "samples",
            "minimum_available_mib",
            "maximum_memory_full_avg10",
            "oom_markers_before",
            "oom_markers_after",
            "listener_observation_count",
            "listener_mismatch_count",
            "listeners_after",
        },
        "host",
    )
    for key in (
        "samples",
        "minimum_available_mib",
        "oom_markers_before",
        "oom_markers_after",
        "listener_observation_count",
        "listener_mismatch_count",
    ):
        _integer(host[key], f"host.{key}", minimum=0)
    _number(host["maximum_memory_full_avg10"], "host.maximum_memory_full_avg10", minimum=0)
    if host["listener_mismatch_count"] > host["listener_observation_count"]:
        _invalid("host.listener_mismatch_count")
    _validate_listeners(host["listeners_after"], "host.listeners_after")

    containers = _exact_mapping(root["containers"], {"app", "gateway"}, "containers")
    for role in ("app", "gateway"):
        container = _exact_mapping(
            containers[role],
            {"state_before", "state_after", "peaks"},
            f"containers.{role}",
        )
        _validate_container_state(container["state_before"], f"containers.{role}.state_before")
        _validate_container_state(container["state_after"], f"containers.{role}.state_after")
        peaks = _exact_mapping(
            container["peaks"],
            {"cpu_percent", "memory_bytes", "pids"},
            f"containers.{role}.peaks",
        )
        _number(peaks["cpu_percent"], f"containers.{role}.peaks.cpu_percent", minimum=0)
        _integer(peaks["memory_bytes"], f"containers.{role}.peaks.memory_bytes", minimum=0)
        _integer(peaks["pids"], f"containers.{role}.peaks.pids", minimum=0)
    _string(root["delta_service_before"], "delta_service_before")
    _string(root["delta_service_after"], "delta_service_after")
    if has_gate:
        gate = _exact_mapping(root["gate"], {"passed", "failures"}, "gate")
        _boolean(gate["passed"], "gate.passed")
        if not isinstance(gate["failures"], list) or any(
            not isinstance(item, str) or not item for item in gate["failures"]
        ):
            _invalid("gate.failures")
        if gate["passed"] != (not gate["failures"]):
            _invalid("gate")


def evaluate_evidence(evidence: dict[str, Any]) -> list[str]:
    try:
        _validate_evidence_shape(evidence, require_gate=False)
    except LoadGateError:
        return ["P014_LOAD_EVIDENCE_INVALID"]

    failures: list[str] = []
    duration = evidence["requested_duration_seconds"]
    concurrency = evidence["concurrency"]
    interval = float(evidence["request_interval_seconds"])
    if not 30 <= duration <= 300 or not 1 <= concurrency <= 16 or not 0.1 <= interval <= 2.0:
        return ["P014_LOAD_PROFILE_INVALID"]
    if evidence["observed_duration_seconds"] < duration * 0.9:
        failures.append("P014_LOAD_OBSERVATION_INCOMPLETE")

    scope = evidence["scope"]
    if (
        scope["scientific_validation"] is not False
        or scope["maximum_capacity_validation"] is not False
        or scope["content_free_aggregates_only"] is not True
    ):
        failures.append("P014_LOAD_SCOPE_INVALID")

    binding = evidence["host_binding"]
    baseline_time = _timestamp(
        binding["baseline_captured_at_utc"],
        "host_binding.baseline_captured_at_utc",
    )
    started = _timestamp(evidence["started_at_utc"], "started_at_utc")
    ended = _timestamp(evidence["ended_at_utc"], "ended_at_utc")
    if (
        binding["host_gate_schema_version"] != REQUIRED_HOST_GATE_SCHEMA_VERSION
        or binding["baseline_phase"] != "pre-docker"
        or binding["baseline_gate_passed"] is not True
        or binding["baseline_identity"] != binding["identity_before"]
        or binding["identity_before"] != binding["identity_after"]
    ):
        failures.append("P014_LOAD_HOST_OR_BOOT_CHANGED")
    baseline_age = (ended - baseline_time).total_seconds()
    if baseline_time > started or baseline_age < 0 or baseline_age > BASELINE_MAX_AGE_SECONDS:
        failures.append("P014_LOAD_BASELINE_STALE")

    workload = evidence["analysis_workload"]
    if (
        workload["mechanism"] != ANALYSIS_MECHANISM
        or workload["fixture_id"] != FIXTURE_ID
        or workload["fixture_sha256"] != FIXTURE_SHA256
        or workload["fixture_byte_count"] != FIXTURE_BYTE_COUNT
        or workload["outcome"] != "completed"
        or workload["exit_code"] != 0
        or workload["success_marker_count"] < 1
        or workload["admission_slot_exercised"] is not True
        or workload["real_stylo_worker_exercised"] is not True
        or workload["production_state_isolated"] is not True
        or workload["scientific_validation"] is not False
        or workload["content_retained"] is not False
        or workload["duration_ms"] < duration * 1000
        or workload["duration_ms"] > (duration + ANALYSIS_TIMEOUT_SECONDS) * 1000
        or workload["duration_ms"] > evidence["observed_duration_seconds"] * 1000 + 1000
    ):
        failures.append("P014_LOAD_BOUNDED_ANALYSIS_FAILED")

    delta = evidence["delta_load"]
    minimum_requests = int(duration / interval * concurrency * 0.8)
    if delta["requests"] < minimum_requests or delta["status_counts"] != {"200": delta["requests"]}:
        failures.append("P014_LOAD_DELTA_REQUEST_FAILED")
    if delta["body_ok"] != delta["requests"]:
        failures.append("P014_LOAD_DELTA_BODY_FAILED")
    lemmata = evidence["lemmata"]
    baseline = lemmata["baseline"]
    during = lemmata["during_load"]
    if (
        baseline["successes"] != baseline["samples"]
        or baseline["body_ok"] != baseline["samples"]
        or during["status_counts"] != {"200": during["requests"]}
        or during["body_ok"] != during["requests"]
        or during["requests"] < max(10, int(duration * 0.6))
    ):
        failures.append("P014_LOAD_LEMMATA_HEALTH_FAILED")
    if during["p95_ms"] > baseline["p95_ms"] * 1.20:
        failures.append("P014_LOAD_LEMMATA_P95_BUDGET_EXCEEDED")
    before = lemmata["service_before"]
    after = lemmata["service_after"]
    if (
        before["active_state"] != "active"
        or after["active_state"] != "active"
        or before["sub_state"] != "running"
        or after["sub_state"] != "running"
        or before["restart_count"] != after["restart_count"]
        or before["start_monotonic_us"] != after["start_monotonic_us"]
        or lemmata["error_markers_during_load"] != 0
    ):
        failures.append("P014_LOAD_LEMMATA_PROCESS_CHANGED")

    host = evidence["host"]
    if host["samples"] < max(10, int(duration * 0.6)):
        failures.append("P014_LOAD_OBSERVATION_INCOMPLETE")
    if host["minimum_available_mib"] < 512 or host["maximum_memory_full_avg10"] >= 1.0:
        failures.append("P014_LOAD_HOST_CAPACITY_FAILED")
    if host["oom_markers_before"] != 0 or host["oom_markers_after"] != 0:
        failures.append("P014_LOAD_HOST_OOM_OBSERVED")
    expected_listeners = _validate_listeners(
        binding["baseline_listeners"],
        "host_binding.baseline_listeners",
    )
    expected_listeners.add(EXPECTED_DELTA_LISTENER)
    observed_listeners = _validate_listeners(host["listeners_after"], "host.listeners_after")
    if (
        host["listener_observation_count"] != host["samples"]
        or host["listener_mismatch_count"] != 0
        or observed_listeners != expected_listeners
    ):
        failures.append("P014_LOAD_LISTENER_SET_INVALID")

    for role in ("app", "gateway"):
        container = evidence["containers"][role]
        state_before = container["state_before"]
        state_after = container["state_after"]
        expected_limits = {
            "cpu_nano": CPU_NANO_LIMITS[role],
            "memory_bytes": MEMORY_LIMITS[role],
            "pids": PID_LIMITS[role],
        }
        if (
            not state_before["running"]
            or not state_after["running"]
            or state_before["oom_killed"]
            or state_after["oom_killed"]
            or state_before["id"] != state_after["id"]
            or state_before["image_id"] != state_after["image_id"]
            or state_before["restart_count"] != state_after["restart_count"]
        ):
            failures.append(f"P014_LOAD_{role.upper()}_STATE_FAILED")
        if (
            state_before["configured_limits"] != expected_limits
            or state_after["configured_limits"] != expected_limits
        ):
            failures.append(f"P014_LOAD_{role.upper()}_LIMIT_CONFIGURATION_FAILED")
        if (
            container["peaks"]["cpu_percent"] > CPU_PERCENT_LIMITS[role]
            or container["peaks"]["memory_bytes"] > MEMORY_LIMITS[role]
            or container["peaks"]["pids"] > PID_LIMITS[role]
        ):
            failures.append(f"P014_LOAD_{role.upper()}_LIMIT_FAILED")
    if evidence["delta_service_before"] != "active" or evidence["delta_service_after"] != "active":
        failures.append("P014_LOAD_DELTA_SERVICE_FAILED")
    return list(dict.fromkeys(failures))


def _write_new(path: Path, value: dict[str, Any]) -> None:
    if not path.is_absolute() or path.exists():
        raise LoadGateError("P014_LOAD_OUTPUT_PATH_INVALID")
    parent = path.parent.stat()
    if parent.st_uid != 0 or parent.st_mode & 0o077:
        raise LoadGateError("P014_LOAD_OUTPUT_PARENT_NOT_PRIVATE")
    _validate_evidence_shape(value, require_gate=True)
    payload = json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-baseline", required=True, type=Path)
    parser.add_argument("--app", required=True)
    parser.add_argument("--gateway", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--duration-seconds", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--request-interval-seconds", type=float, default=0.2)
    args = parser.parse_args(argv)
    if not 30 <= args.duration_seconds <= 300:
        parser.error("--duration-seconds must be between 30 and 300")
    if not 1 <= args.concurrency <= 16:
        parser.error("--concurrency must be between 1 and 16")
    if (
        not math.isfinite(args.request_interval_seconds)
        or not 0.1 <= args.request_interval_seconds <= 2.0
    ):
        parser.error("--request-interval-seconds must be between 0.1 and 2.0")
    for value in (args.app, args.gateway):
        if CONTAINER_RE.fullmatch(value) is None:
            parser.error("container ids must be 12 to 64 lowercase hexadecimal characters")
    if args.app == args.gateway:
        parser.error("app and gateway container ids must differ")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if os.geteuid() != 0:
            raise LoadGateError("P014_LOAD_GATE_REQUIRES_ROOT")
        baseline = HOST_GATE._load_baseline(args.host_baseline)
        evidence = collect_evidence(
            baseline=baseline,
            containers={"app": args.app, "gateway": args.gateway},
            duration_seconds=args.duration_seconds,
            concurrency=args.concurrency,
            request_interval_seconds=args.request_interval_seconds,
        )
        failures = evaluate_evidence(evidence)
        evidence["gate"] = {"passed": not failures, "failures": failures}
        _write_new(args.output, evidence)
    except (
        HostGateError,
        LoadGateError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if failures:
        print("p014-load-gate-failed:" + ",".join(failures), file=sys.stderr)
        return 21
    print("p014-load-gate-ok")
    return 0


HostGateError = HOST_GATE.HostGateError


if __name__ == "__main__":
    raise SystemExit(main())
