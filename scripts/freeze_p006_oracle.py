#!/usr/bin/env python3
"""Freeze byte-identical P006 direct-stylo evidence from canonical Linux runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from validate_p006_fixture_v2 import (
    FIXTURE_DIR as V2_FIXTURE_DIR,
)
from validate_p006_fixture_v2 import (
    MANIFEST_PATH as V2_MANIFEST_PATH,
)
from validate_p006_oracle_outputs import (
    FIXTURE_DIR,
    MANIFEST_PATH,
    validate_output_directory,
    validate_output_directory_v2,
)

ROOT = Path(__file__).resolve().parents[1]
ORACLE_SCRIPT = ROOT / "scripts" / "oracles" / "p006-direct-stylo-v1.R"
ORACLE_SCHEMA = ROOT / "schemas" / "direct-stylo-oracle-v1.schema.json"
GENERATOR = ROOT / "scripts" / "generate_p006_fixtures.py"
V2_GENERATOR = ROOT / "scripts" / "generate_p006_fixtures_v2.py"
DOCKERFILE = ROOT / "containers" / "Dockerfile"
RENV_LOCK = ROOT / "renv.lock"
HEX_40 = re.compile(r"^[0-9a-f]{40}$")
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class SuiteConfiguration:
    fixture_dir: Path
    manifest_path: Path
    generator: Path
    freeze_schema_version: str
    source_paths: tuple[Path, ...]
    validate: Callable[[Path], object]


def _suite_configuration(suite: str) -> SuiteConfiguration:
    if suite == "v1":
        return SuiteConfiguration(
            fixture_dir=FIXTURE_DIR,
            manifest_path=MANIFEST_PATH,
            generator=GENERATOR,
            freeze_schema_version="p006-oracle-freeze-v1",
            source_paths=(
                DOCKERFILE,
                RENV_LOCK,
                ORACLE_SCHEMA,
                GENERATOR,
                ORACLE_SCRIPT,
                FIXTURE_DIR / "LICENSE",
                MANIFEST_PATH,
            ),
            validate=validate_output_directory,
        )
    if suite == "v2":
        return SuiteConfiguration(
            fixture_dir=V2_FIXTURE_DIR,
            manifest_path=V2_MANIFEST_PATH,
            generator=V2_GENERATOR,
            freeze_schema_version="p006-oracle-freeze-v2",
            source_paths=(
                ROOT / ".github" / "workflows" / "p006-oracle-v2-capture.yml",
                DOCKERFILE,
                RENV_LOCK,
                ORACLE_SCHEMA,
                ROOT / "scripts" / "freeze_p006_oracle.py",
                V2_GENERATOR,
                ORACLE_SCRIPT,
                ROOT / "scripts" / "validate_p006_fixture_v2.py",
                ROOT / "scripts" / "validate_p006_oracle_outputs.py",
                ROOT / "scripts" / "verify.sh",
                ROOT / "src" / "delta_lemmata" / "stylo_contracts.py",
                V2_FIXTURE_DIR / "LICENSE",
                V2_MANIFEST_PATH,
            ),
            validate=validate_output_directory_v2,
        )
    raise ValueError("P006_ORACLE_SUITE_INVALID")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()


def _base_image() -> str:
    first_lines = DOCKERFILE.read_text(encoding="utf-8").splitlines()[:4]
    for line in first_lines:
        if line.startswith("FROM --platform=linux/amd64 "):
            return line.removeprefix("FROM --platform=linux/amd64 ")
    raise ValueError("P006_ORACLE_BASE_IMAGE_INVALID")


def _input_records(configuration: SuiteConfiguration) -> list[dict[str, str]]:
    manifest = json.loads(configuration.manifest_path.read_text(encoding="utf-8"))
    records: list[dict[str, str]] = []
    for entry in manifest["fixtures"]:
        input_path = configuration.fixture_dir / entry["input_file"]
        if _sha256(input_path) != entry["input_sha256"]:
            raise ValueError("P006_ORACLE_INPUT_HASH_INVALID")
        records.append(
            {
                "fixture_ref": entry["fixture_ref"],
                "input_file": entry["input_file"],
                "input_sha256": entry["input_sha256"],
            }
        )
    return records


def _source_hashes(configuration: SuiteConfiguration) -> dict[str, str]:
    return {path.relative_to(ROOT).as_posix(): _sha256(path) for path in configuration.source_paths}


def _run_snapshot(directory: Path) -> list[dict[str, str | int]]:
    return [
        {
            "byte_count": path.stat().st_size,
            "path": path.name,
            "sha256": _sha256(path),
        }
        for path in sorted(directory.iterdir())
    ]


def _require_byte_identical(first: Path, second: Path) -> tuple[list[dict[str, str | int]], ...]:
    if first.samefile(second):
        raise ValueError("P006_ORACLE_RUNS_NOT_DISTINCT")
    first_names = tuple(path.name for path in sorted(first.iterdir()))
    second_names = tuple(path.name for path in sorted(second.iterdir()))
    if first_names != second_names:
        raise ValueError("P006_ORACLE_RUN_MISMATCH")
    for name in first_names:
        if (first / name).read_bytes() != (second / name).read_bytes():
            raise ValueError("P006_ORACLE_RUN_MISMATCH")
    return _run_snapshot(first), _run_snapshot(second)


def freeze(
    source_directory: Path,
    comparison_directory: Path,
    destination: Path,
    source_commit: str,
    image_id: str,
    *,
    suite: str = "v1",
) -> None:
    if not HEX_40.fullmatch(source_commit) or not IMAGE_ID.fullmatch(image_id):
        raise ValueError("P006_ORACLE_IDENTITY_INVALID")
    configuration = _suite_configuration(suite)
    configuration.validate(source_directory)
    configuration.validate(comparison_directory)
    run_snapshots = _require_byte_identical(source_directory, comparison_directory)
    if destination.exists():
        raise ValueError("P006_ORACLE_DESTINATION_EXISTS")
    direct_destination = destination / "direct-reference"
    direct_destination.mkdir(parents=True)

    output_records: list[dict[str, str | int]] = []
    for source in sorted(source_directory.glob("*.direct.json")):
        target = direct_destination / source.name
        shutil.copyfile(source, target)
        target.chmod(0o644)
        output_records.append(
            {
                "byte_count": target.stat().st_size,
                "path": target.relative_to(destination).as_posix(),
                "sha256": _sha256(target),
            }
        )
    session_target = destination / "session-info.json"
    shutil.copyfile(source_directory / "session-info.json", session_target)
    session_target.chmod(0o644)

    metadata = {
        "canonical_environment": {
            "base_image": _base_image(),
            "built_image_id": image_id,
            "network": "none",
            "platform": "linux/amd64",
            "read_only_root": True,
            "run_count": 2,
            "run_snapshots": run_snapshots,
            "runs_byte_identical": True,
        },
        "claim_boundary": "fixture-local whole-text parity only",
        "fixture_inputs": _input_records(configuration),
        "outputs": output_records,
        "schema_version": configuration.freeze_schema_version,
        "source_commit": source_commit,
        "source_hashes": _source_hashes(configuration),
    }
    freeze_path = destination / "oracle-freeze.json"
    freeze_path.write_bytes(_canonical_json(metadata))
    freeze_path.chmod(0o644)

    retained = sorted(
        path
        for path in destination.rglob("*")
        if path.is_file() and path.name != "oracle-freeze.sha256"
    )
    checksum_path = destination / "oracle-freeze.sha256"
    checksum_path.write_text(
        "".join(
            f"{_sha256(path)}  {path.relative_to(destination).as_posix()}\n" for path in retained
        ),
        encoding="utf-8",
    )
    checksum_path.chmod(0o644)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_directory", type=Path)
    parser.add_argument("comparison_directory", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--suite", choices=("v1", "v2"), default="v1")
    args = parser.parse_args()
    freeze(
        args.source_directory,
        args.comparison_directory,
        args.destination,
        args.source_commit,
        args.image_id,
        suite=args.suite,
    )
    print("p006-oracle-freeze-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
