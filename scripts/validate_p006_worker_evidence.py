#!/usr/bin/env python3
"""Recompute every claim in a retained P006 fixed-worker evidence package."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

from validate_p006_fixture_v2 import (
    BASE_NAME,
    CANARY_NAME,
    FIXTURE_DIR,
    PERMUTATION_NAME,
)
from validate_p006_worker_parity import (
    BOUNDARY_DIRECT_REFERENCE_DIR,
    BOUNDARY_FIXTURE_DIR,
    BOUNDARY_INPUT_FILE,
    DIRECT_REFERENCE_DIR,
    FAILURE_INPUT_FILE,
    FAILURE_SOURCE_INPUT_FILE,
    MATRIX_TOLERANCE,
    REFERENCE_SESSION_PATH,
    TIE_TOLERANCE,
    CaptureContext,
    FixtureExecution,
    _boundary_manifest_entry,
    _boundary_report,
    _canonical_json,
    _direct_output_name,
    _failure_report,
    _failure_request,
    _injection_request,
    _manifest_entries,
    _sha256_bytes,
    _sha256_path,
    capture_metadata,
    compare_fixture,
    compare_order_permutation,
    compare_unknown_canary,
)

from delta_lemmata.stylo_contracts import (
    STRUCTURAL_TOLERANCE,
    DirectStyloOracleV1,
    WorkerInputV1,
    WorkerResultV1,
    canonical_worker_json,
    parse_direct_stylo_oracle,
    parse_worker_input,
    parse_worker_result,
    validate_direct_stylo_oracle,
    validate_worker_result,
)

CHECKSUM_NAME = "worker-evidence.sha256"
MAX_PACKAGE_BYTES = 2 * 1024 * 1024
PRIVATE_PATH_PATTERNS = (
    re.compile(rb"/Users/[A-Za-z0-9._-]+/"),
    re.compile(rb"/home/[A-Za-z0-9._-]+/"),
    re.compile(rb"/private/var/"),
    re.compile(rb"/(?:capture|repo|tmp)/"),
    re.compile(rb"/opt/delta/"),
    re.compile(rb"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"),
)


def _fail(code: str) -> NoReturn:
    raise ValueError(code) from None


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            _fail("P006_WORKER_EVIDENCE_JSON_INVALID")
        value[key] = item
    return value


def _reject_constant(_value: str) -> NoReturn:
    _fail("P006_WORKER_EVIDENCE_JSON_INVALID")


def _load_canonical_json(path: Path) -> Any:
    payload = path.read_bytes()
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("P006_WORKER_EVIDENCE_JSON_INVALID")
    if payload != _canonical_json(value):
        _fail("P006_WORKER_EVIDENCE_JSON_INVALID")
    return value


def _expected_paths() -> set[str]:
    input_files = [entry["input_file"] for entry in _manifest_entries()]
    input_files.append(BOUNDARY_INPUT_FILE)
    paths = {
        "boundary-report.json",
        "failure-report.json",
        "leakage-report.json",
        "parity-report.json",
        "security-report.json",
        "session-info.json",
        CHECKSUM_NAME,
        "worker-evidence.json",
        "worker-output/failure-boundary.worker.json",
        "worker-output/injection.worker.json",
    }
    for input_file in input_files:
        paths.add(f"direct-reference/{_direct_output_name(input_file)}")
        paths.add("worker-output/" + input_file.removesuffix(".input.json") + ".worker.json")
    return paths


def _package_files(directory: Path) -> dict[str, bytes]:
    if directory.is_symlink() or not directory.is_dir():
        _fail("P006_WORKER_EVIDENCE_DIRECTORY_INVALID")
    files: dict[str, bytes] = {}
    total = 0
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            _fail("P006_WORKER_EVIDENCE_FILE_INVALID")
        if path.is_dir():
            continue
        if not path.is_file():
            _fail("P006_WORKER_EVIDENCE_FILE_INVALID")
        relative = path.relative_to(directory).as_posix()
        payload = path.read_bytes()
        total += len(payload)
        if total > MAX_PACKAGE_BYTES or any(
            pattern.search(payload) for pattern in PRIVATE_PATH_PATTERNS
        ):
            _fail("P006_WORKER_EVIDENCE_PAYLOAD_INVALID")
        files[relative] = payload
    if set(files) != _expected_paths():
        _fail("P006_WORKER_EVIDENCE_FILE_SET_INVALID")
    expected_manifest = "".join(
        f"{_sha256_bytes(files[path])}  {path}\n" for path in sorted(files) if path != CHECKSUM_NAME
    ).encode("ascii")
    if files[CHECKSUM_NAME] != expected_manifest:
        _fail("P006_WORKER_EVIDENCE_CHECKSUM_INVALID")
    return files


def _worker_output_path(directory: Path, input_file: str) -> Path:
    return directory / "worker-output" / (input_file.removesuffix(".input.json") + ".worker.json")


def _load_direct_reference(
    package_path: Path,
    frozen_path: Path,
    request: WorkerInputV1,
) -> DirectStyloOracleV1:
    if package_path.read_bytes() != frozen_path.read_bytes():
        _fail("P006_WORKER_EVIDENCE_DIRECT_REFERENCE_MISMATCH")
    oracle = parse_direct_stylo_oracle(package_path.read_bytes())
    validate_direct_stylo_oracle(request, oracle)
    return oracle


def _load_worker_result(path: Path, request: WorkerInputV1) -> WorkerResultV1:
    result = parse_worker_result(path.read_bytes())
    validate_worker_result(request, result)
    return result


def _capture_context(
    metadata: Any,
    *,
    source_commit: str | None,
    image_id: str | None,
    github_run_id: str | None,
    github_run_attempt: int | None,
) -> CaptureContext:
    try:
        recorded = CaptureContext(
            source_commit=metadata["source_commit"],
            image_id=metadata["container_image_id"],
            github_run_id=metadata["github"]["run_id"],
            github_run_attempt=metadata["github"]["run_attempt"],
        )
    except (KeyError, TypeError):
        _fail("P006_WORKER_EVIDENCE_METADATA_INVALID")
    expected_values = (source_commit, image_id, github_run_id, github_run_attempt)
    if any(value is not None for value in expected_values) and any(
        value is None for value in expected_values
    ):
        _fail("P006_WORKER_EVIDENCE_EXPECTATION_INVALID")
    if source_commit is not None:
        expected = CaptureContext(
            source_commit=source_commit,
            image_id=image_id or "",
            github_run_id=github_run_id or "",
            github_run_attempt=github_run_attempt or 0,
        )
        if recorded != expected:
            _fail("P006_WORKER_EVIDENCE_CAPTURE_MISMATCH")
    try:
        expected_metadata = capture_metadata(recorded)
    except (TypeError, ValueError):
        _fail("P006_WORKER_EVIDENCE_METADATA_INVALID")
    if metadata != expected_metadata:
        _fail("P006_WORKER_EVIDENCE_METADATA_INVALID")
    return recorded


def validate_worker_evidence(
    directory: Path,
    *,
    source_commit: str | None = None,
    image_id: str | None = None,
    github_run_id: str | None = None,
    github_run_attempt: int | None = None,
) -> dict[str, Any]:
    """Validate one extracted package without executing R or trusting its reports."""

    files = _package_files(directory)
    metadata = _load_canonical_json(directory / "worker-evidence.json")
    context = _capture_context(
        metadata,
        source_commit=source_commit,
        image_id=image_id,
        github_run_id=github_run_id,
        github_run_attempt=github_run_attempt,
    )

    session_path = directory / "session-info.json"
    expected_session_payload = REFERENCE_SESSION_PATH.read_bytes()
    if (
        session_path.read_bytes() != expected_session_payload
        or expected_session_payload
        != (BOUNDARY_DIRECT_REFERENCE_DIR.parent / "session-info.json").read_bytes()
    ):
        _fail("P006_WORKER_EVIDENCE_SESSION_MISMATCH")
    session = _load_canonical_json(session_path)

    entries = _manifest_entries()
    requests: dict[str, WorkerInputV1] = {}
    oracles: dict[str, DirectStyloOracleV1] = {}
    results: dict[str, WorkerResultV1] = {}
    payloads: dict[str, bytes] = {}
    fixture_reports: list[dict[str, Any]] = []
    for entry in entries:
        input_file = entry["input_file"]
        request = parse_worker_input((FIXTURE_DIR / input_file).read_bytes())
        direct_name = _direct_output_name(input_file)
        oracle = _load_direct_reference(
            directory / "direct-reference" / direct_name,
            DIRECT_REFERENCE_DIR / direct_name,
            request,
        )
        worker_path = _worker_output_path(directory, input_file)
        result = _load_worker_result(worker_path, request)
        if result.session.model_dump(mode="json") != session:
            _fail("P006_WORKER_EVIDENCE_SESSION_MISMATCH")
        payload = worker_path.read_bytes()
        requests[input_file] = request
        oracles[input_file] = oracle
        results[input_file] = result
        payloads[input_file] = payload
        fixture_reports.append(
            {
                **entry,
                "oracle_sha256": _sha256_path(directory / "direct-reference" / direct_name),
                "worker_output_bytes": len(payload),
                "worker_output_sha256": _sha256_bytes(payload),
                **compare_fixture(request, result, oracle),
            }
        )

    parity_report = {
        "schema_version": "p006-worker-parity-report-v1",
        "claim_boundary": "named whole-text oracle-v2 fixtures only",
        "fixtures": fixture_reports,
        "matrix_tolerance": MATRIX_TOLERANCE,
        "order_permutation": compare_order_permutation(
            requests[BASE_NAME],
            requests[PERMUTATION_NAME],
            results[BASE_NAME],
            results[PERMUTATION_NAME],
        ),
        "reference_session_exact": True,
        "structural_tolerance": STRUCTURAL_TOLERANCE,
        "tie_tolerance": TIE_TOLERANCE,
    }
    if _load_canonical_json(directory / "parity-report.json") != parity_report:
        _fail("P006_WORKER_EVIDENCE_PARITY_REPORT_INVALID")

    leakage_report = {
        "schema_version": "p006-worker-leakage-report-v1",
        "claim_boundary": "worker-level changed-unknown canary only",
        "unknown_canary": compare_unknown_canary(
            requests[BASE_NAME],
            requests[CANARY_NAME],
            results[BASE_NAME],
            results[CANARY_NAME],
        ),
    }
    if _load_canonical_json(directory / "leakage-report.json") != leakage_report:
        _fail("P006_WORKER_EVIDENCE_LEAKAGE_REPORT_INVALID")

    boundary_entry = _boundary_manifest_entry()
    boundary_request = parse_worker_input((BOUNDARY_FIXTURE_DIR / BOUNDARY_INPUT_FILE).read_bytes())
    boundary_direct_name = _direct_output_name(BOUNDARY_INPUT_FILE)
    boundary_oracle = _load_direct_reference(
        directory / "direct-reference" / boundary_direct_name,
        BOUNDARY_DIRECT_REFERENCE_DIR / boundary_direct_name,
        boundary_request,
    )
    boundary_worker_path = _worker_output_path(directory, BOUNDARY_INPUT_FILE)
    boundary_result = _load_worker_result(boundary_worker_path, boundary_request)
    if boundary_result.session.model_dump(mode="json") != session:
        _fail("P006_WORKER_EVIDENCE_SESSION_MISMATCH")
    boundary_payload = boundary_worker_path.read_bytes()
    computed_boundary_report = _boundary_report(
        boundary_entry,
        FixtureExecution(
            input_file=BOUNDARY_INPUT_FILE,
            request=boundary_request,
            result=boundary_result,
            payload=boundary_payload,
            payload_sha256=_sha256_bytes(boundary_payload),
            payload_bytes=len(boundary_payload),
        ),
        boundary_oracle,
    )
    if _load_canonical_json(directory / "boundary-report.json") != computed_boundary_report:
        _fail("P006_WORKER_EVIDENCE_BOUNDARY_REPORT_INVALID")

    failure_source = parse_worker_input(
        (BOUNDARY_FIXTURE_DIR / FAILURE_SOURCE_INPUT_FILE).read_bytes()
    )
    failure_request = _failure_request(failure_source)
    failure_path = _worker_output_path(directory, FAILURE_INPUT_FILE)
    failure_result = _load_worker_result(failure_path, failure_request)
    if failure_result.session.model_dump(mode="json") != session:
        _fail("P006_WORKER_EVIDENCE_SESSION_MISMATCH")
    failure_payload = failure_path.read_bytes()
    computed_failure_report = _failure_report(
        failure_request,
        FixtureExecution(
            input_file=FAILURE_INPUT_FILE,
            request=failure_request,
            result=failure_result,
            payload=failure_payload,
            payload_sha256=_sha256_bytes(failure_payload),
            payload_bytes=len(failure_payload),
        ),
    )
    if _load_canonical_json(directory / "failure-report.json") != computed_failure_report:
        _fail("P006_WORKER_EVIDENCE_FAILURE_REPORT_INVALID")

    injection_request = _injection_request(requests[BASE_NAME])
    injection_path = directory / "worker-output" / "injection.worker.json"
    injection_result = _load_worker_result(injection_path, injection_request)
    if injection_result.session.model_dump(mode="json") != session:
        _fail("P006_WORKER_EVIDENCE_SESSION_MISMATCH")
    security_report = {
        "schema_version": "p006-worker-security-report-v1",
        "claim_boundary": "fixed adapter injection check only",
        "fixed_runtime_configuration": True,
        "injection_executed": False,
        "request_artifact_sha256": _sha256_bytes(canonical_worker_json(injection_request)),
        "result_artifact_sha256": _sha256_path(injection_path),
        "shell_or_code_channel_observed": False,
    }
    if _load_canonical_json(directory / "security-report.json") != security_report:
        _fail("P006_WORKER_EVIDENCE_SECURITY_REPORT_INVALID")

    return {
        "boundary_non_complete_cells": len(computed_boundary_report["expected_non_complete_cells"]),
        "container_image_id": context.image_id,
        "file_count": len(files),
        "fixture_count": len(entries) + 1,
        "literal_failed_cells": len(computed_failure_report["expected_failed_cells"]),
        "source_commit": context.source_commit,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--image-id")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt", type=int)
    args = parser.parse_args(argv)
    summary = validate_worker_evidence(
        args.directory,
        source_commit=args.source_commit,
        image_id=args.image_id,
        github_run_id=args.github_run_id,
        github_run_attempt=args.github_run_attempt,
    )
    print(
        "p006-worker-evidence-ok "
        f"files={summary['file_count']} fixtures={summary['fixture_count']} "
        f"non_complete_cells={summary['boundary_non_complete_cells']} "
        f"failed_cells={summary['literal_failed_cells']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
