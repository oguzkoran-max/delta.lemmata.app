from __future__ import annotations

import hashlib
import importlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from delta_lemmata.stylo_contracts import (
    WorkerResultV1,
    canonical_worker_json,
    parse_direct_stylo_oracle,
    parse_worker_input,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
parity = importlib.import_module("validate_p006_worker_parity")
evidence = importlib.import_module("validate_p006_worker_evidence")


def _execution(
    input_file: str,
    fixture_directory: Path,
    reference_directory: Path,
) -> Any:
    request = parse_worker_input((fixture_directory / input_file).read_bytes())
    direct_name = parity._direct_output_name(input_file)
    oracle = parse_direct_stylo_oracle((reference_directory / direct_name).read_bytes())
    result = parity._oracle_as_worker(oracle)
    payload = canonical_worker_json(result)
    return parity.FixtureExecution(
        input_file=input_file,
        request=request,
        result=result,
        payload=payload,
        payload_sha256=parity._sha256_bytes(payload),
        payload_bytes=len(payload),
    )


def _failure_execution() -> Any:
    source = parse_worker_input(
        (parity.BOUNDARY_FIXTURE_DIR / parity.FAILURE_SOURCE_INPUT_FILE).read_bytes()
    )
    request = parity._failure_request(source)
    session_oracle = parse_direct_stylo_oracle(
        (
            parity.BOUNDARY_DIRECT_REFERENCE_DIR
            / parity._direct_output_name(parity.FAILURE_SOURCE_INPUT_FILE)
        ).read_bytes()
    )
    ranked = parity._expected_ranked_features(request)
    result = WorkerResultV1.model_validate(
        {
            "analysis_unit": request.analysis_unit,
            "cells": [
                {
                    "cell_id": cell.cell_id,
                    "distance": cell.distance,
                    "error_code": "fit_unavailable",
                    "fit_id": cell.fit_id,
                    "status": "failed",
                }
                for cell in request.cells
            ],
            "fits": [
                {
                    "culling_percent": fit.culling_percent,
                    "eligible_feature_count": len(ranked),
                    "error_code": "non_positive_standard_deviation",
                    "fit_id": fit.fit_id,
                    "mfw": fit.mfw,
                    "status": "failed",
                }
                for fit in request.fits
            ],
            "fitting_basis": {
                "known_document_ids": [
                    document.document_id
                    for document in request.documents
                    if document.role.value == "known"
                ],
                "ranked_features": ranked,
            },
            "limit_profile": request.limit_profile,
            "outcome": "failed",
            "request_id": request.request_id,
            "schema_version": "stylo-worker-result-v1",
            "seed": request.seed,
            "session": session_oracle.session,
            "worker_version": "stylo-worker-v1",
        }
    )
    payload = canonical_worker_json(result)
    return parity.FixtureExecution(
        input_file=parity.FAILURE_INPUT_FILE,
        request=request,
        result=result,
        payload=payload,
        payload_sha256=parity._sha256_bytes(payload),
        payload_bytes=len(payload),
    )


def _rewrite_manifest(directory: Path) -> None:
    paths = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.name != evidence.CHECKSUM_NAME
    )
    (directory / evidence.CHECKSUM_NAME).write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
            f"{path.relative_to(directory).as_posix()}\n"
            for path in paths
        ),
        encoding="ascii",
        newline="",
    )


def _package(tmp_path: Path) -> tuple[Path, Any]:
    entries = parity._manifest_entries()
    executions = {
        entry["input_file"]: _execution(
            entry["input_file"],
            parity.FIXTURE_DIR,
            parity.DIRECT_REFERENCE_DIR,
        )
        for entry in entries
    }
    fixture_reports = []
    for entry in entries:
        execution = executions[entry["input_file"]]
        direct_path = parity.DIRECT_REFERENCE_DIR / parity._direct_output_name(entry["input_file"])
        oracle = parse_direct_stylo_oracle(direct_path.read_bytes())
        fixture_reports.append(
            {
                **entry,
                "oracle_sha256": parity._sha256_path(direct_path),
                "worker_output_bytes": execution.payload_bytes,
                "worker_output_sha256": execution.payload_sha256,
                **parity.compare_fixture(execution.request, execution.result, oracle),
            }
        )
    parity_report = {
        "schema_version": "p006-worker-parity-report-v1",
        "claim_boundary": "named whole-text oracle-v2 fixtures only",
        "fixtures": fixture_reports,
        "matrix_tolerance": parity.MATRIX_TOLERANCE,
        "order_permutation": parity.compare_order_permutation(
            executions[parity.BASE_NAME].request,
            executions[parity.PERMUTATION_NAME].request,
            executions[parity.BASE_NAME].result,
            executions[parity.PERMUTATION_NAME].result,
        ),
        "reference_session_exact": True,
        "structural_tolerance": parity.STRUCTURAL_TOLERANCE,
        "tie_tolerance": parity.TIE_TOLERANCE,
    }
    leakage_report = {
        "schema_version": "p006-worker-leakage-report-v1",
        "claim_boundary": "worker-level changed-unknown canary only",
        "unknown_canary": parity.compare_unknown_canary(
            executions[parity.BASE_NAME].request,
            executions[parity.CANARY_NAME].request,
            executions[parity.BASE_NAME].result,
            executions[parity.CANARY_NAME].result,
        ),
    }

    boundary_execution = _execution(
        parity.BOUNDARY_INPUT_FILE,
        parity.BOUNDARY_FIXTURE_DIR,
        parity.BOUNDARY_DIRECT_REFERENCE_DIR,
    )
    boundary_oracle = parse_direct_stylo_oracle(
        (
            parity.BOUNDARY_DIRECT_REFERENCE_DIR
            / parity._direct_output_name(parity.BOUNDARY_INPUT_FILE)
        ).read_bytes()
    )
    boundary_report = parity._boundary_report(
        parity._boundary_manifest_entry(),
        boundary_execution,
        boundary_oracle,
    )
    failure_execution = _failure_execution()
    failure_report = parity._failure_report(
        failure_execution.request,
        failure_execution,
    )

    injection_request = parity._injection_request(executions[parity.BASE_NAME].request)
    injection_payload = executions[parity.BASE_NAME].result.model_dump(mode="python")
    injection_payload["request_id"] = injection_request.request_id
    injection_result = WorkerResultV1.model_validate(injection_payload)
    injection_bytes = canonical_worker_json(injection_result)
    injection_execution = parity.FixtureExecution(
        input_file="injection.input.json",
        request=injection_request,
        result=injection_result,
        payload=injection_bytes,
        payload_sha256=parity._sha256_bytes(injection_bytes),
        payload_bytes=len(injection_bytes),
    )
    security_report = {
        "schema_version": "p006-worker-security-report-v1",
        "claim_boundary": "fixed adapter injection check only",
        "fixed_runtime_configuration": True,
        "injection_executed": False,
        "request_artifact_sha256": parity._sha256_bytes(canonical_worker_json(injection_request)),
        "result_artifact_sha256": injection_execution.payload_sha256,
        "shell_or_code_channel_observed": False,
    }
    context = parity.CaptureContext(
        source_commit="a" * 40,
        image_id="sha256:" + "b" * 64,
        github_run_id="29310000000",
        github_run_attempt=1,
    )
    directory = tmp_path / "worker-evidence"
    retained_executions = {
        **executions,
        parity.BOUNDARY_INPUT_FILE: boundary_execution,
    }
    direct_references = {
        entry["input_file"]: (
            parity.DIRECT_REFERENCE_DIR / parity._direct_output_name(entry["input_file"])
        )
        for entry in entries
    }
    direct_references[parity.BOUNDARY_INPUT_FILE] = (
        parity.BOUNDARY_DIRECT_REFERENCE_DIR
        / parity._direct_output_name(parity.BOUNDARY_INPUT_FILE)
    )
    parity._write_evidence(
        directory,
        retained_executions,
        direct_references,
        injection_execution,
        failure_execution,
        parity_report,
        leakage_report,
        security_report,
        boundary_report,
        failure_report,
        context,
    )
    return directory, context


def test_retained_worker_evidence_is_recomputed_from_exact_outputs(
    tmp_path: Path,
) -> None:
    directory, context = _package(tmp_path)

    summary = evidence.validate_worker_evidence(
        directory,
        source_commit=context.source_commit,
        image_id=context.image_id,
        github_run_id=context.github_run_id,
        github_run_attempt=context.github_run_attempt,
    )

    assert summary == {
        "boundary_non_complete_cells": 3,
        "container_image_id": context.image_id,
        "file_count": 18,
        "fixture_count": 4,
        "literal_failed_cells": 12,
        "source_commit": context.source_commit,
    }


def test_published_worker_evidence_is_replayed_from_frozen_source() -> None:
    summary = evidence.validate_frozen_worker_evidence()

    assert summary == {
        "boundary_non_complete_cells": 3,
        "container_image_id": evidence.CAPTURE_IMAGE_ID,
        "file_count": 18,
        "fixture_count": 4,
        "literal_failed_cells": 12,
        "source_commit": evidence.SOURCE_COMMIT,
    }


def test_frozen_worker_evidence_rejects_altered_bytes_and_wrong_commit(
    tmp_path: Path,
) -> None:
    altered = tmp_path / "worker-v1"
    shutil.copytree(evidence.DEFAULT_EVIDENCE, altered)
    report_path = altered / "parity-report.json"
    report_path.write_bytes(report_path.read_bytes() + b" ")
    with pytest.raises(
        ValueError,
        match="^P006_FROZEN_WORKER_EVIDENCE_COMMIT_INVALID$",
    ):
        evidence.validate_frozen_worker_evidence(altered)

    with pytest.raises(
        ValueError,
        match="^P006_FROZEN_WORKER_EVIDENCE_COMMIT_INVALID$",
    ):
        evidence.validate_frozen_worker_evidence(
            evidence_commit=evidence.SOURCE_COMMIT,
        )

    altered_run = tmp_path / "RUN-20260714-0004.json"
    run = json.loads(evidence.RUN_RECORD.read_bytes())
    run["notes"] = "broader claim"
    altered_run.write_text(json.dumps(run), encoding="utf-8")
    with pytest.raises(
        ValueError,
        match="^P006_FROZEN_WORKER_RUN_INVALID$",
    ):
        evidence.validate_frozen_worker_evidence(run_path=altered_run)


def test_worker_evidence_rejects_missing_boundary_and_wrong_capture(
    tmp_path: Path,
) -> None:
    directory, context = _package(tmp_path)
    (directory / "worker-output" / "partial-boundaries.worker.json").unlink()
    with pytest.raises(ValueError, match="^P006_WORKER_EVIDENCE_FILE_SET_INVALID$"):
        evidence.validate_worker_evidence(directory)

    second_directory, _ = _package(tmp_path / "second")
    with pytest.raises(ValueError, match="^P006_WORKER_EVIDENCE_CAPTURE_MISMATCH$"):
        evidence.validate_worker_evidence(
            second_directory,
            source_commit="c" * 40,
            image_id=context.image_id,
            github_run_id=context.github_run_id,
            github_run_attempt=context.github_run_attempt,
        )

    third_directory, _ = _package(tmp_path / "third")
    metadata_path = third_directory / "worker-evidence.json"
    metadata = json.loads(metadata_path.read_bytes())
    metadata["container_image_id"] = 7
    metadata_path.write_bytes(parity._canonical_json(metadata))
    _rewrite_manifest(third_directory)
    with pytest.raises(ValueError, match="^P006_WORKER_EVIDENCE_METADATA_INVALID$"):
        evidence.validate_worker_evidence(third_directory)


def test_worker_evidence_rejects_missing_or_modified_failure_probe(
    tmp_path: Path,
) -> None:
    directory, _context = _package(tmp_path)
    (directory / "worker-output" / "failure-boundary.worker.json").unlink()
    with pytest.raises(ValueError, match="^P006_WORKER_EVIDENCE_FILE_SET_INVALID$"):
        evidence.validate_worker_evidence(directory)

    second_directory, _ = _package(tmp_path / "second")
    report_path = second_directory / "failure-report.json"
    report = json.loads(report_path.read_bytes())
    report["outcome"] = "partial"
    report_path.write_bytes(parity._canonical_json(report))
    _rewrite_manifest(second_directory)
    with pytest.raises(
        ValueError,
        match="^P006_WORKER_EVIDENCE_FAILURE_REPORT_INVALID$",
    ):
        evidence.validate_worker_evidence(second_directory)


def test_worker_evidence_rejects_private_paths_and_reference_substitution(
    tmp_path: Path,
) -> None:
    directory, _context = _package(tmp_path)
    report_path = directory / "security-report.json"
    report = json.loads(report_path.read_bytes())
    report["private_path"] = "/" + "home/runner/work/private.txt"
    report_path.write_bytes(parity._canonical_json(report))
    _rewrite_manifest(directory)
    with pytest.raises(ValueError, match="^P006_WORKER_EVIDENCE_PAYLOAD_INVALID$"):
        evidence.validate_worker_evidence(directory)

    second_directory, _ = _package(tmp_path / "second")
    direct_path = second_directory / "direct-reference" / "normalization-base.direct.json"
    direct_path.write_bytes(
        direct_path.read_bytes().replace(b'"oracle_version"', b'"oracle_versioN"', 1)
    )
    _rewrite_manifest(second_directory)
    with pytest.raises(
        ValueError,
        match="^P006_WORKER_EVIDENCE_DIRECT_REFERENCE_MISMATCH$",
    ):
        evidence.validate_worker_evidence(second_directory)
