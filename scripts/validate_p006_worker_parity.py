#!/usr/bin/env python3
"""Execute the fixed P006 worker and compare it with frozen oracle v2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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
from validate_p006_oracle_outputs import (
    validate_output_directory,
    validate_output_directory_v2,
)

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
BOUNDARY_FIXTURE_DIR = ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v1"
BOUNDARY_MANIFEST_PATH = BOUNDARY_FIXTURE_DIR / "fixture-manifest.json"
BOUNDARY_REFERENCE_DIR = ROOT / "provenance" / "evidence" / "P006" / "oracle-v1"
BOUNDARY_DIRECT_REFERENCE_DIR = BOUNDARY_REFERENCE_DIR / "direct-reference"
BOUNDARY_SESSION_PATH = BOUNDARY_REFERENCE_DIR / "session-info.json"
BOUNDARY_INPUT_FILE = "partial-boundaries.input.json"
FAILURE_SOURCE_INPUT_FILE = "complete-base.input.json"
FAILURE_INPUT_FILE = "failure-boundary.input.json"
CAPTURE_SCHEMA_VERSION = "p006-worker-evidence-v1"
CAPTURE_REPOSITORY = "oguzkoran-max/delta.lemmata.app"
CAPTURE_WORKFLOW = "CI"
CAPTURE_JOB = "p006-worker-capture"
HEX_40 = re.compile(r"^[0-9a-f]{40}$")
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
POSITIVE_INTEGER = re.compile(r"^[1-9][0-9]*$")
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


@dataclass(frozen=True, slots=True)
class CaptureContext:
    source_commit: str
    image_id: str
    github_run_id: str
    github_run_attempt: int


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


def _validated_capture_context(context: CaptureContext) -> CaptureContext:
    if (
        not isinstance(context.source_commit, str)
        or not HEX_40.fullmatch(context.source_commit)
        or not isinstance(context.image_id, str)
        or not IMAGE_ID.fullmatch(context.image_id)
        or not isinstance(context.github_run_id, str)
        or not POSITIVE_INTEGER.fullmatch(context.github_run_id)
        or type(context.github_run_attempt) is not int
        or context.github_run_attempt <= 0
    ):
        _fail("P006_WORKER_EVIDENCE_CAPTURE_CONTEXT_INVALID")
    return context


def capture_metadata(context: CaptureContext) -> dict[str, Any]:
    """Build the path-free metadata bound into one retained worker package."""

    context = _validated_capture_context(context)
    base_lock = json.loads(
        (ROOT / "containers" / "base-images.lock.json").read_text(encoding="utf-8")
    )
    return {
        "schema_version": CAPTURE_SCHEMA_VERSION,
        "base_image": {
            "linux_amd64_digest": base_lock["linux_amd64_digest"],
            "manifest_list_digest": base_lock["manifest_list_digest"],
            "repository": base_lock["repository"],
            "tag": base_lock["tag"],
        },
        "bindings": {
            "boundary_fixture_manifest_sha256": _sha256_path(BOUNDARY_MANIFEST_PATH),
            "boundary_reference_session_sha256": _sha256_path(BOUNDARY_SESSION_PATH),
            "container_dockerfile_sha256": _sha256_path(ROOT / "containers" / "Dockerfile"),
            "fixture_manifest_sha256": _sha256_path(MANIFEST_PATH),
            "reference_session_sha256": _sha256_path(REFERENCE_SESSION_PATH),
            "renv_lock_sha256": _sha256_path(ROOT / "renv.lock"),
            "uv_lock_sha256": _sha256_path(ROOT / "uv.lock"),
            "worker_script_sha256": _sha256_path(
                ROOT / "scripts" / "workers" / "p006-stylo-worker-v1.R"
            ),
        },
        "capture_profile": {
            "capabilities": "all-dropped",
            "container_platform": "linux/amd64",
            "cpu_limit": "2",
            "memory_limit": "1g",
            "network": "none",
            "no_new_privileges": True,
            "process_limit": 64,
            "root_filesystem": "read-only",
            "runtime_user": "delta",
        },
        "container_image_id": context.image_id,
        "fixture_suites": [
            {
                "purpose": "literal-failed-cell-retention",
                "suite_id": "p006-derived-zero-variance-v1",
            },
            {
                "purpose": "boundary-retention-only",
                "suite_id": "p006-whole-text-v1",
            },
            {
                "purpose": "worker-parity-acceptance",
                "suite_id": "p006-whole-text-v2",
            },
        ],
        "github": {
            "job": CAPTURE_JOB,
            "repository": CAPTURE_REPOSITORY,
            "run_attempt": context.github_run_attempt,
            "run_id": context.github_run_id,
            "workflow": CAPTURE_WORKFLOW,
        },
        "source_commit": context.source_commit,
    }


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


def _failure_request(base: WorkerInputV1) -> WorkerInputV1:
    payload = base.model_dump(mode="python")
    required_counts = {
        "cafe": 10,
        "canary_only": 0,
        "delta": 5,
        "epsilon": 5,
        "gamma": 5,
        "zeta": 20,
        "éclair": 10,
    }
    if set(payload["candidate_features"]) != set(required_counts):
        _fail("P006_WORKER_PARITY_FAILURE_PROBE_INVALID")
    constant_counts = [required_counts[feature] for feature in payload["candidate_features"]]
    for document in payload["documents"]:
        if document["role"] == "known":
            document["counts"] = list(constant_counts)
    payload["request_id"] = (
        "request_" + hashlib.sha256(b"p006-worker-failure-boundary-v1").hexdigest()
    )
    return WorkerInputV1.model_validate(payload)


def _run_injection_check(
    manager: WorkspaceManager,
    root: Path,
    base: WorkerInputV1,
) -> tuple[dict[str, Any], FixtureExecution]:
    execution = _execute_request(manager, _injection_request(base), "injection.input.json")
    if any(path.name == INJECTION_SENTINEL_NAME for path in root.rglob("*")):
        _fail("P006_WORKER_PARITY_INJECTION_EXECUTED")
    return (
        {
            "fixed_runtime_configuration": True,
            "injection_executed": False,
            "request_artifact_sha256": _sha256_bytes(canonical_worker_json(execution.request)),
            "result_artifact_sha256": execution.payload_sha256,
            "shell_or_code_channel_observed": False,
        },
        execution,
    )


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


def _boundary_manifest_entry() -> dict[str, str]:
    manifest = json.loads(BOUNDARY_MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = next(
        (
            candidate
            for candidate in manifest["fixtures"]
            if candidate["input_file"] == BOUNDARY_INPUT_FILE
        ),
        None,
    )
    if not isinstance(entry, dict):
        _fail("P006_WORKER_PARITY_BOUNDARY_MANIFEST_INVALID")
    input_path = BOUNDARY_FIXTURE_DIR / BOUNDARY_INPUT_FILE
    if _sha256_path(input_path) != entry["input_sha256"]:
        _fail("P006_WORKER_PARITY_INPUT_HASH_INVALID")
    return {
        "fixture_ref": entry["fixture_ref"],
        "input_file": entry["input_file"],
        "input_sha256": entry["input_sha256"],
    }


def _non_complete_records(
    values: tuple[Any, ...],
    *,
    identifier: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for value in values:
        payload = value.model_dump(mode="json")
        if payload["status"] == "complete":
            continue
        record = {
            identifier: payload[identifier],
            "status": payload["status"],
        }
        if "eligible_feature_count" in payload:
            record["eligible_feature_count"] = payload["eligible_feature_count"]
        if "error_code" in payload:
            record["error_code"] = payload["error_code"]
        records.append(record)
    return records


def _boundary_report(
    entry: dict[str, str],
    execution: FixtureExecution,
    oracle: DirectStyloOracleV1,
) -> dict[str, Any]:
    comparison = compare_fixture(execution.request, execution.result, oracle)
    expected = _oracle_as_worker(oracle)
    expected_fits = _non_complete_records(expected.fits, identifier="fit_id")
    expected_cells = _non_complete_records(expected.cells, identifier="cell_id")
    actual_fits = _non_complete_records(execution.result.fits, identifier="fit_id")
    actual_cells = _non_complete_records(execution.result.cells, identifier="cell_id")
    if actual_fits != expected_fits or actual_cells != expected_cells:
        _fail("P006_WORKER_PARITY_BOUNDARY_STATUS_MISMATCH")
    return {
        "schema_version": "p006-worker-boundary-report-v1",
        "claim_boundary": "oracle-v1 partial-boundaries retention only",
        **entry,
        "oracle_sha256": _sha256_path(
            BOUNDARY_DIRECT_REFERENCE_DIR / _direct_output_name(entry["input_file"])
        ),
        "worker_output_bytes": execution.payload_bytes,
        "worker_output_sha256": execution.payload_sha256,
        "expected_non_complete_cells": expected_cells,
        "expected_non_complete_fits": expected_fits,
        **comparison,
    }


def _expected_ranked_features(request: WorkerInputV1) -> list[dict[str, Any]]:
    known = [document for document in request.documents if document.role.value == "known"]
    records = []
    for index, feature in enumerate(request.candidate_features):
        total = sum(document.counts[index] for document in known)
        if total == 0:
            continue
        records.append(
            {
                "feature": feature,
                "known_document_count": sum(document.counts[index] > 0 for document in known),
                "known_total_count": total,
            }
        )
    return sorted(
        records,
        key=lambda record: (
            -record["known_total_count"],
            record["feature"].encode("utf-8"),
        ),
    )


def _failure_report(
    request: WorkerInputV1,
    execution: FixtureExecution,
) -> dict[str, Any]:
    known = [document for document in request.documents if document.role.value == "known"]
    expected_ranked = _expected_ranked_features(request)
    expected_basis = {
        "known_document_ids": [document.document_id for document in known],
        "ranked_features": expected_ranked,
    }
    if execution.result.fitting_basis.model_dump(mode="json") != expected_basis:
        _fail("P006_WORKER_PARITY_FAILURE_BASIS_MISMATCH")
    indexes = {feature: index for index, feature in enumerate(request.candidate_features)}
    for ranked in expected_ranked:
        index = indexes[ranked["feature"]]
        first = known[0]
        if any(
            first.counts[index] * document.token_total != document.counts[index] * first.token_total
            for document in known[1:]
        ):
            _fail("P006_WORKER_PARITY_FAILURE_PROBE_INVALID")
    eligible_count = len(expected_ranked)
    expected_fits = [
        {
            "eligible_feature_count": eligible_count,
            "error_code": "non_positive_standard_deviation",
            "fit_id": fit.fit_id,
            "status": "failed",
        }
        for fit in request.fits
    ]
    expected_cells = [
        {
            "cell_id": cell.cell_id,
            "error_code": "fit_unavailable",
            "status": "failed",
        }
        for cell in request.cells
    ]
    if (
        execution.result.outcome.value != "failed"
        or _non_complete_records(execution.result.fits, identifier="fit_id") != expected_fits
        or _non_complete_records(execution.result.cells, identifier="cell_id") != expected_cells
    ):
        _fail("P006_WORKER_PARITY_FAILURE_STATUS_MISMATCH")
    return {
        "schema_version": "p006-worker-failure-report-v1",
        "claim_boundary": "derived zero-variance failure retention only",
        "eligible_feature_count": eligible_count,
        "expected_failed_cells": expected_cells,
        "expected_failed_fits": expected_fits,
        "known_document_count": len(known),
        "outcome": execution.result.outcome.value,
        "request_artifact_sha256": _sha256_bytes(canonical_worker_json(request)),
        "worker_output_bytes": execution.payload_bytes,
        "worker_output_sha256": execution.payload_sha256,
    }


def _direct_output_name(input_file: str) -> str:
    return input_file.removesuffix(".input.json") + ".direct.json"


def _write_evidence(
    output_directory: Path,
    executions: dict[str, FixtureExecution],
    direct_references: dict[str, Path],
    injection_execution: FixtureExecution,
    failure_execution: FixtureExecution,
    parity_report: dict[str, Any],
    leakage_report: dict[str, Any],
    security_report: dict[str, Any],
    boundary_report: dict[str, Any],
    failure_report: dict[str, Any],
    context: CaptureContext,
) -> None:
    if output_directory.exists():
        _fail("P006_WORKER_PARITY_OUTPUT_EXISTS")
    worker_directory = output_directory / "worker-output"
    direct_directory = output_directory / "direct-reference"
    worker_directory.mkdir(parents=True, mode=0o700)
    direct_directory.mkdir(mode=0o700)
    output_directory.chmod(0o700)
    for input_file, execution in executions.items():
        output_name = input_file.removesuffix(".input.json") + ".worker.json"
        (worker_directory / output_name).write_bytes(execution.payload)
        direct_path = direct_references[input_file]
        (direct_directory / _direct_output_name(input_file)).write_bytes(direct_path.read_bytes())
    (worker_directory / "injection.worker.json").write_bytes(injection_execution.payload)
    (worker_directory / "failure-boundary.worker.json").write_bytes(failure_execution.payload)
    (output_directory / "boundary-report.json").write_bytes(_canonical_json(boundary_report))
    (output_directory / "failure-report.json").write_bytes(_canonical_json(failure_report))
    (output_directory / "parity-report.json").write_bytes(_canonical_json(parity_report))
    (output_directory / "leakage-report.json").write_bytes(_canonical_json(leakage_report))
    (output_directory / "security-report.json").write_bytes(_canonical_json(security_report))
    (output_directory / "worker-evidence.json").write_bytes(
        _canonical_json(capture_metadata(context))
    )
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
    include_boundary_fixture: bool = False,
    capture_context: CaptureContext | None = None,
) -> dict[str, Any]:
    """Run the fixed worker suite and optionally retain a canonical evidence package."""

    if sys.platform != "linux" or os.name != "posix":
        _fail("P006_WORKER_PARITY_LINUX_REQUIRED")
    if output_directory is not None and (not include_boundary_fixture or capture_context is None):
        _fail("P006_WORKER_EVIDENCE_CAPTURE_CONTEXT_REQUIRED")
    if output_directory is None and capture_context is not None:
        _fail("P006_WORKER_EVIDENCE_OUTPUT_REQUIRED")
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
        boundary_execution: FixtureExecution | None = None
        boundary_report: dict[str, Any] | None = None
        boundary_direct_path: Path | None = None
        failure_execution: FixtureExecution | None = None
        failure_report: dict[str, Any] | None = None
        if include_boundary_fixture:
            boundary_requests, boundary_oracles = validate_output_directory(
                BOUNDARY_DIRECT_REFERENCE_DIR,
                session_path=BOUNDARY_SESSION_PATH,
            )
            boundary_entry = _boundary_manifest_entry()
            boundary_execution = _execute_request(
                manager,
                boundary_requests[BOUNDARY_INPUT_FILE],
                BOUNDARY_INPUT_FILE,
            )
            if (
                boundary_execution.result.session != first_session
                or boundary_oracles[BOUNDARY_INPUT_FILE].session != first_session
            ):
                _fail("P006_WORKER_PARITY_BOUNDARY_SESSION_MISMATCH")
            boundary_report = _boundary_report(
                boundary_entry,
                boundary_execution,
                boundary_oracles[BOUNDARY_INPUT_FILE],
            )
            boundary_direct_path = BOUNDARY_DIRECT_REFERENCE_DIR / _direct_output_name(
                BOUNDARY_INPUT_FILE
            )
            failure_request = _failure_request(boundary_requests[FAILURE_SOURCE_INPUT_FILE])
            failure_execution = _execute_request(
                manager,
                failure_request,
                FAILURE_INPUT_FILE,
            )
            if failure_execution.result.session != first_session:
                _fail("P006_WORKER_PARITY_FAILURE_SESSION_MISMATCH")
            failure_report = _failure_report(
                failure_request,
                failure_execution,
            )

        injection_report, injection_execution = _run_injection_check(
            manager,
            workspace_root,
            requests[BASE_NAME],
        )
        if injection_execution.result.session != first_session:
            _fail("P006_WORKER_PARITY_INJECTION_SESSION_MISMATCH")
        security_report = {
            "schema_version": "p006-worker-security-report-v1",
            "claim_boundary": "fixed adapter injection check only",
            **injection_report,
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
            if (
                capture_context is None
                or boundary_execution is None
                or boundary_report is None
                or boundary_direct_path is None
                or failure_execution is None
                or failure_report is None
            ):
                _fail("P006_WORKER_EVIDENCE_CAPTURE_CONTEXT_REQUIRED")
            retained_executions = {
                **executions,
                BOUNDARY_INPUT_FILE: boundary_execution,
            }
            direct_references = {
                entry["input_file"]: (
                    DIRECT_REFERENCE_DIR / _direct_output_name(entry["input_file"])
                )
                for entry in entries
            }
            direct_references[BOUNDARY_INPUT_FILE] = boundary_direct_path
            _write_evidence(
                output_directory,
                retained_executions,
                direct_references,
                injection_execution,
                failure_execution,
                parity_report,
                leakage_report,
                security_report,
                boundary_report,
                failure_report,
                capture_context,
            )
    result = {
        "parity": parity_report,
        "leakage": leakage_report,
        "security": security_report,
    }
    if boundary_report is not None:
        result["boundary"] = boundary_report
    if failure_report is not None:
        result["failure"] = failure_report
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--require-reference-session", action="store_true")
    parser.add_argument("--include-boundary-fixture", action="store_true")
    parser.add_argument("--source-commit")
    parser.add_argument("--image-id")
    parser.add_argument("--github-run-id")
    parser.add_argument("--github-run-attempt", type=int)
    args = parser.parse_args()
    context_values = (
        args.source_commit,
        args.image_id,
        args.github_run_id,
        args.github_run_attempt,
    )
    if all(value is None for value in context_values):
        context = None
    elif any(value is None for value in context_values):
        _fail("P006_WORKER_EVIDENCE_CAPTURE_CONTEXT_INVALID")
    else:
        context = CaptureContext(
            source_commit=args.source_commit,
            image_id=args.image_id,
            github_run_id=args.github_run_id,
            github_run_attempt=args.github_run_attempt,
        )
    run_parity(
        output_directory=args.output_directory,
        require_reference_session=args.require_reference_session,
        include_boundary_fixture=args.include_boundary_fixture,
        capture_context=context,
    )
    print("p006-worker-parity-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
