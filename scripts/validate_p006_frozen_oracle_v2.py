#!/usr/bin/env python3
"""Validate the retained adversarial P006 oracle v2 and its audit chain."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import validate_p006_frozen_oracle as shared
from validate_p006_fixture_v2 import FIXTURE_DIR, MANIFEST_PATH
from validate_p006_oracle_outputs import validate_output_directory_v2

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "provenance" / "evidence" / "P006" / "oracle-v2"
EVIDENCE_PREFIX = "provenance/evidence/P006/oracle-v2"
SOURCE_COMMIT = "c6a07e1b62440d56feabf76fd7c58e4b58b63477"
EVIDENCE_COMMIT = "42fe09b690d953fbcf45fcf48fa6d8f462fb8251"
RUN_RECORD = ROOT / "provenance" / "runs" / "RUN-20260714-0002.json"
TRANSPORT_SHA256 = "c94f84b3eb341fc0b16e8bee134f32841080f24ac35d333c838950501db4216c"
SOURCE_PATHS = (
    ".github/workflows/ci.yml",
    "containers/Dockerfile",
    "renv.lock",
    "schemas/direct-stylo-oracle-v1.schema.json",
    "scripts/freeze_p006_oracle.py",
    "scripts/generate_p006_fixtures_v2.py",
    "scripts/oracles/p006-direct-stylo-v1.R",
    "scripts/p006_log_transport.py",
    "scripts/validate_p006_fixture_v2.py",
    "scripts/validate_p006_oracle_outputs.py",
    "scripts/verify.sh",
    "src/delta_lemmata/stylo_contracts.py",
    "tests/fixtures/stylo/p006-whole-text-v2/LICENSE",
    "tests/fixtures/stylo/p006-whole-text-v2/fixture-manifest.json",
)
EXPECTED_RUN_ENVIRONMENT = {
    "architecture": "x86_64",
    "built_image_id": "sha256:73bbf04a2eacd059f1b1b9f319f3645c0a1d552aafb4ac0cbe4a0129d182eabc",
    "capture_container_job": "86980971385",
    "capture_job": "86980971428",
    "capture_verify_job": "86980971766",
    "capture_workflow_run": "29299793944",
    "evidence_commit": EVIDENCE_COMMIT,
    "evidence_publication_ci_container_job": "86981809317",
    "evidence_publication_ci_run": "29300077689",
    "evidence_publication_ci_verify_job": "86981809318",
    "jsonlite": "2.0.0",
    "locale": "C.UTF-8",
    "normal_source_ci_container_job": "86980527228",
    "normal_source_ci_run": "29299641848",
    "normal_source_ci_verify_job": "86980527225",
    "oracle_network": "none",
    "oracle_run_count": 2,
    "os": "GitHub-hosted Ubuntu 24.04",
    "python": "3.13.9",
    "r": "4.5.2",
    "stylo": "0.7.71",
    "timezone": "UTC",
    "transport_chunk_count": 137,
    "transport_envelope_bytes": 78355,
    "transport_envelope_sha256": TRANSPORT_SHA256,
    "transport_schema": "p006-log-transport-v1",
    "uv": "0.11.28",
}


def _manifest_entries() -> list[dict[str, str]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries: list[dict[str, str]] = []
    for raw_entry in manifest["fixtures"]:
        input_file = raw_entry["input_file"]
        input_path = FIXTURE_DIR / input_file
        digest = shared._sha256(input_path)
        if digest != raw_entry["input_sha256"]:
            shared._fail("P006_FROZEN_ORACLE_V2_FIXTURE_INVALID")
        entries.append(
            {
                "fixture_ref": raw_entry["fixture_ref"],
                "input_file": input_file,
                "input_sha256": digest,
            }
        )
    return entries


def _source_binding(metadata: dict[str, Any]) -> dict[str, bytes]:
    source_hashes = metadata.get("source_hashes")
    if metadata.get("source_commit") != SOURCE_COMMIT or not isinstance(source_hashes, dict):
        shared._fail("P006_FROZEN_ORACLE_V2_SOURCE_INVALID")
    if set(source_hashes) != set(SOURCE_PATHS):
        shared._fail("P006_FROZEN_ORACLE_V2_SOURCE_INVALID")
    sources: dict[str, bytes] = {}
    for path in SOURCE_PATHS:
        expected = source_hashes[path]
        if not isinstance(expected, str) or not shared.HEX_64.fullmatch(expected):
            shared._fail("P006_FROZEN_ORACLE_V2_SOURCE_INVALID")
        payload = shared._git_source(SOURCE_COMMIT, path)
        if shared._sha256_bytes(payload) != expected:
            shared._fail("P006_FROZEN_ORACLE_V2_SOURCE_INVALID")
        sources[path] = payload
    return sources


def _snapshot(evidence: Path, entries: list[dict[str, str]]) -> list[dict[str, str | int]]:
    paths = [
        evidence / "direct-reference" / shared._direct_name(entry["input_file"])
        for entry in entries
    ]
    paths.append(evidence / "session-info.json")
    return [
        {
            "byte_count": path.stat().st_size,
            "path": path.name,
            "sha256": shared._sha256(path),
        }
        for path in sorted(paths)
    ]


def _outputs(evidence: Path, entries: list[dict[str, str]]) -> list[dict[str, str | int]]:
    paths = [
        evidence / "direct-reference" / shared._direct_name(entry["input_file"])
        for entry in entries
    ]
    return [
        {
            "byte_count": path.stat().st_size,
            "path": path.relative_to(evidence).as_posix(),
            "sha256": shared._sha256(path),
        }
        for path in sorted(paths)
    ]


def _validate_metadata(
    metadata: dict[str, Any], evidence: Path, entries: list[dict[str, str]]
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
        shared._fail("P006_FROZEN_ORACLE_V2_METADATA_INVALID")
    if (
        metadata["schema_version"] != "p006-oracle-freeze-v2"
        or metadata["claim_boundary"] != "fixture-local whole-text parity only"
        or metadata["fixture_inputs"] != entries
        or metadata["outputs"] != _outputs(evidence, entries)
    ):
        shared._fail("P006_FROZEN_ORACLE_V2_METADATA_INVALID")
    sources = _source_binding(metadata)
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
        shared._fail("P006_FROZEN_ORACLE_V2_ENVIRONMENT_INVALID")
    snapshot = _snapshot(evidence, entries)
    if (
        environment["base_image"] != shared._base_image(sources["containers/Dockerfile"])
        or not isinstance(environment["base_image"], str)
        or not shared.PINNED_IMAGE.fullmatch(environment["base_image"])
        or environment["built_image_id"] != EXPECTED_RUN_ENVIRONMENT["built_image_id"]
        or environment["network"] != "none"
        or environment["platform"] != "linux/amd64"
        or environment["read_only_root"] is not True
        or environment["run_count"] != 2
        or environment["run_snapshots"] != [snapshot, snapshot]
        or environment["runs_byte_identical"] is not True
    ):
        shared._fail("P006_FROZEN_ORACLE_V2_ENVIRONMENT_INVALID")


def _artifact_map(run: dict[str, Any], key: str) -> dict[str, str]:
    try:
        records = run[key]
        mapped = {record["path"]: record["sha256"] for record in records}
    except (KeyError, TypeError):
        shared._fail("P006_FROZEN_ORACLE_V2_RUN_INVALID")
    if not isinstance(records, list) or len(mapped) != len(records):
        shared._fail("P006_FROZEN_ORACLE_V2_RUN_INVALID")
    return mapped


def _expected_run_inputs(metadata: dict[str, Any]) -> dict[str, str]:
    inputs = dict(metadata["source_hashes"])
    for entry in metadata["fixture_inputs"]:
        inputs[f"tests/fixtures/stylo/p006-whole-text-v2/{entry['input_file']}"] = entry[
            "input_sha256"
        ]
    return inputs


def _expected_run_outputs(evidence: Path, expected_files: set[str]) -> dict[str, str]:
    return {
        f"{EVIDENCE_PREFIX}/{relative}": shared._sha256(evidence / relative)
        for relative in expected_files
    }


def _validate_run_record(
    evidence: Path, metadata: dict[str, Any], expected_files: set[str]
) -> None:
    try:
        run = json.loads(RUN_RECORD.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        shared._fail("P006_FROZEN_ORACLE_V2_RUN_INVALID")
    if (
        run.get("schema_version") != "1.1.0"
        or run.get("run_id") != "RUN-20260714-0002"
        or run.get("run_type") != "test"
        or run.get("status") != "passed"
        or run.get("ticket_ids") != ["P006"]
        or run.get("git_commit") != SOURCE_COMMIT
        or run.get("exit_code") != 0
        or run.get("environment") != EXPECTED_RUN_ENVIRONMENT
        or _artifact_map(run, "configuration_artifacts") != metadata["source_hashes"]
        or _artifact_map(run, "input_artifacts") != _expected_run_inputs(metadata)
        or _artifact_map(run, "output_artifacts") != _expected_run_outputs(evidence, expected_files)
    ):
        shared._fail("P006_FROZEN_ORACLE_V2_RUN_INVALID")


def _validate_evidence_commit(
    evidence: Path, metadata: dict[str, Any], expected_files: set[str]
) -> None:
    parent = shared._git_bytes("show", "-s", "--format=%P", EVIDENCE_COMMIT).decode().strip()
    if parent != SOURCE_COMMIT or metadata.get("source_commit") != SOURCE_COMMIT:
        shared._fail("P006_FROZEN_ORACLE_V2_EVIDENCE_COMMIT_INVALID")
    expected_changes = {f"A\t{EVIDENCE_PREFIX}/{relative_path}" for relative_path in expected_files}
    actual_changes = set(
        shared._git_bytes("diff-tree", "--no-commit-id", "--name-status", "-r", EVIDENCE_COMMIT)
        .decode()
        .splitlines()
    )
    if actual_changes != expected_changes:
        shared._fail("P006_FROZEN_ORACLE_V2_EVIDENCE_COMMIT_INVALID")
    for relative_path in expected_files:
        committed = shared._git_source(EVIDENCE_COMMIT, f"{EVIDENCE_PREFIX}/{relative_path}")
        if (evidence / relative_path).read_bytes() != committed:
            shared._fail("P006_FROZEN_ORACLE_V2_EVIDENCE_COMMIT_INVALID")
    _validate_run_record(evidence, metadata, expected_files)


def validate_frozen_oracle_v2(evidence: Path = DEFAULT_EVIDENCE) -> None:
    """Reject an altered, incomplete, unbound, or scientifically invalid v2 freeze."""

    entries = _manifest_entries()
    expected_files = shared._expected_files(entries)
    shared._validate_file_set(evidence, expected_files)
    checksum_path = evidence / "oracle-freeze.sha256"
    if checksum_path.read_bytes() != shared._checksum_manifest(evidence):
        shared._fail("P006_FROZEN_ORACLE_V2_CHECKSUM_INVALID")
    _metadata_bytes, metadata = shared._read_json(
        evidence / "oracle-freeze.json", maximum_bytes=65536
    )
    _validate_metadata(metadata, evidence, entries)
    _validate_evidence_commit(evidence, metadata, expected_files)
    validate_output_directory_v2(
        evidence / "direct-reference", session_path=evidence / "session-info.json"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    validate_frozen_oracle_v2(args.evidence)
    print("p006-frozen-oracle-v2-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
