from __future__ import annotations

from typing import Any, cast

import pytest

from delta_lemmata.job_models import TerminalOutcome
from delta_lemmata.process_controller import ProcessLimit, ProcessOutcome, ProcessResult
from delta_lemmata.scientific_finalizer import (
    ScientificFinalizationCode,
    ScientificFinalizerError,
    ScientificFinalizerErrorCode,
    finalize_scientific_execution,
)
from delta_lemmata.stylo_contracts import (
    AnalysisOutcome,
    CellComplete,
    CellErrorCode,
    CellFailed,
    CellRequest,
    DistanceMatrix,
    DistanceMeasure,
    DocumentCounts,
    DocumentRole,
    FatalErrorCode,
    FatalStage,
    FitComplete,
    FitErrorCode,
    FitFailed,
    FitRequest,
    FittingBasis,
    RankedFeature,
    RSessionInfoV1,
    WorkerFatalErrorV1,
    WorkerInputV1,
    WorkerResultV1,
    canonical_worker_json,
)


def opaque(prefix: str, number: int) -> str:
    return f"{prefix}_{number:064x}"


def request_fixture() -> WorkerInputV1:
    documents = tuple(
        DocumentCounts(
            document_id=opaque("doc", index),
            asset_ref=opaque("asset", index),
            work_ref=opaque("work", index),
            role=role,
            token_total=4,
            counts=counts,
        )
        for index, (role, counts) in enumerate(
            (
                (DocumentRole.KNOWN, (3, 1)),
                (DocumentRole.KNOWN, (1, 3)),
                (DocumentRole.UNKNOWN, (2, 2)),
            ),
            start=1,
        )
    )
    fit = FitRequest(fit_id=opaque("fit", 1), mfw=2, culling_percent=0)
    return WorkerInputV1(
        schema_version="stylo-worker-input-v1",
        request_id=opaque("request", 1),
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        candidate_features=("alpha", "beta"),
        documents=documents,
        fits=(fit,),
        cells=(
            CellRequest(
                cell_id=opaque("cell", 1),
                fit_id=fit.fit_id,
                distance=DistanceMeasure.CLASSIC_DELTA,
            ),
            CellRequest(
                cell_id=opaque("cell", 2),
                fit_id=fit.fit_id,
                distance=DistanceMeasure.COSINE_DELTA,
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


def matrix_fixture(request: WorkerInputV1, scale: float = 1.0) -> DistanceMatrix:
    return DistanceMatrix(
        document_ids=tuple(document.document_id for document in request.documents),
        values=(
            (0.0, 1.0 * scale, 2.0 * scale),
            (1.0 * scale, 0.0, 1.5 * scale),
            (2.0 * scale, 1.5 * scale, 0.0),
        ),
    )


def result_fixture(request: WorkerInputV1) -> WorkerResultV1:
    fit = FitComplete(
        fit_id=request.fits[0].fit_id,
        mfw=2,
        culling_percent=0,
        status="complete",
        eligible_feature_count=2,
        selected_features=("alpha", "beta"),
        means=(50.0, 50.0),
        standard_deviations=(35.35533905932738, 35.35533905932738),
    )
    return WorkerResultV1(
        schema_version="stylo-worker-result-v1",
        request_id=request.request_id,
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        worker_version="stylo-worker-v1",
        outcome=AnalysisOutcome.COMPLETE,
        fitting_basis=FittingBasis(
            known_document_ids=tuple(
                document.document_id
                for document in request.documents
                if document.role is DocumentRole.KNOWN
            ),
            ranked_features=(
                RankedFeature(feature="alpha", known_total_count=4, known_document_count=2),
                RankedFeature(feature="beta", known_total_count=4, known_document_count=2),
            ),
        ),
        fits=(fit,),
        cells=tuple(
            CellComplete(
                cell_id=cell.cell_id,
                fit_id=cell.fit_id,
                distance=cell.distance,
                status="complete",
                matrix=matrix_fixture(request, index + 1),
            )
            for index, cell in enumerate(request.cells)
        ),
        session=session_fixture(),
    )


def failed_result_fixture(request: WorkerInputV1) -> WorkerResultV1:
    complete = result_fixture(request)
    failed_fit = FitFailed(
        fit_id=request.fits[0].fit_id,
        mfw=2,
        culling_percent=0,
        status="failed",
        eligible_feature_count=2,
        error_code=FitErrorCode.CALCULATION_FAILED,
    )
    return complete.model_copy(
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
                for cell in request.cells
            ),
        }
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


def test_complete_and_partial_results_are_accepted_scientific_artifacts() -> None:
    request = request_fixture()
    complete_result = result_fixture(request)
    complete = finalize_scientific_execution(
        process=ProcessResult(ProcessOutcome.SUCCEEDED),
        request=request,
        result_payload=canonical_worker_json(complete_result),
        fatal_error_payload=None,
    )
    assert complete.terminal_outcome is TerminalOutcome.SUCCEEDED
    assert complete.code is ScientificFinalizationCode.RESULT_COMPLETE
    assert complete.analysis_outcome is AnalysisOutcome.COMPLETE
    assert complete.result == complete_result
    assert complete.fatal_error is None
    assert complete.accepted_result

    cells = list(complete_result.cells)
    cells[1] = CellFailed(
        cell_id=request.cells[1].cell_id,
        fit_id=request.cells[1].fit_id,
        distance=request.cells[1].distance,
        status="failed",
        error_code=CellErrorCode.DISTANCE_CALCULATION_FAILED,
    )
    partial_result = complete_result.model_copy(
        update={"outcome": AnalysisOutcome.PARTIAL, "cells": tuple(cells)}
    )
    partial = finalize_scientific_execution(
        process=ProcessResult(ProcessOutcome.SUCCEEDED),
        request=request,
        result_payload=canonical_worker_json(partial_result),
        fatal_error_payload=None,
    )
    assert partial.terminal_outcome is TerminalOutcome.SUCCEEDED
    assert partial.code is ScientificFinalizationCode.RESULT_PARTIAL
    assert partial.analysis_outcome is AnalysisOutcome.PARTIAL
    assert partial.result == partial_result
    assert partial.accepted_result


def test_valid_failed_analysis_is_not_upgraded_to_terminal_success() -> None:
    request = request_fixture()
    failed_result = failed_result_fixture(request)
    decision = finalize_scientific_execution(
        process=ProcessResult(ProcessOutcome.SUCCEEDED),
        request=request,
        result_payload=canonical_worker_json(failed_result),
        fatal_error_payload=None,
    )
    assert decision.terminal_outcome is TerminalOutcome.FAILED
    assert decision.code is ScientificFinalizationCode.RESULT_FAILED
    assert decision.analysis_outcome is AnalysisOutcome.FAILED
    assert decision.result == failed_result
    assert not decision.accepted_result


def test_successful_process_requires_exactly_one_valid_bound_artifact() -> None:
    request = request_fixture()
    process = ProcessResult(ProcessOutcome.SUCCEEDED)
    missing = finalize_scientific_execution(
        process=process,
        request=request,
        result_payload=None,
        fatal_error_payload=None,
    )
    assert missing.code is ScientificFinalizationCode.OUTPUT_MISSING
    assert missing.terminal_outcome is TerminalOutcome.FAILED
    assert not missing.accepted_result

    conflict = finalize_scientific_execution(
        process=process,
        request=request,
        result_payload=b"{}",
        fatal_error_payload=b"{}",
    )
    assert conflict.code is ScientificFinalizationCode.OUTPUT_CONFLICT
    assert conflict.terminal_outcome is TerminalOutcome.FAILED

    malformed = finalize_scientific_execution(
        process=process,
        request=request,
        result_payload=b"{}",
        fatal_error_payload=None,
    )
    assert malformed.code is ScientificFinalizationCode.RESULT_INVALID

    huge_number = finalize_scientific_execution(
        process=process,
        request=request,
        result_payload=b'{"value":' + str(10**400).encode() + b"}",
        fatal_error_payload=None,
    )
    assert huge_number.code is ScientificFinalizationCode.RESULT_INVALID

    wrong_result = result_fixture(request).model_copy(update={"request_id": opaque("request", 9)})
    mismatched = finalize_scientific_execution(
        process=process,
        request=request,
        result_payload=canonical_worker_json(wrong_result),
        fatal_error_payload=None,
    )
    assert mismatched.code is ScientificFinalizationCode.RESULT_INVALID


def test_fatal_error_must_be_well_formed_and_bound_to_the_request() -> None:
    request = request_fixture()
    process = ProcessResult(ProcessOutcome.SUCCEEDED)
    fatal = fatal_fixture(request)
    accepted = finalize_scientific_execution(
        process=process,
        request=request,
        result_payload=None,
        fatal_error_payload=canonical_worker_json(fatal),
    )
    assert accepted.terminal_outcome is TerminalOutcome.FAILED
    assert accepted.code is ScientificFinalizationCode.WORKER_FATAL_ERROR
    assert accepted.fatal_error == fatal
    assert accepted.result is None

    malformed = finalize_scientific_execution(
        process=process,
        request=request,
        result_payload=None,
        fatal_error_payload=b"{}",
    )
    assert malformed.code is ScientificFinalizationCode.FATAL_ERROR_INVALID

    wrong = fatal.model_copy(update={"request_id": opaque("request", 9)})
    mismatched = finalize_scientific_execution(
        process=process,
        request=request,
        result_payload=None,
        fatal_error_payload=canonical_worker_json(wrong),
    )
    assert mismatched.code is ScientificFinalizationCode.FATAL_ERROR_INVALID


@pytest.mark.parametrize(
    ("process", "terminal", "code"),
    [
        (
            ProcessResult(ProcessOutcome.FAILED),
            TerminalOutcome.FAILED,
            ScientificFinalizationCode.PROCESS_FAILED,
        ),
        (
            ProcessResult(ProcessOutcome.CANCELLED),
            TerminalOutcome.CANCELLED,
            ScientificFinalizationCode.PROCESS_CANCELLED,
        ),
        (
            ProcessResult(ProcessOutcome.TIMED_OUT, ProcessLimit.WALL),
            TerminalOutcome.TIMED_OUT,
            ScientificFinalizationCode.PROCESS_TIMED_OUT,
        ),
        (
            ProcessResult(ProcessOutcome.CRASHED),
            TerminalOutcome.CRASHED,
            ScientificFinalizationCode.PROCESS_CRASHED,
        ),
        (
            ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.CPU),
            TerminalOutcome.FAILED,
            ScientificFinalizationCode.PROCESS_LIMIT_EXCEEDED,
        ),
        (
            ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.MEMORY),
            TerminalOutcome.FAILED,
            ScientificFinalizationCode.PROCESS_LIMIT_EXCEEDED,
        ),
        (
            ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.PROCESSES),
            TerminalOutcome.FAILED,
            ScientificFinalizationCode.PROCESS_LIMIT_EXCEEDED,
        ),
    ],
)
def test_non_successful_processes_cannot_be_upgraded_by_worker_artifacts(
    process: ProcessResult,
    terminal: TerminalOutcome,
    code: ScientificFinalizationCode,
) -> None:
    decision = finalize_scientific_execution(
        process=process,
        request=request_fixture(),
        result_payload=b"malformed",
        fatal_error_payload=b"conflicting",
    )
    assert decision.terminal_outcome is terminal
    assert decision.code is code
    assert decision.analysis_outcome is None
    assert decision.result is None
    assert decision.fatal_error is None


@pytest.mark.parametrize(
    "process",
    [
        ProcessResult(ProcessOutcome.SUCCEEDED, ProcessLimit.CPU),
        ProcessResult(ProcessOutcome.FAILED, ProcessLimit.WALL),
        ProcessResult(ProcessOutcome.CANCELLED, ProcessLimit.MEMORY),
        ProcessResult(ProcessOutcome.CRASHED, ProcessLimit.PROCESSES),
        ProcessResult(ProcessOutcome.TIMED_OUT),
        ProcessResult(ProcessOutcome.TIMED_OUT, ProcessLimit.CPU),
        ProcessResult(ProcessOutcome.LIMIT_EXCEEDED),
        ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.WALL),
    ],
)
def test_internally_inconsistent_process_results_fail_closed(process: ProcessResult) -> None:
    decision = finalize_scientific_execution(
        process=process,
        request=request_fixture(),
        result_payload=canonical_worker_json(result_fixture(request_fixture())),
        fatal_error_payload=None,
    )
    assert decision.terminal_outcome is TerminalOutcome.CRASHED
    assert decision.code is ScientificFinalizationCode.PROCESS_INVALID


@pytest.mark.parametrize(
    "overrides",
    [
        {"process": cast(Any, "bad-process")},
        {"request": cast(Any, "bad-request")},
        {"result_payload": cast(Any, "bad-result")},
        {"fatal_error_payload": cast(Any, "bad-fatal")},
    ],
)
def test_caller_contract_errors_are_content_free(overrides: dict[str, Any]) -> None:
    arguments: dict[str, Any] = {
        "process": ProcessResult(ProcessOutcome.SUCCEEDED),
        "request": request_fixture(),
        "result_payload": None,
        "fatal_error_payload": None,
    }
    arguments.update(overrides)
    with pytest.raises(ScientificFinalizerError) as captured:
        finalize_scientific_execution(**arguments)
    error = captured.value
    assert error.code is ScientificFinalizerErrorCode.INVALID_INPUT
    assert str(error) == ScientificFinalizerErrorCode.INVALID_INPUT.value
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
