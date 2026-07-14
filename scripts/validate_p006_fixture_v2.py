#!/usr/bin/env python3
"""Validate the adversarial design of the P006 whole-text v2 fixtures."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from delta_lemmata.stylo_contracts import (
    DistanceMeasure,
    DocumentCounts,
    DocumentRole,
    WorkerInputV1,
    parse_worker_input,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v2"
MANIFEST_PATH = FIXTURE_DIR / "fixture-manifest.json"
BASE_NAME = "normalization-base.input.json"
CANARY_NAME = "normalization-canary.input.json"
PERMUTATION_NAME = "order-permutation.input.json"
EXPECTED_ROLE_ORDER = (
    DocumentRole.KNOWN,
    DocumentRole.UNKNOWN,
    DocumentRole.KNOWN,
    DocumentRole.KNOWN,
    DocumentRole.UNKNOWN,
    DocumentRole.KNOWN,
)
MINIMUM_COUNTERFACTUAL_GAP = 1e-3

type Matrix = tuple[tuple[float, ...], ...]
type MatrixSet = dict[tuple[str, DistanceMeasure], Matrix]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_requests() -> dict[str, WorkerInputV1]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != "p006-fixture-manifest-v1"
        or manifest.get("suite_id") != "p006-whole-text-v2"
        or manifest.get("license") != "CC0-1.0"
        or manifest.get("license_file") != "LICENSE"
    ):
        raise ValueError("P006_V2_MANIFEST_INVALID")
    fixtures = manifest.get("fixtures")
    if not isinstance(fixtures, list) or len(fixtures) != 3:
        raise ValueError("P006_V2_MANIFEST_INVALID")
    requests: dict[str, WorkerInputV1] = {}
    for entry in fixtures:
        if not isinstance(entry, dict):
            raise ValueError("P006_V2_MANIFEST_INVALID")
        input_file = entry.get("input_file")
        input_sha256 = entry.get("input_sha256")
        if (
            not isinstance(input_file, str)
            or not isinstance(input_sha256, str)
            or entry.get("expected_outcome") != "complete"
        ):
            raise ValueError("P006_V2_MANIFEST_INVALID")
        input_path = FIXTURE_DIR / input_file
        if input_path.parent != FIXTURE_DIR or _sha256(input_path) != input_sha256:
            raise ValueError("P006_V2_MANIFEST_INVALID")
        requests[input_file] = parse_worker_input(input_path.read_bytes())
    if set(requests) != {BASE_NAME, CANARY_NAME, PERMUTATION_NAME}:
        raise ValueError("P006_V2_MANIFEST_INVALID")
    return requests


def _documents_by_id(request: WorkerInputV1) -> dict[str, DocumentCounts]:
    return {document.document_id: document for document in request.documents}


def _known_documents(request: WorkerInputV1) -> tuple[DocumentCounts, ...]:
    return tuple(document for document in request.documents if document.role is DocumentRole.KNOWN)


def _ranked_feature_indexes(request: WorkerInputV1) -> tuple[int, ...]:
    known = _known_documents(request)
    totals = tuple(
        sum(document.counts[index] for document in known)
        for index in range(len(request.candidate_features))
    )
    return tuple(
        sorted(
            (index for index, total in enumerate(totals) if total > 0),
            key=lambda index: (-totals[index], request.candidate_features[index].encode()),
        )
    )


def _selected_feature_indexes(request: WorkerInputV1, fit_id: str) -> tuple[int, ...]:
    fit = next(fit for fit in request.fits if fit.fit_id == fit_id)
    known = _known_documents(request)
    eligible = tuple(
        index
        for index in _ranked_feature_indexes(request)
        if sum(document.counts[index] > 0 for document in known) * 100
        >= fit.culling_percent * len(known)
    )
    if len(eligible) < fit.mfw:
        raise ValueError("P006_V2_FIT_NOT_COMPLETE")
    return eligible[: fit.mfw]


def _z_scores(
    request: WorkerInputV1,
    selected: tuple[int, ...],
    *,
    relative: bool,
) -> tuple[tuple[float, ...], ...]:
    rows = tuple(
        tuple(
            document.counts[index] * 100.0 / document.token_total
            if relative
            else float(document.counts[index])
            for index in selected
        )
        for document in request.documents
    )
    known_indexes = tuple(
        index
        for index, document in enumerate(request.documents)
        if document.role is DocumentRole.KNOWN
    )
    means: list[float] = []
    deviations: list[float] = []
    for column in range(len(selected)):
        values = tuple(rows[index][column] for index in known_indexes)
        mean = math.fsum(values) / len(values)
        deviation = math.sqrt(
            math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1)
        )
        if deviation <= 0:
            raise ValueError("P006_V2_NON_POSITIVE_DEVIATION")
        means.append(mean)
        deviations.append(deviation)
    return tuple(
        tuple((value - means[column]) / deviations[column] for column, value in enumerate(row))
        for row in rows
    )


def _distance_matrix(
    z_scores: tuple[tuple[float, ...], ...],
    distance: DistanceMeasure,
) -> Matrix:
    feature_count = len(z_scores[0])
    weights = tuple((1 + rank) / feature_count for rank in range(feature_count, 0, -1))
    norms = tuple(math.sqrt(math.fsum(value * value for value in row)) for row in z_scores)
    if any(norm <= 0 for norm in norms):
        raise ValueError("P006_V2_COSINE_NORM_INVALID")
    matrix: list[tuple[float, ...]] = []
    for left_index, left in enumerate(z_scores):
        values: list[float] = []
        for right_index, right in enumerate(z_scores):
            if left_index == right_index:
                values.append(0.0)
            elif distance is DistanceMeasure.CLASSIC_DELTA:
                values.append(
                    math.fsum(
                        abs(left_value - right_value)
                        for left_value, right_value in zip(left, right, strict=True)
                    )
                    / feature_count
                )
            elif distance is DistanceMeasure.EDERS_DELTA:
                values.append(
                    math.fsum(
                        abs(left_value - right_value) * weight
                        for left_value, right_value, weight in zip(
                            left,
                            right,
                            weights,
                            strict=True,
                        )
                    )
                )
            else:
                values.append(
                    1.0
                    - math.fsum(
                        left_value * right_value
                        for left_value, right_value in zip(left, right, strict=True)
                    )
                    / (norms[left_index] * norms[right_index])
                )
        matrix.append(tuple(values))
    return tuple(matrix)


def counterfactual_matrices(request: WorkerInputV1, *, relative: bool) -> MatrixSet:
    matrices: MatrixSet = {}
    for fit in request.fits:
        selected = _selected_feature_indexes(request, fit.fit_id)
        z_scores = _z_scores(request, selected, relative=relative)
        for distance in DistanceMeasure:
            matrices[(fit.fit_id, distance)] = _distance_matrix(z_scores, distance)
    return matrices


def _known_gap(
    request: WorkerInputV1,
    left: Matrix,
    right: Matrix,
) -> float:
    known_indexes = tuple(
        index
        for index, document in enumerate(request.documents)
        if document.role is DocumentRole.KNOWN
    )
    return max(
        abs(left[row][column] - right[row][column])
        for row in known_indexes
        for column in known_indexes
    )


def _projection_gap(
    left_request: WorkerInputV1,
    left: Matrix,
    right_request: WorkerInputV1,
    right: Matrix,
    left_ids: tuple[str, ...],
    right_ids: tuple[str, ...],
) -> float:
    left_indexes = {
        document.document_id: index for index, document in enumerate(left_request.documents)
    }
    right_indexes = {
        document.document_id: index for index, document in enumerate(right_request.documents)
    }
    return max(
        abs(
            left[left_indexes[left_id]][left_indexes[right_id]]
            - right[right_indexes[left_id]][right_indexes[right_id]]
        )
        for left_id in left_ids
        for right_id in right_ids
    )


def _require_fixture_topology(
    base: WorkerInputV1,
    canary: WorkerInputV1,
    permutation: WorkerInputV1,
) -> None:
    if tuple(document.role for document in base.documents) != EXPECTED_ROLE_ORDER:
        raise ValueError("P006_V2_ROLE_ORDER_INVALID")
    if tuple(document.role for document in canary.documents) != EXPECTED_ROLE_ORDER:
        raise ValueError("P006_V2_ROLE_ORDER_INVALID")
    if permutation.documents[-1].role is not DocumentRole.KNOWN:
        raise ValueError("P006_V2_ROLE_ORDER_INVALID")
    if sum(document.role is DocumentRole.UNKNOWN for document in base.documents) != 2:
        raise ValueError("P006_V2_ROLE_ORDER_INVALID")
    if len({document.token_total for document in base.documents}) != len(base.documents):
        raise ValueError("P006_V2_TOKEN_TOTALS_INVALID")

    base_by_id = _documents_by_id(base)
    canary_by_id = _documents_by_id(canary)
    permutation_by_id = _documents_by_id(permutation)
    if base_by_id.keys() != canary_by_id.keys() or base_by_id != permutation_by_id:
        raise ValueError("P006_V2_PERMUTATION_INVALID")
    if tuple(base_by_id) == tuple(document.document_id for document in permutation.documents):
        raise ValueError("P006_V2_PERMUTATION_INVALID")

    changed_unknowns = 0
    for document_id, base_document in base_by_id.items():
        canary_document = canary_by_id[document_id]
        if base_document.role is DocumentRole.KNOWN:
            if base_document != canary_document:
                raise ValueError("P006_V2_CANARY_INVALID")
        else:
            if (
                base_document.document_id != canary_document.document_id
                or base_document.asset_ref != canary_document.asset_ref
                or base_document.work_ref != canary_document.work_ref
                or base_document.role is not canary_document.role
                or base_document.token_total != canary_document.token_total
                or base_document.counts == canary_document.counts
            ):
                raise ValueError("P006_V2_CANARY_INVALID")
            changed_unknowns += 1
    if changed_unknowns != 2:
        raise ValueError("P006_V2_CANARY_INVALID")
    if base.candidate_features != canary.candidate_features:
        raise ValueError("P006_V2_CANARY_INVALID")
    if base.fits != canary.fits or base.cells != canary.cells:
        raise ValueError("P006_V2_CANARY_INVALID")
    if base.candidate_features != permutation.candidate_features:
        raise ValueError("P006_V2_PERMUTATION_INVALID")
    if base.fits != permutation.fits or base.cells != permutation.cells:
        raise ValueError("P006_V2_PERMUTATION_INVALID")


def _require_counterfactual_separation(base: WorkerInputV1) -> None:
    normalized = counterfactual_matrices(base, relative=True)
    raw = counterfactual_matrices(base, relative=False)
    for distance in DistanceMeasure:
        gaps = tuple(
            _known_gap(base, normalized[(fit.fit_id, distance)], raw[(fit.fit_id, distance)])
            for fit in base.fits
        )
        if min(gaps) <= MINIMUM_COUNTERFACTUAL_GAP:
            raise ValueError("P006_V2_RAW_COUNTERFACTUAL_INACTIVE")


def _require_projection_canaries(
    base: WorkerInputV1,
    canary: WorkerInputV1,
    permutation: WorkerInputV1,
) -> None:
    base_matrices = counterfactual_matrices(base, relative=True)
    canary_matrices = counterfactual_matrices(canary, relative=True)
    permutation_matrices = counterfactual_matrices(permutation, relative=True)
    all_ids = tuple(document.document_id for document in base.documents)
    known_ids = tuple(
        document.document_id for document in base.documents if document.role is DocumentRole.KNOWN
    )
    unknown_ids = tuple(
        document.document_id for document in base.documents if document.role is DocumentRole.UNKNOWN
    )
    for fit in base.fits:
        for distance in DistanceMeasure:
            key = (fit.fit_id, distance)
            if (
                _projection_gap(
                    base,
                    base_matrices[key],
                    canary,
                    canary_matrices[key],
                    known_ids,
                    known_ids,
                )
                > 1e-12
            ):
                raise ValueError("P006_V2_KNOWN_LEAKAGE_CANARY_INVALID")
            if (
                _projection_gap(
                    base,
                    base_matrices[key],
                    permutation,
                    permutation_matrices[key],
                    all_ids,
                    all_ids,
                )
                > 1e-12
            ):
                raise ValueError("P006_V2_PERMUTATION_CANARY_INVALID")
            for unknown_id in unknown_ids:
                if (
                    _projection_gap(
                        base,
                        base_matrices[key],
                        canary,
                        canary_matrices[key],
                        (unknown_id,),
                        known_ids,
                    )
                    <= MINIMUM_COUNTERFACTUAL_GAP
                ):
                    raise ValueError("P006_V2_UNKNOWN_CANARY_INACTIVE")


def validate_fixture_suite() -> dict[str, WorkerInputV1]:
    requests = load_requests()
    base = requests[BASE_NAME]
    canary = requests[CANARY_NAME]
    permutation = requests[PERMUTATION_NAME]
    _require_fixture_topology(base, canary, permutation)
    _require_counterfactual_separation(base)
    _require_projection_canaries(base, canary, permutation)
    return requests


def main() -> int:
    validate_fixture_suite()
    print("p006-v2-fixture-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
