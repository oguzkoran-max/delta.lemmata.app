#!/usr/bin/env python3
"""Validate frozen-candidate P006 direct-stylo outputs and leakage invariants."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from validate_p006_fixture_v2 import (
    BASE_NAME as V2_BASE_NAME,
)
from validate_p006_fixture_v2 import (
    CANARY_NAME as V2_CANARY_NAME,
)
from validate_p006_fixture_v2 import (
    FIXTURE_DIR as V2_FIXTURE_DIR,
)
from validate_p006_fixture_v2 import (
    MANIFEST_PATH as V2_MANIFEST_PATH,
)
from validate_p006_fixture_v2 import (
    MINIMUM_COUNTERFACTUAL_GAP,
    counterfactual_matrices,
    validate_fixture_suite,
)
from validate_p006_fixture_v2 import (
    PERMUTATION_NAME as V2_PERMUTATION_NAME,
)

from delta_lemmata.stylo_contracts import (
    CellComplete,
    CellNotEnoughFeatures,
    DirectStyloOracleV1,
    DistanceMeasure,
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


class _DuplicateSessionKey(ValueError):
    pass


def _unique_session_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateSessionKey
        value[key] = item
    return value


def _reject_session_constant(_value: str) -> None:
    raise ValueError


def _parse_canonical_session(payload: bytes) -> dict[str, Any]:
    try:
        session = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_session_object,
            parse_constant=_reject_session_constant,
        )
        canonical = (
            json.dumps(
                session,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode()
    except (
        _DuplicateSessionKey,
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        raise ValueError("P006_ORACLE_SESSION_INVALID") from None
    if not isinstance(session, dict) or payload != canonical:
        raise ValueError("P006_ORACLE_SESSION_INVALID")
    return session


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
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
    *,
    fixture_dir: Path = FIXTURE_DIR,
    manifest_path: Path = MANIFEST_PATH,
    session_path: Path | None = None,
) -> tuple[dict[str, WorkerInputV1], dict[str, DirectStyloOracleV1]]:
    manifest = _load_manifest(manifest_path)
    fixtures = manifest.get("fixtures")
    if not isinstance(fixtures, list):
        raise ValueError("P006_ORACLE_MANIFEST_INVALID")
    embedded_session = session_path is None
    expected_names = {"session-info.json"} if embedded_session else set()
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
        request = parse_worker_input((fixture_dir / input_file).read_bytes())
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
    resolved_session_path = (
        output_directory / "session-info.json" if embedded_session else session_path
    )
    if (
        resolved_session_path is None
        or resolved_session_path.is_symlink()
        or not resolved_session_path.is_file()
    ):
        raise ValueError("P006_ORACLE_SESSION_INVALID")
    session_bytes = resolved_session_path.read_bytes()
    if not session_bytes or len(session_bytes) > 4096:
        raise ValueError("P006_ORACLE_SESSION_INVALID")
    session = _parse_canonical_session(session_bytes)
    if set(session) != EXPECTED_SESSION_FIELDS:
        raise ValueError("P006_ORACLE_SESSION_INVALID")
    if any(record.session.model_dump(mode="json") != session for record in records.values()):
        raise ValueError("P006_ORACLE_SESSION_MISMATCH")
    return requests, records


def _matrix_projection(
    cell: CellComplete,
    document_ids: tuple[str, ...],
) -> tuple[tuple[float, ...], ...]:
    indexes = {document_id: index for index, document_id in enumerate(cell.matrix.document_ids)}
    return tuple(
        tuple(cell.matrix.values[indexes[left]][indexes[right]] for right in document_ids)
        for left in document_ids
    )


def _document_map(request: WorkerInputV1) -> dict[str, Any]:
    return {document.document_id: document for document in request.documents}


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
    if (
        base_request.candidate_features != canary_request.candidate_features
        or base_request.fits != canary_request.fits
        or base_request.cells != canary_request.cells
    ):
        raise ValueError("P006_ORACLE_FIXTURE_PAIR_INVALID")
    base_documents = _document_map(base_request)
    canary_documents = _document_map(canary_request)
    if base_documents.keys() != canary_documents.keys():
        raise ValueError("P006_ORACLE_FIXTURE_PAIR_INVALID")
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
    changed_unknown_ids: set[str] = set()
    for document_id, base_document in base_documents.items():
        canary_document = canary_documents[document_id]
        if base_document.role.value == "known":
            if base_document != canary_document:
                raise ValueError("P006_ORACLE_FIXTURE_PAIR_INVALID")
        elif (
            base_document.asset_ref != canary_document.asset_ref
            or base_document.work_ref != canary_document.work_ref
            or base_document.role != canary_document.role
            or base_document.token_total != canary_document.token_total
            or base_document.counts == canary_document.counts
        ):
            raise ValueError("P006_ORACLE_FIXTURE_PAIR_INVALID")
        else:
            changed_unknown_ids.add(document_id)
    if changed_unknown_ids != set(unknown_ids):
        raise ValueError("P006_ORACLE_FIXTURE_PAIR_INVALID")

    if base.fitting_basis != canary.fitting_basis or base.fits != canary.fits:
        raise ValueError("P006_ORACLE_UNKNOWN_LEAKAGE")
    known_documents = tuple(
        document for document in base_request.documents if document.role.value == "known"
    )
    unknown_documents = tuple(
        document for document in base_request.documents if document.role.value == "unknown"
    )
    unknown_only_features = {
        feature
        for index, feature in enumerate(base_request.candidate_features)
        if all(document.counts[index] == 0 for document in known_documents)
        and any(document.counts[index] > 0 for document in unknown_documents)
    }
    if not unknown_only_features:
        raise ValueError("P006_ORACLE_FIXTURE_PAIR_INVALID")
    ranked = {item.feature for item in base.fitting_basis.ranked_features}
    if ranked & unknown_only_features:
        raise ValueError("P006_ORACLE_UNKNOWN_LEAKAGE")
    for fit in base.fits:
        if isinstance(fit, FitComplete) and set(fit.selected_features) & unknown_only_features:
            raise ValueError("P006_ORACLE_UNKNOWN_LEAKAGE")

    base_cells = _complete_cells(base)
    canary_cells = _complete_cells(canary)
    if base_cells.keys() != canary_cells.keys():
        raise ValueError("P006_ORACLE_UNKNOWN_LEAKAGE")
    active_pairs: set[tuple[str, str]] = set()
    for key, base_cell in base_cells.items():
        canary_cell = canary_cells[key]
        if _matrix_projection(base_cell, known_ids) != _matrix_projection(
            canary_cell,
            known_ids,
        ):
            raise ValueError("P006_ORACLE_UNKNOWN_LEAKAGE")
        base_indexes = {
            document_id: index for index, document_id in enumerate(base_cell.matrix.document_ids)
        }
        canary_indexes = {
            document_id: index for index, document_id in enumerate(canary_cell.matrix.document_ids)
        }
        for unknown_id in unknown_ids:
            if any(
                abs(
                    base_cell.matrix.values[base_indexes[unknown_id]][base_indexes[known_id]]
                    - canary_cell.matrix.values[canary_indexes[unknown_id]][
                        canary_indexes[known_id]
                    ]
                )
                > 1e-12
                for known_id in known_ids
            ):
                active_pairs.add((unknown_id, base_cell.distance.value))
    active_unknowns = {unknown_id for unknown_id, _distance in active_pairs}
    if active_unknowns != set(unknown_ids):
        raise ValueError("P006_ORACLE_CANARY_INACTIVE")
    expected_pairs = {
        (unknown_id, distance.value) for unknown_id in unknown_ids for distance in DistanceMeasure
    }
    if len(unknown_ids) > 1 and active_pairs != expected_pairs:
        raise ValueError("P006_ORACLE_CANARY_INACTIVE")


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


def _validate_order_permutation(
    base_request: WorkerInputV1,
    permutation_request: WorkerInputV1,
    base: DirectStyloOracleV1,
    permutation: DirectStyloOracleV1,
) -> None:
    if _document_map(base_request) != _document_map(permutation_request):
        raise ValueError("P006_ORACLE_ORDER_INVARIANCE_INVALID")
    if (
        base_request.candidate_features != permutation_request.candidate_features
        or base_request.fits != permutation_request.fits
        or base_request.cells != permutation_request.cells
        or tuple(document.document_id for document in base_request.documents)
        == tuple(document.document_id for document in permutation_request.documents)
    ):
        raise ValueError("P006_ORACLE_ORDER_INVARIANCE_INVALID")
    if (
        base.fitting_basis.ranked_features != permutation.fitting_basis.ranked_features
        or base.fits != permutation.fits
    ):
        raise ValueError("P006_ORACLE_ORDER_INVARIANCE_INVALID")
    base_cells = _complete_cells(base)
    permutation_cells = _complete_cells(permutation)
    if base_cells.keys() != permutation_cells.keys():
        raise ValueError("P006_ORACLE_ORDER_INVARIANCE_INVALID")
    document_ids = tuple(document.document_id for document in base_request.documents)
    for key, base_cell in base_cells.items():
        base_projection = _matrix_projection(base_cell, document_ids)
        permutation_projection = _matrix_projection(permutation_cells[key], document_ids)
        if any(
            abs(left - right) > 1e-12
            for left_row, right_row in zip(
                base_projection,
                permutation_projection,
                strict=True,
            )
            for left, right in zip(left_row, right_row, strict=True)
        ):
            raise ValueError("P006_ORACLE_ORDER_INVARIANCE_INVALID")


def _matrix_gap(
    actual: CellComplete,
    expected: tuple[tuple[float, ...], ...],
    request: WorkerInputV1,
    document_ids: tuple[str, ...],
) -> float:
    actual_indexes = {
        document_id: index for index, document_id in enumerate(actual.matrix.document_ids)
    }
    expected_indexes = {
        document.document_id: index for index, document in enumerate(request.documents)
    }
    return max(
        abs(
            actual.matrix.values[actual_indexes[left]][actual_indexes[right]]
            - expected[expected_indexes[left]][expected_indexes[right]]
        )
        for left in document_ids
        for right in document_ids
    )


def _validate_normalization_counterfactual(
    request: WorkerInputV1,
    record: DirectStyloOracleV1,
) -> None:
    normalized = counterfactual_matrices(request, relative=True)
    raw = counterfactual_matrices(request, relative=False)
    cells = _complete_cells(record)
    all_ids = tuple(document.document_id for document in request.documents)
    known_ids = tuple(
        document.document_id for document in request.documents if document.role.value == "known"
    )
    for fit in request.fits:
        for distance in DistanceMeasure:
            key = (fit.fit_id, distance.value)
            cell = cells[key]
            if _matrix_gap(cell, normalized[(fit.fit_id, distance)], request, all_ids) > 1e-10:
                raise ValueError("P006_ORACLE_NORMALIZED_REFERENCE_INVALID")
            if (
                _matrix_gap(cell, raw[(fit.fit_id, distance)], request, known_ids)
                <= MINIMUM_COUNTERFACTUAL_GAP
            ):
                raise ValueError("P006_ORACLE_RAW_COUNTERFACTUAL_INACTIVE")


def validate_output_directory_v2(
    output_directory: Path,
    *,
    session_path: Path | None = None,
) -> tuple[dict[str, WorkerInputV1], dict[str, DirectStyloOracleV1]]:
    if not output_directory.is_dir():
        raise ValueError("P006_ORACLE_OUTPUT_DIRECTORY_INVALID")
    validate_fixture_suite()
    requests, records = _load_records(
        output_directory,
        fixture_dir=V2_FIXTURE_DIR,
        manifest_path=V2_MANIFEST_PATH,
        session_path=session_path,
    )
    _validate_leakage_pair(
        requests[V2_BASE_NAME],
        requests[V2_CANARY_NAME],
        records[V2_BASE_NAME],
        records[V2_CANARY_NAME],
    )
    _validate_order_permutation(
        requests[V2_BASE_NAME],
        requests[V2_PERMUTATION_NAME],
        records[V2_BASE_NAME],
        records[V2_PERMUTATION_NAME],
    )
    _validate_normalization_counterfactual(
        requests[V2_BASE_NAME],
        records[V2_BASE_NAME],
    )
    return requests, records


def validate_output_directory(
    output_directory: Path,
    *,
    session_path: Path | None = None,
) -> tuple[dict[str, WorkerInputV1], dict[str, DirectStyloOracleV1]]:
    if not output_directory.is_dir():
        raise ValueError("P006_ORACLE_OUTPUT_DIRECTORY_INVALID")
    requests, records = _load_records(output_directory, session_path=session_path)
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
    parser.add_argument("--suite", choices=("v1", "v2"), default="v1")
    args = parser.parse_args()
    if args.suite == "v1":
        validate_output_directory(args.output_directory)
    else:
        validate_output_directory_v2(args.output_directory)
    print("p006-oracle-output-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
