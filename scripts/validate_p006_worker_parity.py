#!/usr/bin/env python3
"""Execute the fixed P006 worker and compare it with frozen oracle v2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from validate_p006_fixture_v2 import (
    BASE_NAME,
    CANARY_NAME,
    FIXTURE_DIR,
    MANIFEST_PATH,
    PERMUTATION_NAME,
)
from validate_p006_oracle_outputs import validate_output_directory_v2

from delta_lemmata.job_workspace import WorkspaceArea, WorkspaceManager
from delta_lemmata.stylo_contracts import (
    STRUCTURAL_TOLERANCE,
    CellComplete,
    DirectStyloOracleV1,
    FitComplete,
    StyloContractError,
    WorkerInputV1,
    WorkerResultV1,
    canonical_worker_json,
    parse_worker_result,
    validate_worker_result,
)
from delta_lemmata.stylo_worker import (
    REQUEST_COMPONENT,
    RESULT_COMPONENT,
    StyloWorkerAdapter,
    WorkerArtifactKind,
)

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "provenance" / "evidence" / "P006" / "oracle-v2"
DIRECT_REFERENCE_DIR = REFERENCE_DIR / "direct-reference"
REFERENCE_SESSION_PATH = REFERENCE_DIR / "session-info.json"
MATRIX_TOLERANCE = 1e-6
TIE_TOLERANCE = 1e-12
INJECTION_SENTINEL_NAME = "p006_injection_executed"
INJECTION_FEATURE = f"system('touch {INJECTION_SENTINEL_NAME}')"
_OWNER_ID = hashlib.sha256(b"p006-worker-parity-owner-v1").hexdigest()


@dataclass(frozen=True, slots=True)
class FixtureExecution:
    input_file: str
    request: WorkerInputV1
    result: WorkerResultV1
    payload: bytes
    payload_sha256: str
    payload_bytes: int


def _fail(code: str) -> NoReturn:
    raise ValueError(code) from None


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_raw_payload(payload: bytes | None, result: WorkerResultV1) -> bytes:
    if payload is None:
        _fail("P006_WORKER_PARITY_OUTPUT_MISSING")
    try:
        parsed = parse_worker_result(payload)
    except StyloContractError:
        _fail("P006_WORKER_PARITY_OUTPUT_INVALID")
    if parsed != result:
        _fail("P006_WORKER_PARITY_OUTPUT_RESULT_MISMATCH")
    return payload


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _oracle_as_worker(oracle: DirectStyloOracleV1) -> WorkerResultV1:
    return WorkerResultV1(
        schema_version="stylo-worker-result-v1",
        request_id=oracle.request_id,
        limit_profile=oracle.limit_profile,
        analysis_unit=oracle.analysis_unit,
        seed=oracle.seed,
        worker_version="stylo-worker-v1",
        outcome=oracle.outcome,
        fitting_basis=oracle.fitting_basis,
        fits=oracle.fits,
        cells=oracle.cells,
        session=oracle.session,
    )


def _matrix_value(cell: CellComplete, left: str, right: str) -> float:
    indexes = {document_id: index for index, document_id in enumerate(cell.matrix.document_ids)}
    try:
        return cell.matrix.values[indexes[left]][indexes[right]]
    except KeyError:
        _fail("P006_WORKER_PARITY_MATRIX_LABEL_INVALID")


def _complete_cells(result: WorkerResultV1) -> dict[tuple[str, str], CellComplete]:
    cells: dict[tuple[str, str], CellComplete] = {}
    for cell in result.cells:
        if not isinstance(cell, CellComplete):
            _fail("P006_WORKER_PARITY_COMPLETE_CELL_REQUIRED")
        cells[(cell.fit_id, cell.distance.value)] = cell
    return cells


def _nearest_groups(cell: CellComplete) -> dict[str, tuple[str, ...]]:
    groups: dict[str, tuple[str, ...]] = {}
    for document_id in cell.matrix.document_ids:
        candidates = tuple(
            (other, _matrix_value(cell, document_id, other))
            for other in cell.matrix.document_ids
            if other != document_id
        )
        minimum = min(value for _other, value in candidates)
        groups[document_id] = tuple(
            sorted(other for other, value in candidates if abs(value - minimum) <= TIE_TOLERANCE)
        )
    return groups


def compare_fixture(
    request: WorkerInputV1,
    actual: WorkerResultV1,
    oracle: DirectStyloOracleV1,
) -> dict[str, Any]:
    """Compare one validated worker result with one independent oracle result."""

    expected = validate_worker_result(request, _oracle_as_worker(oracle))
    validate_worker_result(request, actual)
    if (
        actual.request_id != expected.request_id
        or actual.limit_profile != expected.limit_profile
        or actual.analysis_unit != expected.analysis_unit
        or actual.seed != expected.seed
        or actual.outcome != expected.outcome
        or actual.fitting_basis.ranked_features != expected.fitting_basis.ranked_features
        or actual.fitting_basis.known_document_ids != expected.fitting_basis.known_document_ids
        or len(actual.fits) != len(expected.fits)
        or len(actual.cells) != len(expected.cells)
    ):
        _fail("P006_WORKER_PARITY_STRUCTURE_MISMATCH")

    maximum_structural_gap = 0.0
    for actual_fit, expected_fit in zip(actual.fits, expected.fits, strict=True):
        if type(actual_fit) is not type(expected_fit):
            _fail("P006_WORKER_PARITY_FIT_STATUS_MISMATCH")
        if isinstance(actual_fit, FitComplete) and isinstance(expected_fit, FitComplete):
            if (
                actual_fit.fit_id != expected_fit.fit_id
                or actual_fit.mfw != expected_fit.mfw
                or actual_fit.culling_percent != expected_fit.culling_percent
                or actual_fit.eligible_feature_count != expected_fit.eligible_feature_count
                or actual_fit.selected_features != expected_fit.selected_features
            ):
                _fail("P006_WORKER_PARITY_FEATURE_MISMATCH")
            vector_gaps = tuple(
                abs(left - right)
                for actual_values, expected_values in (
                    (actual_fit.means, expected_fit.means),
                    (
                        actual_fit.standard_deviations,
                        expected_fit.standard_deviations,
                    ),
                )
                for left, right in zip(actual_values, expected_values, strict=True)
            )
            maximum_structural_gap = max(maximum_structural_gap, *vector_gaps)
            if any(gap > STRUCTURAL_TOLERANCE for gap in vector_gaps):
                _fail("P006_WORKER_PARITY_FIT_VALUE_MISMATCH")
        elif actual_fit != expected_fit:
            _fail("P006_WORKER_PARITY_FIT_MISMATCH")

    maximum_matrix_gap = 0.0
    exact_tie_groups = 0
    for actual_cell, expected_cell in zip(actual.cells, expected.cells, strict=True):
        if type(actual_cell) is not type(expected_cell):
            _fail("P006_WORKER_PARITY_CELL_STATUS_MISMATCH")
        if isinstance(actual_cell, CellComplete) and isinstance(expected_cell, CellComplete):
            if (
                actual_cell.cell_id != expected_cell.cell_id
                or actual_cell.fit_id != expected_cell.fit_id
                or actual_cell.distance != expected_cell.distance
                or set(actual_cell.matrix.document_ids) != set(expected_cell.matrix.document_ids)
            ):
                _fail("P006_WORKER_PARITY_CELL_MISMATCH")
            gaps = tuple(
                abs(
                    _matrix_value(actual_cell, left, right)
                    - _matrix_value(expected_cell, left, right)
                )
                for left in expected_cell.matrix.document_ids
                for right in expected_cell.matrix.document_ids
            )
            maximum_matrix_gap = max(maximum_matrix_gap, *gaps)
            if any(gap > MATRIX_TOLERANCE for gap in gaps):
                _fail("P006_WORKER_PARITY_MATRIX_MISMATCH")
            if _nearest_groups(actual_cell) != _nearest_groups(expected_cell):
                _fail("P006_WORKER_PARITY_TIE_GROUP_MISMATCH")
            exact_tie_groups += len(expected_cell.matrix.document_ids)
        elif actual_cell != expected_cell:
            _fail("P006_WORKER_PARITY_CELL_MISMATCH")

    return {
        "cell_count": len(actual.cells),
        "exact_ordered_feature_inventory": True,
        "fit_count": len(actual.fits),
        "maximum_matrix_absolute_difference": maximum_matrix_gap,
        "maximum_structural_absolute_difference": maximum_structural_gap,
        "nearest_neighbor_groups_compared": exact_tie_groups,
        "nearest_neighbor_tie_groups_exact": True,
        "outcome": actual.outcome.value,
    }


def compare_unknown_canary(
    base_request: WorkerInputV1,
    canary_request: WorkerInputV1,
    base: WorkerResultV1,
    canary: WorkerResultV1,
) -> dict[str, Any]:
    """Prove that changed unknown rows cannot alter worker fitting artifacts."""

    if (
        base.fitting_basis != canary.fitting_basis
        or base.fits != canary.fits
        or base_request.fits != canary_request.fits
        or base_request.cells != canary_request.cells
    ):
        _fail("P006_WORKER_PARITY_UNKNOWN_FITTING_LEAKAGE")
    known_ids = tuple(
        document.document_id
        for document in base_request.documents
        if document.role.value == "known"
    )
    unknown_ids = tuple(
        document.document_id
        for document in base_request.documents
        if document.role.value == "unknown"
    )
    base_cells = _complete_cells(base)
    canary_cells = _complete_cells(canary)
    if base_cells.keys() != canary_cells.keys():
        _fail("P006_WORKER_PARITY_UNKNOWN_CELL_MISMATCH")

    active_pairs: set[tuple[str, str]] = set()
    known_values_compared = 0
    for key, base_cell in base_cells.items():
        canary_cell = canary_cells[key]
        for left in known_ids:
            for right in known_ids:
                known_values_compared += 1
                if _matrix_value(base_cell, left, right) != _matrix_value(canary_cell, left, right):
                    _fail("P006_WORKER_PARITY_UNKNOWN_DISTANCE_LEAKAGE")
        for unknown_id in unknown_ids:
            if any(
                abs(
                    _matrix_value(base_cell, unknown_id, known_id)
                    - _matrix_value(canary_cell, unknown_id, known_id)
                )
                > STRUCTURAL_TOLERANCE
                for known_id in known_ids
            ):
                active_pairs.add((unknown_id, key[1]))
    expected_active_pairs = {
        (unknown_id, distance)
        for unknown_id in unknown_ids
        for distance in ("classic_delta", "eders_delta", "cosine_delta")
    }
    if active_pairs != expected_active_pairs:
        _fail("P006_WORKER_PARITY_UNKNOWN_CANARY_INACTIVE")
    return {
        "changed_unknown_documents": len(unknown_ids),
        "fitting_artifacts_exact": True,
        "known_distance_values_compared": known_values_compared,
        "known_known_distances_exact": True,
        "unknown_distance_families_active": len(active_pairs),
    }


def compare_order_permutation(
    base_request: WorkerInputV1,
    permutation_request: WorkerInputV1,
    base: WorkerResultV1,
    permutation: WorkerResultV1,
) -> dict[str, Any]:
    """Compare a reordered request by opaque document identity, never row position."""

    if (
        {document.document_id: document for document in base_request.documents}
        != {document.document_id: document for document in permutation_request.documents}
        or base.fitting_basis.ranked_features != permutation.fitting_basis.ranked_features
        or base.fits != permutation.fits
    ):
        _fail("P006_WORKER_PARITY_ORDER_STRUCTURE_MISMATCH")
    base_cells = _complete_cells(base)
    permutation_cells = _complete_cells(permutation)
    if base_cells.keys() != permutation_cells.keys():
        _fail("P006_WORKER_PARITY_ORDER_CELL_MISMATCH")
    document_ids = tuple(document.document_id for document in base_request.documents)
    maximum_gap = 0.0
    values_compared = 0
    for key, base_cell in base_cells.items():
        permutation_cell = permutation_cells[key]
        for left in document_ids:
            for right in document_ids:
                values_compared += 1
                gap = abs(
                    _matrix_value(base_cell, left, right)
                    - _matrix_value(permutation_cell, left, right)
                )
                maximum_gap = max(maximum_gap, gap)
                if gap > STRUCTURAL_TOLERANCE:
                    _fail("P006_WORKER_PARITY_ORDER_VALUE_MISMATCH")
    return {
        "fitting_artifacts_exact": True,
        "maximum_absolute_difference": maximum_gap,
        "matrix_values_compared": values_compared,
        "opaque_id_equivariance": True,
    }


def _execute_request(
    manager: WorkspaceManager,
    request: WorkerInputV1,
    input_file: str,
) -> FixtureExecution:
    job_id = hashlib.sha256(f"p006-worker:{input_file}".encode("ascii")).hexdigest()
    layout = manager.create(_OWNER_ID, job_id)
    execution = StyloWorkerAdapter(manager, layout).execute(request)
    result = execution.finalization.result
    if not execution.accepted_result or result is None:
        _fail("P006_WORKER_PARITY_EXECUTION_REJECTED")
    payload = manager.read_file(
        layout,
        WorkspaceArea.WORK,
        RESULT_COMPONENT,
        maximum_bytes=32 * 1024 * 1024,
    )
    payload = _validated_raw_payload(payload, result)
    if {path.name for path in layout.work.iterdir()} != {
        REQUEST_COMPONENT,
        RESULT_COMPONENT,
    }:
        _fail("P006_WORKER_PARITY_WORKSPACE_SET_INVALID")
    if len(execution.artifacts) != 1:
        _fail("P006_WORKER_PARITY_RECEIPT_INVALID")
    receipt = execution.artifacts[0]
    digest = _sha256_bytes(payload)
    if (
        receipt.kind is not WorkerArtifactKind.RESULT
        or receipt.component != RESULT_COMPONENT
        or receipt.byte_size != len(payload)
        or receipt.sha256 != digest
    ):
        _fail("P006_WORKER_PARITY_RECEIPT_INVALID")
    return FixtureExecution(
        input_file=input_file,
        request=request,
        result=result,
        payload=payload,
        payload_sha256=digest,
        payload_bytes=len(payload),
    )


def _injection_request(base: WorkerInputV1) -> WorkerInputV1:
    payload = base.model_dump(mode="python")
    features = list(payload["candidate_features"])
    features[-1] = INJECTION_FEATURE
    payload["candidate_features"] = features
    payload["request_id"] = "request_" + hashlib.sha256(b"p006-worker-injection-v1").hexdigest()
    return WorkerInputV1.model_validate(payload)


def _run_injection_check(
    manager: WorkspaceManager,
    root: Path,
    base: WorkerInputV1,
) -> dict[str, Any]:
    execution = _execute_request(manager, _injection_request(base), "injection.input.json")
    if any(path.name == INJECTION_SENTINEL_NAME for path in root.rglob("*")):
        _fail("P006_WORKER_PARITY_INJECTION_EXECUTED")
    return {
        "fixed_runtime_configuration": True,
        "injection_executed": False,
        "request_artifact_sha256": _sha256_bytes(canonical_worker_json(execution.request)),
        "result_artifact_sha256": execution.payload_sha256,
        "shell_or_code_channel_observed": False,
    }


def _manifest_entries() -> list[dict[str, str]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries: list[dict[str, str]] = []
    for entry in manifest["fixtures"]:
        input_file = entry["input_file"]
        input_path = FIXTURE_DIR / input_file
        if _sha256_path(input_path) != entry["input_sha256"]:
            _fail("P006_WORKER_PARITY_INPUT_HASH_INVALID")
        entries.append(
            {
                "fixture_ref": entry["fixture_ref"],
                "input_file": input_file,
                "input_sha256": entry["input_sha256"],
            }
        )
    return entries


def _direct_output_name(input_file: str) -> str:
    return input_file.removesuffix(".input.json") + ".direct.json"


def _write_evidence(
    output_directory: Path,
    executions: dict[str, FixtureExecution],
    parity_report: dict[str, Any],
    leakage_report: dict[str, Any],
    security_report: dict[str, Any],
) -> None:
    if output_directory.exists():
        _fail("P006_WORKER_PARITY_OUTPUT_EXISTS")
    worker_directory = output_directory / "worker-output"
    worker_directory.mkdir(parents=True, mode=0o700)
    output_directory.chmod(0o700)
    for input_file, execution in executions.items():
        output_name = input_file.removesuffix(".input.json") + ".worker.json"
        (worker_directory / output_name).write_bytes(execution.payload)
    (output_directory / "parity-report.json").write_bytes(_canonical_json(parity_report))
    (output_directory / "leakage-report.json").write_bytes(_canonical_json(leakage_report))
    (output_directory / "security-report.json").write_bytes(_canonical_json(security_report))
    first_result = executions[next(iter(executions))].result
    (output_directory / "session-info.json").write_bytes(
        _canonical_json(first_result.session.model_dump(mode="json"))
    )
    evidence_paths = sorted(path for path in output_directory.rglob("*") if path.is_file())
    checksum = "".join(
        f"{_sha256_path(path)}  {path.relative_to(output_directory).as_posix()}\n"
        for path in evidence_paths
    )
    (output_directory / "worker-evidence.sha256").write_text(checksum, encoding="ascii", newline="")


def run_parity(
    *,
    output_directory: Path | None = None,
    require_reference_session: bool = False,
) -> dict[str, Any]:
    """Run the fixed worker suite and optionally retain a canonical evidence package."""

    if sys.platform != "linux" or os.name != "posix":
        _fail("P006_WORKER_PARITY_LINUX_REQUIRED")
    if STRUCTURAL_TOLERANCE != 1e-12 or TIE_TOLERANCE != 1e-12:
        _fail("P006_WORKER_PARITY_PROTOCOL_INVALID")
    requests, oracles = validate_output_directory_v2(
        DIRECT_REFERENCE_DIR,
        session_path=REFERENCE_SESSION_PATH,
    )
    entries = _manifest_entries()
    with tempfile.TemporaryDirectory(prefix="p006-worker-parity-") as temporary:
        workspace_root = Path(temporary) / "jobs"
        workspace_root.mkdir(mode=0o700)
        if stat.S_IMODE(workspace_root.stat().st_mode) != 0o700:
            _fail("P006_WORKER_PARITY_WORKSPACE_INVALID")
        manager = WorkspaceManager(workspace_root)
        executions = {
            entry["input_file"]: _execute_request(
                manager,
                requests[entry["input_file"]],
                entry["input_file"],
            )
            for entry in entries
        }
        first_session = executions[entries[0]["input_file"]].result.session
        if any(execution.result.session != first_session for execution in executions.values()):
            _fail("P006_WORKER_PARITY_SESSION_DRIFT")
        reference_session_match = all(
            execution.result.session == oracles[input_file].session
            for input_file, execution in executions.items()
        )
        if require_reference_session and not reference_session_match:
            _fail("P006_WORKER_PARITY_REFERENCE_SESSION_MISMATCH")

        fixture_reports: list[dict[str, Any]] = []
        for entry in entries:
            input_file = entry["input_file"]
            execution = executions[input_file]
            comparison = compare_fixture(
                execution.request,
                execution.result,
                oracles[input_file],
            )
            fixture_reports.append(
                {
                    **entry,
                    "oracle_sha256": _sha256_path(
                        DIRECT_REFERENCE_DIR / _direct_output_name(input_file)
                    ),
                    "worker_output_bytes": execution.payload_bytes,
                    "worker_output_sha256": execution.payload_sha256,
                    **comparison,
                }
            )

        unknown_canary = compare_unknown_canary(
            requests[BASE_NAME],
            requests[CANARY_NAME],
            executions[BASE_NAME].result,
            executions[CANARY_NAME].result,
        )
        order_permutation = compare_order_permutation(
            requests[BASE_NAME],
            requests[PERMUTATION_NAME],
            executions[BASE_NAME].result,
            executions[PERMUTATION_NAME].result,
        )
        security_report = {
            "schema_version": "p006-worker-security-report-v1",
            "claim_boundary": "fixed adapter injection check only",
            **_run_injection_check(manager, workspace_root, requests[BASE_NAME]),
        }
        parity_report = {
            "schema_version": "p006-worker-parity-report-v1",
            "claim_boundary": "named whole-text oracle-v2 fixtures only",
            "fixtures": fixture_reports,
            "matrix_tolerance": MATRIX_TOLERANCE,
            "order_permutation": order_permutation,
            "reference_session_exact": reference_session_match,
            "structural_tolerance": STRUCTURAL_TOLERANCE,
            "tie_tolerance": TIE_TOLERANCE,
        }
        leakage_report = {
            "schema_version": "p006-worker-leakage-report-v1",
            "claim_boundary": "worker-level changed-unknown canary only",
            "unknown_canary": unknown_canary,
        }
        if output_directory is not None:
            _write_evidence(
                output_directory,
                executions,
                parity_report,
                leakage_report,
                security_report,
            )
    return {
        "parity": parity_report,
        "leakage": leakage_report,
        "security": security_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--require-reference-session", action="store_true")
    args = parser.parse_args()
    run_parity(
        output_directory=args.output_directory,
        require_reference_session=args.require_reference_session,
    )
    print("p006-worker-parity-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
