#!/usr/bin/env python3
"""Validate the retained P006 direct-stylo evidence and its source binding."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, NoReturn

from validate_p006_oracle_outputs import FIXTURE_DIR, MANIFEST_PATH, validate_output_directory

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "provenance" / "evidence" / "P006" / "oracle-v1"
EVIDENCE_PREFIX = "provenance/evidence/P006/oracle-v1"
EVIDENCE_COMMIT = "b5a842fdee5456c7f5f9d0397c0f5a2f7d7a336f"
RUN_RECORD = ROOT / "provenance" / "runs" / "RUN-20260714-0001.json"
SOURCE_PATHS = (
    "containers/Dockerfile",
    "renv.lock",
    "schemas/direct-stylo-oracle-v1.schema.json",
    "scripts/generate_p006_fixtures.py",
    "scripts/oracles/p006-direct-stylo-v1.R",
    "tests/fixtures/stylo/p006-whole-text-v1/LICENSE",
    "tests/fixtures/stylo/p006-whole-text-v1/fixture-manifest.json",
)
HEX_40 = re.compile(r"^[0-9a-f]{40}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
PINNED_IMAGE = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
RUN_CONFIGURATION_HASHES = {
    ".github/workflows/p006-oracle-freeze.yml": (
        "82ed399f60ba5ce1d884c086a6eabe90295c1bf1b711f750ff173a3c282d7fd0"
    ),
    "containers/Dockerfile": ("8935705128aa80032c0cc3b43b0b13c501fd4b9cddcbd28f222530a85805c1b5"),
    "renv.lock": "bb792d224470650053412194edc35f3fd866673bd78d30ca756fcec3ad86ea1d",
    "schemas/direct-stylo-oracle-v1.schema.json": (
        "8adca72f556ab3e1c46d800bdab889e9de5f5ba769b23d86dd6caa15729519e2"
    ),
    "scripts/freeze_p006_oracle.py": (
        "a227cf631363439ea3e8add390bafcd57bf65f72329b716dadf9a9563cd2d506"
    ),
    "scripts/generate_p006_fixtures.py": (
        "dd4dfe83c2ef23575757baba558cd0fd6825ffdd7e2ed38f087cf6e61ce80a6a"
    ),
    "scripts/oracles/p006-direct-stylo-v1.R": (
        "325e96dc073fdf8b241df0e759524afe833dc357e6388d18a928660c9fefcd84"
    ),
    "scripts/validate_p006_oracle_outputs.py": (
        "23edabfed5032486fded33599818d3e2d0d323aee2a54c19a3c39dede9d87a57"
    ),
    "scripts/verify.sh": ("6ac086fabf5e99e34478ae5035773ae12530afa6dce3da8b5597131e22ccfee0"),
    "src/delta_lemmata/stylo_contracts.py": (
        "a85d1c76302fa705556ea793ae5e3f23814df6c5abb4964d078e320a55dad383"
    ),
}


def _fail(code: str) -> NoReturn:
    raise ValueError(code)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            _fail("P006_FROZEN_ORACLE_DUPLICATE_KEY")
        value[key] = item
    return value


def _read_json(path: Path, *, maximum_bytes: int) -> tuple[bytes, dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        _fail("P006_FROZEN_ORACLE_FILE_INVALID")
    payload = path.read_bytes()
    if not payload or len(payload) > maximum_bytes:
        _fail("P006_FROZEN_ORACLE_FILE_INVALID")
    try:
        value = json.loads(payload, object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("P006_FROZEN_ORACLE_JSON_INVALID")
    if not isinstance(value, dict) or payload != _canonical_json(value):
        _fail("P006_FROZEN_ORACLE_JSON_INVALID")
    return payload, value


def _manifest_entries() -> list[dict[str, str]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries: list[dict[str, str]] = []
    for raw_entry in manifest["fixtures"]:
        input_file = raw_entry["input_file"]
        input_path = FIXTURE_DIR / input_file
        digest = _sha256(input_path)
        if digest != raw_entry["input_sha256"]:
            _fail("P006_FROZEN_ORACLE_FIXTURE_INVALID")
        entries.append(
            {
                "fixture_ref": raw_entry["fixture_ref"],
                "input_file": input_file,
                "input_sha256": digest,
            }
        )
    return entries


def _direct_name(input_file: str) -> str:
    suffix = ".input.json"
    if not input_file.endswith(suffix):
        _fail("P006_FROZEN_ORACLE_FIXTURE_INVALID")
    return f"{input_file[: -len(suffix)]}.direct.json"


def _expected_files(entries: list[dict[str, str]]) -> set[str]:
    return {
        "oracle-freeze.json",
        "oracle-freeze.sha256",
        "session-info.json",
        *(f"direct-reference/{_direct_name(entry['input_file'])}" for entry in entries),
    }


def _validate_file_set(evidence: Path, expected_files: set[str]) -> None:
    if evidence.is_symlink() or not evidence.is_dir():
        _fail("P006_FROZEN_ORACLE_DIRECTORY_INVALID")
    actual_files: set[str] = set()
    for path in evidence.rglob("*"):
        if path.is_symlink():
            _fail("P006_FROZEN_ORACLE_FILE_SET_INVALID")
        if path.is_file():
            actual_files.add(path.relative_to(evidence).as_posix())
        elif not path.is_dir():
            _fail("P006_FROZEN_ORACLE_FILE_SET_INVALID")
    if actual_files != expected_files:
        _fail("P006_FROZEN_ORACLE_FILE_SET_INVALID")


def _checksum_manifest(evidence: Path) -> bytes:
    retained = sorted(
        relative for relative in _relative_files(evidence) if relative != "oracle-freeze.sha256"
    )
    return "".join(
        f"{_sha256(evidence / relative)}  {relative}\n" for relative in retained
    ).encode()


def _relative_files(evidence: Path) -> list[str]:
    return [path.relative_to(evidence).as_posix() for path in evidence.rglob("*") if path.is_file()]


def _git_bytes(*arguments: str, allow_empty: bool = False) -> bytes:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    if completed.returncode != 0 or (not allow_empty and not completed.stdout):
        _fail("P006_FROZEN_ORACLE_SOURCE_INVALID")
    return completed.stdout


def _git_source(source_commit: str, source_path: str) -> bytes:
    return _git_bytes("show", f"{source_commit}:{source_path}")


def _validate_source_binding(metadata: dict[str, Any]) -> dict[str, bytes]:
    source_commit = metadata.get("source_commit")
    source_hashes = metadata.get("source_hashes")
    if (
        not isinstance(source_commit, str)
        or not HEX_40.fullmatch(source_commit)
        or not isinstance(source_hashes, dict)
        or set(source_hashes) != set(SOURCE_PATHS)
    ):
        _fail("P006_FROZEN_ORACLE_SOURCE_INVALID")
    sources: dict[str, bytes] = {}
    for path in SOURCE_PATHS:
        expected = source_hashes[path]
        if not isinstance(expected, str) or not HEX_64.fullmatch(expected):
            _fail("P006_FROZEN_ORACLE_SOURCE_INVALID")
        payload = _git_source(source_commit, path)
        if _sha256_bytes(payload) != expected:
            _fail("P006_FROZEN_ORACLE_SOURCE_INVALID")
        sources[path] = payload
    return sources


def _validate_evidence_commit(
    evidence: Path,
    metadata: dict[str, Any],
    expected_files: set[str],
) -> None:
    source_commit = metadata.get("source_commit")
    parent = _git_bytes("show", "-s", "--format=%P", EVIDENCE_COMMIT).decode().strip()
    if parent != source_commit:
        _fail("P006_FROZEN_ORACLE_EVIDENCE_COMMIT_INVALID")

    expected_changes = {f"A\t{EVIDENCE_PREFIX}/{relative_path}" for relative_path in expected_files}
    actual_changes = set(
        _git_bytes(
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            EVIDENCE_COMMIT,
        )
        .decode()
        .splitlines()
    )
    if actual_changes != expected_changes:
        _fail("P006_FROZEN_ORACLE_EVIDENCE_COMMIT_INVALID")

    for relative_path in expected_files:
        committed = _git_source(
            EVIDENCE_COMMIT,
            f"{EVIDENCE_PREFIX}/{relative_path}",
        )
        if (evidence / relative_path).read_bytes() != committed:
            _fail("P006_FROZEN_ORACLE_EVIDENCE_COMMIT_INVALID")

    try:
        run = json.loads(RUN_RECORD.read_text(encoding="utf-8"))
        recorded_source = run["git_commit"]
        recorded_evidence = run["environment"]["evidence_commit"]
        configuration = {item["path"]: item["sha256"] for item in run["configuration_artifacts"]}
        inputs = {item["path"]: item["sha256"] for item in run["input_artifacts"]}
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
        _fail("P006_FROZEN_ORACLE_EVIDENCE_COMMIT_INVALID")
    if (
        recorded_source != source_commit
        or recorded_evidence != EVIDENCE_COMMIT
        or configuration != RUN_CONFIGURATION_HASHES
        or any(inputs.get(path) != digest for path, digest in RUN_CONFIGURATION_HASHES.items())
    ):
        _fail("P006_FROZEN_ORACLE_EVIDENCE_COMMIT_INVALID")
    for path, digest in RUN_CONFIGURATION_HASHES.items():
        if _sha256_bytes(_git_source(source_commit, path)) != digest:
            _fail("P006_FROZEN_ORACLE_EVIDENCE_COMMIT_INVALID")


def _snapshot(evidence: Path, entries: list[dict[str, str]]) -> list[dict[str, str | int]]:
    paths = [evidence / "direct-reference" / _direct_name(entry["input_file"]) for entry in entries]
    paths.append(evidence / "session-info.json")
    return [
        {
            "byte_count": path.stat().st_size,
            "path": path.name,
            "sha256": _sha256(path),
        }
        for path in sorted(paths)
    ]


def _outputs(evidence: Path, entries: list[dict[str, str]]) -> list[dict[str, str | int]]:
    paths = [evidence / "direct-reference" / _direct_name(entry["input_file"]) for entry in entries]
    return [
        {
            "byte_count": path.stat().st_size,
            "path": path.relative_to(evidence).as_posix(),
            "sha256": _sha256(path),
        }
        for path in sorted(paths)
    ]


def _base_image(dockerfile: bytes) -> str:
    for line in dockerfile.decode("utf-8").splitlines()[:4]:
        prefix = "FROM --platform=linux/amd64 "
        if line.startswith(prefix):
            return line.removeprefix(prefix)
    _fail("P006_FROZEN_ORACLE_ENVIRONMENT_INVALID")


def _validate_metadata(
    metadata: dict[str, Any],
    evidence: Path,
    entries: list[dict[str, str]],
) -> None:
    if set(metadata) != {
        "canonical_environment",
        "claim_boundary",
        "fixture_inputs",
        "outputs",
        "schema_version",
        "source_commit",
        "source_hashes",
    }:
        _fail("P006_FROZEN_ORACLE_METADATA_INVALID")
    if (
        metadata["schema_version"] != "p006-oracle-freeze-v1"
        or metadata["claim_boundary"] != "fixture-local whole-text parity only"
        or metadata["fixture_inputs"] != entries
        or metadata["outputs"] != _outputs(evidence, entries)
    ):
        _fail("P006_FROZEN_ORACLE_METADATA_INVALID")
    sources = _validate_source_binding(metadata)
    environment = metadata["canonical_environment"]
    if not isinstance(environment, dict) or set(environment) != {
        "base_image",
        "built_image_id",
        "network",
        "platform",
        "read_only_root",
        "run_count",
        "run_snapshots",
        "runs_byte_identical",
    }:
        _fail("P006_FROZEN_ORACLE_ENVIRONMENT_INVALID")
    snapshot = _snapshot(evidence, entries)
    if (
        environment["base_image"] != _base_image(sources["containers/Dockerfile"])
        or not isinstance(environment["base_image"], str)
        or not PINNED_IMAGE.fullmatch(environment["base_image"])
        or not isinstance(environment["built_image_id"], str)
        or not IMAGE_ID.fullmatch(environment["built_image_id"])
        or environment["network"] != "none"
        or environment["platform"] != "linux/amd64"
        or environment["read_only_root"] is not True
        or environment["run_count"] != 2
        or environment["run_snapshots"] != [snapshot, snapshot]
        or environment["runs_byte_identical"] is not True
    ):
        _fail("P006_FROZEN_ORACLE_ENVIRONMENT_INVALID")


def validate_frozen_oracle(evidence: Path = DEFAULT_EVIDENCE) -> None:
    """Reject an altered, incomplete, unbound, or contract-invalid freeze."""

    entries = _manifest_entries()
    expected_files = _expected_files(entries)
    _validate_file_set(evidence, expected_files)
    checksum_path = evidence / "oracle-freeze.sha256"
    if checksum_path.read_bytes() != _checksum_manifest(evidence):
        _fail("P006_FROZEN_ORACLE_CHECKSUM_INVALID")
    _metadata_bytes, metadata = _read_json(
        evidence / "oracle-freeze.json",
        maximum_bytes=65536,
    )
    _validate_metadata(metadata, evidence, entries)
    _validate_evidence_commit(evidence, metadata, expected_files)
    validate_output_directory(
        evidence / "direct-reference",
        session_path=evidence / "session-info.json",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    validate_frozen_oracle(args.evidence)
    print("p006-frozen-oracle-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
