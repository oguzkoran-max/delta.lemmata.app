from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

from delta_lemmata.stylo_contracts import (
    CellComplete,
    DirectStyloOracleV1,
    FitComplete,
    WorkerInputV1,
    WorkerResultV1,
    canonical_worker_json,
    parse_direct_stylo_oracle,
    parse_worker_input,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
parity = importlib.import_module("validate_p006_worker_parity")

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v2"
REFERENCE_DIR = ROOT / "provenance" / "evidence" / "P006" / "oracle-v2" / "direct-reference"
BOUNDARY_FIXTURE_DIR = ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v1"
BOUNDARY_REFERENCE_DIR = (
    ROOT / "provenance" / "evidence" / "P006" / "oracle-v1" / "direct-reference"
)


def load_pair(name: str) -> tuple[WorkerInputV1, DirectStyloOracleV1, WorkerResultV1]:
    request = parse_worker_input((FIXTURE_DIR / f"{name}.input.json").read_bytes())
    oracle = parse_direct_stylo_oracle((REFERENCE_DIR / f"{name}.direct.json").read_bytes())
    return request, oracle, parity._oracle_as_worker(oracle)


def mutate_matrix_edge(
    result: WorkerResultV1,
    *,
    cell_index: int,
    left: int,
    right: int,
    value: float,
) -> WorkerResultV1:
    payload = result.model_dump(mode="python")
    matrix = [list(row) for row in payload["cells"][cell_index]["matrix"]["values"]]
    matrix[left][right] = value
    matrix[right][left] = value
    payload["cells"][cell_index]["matrix"]["values"] = matrix
    return WorkerResultV1.model_validate(payload)


def mutate_oracle_matrix_edge(
    oracle: DirectStyloOracleV1,
    *,
    cell_index: int,
    left: int,
    right: int,
    value: float,
) -> DirectStyloOracleV1:
    payload = oracle.model_dump(mode="python")
    matrix = [list(row) for row in payload["cells"][cell_index]["matrix"]["values"]]
    matrix[left][right] = value
    matrix[right][left] = value
    payload["cells"][cell_index]["matrix"]["values"] = matrix
    return DirectStyloOracleV1.model_validate(payload)


def test_exact_oracle_equivalent_passes_all_comparison_protocols() -> None:
    base_request, base_oracle, base = load_pair("normalization-base")
    canary_request, _canary_oracle, canary = load_pair("normalization-canary")
    permutation_request, _permutation_oracle, permutation = load_pair("order-permutation")

    fixture = parity.compare_fixture(base_request, base, base_oracle)
    leakage = parity.compare_unknown_canary(
        base_request,
        canary_request,
        base,
        canary,
    )
    order = parity.compare_order_permutation(
        base_request,
        permutation_request,
        base,
        permutation,
    )

    assert fixture["maximum_matrix_absolute_difference"] == 0
    assert fixture["maximum_structural_absolute_difference"] == 0
    assert fixture["nearest_neighbor_tie_groups_exact"] is True
    assert leakage == {
        "changed_unknown_documents": 2,
        "fitting_artifacts_exact": True,
        "known_distance_values_compared": 192,
        "known_known_distances_exact": True,
        "unknown_distance_families_active": 6,
    }
    assert order == {
        "fitting_artifacts_exact": True,
        "maximum_absolute_difference": 0.0,
        "matrix_values_compared": 432,
        "opaque_id_equivariance": True,
    }


def test_matrix_tolerance_and_tie_groups_fail_independently() -> None:
    request, oracle, result = load_pair("normalization-base")
    complete_index = next(
        index for index, cell in enumerate(result.cells) if isinstance(cell, CellComplete)
    )
    cell = result.cells[complete_index]
    assert isinstance(cell, CellComplete)
    changed = mutate_matrix_edge(
        result,
        cell_index=complete_index,
        left=0,
        right=1,
        value=cell.matrix.values[0][1] + 2e-6,
    )
    with pytest.raises(ValueError, match="^P006_WORKER_PARITY_MATRIX_MISMATCH$"):
        parity.compare_fixture(request, changed, oracle)

    expected_result = parity._oracle_as_worker(oracle)
    target_fit = next(
        fit
        for fit in expected_result.fits
        if isinstance(fit, FitComplete) and fit.mfw == 3 and fit.culling_percent == 100
    )
    tie_cell_index = next(
        index
        for index, candidate in enumerate(expected_result.cells)
        if isinstance(candidate, CellComplete)
        and candidate.fit_id == target_fit.fit_id
        and candidate.distance.value == "classic_delta"
    )
    tie_cell = expected_result.cells[tie_cell_index]
    assert isinstance(tie_cell, CellComplete)
    nearest_value = tie_cell.matrix.values[0][2]
    tied_oracle = mutate_oracle_matrix_edge(
        oracle,
        cell_index=tie_cell_index,
        left=0,
        right=4,
        value=nearest_value,
    )
    tied_result = parity._oracle_as_worker(tied_oracle)
    broken_tie = mutate_matrix_edge(
        tied_result,
        cell_index=tie_cell_index,
        left=0,
        right=4,
        value=nearest_value + 1e-9,
    )
    with pytest.raises(ValueError, match="^P006_WORKER_PARITY_TIE_GROUP_MISMATCH$"):
        parity.compare_fixture(request, broken_tie, tied_oracle)


def test_unknown_known_distance_and_order_drift_are_rejected() -> None:
    base_request, _base_oracle, base = load_pair("normalization-base")
    canary_request, _canary_oracle, canary = load_pair("normalization-canary")
    permutation_request, _permutation_oracle, permutation = load_pair("order-permutation")
    cell = canary.cells[0]
    assert isinstance(cell, CellComplete)
    leaked = mutate_matrix_edge(
        canary,
        cell_index=0,
        left=0,
        right=2,
        value=cell.matrix.values[0][2] + 5e-13,
    )
    with pytest.raises(ValueError, match="^P006_WORKER_PARITY_UNKNOWN_DISTANCE_LEAKAGE$"):
        parity.compare_unknown_canary(base_request, canary_request, base, leaked)

    permutation_cell = permutation.cells[0]
    assert isinstance(permutation_cell, CellComplete)
    reordered = mutate_matrix_edge(
        permutation,
        cell_index=0,
        left=0,
        right=1,
        value=permutation_cell.matrix.values[0][1] + 2e-12,
    )
    with pytest.raises(ValueError, match="^P006_WORKER_PARITY_ORDER_VALUE_MISMATCH$"):
        parity.compare_order_permutation(
            base_request,
            permutation_request,
            base,
            reordered,
        )


def test_injection_request_is_data_and_evidence_package_is_canonical(tmp_path: Path) -> None:
    request, _oracle, result = load_pair("normalization-base")
    injected = parity._injection_request(request)
    assert parity.INJECTION_FEATURE in injected.candidate_features
    assert injected.request_id != request.request_id

    payload = canonical_worker_json(result)
    execution = parity.FixtureExecution(
        input_file="normalization-base.input.json",
        request=request,
        result=result,
        payload=payload,
        payload_sha256=parity._sha256_bytes(payload),
        payload_bytes=len(payload),
    )
    destination = tmp_path / "evidence"
    parity._write_evidence(
        destination,
        {execution.input_file: execution},
        {execution.input_file: REFERENCE_DIR / "normalization-base.direct.json"},
        execution,
        execution,
        {"schema_version": "parity-test"},
        {"schema_version": "leakage-test"},
        {"schema_version": "security-test"},
        {"schema_version": "boundary-test"},
        {"schema_version": "failure-test"},
        parity.CaptureContext(
            source_commit="a" * 40,
            image_id="sha256:" + "b" * 64,
            github_run_id="1",
            github_run_attempt=1,
        ),
    )

    expected_files = {
        "boundary-report.json",
        "direct-reference/normalization-base.direct.json",
        "failure-report.json",
        "leakage-report.json",
        "parity-report.json",
        "security-report.json",
        "session-info.json",
        "worker-evidence.sha256",
        "worker-evidence.json",
        "worker-output/failure-boundary.worker.json",
        "worker-output/injection.worker.json",
        "worker-output/normalization-base.worker.json",
    }
    actual_files = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    }
    assert actual_files == expected_files
    assert json.loads((destination / "parity-report.json").read_bytes()) == {
        "schema_version": "parity-test"
    }
    checksum = (destination / "worker-evidence.sha256").read_text(encoding="ascii")
    assert "worker-evidence.sha256" not in checksum
    assert str(tmp_path) not in checksum
    with pytest.raises(ValueError, match="^P006_WORKER_PARITY_OUTPUT_EXISTS$"):
        parity._write_evidence(
            destination,
            {execution.input_file: execution},
            {execution.input_file: REFERENCE_DIR / "normalization-base.direct.json"},
            execution,
            execution,
            {},
            {},
            {},
            {},
            {},
            parity.CaptureContext(
                source_commit="a" * 40,
                image_id="sha256:" + "b" * 64,
                github_run_id="1",
                github_run_attempt=1,
            ),
        )


def test_valid_r_numeric_lexeme_does_not_need_python_byte_canonicalization() -> None:
    _request, _oracle, result = load_pair("normalization-base")
    python_payload = canonical_worker_json(result)
    r_style_payload = python_payload.replace(b'"values":[[0.0,', b'"values":[[0,', 1)
    assert r_style_payload != python_payload
    assert parity._validated_raw_payload(r_style_payload, result) == r_style_payload


def test_boundary_report_retains_every_expected_non_complete_fit_and_cell() -> None:
    request = parse_worker_input(
        (BOUNDARY_FIXTURE_DIR / "partial-boundaries.input.json").read_bytes()
    )
    oracle = parse_direct_stylo_oracle(
        (BOUNDARY_REFERENCE_DIR / "partial-boundaries.direct.json").read_bytes()
    )
    result = parity._oracle_as_worker(oracle)
    payload = canonical_worker_json(result)
    execution = parity.FixtureExecution(
        input_file="partial-boundaries.input.json",
        request=request,
        result=result,
        payload=payload,
        payload_sha256=parity._sha256_bytes(payload),
        payload_bytes=len(payload),
    )

    report = parity._boundary_report(
        parity._boundary_manifest_entry(),
        execution,
        oracle,
    )

    assert report["claim_boundary"] == "oracle-v1 partial-boundaries retention only"
    assert report["outcome"] == "partial"
    assert len(report["expected_non_complete_fits"]) == 3
    assert len(report["expected_non_complete_cells"]) == 3
    assert {record["status"] for record in report["expected_non_complete_cells"]} == {
        "not_enough_features"
    }


def test_derived_failure_probe_predeclares_literal_failed_cells() -> None:
    source = parse_worker_input((BOUNDARY_FIXTURE_DIR / "complete-base.input.json").read_bytes())
    request = parity._failure_request(source)
    oracle = parse_direct_stylo_oracle(
        (BOUNDARY_REFERENCE_DIR / "complete-base.direct.json").read_bytes()
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
            "session": oracle.session,
            "worker_version": "stylo-worker-v1",
        }
    )
    payload = canonical_worker_json(result)
    report = parity._failure_report(
        request,
        parity.FixtureExecution(
            input_file=parity.FAILURE_INPUT_FILE,
            request=request,
            result=result,
            payload=payload,
            payload_sha256=parity._sha256_bytes(payload),
            payload_bytes=len(payload),
        ),
    )

    assert report["outcome"] == "failed"
    assert len(report["expected_failed_fits"]) == 4
    assert len(report["expected_failed_cells"]) == 12
    assert {record["status"] for record in report["expected_failed_cells"]} == {"failed"}


def test_capture_metadata_is_path_free_and_binds_critical_inputs() -> None:
    context = parity.CaptureContext(
        source_commit="a" * 40,
        image_id="sha256:" + "b" * 64,
        github_run_id="29310000000",
        github_run_attempt=1,
    )
    metadata = parity.capture_metadata(context)

    assert metadata["source_commit"] == context.source_commit
    assert metadata["container_image_id"] == context.image_id
    assert metadata["capture_profile"]["container_platform"] == "linux/amd64"
    assert metadata["capture_profile"]["container_memory_limit"] == "2g"
    assert metadata["capture_profile"]["network"] == "none"
    assert metadata["capture_profile"]["renv_runtime"] == "read-only-prebuilt-library"
    assert metadata["capture_profile"]["worker_limit_profile"] == {
        "cpu_time_seconds": 30,
        "max_processes": 8,
        "memory_bytes": 1073741824,
        "profile_version": "stylo-worker-limits-v1",
        "terminate_grace_seconds": 2,
        "wall_time_seconds": 60,
    }
    assert metadata["github"]["job"] == "p006-worker-capture"
    assert metadata["bindings"]["worker_script_sha256"] == parity._sha256_path(
        ROOT / "scripts" / "workers" / "p006-stylo-worker-v1.R"
    )
    serialized = parity._canonical_json(metadata)
    assert b"/Users/" not in serialized
    assert ("/" + "home/runner/").encode() not in serialized

    with pytest.raises(
        ValueError,
        match="^P006_WORKER_EVIDENCE_CAPTURE_CONTEXT_INVALID$",
    ):
        parity.capture_metadata(
            parity.CaptureContext(
                source_commit="invalid",
                image_id=context.image_id,
                github_run_id=context.github_run_id,
                github_run_attempt=context.github_run_attempt,
            )
        )
