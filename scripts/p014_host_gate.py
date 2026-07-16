#!/usr/bin/env python3
"""Capture and evaluate content-free P014 shared-host measurements."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

SCHEMA_VERSION = "1.3.0"
PHASES = ("pre-docker", "pre-mutation", "post-docker", "delta-idle", "post-rollback")
BASELINE_MAX_AGE_SECONDS = 7200
LEMMATA_URL = "https://lda.lemmata.app/_stcore/health"
DELTA_URL = "http://127.0.0.1:8502/_stcore/health"
DOCKER_KEY = Path("/etc/apt/keyrings/docker.asc")
DOCKER_SOURCE = Path("/etc/apt/sources.list.d/docker.sources")
DOCKER_REPOSITORY_URL = "https://download.docker.com/linux/ubuntu"
EXPECTED_DOCKER_KEY_FINGERPRINT = "9DC858229FC7DD38854AE2D88D81803C0EBFCD88"
DOCKER_PACKAGES = (
    "docker-ce",
    "docker-ce-cli",
    "containerd.io",
    "docker-buildx-plugin",
    "docker-compose-plugin",
)
FIREWALL_COMMANDS = {
    "nftables": ["nft", "list", "ruleset"],
    "iptables": ["iptables-save"],
    "ip6tables": ["ip6tables-save"],
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FINGERPRINT_RE = re.compile(r"^[0-9A-F]{40}$")


class HostGateError(RuntimeError):
    """Raised when a content-free host measurement cannot be completed."""


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
        raise HostGateError(f"P014_COMMAND_FAILED:{command[0]}") from exc


def _required_stdout(command: list[str], *, timeout: float = 20.0) -> str:
    completed = _run(command, timeout=timeout)
    if completed.returncode != 0:
        raise HostGateError(f"P014_COMMAND_NONZERO:{command[0]}")
    return completed.stdout.strip()


def _read_os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        values[key] = value.strip().strip('"')
    return {key: values.get(key, "") for key in ("ID", "VERSION_ID", "VERSION_CODENAME")}


def _read_meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        key, remainder = line.split(":", maxsplit=1)
        token = remainder.strip().split()[0]
        values[key] = int(token) // 1024
    return {
        "total_mib": values["MemTotal"],
        "available_mib": values["MemAvailable"],
        "swap_total_mib": values["SwapTotal"],
    }


def _read_pressure() -> dict[str, float]:
    pressure: dict[str, float] = {}
    for line in Path("/proc/pressure/memory").read_text(encoding="ascii").splitlines():
        parts = line.split()
        kind = parts[0]
        fields = dict(item.split("=", maxsplit=1) for item in parts[1:])
        if kind in {"some", "full"}:
            pressure[f"{kind}_avg10"] = float(fields["avg10"])
    if set(pressure) != {"some_avg10", "full_avg10"}:
        raise HostGateError("P014_MEMORY_PRESSURE_UNAVAILABLE")
    return pressure


def _service_state(name: str) -> str:
    completed = _run(["systemctl", "is-active", name])
    value = completed.stdout.strip()
    if not value:
        raise HostGateError(f"P014_SERVICE_STATE_UNAVAILABLE:{name}")
    return value


def _lemmata_properties() -> dict[str, str | int]:
    output = _required_stdout(
        [
            "systemctl",
            "show",
            "lemmata",
            "--property=ActiveState,SubState,NRestarts,MemoryCurrent,ExecMainStartTimestampMonotonic",
        ]
    )
    values = dict(line.split("=", maxsplit=1) for line in output.splitlines() if "=" in line)
    required = {
        "ActiveState",
        "SubState",
        "NRestarts",
        "MemoryCurrent",
        "ExecMainStartTimestampMonotonic",
    }
    if not required.issubset(values):
        raise HostGateError("P014_LEMMATA_PROPERTIES_INCOMPLETE")
    return {
        "active_state": values["ActiveState"],
        "sub_state": values["SubState"],
        "restart_count": int(values["NRestarts"]),
        "memory_bytes": int(values["MemoryCurrent"]),
        "start_monotonic_us": int(values["ExecMainStartTimestampMonotonic"]),
    }


def _split_listener(value: str) -> tuple[str, int]:
    if value.startswith("[") and "]:" in value:
        host, port = value[1:].rsplit("]:", maxsplit=1)
    else:
        host, port = value.rsplit(":", maxsplit=1)
    return host, int(port)


def _listeners() -> list[dict[str, str | int]]:
    output = _required_stdout(["ss", "-H", "-ltn"])
    listeners: set[tuple[str, int]] = set()
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 4:
            raise HostGateError("P014_LISTENER_PARSE_FAILED")
        try:
            listeners.add(_split_listener(parts[3]))
        except (ValueError, IndexError) as exc:
            raise HostGateError("P014_LISTENER_PARSE_FAILED") from exc
    return [{"address": host, "port": port} for host, port in sorted(listeners)]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _optional_sha256(path: Path) -> str | None:
    return _sha256(path) if path.is_file() else None


def _identity() -> dict[str, str]:
    return {
        "machine_id_sha256": _sha256(Path("/etc/machine-id")),
        "boot_id_sha256": _sha256(Path("/proc/sys/kernel/random/boot_id")),
        "kernel_release": platform.release(),
    }


def _command_fingerprint(name: str, command: list[str]) -> dict[str, str | int]:
    if shutil.which(command[0]) is None:
        raise HostGateError(f"P014_FIREWALL_COMMAND_MISSING:{name}")
    completed = _run(command)
    if completed.returncode != 0:
        raise HostGateError(f"P014_FIREWALL_COMMAND_NONZERO:{name}")
    payload = completed.stdout.encode("utf-8")
    return {
        "line_count": sum(1 for line in completed.stdout.splitlines() if line.strip()),
        "sha256": _sha256_bytes(payload),
    }


def _firewall_fingerprints() -> dict[str, dict[str, str | int]]:
    return {
        name: _command_fingerprint(name, command) for name, command in FIREWALL_COMMANDS.items()
    }


def _forwarding() -> dict[str, int]:
    return {
        "ipv4": int(Path("/proc/sys/net/ipv4/ip_forward").read_text(encoding="ascii").strip()),
        "ipv6": int(
            Path("/proc/sys/net/ipv6/conf/all/forwarding").read_text(encoding="ascii").strip()
        ),
    }


def _http_probe(url: str, *, host: str | None, samples: int) -> dict[str, Any]:
    durations: list[float] = []
    successes = 0
    body_ok = 0
    for _ in range(samples):
        headers = {} if host is None else {"Host": host}
        request = urllib.request.Request(url, headers=headers)
        started = time.monotonic_ns()
        try:
            with urllib.request.urlopen(request, timeout=5.0) as response:
                payload = response.read(16)
                status = response.status
        except (urllib.error.URLError, TimeoutError, OSError):
            continue
        durations.append((time.monotonic_ns() - started) / 1_000_000)
        if status == 200:
            successes += 1
        if payload.strip() == b"ok":
            body_ok += 1
    ordered = sorted(durations)
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1) if ordered else 0
    return {
        "samples": samples,
        "successes": successes,
        "body_ok": body_ok,
        "median_ms": round(statistics.median(ordered), 3) if ordered else None,
        "p95_ms": round(ordered[p95_index], 3) if ordered else None,
        "max_ms": round(max(ordered), 3) if ordered else None,
    }


def _docker_primary_fingerprints() -> list[str]:
    if not DOCKER_KEY.is_file():
        return []
    output = _required_stdout(["gpg", "--batch", "--show-keys", "--with-colons", str(DOCKER_KEY)])
    fingerprints: list[str] = []
    awaiting_primary_fingerprint = False
    for line in output.splitlines():
        fields = line.split(":")
        record_type = fields[0]
        if record_type == "pub":
            awaiting_primary_fingerprint = True
        elif record_type == "fpr" and awaiting_primary_fingerprint and len(fields) > 9:
            fingerprints.append(fields[9])
            awaiting_primary_fingerprint = False
        elif record_type not in {"tru", "uid", "uat", "sig", "rev", "rvk"}:
            awaiting_primary_fingerprint = False
    if awaiting_primary_fingerprint or not fingerprints:
        raise HostGateError("P014_DOCKER_KEY_FINGERPRINT_MISSING")
    return fingerprints


def _docker_source_profile_valid() -> bool:
    if not DOCKER_SOURCE.is_file():
        return False
    os_release = _read_os_release()
    architecture = _required_stdout(["dpkg", "--print-architecture"])
    expected = "\n".join(
        (
            "Types: deb",
            f"URIs: {DOCKER_REPOSITORY_URL}",
            f"Suites: {os_release['VERSION_CODENAME']}",
            "Components: stable",
            f"Architectures: {architecture}",
            f"Signed-By: {DOCKER_KEY}",
            "",
        )
    )
    return DOCKER_SOURCE.read_text(encoding="utf-8") == expected


def _candidate_from_policy(output: str) -> str | None:
    candidate = next(
        (
            line.split(":", maxsplit=1)[1].strip()
            for line in output.splitlines()
            if line.strip().startswith("Candidate:")
        ),
        None,
    )
    if not candidate or candidate == "(none)":
        return None
    return candidate


def _candidate_has_exact_official_origin(output: str, candidate: str) -> bool:
    os_release = _read_os_release()
    architecture = _required_stdout(["dpkg", "--print-architecture"])
    expected_suite = f"{os_release['VERSION_CODENAME']}/stable"
    in_candidate_stanza = False
    for line in output.splitlines():
        version = re.match(r"^\s*(?:\*\*\*\s+)?(\S+)\s+\d+\s*$", line)
        if version is not None:
            in_candidate_stanza = version.group(1) == candidate
            continue
        if not in_candidate_stanza:
            continue
        fields = line.split()
        if len(fields) >= 5 and fields[0].isdigit():
            if fields[1:5] == [
                DOCKER_REPOSITORY_URL,
                expected_suite,
                architecture,
                "Packages",
            ]:
                return True
    return False


def _apt_candidate(package: str) -> tuple[str | None, bool]:
    official_output = _required_stdout(
        [
            "apt-cache",
            "-o",
            f"Dir::Etc::sourcelist={DOCKER_SOURCE}",
            "-o",
            "Dir::Etc::sourceparts=-",
            "-o",
            "APT::Get::List-Cleanup=0",
            "policy",
            package,
        ]
    )
    official_candidate = _candidate_from_policy(official_output)
    exact_origin = bool(
        official_candidate
        and _candidate_has_exact_official_origin(official_output, official_candidate)
    )
    return official_candidate, exact_origin


def _docker_facts() -> dict[str, Any]:
    installed = shutil.which("docker") is not None
    facts: dict[str, Any] = {
        "installed": installed,
        "service": _service_state("docker"),
        "engine_version": None,
        "compose_version": None,
        "packages": {},
        "candidate_versions": {},
        "official_candidates": {},
        "repository": {
            "key_sha256": _optional_sha256(DOCKER_KEY),
            "source_sha256": _optional_sha256(DOCKER_SOURCE),
            "primary_fingerprints": _docker_primary_fingerprints(),
            "source_profile_valid": _docker_source_profile_valid(),
        },
    }
    if installed:
        engine = _run(["docker", "version", "--format", "{{.Server.Version}}"])
        compose = _run(["docker", "compose", "version", "--short"])
        facts["engine_version"] = engine.stdout.strip() if engine.returncode == 0 else None
        facts["compose_version"] = compose.stdout.strip() if compose.returncode == 0 else None
    for package in DOCKER_PACKAGES:
        completed = _run(["dpkg-query", "-W", "-f=${db:Status-Status}\t${Version}", package])
        if completed.returncode != 0:
            continue
        status, _, version = completed.stdout.partition("\t")
        if status == "installed" and version.strip():
            facts["packages"][package] = version.strip()
            candidate, official = _apt_candidate(package)
            if candidate is not None:
                facts["candidate_versions"][package] = candidate
            facts["official_candidates"][package] = official
    return facts


def _kernel_oom_count() -> int:
    output = _required_stdout(["journalctl", "-k", "--since", "-30min", "--no-pager", "--quiet"])
    markers = ("out of memory", "oom-kill", "killed process")
    return sum(
        1 for line in output.lower().splitlines() if any(marker in line for marker in markers)
    )


def collect_snapshot(phase: str, *, samples: int) -> dict[str, Any]:
    if phase not in PHASES:
        raise HostGateError("P014_PHASE_INVALID")
    root = shutil.disk_usage("/")
    return {
        "schema_version": SCHEMA_VERSION,
        "capture_mode": "live",
        "phase": phase,
        "captured_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "host": {
            "identity": _identity(),
            "os": _read_os_release(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count(),
            "memory": _read_meminfo(),
            "root_free_mib": root.free // (1024 * 1024),
            "memory_pressure": _read_pressure(),
            "forwarding": _forwarding(),
            "firewall": _firewall_fingerprints(),
            "listeners": _listeners(),
            "kernel_oom_markers_30m": _kernel_oom_count(),
        },
        "services": {
            "caddy": _service_state("caddy"),
            "lemmata": _service_state("lemmata"),
            "docker": _service_state("docker"),
            "delta_public_alpha": _service_state("delta-public-alpha"),
        },
        "lemmata": {
            "service": _lemmata_properties(),
            "health": _http_probe(LEMMATA_URL, host=None, samples=samples),
        },
        "delta": {
            "health": (
                _http_probe(DELTA_URL, host="delta.lemmata.app", samples=samples)
                if phase == "delta-idle"
                else None
            )
        },
        "caddyfile_sha256": _sha256(Path("/etc/caddy/Caddyfile")),
        "docker": _docker_facts(),
    }


def _invalid(path: str) -> NoReturn:
    raise HostGateError(f"P014_SNAPSHOT_FIELD_INVALID:{path}")


def _exact_mapping(value: Any, keys: set[str], path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        _invalid(path)
    return value


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _invalid(path)
    return value


def _number_or_none(value: Any, path: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _invalid(path)
    if not math.isfinite(float(value)) or float(value) < 0:
        _invalid(path)


def _string(value: Any, path: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        _invalid(path)
    return value


def _sha_or_none(value: Any, path: str) -> None:
    if value is not None and (not isinstance(value, str) or SHA256_RE.fullmatch(value) is None):
        _invalid(path)


def _parse_timestamp(value: Any, path: str) -> datetime:
    text = _string(value, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HostGateError(f"P014_SNAPSHOT_FIELD_INVALID:{path}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        _invalid(path)
    return parsed


def _validate_health(value: Any, path: str) -> None:
    health = _exact_mapping(
        value,
        {"samples", "successes", "body_ok", "median_ms", "p95_ms", "max_ms"},
        path,
    )
    samples = _integer(health["samples"], f"{path}.samples", minimum=5)
    if samples > 100:
        _invalid(f"{path}.samples")
    for key in ("successes", "body_ok"):
        count = _integer(health[key], f"{path}.{key}")
        if count > samples:
            _invalid(f"{path}.{key}")
    for key in ("median_ms", "p95_ms", "max_ms"):
        _number_or_none(health[key], f"{path}.{key}")
    non_null = [health[key] for key in ("median_ms", "p95_ms", "max_ms") if health[key] is not None]
    if len(non_null) not in {0, 3}:
        _invalid(path)
    if len(non_null) == 3 and (
        float(health["median_ms"]) > float(health["max_ms"])
        or float(health["p95_ms"]) > float(health["max_ms"])
    ):
        _invalid(path)


def _validate_snapshot_shape(snapshot: Any, *, require_gate: bool | None = None) -> None:
    base_keys = {
        "schema_version",
        "capture_mode",
        "phase",
        "captured_at_utc",
        "host",
        "services",
        "lemmata",
        "delta",
        "caddyfile_sha256",
        "docker",
    }
    if not isinstance(snapshot, dict):
        _invalid("root")
    has_gate = "gate" in snapshot
    if require_gate is True and not has_gate:
        _invalid("gate")
    if require_gate is False and has_gate:
        _invalid("gate")
    _exact_mapping(snapshot, base_keys | ({"gate"} if has_gate else set()), "root")
    if snapshot["schema_version"] != SCHEMA_VERSION:
        _invalid("schema_version")
    if snapshot["capture_mode"] != "live" or snapshot["phase"] not in PHASES:
        _invalid("capture_mode_or_phase")
    _parse_timestamp(snapshot["captured_at_utc"], "captured_at_utc")

    host = _exact_mapping(
        snapshot["host"],
        {
            "identity",
            "os",
            "architecture",
            "cpu_count",
            "memory",
            "root_free_mib",
            "memory_pressure",
            "forwarding",
            "firewall",
            "listeners",
            "kernel_oom_markers_30m",
        },
        "host",
    )
    identity = _exact_mapping(
        host["identity"],
        {"machine_id_sha256", "boot_id_sha256", "kernel_release"},
        "host.identity",
    )
    _sha_or_none(identity["machine_id_sha256"], "host.identity.machine_id_sha256")
    _sha_or_none(identity["boot_id_sha256"], "host.identity.boot_id_sha256")
    if identity["machine_id_sha256"] is None or identity["boot_id_sha256"] is None:
        _invalid("host.identity")
    _string(identity["kernel_release"], "host.identity.kernel_release")
    operating_system = _exact_mapping(
        host["os"], {"ID", "VERSION_ID", "VERSION_CODENAME"}, "host.os"
    )
    for key in operating_system:
        _string(operating_system[key], f"host.os.{key}")
    _string(host["architecture"], "host.architecture")
    _integer(host["cpu_count"], "host.cpu_count", minimum=1)
    memory = _exact_mapping(
        host["memory"], {"total_mib", "available_mib", "swap_total_mib"}, "host.memory"
    )
    total = _integer(memory["total_mib"], "host.memory.total_mib", minimum=1)
    available = _integer(memory["available_mib"], "host.memory.available_mib")
    if available > total:
        _invalid("host.memory.available_mib")
    _integer(memory["swap_total_mib"], "host.memory.swap_total_mib")
    _integer(host["root_free_mib"], "host.root_free_mib")
    pressure = _exact_mapping(
        host["memory_pressure"], {"some_avg10", "full_avg10"}, "host.memory_pressure"
    )
    for key in pressure:
        _number_or_none(pressure[key], f"host.memory_pressure.{key}")
        if pressure[key] is None:
            _invalid(f"host.memory_pressure.{key}")
    forwarding = _exact_mapping(host["forwarding"], {"ipv4", "ipv6"}, "host.forwarding")
    for key in forwarding:
        if _integer(forwarding[key], f"host.forwarding.{key}") not in {0, 1}:
            _invalid(f"host.forwarding.{key}")
    firewall = _exact_mapping(host["firewall"], set(FIREWALL_COMMANDS), "host.firewall")
    for name, value in firewall.items():
        fingerprint = _exact_mapping(value, {"line_count", "sha256"}, f"host.firewall.{name}")
        _integer(fingerprint["line_count"], f"host.firewall.{name}.line_count")
        _sha_or_none(fingerprint["sha256"], f"host.firewall.{name}.sha256")
        if fingerprint["sha256"] is None:
            _invalid(f"host.firewall.{name}.sha256")
    if not isinstance(host["listeners"], list):
        _invalid("host.listeners")
    seen: set[tuple[str, int]] = set()
    for index, raw_listener in enumerate(host["listeners"]):
        listener = _exact_mapping(raw_listener, {"address", "port"}, f"host.listeners[{index}]")
        address = _string(listener["address"], f"host.listeners[{index}].address")
        port = _integer(listener["port"], f"host.listeners[{index}].port", minimum=1)
        if port > 65535 or (address, port) in seen:
            _invalid(f"host.listeners[{index}]")
        seen.add((address, port))
    _integer(host["kernel_oom_markers_30m"], "host.kernel_oom_markers_30m")

    services = _exact_mapping(
        snapshot["services"],
        {"caddy", "lemmata", "docker", "delta_public_alpha"},
        "services",
    )
    for key in services:
        _string(services[key], f"services.{key}")
    lemmata = _exact_mapping(snapshot["lemmata"], {"service", "health"}, "lemmata")
    service = _exact_mapping(
        lemmata["service"],
        {"active_state", "sub_state", "restart_count", "memory_bytes", "start_monotonic_us"},
        "lemmata.service",
    )
    _string(service["active_state"], "lemmata.service.active_state")
    _string(service["sub_state"], "lemmata.service.sub_state")
    for key in ("restart_count", "memory_bytes", "start_monotonic_us"):
        _integer(service[key], f"lemmata.service.{key}")
    _validate_health(lemmata["health"], "lemmata.health")
    delta = _exact_mapping(snapshot["delta"], {"health"}, "delta")
    if delta["health"] is not None:
        _validate_health(delta["health"], "delta.health")
    _sha_or_none(snapshot["caddyfile_sha256"], "caddyfile_sha256")
    if snapshot["caddyfile_sha256"] is None:
        _invalid("caddyfile_sha256")

    docker = _exact_mapping(
        snapshot["docker"],
        {
            "installed",
            "service",
            "engine_version",
            "compose_version",
            "packages",
            "candidate_versions",
            "official_candidates",
            "repository",
        },
        "docker",
    )
    if not isinstance(docker["installed"], bool):
        _invalid("docker.installed")
    _string(docker["service"], "docker.service")
    for key in ("engine_version", "compose_version"):
        if docker[key] is not None:
            _string(docker[key], f"docker.{key}")
    if not isinstance(docker["packages"], dict) or not set(docker["packages"]).issubset(
        DOCKER_PACKAGES
    ):
        _invalid("docker.packages")
    for package, version in docker["packages"].items():
        _string(version, f"docker.packages.{package}")
    if not isinstance(docker["candidate_versions"], dict) or not set(
        docker["candidate_versions"]
    ).issubset(DOCKER_PACKAGES):
        _invalid("docker.candidate_versions")
    for package, version in docker["candidate_versions"].items():
        _string(version, f"docker.candidate_versions.{package}")
    if not isinstance(docker["official_candidates"], dict) or not set(
        docker["official_candidates"]
    ).issubset(DOCKER_PACKAGES):
        _invalid("docker.official_candidates")
    if any(not isinstance(value, bool) for value in docker["official_candidates"].values()):
        _invalid("docker.official_candidates")
    repository = _exact_mapping(
        docker["repository"],
        {"key_sha256", "source_sha256", "primary_fingerprints", "source_profile_valid"},
        "docker.repository",
    )
    for key in ("key_sha256", "source_sha256"):
        _sha_or_none(repository[key], f"docker.repository.{key}")
    fingerprints = repository["primary_fingerprints"]
    if not isinstance(fingerprints, list) or any(
        not isinstance(fingerprint, str) or FINGERPRINT_RE.fullmatch(fingerprint) is None
        for fingerprint in fingerprints
    ):
        _invalid("docker.repository.primary_fingerprints")
    if not isinstance(repository["source_profile_valid"], bool):
        _invalid("docker.repository.source_profile_valid")

    if has_gate:
        gate = _exact_mapping(snapshot["gate"], {"passed", "failures"}, "gate")
        if not isinstance(gate["passed"], bool) or not isinstance(gate["failures"], list):
            _invalid("gate")
        if any(not isinstance(item, str) or not item for item in gate["failures"]):
            _invalid("gate.failures")
        if gate["passed"] != (not gate["failures"]):
            _invalid("gate")


def _listener_set(snapshot: dict[str, Any]) -> set[tuple[str, int]]:
    return {(str(item["address"]), int(item["port"])) for item in snapshot["host"]["listeners"]}


def _complete_health(probe: dict[str, Any] | None) -> bool:
    return bool(
        probe
        and probe["successes"] == probe["samples"]
        and probe["body_ok"] == probe["samples"]
        and probe["p95_ms"] is not None
    )


def _compare_lemmata(
    snapshot: dict[str, Any], baseline: dict[str, Any], failures: list[str]
) -> None:
    current = snapshot["lemmata"]["service"]
    previous = baseline["lemmata"]["service"]
    if current["restart_count"] != previous["restart_count"]:
        failures.append("P014_LEMMATA_RESTART_CHANGED")
    if current["start_monotonic_us"] != previous["start_monotonic_us"]:
        failures.append("P014_LEMMATA_START_CHANGED")
    current_health = snapshot["lemmata"]["health"]
    baseline_health = baseline["lemmata"]["health"]
    if current_health["samples"] != baseline_health["samples"]:
        failures.append("P014_LEMMATA_SAMPLE_COUNT_CHANGED")
    current_p95 = current_health["p95_ms"]
    baseline_p95 = baseline_health["p95_ms"]
    if current_p95 is None or baseline_p95 is None or current_p95 > baseline_p95 * 1.20:
        failures.append("P014_LEMMATA_P95_BUDGET_EXCEEDED")


def _baseline_failures(snapshot: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    try:
        _validate_snapshot_shape(baseline, require_gate=True)
    except HostGateError:
        return ["P014_BASELINE_INVALID"]
    if baseline["phase"] != "pre-docker" or baseline["gate"]["passed"] is not True:
        failures.append("P014_BASELINE_NOT_ACCEPTED")
    if snapshot["host"]["identity"] != baseline["host"]["identity"]:
        failures.append("P014_BASELINE_HOST_OR_BOOT_CHANGED")
    current_time = _parse_timestamp(snapshot["captured_at_utc"], "captured_at_utc")
    baseline_time = _parse_timestamp(baseline["captured_at_utc"], "captured_at_utc")
    age = (current_time - baseline_time).total_seconds()
    if age < 0 or age > BASELINE_MAX_AGE_SECONDS:
        failures.append("P014_BASELINE_STALE")
    return failures


def _host_profile_failures(snapshot: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    host = snapshot["host"]
    if (
        host["os"]["ID"] != "ubuntu"
        or host["os"]["VERSION_ID"] != "26.04"
        or host["architecture"] not in {"x86_64", "amd64"}
        or host["cpu_count"] < 2
    ):
        failures.append("P014_HOST_PROFILE_UNSUPPORTED")
    if host["memory"]["swap_total_mib"] != 0:
        failures.append("P014_UNEXPECTED_HOST_SWAP")
    if host["kernel_oom_markers_30m"] != 0:
        failures.append("P014_KERNEL_OOM_OBSERVED")
    return failures


def _docker_profile_failures(snapshot: dict[str, Any], *, expected: bool) -> list[str]:
    failures: list[str] = []
    docker = snapshot["docker"]
    service_active = snapshot["services"]["docker"] == "active" and docker["service"] == "active"
    if expected:
        if not docker["installed"] or not service_active:
            failures.append("P014_DOCKER_NOT_ACTIVE")
        if not docker["engine_version"] or not docker["compose_version"]:
            failures.append("P014_DOCKER_VERSION_MISSING")
        if set(docker["packages"]) != set(DOCKER_PACKAGES):
            failures.append("P014_DOCKER_PACKAGE_SET_INVALID")
        if docker["packages"] != docker["candidate_versions"]:
            failures.append("P014_DOCKER_CANDIDATE_VERSION_MISMATCH")
        if docker["official_candidates"] != {package: True for package in DOCKER_PACKAGES}:
            failures.append("P014_DOCKER_PACKAGE_ORIGIN_INVALID")
        repository = docker["repository"]
        if (
            repository["key_sha256"] is None
            or repository["source_sha256"] is None
            or repository["primary_fingerprints"] != [EXPECTED_DOCKER_KEY_FINGERPRINT]
            or repository["source_profile_valid"] is not True
        ):
            failures.append("P014_DOCKER_REPOSITORY_EVIDENCE_MISSING")
    elif (
        docker["installed"]
        or service_active
        or docker["packages"]
        or docker["candidate_versions"]
        or docker["official_candidates"]
        or any(docker["repository"].values())
    ):
        failures.append("P014_DOCKER_ROLLBACK_INCOMPLETE")
    return failures


def evaluate_snapshot(snapshot: dict[str, Any], baseline: dict[str, Any] | None) -> list[str]:
    try:
        _validate_snapshot_shape(snapshot)
    except HostGateError:
        return ["P014_SNAPSHOT_INVALID"]

    failures = _host_profile_failures(snapshot)
    phase = snapshot["phase"]
    host = snapshot["host"]
    memory = host["memory"]
    services = snapshot["services"]
    listeners = _listener_set(snapshot)
    if services["caddy"] != "active" or services["lemmata"] != "active":
        failures.append("P014_LEMMATA_OR_CADDY_INACTIVE")
    if not _complete_health(snapshot["lemmata"]["health"]):
        failures.append("P014_LEMMATA_HEALTH_FAILED")

    if phase == "pre-docker":
        failures.extend(_docker_profile_failures(snapshot, expected=False))
        if memory["available_mib"] < 2048:
            failures.append("P014_PRE_DOCKER_MEMORY_LOW")
        if host["root_free_mib"] < 10240:
            failures.append("P014_ROOT_DISK_LOW")
        if any(port == 8502 for _, port in listeners):
            failures.append("P014_PORT_8502_OCCUPIED")
        return failures

    if baseline is None:
        return failures + ["P014_BASELINE_REQUIRED"]
    failures.extend(_baseline_failures(snapshot, baseline))
    if "P014_BASELINE_INVALID" in failures:
        return failures
    _compare_lemmata(snapshot, baseline, failures)
    if snapshot["caddyfile_sha256"] != baseline["caddyfile_sha256"]:
        failures.append("P014_CADDYFILE_CHANGED")

    if phase == "pre-mutation":
        failures.extend(_docker_profile_failures(snapshot, expected=False))
        if memory["available_mib"] < 2048:
            failures.append("P014_PRE_DOCKER_MEMORY_LOW")
        if host["root_free_mib"] < 10240:
            failures.append("P014_ROOT_DISK_LOW")
        if listeners != _listener_set(baseline):
            failures.append("P014_PRE_MUTATION_LISTENERS_CHANGED")
        if host["forwarding"] != baseline["host"]["forwarding"]:
            failures.append("P014_PRE_MUTATION_FORWARDING_CHANGED")
        if host["firewall"] != baseline["host"]["firewall"]:
            failures.append("P014_PRE_MUTATION_FIREWALL_CHANGED")
        if any(port == 8502 for _, port in listeners):
            failures.append("P014_PORT_8502_OCCUPIED")
        return failures

    if phase == "post-rollback":
        failures.extend(_docker_profile_failures(snapshot, expected=False))
        if memory["available_mib"] < 1800:
            failures.append("P014_POST_ROLLBACK_MEMORY_LOW")
        if listeners != _listener_set(baseline):
            failures.append("P014_LISTENERS_NOT_RESTORED")
        if host["forwarding"] != baseline["host"]["forwarding"]:
            failures.append("P014_FORWARDING_NOT_RESTORED")
        if host["firewall"] != baseline["host"]["firewall"]:
            failures.append("P014_FIREWALL_NOT_RESTORED")
        return failures

    failures.extend(_docker_profile_failures(snapshot, expected=True))
    expected_listeners = _listener_set(baseline)
    if phase == "post-docker":
        if memory["available_mib"] < 1800:
            failures.append("P014_POST_DOCKER_MEMORY_LOW")
        if listeners != expected_listeners:
            failures.append("P014_UNEXPECTED_LISTENER_AFTER_DOCKER")
        return failures

    expected_listeners.add(("127.0.0.1", 8502))
    if services["delta_public_alpha"] != "active":
        failures.append("P014_DELTA_SERVICE_INACTIVE")
    if listeners != expected_listeners:
        failures.append("P014_DELTA_LISTENER_SET_INVALID")
    if not _complete_health(snapshot["delta"]["health"]):
        failures.append("P014_DELTA_HEALTH_FAILED")
    if memory["available_mib"] < 768:
        failures.append("P014_DELTA_MEMORY_LOW")
    if host["memory_pressure"]["full_avg10"] >= 1.0:
        failures.append("P014_MEMORY_PRESSURE_HIGH")
    return failures


def _reject_json_constant(value: str) -> NoReturn:
    raise HostGateError(f"P014_JSON_CONSTANT_INVALID:{value}")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=_reject_json_constant,
    )
    if not isinstance(value, dict):
        raise HostGateError("P014_JSON_ROOT_INVALID")
    return value


def _load_baseline(path: Path) -> dict[str, Any]:
    if not path.is_absolute() or not path.is_file():
        raise HostGateError("P014_BASELINE_PATH_INVALID")
    stat = path.stat()
    if stat.st_uid != 0 or stat.st_mode & 0o777 != 0o600:
        raise HostGateError("P014_BASELINE_PERMISSIONS_INVALID")
    value = _load_json(path)
    _validate_snapshot_shape(value, require_gate=True)
    return value


def _write_new(path: Path, value: dict[str, Any]) -> None:
    if not path.is_absolute():
        raise HostGateError("P014_OUTPUT_NOT_ABSOLUTE")
    if path.exists():
        raise HostGateError("P014_OUTPUT_EXISTS")
    parent = path.parent.stat()
    if parent.st_uid != 0 or parent.st_mode & 0o077:
        raise HostGateError("P014_OUTPUT_PARENT_NOT_PRIVATE")
    payload = json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=PHASES)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args(argv)
    if args.samples < 5 or args.samples > 100:
        parser.error("--samples must be between 5 and 100")
    if args.phase == "pre-docker" and args.baseline is not None:
        parser.error("--baseline is not accepted for pre-docker")
    if args.phase != "pre-docker" and args.baseline is None:
        parser.error("--baseline is required after pre-docker")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if os.geteuid() != 0:
            raise HostGateError("P014_HOST_GATE_REQUIRES_ROOT")
        snapshot = collect_snapshot(args.phase, samples=args.samples)
        baseline = _load_baseline(args.baseline) if args.baseline is not None else None
        failures = evaluate_snapshot(snapshot, baseline)
        snapshot["gate"] = {"passed": not failures, "failures": failures}
        _write_new(args.output, snapshot)
    except (HostGateError, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if failures:
        print("p014-host-gate-failed:" + ",".join(failures), file=sys.stderr)
        return 21
    print(f"p014-host-gate-ok phase={args.phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
