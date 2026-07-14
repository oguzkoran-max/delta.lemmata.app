"""Fixed P006 R/stylo execution adapter with bounded private artifacts."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, NoReturn

from delta_lemmata.job_models import ScientificResultReceipt
from delta_lemmata.job_policy import STYLO_WORKER_LIMITS
from delta_lemmata.job_workspace import (
    WorkspaceArea,
    WorkspaceError,
    WorkspaceLayout,
    WorkspaceManager,
)
from delta_lemmata.process_controller import (
    ProcessController,
    ProcessControllerError,
    ProcessEnvironmentProfile,
    ProcessResult,
)
from delta_lemmata.scientific_finalizer import (
    ScientificFinalization,
    finalize_scientific_execution,
)
from delta_lemmata.stylo_contracts import (
    FATAL_ERROR_MAX_BYTES,
    RESULT_MAX_BYTES,
    AnalysisOutcome,
    StyloContractError,
    WorkerInputV1,
    canonical_worker_json,
)

REQUEST_COMPONENT = "28e9d3d83efa686b8b51b80eccd9b4f3439aeb56141e459abd97729c9c5b9184"
RESULT_COMPONENT: Literal["053bf21e22c557bd2e9cc53b858b02603c19200680fe1cc2d885bd1b11d6987b"] = (
    "053bf21e22c557bd2e9cc53b858b02603c19200680fe1cc2d885bd1b11d6987b"
)
FATAL_ERROR_COMPONENT = "24ae13b5ee15a59e2f7924a480c4160907d13e900a8d879f1d81b0faab8f6548"

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_RSCRIPT_PATH = Path("/usr/local/bin/Rscript")
_WORKER_SCRIPT_PATH = _PROJECT_ROOT / "scripts" / "workers" / "p006-stylo-worker-v1.R"
STYLO_WORKER_ARGV = (
    str(_RSCRIPT_PATH),
    "--vanilla",
    str(_WORKER_SCRIPT_PATH),
)


class StyloWorkerAdapterErrorCode(StrEnum):
    INVALID_CONFIGURATION = "STYLO_WORKER_INVALID_CONFIGURATION"
    INVALID_REQUEST = "STYLO_WORKER_INVALID_REQUEST"
    PREPARE_FAILED = "STYLO_WORKER_PREPARE_FAILED"
    EXECUTION_FAILED = "STYLO_WORKER_EXECUTION_FAILED"
    CAPTURE_FAILED = "STYLO_WORKER_CAPTURE_FAILED"


class StyloWorkerAdapterError(RuntimeError):
    """Content-free adapter rejection."""

    def __init__(self, code: StyloWorkerAdapterErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class WorkerArtifactKind(StrEnum):
    RESULT = "result"
    FATAL_ERROR = "fatal_error"


@dataclass(frozen=True, slots=True)
class WorkerArtifactReceipt:
    kind: WorkerArtifactKind
    component: str
    byte_size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class StyloWorkerExecution:
    finalization: ScientificFinalization
    artifacts: tuple[WorkerArtifactReceipt, ...]

    @property
    def accepted_result(self) -> bool:
        return self.finalization.accepted_result


def _reject(code: StyloWorkerAdapterErrorCode) -> NoReturn:
    error = StyloWorkerAdapterError(code)
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True
    raise error from None


def _trusted_runtime() -> None:
    runtime_invalid = False
    try:
        executable = _RSCRIPT_PATH.resolve(strict=True)
        executable_info = executable.stat()
        script_info = _WORKER_SCRIPT_PATH.lstat()
    except (OSError, RuntimeError):
        runtime_invalid = True
    if runtime_invalid:
        _reject(StyloWorkerAdapterErrorCode.INVALID_CONFIGURATION)
    if (
        not executable.is_absolute()
        or not stat.S_ISREG(executable_info.st_mode)
        or not os.access(executable, os.X_OK)
        or _WORKER_SCRIPT_PATH.is_symlink()
        or not stat.S_ISREG(script_info.st_mode)
    ):
        _reject(StyloWorkerAdapterErrorCode.INVALID_CONFIGURATION)


def _receipt(
    kind: WorkerArtifactKind,
    component: str,
    payload: bytes,
) -> WorkerArtifactReceipt:
    return WorkerArtifactReceipt(
        kind=kind,
        component=component,
        byte_size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )


class StyloWorkerAdapter:
    """Execute the one fixed worker without accepting runtime or path parameters."""

    def __init__(self, manager: WorkspaceManager, layout: WorkspaceLayout) -> None:
        if not isinstance(manager, WorkspaceManager) or not isinstance(layout, WorkspaceLayout):
            _reject(StyloWorkerAdapterErrorCode.INVALID_CONFIGURATION)
        _trusted_runtime()
        self._manager = manager
        self._layout = layout

    def prepare(self, request: WorkerInputV1) -> None:
        """Write one canonical request before a guardian starts the fixed worker."""

        if not isinstance(request, WorkerInputV1):
            _reject(StyloWorkerAdapterErrorCode.INVALID_REQUEST)
        prepare_failed = False
        try:
            request_payload = canonical_worker_json(request)
            for component, maximum in (
                (RESULT_COMPONENT, RESULT_MAX_BYTES),
                (FATAL_ERROR_COMPONENT, FATAL_ERROR_MAX_BYTES),
            ):
                if (
                    self._manager.read_file(
                        self._layout,
                        WorkspaceArea.WORK,
                        component,
                        maximum_bytes=maximum,
                    )
                    is not None
                ):
                    _reject(StyloWorkerAdapterErrorCode.PREPARE_FAILED)
            self._manager.create_file(
                self._layout,
                WorkspaceArea.WORK,
                REQUEST_COMPONENT,
                request_payload,
            )
        except (StyloContractError, WorkspaceError, OSError):
            prepare_failed = True
        if prepare_failed:
            _reject(StyloWorkerAdapterErrorCode.PREPARE_FAILED)

    def capture(
        self,
        request: WorkerInputV1,
        process: ProcessResult,
    ) -> StyloWorkerExecution:
        """Capture and scientifically classify bounded worker artifacts."""

        if not isinstance(request, WorkerInputV1) or not isinstance(process, ProcessResult):
            _reject(StyloWorkerAdapterErrorCode.INVALID_REQUEST)

        capture_failed = False
        try:
            result_payload = self._manager.read_file(
                self._layout,
                WorkspaceArea.WORK,
                RESULT_COMPONENT,
                maximum_bytes=RESULT_MAX_BYTES,
            )
            fatal_error_payload = self._manager.read_file(
                self._layout,
                WorkspaceArea.WORK,
                FATAL_ERROR_COMPONENT,
                maximum_bytes=FATAL_ERROR_MAX_BYTES,
            )
        except (WorkspaceError, OSError):
            capture_failed = True
        if capture_failed:
            _reject(StyloWorkerAdapterErrorCode.CAPTURE_FAILED)

        artifacts = tuple(
            receipt
            for receipt in (
                _receipt(WorkerArtifactKind.RESULT, RESULT_COMPONENT, result_payload)
                if result_payload is not None
                else None,
                _receipt(
                    WorkerArtifactKind.FATAL_ERROR,
                    FATAL_ERROR_COMPONENT,
                    fatal_error_payload,
                )
                if fatal_error_payload is not None
                else None,
            )
            if receipt is not None
        )
        finalization = finalize_scientific_execution(
            process=process,
            request=request,
            result_payload=result_payload,
            fatal_error_payload=fatal_error_payload,
        )
        return StyloWorkerExecution(finalization=finalization, artifacts=artifacts)

    def publish_validated_result(
        self,
        request: WorkerInputV1,
        execution: StyloWorkerExecution,
    ) -> ScientificResultReceipt:
        """Copy one accepted raw result into its retained area and bind it by digest."""

        if (
            not isinstance(request, WorkerInputV1)
            or not isinstance(execution, StyloWorkerExecution)
            or not execution.accepted_result
            or execution.finalization.result is None
            or execution.finalization.analysis_outcome is None
            or execution.finalization.result.request_id != request.request_id
        ):
            _reject(StyloWorkerAdapterErrorCode.CAPTURE_FAILED)
        result_receipts = tuple(
            item for item in execution.artifacts if item.kind is WorkerArtifactKind.RESULT
        )
        if len(result_receipts) != 1:
            _reject(StyloWorkerAdapterErrorCode.CAPTURE_FAILED)
        source_receipt = result_receipts[0]
        publish_failed = False
        request_payload = b""
        try:
            source = self._manager.read_file(
                self._layout,
                WorkspaceArea.WORK,
                RESULT_COMPONENT,
                maximum_bytes=RESULT_MAX_BYTES,
            )
            existing = self._manager.read_file(
                self._layout,
                WorkspaceArea.RESULT,
                RESULT_COMPONENT,
                maximum_bytes=RESULT_MAX_BYTES,
            )
            if source is None or (
                _receipt(WorkerArtifactKind.RESULT, RESULT_COMPONENT, source) != source_receipt
            ):
                publish_failed = True
            elif existing is not None:
                if (
                    _receipt(WorkerArtifactKind.RESULT, RESULT_COMPONENT, existing)
                    != source_receipt
                ):
                    publish_failed = True
            else:
                self._manager.create_file(
                    self._layout,
                    WorkspaceArea.RESULT,
                    RESULT_COMPONENT,
                    source,
                )
                retained = self._manager.read_file(
                    self._layout,
                    WorkspaceArea.RESULT,
                    RESULT_COMPONENT,
                    maximum_bytes=RESULT_MAX_BYTES,
                )
                if (
                    retained is None
                    or _receipt(WorkerArtifactKind.RESULT, RESULT_COMPONENT, retained)
                    != source_receipt
                ):
                    publish_failed = True
            request_payload = canonical_worker_json(request)
        except (StyloContractError, WorkspaceError, OSError):
            publish_failed = True
        if publish_failed:
            _reject(StyloWorkerAdapterErrorCode.CAPTURE_FAILED)
        result = execution.finalization.result
        analysis_outcome = execution.finalization.analysis_outcome
        if result is None or analysis_outcome is None:  # pragma: no cover - guarded above
            _reject(StyloWorkerAdapterErrorCode.CAPTURE_FAILED)
        receipt_outcome: Literal["complete", "partial"]
        if analysis_outcome is AnalysisOutcome.COMPLETE:
            receipt_outcome = "complete"
        elif analysis_outcome is AnalysisOutcome.PARTIAL:
            receipt_outcome = "partial"
        else:  # pragma: no cover - accepted-result invariant
            _reject(StyloWorkerAdapterErrorCode.CAPTURE_FAILED)
        return ScientificResultReceipt(
            schema_version="scientific-result-receipt-v1",
            request_id=result.request_id,
            request_sha256=hashlib.sha256(request_payload).hexdigest(),
            worker_version=result.worker_version,
            result_schema_version=result.schema_version,
            analysis_outcome=receipt_outcome,
            artifact_component=RESULT_COMPONENT,
            byte_size=source_receipt.byte_size,
            sha256=source_receipt.sha256,
        )

    def execute(self, request: WorkerInputV1) -> StyloWorkerExecution:
        self.prepare(request)

        execution_failed = False
        try:
            process = ProcessController(
                argv=STYLO_WORKER_ARGV,
                cwd=self._layout.work,
                limits=STYLO_WORKER_LIMITS,
                environment_profile=ProcessEnvironmentProfile.R_STYLO,
            ).run()
        except ProcessControllerError:
            execution_failed = True
        if execution_failed:
            _reject(StyloWorkerAdapterErrorCode.EXECUTION_FAILED)
        return self.capture(request, process)


__all__ = [
    "FATAL_ERROR_COMPONENT",
    "REQUEST_COMPONENT",
    "RESULT_COMPONENT",
    "STYLO_WORKER_ARGV",
    "StyloWorkerAdapter",
    "StyloWorkerAdapterError",
    "StyloWorkerAdapterErrorCode",
    "StyloWorkerExecution",
    "WorkerArtifactKind",
    "WorkerArtifactReceipt",
]
