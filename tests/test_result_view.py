from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from delta_lemmata.corpus_models import PurposeId
from delta_lemmata.result_view import (
    MAX_RESULT_VIEW_BYTES,
    P009ContractError,
    P009ContractErrorCode,
    ResultCellStatus,
    ResultDocumentDescriptor,
    ResultViewV1,
    canonical_result_view,
    classical_mds,
    export_p009_schema,
    nearest_neighbours,
    parse_result_view,
    project_result_view,
    result_view_sha256,
)
from delta_lemmata.stylo_contracts import (
    AnalysisOutcome,
    CellComplete,
    CellErrorCode,
    CellFailed,
    CellNotEnoughFeatures,
    DistanceMatrix,
    DistanceMeasure,
    DocumentRole,
    FitComplete,
    FitNotEnoughFeatures,
    FittingBasis,
    RSessionInfoV1,
    WorkerResultV1,
)
from delta_lemmata.workflow_models import resolve_guided_workflow, workflow_config_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "result-view-v1.schema.json"


def _opaque(prefix: str, index: int) -> str:
    return f"{prefix}_{hashlib.sha256(f'{prefix}-{index}'.encode()).hexdigest()}"


DOCUMENT_IDS = tuple(_opaque("doc", index) for index in range(3))
DESCRIPTORS = tuple(
    ResultDocumentDescriptor(
        document_id=document_id,
        title=title,
        role=DocumentRole.KNOWN,
    )
    for document_id, title in zip(
        DOCUMENT_IDS,
        ("Early work", "Middle work", "Late work"),
        strict=True,
    )
)
BASE_MATRIX = (
    (0.0, 1.0, 1.0),
    (1.0, 0.0, 1.5),
    (1.0, 1.5, 0.0),
)


def _session() -> RSessionInfoV1:
    return RSessionInfoV1(
        r_version="4.5.2",
        stylo_version="0.7.71",
        jsonlite_version="2.0.0",
        platform="x86_64-pc-linux-gnu",
        operating_system="Ubuntu 24.04",
        lang="C.UTF-8",
        lc_collate="C.UTF-8",
        lc_ctype="C.UTF-8",
        lc_numeric="C",
        timezone="UTC",
        unicode_normalization="NFC",
        rng_generator="Mersenne-Twister",
        rng_normal_generator="Inversion",
        rng_sample_kind="Rejection",
        seed=20260713,
        blas="Reference BLAS",
        lapack="Reference LAPACK",
    )


def _result(*, partial: bool = False) -> WorkerResultV1:
    mfws = (100, 300, 500, 1000)
    fits = []
    cells = []
    for index, mfw in enumerate(mfws):
        fit_id = _opaque("fit", index)
        cell_id = _opaque("cell", index)
        if partial and mfw == 1000:
            fits.append(
                FitNotEnoughFeatures(
                    fit_id=fit_id,
                    mfw=mfw,
                    culling_percent=0,
                    status="not_enough_features",
                    eligible_feature_count=900,
                )
            )
            cells.append(
                CellNotEnoughFeatures(
                    cell_id=cell_id,
                    fit_id=fit_id,
                    distance=DistanceMeasure.CLASSIC_DELTA,
                    status="not_enough_features",
                    error_code="not_enough_features",
                )
            )
            continue
        features = tuple(f"feature-{feature:04d}" for feature in range(mfw))
        fits.append(
            FitComplete(
                fit_id=fit_id,
                mfw=mfw,
                culling_percent=0,
                status="complete",
                eligible_feature_count=1200,
                selected_features=features,
                means=tuple(0.0 for _ in features),
                standard_deviations=tuple(1.0 for _ in features),
            )
        )
        scale = 1.0 + index / 10
        cells.append(
            CellComplete(
                cell_id=cell_id,
                fit_id=fit_id,
                distance=DistanceMeasure.CLASSIC_DELTA,
                status="complete",
                matrix=DistanceMatrix(
                    document_ids=DOCUMENT_IDS,
                    values=tuple(tuple(value * scale for value in row) for row in BASE_MATRIX),
                ),
            )
        )
    return WorkerResultV1(
        schema_version="stylo-worker-result-v1",
        request_id=_opaque("request", 1),
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        worker_version="stylo-worker-v1",
        outcome=AnalysisOutcome.PARTIAL if partial else AnalysisOutcome.COMPLETE,
        fitting_basis=FittingBasis(
            known_document_ids=DOCUMENT_IDS,
            ranked_features=(),
        ),
        fits=tuple(fits),
        cells=tuple(cells),
        session=_session(),
    )


def _view(*, partial: bool = False) -> ResultViewV1:
    return project_result_view(
        config=resolve_guided_workflow(
            purpose=PurposeId.TEXT_PROXIMITY,
            known_work_count=3,
            unknown_work_count=0,
        ),
        result=_result(partial=partial),
        source_result_sha256="a" * 64,
        documents=DESCRIPTORS,
    )


def _expect_error(code: P009ContractErrorCode, action: Callable[[], object]) -> None:
    with pytest.raises(P009ContractError) as captured:
        action()
    assert captured.value.code is code
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


def test_projection_retains_exact_guided_order_and_public_only_document_keys() -> None:
    config = resolve_guided_workflow(
        purpose=PurposeId.TEXT_PROXIMITY,
        known_work_count=3,
        unknown_work_count=0,
    )
    view = project_result_view(
        config=config,
        result=_result(),
        source_result_sha256="a" * 64,
        documents=DESCRIPTORS,
    )

    assert view.workflow_config_sha256 == workflow_config_sha256(config)
    assert view.source_result_sha256 == "a" * 64
    assert view.source_result_outcome == "complete"
    assert tuple(document.key for document in view.documents) == ("D01", "D02", "D03")
    assert tuple(document.title for document in view.documents) == (
        "Early work",
        "Middle work",
        "Late work",
    )
    assert tuple(cell.mfw for cell in view.cells) == (100, 300, 500, 1000)
    assert tuple(cell.status for cell in view.cells) == (ResultCellStatus.COMPLETE,) * 4
    assert tuple(cell.is_reference for cell in view.cells) == (False, False, True, False)
    assert view.cells[2].matrix is not None
    assert view.cells[2].matrix.document_keys == ("D01", "D02", "D03")


def test_partial_projection_preserves_unavailable_cell_without_substitution() -> None:
    view = _view(partial=True)

    assert view.source_result_outcome == "partial"
    assert view.cells[3].status is ResultCellStatus.NOT_ENOUGH_FEATURES
    assert view.cells[3].error_code == "not_enough_features"
    assert view.cells[3].matrix is None
    assert all(cell.matrix is not None for cell in view.cells[:3])


def test_projection_rejects_document_and_cell_binding_drift() -> None:
    config = resolve_guided_workflow(
        purpose=PurposeId.TEXT_PROXIMITY,
        known_work_count=3,
        unknown_work_count=0,
    )
    altered_documents = (
        DESCRIPTORS[0],
        DESCRIPTORS[1],
        ResultDocumentDescriptor(
            document_id=_opaque("doc", 99),
            title="Other",
            role=DocumentRole.KNOWN,
        ),
    )
    _expect_error(
        P009ContractErrorCode.BINDING_MISMATCH,
        lambda: project_result_view(
            config=config,
            result=_result(),
            source_result_sha256="a" * 64,
            documents=altered_documents,
        ),
    )

    reversed_cells = _result().model_copy(update={"cells": tuple(reversed(_result().cells))})
    _expect_error(
        P009ContractErrorCode.BINDING_MISMATCH,
        lambda: project_result_view(
            config=config,
            result=reversed_cells,
            source_result_sha256="a" * 64,
            documents=DESCRIPTORS,
        ),
    )


def test_canonical_round_trip_is_deterministic_and_excludes_private_material() -> None:
    view = _view(partial=True)
    payload = canonical_result_view(view)

    assert parse_result_view(payload) == view
    assert canonical_result_view(parse_result_view(payload)) == payload
    assert result_view_sha256(view) == hashlib.sha256(payload).hexdigest()
    assert payload.endswith(b"\n")
    for forbidden in (
        b"selected_features",
        b"ranked_features",
        b"means",
        b"standard_deviations",
        b"token",
        b"capability",
        b"workspace",
        DOCUMENT_IDS[0].encode(),
    ):
        assert forbidden not in payload


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (None, P009ContractErrorCode.PAYLOAD_TYPE),
        (b"", P009ContractErrorCode.PAYLOAD_EMPTY),
        (b"\xff", P009ContractErrorCode.INVALID_UTF8),
        (b"{", P009ContractErrorCode.INVALID_JSON),
        (b'{"schema_version":"x","schema_version":"y"}', P009ContractErrorCode.DUPLICATE_KEY),
        (b'{"value":NaN}', P009ContractErrorCode.NON_FINITE_NUMBER),
        (b'{"value":1e999}', P009ContractErrorCode.NUMBER_OUT_OF_RANGE),
        (b'{"value":"\\ud800"}', P009ContractErrorCode.INVALID_UNICODE),
        (b'{"unexpected":true}', P009ContractErrorCode.SCHEMA_INVALID),
    ],
)
def test_parser_rejects_hostile_or_malformed_payloads(
    payload: Any,
    code: P009ContractErrorCode,
) -> None:
    _expect_error(code, lambda: parse_result_view(payload))


def test_parser_rejects_oversized_and_finite_domain_overflowing_payloads() -> None:
    _expect_error(
        P009ContractErrorCode.PAYLOAD_TOO_LARGE,
        lambda: parse_result_view(b" " * (MAX_RESULT_VIEW_BYTES + 1)),
    )
    _expect_error(
        P009ContractErrorCode.NUMBER_OUT_OF_RANGE,
        lambda: parse_result_view(('{"value":' + "9" * 400 + "}").encode()),
    )


def test_nearest_neighbours_preserve_ties_within_structural_tolerance() -> None:
    cell = _view().cells[0]
    rows = nearest_neighbours(cell)

    assert tuple((row.document_key, row.neighbour_key) for row in rows) == (
        ("D01", "D02"),
        ("D01", "D03"),
        ("D02", "D01"),
        ("D03", "D01"),
    )
    assert tuple(row.tie_count for row in rows) == (2, 2, 1, 1)
    assert tuple(row.distance for row in rows) == (1.0, 1.0, 1.0, 1.0)

    matrix = cell.matrix
    assert matrix is not None
    near_tie = matrix.model_copy(
        update={
            "values": (
                (0.0, 1.0, 1.0 + 5e-13),
                (1.0, 0.0, 1.5),
                (1.0 + 5e-13, 1.5, 0.0),
            )
        }
    )
    tolerance_rows = nearest_neighbours(cell.model_copy(update={"matrix": near_tie}))
    assert tuple(row.neighbour_key for row in tolerance_rows if row.document_key == "D01") == (
        "D02",
        "D03",
    )
    assert tuple(row.tie_count for row in tolerance_rows if row.document_key == "D01") == (2, 2)


def test_classical_mds_is_deterministic_centered_and_recovers_three_point_distances() -> None:
    cell = _view().cells[0]
    first = classical_mds(cell)
    second = classical_mds(cell)

    assert first == second
    assert math.isclose(sum(point.x for point in first), 0.0, abs_tol=1e-12)
    assert math.isclose(sum(point.y for point in first), 0.0, abs_tol=1e-12)
    for left in range(3):
        for right in range(3):
            observed = math.hypot(
                first[left].x - first[right].x,
                first[left].y - first[right].y,
            )
            assert math.isclose(observed, BASE_MATRIX[left][right], abs_tol=1e-12)


def test_matrix_derivations_require_a_complete_cell() -> None:
    unavailable = _view(partial=True).cells[3]
    _expect_error(
        P009ContractErrorCode.INVALID_REQUEST,
        lambda: nearest_neighbours(unavailable),
    )
    _expect_error(P009ContractErrorCode.INVALID_REQUEST, lambda: classical_mds(unavailable))
    _expect_error(
        P009ContractErrorCode.INVALID_REQUEST,
        lambda: canonical_result_view(object()),  # type: ignore[arg-type]
    )


def test_closed_model_rejects_cell_and_scope_mutations() -> None:
    payload = _view().model_dump(mode="json")
    payload["source_result_outcome"] = "partial"
    with pytest.raises(ValidationError):
        ResultViewV1.model_validate(payload)

    payload = _view().model_dump(mode="json")
    payload["analysis_scope"] = "unknown_holdout"
    with pytest.raises(ValidationError):
        ResultViewV1.model_validate(payload)


def test_checked_in_schema_matches_the_closed_model() -> None:
    expected = export_p009_schema(
        ResultViewV1,
        "https://delta.lemmata.app/schemas/result-view-v1.schema.json",
    )
    assert json.loads(SCHEMA.read_text(encoding="utf-8")) == expected


def test_result_model_rejects_non_finite_matrix_values() -> None:
    payload = _view().model_dump(mode="json")
    payload["cells"][0]["matrix"]["values"][0][1] = math.inf
    with pytest.raises(ValidationError):
        ResultViewV1.model_validate(payload)


@pytest.mark.parametrize(
    "mutation",
    [
        "unsafe-title",
        "non-row-values",
        "duplicate-keys",
        "row-count",
        "non-square",
        "negative",
        "diagonal",
        "asymmetric",
        "complete-with-error",
        "failed-with-matrix",
        "wrong-reference",
        "non-sequential-documents",
        "cell-order",
        "culling",
        "matrix-order",
    ],
)
def test_closed_result_view_rejects_structural_drift(mutation: str) -> None:
    payload = _view().model_dump(mode="json")
    matrix = payload["cells"][0]["matrix"]
    if mutation == "unsafe-title":
        payload["documents"][0]["title"] = " Early work"
    elif mutation == "non-row-values":
        matrix["values"] = "not-a-matrix"
    elif mutation == "duplicate-keys":
        matrix["document_keys"] = ("D01", "D01", "D03")
    elif mutation == "row-count":
        matrix["values"] = matrix["values"][:-1]
    elif mutation == "non-square":
        matrix["values"][0] = matrix["values"][0][:-1]
    elif mutation == "negative":
        matrix["values"][0][1] = -1.0
        matrix["values"][1][0] = -1.0
    elif mutation == "diagonal":
        matrix["values"][0][0] = 1.0
    elif mutation == "asymmetric":
        matrix["values"][0][1] = 2.0
    elif mutation == "complete-with-error":
        payload["cells"][0]["error_code"] = "fit_unavailable"
    elif mutation == "failed-with-matrix":
        payload["cells"][0]["status"] = "failed"
        payload["cells"][0]["error_code"] = "fit_unavailable"
    elif mutation == "wrong-reference":
        payload["cells"][2]["is_reference"] = False
    elif mutation == "non-sequential-documents":
        payload["documents"][0]["key"] = "D02"
    elif mutation == "cell-order":
        payload["cells"][0], payload["cells"][1] = (
            payload["cells"][1],
            payload["cells"][0],
        )
    elif mutation == "culling":
        payload["cells"][0]["culling_percent"] = 10
    elif mutation == "matrix-order":
        matrix["document_keys"] = tuple(reversed(matrix["document_keys"]))
    with pytest.raises(ValidationError):
        ResultViewV1.model_validate(payload)


def test_view_level_redundant_invariants_fail_closed() -> None:
    view = _view()
    no_reference = view.model_copy(
        update={
            "cells": tuple(cell.model_copy(update={"is_reference": False}) for cell in view.cells)
        }
    )
    with pytest.raises(ValueError, match="one fixed reference"):
        no_reference.require_closed_guided_view()

    no_complete = view.model_copy(
        update={
            "source_result_outcome": "partial",
            "cells": tuple(
                cell.model_copy(
                    update={
                        "status": ResultCellStatus.FAILED,
                        "matrix": None,
                        "error_code": "fit_unavailable",
                    }
                )
                for cell in view.cells
            ),
        }
    )
    with pytest.raises(ValueError, match="visible cell completeness"):
        no_complete.require_closed_guided_view()


def test_projection_rejects_invalid_types_outcomes_descriptors_and_cell_counts() -> None:
    config = resolve_guided_workflow(
        purpose=PurposeId.TEXT_PROXIMITY,
        known_work_count=3,
        unknown_work_count=0,
    )
    _expect_error(
        P009ContractErrorCode.INVALID_REQUEST,
        lambda: project_result_view(
            config=object(),  # type: ignore[arg-type]
            result=_result(),
            source_result_sha256="a" * 64,
            documents=DESCRIPTORS,
        ),
    )
    failed = _result().model_copy(update={"outcome": AnalysisOutcome.FAILED})
    _expect_error(
        P009ContractErrorCode.BINDING_MISMATCH,
        lambda: project_result_view(
            config=config,
            result=failed,
            source_result_sha256="a" * 64,
            documents=DESCRIPTORS,
        ),
    )
    invalid_descriptors = (DESCRIPTORS[0], DESCRIPTORS[1], object())
    _expect_error(
        P009ContractErrorCode.BINDING_MISMATCH,
        lambda: project_result_view(
            config=config,
            result=_result(),
            source_result_sha256="a" * 64,
            documents=invalid_descriptors,  # type: ignore[arg-type]
        ),
    )
    unsafe_title = (
        DESCRIPTORS[0],
        DESCRIPTORS[1],
        ResultDocumentDescriptor(
            document_id=DESCRIPTORS[2].document_id,
            title=" Late work",
            role=DocumentRole.KNOWN,
        ),
    )
    _expect_error(
        P009ContractErrorCode.BINDING_MISMATCH,
        lambda: project_result_view(
            config=config,
            result=_result(),
            source_result_sha256="a" * 64,
            documents=unsafe_title,
        ),
    )
    short_result = _result().model_copy(update={"cells": _result().cells[:-1]})
    _expect_error(
        P009ContractErrorCode.BINDING_MISMATCH,
        lambda: project_result_view(
            config=config,
            result=short_result,
            source_result_sha256="a" * 64,
            documents=DESCRIPTORS,
        ),
    )


def test_projection_maps_public_failure_and_rejects_matrix_document_order() -> None:
    config = resolve_guided_workflow(
        purpose=PurposeId.TEXT_PROXIMITY,
        known_work_count=3,
        unknown_work_count=0,
    )
    base = _result()
    failed_cell = CellFailed(
        cell_id=base.cells[-1].cell_id,
        fit_id=base.cells[-1].fit_id,
        distance=DistanceMeasure.CLASSIC_DELTA,
        status="failed",
        error_code=CellErrorCode.FIT_UNAVAILABLE,
    )
    partial = base.model_copy(
        update={"outcome": AnalysisOutcome.PARTIAL, "cells": (*base.cells[:-1], failed_cell)}
    )
    view = project_result_view(
        config=config,
        result=partial,
        source_result_sha256="a" * 64,
        documents=DESCRIPTORS,
    )
    assert view.cells[-1].status is ResultCellStatus.FAILED
    assert view.cells[-1].error_code == "fit_unavailable"

    complete = base.cells[0]
    assert isinstance(complete, CellComplete)
    reversed_matrix = complete.matrix.model_copy(
        update={"document_ids": tuple(reversed(complete.matrix.document_ids))}
    )
    drifted = base.model_copy(
        update={
            "cells": (
                complete.model_copy(update={"matrix": reversed_matrix}),
                *base.cells[1:],
            )
        }
    )
    _expect_error(
        P009ContractErrorCode.BINDING_MISMATCH,
        lambda: project_result_view(
            config=config,
            result=drifted,
            source_result_sha256="a" * 64,
            documents=DESCRIPTORS,
        ),
    )


def test_classical_mds_handles_one_axis_and_zero_distance_geometry() -> None:
    view = _view()
    payload = view.model_dump(mode="python")
    payload["documents"] = payload["documents"][:2]
    for cell in payload["cells"]:
        cell["matrix"]["document_keys"] = ("D01", "D02")
        cell["matrix"]["values"] = ((0.0, 1.0), (1.0, 0.0))
    two_point = ResultViewV1.model_validate(payload)
    points = classical_mds(two_point.cells[0])
    assert len(points) == 2
    assert all(point.y == 0.0 for point in points)

    zero_payload = two_point.model_dump(mode="python")
    for cell in zero_payload["cells"]:
        cell["matrix"]["values"] = ((0.0, 0.0), (0.0, 0.0))
    zero_view = ResultViewV1.model_validate(zero_payload)
    assert {(point.x, point.y) for point in classical_mds(zero_view.cells[0])} == {(0.0, 0.0)}
