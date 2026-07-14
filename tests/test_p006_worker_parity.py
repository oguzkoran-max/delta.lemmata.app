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
        {"schema_version": "parity-test"},
        {"schema_version": "leakage-test"},
        {"schema_version": "security-test"},
    )

    expected_files = {
        "leakage-report.json",
        "parity-report.json",
        "security-report.json",
        "session-info.json",
        "worker-evidence.sha256",
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
            {},
            {},
            {},
        )


def test_valid_r_numeric_lexeme_does_not_need_python_byte_canonicalization() -> None:
    _request, _oracle, result = load_pair("normalization-base")
    python_payload = canonical_worker_json(result)
    r_style_payload = python_payload.replace(b'"values":[[0.0,', b'"values":[[0,', 1)
    assert r_style_payload != python_payload
    assert parity._validated_raw_payload(r_style_payload, result) == r_style_payload
