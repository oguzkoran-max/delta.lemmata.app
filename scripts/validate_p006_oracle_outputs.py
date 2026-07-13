#!/usr/bin/env python3
"""Validate frozen-candidate P006 direct-stylo outputs and leakage invariants."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from delta_lemmata.stylo_contracts import (
    CellComplete,
    CellNotEnoughFeatures,
    DirectStyloOracleV1,
    FitComplete,
    FitNotEnoughFeatures,
    WorkerInputV1,
    parse_direct_stylo_oracle,
    parse_worker_input,
    validate_direct_stylo_oracle,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v1"
MANIFEST_PATH = FIXTURE_DIR / "fixture-manifest.json"
EXPECTED_SESSION_FIELDS = {
    "blas",
    "jsonlite_version",
    "lang",
    "lapack",
    "lc_collate",
    "lc_ctype",
    "lc_numeric",
    "operating_system",
    "platform",
    "r_version",
    "rng_generator",
    "rng_normal_generator",
    "rng_sample_kind",
    "seed",
    "stylo_version",
    "timezone",
    "unicode_normalization",
}


def _load_manifest() -> dict[str, Any]:
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("P006_ORACLE_MANIFEST_INVALID")
    return value


def _direct_name(input_file: str) -> str:
    suffix = ".input.json"
    if not input_file.endswith(suffix):
        raise ValueError("P006_ORACLE_MANIFEST_INVALID")
    return f"{input_file[: -len(suffix)]}.direct.json"


def _load_records(
    output_directory: Path,
) -> tuple[dict[str, WorkerInputV1], dict[str, DirectStyloOracleV1]]:
    manifest = _load_manifest()
    fixtures = manifest.get("fixtures")
    if not isinstance(fixtures, list):
        raise ValueError("P006_ORACLE_MANIFEST_INVALID")
    expected_names = {"session-info.json"}
    requests: dict[str, WorkerInputV1] = {}
    records: dict[str, DirectStyloOracleV1] = {}
    for entry in fixtures:
        if not isinstance(entry, dict):
            raise ValueError("P006_ORACLE_MANIFEST_INVALID")
        input_file = entry.get("input_file")
        fixture_ref = entry.get("fixture_ref")
        expected_outcome = entry.get("expected_outcome")
        if not isinstance(input_file, str) or not isinstance(fixture_ref, str):
            raise ValueError("P006_ORACLE_MANIFEST_INVALID")
        direct_name = _direct_name(input_file)
        expected_names.add(direct_name)
        request = parse_worker_input((FIXTURE_DIR / input_file).read_bytes())
        record = parse_direct_stylo_oracle((output_directory / direct_name).read_bytes())
        validate_direct_stylo_oracle(request, record)
        if record.fixture_ref != fixture_ref or record.outcome.value != expected_outcome:
            raise ValueError("P006_ORACLE_BINDING_INVALID")
        requests[input_file] = request
        records[input_file] = record
    output_entries = tuple(output_directory.iterdir())
    if any(path.is_symlink() or not path.is_file() for path in output_entries):
        raise ValueError("P006_ORACLE_OUTPUT_SET_INVALID")
    actual_names = {path.name for path in output_entries}
    if actual_names != expected_names:
        raise ValueError("P006_ORACLE_OUTPUT_SET_INVALID")
    session_bytes = (output_directory / "session-info.json").read_bytes()
    if not session_bytes or len(session_bytes) > 4096:
        raise ValueError("P006_ORACLE_SESSION_INVALID")
    session = json.loads(session_bytes)
    if not isinstance(session, dict) or set(session) != EXPECTED_SESSION_FIELDS:
        raise ValueError("P006_ORACLE_SESSION_INVALID")
    if any(record.session.model_dump(mode="json") != session for record in records.values()):
        raise ValueError("P006_ORACLE_SESSION_MISMATCH")
    return requests, records


def _known_submatrix(cell: CellComplete, known_count: int) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(row[:known_count]) for row in cell.matrix.values[:known_count])


def _complete_cells(record: DirectStyloOracleV1) -> dict[tuple[str, str], CellComplete]:
    cells: dict[tuple[str, str], CellComplete] = {}
    for cell in record.cells:
        if not isinstance(cell, CellComplete):
            raise ValueError("P006_ORACLE_COMPLETE_FIXTURE_INVALID")
        cells[(cell.fit_id, cell.distance.value)] = cell
    return cells


def _validate_leakage_pair(
    base_request: WorkerInputV1,
    canary_request: WorkerInputV1,
    base: DirectStyloOracleV1,
    canary: DirectStyloOracleV1,
) -> None:
    if base.fitting_basis != canary.fitting_basis or base.fits != canary.fits:
        raise ValueError("P006_ORACLE_UNKNOWN_LEAKAGE")
    ranked = tuple(item.feature for item in base.fitting_basis.ranked_features)
    if "canary_only" in ranked:
        raise ValueError("P006_ORACLE_UNKNOWN_LEAKAGE")
    for fit in base.fits:
        if isinstance(fit, FitComplete) and "canary_only" in fit.selected_features:
            raise ValueError("P006_ORACLE_UNKNOWN_LEAKAGE")

    known_count = len(base.fitting_basis.known_document_ids)
    base_cells = _complete_cells(base)
    canary_cells = _complete_cells(canary)
    if base_cells.keys() != canary_cells.keys():
        raise ValueError("P006_ORACLE_UNKNOWN_LEAKAGE")
    unknown_changed = False
    for key, base_cell in base_cells.items():
        canary_cell = canary_cells[key]
        if _known_submatrix(base_cell, known_count) != _known_submatrix(canary_cell, known_count):
            raise ValueError("P006_ORACLE_UNKNOWN_LEAKAGE")
        base_unknown = base_cell.matrix.values[known_count]
        canary_unknown = canary_cell.matrix.values[known_count]
        if any(
            abs(left - right) > 1e-12
            for left, right in zip(
                base_unknown[:known_count],
                canary_unknown[:known_count],
                strict=True,
            )
        ):
            unknown_changed = True
    if not unknown_changed:
        raise ValueError("P006_ORACLE_CANARY_INACTIVE")
    if base_request.documents[:-1] != canary_request.documents[:-1]:
        raise ValueError("P006_ORACLE_FIXTURE_PAIR_INVALID")


def _validate_declared_ties(record: DirectStyloOracleV1) -> None:
    target_fit = next(
        (
            fit
            for fit in record.fits
            if isinstance(fit, FitComplete) and fit.mfw == 3 and fit.culling_percent == 100
        ),
        None,
    )
    if target_fit is None:
        raise ValueError("P006_ORACLE_TIE_FIXTURE_INVALID")
    cells = _complete_cells(record)
    for distance in ("classic_delta", "eders_delta"):
        matrix = cells[(target_fit.fit_id, distance)].matrix.values
        if abs(matrix[1][0] - matrix[1][2]) > 1e-12:
            raise ValueError("P006_ORACLE_TIE_FIXTURE_INVALID")


def validate_output_directory(
    output_directory: Path,
) -> tuple[dict[str, WorkerInputV1], dict[str, DirectStyloOracleV1]]:
    if not output_directory.is_dir():
        raise ValueError("P006_ORACLE_OUTPUT_DIRECTORY_INVALID")
    requests, records = _load_records(output_directory)
    _validate_leakage_pair(
        requests["complete-base.input.json"],
        requests["complete-canary.input.json"],
        records["complete-base.input.json"],
        records["complete-canary.input.json"],
    )
    _validate_declared_ties(records["complete-base.input.json"])
    partial = records["partial-boundaries.input.json"]
    fit_statuses = tuple(type(fit) for fit in partial.fits)
    if fit_statuses != (
        FitComplete,
        FitNotEnoughFeatures,
        FitComplete,
        FitNotEnoughFeatures,
        FitComplete,
        FitNotEnoughFeatures,
        FitComplete,
    ):
        raise ValueError("P006_ORACLE_BOUNDARY_STATUSES_INVALID")
    cell_statuses = tuple(type(cell) for cell in partial.cells)
    if cell_statuses != (
        CellComplete,
        CellNotEnoughFeatures,
        CellComplete,
        CellNotEnoughFeatures,
        CellComplete,
        CellNotEnoughFeatures,
        CellComplete,
    ):
        raise ValueError("P006_ORACLE_BOUNDARY_STATUSES_INVALID")
    return requests, records


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    validate_output_directory(args.output_directory)
    print("p006-oracle-output-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
