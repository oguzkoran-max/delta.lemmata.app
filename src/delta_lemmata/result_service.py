"""Capability-authorized P006 readback and bounded P009 result publication."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from functools import wraps

from delta_lemmata.clock import Clock, require_utc
from delta_lemmata.job_models import (
    CleanupState,
    ExecutionState,
    JobRecord,
    ResultViewReceipt,
    TerminalOutcome,
    VersionConflictError,
    commit_result_view,
)
from delta_lemmata.job_store import SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceArea, WorkspaceLayout, WorkspaceManager
from delta_lemmata.prepared_corpus_service import (
    PREPARED_REQUEST_INDEX_COMPONENT,
    PREPARED_REQUEST_INDEX_MAX_BYTES,
    PreparedRequestIndexV2,
    canonical_prepared_request_index,
)
from delta_lemmata.result_view import (
    MAX_RESULT_VIEW_BYTES,
    RESULT_VIEW_COMPONENT,
    ResultDocumentDescriptor,
    ResultViewV1,
    canonical_result_view,
    parse_result_view,
    project_result_view,
)
from delta_lemmata.session_identity import JobId, SessionCapability, workspace_component
from delta_lemmata.stylo_contracts import (
    INPUT_MAX_BYTES,
    RESULT_MAX_BYTES,
    WorkerInputV1,
    WorkerResultV1,
    canonical_worker_json,
    parse_worker_input,
    parse_worker_result,
    validate_worker_result,
)
from delta_lemmata.stylo_worker import RESULT_COMPONENT
from delta_lemmata.workflow_models import (
    MAX_WORKFLOW_CONFIG_BYTES,
    ResolvedWorkflowConfigV1,
    canonical_p008_json,
    parse_resolved_workflow_config,
    workflow_config_sha256,
)

_OPERATION_DOMAIN = b"delta-lemmata\x00p009-result-view\x00v1\x00"


class ResultPackageErrorCode(StrEnum):
    INVALID_CONFIGURATION = "P009_RESULT_INVALID_CONFIGURATION"
    INVALID_REQUEST = "P009_RESULT_INVALID_REQUEST"
    NOT_AVAILABLE = "P009_RESULT_NOT_AVAILABLE"
    EXPIRED = "P009_RESULT_EXPIRED"
    INTEGRITY = "P009_RESULT_INTEGRITY"
    BINDING_MISMATCH = "P009_RESULT_BINDING_MISMATCH"
    CONFLICT = "P009_RESULT_CONFLICT"
    OPERATION_FAILED = "P009_RESULT_OPERATION_FAILED"


class ResultPackageError(RuntimeError):
    """Content-free result readback or publication rejection."""

    def __init__(self, code: ResultPackageErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class VerifiedScientificResult:
    result: WorkerResultV1
    sha256: str


@dataclass(frozen=True, slots=True)
class _VerifiedContext:
    job: JobRecord
    layout: WorkspaceLayout
    request: WorkerInputV1
    config: ResolvedWorkflowConfigV1
    scientific: VerifiedScientificResult


def _detach(error: ResultPackageError) -> None:
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True


def _error(code: ResultPackageErrorCode) -> ResultPackageError:
    error = ResultPackageError(code)
    _detach(error)
    return error


def _content_free[**P, ResultT](method: Callable[P, ResultT]) -> Callable[P, ResultT]:
    @wraps(method)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResultT:
        try:
            return method(*args, **kwargs)
        except ResultPackageError as error:
            rejection = error
        except Exception:
            rejection = ResultPackageError(ResultPackageErrorCode.OPERATION_FAILED)
        _detach(rejection)
        raise rejection

    return wrapped


class ResultPackageService:
    """Verify private scientific output before exposing one closed public projection."""

    @_content_free
    def __init__(
        self,
        *,
        store: SQLiteJobStore,
        workspaces: WorkspaceManager,
        clock: Clock,
    ) -> None:
        if (
            not isinstance(store, SQLiteJobStore)
            or not isinstance(workspaces, WorkspaceManager)
            or not hasattr(clock, "now")
        ):
            raise _error(ResultPackageErrorCode.INVALID_CONFIGURATION)
        self._store = store
        self._workspaces = workspaces
        self._clock = clock

    def _now(self) -> datetime:
        try:
            return require_utc(self._clock.now(), field_name="result package clock")
        except Exception:
            raise _error(ResultPackageErrorCode.INVALID_CONFIGURATION) from None

    def _load_job(
        self,
        *,
        job_id: str,
        capability: SessionCapability,
    ) -> tuple[JobRecord, WorkspaceLayout]:
        if not isinstance(job_id, str) or not isinstance(capability, SessionCapability):
            raise _error(ResultPackageErrorCode.INVALID_REQUEST)
        try:
            parsed_job_id = JobId.from_urlsafe(job_id)
            job = self._store.get_job(job_id=parsed_job_id, capability=capability)
            layout = self._workspaces.load_optional(
                job.owner_digest,
                workspace_component(parsed_job_id),
            )
        except Exception:
            raise _error(ResultPackageErrorCode.NOT_AVAILABLE) from None
        if layout is None:
            raise _error(ResultPackageErrorCode.NOT_AVAILABLE)
        return job, layout

    def _read_prepared_context(
        self,
        layout: WorkspaceLayout,
    ) -> tuple[WorkerInputV1, ResolvedWorkflowConfigV1]:
        try:
            index_payload = self._workspaces.read_file(
                layout,
                WorkspaceArea.WORK,
                PREPARED_REQUEST_INDEX_COMPONENT,
                maximum_bytes=PREPARED_REQUEST_INDEX_MAX_BYTES,
            )
            if index_payload is None:
                raise ValueError
            index = PreparedRequestIndexV2.model_validate_json(index_payload)
            if canonical_prepared_request_index(index) != index_payload:
                raise ValueError
            request_payload = self._workspaces.read_file(
                layout,
                WorkspaceArea.WORK,
                index.request_component,
                maximum_bytes=INPUT_MAX_BYTES,
            )
            config_payload = self._workspaces.read_file(
                layout,
                WorkspaceArea.WORK,
                index.workflow_config_component,
                maximum_bytes=MAX_WORKFLOW_CONFIG_BYTES,
            )
            if (
                request_payload is None
                or len(request_payload) != index.request_byte_count
                or hashlib.sha256(request_payload).hexdigest() != index.request_sha256
                or config_payload is None
                or len(config_payload) != index.workflow_config_byte_count
                or hashlib.sha256(config_payload).hexdigest() != index.workflow_config_sha256
            ):
                raise ValueError
            request = parse_worker_input(request_payload)
            config = parse_resolved_workflow_config(config_payload)
            if (
                canonical_worker_json(request) != request_payload
                or canonical_p008_json(config) != config_payload
                or workflow_config_sha256(config) != index.workflow_config_sha256
            ):
                raise ValueError
        except Exception:
            raise _error(ResultPackageErrorCode.INTEGRITY) from None
        return request, config

    def _read_scientific(
        self,
        *,
        job: JobRecord,
        layout: WorkspaceLayout,
        request: WorkerInputV1,
    ) -> VerifiedScientificResult:
        receipt = job.scientific_result
        result_status = job.artifacts.result
        if (
            job.execution.state is not ExecutionState.TERMINAL
            or job.outcome is None
            or job.outcome.kind is not TerminalOutcome.SUCCEEDED
            or receipt is None
            or not job.scientific_result_confirmed
            or result_status.state is not CleanupState.PRESENT
            or result_status.delete_by_utc is None
        ):
            raise _error(ResultPackageErrorCode.NOT_AVAILABLE)
        if self._now() >= result_status.delete_by_utc:
            raise _error(ResultPackageErrorCode.EXPIRED)
        try:
            payload = self._workspaces.read_file(
                layout,
                WorkspaceArea.RESULT,
                RESULT_COMPONENT,
                maximum_bytes=RESULT_MAX_BYTES,
            )
            if (
                payload is None
                or receipt.artifact_component != RESULT_COMPONENT
                or len(payload) != receipt.byte_size
                or hashlib.sha256(payload).hexdigest() != receipt.sha256
                or receipt.request_id != request.request_id
                or receipt.request_sha256
                != hashlib.sha256(canonical_worker_json(request)).hexdigest()
            ):
                raise ValueError
            result = validate_worker_result(request, parse_worker_result(payload))
            if (
                canonical_worker_json(result) != payload
                or result.worker_version != receipt.worker_version
                or result.schema_version != receipt.result_schema_version
                or result.outcome.value != receipt.analysis_outcome
            ):
                raise ValueError
        except Exception:
            raise _error(ResultPackageErrorCode.INTEGRITY) from None
        return VerifiedScientificResult(result=result, sha256=receipt.sha256)

    def _verified_context(
        self,
        *,
        job_id: str,
        capability: SessionCapability,
    ) -> _VerifiedContext:
        job, layout = self._load_job(job_id=job_id, capability=capability)
        request, config = self._read_prepared_context(layout)
        scientific = self._read_scientific(job=job, layout=layout, request=request)
        return _VerifiedContext(
            job=job,
            layout=layout,
            request=request,
            config=config,
            scientific=scientific,
        )

    @staticmethod
    def _receipt(view: ResultViewV1, payload: bytes) -> ResultViewReceipt:
        return ResultViewReceipt(
            schema_version="result-view-receipt-v1",
            source_result_sha256=view.source_result_sha256,
            workflow_config_sha256=view.workflow_config_sha256,
            view_schema_version=view.schema_version,
            artifact_component=RESULT_VIEW_COMPONENT,
            byte_size=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
        )

    @staticmethod
    def _operation_id(job_id: str, receipt: ResultViewReceipt) -> str:
        material = (
            job_id.encode("ascii")
            + b"\x00"
            + receipt.sha256.encode("ascii")
            + b"\x00"
            + receipt.source_result_sha256.encode("ascii")
        )
        return "op_" + hashlib.sha256(_OPERATION_DOMAIN + material).hexdigest()

    def _create_or_verify_view(
        self,
        *,
        layout: WorkspaceLayout,
        payload: bytes,
    ) -> None:
        try:
            self._workspaces.create_file(
                layout,
                WorkspaceArea.EXPORT,
                RESULT_VIEW_COMPONENT,
                payload,
            )
            return
        except Exception:
            pass
        try:
            existing = self._workspaces.read_file(
                layout,
                WorkspaceArea.EXPORT,
                RESULT_VIEW_COMPONENT,
                maximum_bytes=MAX_RESULT_VIEW_BYTES,
            )
        except Exception:
            existing = None
        if existing != payload:
            raise _error(ResultPackageErrorCode.CONFLICT)

    def _verify_view_file(
        self,
        *,
        job: JobRecord,
        layout: WorkspaceLayout,
        require_published: bool,
    ) -> ResultViewV1:
        receipt = job.result_view
        export = job.artifacts.export
        if (
            receipt is None
            or export.state is not CleanupState.PRESENT
            or export.delete_by_utc is None
            or (require_published and not job.export_available)
        ):
            raise _error(ResultPackageErrorCode.NOT_AVAILABLE)
        if self._now() >= export.delete_by_utc:
            raise _error(ResultPackageErrorCode.EXPIRED)
        try:
            payload = self._workspaces.read_file(
                layout,
                WorkspaceArea.EXPORT,
                RESULT_VIEW_COMPONENT,
                maximum_bytes=MAX_RESULT_VIEW_BYTES,
            )
            if (
                payload is None
                or receipt.artifact_component != RESULT_VIEW_COMPONENT
                or len(payload) != receipt.byte_size
                or hashlib.sha256(payload).hexdigest() != receipt.sha256
            ):
                raise ValueError
            view = parse_result_view(payload)
            if (
                canonical_result_view(view) != payload
                or view.source_result_sha256 != receipt.source_result_sha256
                or view.workflow_config_sha256 != receipt.workflow_config_sha256
                or job.scientific_result is None
                or view.source_result_sha256 != job.scientific_result.sha256
            ):
                raise ValueError
        except ResultPackageError:
            raise
        except Exception:
            raise _error(ResultPackageErrorCode.INTEGRITY) from None
        return view

    @_content_free
    def read_scientific_result(
        self,
        *,
        job_id: str,
        capability: SessionCapability,
    ) -> VerifiedScientificResult:
        """Return one fully revalidated scientific result to trusted server code."""

        return self._verified_context(job_id=job_id, capability=capability).scientific

    @_content_free
    def publish_view(
        self,
        *,
        job_id: str,
        capability: SessionCapability,
        view: ResultViewV1,
    ) -> ResultViewReceipt:
        """Verify and durably stage one exact public projection before cleanup."""

        if not isinstance(view, ResultViewV1):
            raise _error(ResultPackageErrorCode.INVALID_REQUEST)
        checked = parse_result_view(canonical_result_view(view))
        payload = canonical_result_view(checked)
        receipt = self._receipt(checked, payload)
        job, layout = self._load_job(job_id=job_id, capability=capability)
        if job.result_view is not None:
            if job.result_view != receipt:
                raise _error(ResultPackageErrorCode.CONFLICT)
            self._verify_view_file(job=job, layout=layout, require_published=False)
            return receipt

        context = self._verified_context(job_id=job_id, capability=capability)
        descriptors = tuple(
            ResultDocumentDescriptor(
                document_id=document.document_id,
                title=public.title,
                role=document.role,
            )
            for document, public in zip(
                context.request.documents,
                checked.documents,
                strict=True,
            )
        )
        expected = project_result_view(
            config=context.config,
            result=context.scientific.result,
            source_result_sha256=context.scientific.sha256,
            documents=descriptors,
        )
        if expected != checked:
            raise _error(ResultPackageErrorCode.BINDING_MISMATCH)
        self._create_or_verify_view(layout=context.layout, payload=payload)

        operation_id = self._operation_id(job_id, receipt)
        current = context.job
        for _attempt in range(3):
            if current.result_view is not None:
                if current.result_view != receipt:
                    raise _error(ResultPackageErrorCode.CONFLICT)
                self._verify_view_file(
                    job=current,
                    layout=context.layout,
                    require_published=False,
                )
                return receipt
            try:
                updated = commit_result_view(
                    current,
                    receipt=receipt,
                    at_utc=self._now(),
                    expected_version=current.version,
                    operation_id=operation_id,
                )
                self._store.compare_and_swap(
                    job_id=job_id,
                    capability=capability,
                    expected_version=current.version,
                    updated=updated,
                    at_utc=self._now(),
                )
                return receipt
            except VersionConflictError:
                current, _layout = self._load_job(job_id=job_id, capability=capability)
            except ResultPackageError:
                raise
            except Exception:
                raise _error(ResultPackageErrorCode.CONFLICT) from None
        raise _error(ResultPackageErrorCode.CONFLICT)

    @_content_free
    def read_view(
        self,
        *,
        job_id: str,
        capability: SessionCapability,
    ) -> ResultViewV1:
        """Read one published public projection and revalidate its durable receipt."""

        job, layout = self._load_job(job_id=job_id, capability=capability)
        return self._verify_view_file(job=job, layout=layout, require_published=True)


__all__ = [
    "ResultPackageError",
    "ResultPackageErrorCode",
    "ResultPackageService",
    "VerifiedScientificResult",
]
