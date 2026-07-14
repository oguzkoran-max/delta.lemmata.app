from __future__ import annotations

import copy
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError

import delta_lemmata.stylo_contracts as contracts
from delta_lemmata.stylo_contracts import (
    AnalysisOutcome,
    CellComplete,
    CellErrorCode,
    CellFailed,
    CellNotEnoughFeatures,
    CellRequest,
    DirectStyloOracleV1,
    DistanceMatrix,
    DistanceMeasure,
    DocumentCounts,
    DocumentRole,
    FatalErrorCode,
    FatalStage,
    FitComplete,
    FitErrorCode,
    FitFailed,
    FitNotEnoughFeatures,
    FitRequest,
    FittingBasis,
    RankedFeature,
    RSessionInfoV1,
    StyloContractError,
    StyloContractErrorCode,
    WorkerFatalErrorV1,
    WorkerInputV1,
    WorkerResultV1,
    canonical_worker_json,
    export_stylo_schema,
    parse_direct_stylo_oracle,
    parse_worker_fatal_error,
    parse_worker_input,
    parse_worker_result,
    validate_direct_stylo_oracle,
    validate_worker_fatal_error,
    validate_worker_result,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


def opaque(prefix: str, number: int) -> str:
    return f"{prefix}_{number:064x}"


def request_fixture() -> WorkerInputV1:
    rows = (
        (DocumentRole.KNOWN, (4, 3, 2, 1)),
        (DocumentRole.KNOWN, (1, 4, 3, 2)),
        (DocumentRole.KNOWN, (2, 1, 4, 3)),
        (DocumentRole.UNKNOWN, (3, 2, 1, 4)),
    )
    documents = tuple(
        DocumentCounts(
            document_id=opaque("doc", index),
            asset_ref=opaque("asset", index),
            work_ref=opaque("work", index),
            role=role,
            token_total=10,
            counts=counts,
        )
        for index, (role, counts) in enumerate(rows, start=1)
    )
    first_fit = FitRequest(fit_id=opaque("fit", 1), mfw=2, culling_percent=0)
    short_fit = FitRequest(fit_id=opaque("fit", 2), mfw=5, culling_percent=0)
    return WorkerInputV1(
        schema_version="stylo-worker-input-v1",
        request_id=opaque("request", 1),
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        candidate_features=("alpha", "beta", "gamma", "delta"),
        documents=documents,
        fits=(first_fit, short_fit),
        cells=(
            CellRequest(
                cell_id=opaque("cell", 1),
                fit_id=first_fit.fit_id,
                distance=DistanceMeasure.CLASSIC_DELTA,
            ),
            CellRequest(
                cell_id=opaque("cell", 2),
                fit_id=first_fit.fit_id,
                distance=DistanceMeasure.COSINE_DELTA,
            ),
            CellRequest(
                cell_id=opaque("cell", 3),
                fit_id=short_fit.fit_id,
                distance=DistanceMeasure.CLASSIC_DELTA,
            ),
        ),
    )


def session_fixture() -> RSessionInfoV1:
    return RSessionInfoV1(
        r_version="4.5.2",
        stylo_version="0.7.71",
        jsonlite_version="2.0.0",
        platform="x86_64-pc-linux-gnu",
        operating_system="Ubuntu 24.04.2 LTS",
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
        blas="libopenblas.so.0",
        lapack="libopenblas.so.0",
    )


def matrix_fixture(request: WorkerInputV1, *, scale: float = 1.0) -> DistanceMatrix:
    return DistanceMatrix(
        document_ids=tuple(document.document_id for document in request.documents),
        values=(
            (0.0, 1.0 * scale, 2.0 * scale, 3.0 * scale),
            (1.0 * scale, 0.0, 1.5 * scale, 2.5 * scale),
            (2.0 * scale, 1.5 * scale, 0.0, 1.0 * scale),
            (3.0 * scale, 2.5 * scale, 1.0 * scale, 0.0),
        ),
    )


def result_fixture(request: WorkerInputV1) -> WorkerResultV1:
    known_ids = tuple(
        document.document_id
        for document in request.documents
        if document.role is DocumentRole.KNOWN
    )
    beta = (30.0, 40.0, 10.0)
    complete_fit = FitComplete(
        fit_id=request.fits[0].fit_id,
        mfw=2,
        culling_percent=0,
        status="complete",
        eligible_feature_count=4,
        selected_features=("gamma", "beta"),
        means=(30.0, sum(beta) / len(beta)),
        standard_deviations=(10.0, statistics.stdev(beta)),
    )
    short_fit = FitNotEnoughFeatures(
        fit_id=request.fits[1].fit_id,
        mfw=5,
        culling_percent=0,
        status="not_enough_features",
        eligible_feature_count=4,
    )
    return WorkerResultV1(
        schema_version="stylo-worker-result-v1",
        request_id=request.request_id,
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        worker_version="stylo-worker-v1",
        outcome=AnalysisOutcome.PARTIAL,
        fitting_basis=FittingBasis(
            known_document_ids=known_ids,
            ranked_features=(
                RankedFeature(feature="gamma", known_total_count=9, known_document_count=3),
                RankedFeature(feature="beta", known_total_count=8, known_document_count=3),
                RankedFeature(feature="alpha", known_total_count=7, known_document_count=3),
                RankedFeature(feature="delta", known_total_count=6, known_document_count=3),
            ),
        ),
        fits=(complete_fit, short_fit),
        cells=(
            CellComplete(
                cell_id=request.cells[0].cell_id,
                fit_id=request.cells[0].fit_id,
                distance=request.cells[0].distance,
                status="complete",
                matrix=matrix_fixture(request),
            ),
            CellComplete(
                cell_id=request.cells[1].cell_id,
                fit_id=request.cells[1].fit_id,
                distance=request.cells[1].distance,
                status="complete",
                matrix=matrix_fixture(request, scale=0.5),
            ),
            CellNotEnoughFeatures(
                cell_id=request.cells[2].cell_id,
                fit_id=request.cells[2].fit_id,
                distance=request.cells[2].distance,
                status="not_enough_features",
                error_code="not_enough_features",
            ),
        ),
        session=session_fixture(),
    )


def fatal_fixture(request: WorkerInputV1) -> WorkerFatalErrorV1:
    return WorkerFatalErrorV1(
        schema_version="stylo-worker-fatal-error-v1",
        request_id=request.request_id,
        worker_version="stylo-worker-v1",
        status="fatal_error",
        stage=FatalStage.ANALYSIS,
        error_code=FatalErrorCode.ANALYSIS_FAILED,
    )


def oracle_fixture(request: WorkerInputV1) -> DirectStyloOracleV1:
    result = result_fixture(request)
    return DirectStyloOracleV1(
        schema_version="direct-stylo-oracle-v1",
        fixture_ref=opaque("fixture", 1),
        input_sha256=hashlib.sha256(canonical_worker_json(request)).hexdigest(),
        request_id=result.request_id,
        limit_profile=result.limit_profile,
        analysis_unit=result.analysis_unit,
        seed=result.seed,
        oracle_version="p006-direct-stylo-v1",
        outcome=result.outcome,
        fitting_basis=result.fitting_basis,
        fits=result.fits,
        cells=result.cells,
        session=result.session,
    )


def expect_contract_error(
    code: StyloContractErrorCode,
    action: Any,
) -> StyloContractError:
    with pytest.raises(StyloContractError) as captured:
        assert callable(action)
        action()
    error = captured.value
    assert error.code is code
    assert str(error) == code.value
    assert error.__context__ is None
    assert error.__cause__ is None
    return error


def test_closed_contracts_round_trip_through_canonical_json_and_semantics() -> None:
    request = request_fixture()
    result = result_fixture(request)
    fatal = fatal_fixture(request)
    oracle = oracle_fixture(request)
    assert parse_worker_input(canonical_worker_json(request)) == request
    parsed_result = parse_worker_result(canonical_worker_json(result))
    assert validate_worker_result(request, parsed_result) == result
    parsed_oracle = parse_direct_stylo_oracle(canonical_worker_json(oracle))
    assert validate_direct_stylo_oracle(request, parsed_oracle) == oracle
    assert (
        validate_worker_fatal_error(
            request,
            parse_worker_fatal_error(canonical_worker_json(fatal)),
        )
        == fatal
    )
    assert canonical_worker_json(request).endswith(b"\n")


def test_direct_oracle_must_bind_exact_input_bytes_and_scientific_semantics() -> None:
    request = request_fixture()
    oracle = oracle_fixture(request)
    wrong_digest = oracle.model_copy(update={"input_sha256": "0" * 64})
    expect_contract_error(
        StyloContractErrorCode.SEMANTIC_INVALID,
        lambda: validate_direct_stylo_oracle(request, wrong_digest),
    )
    wrong_request = oracle.model_copy(update={"request_id": opaque("request", 99)})
    expect_contract_error(
        StyloContractErrorCode.SEMANTIC_INVALID,
        lambda: validate_direct_stylo_oracle(request, wrong_request),
    )


@pytest.mark.parametrize("field", ["fits", "cells"])
def test_direct_oracle_rejects_duplicate_result_identifiers(field: str) -> None:
    payload = oracle_fixture(request_fixture()).model_dump(mode="python")
    payload[field] = (payload[field][0], payload[field][0])
    with pytest.raises(ValidationError):
        DirectStyloOracleV1.model_validate(payload)


def test_mfw_one_is_rejected_before_stylo_execution() -> None:
    with pytest.raises(ValidationError):
        FitRequest(fit_id=opaque("fit", 99), mfw=1, culling_percent=0)


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (cast(Any, "not-bytes"), StyloContractErrorCode.PAYLOAD_TYPE),
        (b"", StyloContractErrorCode.PAYLOAD_EMPTY),
        (b"\xff", StyloContractErrorCode.INVALID_UTF8),
        (b'{"x":1}{"y":2}', StyloContractErrorCode.INVALID_JSON),
        (b'{"x":1,"x":2}', StyloContractErrorCode.DUPLICATE_KEY),
        (b'{"x":NaN}', StyloContractErrorCode.NON_FINITE_NUMBER),
        (b'{"x":1e9999}', StyloContractErrorCode.NON_FINITE_NUMBER),
        (
            b'{"x":' + str(10**400).encode() + b"}",
            StyloContractErrorCode.NUMBER_OUT_OF_RANGE,
        ),
        (b'{"x":"\\ud800"}', StyloContractErrorCode.INVALID_UNICODE),
        (b'{"unexpected":true}', StyloContractErrorCode.SCHEMA_INVALID),
    ],
)
def test_strict_parser_rejects_lexical_and_schema_failures(
    payload: bytes,
    code: StyloContractErrorCode,
) -> None:
    expect_contract_error(code, lambda: parse_worker_input(payload))


def test_strict_parser_rejects_bounded_and_recursive_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = canonical_worker_json(request_fixture())
    monkeypatch.setattr(contracts, "INPUT_MAX_BYTES", len(valid) - 1)
    expect_contract_error(
        StyloContractErrorCode.PAYLOAD_TOO_LARGE,
        lambda: canonical_worker_json(request_fixture()),
    )
    expect_contract_error(
        StyloContractErrorCode.PAYLOAD_TOO_LARGE,
        lambda: parse_worker_input(valid),
    )
    monkeypatch.setattr(
        json,
        "loads",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RecursionError),
    )
    expect_contract_error(
        StyloContractErrorCode.INVALID_JSON,
        lambda: parse_worker_input(b"{}"),
    )


def test_single_parse_path_keeps_scalar_types_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_loads = json.loads
    calls = 0

    def counted_loads(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        return real_loads(*args, **kwargs)

    monkeypatch.setattr(contracts.json, "loads", counted_loads)
    assert parse_worker_input(canonical_worker_json(request_fixture())) == request_fixture()
    assert calls == 1

    payload = json.loads(canonical_worker_json(request_fixture()))
    payload["documents"][0]["counts"][0] = "4"
    encoded = json.dumps(payload, separators=(",", ":")).encode()

    expect_contract_error(
        StyloContractErrorCode.SCHEMA_INVALID,
        lambda: parse_worker_input(encoded),
    )


def test_limit_profile_is_composable_with_transport_byte_caps() -> None:
    assert contracts.MAX_FITS * 3 == contracts.MAX_CELLS
    assert contracts.INPUT_WIRE_UPPER_BOUND < contracts.INPUT_MAX_BYTES
    assert contracts.RESULT_WIRE_UPPER_BOUND < contracts.RESULT_MAX_BYTES


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data.update(candidate_features=("alpha", "alpha", "gamma", "delta")),
        lambda data: data.update(candidate_features=("a\u0301", "beta", "gamma", "delta")),
        lambda data: data.update(candidate_features=("bad\n", "beta", "gamma", "delta")),
        lambda data: data.update(candidate_features=("é" * 40, "beta", "gamma", "delta")),
        lambda data: data["documents"][0].update(token_total=1),
        lambda data: data["documents"][0].update(counts=(1, 2)),
        lambda data: (
            data["documents"][0].update(role=DocumentRole.UNKNOWN),
            data["documents"][1].update(role=DocumentRole.UNKNOWN),
        ),
        lambda data: data["documents"][1].update(document_id=data["documents"][0]["document_id"]),
        lambda data: data["documents"][1].update(asset_ref=data["documents"][0]["asset_ref"]),
        lambda data: data["documents"][1].update(work_ref=data["documents"][0]["work_ref"]),
        lambda data: data["fits"][1].update(fit_id=data["fits"][0]["fit_id"]),
        lambda data: data["fits"][1].update(mfw=2),
        lambda data: data["cells"][1].update(cell_id=data["cells"][0]["cell_id"]),
        lambda data: data["cells"][1].update(distance="classic_delta"),
        lambda data: data["cells"][2].update(fit_id=opaque("fit", 99)),
        lambda data: data.update(cells=tuple(data["cells"][:2])),
    ],
)
def test_input_model_rejects_scientifically_ambiguous_graphs(mutation: Any) -> None:
    payload = request_fixture().model_dump(mode="python")
    assert callable(mutation)
    mutation(payload)
    with pytest.raises(ValidationError):
        WorkerInputV1.model_validate(payload)


def test_result_local_models_reject_malformed_vectors_and_graphs() -> None:
    request = request_fixture()
    result = result_fixture(request)
    payload = result.model_dump(mode="python")
    payload["fitting_basis"]["known_document_ids"] = (
        result.fitting_basis.known_document_ids[0],
        result.fitting_basis.known_document_ids[0],
    )
    with pytest.raises(ValidationError):
        WorkerResultV1.model_validate(payload)

    payload = result.model_dump(mode="python")
    payload["fitting_basis"]["ranked_features"] = (
        result.fitting_basis.ranked_features[0],
        result.fitting_basis.ranked_features[0],
    )
    with pytest.raises(ValidationError):
        WorkerResultV1.model_validate(payload)

    for field, value in (
        ("selected_features", ("gamma",)),
        ("means", (30.0,)),
        ("standard_deviations", (10.0,)),
        ("eligible_feature_count", 1),
        ("standard_deviations", (10.0, 0.0)),
    ):
        payload = result.fits[0].model_dump(mode="python")
        payload[field] = value
        with pytest.raises(ValidationError):
            FitComplete.model_validate(payload)

    with pytest.raises(ValidationError):
        FitNotEnoughFeatures(
            fit_id=request.fits[0].fit_id,
            mfw=2,
            culling_percent=0,
            status="not_enough_features",
            eligible_feature_count=2,
        )
    with pytest.raises(ValidationError):
        DistanceMatrix(
            document_ids=(opaque("doc", 1), opaque("doc", 1)),
            values=((0.0, 1.0), (1.0, 0.0)),
        )
    with pytest.raises(ValidationError):
        DistanceMatrix(
            document_ids=(opaque("doc", 1), opaque("doc", 2)),
            values=((0.0,), (1.0, 0.0)),
        )

    with pytest.raises(ValidationError):
        RankedFeature(feature="a\u0301", known_total_count=1, known_document_count=1)

    payload = result.model_dump(mode="python")
    payload["fits"] = (payload["fits"][0], payload["fits"][0])
    with pytest.raises(ValidationError):
        WorkerResultV1.model_validate(payload)

    payload = result.model_dump(mode="python")
    payload["cells"] = (payload["cells"][0], payload["cells"][0], payload["cells"][2])
    with pytest.raises(ValidationError):
        WorkerResultV1.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("means", "not-a-sequence"),
        ("means", (True, 1.0)),
        ("means", ("1", 1.0)),
        ("means", (float("inf"), 1.0)),
        ("means", (10**400, 1.0)),
    ],
)
def test_fit_numeric_vectors_accept_only_finite_json_numbers(field: str, value: Any) -> None:
    payload = result_fixture(request_fixture()).fits[0].model_dump(mode="python")
    payload[field] = value
    with pytest.raises(ValidationError):
        FitComplete.model_validate(payload)


def test_matrix_numeric_rows_accept_only_finite_sequences() -> None:
    ids = (opaque("doc", 1), opaque("doc", 2))
    for values in ("not-a-matrix", ("not-a-row", "not-a-row"), ((0.0, True), (1.0, 0.0))):
        with pytest.raises(ValidationError):
            DistanceMatrix(document_ids=ids, values=values)  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        DistanceMatrix(document_ids=ids, values=((0.0, 10**400), (1.0, 0.0)))


def test_finite_delta_above_one_trillion_remains_contract_valid() -> None:
    known_frequencies = (100.0 / 3_000_000, 100.0 / 2_999_999)
    mean = statistics.mean(known_frequencies)
    deviation = statistics.stdev(known_frequencies)
    reachable_distance = abs((50.0 - mean) / deviation)
    ids = (opaque("doc", 1), opaque("doc", 2))

    assert reachable_distance > 1_000_000_000_000.0
    matrix = DistanceMatrix(
        document_ids=ids,
        values=((0.0, reachable_distance), (reachable_distance, 0.0)),
    )
    assert matrix.values[0][1] == reachable_distance


def test_fatal_contract_is_closed_content_free_and_stage_specific() -> None:
    request = request_fixture()
    payload = fatal_fixture(request).model_dump(mode="python")
    payload["error_code"] = FatalErrorCode.RESULT_WRITE_FAILED
    with pytest.raises(ValidationError):
        WorkerFatalErrorV1.model_validate(payload)
    payload = fatal_fixture(request).model_dump(mode="python")
    payload["request_id"] = None
    with pytest.raises(ValidationError):
        WorkerFatalErrorV1.model_validate(payload)
    preparse = WorkerFatalErrorV1(
        schema_version="stylo-worker-fatal-error-v1",
        request_id=None,
        worker_version="stylo-worker-v1",
        status="fatal_error",
        stage=FatalStage.INPUT_PARSE,
        error_code=FatalErrorCode.INPUT_INVALID_JSON,
    )
    assert preparse.request_id is None


def test_semantic_validator_accepts_complete_partial_and_failed_outcomes() -> None:
    request = request_fixture()
    partial = result_fixture(request)
    assert validate_worker_result(request, partial).outcome is AnalysisOutcome.PARTIAL

    complete_request = request.model_copy(
        update={"fits": (request.fits[0],), "cells": request.cells[:2]}
    )
    complete = partial.model_copy(
        update={
            "outcome": AnalysisOutcome.COMPLETE,
            "fits": partial.fits[:1],
            "cells": partial.cells[:2],
        }
    )
    assert validate_worker_result(complete_request, complete).outcome is AnalysisOutcome.COMPLETE

    failed_fit = FitFailed(
        fit_id=request.fits[0].fit_id,
        mfw=2,
        culling_percent=0,
        status="failed",
        eligible_feature_count=4,
        error_code=FitErrorCode.CALCULATION_FAILED,
    )
    failed = complete.model_copy(
        update={
            "outcome": AnalysisOutcome.FAILED,
            "fits": (failed_fit,),
            "cells": tuple(
                CellFailed(
                    cell_id=cell.cell_id,
                    fit_id=cell.fit_id,
                    distance=cell.distance,
                    status="failed",
                    error_code=CellErrorCode.FIT_UNAVAILABLE,
                )
                for cell in complete_request.cells
            ),
        }
    )
    assert validate_worker_result(complete_request, failed).outcome is AnalysisOutcome.FAILED


@pytest.mark.parametrize(
    "mutation",
    [
        lambda request, result: object.__setattr__(result, "request_id", opaque("request", 9)),
        lambda request, result: object.__setattr__(
            result.fitting_basis,
            "known_document_ids",
            tuple(reversed(result.fitting_basis.known_document_ids)),
        ),
        lambda request, result: object.__setattr__(
            result.fitting_basis,
            "ranked_features",
            tuple(reversed(result.fitting_basis.ranked_features)),
        ),
        lambda request, result: object.__setattr__(result, "fits", result.fits[:1]),
        lambda request, result: object.__setattr__(result, "cells", result.cells[:2]),
        lambda request, result: object.__setattr__(result.fits[0], "mfw", 3),
        lambda request, result: object.__setattr__(result.fits[0], "eligible_feature_count", 3),
        lambda request, result: object.__setattr__(
            result.fits[0], "selected_features", ("beta", "gamma")
        ),
        lambda request, result: object.__setattr__(result.fits[0], "means", (31.0, 20.0)),
        lambda request, result: object.__setattr__(
            result.fits[0], "standard_deviations", (11.0, 12.0)
        ),
        lambda request, result: object.__setattr__(result.cells[0], "cell_id", opaque("cell", 99)),
        lambda request, result: object.__setattr__(result, "outcome", AnalysisOutcome.COMPLETE),
    ],
)
def test_semantic_validator_rejects_cross_contract_mismatches(mutation: Any) -> None:
    request = request_fixture()
    result = result_fixture(request).model_copy(deep=True)
    assert callable(mutation)
    mutation(request, result)
    expect_contract_error(
        StyloContractErrorCode.SEMANTIC_INVALID,
        lambda: validate_worker_result(request, result),
    )


@pytest.mark.parametrize(
    "values",
    [
        (
            (0.0, -1.0, 2.0, 3.0),
            (-1.0, 0.0, 1.5, 2.5),
            (2.0, 1.5, 0.0, 1.0),
            (3.0, 2.5, 1.0, 0.0),
        ),
        (
            (1e-6, 1.0, 2.0, 3.0),
            (1.0, 0.0, 1.5, 2.5),
            (2.0, 1.5, 0.0, 1.0),
            (3.0, 2.5, 1.0, 0.0),
        ),
        (
            (0.0, 1.1, 2.0, 3.0),
            (1.0, 0.0, 1.5, 2.5),
            (2.0, 1.5, 0.0, 1.0),
            (3.0, 2.5, 1.0, 0.0),
        ),
    ],
)
def test_semantic_validator_rejects_negative_diagonal_and_asymmetric_matrices(
    values: tuple[tuple[float, ...], ...],
) -> None:
    request = request_fixture()
    result = result_fixture(request)
    bad = DistanceMatrix(document_ids=result.cells[0].matrix.document_ids, values=values)  # type: ignore[union-attr]
    object.__setattr__(result.cells[0], "matrix", bad)
    expect_contract_error(
        StyloContractErrorCode.SEMANTIC_INVALID,
        lambda: validate_worker_result(request, result),
    )


def test_semantic_validator_rejects_matrix_labels_and_missing_fit_reference() -> None:
    request = request_fixture()
    result = result_fixture(request)
    complete = cast(CellComplete, result.cells[0])
    wrong_labels = complete.matrix.model_copy(
        update={"document_ids": tuple(reversed(complete.matrix.document_ids))}
    )
    object.__setattr__(complete, "matrix", wrong_labels)
    expect_contract_error(
        StyloContractErrorCode.SEMANTIC_INVALID,
        lambda: validate_worker_result(request, result),
    )

    result = result_fixture(request)
    complete = cast(CellComplete, result.cells[0])
    object.__setattr__(
        complete.matrix,
        "values",
        (complete.matrix.values[0][:-1], *complete.matrix.values[1:]),
    )
    expect_contract_error(
        StyloContractErrorCode.SEMANTIC_INVALID,
        lambda: validate_worker_result(request, result),
    )

    result = result_fixture(request)
    object.__setattr__(result.cells[0], "fit_id", opaque("fit", 99))
    expect_contract_error(
        StyloContractErrorCode.SEMANTIC_INVALID,
        lambda: validate_worker_result(request, result),
    )


def test_semantic_validator_requires_fit_and_cell_failure_alignment() -> None:
    request = request_fixture()
    result = result_fixture(request)
    object.__setattr__(
        result,
        "fits",
        (
            result.fits[0],
            FitFailed(
                fit_id=request.fits[1].fit_id,
                mfw=5,
                culling_percent=0,
                status="failed",
                eligible_feature_count=4,
                error_code=FitErrorCode.CALCULATION_FAILED,
            ),
        ),
    )
    expect_contract_error(
        StyloContractErrorCode.SEMANTIC_INVALID,
        lambda: validate_worker_result(request, result),
    )

    result = result_fixture(request)
    object.__setattr__(
        result,
        "cells",
        (
            *result.cells[:2],
            CellFailed(
                cell_id=request.cells[2].cell_id,
                fit_id=request.cells[2].fit_id,
                distance=request.cells[2].distance,
                status="failed",
                error_code=CellErrorCode.FIT_UNAVAILABLE,
            ),
        ),
    )
    expect_contract_error(
        StyloContractErrorCode.SEMANTIC_INVALID,
        lambda: validate_worker_result(request, result),
    )


def test_zero_variance_is_an_explicit_failed_fit_not_a_nonfinite_success() -> None:
    request = request_fixture()
    payload = request.model_dump(mode="python")
    for document in payload["documents"][:3]:
        document["counts"] = (2, 3, 4, 1)
    constant_request = WorkerInputV1.model_validate(payload)
    base = result_fixture(constant_request)
    failed_fits = (
        FitFailed(
            fit_id=constant_request.fits[0].fit_id,
            mfw=constant_request.fits[0].mfw,
            culling_percent=constant_request.fits[0].culling_percent,
            status="failed",
            eligible_feature_count=4,
            error_code=FitErrorCode.NON_POSITIVE_STANDARD_DEVIATION,
        ),
        FitNotEnoughFeatures(
            fit_id=constant_request.fits[1].fit_id,
            mfw=constant_request.fits[1].mfw,
            culling_percent=constant_request.fits[1].culling_percent,
            status="not_enough_features",
            eligible_feature_count=4,
        ),
    )
    failed_cells = (
        *tuple(
            CellFailed(
                cell_id=cell.cell_id,
                fit_id=cell.fit_id,
                distance=cell.distance,
                status="failed",
                error_code=CellErrorCode.FIT_UNAVAILABLE,
            )
            for cell in constant_request.cells[:2]
        ),
        CellNotEnoughFeatures(
            cell_id=constant_request.cells[2].cell_id,
            fit_id=constant_request.cells[2].fit_id,
            distance=constant_request.cells[2].distance,
            status="not_enough_features",
            error_code="not_enough_features",
        ),
    )
    fitting_basis = FittingBasis(
        known_document_ids=base.fitting_basis.known_document_ids,
        ranked_features=(
            RankedFeature(feature="gamma", known_total_count=12, known_document_count=3),
            RankedFeature(feature="beta", known_total_count=9, known_document_count=3),
            RankedFeature(feature="alpha", known_total_count=6, known_document_count=3),
            RankedFeature(feature="delta", known_total_count=3, known_document_count=3),
        ),
    )
    failed = base.model_copy(
        update={
            "outcome": AnalysisOutcome.FAILED,
            "fitting_basis": fitting_basis,
            "fits": failed_fits,
            "cells": failed_cells,
        }
    )
    assert validate_worker_result(constant_request, failed).outcome is AnalysisOutcome.FAILED


def test_known_zero_total_feature_is_excluded_from_the_fitting_basis() -> None:
    request = request_fixture()
    payload = request.model_dump(mode="python")
    payload["candidate_features"] = (*payload["candidate_features"], "unknown_only")
    for document in payload["documents"][:3]:
        document["counts"] = (*document["counts"], 0)
    payload["documents"][3]["counts"] = (*payload["documents"][3]["counts"], 1)
    payload["documents"][3]["token_total"] += 1
    extended = WorkerInputV1.model_validate(payload)
    result = result_fixture(extended)
    assert validate_worker_result(extended, result).fitting_basis == result.fitting_basis


def test_zero_candidate_overlap_is_a_valid_projected_document() -> None:
    payload = request_fixture().model_dump(mode="python")
    payload["documents"][3]["counts"] = (0, 0, 0, 0)
    projected = WorkerInputV1.model_validate(payload)

    assert projected.documents[3].token_total == 10
    assert sum(projected.documents[3].counts) == 0


def test_aggregate_counts_exceed_one_document_limit_without_escaping_validation() -> None:
    documents = tuple(
        DocumentCounts(
            document_id=opaque("doc", index),
            asset_ref=opaque("asset", index),
            work_ref=opaque("work", index),
            role=DocumentRole.KNOWN,
            token_total=count,
            counts=(count, 0),
        )
        for index, count in enumerate((2_000_000, 1_999_999), start=1)
    )
    fit = FitRequest(fit_id=opaque("fit", 20), mfw=2, culling_percent=0)
    cell = CellRequest(
        cell_id=opaque("cell", 20),
        fit_id=fit.fit_id,
        distance=DistanceMeasure.CLASSIC_DELTA,
    )
    request = WorkerInputV1(
        schema_version="stylo-worker-input-v1",
        request_id=opaque("request", 20),
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        candidate_features=("alpha", "beta"),
        documents=documents,
        fits=(fit,),
        cells=(cell,),
    )
    ranked = contracts._ranked_features(request)
    means, deviations = contracts._fit_statistics(request, ("alpha",))
    result = WorkerResultV1(
        schema_version="stylo-worker-result-v1",
        request_id=request.request_id,
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        worker_version="stylo-worker-v1",
        outcome=AnalysisOutcome.FAILED,
        fitting_basis=FittingBasis(
            known_document_ids=tuple(document.document_id for document in documents),
            ranked_features=ranked,
        ),
        fits=(
            FitNotEnoughFeatures(
                fit_id=fit.fit_id,
                mfw=2,
                culling_percent=0,
                status="not_enough_features",
                eligible_feature_count=1,
            ),
        ),
        cells=(
            CellNotEnoughFeatures(
                cell_id=cell.cell_id,
                fit_id=fit.fit_id,
                distance=cell.distance,
                status="not_enough_features",
                error_code="not_enough_features",
            ),
        ),
        session=session_fixture(),
    )

    assert ranked[0].known_total_count == 3_999_999
    assert means == (100.0,)
    assert deviations == (0.0,)
    assert validate_worker_result(request, result) == result


def test_culling_boundary_and_fitting_ignore_unknown_only_counts() -> None:
    rows = (
        (DocumentRole.KNOWN, (3, 1, 0, 0)),
        (DocumentRole.KNOWN, (3, 1, 0, 0)),
        (DocumentRole.KNOWN, (3, 0, 1, 0)),
        (DocumentRole.KNOWN, (3, 0, 0, 0)),
        (DocumentRole.UNKNOWN, (0, 0, 0, 9)),
    )
    documents = tuple(
        DocumentCounts(
            document_id=opaque("doc", index + 30),
            asset_ref=opaque("asset", index + 30),
            work_ref=opaque("work", index + 30),
            role=role,
            token_total=20,
            counts=counts,
        )
        for index, (role, counts) in enumerate(rows)
    )
    fit = FitRequest(fit_id=opaque("fit", 30), mfw=2, culling_percent=50)
    request = WorkerInputV1(
        schema_version="stylo-worker-input-v1",
        request_id=opaque("request", 30),
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        candidate_features=("zeta", "equal", "below", "unknown_only"),
        documents=documents,
        fits=(fit,),
        cells=(
            CellRequest(
                cell_id=opaque("cell", 30),
                fit_id=fit.fit_id,
                distance=DistanceMeasure.CLASSIC_DELTA,
            ),
        ),
    )
    ranked = contracts._ranked_features(request)
    eligible = contracts._eligible_features(
        ranked,
        known_count=4,
        culling_percent=50,
    )
    fitting = contracts._fit_statistics(request, eligible)

    assert tuple(item.feature for item in ranked) == ("zeta", "equal", "below")
    assert eligible == ("zeta", "equal")

    changed_documents = list(request.documents)
    changed_documents[-1] = changed_documents[-1].model_copy(update={"counts": (9, 0, 0, 9)})
    changed = request.model_copy(update={"documents": tuple(changed_documents)})
    assert contracts._ranked_features(changed) == ranked
    assert contracts._fit_statistics(changed, eligible) == fitting


def test_relative_frequencies_use_token_total_not_candidate_sum() -> None:
    documents = tuple(
        DocumentCounts(
            document_id=opaque("doc", index + 40),
            asset_ref=opaque("asset", index + 40),
            work_ref=opaque("work", index + 40),
            role=DocumentRole.KNOWN,
            token_total=token_total,
            counts=counts,
        )
        for index, (token_total, counts) in enumerate(((100, (10, 20)), (200, (20, 10))))
    )
    fit = FitRequest(fit_id=opaque("fit", 40), mfw=2, culling_percent=0)
    request = WorkerInputV1(
        schema_version="stylo-worker-input-v1",
        request_id=opaque("request", 40),
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        candidate_features=("alpha", "beta"),
        documents=documents,
        fits=(fit,),
        cells=(
            CellRequest(
                cell_id=opaque("cell", 40),
                fit_id=fit.fit_id,
                distance=DistanceMeasure.CLASSIC_DELTA,
            ),
        ),
    )
    means, deviations = contracts._fit_statistics(request, ("beta",))

    assert means == pytest.approx((12.5,))
    assert deviations == pytest.approx((statistics.stdev((20.0, 5.0)),))


def test_equal_frequency_ranking_uses_locked_utf8_byte_order() -> None:
    documents = tuple(
        DocumentCounts(
            document_id=opaque("doc", index + 50),
            asset_ref=opaque("asset", index + 50),
            work_ref=opaque("work", index + 50),
            role=DocumentRole.KNOWN,
            token_total=4,
            counts=(1, 1),
        )
        for index in range(2)
    )
    fit = FitRequest(fit_id=opaque("fit", 50), mfw=2, culling_percent=0)
    request = WorkerInputV1(
        schema_version="stylo-worker-input-v1",
        request_id=opaque("request", 50),
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        candidate_features=("é", "z"),
        documents=documents,
        fits=(fit,),
        cells=(
            CellRequest(
                cell_id=opaque("cell", 50),
                fit_id=fit.fit_id,
                distance=DistanceMeasure.CLASSIC_DELTA,
            ),
        ),
    )

    assert tuple(item.feature for item in contracts._ranked_features(request)) == ("z", "é")


def test_valid_complete_fit_may_report_bounded_distance_failure() -> None:
    request = request_fixture()
    result = result_fixture(request)
    cells = list(result.cells)
    cells[0] = CellFailed(
        cell_id=request.cells[0].cell_id,
        fit_id=request.cells[0].fit_id,
        distance=request.cells[0].distance,
        status="failed",
        error_code=CellErrorCode.DISTANCE_CALCULATION_FAILED,
    )
    partial = result.model_copy(update={"cells": tuple(cells)})
    assert validate_worker_result(request, partial).outcome is AnalysisOutcome.PARTIAL


def test_fatal_semantics_require_the_exact_trusted_request() -> None:
    request = request_fixture()
    wrong = fatal_fixture(request).model_copy(update={"request_id": opaque("request", 9)})
    expect_contract_error(
        StyloContractErrorCode.SEMANTIC_INVALID,
        lambda: validate_worker_fatal_error(request, wrong),
    )


@pytest.mark.parametrize(
    ("filename", "model", "record"),
    [
        (
            "direct-stylo-oracle-v1.schema.json",
            DirectStyloOracleV1,
            lambda request: oracle_fixture(request),
        ),
        (
            "stylo-worker-input-v1.schema.json",
            WorkerInputV1,
            lambda request: request,
        ),
        (
            "stylo-worker-result-v1.schema.json",
            WorkerResultV1,
            lambda request: result_fixture(request),
        ),
        (
            "stylo-worker-fatal-error-v1.schema.json",
            WorkerFatalErrorV1,
            lambda request: fatal_fixture(request),
        ),
    ],
)
def test_checked_in_schemas_match_models_and_reject_extensions(
    filename: str,
    model: type[Any],
    record: Any,
) -> None:
    request = request_fixture()
    checked_in = json.loads((SCHEMAS / filename).read_text(encoding="utf-8"))
    assert checked_in == export_stylo_schema(
        model,
        f"https://delta.lemmata.app/schemas/{filename}",
    )
    validator = Draft202012Validator(checked_in)
    payload = record(request).model_dump(mode="json")
    validator.validate(payload)
    extended = copy.deepcopy(payload)
    extended["unexpected"] = True
    with pytest.raises(JsonSchemaValidationError):
        validator.validate(extended)
