"""Private P008 admission bundle verification and P006 execution orchestration."""

from __future__ import annotations

import hashlib
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from functools import wraps
from typing import Protocol

from pydantic import ValidationError

from delta_lemmata.clock import Clock, require_utc
from delta_lemmata.job_models import (
    ExecutionState,
    JobRecord,
    TerminalOutcome,
    transition_execution,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY, JobPolicy
from delta_lemmata.job_store import SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceArea, WorkspaceLayout, WorkspaceManager
from delta_lemmata.prepared_corpus_service import (
    PREPARED_REQUEST_INDEX_COMPONENT,
    PREPARED_REQUEST_INDEX_MAX_BYTES,
    PreparedRequestIndexV2,
    canonical_prepared_request_index,
)
from delta_lemmata.session_identity import JobId, workspace_component
from delta_lemmata.stylo_contracts import (
    INPUT_MAX_BYTES,
    DocumentRole,
    WorkerInputV1,
    canonical_worker_json,
    parse_worker_input,
)
from delta_lemmata.workflow_models import (
    MAX_WORKFLOW_CONFIG_BYTES,
    ResolvedWorkflowConfigV1,
    canonical_p008_json,
    parse_resolved_workflow_config,
)

OperationIdFactory = Callable[[], str]
_OPERATION_ID = re.compile(r"^op_[0-9a-f]{64}$", flags=re.ASCII)


class AnalysisRunner(Protocol):
    def run(
        self,
        *,
        job: JobRecord,
        layout: WorkspaceLayout,
        request: WorkerInputV1,
    ) -> JobRecord: ...


class AnalysisOrchestratorErrorCode(StrEnum):
    INVALID_CONFIGURATION = "P008_ORCHESTRATOR_INVALID_CONFIGURATION"
    INVALID_OPERATION = "P008_ORCHESTRATOR_INVALID_OPERATION"
    BUNDLE_NOT_AVAILABLE = "P008_ORCHESTRATOR_BUNDLE_NOT_AVAILABLE"
    BUNDLE_INTEGRITY = "P008_ORCHESTRATOR_BUNDLE_INTEGRITY"
    OPERATION_FAILED = "P008_ORCHESTRATOR_OPERATION_FAILED"


class AnalysisOrchestratorError(RuntimeError):
    def __init__(self, code: AnalysisOrchestratorErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class _PreparedAnalysisBundle:
    config: ResolvedWorkflowConfigV1 = field(repr=False)
    request: WorkerInputV1 = field(repr=False)


def _error(code: AnalysisOrchestratorErrorCode) -> AnalysisOrchestratorError:
    error = AnalysisOrchestratorError(code)
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True
    return error


def _content_free[**P, ResultT](method: Callable[P, ResultT]) -> Callable[P, ResultT]:
    @wraps(method)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResultT:
        try:
            return method(*args, **kwargs)
        except AnalysisOrchestratorError as error:
            rejection = error
        except Exception:
            rejection = AnalysisOrchestratorError(AnalysisOrchestratorErrorCode.OPERATION_FAILED)
        rejection.__context__ = None
        rejection.__cause__ = None
        rejection.__suppress_context__ = True
        raise rejection

    return wrapped


def _default_operation_id() -> str:
    return "op_" + secrets.token_hex(32)


class AnalysisOrchestrator:
    """Claim one queued analysis, verify its private bundle, and run P006."""

    @_content_free
    def __init__(
        self,
        *,
        store: SQLiteJobStore,
        workspaces: WorkspaceManager,
        runner: AnalysisRunner,
        clock: Clock,
        policy: JobPolicy = DEFAULT_JOB_POLICY,
        operation_id_factory: OperationIdFactory = _default_operation_id,
    ) -> None:
        if (
            not isinstance(store, SQLiteJobStore)
            or not isinstance(workspaces, WorkspaceManager)
            or not callable(getattr(runner, "run", None))
            or not hasattr(clock, "now")
            or not isinstance(policy, JobPolicy)
            or not callable(operation_id_factory)
        ):
            raise _error(AnalysisOrchestratorErrorCode.INVALID_CONFIGURATION)
        self._store = store
        self._workspaces = workspaces
        self._runner = runner
        self._clock = clock
        self._policy = policy
        self._operation_id_factory = operation_id_factory

    def _now(self) -> datetime:
        rejection = False
        try:
            value = require_utc(self._clock.now(), field_name="analysis orchestrator clock")
        except Exception:
            rejection = True
            value = None
        if rejection or value is None:
            raise _error(AnalysisOrchestratorErrorCode.INVALID_CONFIGURATION)
        return value

    def _operation_id(self) -> str:
        factory_failed = False
        try:
            value = self._operation_id_factory()
        except Exception:
            factory_failed = True
            value = None
        if factory_failed:
            raise _error(AnalysisOrchestratorErrorCode.INVALID_OPERATION)
        if not isinstance(value, str) or _OPERATION_ID.fullmatch(value) is None:
            raise _error(AnalysisOrchestratorErrorCode.INVALID_OPERATION)
        return value

    def _read(
        self,
        *,
        layout: WorkspaceLayout,
        component: str,
        maximum_bytes: int,
    ) -> bytes:
        payload = self._workspaces.read_file(
            layout,
            WorkspaceArea.WORK,
            component,
            maximum_bytes=maximum_bytes,
        )
        if payload is None:
            raise _error(AnalysisOrchestratorErrorCode.BUNDLE_NOT_AVAILABLE)
        return payload

    @staticmethod
    def _verify_semantic_binding(
        config: ResolvedWorkflowConfigV1,
        request: WorkerInputV1,
    ) -> None:
        fit_by_id = {fit.fit_id: (fit.mfw, fit.culling_percent) for fit in request.fits}
        expected_fit_keys = tuple(
            dict.fromkeys((cell.mfw, cell.culling_percent) for cell in config.cells)
        )
        actual_fit_keys = tuple((fit.mfw, fit.culling_percent) for fit in request.fits)
        expected_cells = tuple(
            (cell.mfw, cell.culling_percent, cell.distance) for cell in config.cells
        )
        missing_fit = False
        try:
            actual_cells = tuple((*fit_by_id[cell.fit_id], cell.distance) for cell in request.cells)
        except KeyError:
            missing_fit = True
            actual_cells = ()
        if missing_fit:
            raise _error(AnalysisOrchestratorErrorCode.BUNDLE_INTEGRITY)
        known_count = sum(document.role is DocumentRole.KNOWN for document in request.documents)
        unknown_count = sum(document.role is DocumentRole.UNKNOWN for document in request.documents)
        expected_signature = (
            config.analysis_unit,
            config.seed,
            expected_fit_keys,
            expected_cells,
            config.cell_count,
            config.known_work_count,
            config.unknown_work_count,
        )
        actual_signature = (
            request.analysis_unit,
            request.seed,
            actual_fit_keys,
            actual_cells,
            len(request.cells),
            known_count,
            unknown_count,
        )
        if actual_signature != expected_signature:
            raise _error(AnalysisOrchestratorErrorCode.BUNDLE_INTEGRITY)

    def _load_bundle(self, layout: WorkspaceLayout) -> _PreparedAnalysisBundle:
        index_payload = self._read(
            layout=layout,
            component=PREPARED_REQUEST_INDEX_COMPONENT,
            maximum_bytes=PREPARED_REQUEST_INDEX_MAX_BYTES,
        )
        try:
            index = PreparedRequestIndexV2.model_validate_json(index_payload)
        except ValidationError:
            raise _error(AnalysisOrchestratorErrorCode.BUNDLE_INTEGRITY) from None
        if canonical_prepared_request_index(index) != index_payload:
            raise _error(AnalysisOrchestratorErrorCode.BUNDLE_INTEGRITY)

        config_payload = self._read(
            layout=layout,
            component=index.workflow_config_component,
            maximum_bytes=MAX_WORKFLOW_CONFIG_BYTES,
        )
        request_payload = self._read(
            layout=layout,
            component=index.request_component,
            maximum_bytes=INPUT_MAX_BYTES,
        )
        observed_bindings = (
            (len(config_payload), hashlib.sha256(config_payload).hexdigest()),
            (len(request_payload), hashlib.sha256(request_payload).hexdigest()),
        )
        indexed_bindings = (
            (index.workflow_config_byte_count, index.workflow_config_sha256),
            (index.request_byte_count, index.request_sha256),
        )
        if observed_bindings != indexed_bindings:
            raise _error(AnalysisOrchestratorErrorCode.BUNDLE_INTEGRITY)
        try:
            config = parse_resolved_workflow_config(config_payload)
            request = parse_worker_input(request_payload)
        except Exception:
            raise _error(AnalysisOrchestratorErrorCode.BUNDLE_INTEGRITY) from None
        if (
            canonical_p008_json(config) != config_payload
            or canonical_worker_json(request) != request_payload
        ):
            raise _error(AnalysisOrchestratorErrorCode.BUNDLE_INTEGRITY)
        self._verify_semantic_binding(config, request)
        return _PreparedAnalysisBundle(config=config, request=request)

    def _record_preflight_failure(self, job: JobRecord) -> JobRecord:
        at_utc = self._now()
        terminal = transition_execution(
            job,
            target=ExecutionState.TERMINAL,
            outcome=TerminalOutcome.CRASHED,
            at_utc=at_utc,
            tombstone_expires_at_utc=at_utc + timedelta(seconds=self._policy.tombstone_ttl_seconds),
            expected_version=job.version,
            operation_id=self._operation_id(),
        )
        return self._store.maintenance_compare_and_swap(
            job_id=job.job_id,
            expected_version=job.version,
            updated=terminal,
            at_utc=at_utc,
        )

    @_content_free
    def run_next(self, *, expected_job_id: str | None = None) -> JobRecord | None:
        """Run the oldest queued job when it matches the expected server-side identity."""

        job = self._store.claim_next(
            at_utc=self._now(),
            operation_id=self._operation_id(),
            expected_job_id=expected_job_id,
        )
        if job is None:
            return None
        layout = self._workspaces.load_optional(
            job.owner_digest,
            workspace_component(JobId.from_urlsafe(job.job_id)),
        )
        if layout is None:
            self._record_preflight_failure(job)
            raise _error(AnalysisOrchestratorErrorCode.BUNDLE_NOT_AVAILABLE)
        try:
            self._workspaces.verify(layout)
            bundle = self._load_bundle(layout)
        except AnalysisOrchestratorError:
            self._record_preflight_failure(job)
            raise
        return self._runner.run(job=job, layout=layout, request=bundle.request)

    @_content_free
    def run_until(self, *, expected_job_id: str) -> JobRecord | None:
        """Run the bounded FIFO prefix through one expected server-side job."""

        expected = JobId.from_urlsafe(expected_job_id).to_urlsafe()
        for _ in range(self._policy.max_queued):
            completed = self.run_next()
            if completed is None:
                return None
            if completed.job_id == expected:
                return completed
        return None


__all__ = [
    "AnalysisOrchestrator",
    "AnalysisOrchestratorError",
    "AnalysisOrchestratorErrorCode",
    "AnalysisRunner",
    "OperationIdFactory",
]
