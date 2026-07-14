"""Ordered durable handoff from one fixed stylo worker to the P005 lifecycle."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import timedelta

from delta_lemmata.clock import Clock, require_utc
from delta_lemmata.guardian_controller import GuardianArtifactBinding, GuardianController
from delta_lemmata.job_models import (
    ExecutionState,
    JobRecord,
    ScientificResultReceipt,
    transition_execution,
    transition_scientific_execution_claim,
    transition_scientific_success,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY, STYLO_WORKER_LIMITS, JobPolicy
from delta_lemmata.job_store import SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceLayout, WorkspaceManager
from delta_lemmata.process_controller import ProcessEnvironmentProfile
from delta_lemmata.recovery_receipt import RecoveryReceiptStore
from delta_lemmata.session_identity import JobId, workspace_component
from delta_lemmata.stylo_contracts import RESULT_MAX_BYTES, WorkerInputV1
from delta_lemmata.stylo_worker import (
    RESULT_COMPONENT,
    STYLO_WORKER_ARGV,
    StyloWorkerAdapter,
)

OperationIdFactory = Callable[[], str]


def _default_operation_id() -> str:
    return "op_" + secrets.token_hex(32)


class StyloJobRunner:
    """Claim, run, validate, persist, and acknowledge one P006 job."""

    def __init__(
        self,
        *,
        store: SQLiteJobStore,
        workspaces: WorkspaceManager,
        receipts: RecoveryReceiptStore,
        clock: Clock,
        policy: JobPolicy = DEFAULT_JOB_POLICY,
        operation_id_factory: OperationIdFactory = _default_operation_id,
    ) -> None:
        if (
            not isinstance(store, SQLiteJobStore)
            or not isinstance(workspaces, WorkspaceManager)
            or not isinstance(receipts, RecoveryReceiptStore)
            or not hasattr(clock, "now")
            or not isinstance(policy, JobPolicy)
            or not callable(operation_id_factory)
        ):
            raise ValueError("STYLO_JOB_RUNNER_INVALID_CONFIGURATION")
        self._store = store
        self._workspaces = workspaces
        self._receipts = receipts
        self._clock = clock
        self._policy = policy
        self._operation_id_factory = operation_id_factory

    def run(
        self,
        *,
        job: JobRecord,
        layout: WorkspaceLayout,
        request: WorkerInputV1,
    ) -> JobRecord:
        """Apply the AC-03 order without opening the public P008 workflow."""

        execution_reference = self._execution_reference(job)
        self._require_layout(job, layout)
        claim_at = require_utc(self._clock.now(), field_name="clock.now")
        claim = transition_scientific_execution_claim(
            job,
            expected_version=job.version,
            operation_id=self._operation_id(),
        )
        claimed = self._store.maintenance_compare_and_swap(
            job_id=job.job_id,
            expected_version=job.version,
            updated=claim,
            at_utc=claim_at,
        )
        adapter = StyloWorkerAdapter(self._workspaces, layout)
        adapter.prepare(request)
        guardian = GuardianController(
            argv=STYLO_WORKER_ARGV,
            cwd=layout.work,
            limits=STYLO_WORKER_LIMITS,
            job_id=JobId.from_urlsafe(job.job_id),
            execution_reference=execution_reference,
            store=self._store,
            workspace_root=self._workspaces.root,
            owner_component=job.owner_digest,
            job_component=workspace_component(JobId.from_urlsafe(job.job_id)),
            receipt_store=self._receipts,
            artifact_binding=GuardianArtifactBinding(
                component=RESULT_COMPONENT,
                maximum_bytes=RESULT_MAX_BYTES,
            ),
            environment_profile=ProcessEnvironmentProfile.R_STYLO,
        )
        guardian.start()
        process = guardian.wait()
        execution = adapter.capture(request, process)
        receipt: ScientificResultReceipt | None = None
        if execution.accepted_result:
            receipt = adapter.publish_validated_result(request, execution)
        now = require_utc(self._clock.now(), field_name="clock.now")
        tombstone = now + timedelta(seconds=self._policy.tombstone_ttl_seconds)
        if receipt is None:
            terminal = transition_execution(
                claimed,
                target=ExecutionState.TERMINAL,
                outcome=execution.finalization.terminal_outcome,
                at_utc=now,
                tombstone_expires_at_utc=tombstone,
                expected_version=claimed.version,
                operation_id=self._operation_id(),
            )
        else:
            terminal = transition_scientific_success(
                claimed,
                receipt=receipt,
                at_utc=now,
                tombstone_expires_at_utc=tombstone,
                expected_version=claimed.version,
                operation_id=self._operation_id(),
            )
        saved = self._store.maintenance_compare_and_swap(
            job_id=claimed.job_id,
            expected_version=claimed.version,
            updated=terminal,
            at_utc=now,
        )
        guardian.acknowledge_terminal_persisted(
            expected_version=saved.version,
            expected_outcome=execution.finalization.terminal_outcome,
            expected_result=receipt,
        )
        if receipt is None:
            return saved
        confirmed_at = require_utc(self._clock.now(), field_name="clock.now")
        return self._store.confirm_scientific_result_after_guardian(
            job_id=saved.job_id,
            expected_terminal_version=saved.version,
            expected_result=receipt,
            operation_id=self._operation_id(),
            at_utc=confirmed_at,
        )

    @staticmethod
    def _execution_reference(job: JobRecord) -> str:
        references = tuple(
            operation.operation_id
            for operation in job.operations
            if operation.action == "execution:running:none"
        )
        if job.execution.state is not ExecutionState.RUNNING or len(references) != 1:
            raise ValueError("STYLO_JOB_RUNNER_INVALID_JOB")
        return references[0]

    def _require_layout(self, job: JobRecord, layout: WorkspaceLayout) -> None:
        expected = self._workspaces.load_optional(
            job.owner_digest,
            workspace_component(JobId.from_urlsafe(job.job_id)),
        )
        if expected != layout:
            raise ValueError("STYLO_JOB_RUNNER_INVALID_LAYOUT")
        self._workspaces.verify(layout)

    def _operation_id(self) -> str:
        value = self._operation_id_factory()
        if not isinstance(value, str):
            raise ValueError("STYLO_JOB_RUNNER_INVALID_OPERATION")
        return value


__all__ = ["OperationIdFactory", "StyloJobRunner"]
