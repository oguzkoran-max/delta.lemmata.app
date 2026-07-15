"""Capability-first application boundary for ephemeral job operations."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from functools import wraps
from typing import Protocol

from delta_lemmata.clock import Clock, require_utc
from delta_lemmata.job_events import DeletionReason, new_deletion_event
from delta_lemmata.job_models import (
    ArtifactKind,
    CancellationState,
    CleanupState,
    ExecutionState,
    JobRecord,
    TerminalOutcome,
    VersionConflictError,
    request_cancellation,
    transition_artifact,
    transition_execution,
    withdraw_export,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY, JobPolicy
from delta_lemmata.job_projection import project_job_record
from delta_lemmata.job_staging import (
    MaterializationReceipt,
    ValidatedPayload,
    materialize_validated_payloads,
)
from delta_lemmata.job_store import (
    AnalysisAdmissionRejectedError,
    AnalysisAdmissionReusedError,
    JobAdmissionCleanupUnresolvedError,
    JobAdmissionRejectedError,
    JobNotAvailableError,
    SQLiteJobStore,
)
from delta_lemmata.job_ui import JobPresentation
from delta_lemmata.job_workspace import CleanupReport, WorkspaceLayout, WorkspaceManager
from delta_lemmata.session_identity import JobId, SessionCapability, workspace_component

OperationIdFactory = Callable[[], str]
Materializer = Callable[
    [WorkspaceManager, WorkspaceLayout, Sequence[ValidatedPayload]],
    MaterializationReceipt,
]


class ProcessGateway(Protocol):
    """Scheduler-owned process surface with idempotent synchronous cancellation.

    A failed ``start`` must either leave no live process or keep ``cancel`` able to
    synchronously prove the worker absent before it returns.
    """

    def start(self, job: JobRecord, layout: WorkspaceLayout) -> None: ...

    def cancel(self, job: JobRecord) -> None: ...


@dataclass(frozen=True, slots=True)
class JobAdmission:
    """Payload-free receipt for one committed stage or queue admission."""

    job: JobRecord
    materialization: MaterializationReceipt


class JobServiceErrorCode(StrEnum):
    """Stable application errors with no research or infrastructure content."""

    INVALID_CONFIGURATION = "JOB_SERVICE_INVALID_CONFIGURATION"
    ADMISSION_REJECTED = "JOB_ADMISSION_REJECTED"
    NOT_AVAILABLE = "JOB_NOT_AVAILABLE"
    ARTIFACT_NOT_AVAILABLE = "JOB_ARTIFACT_NOT_AVAILABLE"
    INVALID_STATE = "JOB_SERVICE_INVALID_STATE"
    ANALYSIS_ADMISSION_REJECTED = "JOB_SERVICE_ANALYSIS_ADMISSION_REJECTED"
    ANALYSIS_ADMISSION_REUSED = "JOB_SERVICE_ANALYSIS_ADMISSION_REUSED"
    OPERATION_FAILED = "JOB_SERVICE_OPERATION_FAILED"


class JobServiceError(RuntimeError):
    """A content-free application-boundary rejection."""

    def __init__(self, code: JobServiceErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class JobServiceNotAvailableError(JobServiceError):
    """Common response for an unknown, malformed, or unauthorized job."""

    def __init__(self) -> None:
        super().__init__(JobServiceErrorCode.NOT_AVAILABLE)


class JobServiceAdmissionRejectedError(JobServiceError):
    """A session or capacity denial before allocation."""

    def __init__(self) -> None:
        super().__init__(JobServiceErrorCode.ADMISSION_REJECTED)


def _detach(error: JobServiceError) -> None:
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True


def _content_free[**P, T](method: Callable[P, T]) -> Callable[P, T]:
    @wraps(method)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return method(*args, **kwargs)
        except JobServiceError as error:
            rejection = error
        except JobNotAvailableError:
            rejection = JobServiceNotAvailableError()
        except JobAdmissionRejectedError:
            rejection = JobServiceAdmissionRejectedError()
        except AnalysisAdmissionRejectedError:
            rejection = JobServiceError(JobServiceErrorCode.ANALYSIS_ADMISSION_REJECTED)
        except AnalysisAdmissionReusedError:
            rejection = JobServiceError(JobServiceErrorCode.ANALYSIS_ADMISSION_REUSED)
        except Exception:
            rejection = JobServiceError(JobServiceErrorCode.OPERATION_FAILED)
        _detach(rejection)
        raise rejection

    return wrapped


def _default_operation_id() -> str:
    return "op_" + secrets.token_hex(32)


class JobService:
    """Compose store, workspace, artifact, and process operations safely."""

    @_content_free
    def __init__(
        self,
        *,
        store: SQLiteJobStore,
        workspaces: WorkspaceManager,
        clock: Clock,
        policy: JobPolicy = DEFAULT_JOB_POLICY,
        materializer: Materializer = materialize_validated_payloads,
        operation_id_factory: OperationIdFactory = _default_operation_id,
        process_gateway: ProcessGateway | None = None,
    ) -> None:
        process_valid = process_gateway is None or (
            callable(getattr(process_gateway, "start", None))
            and callable(getattr(process_gateway, "cancel", None))
        )
        if (
            not isinstance(store, SQLiteJobStore)
            or not isinstance(workspaces, WorkspaceManager)
            or not hasattr(clock, "now")
            or not isinstance(policy, JobPolicy)
            or not callable(materializer)
            or not callable(operation_id_factory)
            or not process_valid
        ):
            raise JobServiceError(JobServiceErrorCode.INVALID_CONFIGURATION)
        self._store = store
        self._workspaces = workspaces
        self._clock = clock
        self._policy = policy
        self._materializer = materializer
        self._operation_id_factory = operation_id_factory
        self._process_gateway = process_gateway

    @_content_free
    def admit(
        self,
        *,
        capability: SessionCapability,
        payloads: Sequence[ValidatedPayload],
        queued: bool = False,
    ) -> JobAdmission:
        """Admit and materialize one job, rolling back both surfaces on failure."""

        now = self._now()
        layout: WorkspaceLayout | None = None
        materialization: MaterializationReceipt | None = None
        staged: JobRecord | None = None
        try:
            with self._store.reserve_admission(
                capability=capability,
                at_utc=now,
                queued=queued,
            ) as reserved:
                staged = reserved
                try:
                    layout = self._workspaces.create(
                        reserved.owner_digest,
                        workspace_component(JobId.from_urlsafe(reserved.job_id)),
                    )
                    materialization = self._materializer(self._workspaces, layout, payloads)
                except Exception:
                    if layout is None:
                        raise
                    try:
                        self._workspaces.cleanup(layout)
                    except Exception:
                        raise JobAdmissionCleanupUnresolvedError from None
                    raise
        except Exception:
            if layout is not None:
                try:
                    self._workspaces.cleanup(layout)
                except Exception:
                    pass
            raise
        if staged is None or materialization is None:  # pragma: no cover - success invariant
            raise JobServiceError(JobServiceErrorCode.OPERATION_FAILED)
        committed = self._store.get_job(job_id=staged.job_id, capability=capability)
        return JobAdmission(job=committed, materialization=materialization)

    @_content_free
    def status(
        self,
        *,
        job_id: JobId | str,
        capability: SessionCapability,
    ) -> JobPresentation:
        """Project one owned job without opening its workspace."""

        return project_job_record(self._authorize(job_id=job_id, capability=capability))

    @_content_free
    def bind_analysis_admission(
        self,
        *,
        receipt_hmac: str,
        job_id: JobId | str,
        capability: SessionCapability,
        at_utc: datetime,
        expires_at_utc: datetime,
        expected_job_version: int,
    ) -> None:
        """Bind one READY authority without exposing the control store."""

        self._store.bind_analysis_admission(
            receipt_hmac=receipt_hmac,
            job_id=job_id,
            capability=capability,
            at_utc=at_utc,
            expires_at_utc=expires_at_utc,
            expected_job_version=expected_job_version,
        )

    @_content_free
    def consume_analysis_admission(
        self,
        *,
        receipt_hmac: str,
        job_id: JobId | str,
        capability: SessionCapability,
        at_utc: datetime,
        operation_id: str,
    ) -> JobPresentation:
        """Consume one READY authority and return its queued projection."""

        queued = self._store.consume_analysis_admission(
            receipt_hmac=receipt_hmac,
            job_id=job_id,
            capability=capability,
            at_utc=at_utc,
            operation_id=operation_id,
        )
        return project_job_record(queued)

    @_content_free
    def cancel(
        self,
        *,
        job_id: JobId | str,
        capability: SessionCapability,
    ) -> JobPresentation:
        """Persist an owned cancellation request before touching process control."""

        job = self._authorize(job_id=job_id, capability=capability)
        if job.cancellation.state is CancellationState.REQUESTED:
            self._deliver_cancellation(job)
            return project_job_record(job)
        now = self._now()
        updated = request_cancellation(
            job,
            at_utc=now,
            expected_version=job.version,
            operation_id=self._stable_operation_id(job, "cancel"),
        )
        try:
            saved = self._store.compare_and_swap(
                job_id=job.job_id,
                capability=capability,
                expected_version=job.version,
                updated=updated,
                at_utc=now,
            )
        except VersionConflictError:
            saved = self._authorize(job_id=job.job_id, capability=capability)
            if saved.cancellation.state is not CancellationState.REQUESTED:
                raise
        self._deliver_cancellation(saved)
        return project_job_record(saved)

    @_content_free
    def result(
        self,
        *,
        job_id: JobId | str,
        capability: SessionCapability,
    ) -> bytes:
        """Authorize result access while P006 artifact validation remains locked."""

        self._authorize(job_id=job_id, capability=capability)
        raise JobServiceError(JobServiceErrorCode.ARTIFACT_NOT_AVAILABLE)

    @_content_free
    def export(
        self,
        *,
        job_id: JobId | str,
        capability: SessionCapability,
    ) -> bytes:
        """Authorize export access while P006 artifact validation remains locked."""

        self._authorize(job_id=job_id, capability=capability)
        raise JobServiceError(JobServiceErrorCode.ARTIFACT_NOT_AVAILABLE)

    @_content_free
    def cleanup(
        self,
        *,
        job_id: JobId | str,
        capability: SessionCapability,
    ) -> CleanupReport:
        """Remove one owned staged or terminal workspace and persist absence."""

        job = self._authorize(job_id=job_id, capability=capability)
        now = self._now()
        if job.execution.state is ExecutionState.STAGED:
            terminal = transition_execution(
                job,
                target=ExecutionState.TERMINAL,
                outcome=TerminalOutcome.ABANDONED,
                at_utc=now,
                tombstone_expires_at_utc=now
                + timedelta(seconds=self._policy.tombstone_ttl_seconds),
                expected_version=job.version,
                operation_id=self._operation_id(),
            )
            job = self._store.compare_and_swap(
                job_id=job.job_id,
                capability=capability,
                expected_version=job.version,
                updated=terminal,
                at_utc=now,
            )
        elif job.execution.state is not ExecutionState.TERMINAL:
            raise JobServiceError(JobServiceErrorCode.INVALID_STATE)
        layout = self._layout(job)
        report = (
            CleanupReport(file_count=0, byte_count=0, already_absent=True)
            if layout is None
            else self._workspaces.cleanup(layout)
        )
        job = self._persist_verified_absence(
            job=job,
            capability=capability,
            at_utc=now,
        )
        event = new_deletion_event(
            job_id=JobId.from_urlsafe(job.job_id),
            occurred_at_utc=now,
            reason=DeletionReason.OWNER_REQUEST,
            file_count=report.file_count,
            byte_count=report.byte_count,
            policy_version=self._policy.profile_version,
            event_ttl_seconds=self._policy.event_ttl_seconds,
        )
        self._store.record_deletion_event(job_id=job.job_id, event=event, at_utc=now)
        return report

    @_content_free
    def start_next(self) -> JobPresentation | None:
        """Claim and launch one queued job; saturation touches no process surface."""

        if self._process_gateway is None:
            raise JobServiceError(JobServiceErrorCode.INVALID_CONFIGURATION)
        now = self._now()
        job = self._store.claim_next(at_utc=now, operation_id=self._operation_id())
        if job is None:
            return None
        layout: WorkspaceLayout | None = None
        try:
            layout = self._layout(job)
            if layout is None:
                raise JobServiceError(JobServiceErrorCode.OPERATION_FAILED)
            self._process_gateway.start(job, layout)
        except Exception:
            if layout is not None:
                try:
                    self._process_gateway.cancel(job)
                except Exception:
                    self._record_launch_cancellation(job, at_utc=now)
                    raise
            self._record_launch_failure(job, at_utc=now)
            raise
        return project_job_record(job)

    def _record_launch_failure(self, job: JobRecord, *, at_utc: datetime) -> JobRecord:
        terminal = transition_execution(
            job,
            target=ExecutionState.TERMINAL,
            outcome=TerminalOutcome.CRASHED,
            at_utc=at_utc,
            tombstone_expires_at_utc=at_utc + timedelta(seconds=self._policy.tombstone_ttl_seconds),
            expected_version=job.version,
            operation_id=self._stable_operation_id(job, "launch-failed"),
        )
        return self._store.maintenance_compare_and_swap(
            job_id=job.job_id,
            expected_version=job.version,
            updated=terminal,
            at_utc=at_utc,
        )

    def _record_launch_cancellation(self, job: JobRecord, *, at_utc: datetime) -> JobRecord:
        cancelling = request_cancellation(
            job,
            at_utc=at_utc,
            expected_version=job.version,
            operation_id=self._stable_operation_id(job, "launch-cancel"),
        )
        return self._store.maintenance_compare_and_swap(
            job_id=job.job_id,
            expected_version=job.version,
            updated=cancelling,
            at_utc=at_utc,
        )

    def _deliver_cancellation(self, job: JobRecord) -> None:
        if job.execution.state is ExecutionState.RUNNING and self._process_gateway is not None:
            self._process_gateway.cancel(job)

    def _authorize(
        self,
        *,
        job_id: JobId | str,
        capability: SessionCapability,
    ) -> JobRecord:
        return self._store.get_job(job_id=job_id, capability=capability)

    def _persist_verified_absence(
        self,
        *,
        job: JobRecord,
        capability: SessionCapability,
        at_utc: datetime,
    ) -> JobRecord:
        current = job
        if current.export_available:
            withdrawn = withdraw_export(
                current,
                at_utc=at_utc,
                expected_version=current.version,
                operation_id=self._operation_id(),
            )
            current = self._store.compare_and_swap(
                job_id=current.job_id,
                capability=capability,
                expected_version=current.version,
                updated=withdrawn,
                at_utc=at_utc,
            )
        for kind in ArtifactKind:
            while current.artifacts.for_kind(kind).state is not CleanupState.VERIFIED_ABSENT:
                artifact = current.artifacts.for_kind(kind)
                target = (
                    CleanupState.IN_PROGRESS
                    if artifact.state in {CleanupState.PENDING, CleanupState.FAILED}
                    else CleanupState.VERIFIED_ABSENT
                )
                updated = transition_artifact(
                    current,
                    kind=kind,
                    target=target,
                    at_utc=at_utc,
                    expected_version=current.version,
                    operation_id=self._operation_id(),
                    delete_by_utc=(
                        artifact.delete_by_utc if target is CleanupState.IN_PROGRESS else None
                    ),
                )
                current = self._store.compare_and_swap(
                    job_id=current.job_id,
                    capability=capability,
                    expected_version=current.version,
                    updated=updated,
                    at_utc=at_utc,
                )
        return current

    def _layout(self, job: JobRecord) -> WorkspaceLayout | None:
        parsed = JobId.from_urlsafe(job.job_id)
        return self._workspaces.load_optional(job.owner_digest, workspace_component(parsed))

    def _operation_id(self) -> str:
        value = self._operation_id_factory()
        if not isinstance(value, str):
            raise JobServiceError(JobServiceErrorCode.OPERATION_FAILED)
        return value

    @staticmethod
    def _stable_operation_id(job: JobRecord, action: str) -> str:
        material = b"delta-lemmata\x00job-service\x00v1\x00" + action.encode("ascii")
        material += b"\x00" + job.job_id.encode("ascii")
        return "op_" + hashlib.sha256(material).hexdigest()

    def _now(self) -> datetime:
        return require_utc(self._clock.now(), field_name="clock.now")


__all__ = [
    "JobAdmission",
    "JobService",
    "JobServiceAdmissionRejectedError",
    "JobServiceError",
    "JobServiceErrorCode",
    "JobServiceNotAvailableError",
    "Materializer",
    "OperationIdFactory",
    "ProcessGateway",
]
