from __future__ import annotations

import hashlib
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

import delta_lemmata.stylo_job_runner as runner_module
from delta_lemmata.clock import FakeClock
from delta_lemmata.guardian_controller import GuardianArtifactBinding
from delta_lemmata.job_models import (
    ArtifactKind,
    CleanupState,
    ExecutionState,
    JobRecord,
    ScientificResultReceipt,
    TerminalOutcome,
    VersionConflictError,
    transition_artifact,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY, STYLO_WORKER_LIMITS
from delta_lemmata.job_store import JobStoreError, JobStoreErrorCode, SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceArea, WorkspaceLayout, WorkspaceManager
from delta_lemmata.process_controller import (
    ProcessEnvironmentProfile,
    ProcessOutcome,
    ProcessResult,
)
from delta_lemmata.recovery_receipt import RecoveryReceiptStore
from delta_lemmata.scientific_finalizer import (
    ScientificFinalization,
    ScientificFinalizationCode,
)
from delta_lemmata.session_identity import JobId, SessionCapability, workspace_component
from delta_lemmata.stylo_contracts import (
    RESULT_MAX_BYTES,
    AnalysisOutcome,
    WorkerInputV1,
    canonical_worker_json,
    parse_worker_input,
)
from delta_lemmata.stylo_job_runner import StyloJobRunner
from delta_lemmata.stylo_worker import (
    RESULT_COMPONENT,
    STYLO_WORKER_ARGV,
    StyloWorkerExecution,
)

ROOT = Path(__file__).resolve().parents[1]
REQUEST_FIXTURE = (
    ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v2" / "normalization-base.input.json"
)
NOW = datetime(2026, 7, 14, 8, 0, tzinfo=UTC)
OWNER_SECRET = b"stylo-runner-owner-secret-v1-32bytes"
RECEIPT_SECRET = b"stylo-runner-receipt-v1-32bytes!!"


def operation(number: int) -> str:
    return "op_" + f"{number:064x}"


def operation_factory(*numbers: int) -> Any:
    values = iter(numbers)
    return lambda: operation(next(values))


def fixed_job() -> JobId:
    return JobId.generate(lambda size: b"j" * size)


@pytest.fixture
def environment(
    tmp_path: Path,
) -> tuple[
    SQLiteJobStore,
    WorkspaceManager,
    RecoveryReceiptStore,
    FakeClock,
    JobRecord,
    JobRecord,
    WorkspaceLayout,
    WorkerInputV1,
]:
    database_root = tmp_path / "database"
    workspace_root = tmp_path / "workspaces"
    receipt_root = tmp_path / "receipts"
    for root in (database_root, workspace_root, receipt_root):
        root.mkdir(mode=0o700)
    job_id = fixed_job()
    capability = SessionCapability.generate(lambda size: b"c" * size)
    store = SQLiteJobStore(
        database_root / "control.sqlite3",
        owner_secret=OWNER_SECRET,
        job_id_factory=lambda: job_id,
    )
    staged = store.stage_job(capability=capability, at_utc=NOW)
    store.enqueue_job(
        job_id=staged.job_id,
        capability=capability,
        at_utc=NOW + timedelta(microseconds=1),
        expected_version=staged.version,
        operation_id=operation(1),
    )
    running = store.claim_next(
        at_utc=NOW + timedelta(microseconds=2),
        operation_id=operation(2),
    )
    assert running is not None
    workspaces = WorkspaceManager(workspace_root)
    layout = workspaces.create(running.owner_digest, workspace_component(job_id))
    receipts = RecoveryReceiptStore(receipt_root, signing_secret=RECEIPT_SECRET)
    request = parse_worker_input(REQUEST_FIXTURE.read_bytes())
    return (
        store,
        workspaces,
        receipts,
        FakeClock(NOW + timedelta(seconds=1)),
        staged,
        running,
        layout,
        request,
    )


def scientific_receipt(request: WorkerInputV1) -> ScientificResultReceipt:
    payload = b'{"trusted":"result"}\n'
    return ScientificResultReceipt(
        schema_version="scientific-result-receipt-v1",
        request_id=request.request_id,
        request_sha256=hashlib.sha256(canonical_worker_json(request)).hexdigest(),
        worker_version="stylo-worker-v1",
        result_schema_version="stylo-worker-result-v1",
        analysis_outcome="complete",
        artifact_component=RESULT_COMPONENT,
        byte_size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def execution(
    *,
    outcome: TerminalOutcome,
    code: ScientificFinalizationCode,
) -> StyloWorkerExecution:
    return StyloWorkerExecution(
        finalization=ScientificFinalization(
            process=ProcessResult(ProcessOutcome.SUCCEEDED),
            terminal_outcome=outcome,
            code=code,
            analysis_outcome=(
                AnalysisOutcome.COMPLETE if outcome is TerminalOutcome.SUCCEEDED else None
            ),
        ),
        artifacts=(),
    )


def install_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    store: SQLiteJobStore,
    worker_execution: StyloWorkerExecution,
    receipt: ScientificResultReceipt | None,
    before_guardian_ack: Callable[[], None] | None = None,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[str] = []
    adapter_configurations: list[dict[str, Any]] = []
    guardian_configurations: list[dict[str, Any]] = []

    class FakeAdapter:
        def __init__(self, manager: WorkspaceManager, layout: WorkspaceLayout) -> None:
            adapter_configurations.append({"manager": manager, "layout": layout})
            events.append("adapter:init")

        def prepare(self, request: WorkerInputV1) -> None:
            assert isinstance(request, WorkerInputV1)
            events.append("adapter:prepare")

        def capture(
            self,
            request: WorkerInputV1,
            process: ProcessResult,
        ) -> StyloWorkerExecution:
            assert isinstance(request, WorkerInputV1)
            assert process == ProcessResult(ProcessOutcome.SUCCEEDED)
            events.append("adapter:capture")
            return worker_execution

        def publish_validated_result(
            self,
            request: WorkerInputV1,
            captured: StyloWorkerExecution,
        ) -> ScientificResultReceipt:
            assert isinstance(request, WorkerInputV1)
            assert captured is worker_execution
            assert receipt is not None
            events.append("adapter:publish")
            return receipt

    class FakeGuardian:
        def __init__(self, **configuration: Any) -> None:
            guardian_configurations.append(configuration)
            events.append("guardian:init")

        def start(self) -> None:
            events.append("guardian:start")

        def wait(self) -> ProcessResult:
            events.append("guardian:wait")
            return ProcessResult(ProcessOutcome.SUCCEEDED)

        def acknowledge_terminal_persisted(
            self,
            *,
            expected_version: int,
            expected_outcome: TerminalOutcome,
            expected_result: ScientificResultReceipt | None,
        ) -> None:
            if before_guardian_ack is not None:
                before_guardian_ack()
            persisted = next(
                job
                for job in store.list_jobs_for_maintenance()
                if job.execution.state is ExecutionState.TERMINAL
            )
            assert persisted.outcome is not None
            assert persisted.outcome.kind is expected_outcome
            assert persisted.scientific_result == expected_result
            assert store.terminal_transition_matches(
                job_id=persisted.job_id,
                execution_reference=operation(2),
                expected_version=expected_version,
                expected_outcome=expected_outcome,
                expected_result=expected_result,
            )
            events.append("guardian:ack")

    monkeypatch.setattr(runner_module, "StyloWorkerAdapter", FakeAdapter)
    monkeypatch.setattr(runner_module, "GuardianController", FakeGuardian)
    return events, adapter_configurations, guardian_configurations


def test_runner_persists_validated_result_before_guardian_ack(
    environment: tuple[
        SQLiteJobStore,
        WorkspaceManager,
        RecoveryReceiptStore,
        FakeClock,
        JobRecord,
        JobRecord,
        WorkspaceLayout,
        WorkerInputV1,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, workspaces, receipts, clock, _staged, running, layout, request = environment
    receipt = scientific_receipt(request)
    worker_execution = execution(
        outcome=TerminalOutcome.SUCCEEDED,
        code=ScientificFinalizationCode.RESULT_COMPLETE,
    )
    events, adapter_configs, guardian_configs = install_fakes(
        monkeypatch,
        store=store,
        worker_execution=worker_execution,
        receipt=receipt,
    )
    runner = StyloJobRunner(
        store=store,
        workspaces=workspaces,
        receipts=receipts,
        clock=clock,
        operation_id_factory=operation_factory(3, 4, 5),
    )

    original_compare_and_swap = store.maintenance_compare_and_swap
    original_confirmation = store.confirm_scientific_result_after_guardian

    def tracked_compare_and_swap(**kwargs: Any) -> JobRecord:
        updated = cast(JobRecord, kwargs["updated"])
        action = updated.operations[-1].action
        if action == "scientific:execution:claimed":
            events.append("store:claim")
        elif action.startswith("scientific:terminal:succeeded:"):
            events.append("store:terminal")
        return original_compare_and_swap(**kwargs)

    def tracked_confirmation(**kwargs: Any) -> JobRecord:
        events.append("store:confirm")
        return original_confirmation(**kwargs)

    monkeypatch.setattr(store, "maintenance_compare_and_swap", tracked_compare_and_swap)
    monkeypatch.setattr(
        store,
        "confirm_scientific_result_after_guardian",
        tracked_confirmation,
    )

    saved = runner.run(job=running, layout=layout, request=request)

    assert events == [
        "store:claim",
        "adapter:init",
        "adapter:prepare",
        "guardian:init",
        "guardian:start",
        "guardian:wait",
        "adapter:capture",
        "adapter:publish",
        "store:terminal",
        "guardian:ack",
        "store:confirm",
    ]
    assert adapter_configs == [{"manager": workspaces, "layout": layout}]
    assert guardian_configs == [
        {
            "argv": STYLO_WORKER_ARGV,
            "cwd": layout.work,
            "limits": STYLO_WORKER_LIMITS,
            "job_id": fixed_job(),
            "execution_reference": operation(2),
            "store": store,
            "workspace_root": workspaces.root,
            "owner_component": running.owner_digest,
            "job_component": workspace_component(fixed_job()),
            "receipt_store": receipts,
            "artifact_binding": GuardianArtifactBinding(
                component=RESULT_COMPONENT,
                maximum_bytes=RESULT_MAX_BYTES,
            ),
            "environment_profile": ProcessEnvironmentProfile.R_STYLO,
        }
    ]
    assert saved.execution.state is ExecutionState.TERMINAL
    assert saved.outcome is not None
    assert saved.outcome.kind is TerminalOutcome.SUCCEEDED
    assert saved.scientific_result == receipt
    assert saved.scientific_result_confirmed is True
    assert saved.artifacts.result.state is CleanupState.PRESENT


def test_runner_confirms_after_janitor_advances_the_terminal_row(
    environment: tuple[
        SQLiteJobStore,
        WorkspaceManager,
        RecoveryReceiptStore,
        FakeClock,
        JobRecord,
        JobRecord,
        WorkspaceLayout,
        WorkerInputV1,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, workspaces, receipts, clock, _staged, running, layout, request = environment
    receipt = scientific_receipt(request)
    worker_execution = execution(
        outcome=TerminalOutcome.SUCCEEDED,
        code=ScientificFinalizationCode.RESULT_COMPLETE,
    )

    def advance_terminal_row() -> None:
        terminal = next(
            job
            for job in store.list_jobs_for_maintenance()
            if job.execution.state is ExecutionState.TERMINAL
        )
        cleaned = transition_artifact(
            terminal,
            kind=ArtifactKind.INPUT,
            target=CleanupState.VERIFIED_ABSENT,
            at_utc=NOW + timedelta(seconds=1, microseconds=1),
            expected_version=terminal.version,
            operation_id=operation(90),
        )
        store.maintenance_compare_and_swap(
            job_id=terminal.job_id,
            expected_version=terminal.version,
            updated=cleaned,
            at_utc=NOW + timedelta(seconds=1, microseconds=1),
        )

    events, _adapter_configs, _guardian_configs = install_fakes(
        monkeypatch,
        store=store,
        worker_execution=worker_execution,
        receipt=receipt,
        before_guardian_ack=advance_terminal_row,
    )
    runner = StyloJobRunner(
        store=store,
        workspaces=workspaces,
        receipts=receipts,
        clock=clock,
        operation_id_factory=operation_factory(3, 4, 5),
    )

    saved = runner.run(job=running, layout=layout, request=request)

    assert events[-1] == "guardian:ack"
    assert saved.scientific_result_confirmed is True
    assert saved.scientific_result == receipt
    assert saved.artifacts.input.state is CleanupState.VERIFIED_ABSENT
    assert saved.version == 6


@pytest.mark.skipif(sys.platform != "linux", reason="canonical R worker integration requires Linux")
def test_real_linux_runner_binds_r_worker_result_to_sqlite_and_guardian(
    environment: tuple[
        SQLiteJobStore,
        WorkspaceManager,
        RecoveryReceiptStore,
        FakeClock,
        JobRecord,
        JobRecord,
        WorkspaceLayout,
        WorkerInputV1,
    ],
) -> None:
    store, workspaces, receipts, clock, _staged, running, layout, request = environment
    runner = StyloJobRunner(
        store=store,
        workspaces=workspaces,
        receipts=receipts,
        clock=clock,
        operation_id_factory=operation_factory(3, 4, 5),
    )

    saved = runner.run(job=running, layout=layout, request=request)

    assert saved.outcome is not None
    assert saved.outcome.kind is TerminalOutcome.SUCCEEDED
    receipt = saved.scientific_result
    assert receipt is not None
    assert saved.scientific_result_confirmed is True
    retained = (layout.result / RESULT_COMPONENT).read_bytes()
    assert len(retained) == receipt.byte_size
    assert hashlib.sha256(retained).hexdigest() == receipt.sha256
    disposition = receipts.read(fixed_job(), operation(2))
    assert disposition is not None
    assert disposition.outcome == "accepted"
    assert disposition.terminal_version == saved.version - 1
    assert disposition.terminal_outcome is TerminalOutcome.SUCCEEDED
    assert disposition.artifact_sha256 == receipt.sha256
    assert disposition.artifact_byte_size == receipt.byte_size


def test_runner_persists_scientific_rejection_without_result(
    environment: tuple[
        SQLiteJobStore,
        WorkspaceManager,
        RecoveryReceiptStore,
        FakeClock,
        JobRecord,
        JobRecord,
        WorkspaceLayout,
        WorkerInputV1,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, workspaces, receipts, clock, _staged, running, layout, request = environment
    worker_execution = execution(
        outcome=TerminalOutcome.FAILED,
        code=ScientificFinalizationCode.OUTPUT_MISSING,
    )
    events, _adapter_configs, _guardian_configs = install_fakes(
        monkeypatch,
        store=store,
        worker_execution=worker_execution,
        receipt=None,
    )
    runner = StyloJobRunner(
        store=store,
        workspaces=workspaces,
        receipts=receipts,
        clock=clock,
        operation_id_factory=operation_factory(3, 4),
    )

    saved = runner.run(job=running, layout=layout, request=request)

    assert events == [
        "adapter:init",
        "adapter:prepare",
        "guardian:init",
        "guardian:start",
        "guardian:wait",
        "adapter:capture",
        "guardian:ack",
    ]
    assert saved.outcome is not None
    assert saved.outcome.kind is TerminalOutcome.FAILED
    assert saved.scientific_result is None
    assert saved.artifacts.result.state is CleanupState.NOT_CREATED


def test_runner_never_acks_when_terminal_compare_and_swap_fails(
    environment: tuple[
        SQLiteJobStore,
        WorkspaceManager,
        RecoveryReceiptStore,
        FakeClock,
        JobRecord,
        JobRecord,
        WorkspaceLayout,
        WorkerInputV1,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, workspaces, receipts, clock, _staged, running, layout, request = environment
    receipt = scientific_receipt(request)
    events, _adapter_configs, _guardian_configs = install_fakes(
        monkeypatch,
        store=store,
        worker_execution=execution(
            outcome=TerminalOutcome.SUCCEEDED,
            code=ScientificFinalizationCode.RESULT_COMPLETE,
        ),
        receipt=receipt,
    )

    original_compare_and_swap = store.maintenance_compare_and_swap
    calls = 0

    def reject_terminal_compare_and_swap(**kwargs: Any) -> JobRecord:
        nonlocal calls
        calls += 1
        if calls == 1:
            return original_compare_and_swap(**kwargs)
        raise JobStoreError(JobStoreErrorCode.DATABASE_FAILURE)

    monkeypatch.setattr(
        store,
        "maintenance_compare_and_swap",
        reject_terminal_compare_and_swap,
    )
    runner = StyloJobRunner(
        store=store,
        workspaces=workspaces,
        receipts=receipts,
        clock=clock,
        operation_id_factory=operation_factory(3, 4),
    )

    with pytest.raises(JobStoreError, match=JobStoreErrorCode.DATABASE_FAILURE.value):
        runner.run(job=running, layout=layout, request=request)

    assert events[-1] == "adapter:publish"
    assert "guardian:ack" not in events


def test_runner_stale_snapshot_fails_before_adapter_or_guardian_side_effects(
    environment: tuple[
        SQLiteJobStore,
        WorkspaceManager,
        RecoveryReceiptStore,
        FakeClock,
        JobRecord,
        JobRecord,
        WorkspaceLayout,
        WorkerInputV1,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, workspaces, receipts, clock, _staged, running, layout, request = environment
    item = scientific_receipt(request)
    events, _adapter_configs, _guardian_configs = install_fakes(
        monkeypatch,
        store=store,
        worker_execution=execution(
            outcome=TerminalOutcome.SUCCEEDED,
            code=ScientificFinalizationCode.RESULT_COMPLETE,
        ),
        receipt=item,
    )
    first_runner = StyloJobRunner(
        store=store,
        workspaces=workspaces,
        receipts=receipts,
        clock=clock,
        operation_id_factory=operation_factory(3, 4, 5),
    )
    accepted = first_runner.run(job=running, layout=layout, request=request)
    assert accepted.scientific_result_confirmed is True
    payload = b'{"trusted":"result"}\n'
    workspaces.create_file(layout, WorkspaceArea.RESULT, RESULT_COMPONENT, payload)
    events.clear()
    stale_runner = StyloJobRunner(
        store=store,
        workspaces=workspaces,
        receipts=receipts,
        clock=clock,
        operation_id_factory=operation_factory(6),
    )

    with pytest.raises(VersionConflictError, match="JOB_VERSION_CONFLICT"):
        stale_runner.run(job=running, layout=layout, request=request)

    assert events == []
    assert (layout.result / RESULT_COMPONENT).read_bytes() == payload


def test_runner_leaves_accepted_result_pending_when_confirmation_cas_fails(
    environment: tuple[
        SQLiteJobStore,
        WorkspaceManager,
        RecoveryReceiptStore,
        FakeClock,
        JobRecord,
        JobRecord,
        WorkspaceLayout,
        WorkerInputV1,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, workspaces, receipts, clock, _staged, running, layout, request = environment
    item = scientific_receipt(request)
    events, _adapter_configs, _guardian_configs = install_fakes(
        monkeypatch,
        store=store,
        worker_execution=execution(
            outcome=TerminalOutcome.SUCCEEDED,
            code=ScientificFinalizationCode.RESULT_COMPLETE,
        ),
        receipt=item,
    )

    def reject_confirmation(**_kwargs: Any) -> JobRecord:
        raise JobStoreError(JobStoreErrorCode.DATABASE_FAILURE)

    monkeypatch.setattr(
        store,
        "confirm_scientific_result_after_guardian",
        reject_confirmation,
    )
    runner = StyloJobRunner(
        store=store,
        workspaces=workspaces,
        receipts=receipts,
        clock=clock,
        operation_id_factory=operation_factory(3, 4, 5),
    )

    with pytest.raises(JobStoreError, match=JobStoreErrorCode.DATABASE_FAILURE.value):
        runner.run(job=running, layout=layout, request=request)

    pending = store.list_jobs_for_maintenance()[0]
    assert events[-1] == "guardian:ack"
    assert pending.scientific_result == item
    assert pending.scientific_result_confirmed is False
    assert pending.artifacts.result.state is CleanupState.PRESENT


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("store", object()),
        ("workspaces", object()),
        ("receipts", object()),
        ("clock", object()),
        ("policy", object()),
        ("operation_id_factory", 7),
    ],
)
def test_runner_rejects_invalid_configuration(
    environment: tuple[
        SQLiteJobStore,
        WorkspaceManager,
        RecoveryReceiptStore,
        FakeClock,
        JobRecord,
        JobRecord,
        WorkspaceLayout,
        WorkerInputV1,
    ],
    field: str,
    invalid: object,
) -> None:
    store, workspaces, receipts, clock, *_rest = environment
    configuration: dict[str, Any] = {
        "store": store,
        "workspaces": workspaces,
        "receipts": receipts,
        "clock": clock,
        "policy": DEFAULT_JOB_POLICY,
        "operation_id_factory": lambda: operation(3),
    }
    configuration[field] = invalid
    with pytest.raises(ValueError, match="STYLO_JOB_RUNNER_INVALID_CONFIGURATION"):
        StyloJobRunner(**configuration)


def test_runner_rejects_invalid_job_layout_and_operation(
    environment: tuple[
        SQLiteJobStore,
        WorkspaceManager,
        RecoveryReceiptStore,
        FakeClock,
        JobRecord,
        JobRecord,
        WorkspaceLayout,
        WorkerInputV1,
    ],
) -> None:
    store, workspaces, receipts, clock, staged, running, layout, request = environment
    runner = StyloJobRunner(
        store=store,
        workspaces=workspaces,
        receipts=receipts,
        clock=clock,
        operation_id_factory=cast(Any, lambda: 7),
    )
    with pytest.raises(ValueError, match="STYLO_JOB_RUNNER_INVALID_JOB"):
        runner.run(job=staged, layout=layout, request=request)
    invalid_running = running.model_copy(update={"operations": ()})
    with pytest.raises(ValueError, match="STYLO_JOB_RUNNER_INVALID_JOB"):
        runner.run(job=invalid_running, layout=layout, request=request)
    other_layout = workspaces.create(running.owner_digest, "f" * 64)
    with pytest.raises(ValueError, match="STYLO_JOB_RUNNER_INVALID_LAYOUT"):
        runner.run(job=running, layout=other_layout, request=request)
    with pytest.raises(ValueError, match="STYLO_JOB_RUNNER_INVALID_OPERATION"):
        runner._operation_id()

    default_runner = StyloJobRunner(
        store=store,
        workspaces=workspaces,
        receipts=receipts,
        clock=clock,
    )
    generated = default_runner._operation_id()
    assert generated.startswith("op_")
    assert len(generated) == 67
