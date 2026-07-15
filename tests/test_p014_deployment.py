from __future__ import annotations

import copy
import http.server
import importlib.util
import os
import socketserver
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_p014_deployment.py"
GENERATOR_PATH = ROOT / "scripts" / "generate_p014_secrets.py"
SMOKE_PATH = ROOT / "scripts" / "smoke_p014_stack.sh"


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load_script("validate_p014_deployment", VALIDATOR_PATH)
GENERATOR = _load_script("generate_p014_secrets", GENERATOR_PATH)


def test_public_alpha_deployment_package_is_fail_closed() -> None:
    VALIDATOR.validate()


def test_runtime_gate_cleans_failed_start_and_logs_only_the_pre_public_gateway() -> None:
    gate = (ROOT / "scripts" / "run_p014_runtime_gate.sh").read_text(encoding="utf-8")
    marker = "STACK_STARTED=1\nif ! docker compose"
    assert marker in gate
    assert gate.index("STACK_STARTED=1") < gate.index("up \\")
    assert "--no-color --tail 100 gateway" in gate
    assert "--no-color --tail 100 app" not in gate
    assert "p014-runtime-stack-start-failed" in gate
    assert "p014-runtime-published-gateway-failed" in gate
    assert gate.count("gateway_start_diagnostics") == 3


def test_stack_smoke_waits_for_delayed_published_gateway() -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.headers.get("Host") == "invalid.example":
                self.send_response(421)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, _format: str, *args: object) -> None:
            del args

    server = socketserver.TCPServer(("127.0.0.1", 0), Handler, bind_and_activate=False)
    server.server_bind()
    port = server.server_address[1]

    def delayed_server() -> None:
        time.sleep(0.15)
        server.server_activate()
        server.serve_forever(poll_interval=0.01)

    thread = threading.Thread(target=delayed_server, daemon=True)
    thread.start()
    env = {
        **os.environ,
        "DELTA_SMOKE_URL": f"http://127.0.0.1:{port}",
        "DELTA_SMOKE_READINESS_ATTEMPTS": "20",
        "DELTA_SMOKE_READINESS_DELAY": "0.05",
    }
    try:
        completed = subprocess.run(
            [str(SMOKE_PATH)],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)

    assert completed.returncode == 0
    assert completed.stdout == "p014-stack-smoke-ok\n"
    assert completed.stderr == ""


def test_stack_smoke_fails_closed_after_bounded_readiness_attempts() -> None:
    server = socketserver.TCPServer(("127.0.0.1", 0), None, bind_and_activate=False)
    server.server_bind()
    port = server.server_address[1]
    env = {
        **os.environ,
        "DELTA_SMOKE_URL": f"http://127.0.0.1:{port}",
        "DELTA_SMOKE_READINESS_ATTEMPTS": "2",
        "DELTA_SMOKE_READINESS_DELAY": "0.01",
    }
    try:
        completed = subprocess.run(
            [str(SMOKE_PATH)],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    finally:
        server.server_close()

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "p014-smoke-published-gateway-unavailable" in completed.stderr


def test_compose_tampering_is_rejected() -> None:
    compose = VALIDATOR._load_compose(ROOT / "deploy" / "public-alpha" / "compose.yml")
    copied = {**compose, "services": {**compose["services"]}}
    copied["services"]["app"] = {**copied["services"]["app"], "read_only": False}
    with pytest.raises(VALIDATOR.DeploymentValidationError, match="P014_APP_HARDENING_INVALID"):
        VALIDATOR._validate_compose(copied)


def test_application_cannot_join_the_loopback_publication_network() -> None:
    compose = copy.deepcopy(
        VALIDATOR._load_compose(ROOT / "deploy" / "public-alpha" / "compose.yml")
    )
    compose["services"]["app"]["networks"].append("delta_edge")
    with pytest.raises(VALIDATOR.DeploymentValidationError, match="P014_APP_NETWORK_INVALID"):
        VALIDATOR._validate_compose(compose)


def test_gateway_requires_the_loopback_publication_network() -> None:
    compose = copy.deepcopy(
        VALIDATOR._load_compose(ROOT / "deploy" / "public-alpha" / "compose.yml")
    )
    compose["services"]["gateway"]["networks"] = ["delta_internal"]
    with pytest.raises(
        VALIDATOR.DeploymentValidationError,
        match="P014_GATEWAY_NETWORK_INVALID",
    ):
        VALIDATOR._validate_compose(compose)


def test_gateway_requires_every_nginx_temp_directory_in_bounded_tmpfs() -> None:
    compose = copy.deepcopy(
        VALIDATOR._load_compose(ROOT / "deploy" / "public-alpha" / "compose.yml")
    )
    gateway = compose["services"]["gateway"]
    gateway["entrypoint"][2] = gateway["entrypoint"][2].replace(
        "/tmp/fastcgi_temp", "/tmp/missing_fastcgi_temp"
    )
    with pytest.raises(
        VALIDATOR.DeploymentValidationError,
        match="P014_GATEWAY_TEMP_SETUP_INCOMPLETE",
    ):
        VALIDATOR._validate_compose(compose)


def test_gateway_rejects_writable_nginx_cache_mount() -> None:
    compose = copy.deepcopy(
        VALIDATOR._load_compose(ROOT / "deploy" / "public-alpha" / "compose.yml")
    )
    compose["services"]["gateway"]["volumes"].append("gateway-cache:/var/cache/nginx:rw")
    with pytest.raises(
        VALIDATOR.DeploymentValidationError,
        match="P014_GATEWAY_CACHE_MOUNT_FORBIDDEN",
    ):
        VALIDATOR._validate_compose(compose)


def test_secret_generator_creates_three_distinct_private_values(tmp_path: Path) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    output = private / "runtime.env"
    GENERATOR.create_secret_file(output)

    info = os.lstat(output)
    assert stat.S_ISREG(info.st_mode)
    assert stat.S_IMODE(info.st_mode) == 0o600
    records = dict(
        line.split("=", maxsplit=1) for line in output.read_text(encoding="ascii").splitlines()
    )
    assert tuple(records) == GENERATOR.SECRET_NAMES
    assert len(set(records.values())) == 3
    assert all(
        len(value) == 64 and bytes.fromhex(value).hex() == value for value in records.values()
    )


def test_secret_generator_refuses_overwrite_and_never_prints_values(tmp_path: Path) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    output = private / "runtime.env"
    first = subprocess.run(
        [sys.executable, str(GENERATOR_PATH), "--output", str(output)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    before = output.read_text(encoding="ascii")
    second = subprocess.run(
        [sys.executable, str(GENERATOR_PATH), "--output", str(output)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0
    assert first.stdout == "p014-secrets-created\n"
    assert second.returncode == 1
    assert second.stderr == "P014_SECRET_FILE_EXISTS\n"
    assert output.read_text(encoding="ascii") == before
    assert all(
        value not in first.stdout + first.stderr + second.stdout + second.stderr
        for value in before.split("=")[1:]
    )


def test_secret_generator_rejects_relative_or_public_parent(tmp_path: Path) -> None:
    with pytest.raises(GENERATOR.SecretFileError, match="P014_SECRET_PATH_NOT_ABSOLUTE"):
        GENERATOR.create_secret_file(Path("runtime.env"))
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    with pytest.raises(GENERATOR.SecretFileError, match="P014_SECRET_PARENT_NOT_PRIVATE"):
        GENERATOR.create_secret_file(public / "runtime.env")
