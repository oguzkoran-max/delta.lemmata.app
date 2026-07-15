from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_p014_deployment.py"
GENERATOR_PATH = ROOT / "scripts" / "generate_p014_secrets.py"


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


def test_compose_tampering_is_rejected() -> None:
    compose = VALIDATOR._load_compose(ROOT / "deploy" / "public-alpha" / "compose.yml")
    copied = {**compose, "services": {**compose["services"]}}
    copied["services"]["app"] = {**copied["services"]["app"], "read_only": False}
    with pytest.raises(VALIDATOR.DeploymentValidationError, match="P014_APP_HARDENING_INVALID"):
        VALIDATOR._validate_compose(copied)


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
