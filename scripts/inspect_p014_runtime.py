#!/usr/bin/env python3
"""Inspect live P014 containers without printing environment or secret values."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from typing import Any

APP_MEMORY = 1536 * 1024 * 1024
GATEWAY_MEMORY = 128 * 1024 * 1024
APP_TMPFS = {
    "/tmp": {"size": "64m", "mode": "1777", "uid": "10001", "gid": "10001"},
    "/var/lib/delta/runtime": {
        "size": "512m",
        "mode": "0700",
        "uid": "10001",
        "gid": "10001",
    },
}
GATEWAY_TMPFS = {
    "/tmp": {"size": "32m", "mode": "0700", "uid": "101", "gid": "101"},
}
GATEWAY_REFERENCE = (
    "nginxinc/nginx-unprivileged:1.30.3-alpine-slim@"
    "sha256:3b24c4bfb2b9f60359b1475605ca1c8ed6e4963eb8369c6835be4d96bdb3ea81"
)
SECRET_NAMES = (
    "DELTA_JOB_OWNER_SECRET_HEX",
    "DELTA_PREPARATION_AUTHORITY_SECRET_HEX",
    "DELTA_RECOVERY_RECEIPT_SECRET_HEX",
)
IMMUTABLE_IMAGE = re.compile(r"(?:^sha256:|@sha256:)[0-9a-f]{64}$")
SECRET_VALUE = re.compile(r"[0-9a-f]{64}")
SOURCE_COMMIT = re.compile(r"[0-9a-f]{40}")
SOURCE_URL = "https://github.com/oguzkoran-max/delta.lemmata.app"


class RuntimeInspectionError(RuntimeError):
    """A stable, content-free runtime inspection failure."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeInspectionError(code)


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), code)
    return value


def _environment(record: Mapping[str, Any]) -> Mapping[str, str]:
    config = _mapping(record.get("Config"), "P014_RUNTIME_CONFIG_INVALID")
    entries = config.get("Env")
    _require(isinstance(entries, list), "P014_RUNTIME_ENV_INVALID")
    environment: dict[str, str] = {}
    for entry in entries:
        _require(isinstance(entry, str) and "=" in entry, "P014_RUNTIME_ENV_INVALID")
        name, value = entry.split("=", maxsplit=1)
        _require(name not in environment, "P014_RUNTIME_ENV_DUPLICATE")
        environment[name] = value
    return environment


def _validate_common(
    record: Mapping[str, Any],
    *,
    user: str,
    pids: int,
    nano_cpus: int,
    memory: int,
) -> None:
    config = _mapping(record.get("Config"), "P014_RUNTIME_CONFIG_INVALID")
    host = _mapping(record.get("HostConfig"), "P014_RUNTIME_HOST_CONFIG_INVALID")
    state = _mapping(record.get("State"), "P014_RUNTIME_STATE_INVALID")
    health = _mapping(state.get("Health"), "P014_RUNTIME_HEALTH_INVALID")
    restart = _mapping(host.get("RestartPolicy"), "P014_RUNTIME_RESTART_INVALID")
    _require(config.get("User") == user, "P014_RUNTIME_USER_INVALID")
    _require(host.get("ReadonlyRootfs") is True, "P014_RUNTIME_ROOT_WRITABLE")
    _require(host.get("CapDrop") == ["ALL"], "P014_RUNTIME_CAPABILITIES_INVALID")
    _require(
        "no-new-privileges:true" in (host.get("SecurityOpt") or []),
        "P014_RUNTIME_PRIVILEGES_INVALID",
    )
    _require(host.get("PidsLimit") == pids, "P014_RUNTIME_PID_LIMIT_INVALID")
    _require(host.get("NanoCpus") == nano_cpus, "P014_RUNTIME_CPU_LIMIT_INVALID")
    _require(host.get("Memory") == memory, "P014_RUNTIME_MEMORY_LIMIT_INVALID")
    _require(host.get("MemorySwap") == memory, "P014_RUNTIME_SWAP_LIMIT_INVALID")
    _require(
        restart.get("Name") == "on-failure" and restart.get("MaximumRetryCount") == 3,
        "P014_RUNTIME_RESTART_INVALID",
    )
    _require(health.get("Status") == "healthy", "P014_RUNTIME_NOT_HEALTHY")
    _require(state.get("Running") is True, "P014_RUNTIME_NOT_RUNNING")


def _mount_destinations(record: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    mounts = record.get("Mounts")
    _require(isinstance(mounts, list), "P014_RUNTIME_MOUNTS_INVALID")
    projected: dict[str, Mapping[str, Any]] = {}
    for item in mounts:
        mount = _mapping(item, "P014_RUNTIME_MOUNT_INVALID")
        destination = mount.get("Destination")
        _require(isinstance(destination, str), "P014_RUNTIME_MOUNT_INVALID")
        _require(destination not in projected, "P014_RUNTIME_MOUNT_DUPLICATE")
        projected[destination] = mount
    return projected


def _validate_tmpfs(
    host: Mapping[str, Any],
    expected: Mapping[str, Mapping[str, str]],
) -> None:
    raw = _mapping(host.get("Tmpfs"), "P014_RUNTIME_TMPFS_INVALID")
    _require(set(raw) == set(expected), "P014_RUNTIME_TMPFS_SET_INVALID")
    for destination, expected_values in expected.items():
        options = raw[destination]
        _require(isinstance(options, str), "P014_RUNTIME_TMPFS_INVALID")
        flags: set[str] = set()
        values: dict[str, str] = {}
        for option in options.split(","):
            name, separator, value = option.partition("=")
            if separator:
                _require(name not in values, "P014_RUNTIME_TMPFS_INVALID")
                values[name] = value
            else:
                flags.add(name)
        _require(flags == {"rw", "nosuid", "nodev", "noexec"}, "P014_RUNTIME_TMPFS_FLAGS_INVALID")
        _require(values == expected_values, "P014_RUNTIME_TMPFS_OPTIONS_INVALID")


def _validate_network(record: Mapping[str, Any], expected: set[str]) -> None:
    network_settings = _mapping(record.get("NetworkSettings"), "P014_RUNTIME_NETWORK_INVALID")
    networks = _mapping(network_settings.get("Networks"), "P014_RUNTIME_NETWORK_INVALID")
    _require(set(networks) == expected, "P014_RUNTIME_NETWORK_SET_INVALID")


def _validate_published_gateway_port(record: Mapping[str, Any]) -> None:
    network_settings = _mapping(record.get("NetworkSettings"), "P014_RUNTIME_NETWORK_INVALID")
    ports = _mapping(network_settings.get("Ports"), "P014_RUNTIME_PORTS_INVALID")
    _require(set(ports) == {"8080/tcp"}, "P014_RUNTIME_PORT_SET_INVALID")
    _require(
        ports["8080/tcp"] == [{"HostIp": "127.0.0.1", "HostPort": "8502"}],
        "P014_GATEWAY_PORT_NOT_PUBLISHED",
    )


def validate_runtime_records(
    app: Mapping[str, Any],
    gateway: Mapping[str, Any],
) -> tuple[str, str]:
    """Validate two docker-inspect records and return only their safe image IDs."""

    _validate_common(app, user="10001:10001", pids=128, nano_cpus=1_500_000_000, memory=APP_MEMORY)
    _validate_common(gateway, user="101:101", pids=64, nano_cpus=250_000_000, memory=GATEWAY_MEMORY)
    _validate_network(app, {"delta-public-alpha_delta_internal"})
    _validate_network(
        gateway,
        {
            "delta-public-alpha_delta_internal",
            "delta-public-alpha_delta_edge",
        },
    )
    _validate_published_gateway_port(gateway)

    app_config = _mapping(app.get("Config"), "P014_RUNTIME_CONFIG_INVALID")
    gateway_config = _mapping(gateway.get("Config"), "P014_RUNTIME_CONFIG_INVALID")
    app_image_reference = app_config.get("Image")
    _require(
        isinstance(app_image_reference, str)
        and IMMUTABLE_IMAGE.search(app_image_reference) is not None,
        "P014_APP_IMAGE_NOT_IMMUTABLE",
    )
    _require(gateway_config.get("Image") == GATEWAY_REFERENCE, "P014_GATEWAY_IMAGE_MISMATCH")
    _require(app.get("Path") == "/opt/delta/.venv/bin/streamlit", "P014_APP_COMMAND_INVALID")

    environment = _environment(app)
    _require(environment.get("DELTA_ENV") == "production", "P014_RUNTIME_PROFILE_INVALID")
    build_id = environment.get("DELTA_BUILD_ID", "")
    _require(SOURCE_COMMIT.fullmatch(build_id) is not None, "P014_RUNTIME_BUILD_ID_INVALID")
    _require(
        environment.get("DELTA_EXTERNAL_NETWORK") == "disabled",
        "P014_RUNTIME_EGRESS_POLICY_INVALID",
    )
    _require(
        environment.get("DELTA_RUNTIME_ROOT") == "/var/lib/delta/runtime",
        "P014_RUNTIME_ROOT_INVALID",
    )
    secret_values = tuple(environment.get(name, "") for name in SECRET_NAMES)
    _require(
        all(SECRET_VALUE.fullmatch(value) is not None for value in secret_values),
        "P014_RUNTIME_SECRET_INVALID",
    )
    _require(len(set(secret_values)) == len(SECRET_NAMES), "P014_RUNTIME_SECRET_REUSE")

    app_host = _mapping(app.get("HostConfig"), "P014_RUNTIME_HOST_CONFIG_INVALID")
    gateway_host = _mapping(gateway.get("HostConfig"), "P014_RUNTIME_HOST_CONFIG_INVALID")
    _require(app_host.get("Init") is True, "P014_APP_INIT_INVALID")
    _validate_tmpfs(app_host, APP_TMPFS)
    _validate_tmpfs(gateway_host, GATEWAY_TMPFS)
    _require(not app_host.get("PortBindings"), "P014_APP_PORT_PUBLISHED")
    bindings = _mapping(gateway_host.get("PortBindings"), "P014_GATEWAY_PORTS_INVALID")
    _require(set(bindings) == {"8080/tcp"}, "P014_GATEWAY_PORT_SET_INVALID")
    binding = bindings["8080/tcp"]
    _require(isinstance(binding, list) and len(binding) == 1, "P014_GATEWAY_BIND_INVALID")
    _require(
        binding[0] == {"HostIp": "127.0.0.1", "HostPort": "8502"},
        "P014_GATEWAY_BIND_INVALID",
    )

    app_mounts = _mount_destinations(app)
    _require(
        set(app_mounts).issubset(APP_TMPFS),
        "P014_APP_MOUNT_SET_INVALID",
    )
    _require(
        all(item.get("Type") == "tmpfs" for item in app_mounts.values()),
        "P014_APP_MOUNT_TYPE_INVALID",
    )
    gateway_mounts = _mount_destinations(gateway)
    _require(
        "/etc/nginx/nginx.conf" in gateway_mounts
        and set(gateway_mounts).issubset({"/tmp", "/etc/nginx/nginx.conf"}),
        "P014_GATEWAY_MOUNT_SET_INVALID",
    )
    config_mount = gateway_mounts["/etc/nginx/nginx.conf"]
    _require(
        config_mount.get("Type") == "bind" and config_mount.get("RW") is False,
        "P014_GATEWAY_CONFIG_MOUNT_INVALID",
    )
    if "/tmp" in gateway_mounts:
        _require(gateway_mounts["/tmp"].get("Type") == "tmpfs", "P014_GATEWAY_TMPFS_INVALID")

    app_labels = _mapping(app_config.get("Labels"), "P014_APP_LABELS_INVALID")
    gateway_labels = _mapping(gateway_config.get("Labels"), "P014_GATEWAY_LABELS_INVALID")
    _require(
        app_labels.get("app.delta-lemmata.release-stage") == "public-alpha",
        "P014_APP_RELEASE_LABEL_INVALID",
    )
    _require(
        app_labels.get("org.opencontainers.image.source") == SOURCE_URL,
        "P014_APP_SOURCE_LABEL_INVALID",
    )
    _require(
        app_labels.get("org.opencontainers.image.revision") == build_id,
        "P014_APP_REVISION_LABEL_INVALID",
    )
    _require(
        app_labels.get("org.opencontainers.image.licenses") == "MIT",
        "P014_APP_LICENSE_LABEL_INVALID",
    )
    _require(
        gateway_labels.get("app.delta-lemmata.release-stage") == "public-alpha",
        "P014_GATEWAY_RELEASE_LABEL_INVALID",
    )

    app_image_id = app.get("Image")
    gateway_image_id = gateway.get("Image")
    _require(
        isinstance(app_image_id, str)
        and SECRET_VALUE.fullmatch(app_image_id.removeprefix("sha256:")),
        "P014_APP_IMAGE_ID_INVALID",
    )
    _require(
        isinstance(gateway_image_id, str)
        and SECRET_VALUE.fullmatch(gateway_image_id.removeprefix("sha256:")),
        "P014_GATEWAY_IMAGE_ID_INVALID",
    )
    return app_image_id, gateway_image_id


def _docker_inspect(identifier: str) -> Mapping[str, Any]:
    completed = subprocess.run(
        ["docker", "inspect", identifier],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if completed.returncode != 0:
        raise RuntimeInspectionError("P014_DOCKER_INSPECT_FAILED")
    try:
        loaded = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeInspectionError("P014_DOCKER_INSPECT_INVALID") from error
    _require(isinstance(loaded, list) and len(loaded) == 1, "P014_DOCKER_INSPECT_INVALID")
    return _mapping(loaded[0], "P014_DOCKER_INSPECT_INVALID")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True)
    parser.add_argument("--gateway", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_args(argv)
    app_image, gateway_image = validate_runtime_records(
        _docker_inspect(arguments.app),
        _docker_inspect(arguments.gateway),
    )
    print(f"p014-runtime-inspection-ok app={app_image} gateway={gateway_image}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
