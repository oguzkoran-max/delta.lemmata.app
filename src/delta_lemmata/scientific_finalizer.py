"""Fail-closed scientific finalization for one P006 worker execution.

Process completion and scientific acceptance are deliberately separate.  A zero
exit status only permits validation to begin; it never upgrades an absent,
conflicting, malformed, or semantically invalid worker artifact into success.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import NoReturn, cast

from delta_lemmata.job_models import TerminalOutcome
from delta_lemmata.process_controller import (
    ProcessLimit,
    ProcessOutcome,
    ProcessResult,
)
from delta_lemmata.stylo_contracts import (
    AnalysisOutcome,
    StyloContractError,
    WorkerFatalErrorV1,
    WorkerInputV1,
    WorkerResultV1,
    parse_worker_fatal_error,
    parse_worker_result,
    validate_worker_fatal_error,
    validate_worker_result,
)


class ScientificFinalizationCode(StrEnum):
    """Stable, content-free reason for one terminal classification."""

    PROCESS_INVALID = "SCIENTIFIC_PROCESS_INVALID"
    PROCESS_FAILED = "SCIENTIFIC_PROCESS_FAILED"
    PROCESS_CANCELLED = "SCIENTIFIC_PROCESS_CANCELLED"
    PROCESS_TIMED_OUT = "SCIENTIFIC_PROCESS_TIMED_OUT"
    PROCESS_CRASHED = "SCIENTIFIC_PROCESS_CRASHED"
    PROCESS_LIMIT_EXCEEDED = "SCIENTIFIC_PROCESS_LIMIT_EXCEEDED"
    OUTPUT_MISSING = "SCIENTIFIC_OUTPUT_MISSING"
    OUTPUT_CONFLICT = "SCIENTIFIC_OUTPUT_CONFLICT"
    RESULT_INVALID = "SCIENTIFIC_RESULT_INVALID"
    FATAL_ERROR_INVALID = "SCIENTIFIC_FATAL_ERROR_INVALID"
    WORKER_FATAL_ERROR = "SCIENTIFIC_WORKER_FATAL_ERROR"
    RESULT_COMPLETE = "SCIENTIFIC_RESULT_COMPLETE"
    RESULT_PARTIAL = "SCIENTIFIC_RESULT_PARTIAL"
    RESULT_FAILED = "SCIENTIFIC_RESULT_FAILED"


class ScientificFinalizerErrorCode(StrEnum):
    INVALID_INPUT = "SCIENTIFIC_FINALIZER_INVALID_INPUT"


class ScientificFinalizerError(RuntimeError):
    """A caller-contract failure with no payload or infrastructure detail."""

    def __init__(self, code: ScientificFinalizerErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class ScientificFinalization:
    """Trusted internal decision produced after process and artifact checks."""

    process: ProcessResult
    terminal_outcome: TerminalOutcome
    code: ScientificFinalizationCode
    analysis_outcome: AnalysisOutcome | None = None
    result: WorkerResultV1 | None = None
    fatal_error: WorkerFatalErrorV1 | None = None

    @property
    def accepted_result(self) -> bool:
        return self.code in {
            ScientificFinalizationCode.RESULT_COMPLETE,
            ScientificFinalizationCode.RESULT_PARTIAL,
        }


def _reject(code: ScientificFinalizerErrorCode) -> NoReturn:
    error = ScientificFinalizerError(code)
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True
    raise error from None


def _valid_process_result(result: ProcessResult) -> bool:
    return bool(
        (
            result.outcome
            in {
                ProcessOutcome.SUCCEEDED,
                ProcessOutcome.FAILED,
                ProcessOutcome.CANCELLED,
                ProcessOutcome.CRASHED,
            }
            and result.limit is None
        )
        or (result.outcome is ProcessOutcome.TIMED_OUT and result.limit is ProcessLimit.WALL)
        or (
            result.outcome is ProcessOutcome.LIMIT_EXCEEDED
            and result.limit
            in {
                ProcessLimit.CPU,
                ProcessLimit.MEMORY,
                ProcessLimit.PROCESSES,
            }
        )
    )


def _process_failure(result: ProcessResult) -> ScientificFinalization:
    mapping = {
        ProcessOutcome.FAILED: (
            TerminalOutcome.FAILED,
            ScientificFinalizationCode.PROCESS_FAILED,
        ),
        ProcessOutcome.CANCELLED: (
            TerminalOutcome.CANCELLED,
            ScientificFinalizationCode.PROCESS_CANCELLED,
        ),
        ProcessOutcome.TIMED_OUT: (
            TerminalOutcome.TIMED_OUT,
            ScientificFinalizationCode.PROCESS_TIMED_OUT,
        ),
        ProcessOutcome.CRASHED: (
            TerminalOutcome.CRASHED,
            ScientificFinalizationCode.PROCESS_CRASHED,
        ),
        ProcessOutcome.LIMIT_EXCEEDED: (
            TerminalOutcome.FAILED,
            ScientificFinalizationCode.PROCESS_LIMIT_EXCEEDED,
        ),
    }
    terminal, code = mapping[result.outcome]
    return ScientificFinalization(process=result, terminal_outcome=terminal, code=code)


def finalize_scientific_execution(
    *,
    process: ProcessResult,
    request: WorkerInputV1,
    result_payload: bytes | None,
    fatal_error_payload: bytes | None,
) -> ScientificFinalization:
    """Classify one execution without trusting process success or worker JSON."""

    if (
        not isinstance(process, ProcessResult)
        or not isinstance(request, WorkerInputV1)
        or (result_payload is not None and not isinstance(result_payload, bytes))
        or (fatal_error_payload is not None and not isinstance(fatal_error_payload, bytes))
    ):
        _reject(ScientificFinalizerErrorCode.INVALID_INPUT)
    if not _valid_process_result(process):
        return ScientificFinalization(
            process=process,
            terminal_outcome=TerminalOutcome.CRASHED,
            code=ScientificFinalizationCode.PROCESS_INVALID,
        )
    if process.outcome is not ProcessOutcome.SUCCEEDED:
        return _process_failure(process)

    if result_payload is None and fatal_error_payload is None:
        return ScientificFinalization(
            process=process,
            terminal_outcome=TerminalOutcome.FAILED,
            code=ScientificFinalizationCode.OUTPUT_MISSING,
        )
    if result_payload is not None and fatal_error_payload is not None:
        return ScientificFinalization(
            process=process,
            terminal_outcome=TerminalOutcome.FAILED,
            code=ScientificFinalizationCode.OUTPUT_CONFLICT,
        )
    if result_payload is not None:
        try:
            result = validate_worker_result(request, parse_worker_result(result_payload))
        except StyloContractError:
            return ScientificFinalization(
                process=process,
                terminal_outcome=TerminalOutcome.FAILED,
                code=ScientificFinalizationCode.RESULT_INVALID,
            )
        if result.outcome is AnalysisOutcome.COMPLETE:
            code = ScientificFinalizationCode.RESULT_COMPLETE
            terminal = TerminalOutcome.SUCCEEDED
        elif result.outcome is AnalysisOutcome.PARTIAL:
            code = ScientificFinalizationCode.RESULT_PARTIAL
            terminal = TerminalOutcome.SUCCEEDED
        else:
            code = ScientificFinalizationCode.RESULT_FAILED
            terminal = TerminalOutcome.FAILED
        return ScientificFinalization(
            process=process,
            terminal_outcome=terminal,
            code=code,
            analysis_outcome=result.outcome,
            result=result,
        )

    try:
        fatal_error = validate_worker_fatal_error(
            request,
            parse_worker_fatal_error(cast(bytes, fatal_error_payload)),
        )
    except StyloContractError:
        return ScientificFinalization(
            process=process,
            terminal_outcome=TerminalOutcome.FAILED,
            code=ScientificFinalizationCode.FATAL_ERROR_INVALID,
        )
    return ScientificFinalization(
        process=process,
        terminal_outcome=TerminalOutcome.FAILED,
        code=ScientificFinalizationCode.WORKER_FATAL_ERROR,
        fatal_error=fatal_error,
    )


__all__ = [
    "ScientificFinalization",
    "ScientificFinalizationCode",
    "ScientificFinalizerError",
    "ScientificFinalizerErrorCode",
    "finalize_scientific_execution",
]
