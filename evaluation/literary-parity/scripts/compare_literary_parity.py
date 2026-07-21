#!/usr/bin/env python3
"""Validate and compare literary Delta worker and direct R stylo evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any


MFW_GRID = (100, 300, 500, 1000)
MATRIX_TOLERANCE = 1e-6
STRUCTURAL_TOLERANCE = 1e-12
TIE_TOLERANCE = 1e-12


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
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


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)


def load_frozen_comparator(repo: Path):
    path = repo / "scripts" / "validate_p006_worker_parity.py"
    source_path = str(repo / "src")
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
    scripts_path = str(repo / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    spec = importlib.util.spec_from_file_location("frozen_p006_comparator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("literary-comparator-load-failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def matrix_values(cell: Any) -> tuple[tuple[str, ...], tuple[tuple[float, ...], ...]]:
    labels = tuple(cell.matrix.document_ids)
    values = tuple(tuple(float(value) for value in row) for row in cell.matrix.values)
    return labels, values


def nearest_groups(
    labels: tuple[str, ...], values: tuple[tuple[float, ...], ...]
) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for row_index, label in enumerate(labels):
        candidates = [
            (other, values[row_index][column_index])
            for column_index, other in enumerate(labels)
            if column_index != row_index
        ]
        minimum = min(value for _other, value in candidates)
        groups[label] = sorted(
            other for other, value in candidates if abs(value - minimum) <= TIE_TOLERANCE
        )
    return groups


def structural_metrics(values: tuple[tuple[float, ...], ...]) -> dict[str, Any]:
    size = len(values)
    finite = all(math.isfinite(value) for row in values for value in row)
    diagonal = max(abs(values[index][index]) for index in range(size))
    symmetry = max(
        abs(values[left][right] - values[right][left])
        for left in range(size)
        for right in range(size)
    )
    return {
        "all_values_finite": finite,
        "maximum_absolute_diagonal": diagonal,
        "maximum_symmetry_residual": symmetry,
    }


def prepared_z_scores(request: Any, fit: Any) -> list[list[float]]:
    indexes = {feature: index for index, feature in enumerate(request.candidate_features)}
    output: list[list[float]] = []
    for document in request.documents:
        row: list[float] = []
        for feature, mean, deviation in zip(
            fit.selected_features, fit.means, fit.standard_deviations, strict=True
        ):
            frequency = document.counts[indexes[feature]] * 100.0 / document.token_total
            row.append((frequency - mean) / deviation)
        output.append(row)
    return output


def hash_lines(values: list[str]) -> str:
    return hashlib.sha256(canonical_json(values)).hexdigest()


def sha_manifest(folder: Path) -> None:
    rows = []
    for path in sorted(folder.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{sha256_file(path)}  {path.name}")
    (folder / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("/opt/delta"))
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--request-metadata", type=Path, required=True)
    parser.add_argument("--worker-result", type=Path, required=True)
    parser.add_argument("--worker-fatal", type=Path, required=True)
    parser.add_argument("--oracle-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    sys.path.insert(0, str(repo / "src"))
    from delta_lemmata.stylo_contracts import (
        FitComplete,
        StyloContractError,
        parse_direct_stylo_oracle,
        parse_worker_fatal_error,
        parse_worker_input,
        parse_worker_result,
        validate_direct_stylo_oracle,
        validate_worker_result,
    )

    if args.worker_fatal.exists():
        fatal = parse_worker_fatal_error(args.worker_fatal.read_bytes())
        raise RuntimeError(f"literary-worker-fatal:{fatal.stage.value}:{fatal.error_code.value}")
    if not args.worker_result.is_file():
        raise RuntimeError("literary-worker-result-missing")

    request = parse_worker_input(args.request.read_bytes())
    worker = parse_worker_result(args.worker_result.read_bytes())
    oracle = parse_direct_stylo_oracle(args.oracle_result.read_bytes())
    validate_worker_result(request, worker)
    validate_direct_stylo_oracle(request, oracle)
    frozen = load_frozen_comparator(repo)
    try:
        whole_comparison = frozen.compare_fixture(request, worker, oracle)
    except (StyloContractError, SystemExit) as error:
        raise RuntimeError("literary-frozen-comparator-rejected") from error

    if worker.outcome.value != "complete" or oracle.outcome.value != "complete":
        raise RuntimeError("literary-parity-noncomplete-outcome")
    metadata = json.loads(args.request_metadata.read_text(encoding="utf-8"))
    binding = {
        row["document_id"]: row["logical_document_id"] for row in metadata["bindings"]
    }
    expected_labels = tuple(document.document_id for document in request.documents)
    logical_labels = [binding[label] for label in expected_labels]
    if hash_lines(list(expected_labels)) != metadata["ordered_document_ids_sha256"]:
        raise RuntimeError("literary-label-binding-hash-mismatch")

    output = args.output.resolve()
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for source, name in (
        (args.request, "literary_worker_request.json"),
        (args.request_metadata, "request_metadata.json"),
        (args.worker_result, "worker_result.json"),
        (args.oracle_result, "direct_oracle_result.json"),
    ):
        shutil.copy2(source, raw_dir / name)

    worker_fits = {fit.mfw: fit for fit in worker.fits if isinstance(fit, FitComplete)}
    oracle_fits = {fit.mfw: fit for fit in oracle.fits if isinstance(fit, FitComplete)}
    worker_cells = {fit.mfw: cell for fit, cell in zip(worker.fits, worker.cells, strict=True)}
    oracle_cells = {fit.mfw: cell for fit, cell in zip(oracle.fits, oracle.cells, strict=True)}
    summaries: list[dict[str, Any]] = []

    for mfw in MFW_GRID:
        worker_fit = worker_fits.get(mfw)
        oracle_fit = oracle_fits.get(mfw)
        if worker_fit is None or oracle_fit is None:
            raise RuntimeError(f"literary-complete-fit-missing:{mfw}")
        worker_cell = worker_cells[mfw]
        oracle_cell = oracle_cells[mfw]
        worker_labels, worker_matrix = matrix_values(worker_cell)
        oracle_labels, oracle_matrix = matrix_values(oracle_cell)
        if worker_labels != expected_labels or oracle_labels != expected_labels:
            raise RuntimeError(f"literary-matrix-label-order-mismatch:{mfw}")

        maximum_gap = -1.0
        maximum_location = (0, 0)
        for left in range(len(expected_labels)):
            for right in range(len(expected_labels)):
                gap = abs(worker_matrix[left][right] - oracle_matrix[left][right])
                if gap > maximum_gap:
                    maximum_gap = gap
                    maximum_location = (left, right)
        worker_structure = structural_metrics(worker_matrix)
        oracle_structure = structural_metrics(oracle_matrix)
        worker_ties = nearest_groups(worker_labels, worker_matrix)
        oracle_ties = nearest_groups(oracle_labels, oracle_matrix)
        worker_z = prepared_z_scores(request, worker_fit)
        oracle_z = prepared_z_scores(request, oracle_fit)
        maximum_z_gap = max(
            abs(left - right)
            for worker_row, oracle_row in zip(worker_z, oracle_z, strict=True)
            for left, right in zip(worker_row, oracle_row, strict=True)
        )
        selected_exact = worker_fit.selected_features == oracle_fit.selected_features
        ties_exact = worker_ties == oracle_ties
        passed = (
            selected_exact
            and maximum_gap <= MATRIX_TOLERANCE
            and maximum_z_gap <= STRUCTURAL_TOLERANCE
            and ties_exact
            and worker_structure["all_values_finite"]
            and oracle_structure["all_values_finite"]
            and worker_structure["maximum_absolute_diagonal"] <= STRUCTURAL_TOLERANCE
            and oracle_structure["maximum_absolute_diagonal"] <= STRUCTURAL_TOLERANCE
            and worker_structure["maximum_symmetry_residual"] <= STRUCTURAL_TOLERANCE
            and oracle_structure["maximum_symmetry_residual"] <= STRUCTURAL_TOLERANCE
        )

        folder = output / f"mfw-{mfw:04d}"
        folder.mkdir(parents=True, exist_ok=True)
        matrix_header = [["document_id", *logical_labels]]
        write_csv(
            folder / "worker_distance_matrix.csv",
            matrix_header
            + [
                [logical_labels[index], *(format(value, ".17g") for value in row)]
                for index, row in enumerate(worker_matrix)
            ],
        )
        write_csv(
            folder / "reference_distance_matrix.csv",
            matrix_header
            + [
                [logical_labels[index], *(format(value, ".17g") for value in row)]
                for index, row in enumerate(oracle_matrix)
            ],
        )
        z_header = [["document_id", *worker_fit.selected_features]]
        write_csv(
            folder / "worker_prepared_z_scores.csv",
            z_header
            + [
                [logical_labels[index], *(format(value, ".17g") for value in row)]
                for index, row in enumerate(worker_z)
            ],
        )
        write_csv(
            folder / "reference_prepared_z_scores.csv",
            z_header
            + [
                [logical_labels[index], *(format(value, ".17g") for value in row)]
                for index, row in enumerate(oracle_z)
            ],
        )
        write_json(folder / "selected_features.json", list(worker_fit.selected_features))
        write_json(
            folder / "nearest_neighbor_groups.json",
            {
                "reference": {
                    binding[label]: [binding[item] for item in group]
                    for label, group in oracle_ties.items()
                },
                "worker": {
                    binding[label]: [binding[item] for item in group]
                    for label, group in worker_ties.items()
                },
            },
        )
        summary = {
            "all_values_finite": worker_structure["all_values_finite"]
            and oracle_structure["all_values_finite"],
            "document_count": len(expected_labels),
            "maximum_matrix_absolute_difference": maximum_gap,
            "maximum_matrix_difference_cell": [
                logical_labels[maximum_location[0]],
                logical_labels[maximum_location[1]],
            ],
            "maximum_prepared_z_score_absolute_difference": maximum_z_gap,
            "mfw": mfw,
            "nearest_neighbor_tie_groups_exact": ties_exact,
            "ordered_document_ids_sha256": metadata["ordered_document_ids_sha256"],
            "ordered_features_exact": selected_exact,
            "pass": passed,
            "reference_matrix_sha256": sha256_file(folder / "reference_distance_matrix.csv"),
            "reference_prepared_z_scores_sha256": sha256_file(
                folder / "reference_prepared_z_scores.csv"
            ),
            "reference_structure": oracle_structure,
            "request_sha256": sha256_file(args.request),
            "schema_version": "literary-parity-comparison-v1",
            "selected_features_sha256": sha256_file(folder / "selected_features.json"),
            "thresholds": {
                "matrix": MATRIX_TOLERANCE,
                "structural": STRUCTURAL_TOLERANCE,
                "tie": TIE_TOLERANCE,
            },
            "worker_matrix_sha256": sha256_file(folder / "worker_distance_matrix.csv"),
            "worker_prepared_z_scores_sha256": sha256_file(
                folder / "worker_prepared_z_scores.csv"
            ),
            "worker_structure": worker_structure,
        }
        write_json(folder / "comparison_report.json", summary)
        sha_manifest(folder)
        summaries.append(summary)

    overall = {
        "all_mfw_pass": all(item["pass"] for item in summaries),
        "frozen_comparator_summary": whole_comparison,
        "mfw_results": summaries,
        "oracle_result_sha256": sha256_file(args.oracle_result),
        "request_sha256": sha256_file(args.request),
        "schema_version": "literary-parity-comparison-suite-v1",
        "worker_result_sha256": sha256_file(args.worker_result),
    }
    write_json(output / "comparison_summary.json", overall)
    sha_manifest(raw_dir)
    if not overall["all_mfw_pass"]:
        raise RuntimeError("literary-parity-threshold-failure")
    print("literary_parity=pass")
    print("mfw=100,300,500,1000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
