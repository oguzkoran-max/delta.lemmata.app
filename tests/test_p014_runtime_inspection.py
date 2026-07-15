from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "inspect_p014_runtime", ROOT / "scripts" / "inspect_p014_runtime.py"
)
assert SPEC is not None and SPEC.loader is not None
INSPECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSPECTOR)

APP_ID = "sha256:" + "a" * 64
GATEWAY_ID = "sha256:" + "b" * 64
BUILD_ID = "c" * 40


def _common(
    *, user: str, pids: int, cpus: int, memory: int, image_reference: str, image_id: str
) -> dict[str, Any]:
    return {
        "Config": {
            "User": user,
            "Image": image_reference,
            "Env": [],
            "Labels": {"app.delta-lemmata.release-stage": "public-alpha"},
        },
        "HostConfig": {
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
            "PidsLimit": pids,
            "NanoCpus": cpus,
            "Memory": memory,
            "MemorySwap": memory,
            "RestartPolicy": {"Name": "on-failure", "MaximumRetryCount": 3},
            "Tmpfs": {},
        },
        "State": {"Running": True, "Health": {"Status": "healthy"}},
        "NetworkSettings": {"Networks": {"delta-public-alpha_delta_internal": {}}},
        "Image": image_id,
    }


def _records() -> tuple[dict[str, Any], dict[str, Any]]:
    app = _common(
        user="10001:10001",
        pids=128,
        cpus=1_500_000_000,
        memory=INSPECTOR.APP_MEMORY,
        image_reference=APP_ID,
        image_id=APP_ID,
    )
    app.update(
        {
            "Path": "/opt/delta/.venv/bin/streamlit",
            "Mounts": [
                {"Type": "tmpfs", "Destination": "/tmp", "RW": True},
                {
                    "Type": "tmpfs",
                    "Destination": "/var/lib/delta/runtime",
                    "RW": True,
                },
            ],
        }
    )
    app["Config"]["Env"] = [
        "DELTA_ENV=production",
        f"DELTA_BUILD_ID={BUILD_ID}",
        "DELTA_EXTERNAL_NETWORK=disabled",
        "DELTA_RUNTIME_ROOT=/var/lib/delta/runtime",
        f"DELTA_JOB_OWNER_SECRET_HEX={'1' * 64}",
        f"DELTA_PREPARATION_AUTHORITY_SECRET_HEX={'2' * 64}",
        f"DELTA_RECOVERY_RECEIPT_SECRET_HEX={'3' * 64}",
    ]
    app["Config"]["Labels"].update(
        {
            "org.opencontainers.image.source": INSPECTOR.SOURCE_URL,
            "org.opencontainers.image.revision": BUILD_ID,
            "org.opencontainers.image.licenses": "MIT",
        }
    )
    app["HostConfig"]["PortBindings"] = {}
    app["HostConfig"]["Init"] = True
    app["HostConfig"]["Tmpfs"] = {
        destination: "rw,nosuid,nodev,noexec,"
        + ",".join(f"{name}={value}" for name, value in options.items())
        for destination, options in INSPECTOR.APP_TMPFS.items()
    }

    gateway = _common(
        user="101:101",
        pids=64,
        cpus=250_000_000,
        memory=INSPECTOR.GATEWAY_MEMORY,
        image_reference=INSPECTOR.GATEWAY_REFERENCE,
        image_id=GATEWAY_ID,
    )
    gateway["Mounts"] = [
        {"Type": "tmpfs", "Destination": "/tmp", "RW": True},
        {"Type": "bind", "Destination": "/etc/nginx/nginx.conf", "RW": False},
    ]
    gateway["HostConfig"]["PortBindings"] = {
        "8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8502"}]
    }
    gateway["HostConfig"]["Tmpfs"] = {
        destination: "rw,nosuid,nodev,noexec,"
        + ",".join(f"{name}={value}" for name, value in options.items())
        for destination, options in INSPECTOR.GATEWAY_TMPFS.items()
    }
    return app, gateway


def test_runtime_inspection_accepts_only_the_bounded_profile() -> None:
    app, gateway = _records()
    assert INSPECTOR.validate_runtime_records(app, gateway) == (APP_ID, GATEWAY_ID)


def test_runtime_inspection_accepts_engine_that_reports_short_tmpfs_only_in_host_config() -> None:
    app, gateway = _records()
    app["Mounts"] = []
    gateway["Mounts"] = [gateway["Mounts"][1]]
    assert INSPECTOR.validate_runtime_records(app, gateway) == (APP_ID, GATEWAY_ID)


@pytest.mark.parametrize(
    ("target", "path", "value", "code"),
    [
        ("app", ("HostConfig", "ReadonlyRootfs"), False, "P014_RUNTIME_ROOT_WRITABLE"),
        ("app", ("HostConfig", "NanoCpus"), 0, "P014_RUNTIME_CPU_LIMIT_INVALID"),
        ("app", ("HostConfig", "PortBindings"), {"8501/tcp": [{}]}, "P014_APP_PORT_PUBLISHED"),
        ("gateway", ("HostConfig", "PidsLimit"), 0, "P014_RUNTIME_PID_LIMIT_INVALID"),
        ("gateway", ("State", "Health", "Status"), "unhealthy", "P014_RUNTIME_NOT_HEALTHY"),
        ("app", ("HostConfig", "Init"), False, "P014_APP_INIT_INVALID"),
        (
            "gateway",
            ("HostConfig", "Tmpfs", "/tmp"),
            "rw,nosuid,nodev,noexec,size=1g,mode=0700,uid=101,gid=101",
            "P014_RUNTIME_TMPFS_OPTIONS_INVALID",
        ),
        (
            "app",
            ("Config", "Labels", "org.opencontainers.image.revision"),
            "d" * 40,
            "P014_APP_REVISION_LABEL_INVALID",
        ),
    ],
)
def test_runtime_inspection_rejects_weakened_controls(
    target: str, path: tuple[str, ...], value: Any, code: str
) -> None:
    app, gateway = _records()
    record = app if target == "app" else gateway
    changed = copy.deepcopy(record)
    cursor = changed
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(INSPECTOR.RuntimeInspectionError, match=code):
        INSPECTOR.validate_runtime_records(
            changed if target == "app" else app, changed if target == "gateway" else gateway
        )


def test_runtime_inspection_rejects_secret_reuse_without_exposing_value() -> None:
    app, gateway = _records()
    reused = "4" * 64
    app["Config"]["Env"] = [
        entry
        for entry in app["Config"]["Env"]
        if not entry.startswith(
            ("DELTA_JOB_OWNER_SECRET_HEX=", "DELTA_PREPARATION_AUTHORITY_SECRET_HEX=")
        )
    ] + [
        f"DELTA_JOB_OWNER_SECRET_HEX={reused}",
        f"DELTA_PREPARATION_AUTHORITY_SECRET_HEX={reused}",
    ]
    with pytest.raises(INSPECTOR.RuntimeInspectionError) as captured:
        INSPECTOR.validate_runtime_records(app, gateway)
    assert str(captured.value) == "P014_RUNTIME_SECRET_REUSE"
    assert reused not in str(captured.value)
