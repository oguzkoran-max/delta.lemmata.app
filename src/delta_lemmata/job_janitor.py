"""Deadline-driven cleanup and restart reconciliation for ephemeral jobs."""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from delta_lemmata.clock import Clock, require_utc
from delta_lemmata.job_events import DeletionReason, new_deletion_event
from delta_lemmata.job_models import (
    ArtifactKind,
    CleanupState,
    ExecutionState,
    JobRecord,
    TerminalOutcome,
    VersionConflictError,
    publish_export,
    retire_export,
    transition_artifact,
    transition_execution,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY, JobPolicy
from delta_lemmata.job_store import (
    JobNotAvailableError,
    SQLiteJobStore,
    StorePurgeReport,
)
from delta_lemmata.job_workspace import (
    CleanupReport,
    WorkspaceArea,
    WorkspaceError,
    WorkspaceLayout,
    WorkspaceManager,
)
from delta_lemmata.session_identity import JobId, workspace_component

RunningRecovery = Callable[[JobRecord], bool]

_OPERATION_DOMAIN = b"delta-lemmata\x00janitor-operation\x00v1\x00"


@dataclass(frozen=True, slots=True)
class JanitorRunReport:
    """Content-free counters from one deterministic maintenance pass."""

    jobs_scanned: int
    waiting_jobs_expired: int
    running_jobs_recovered: int
    running_recovery_unresolved: int
    cleanup_attempts: int
    cleanup_failures: int
    state_conflicts: int
    artifacts_verified_absent: int
    exports_published: int
    workspaces_removed: int
    deletion_events_recorded: int
    purge: StorePurgeReport
    untracked_workspaces_removed: int = 0


def _operation_id(job: JobRecord, action: str, at_utc: datetime) -> str:
    material = b"\x00".join(
        (
            job.job_id.encode("ascii"),
            str(job.version).encode("ascii"),
            action.encode("ascii"),
            at_utc.isoformat().encode("ascii"),
        )
    )
    return "op_" + hashlib.sha256(_OPERATION_DOMAIN + material).hexdigest()


class JobJanitor:
    """Reconcile expired jobs and artifact deadlines without retaining payloads."""

    def __init__(
        self,
        *,
        store: SQLiteJobStore,
        workspaces: WorkspaceManager,
        clock: Clock,
        policy: JobPolicy = DEFAULT_JOB_POLICY,
    ) -> None:
        if (
            not isinstance(store, SQLiteJobStore)
            or not isinstance(workspaces, WorkspaceManager)
            or not hasattr(clock, "now")
            or not isinstance(policy, JobPolicy)
        ):
            raise ValueError("JOB_JANITOR_INVALID_CONFIGURATION")
        self._store = store
        self._workspaces = workspaces
        self._clock = clock
        self._policy = policy

    def run_once(self) -> JanitorRunReport:
        """Apply every deadline due at the current clock instant exactly once."""

        return self._run_at(
            require_utc(self._clock.now(), field_name="clock.now"),
            running_jobs_recovered=0,
            running_recovery_unresolved=0,
            reason_overrides={},
        )

    def recover_startup(
        self,
        recovery: RunningRecovery | None = None,
    ) -> JanitorRunReport:
        """Reconcile running rows only after an external guardian proves them stopped."""

        if recovery is not None and not callable(recovery):
            raise ValueError("JOB_JANITOR_INVALID_RECOVERY")
        now = require_utc(self._clock.now(), field_name="clock.now")
        orphan_attempts, orphan_removed, orphan_failures = self._reconcile_untracked_workspaces()
        recovered = 0
        unresolved = 0
        conflicts = 0
        reason_overrides: dict[str, DeletionReason] = {}
        for job in self._store.list_jobs_for_maintenance():
            if job.execution.state is not ExecutionState.RUNNING:
                continue
            try:
                stopped = False if recovery is None else bool(recovery(job))
            except Exception:
                stopped = False
            if not stopped:
                unresolved += 1
                continue
            updated = transition_execution(
                job,
                target=ExecutionState.TERMINAL,
                outcome=TerminalOutcome.ABANDONED,
                at_utc=now,
                tombstone_expires_at_utc=now
                + timedelta(seconds=self._policy.tombstone_ttl_seconds),
                expected_version=job.version,
                operation_id=_operation_id(job, "startup:abandon", now),
            )
            try:
                self._store.maintenance_compare_and_swap(
                    job_id=job.job_id,
                    expected_version=job.version,
                    updated=updated,
                    at_utc=now,
                )
            except (VersionConflictError, JobNotAvailableError):
                conflicts += 1
                continue
            recovered += 1
            reason_overrides[job.job_id] = DeletionReason.STARTUP_RECOVERY
        report = self._run_at(
            now,
            running_jobs_recovered=recovered,
            running_recovery_unresolved=unresolved,
            reason_overrides=reason_overrides,
        )
        return replace(
            report,
            cleanup_attempts=report.cleanup_attempts + orphan_attempts,
            cleanup_failures=report.cleanup_failures + orphan_failures,
            state_conflicts=report.state_conflicts + conflicts,
            workspaces_removed=report.workspaces_removed + orphan_removed,
            untracked_workspaces_removed=orphan_removed,
        )

    def run_continuously(
        self,
        *,
        stop_event: threading.Event,
        interval_seconds: float,
    ) -> None:
        """Run maintenance until the caller signals shutdown."""

        if not isinstance(stop_event, threading.Event) or interval_seconds <= 0:
            raise ValueError("JOB_JANITOR_INVALID_LOOP")
        while not stop_event.is_set():
            self.run_once()
            stop_event.wait(interval_seconds)

    def _reconcile_untracked_workspaces(self) -> tuple[int, int, int]:
        known = {
            (job.owner_digest, workspace_component(JobId.from_urlsafe(job.job_id)))
            for job in self._store.list_jobs_for_maintenance()
        }
        attempts = 0
        removed = 0
        failures = 0
        for layout in self._workspaces.list_layouts():
            identity = (layout.owner.name, layout.job.name)
            if identity in known:
                continue
            attempts += 1
            try:
                self._workspaces.cleanup(layout)
            except WorkspaceError:
                failures += 1
            else:
                removed += 1
        return attempts, removed, failures

    def _run_at(
        self,
        now: datetime,
        *,
        running_jobs_recovered: int,
        running_recovery_unresolved: int,
        reason_overrides: dict[str, DeletionReason],
    ) -> JanitorRunReport:
        counters = {
            "waiting_jobs_expired": 0,
            "cleanup_attempts": 0,
            "cleanup_failures": 0,
            "state_conflicts": 0,
            "artifacts_verified_absent": 0,
            "exports_published": 0,
            "workspaces_removed": 0,
            "deletion_events_recorded": 0,
        }
        jobs = self._store.list_jobs_for_maintenance()
        workspace_absent: set[str] = set()
        for snapshot in jobs:
            job = snapshot
            try:
                if job.execution.state in {ExecutionState.STAGED, ExecutionState.QUEUED}:
                    deadline = job.execution.deadline_at_utc
                    if deadline is not None and deadline <= now:
                        source = job.execution.state
                        expired = transition_execution(
                            job,
                            target=ExecutionState.TERMINAL,
                            outcome=TerminalOutcome.EXPIRED,
                            at_utc=now,
                            tombstone_expires_at_utc=now
                            + timedelta(seconds=self._policy.tombstone_ttl_seconds),
                            expected_version=job.version,
                            operation_id=_operation_id(job, "waiting:expire", now),
                        )
                        job = self._store.maintenance_compare_and_swap(
                            job_id=job.job_id,
                            expected_version=job.version,
                            updated=expired,
                            at_utc=now,
                        )
                        counters["waiting_jobs_expired"] += 1
                        reason_overrides[job.job_id] = (
                            DeletionReason.STAGED_EXPIRED
                            if source is ExecutionState.STAGED
                            else DeletionReason.QUEUE_EXPIRED
                        )
                if job.execution.state is ExecutionState.TERMINAL:
                    reason = reason_overrides.get(job.job_id)
                    job = self._maintain_terminal(job, now, reason, counters)
                    if self._layout(job) is None:
                        workspace_absent.add(job.job_id)
            except WorkspaceError:
                counters["cleanup_failures"] += 1
            except (VersionConflictError, JobNotAvailableError):
                counters["state_conflicts"] += 1
        purge = self._store.purge_expired(
            at_utc=now,
            workspace_absent_job_ids=frozenset(workspace_absent),
        )
        return JanitorRunReport(
            jobs_scanned=len(jobs),
            waiting_jobs_expired=counters["waiting_jobs_expired"],
            running_jobs_recovered=running_jobs_recovered,
            running_recovery_unresolved=running_recovery_unresolved,
            cleanup_attempts=counters["cleanup_attempts"],
            cleanup_failures=counters["cleanup_failures"],
            state_conflicts=counters["state_conflicts"],
            artifacts_verified_absent=counters["artifacts_verified_absent"],
            exports_published=counters["exports_published"],
            workspaces_removed=counters["workspaces_removed"],
            deletion_events_recorded=counters["deletion_events_recorded"],
            purge=purge,
        )

    def _maintain_terminal(
        self,
        job: JobRecord,
        now: datetime,
        reason: DeletionReason | None,
        counters: dict[str, int],
    ) -> JobRecord:
        if job.outcome is None:
            return job
        if job.outcome.kind is not TerminalOutcome.SUCCEEDED:
            return self._cleanup_unsuccessful(
                job,
                now,
                reason or self._unsuccessful_reason(job),
                counters,
            )
        return self._cleanup_success(job, now, counters)

    @staticmethod
    def _unsuccessful_reason(job: JobRecord) -> DeletionReason:
        if job.outcome is not None and job.outcome.kind is TerminalOutcome.EXPIRED:
            queued = any(
                operation.action == "execution:queued:none" for operation in job.operations
            )
            return DeletionReason.QUEUE_EXPIRED if queued else DeletionReason.STAGED_EXPIRED
        return DeletionReason.UNSUCCESSFUL_TERMINAL

    def _cleanup_unsuccessful(
        self,
        job: JobRecord,
        now: datetime,
        reason: DeletionReason,
        counters: dict[str, int],
    ) -> JobRecord:
        layout = self._layout(job)
        needs_verification = any(
            job.artifacts.for_kind(kind).state is not CleanupState.VERIFIED_ABSENT
            for kind in ArtifactKind
        )
        if layout is None and not needs_verification:
            return job
        counters["cleanup_attempts"] += 1
        report = CleanupReport(0, 0, True) if layout is None else self._workspaces.cleanup(layout)
        self._record_deletion(job, report, reason, now, counters)
        return self._verify_artifacts(
            job,
            tuple(ArtifactKind),
            now,
            counters,
            verify_not_created=True,
        )

    def _cleanup_success(
        self,
        job: JobRecord,
        now: datetime,
        counters: dict[str, int],
    ) -> JobRecord:
        if any(
            job.artifacts.for_kind(kind).state is not CleanupState.VERIFIED_ABSENT
            for kind in (ArtifactKind.INPUT, ArtifactKind.WORK)
        ):
            report = self._clear_areas(job, (WorkspaceArea.INPUT, WorkspaceArea.WORK))
            counters["cleanup_attempts"] += 1
            self._record_deletion(
                job,
                report,
                DeletionReason.SUCCESSFUL_TERMINAL,
                now,
                counters,
            )
            job = self._verify_artifacts(
                job,
                (ArtifactKind.INPUT, ArtifactKind.WORK),
                now,
                counters,
                verify_not_created=True,
            )

        result = job.artifacts.result
        if (
            result.state not in {CleanupState.NOT_CREATED, CleanupState.VERIFIED_ABSENT}
            and result.delete_by_utc is not None
            and result.delete_by_utc <= now
        ):
            report = self._clear_areas(job, (WorkspaceArea.RESULT,))
            counters["cleanup_attempts"] += 1
            self._record_deletion(
                job,
                report,
                DeletionReason.RESULT_EXPIRED,
                now,
                counters,
            )
            job = self._verify_artifacts(
                job,
                (ArtifactKind.RESULT,),
                now,
                counters,
                verify_not_created=False,
            )

        export = job.artifacts.export
        export_due = (
            export.state not in {CleanupState.NOT_CREATED, CleanupState.VERIFIED_ABSENT}
            and export.delete_by_utc is not None
            and export.delete_by_utc <= now
        )
        if export_due:
            report = self._clear_areas(job, (WorkspaceArea.EXPORT,))
            counters["cleanup_attempts"] += 1
            self._record_deletion(
                job,
                report,
                DeletionReason.EXPORT_EXPIRED,
                now,
                counters,
            )
            if job.export_available:
                retired = retire_export(
                    job,
                    at_utc=now,
                    expected_version=job.version,
                    operation_id=_operation_id(job, "export:retire", now),
                )
                job = self._store.maintenance_compare_and_swap(
                    job_id=job.job_id,
                    expected_version=job.version,
                    updated=retired,
                    at_utc=now,
                )
                counters["artifacts_verified_absent"] += 1
            else:
                job = self._verify_artifacts(
                    job,
                    (ArtifactKind.EXPORT,),
                    now,
                    counters,
                    verify_not_created=False,
                )
        elif not job.export_available and job.can_publish_export:
            published = publish_export(
                job,
                expected_version=job.version,
                operation_id=_operation_id(job, "export:publish", now),
            )
            job = self._store.maintenance_compare_and_swap(
                job_id=job.job_id,
                expected_version=job.version,
                updated=published,
                at_utc=now,
            )
            counters["exports_published"] += 1

        retained = any(
            job.artifacts.for_kind(kind).state
            not in {CleanupState.NOT_CREATED, CleanupState.VERIFIED_ABSENT}
            for kind in ArtifactKind
        )
        if not retained and not job.export_available:
            layout = self._layout(job)
            if layout is not None:
                counters["cleanup_attempts"] += 1
                report = self._workspaces.cleanup(layout)
                counters["workspaces_removed"] += 1
                if report.file_count:
                    self._record_deletion(
                        job,
                        report,
                        DeletionReason.SUCCESSFUL_TERMINAL,
                        now,
                        counters,
                    )
        return job

    def _verify_artifacts(
        self,
        job: JobRecord,
        kinds: tuple[ArtifactKind, ...],
        now: datetime,
        counters: dict[str, int],
        *,
        verify_not_created: bool,
    ) -> JobRecord:
        for kind in kinds:
            while True:
                current = job.artifacts.for_kind(kind)
                if current.state is CleanupState.VERIFIED_ABSENT or (
                    current.state is CleanupState.NOT_CREATED and not verify_not_created
                ):
                    break
                target = (
                    CleanupState.IN_PROGRESS
                    if current.state in {CleanupState.PENDING, CleanupState.FAILED}
                    else CleanupState.VERIFIED_ABSENT
                )
                updated = transition_artifact(
                    job,
                    kind=kind,
                    target=target,
                    at_utc=now,
                    delete_by_utc=(
                        current.delete_by_utc if target is CleanupState.IN_PROGRESS else None
                    ),
                    expected_version=job.version,
                    operation_id=_operation_id(
                        job,
                        f"artifact:{kind.value}:{target.value}",
                        now,
                    ),
                )
                job = self._store.maintenance_compare_and_swap(
                    job_id=job.job_id,
                    expected_version=job.version,
                    updated=updated,
                    at_utc=now,
                )
                if target is CleanupState.VERIFIED_ABSENT:
                    counters["artifacts_verified_absent"] += 1
        return job

    def _record_deletion(
        self,
        job: JobRecord,
        report: CleanupReport,
        reason: DeletionReason,
        now: datetime,
        counters: dict[str, int],
    ) -> None:
        event = new_deletion_event(
            job_id=JobId.from_urlsafe(job.job_id),
            occurred_at_utc=now,
            reason=reason,
            file_count=report.file_count,
            byte_count=report.byte_count,
            policy_version="job-policy-v1",
            event_ttl_seconds=self._policy.event_ttl_seconds,
        )
        if self._store.record_deletion_event(job_id=job.job_id, event=event, at_utc=now):
            counters["deletion_events_recorded"] += 1

    def _clear_areas(
        self,
        job: JobRecord,
        areas: tuple[WorkspaceArea, ...],
    ) -> CleanupReport:
        layout = self._layout(job)
        if layout is None:
            return CleanupReport(0, 0, True)
        return self._workspaces.clear_areas(layout, areas)

    def _layout(self, job: JobRecord) -> WorkspaceLayout | None:
        job_id = JobId.from_urlsafe(job.job_id)
        return self._workspaces.load_optional(job.owner_digest, workspace_component(job_id))


__all__ = ["JanitorRunReport", "JobJanitor", "RunningRecovery"]
