from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import delta_lemmata.analysis_orchestrator as orchestrator_module
from delta_lemmata.analysis_orchestrator import (
    AnalysisOrchestrator,
    AnalysisOrchestratorError,
    AnalysisOrchestratorErrorCode,
)
from delta_lemmata.clock import FakeClock
from delta_lemmata.corpus_models import PurposeId
from delta_lemmata.job_models import (
    ExecutionState,
    JobRecord,
    TerminalOutcome,
    transition_execution,
)
from delta_lemmata.job_store import SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceArea, WorkspaceLayout, WorkspaceManager
from delta_lemmata.prepared_corpus_service import (
    PREPARED_REQUEST_INDEX_COMPONENT,
    PreparedRequestIndexV2,
    canonical_prepared_request_index,
)
from delta_lemmata.session_identity import JobId, SessionCapability, workspace_component
from delta_lemmata.stylo_contracts import (
    CellRequest,
    DocumentCounts,
    DocumentRole,
    FitRequest,
    WorkerInputV1,
    canonical_worker_json,
)
from delta_lemmata.workflow_models import (
    ResolvedWorkflowConfigV1,
    canonical_p008_json,
    resolve_guided_workflow,
)

NOW = datetime(2026, 7, 15, 1, 0, tzinfo=UTC)
OWNER_SECRET = b"p008-orchestrator-owner-secret-32bytes"


def _op(number: int) -> str:
    return "op_" + f"{number:064x}"


def _workflow() -> ResolvedWorkflowConfigV1:
    return resolve_guided_workflow(
        purpose=PurposeId.TEXT_PROXIMITY,
        known_work_count=2,
        unknown_work_count=0,
    )


def _request(config: ResolvedWorkflowConfigV1 | None = None) -> WorkerInputV1:
    config = config or _workflow()
    fit_ids = {
        (cell.mfw, cell.culling_percent): f"fit_{index:064x}"
        for index, cell in enumerate(config.cells, start=1)
    }
    fits = tuple(
        FitRequest(
            fit_id=fit_id,
            mfw=mfw,
            culling_percent=culling,
        )
        for (mfw, culling), fit_id in fit_ids.items()
    )
    cells = tuple(
        CellRequest(
            cell_id=f"cell_{index:064x}",
            fit_id=fit_ids[(cell.mfw, cell.culling_percent)],
            distance=cell.distance,
        )
        for index, cell in enumerate(config.cells, start=1)
    )
    documents = tuple(
        DocumentCounts(
            document_id=f"doc_{index:064x}",
            asset_ref=f"asset_{index:064x}",
            work_ref=f"work_{index:064x}",
            role=DocumentRole.KNOWN,
            token_total=5,
            counts=(index, 1),
        )
        for index in (1, 2)
    )
    return WorkerInputV1(
        schema_version="stylo-worker-input-v1",
        request_id="request_" + "9" * 64,
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        candidate_features=("alpha", "beta"),
        documents=documents,
        fits=fits,
        cells=cells,
    )


@dataclass(slots=True)
class FakeRunner:
    calls: list[tuple[JobRecord, WorkspaceLayout, WorkerInputV1]] = field(default_factory=list)

    def run(
        self,
        *,
        job: JobRecord,
        layout: WorkspaceLayout,
        request: WorkerInputV1,
    ) -> JobRecord:
        self.calls.append((job, layout, request))
        return job


@dataclass(slots=True)
class TerminalizingRunner:
    store: SQLiteJobStore
    clock: FakeClock
    failure_job_ids: frozenset[str] = frozenset()
    calls: list[str] = field(default_factory=list)

    def run(
        self,
        *,
        job: JobRecord,
        layout: WorkspaceLayout,
        request: WorkerInputV1,
    ) -> JobRecord:
        del layout, request
        self.calls.append(job.job_id)
        at_utc = self.clock.now()
        failed = job.job_id in self.failure_job_ids
        terminal = transition_execution(
            job,
            target=ExecutionState.TERMINAL,
            outcome=TerminalOutcome.FAILED if failed else TerminalOutcome.SUCCEEDED,
            at_utc=at_utc,
            tombstone_expires_at_utc=at_utc + timedelta(days=7),
            expected_version=job.version,
            operation_id=_op(100 + len(self.calls)),
        )
        saved = self.store.maintenance_compare_and_swap(
            job_id=job.job_id,
            expected_version=job.version,
            updated=terminal,
            at_utc=at_utc,
        )
        if failed:
            raise RuntimeError("private scientific runner failure")
        return saved


@dataclass(slots=True)
class Environment:
    store: SQLiteJobStore
    workspaces: WorkspaceManager
    clock: FakeClock
    runner: FakeRunner
    orchestrator: AnalysisOrchestrator
    layout: WorkspaceLayout
    request: WorkerInputV1
    config: ResolvedWorkflowConfigV1


def _environment(tmp_path: Path, *, with_bundle: bool = True) -> Environment:
    database_root = tmp_path / "database"
    workspace_root = tmp_path / "workspaces"
    database_root.mkdir(mode=0o700, parents=True)
    workspace_root.mkdir(mode=0o700, parents=True)
    job_id = JobId.generate(lambda size: b"j" * size)
    capability = SessionCapability.generate(lambda size: b"c" * size)
    store = SQLiteJobStore(
        database_root / "control.sqlite3",
        owner_secret=OWNER_SECRET,
        job_id_factory=lambda: job_id,
    )
    staged = store.stage_job(capability=capability, at_utc=NOW)
    workspaces = WorkspaceManager(workspace_root)
    layout = workspaces.create(staged.owner_digest, workspace_component(job_id))
    store.enqueue_job(
        job_id=staged.job_id,
        capability=capability,
        at_utc=NOW + timedelta(microseconds=1),
        expected_version=staged.version,
        operation_id=_op(1),
    )
    config = _workflow()
    request = _request(config)
    if with_bundle:
        _write_bundle(workspaces, layout, config, request)
    clock = FakeClock(NOW + timedelta(microseconds=2))
    runner = FakeRunner()
    values = iter((_op(2), _op(3), _op(4), _op(5)))
    orchestrator = AnalysisOrchestrator(
        store=store,
        workspaces=workspaces,
        runner=runner,
        clock=clock,
        operation_id_factory=lambda: next(values),
    )
    return Environment(
        store=store,
        workspaces=workspaces,
        clock=clock,
        runner=runner,
        orchestrator=orchestrator,
        layout=layout,
        request=request,
        config=config,
    )


def _write_bundle(
    workspaces: WorkspaceManager,
    layout: WorkspaceLayout,
    config: ResolvedWorkflowConfigV1,
    request: WorkerInputV1,
) -> None:
    config_payload = canonical_p008_json(config)
    request_payload = canonical_worker_json(request)
    config_component = "a" * 64
    request_component = "b" * 64
    index = PreparedRequestIndexV2(
        schema_version="prepared-stylo-request-index-v2",
        request_component=request_component,
        request_byte_count=len(request_payload),
        request_sha256=hashlib.sha256(request_payload).hexdigest(),
        workflow_config_component=config_component,
        workflow_config_byte_count=len(config_payload),
        workflow_config_sha256=hashlib.sha256(config_payload).hexdigest(),
    )
    workspaces.create_file(layout, WorkspaceArea.WORK, config_component, config_payload)
    workspaces.create_file(layout, WorkspaceArea.WORK, request_component, request_payload)
    workspaces.create_file(
        layout,
        WorkspaceArea.WORK,
        PREPARED_REQUEST_INDEX_COMPONENT,
        canonical_prepared_request_index(index),
    )


def _fifo_environment(
    tmp_path: Path,
    *,
    missing_bundle_indexes: frozenset[int] = frozenset(),
    corrupt_bundle_indexes: frozenset[int] = frozenset(),
    failing_runner_indexes: frozenset[int] = frozenset(),
) -> tuple[AnalysisOrchestrator, SQLiteJobStore, TerminalizingRunner, tuple[JobRecord, ...]]:
    database_root = tmp_path / "database"
    workspace_root = tmp_path / "workspaces"
    database_root.mkdir(mode=0o700, parents=True)
    workspace_root.mkdir(mode=0o700, parents=True)
    job_ids = tuple(
        JobId.generate(lambda size, byte=byte: bytes((byte,)) * size)
        for byte in (ord("a"), ord("b"), ord("c"))
    )
    job_id_values = iter(job_ids)
    store = SQLiteJobStore(
        database_root / "control.sqlite3",
        owner_secret=OWNER_SECRET,
        job_id_factory=lambda: next(job_id_values),
    )
    workspaces = WorkspaceManager(workspace_root)
    config = _workflow()
    request = _request(config)
    queued: list[JobRecord] = []
    for index, job_id in enumerate(job_ids):
        capability_byte = ord("d") + index
        capability = SessionCapability.generate(
            lambda size, byte=capability_byte: bytes((byte,)) * size
        )
        staged = store.stage_job(
            capability=capability,
            at_utc=NOW + timedelta(microseconds=index * 2),
        )
        assert staged.job_id == job_id.to_urlsafe()
        if index not in missing_bundle_indexes:
            layout = workspaces.create(staged.owner_digest, workspace_component(job_id))
            bound_request = (
                request.model_copy(update={"cells": tuple(reversed(request.cells))})
                if index in corrupt_bundle_indexes
                else request
            )
            _write_bundle(workspaces, layout, config, bound_request)
        queued.append(
            store.enqueue_job(
                job_id=staged.job_id,
                capability=capability,
                at_utc=NOW + timedelta(microseconds=(index * 2) + 1),
                expected_version=staged.version,
                operation_id=_op(10 + index),
            )
        )
    clock = FakeClock(NOW + timedelta(microseconds=10))
    runner = TerminalizingRunner(
        store=store,
        clock=clock,
        failure_job_ids=frozenset(queued[index].job_id for index in failing_runner_indexes),
    )
    operations = iter(_op(number) for number in range(20, 40))
    orchestrator = AnalysisOrchestrator(
        store=store,
        workspaces=workspaces,
        runner=runner,
        clock=clock,
        operation_id_factory=lambda: next(operations),
    )
    return orchestrator, store, runner, tuple(queued)


def _expect_error(
    action: Callable[[], object],
    code: AnalysisOrchestratorErrorCode,
) -> None:
    with pytest.raises(AnalysisOrchestratorError) as captured:
        action()
    assert captured.value.code is code
    assert str(captured.value) == code.value
    assert captured.value.__context__ is None
    assert captured.value.__cause__ is None


def _index(environment: Environment) -> PreparedRequestIndexV2:
    return PreparedRequestIndexV2.model_validate_json(
        (environment.layout.work / PREPARED_REQUEST_INDEX_COMPONENT).read_bytes()
    )


def test_orchestrator_claims_verifies_and_hands_one_bound_request_to_runner(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)
    [queued] = environment.store.list_jobs_for_maintenance()
    other_job_id = JobId.generate(lambda size: b"x" * size).to_urlsafe()

    assert environment.orchestrator.run_next(expected_job_id=other_job_id) is None
    assert environment.runner.calls == []

    running = environment.orchestrator.run_next(expected_job_id=queued.job_id)

    assert running is not None
    assert running.execution.state is ExecutionState.RUNNING
    assert environment.runner.calls == [(running, environment.layout, environment.request)]
    assert environment.orchestrator.run_next() is None


def test_run_until_advances_one_real_sqlite_fifo_job_per_interaction(tmp_path: Path) -> None:
    orchestrator, store, runner, queued = _fifo_environment(tmp_path)
    expected = queued[-1]

    assert orchestrator.run_until(expected_job_id=expected.job_id) is None
    assert runner.calls == [queued[0].job_id]
    assert orchestrator.run_until(expected_job_id=expected.job_id) is None
    assert runner.calls == [queued[0].job_id, queued[1].job_id]
    completed = orchestrator.run_until(expected_job_id=expected.job_id)

    assert completed is not None
    assert completed.job_id == expected.job_id
    assert completed.execution.state is ExecutionState.TERMINAL
    assert runner.calls == [job.job_id for job in queued]
    assert all(
        job.execution.state is ExecutionState.TERMINAL for job in store.list_jobs_for_maintenance()
    )


def test_run_until_hides_a_distinct_owner_predecessor_bundle_failure(tmp_path: Path) -> None:
    orchestrator, store, runner, queued = _fifo_environment(
        tmp_path,
        missing_bundle_indexes=frozenset({0}),
    )
    expected = queued[-1]

    assert orchestrator.run_until(expected_job_id=expected.job_id) is None
    first = next(job for job in store.list_jobs_for_maintenance() if job.job_id == queued[0].job_id)
    assert first.execution.state is ExecutionState.TERMINAL
    assert first.outcome is not None
    assert first.outcome.kind is TerminalOutcome.CRASHED
    assert runner.calls == []

    assert orchestrator.run_until(expected_job_id=expected.job_id) is None
    completed = orchestrator.run_until(expected_job_id=expected.job_id)
    assert completed is not None
    assert completed.job_id == expected.job_id
    assert runner.calls == [queued[1].job_id, expected.job_id]


@pytest.mark.parametrize(
    ("environment_options", "expected_outcome"),
    [
        ({"corrupt_bundle_indexes": frozenset({0})}, TerminalOutcome.CRASHED),
        ({"failing_runner_indexes": frozenset({0})}, TerminalOutcome.FAILED),
    ],
)
def test_run_until_hides_distinct_owner_predecessor_failures(
    tmp_path: Path,
    environment_options: dict[str, frozenset[int]],
    expected_outcome: TerminalOutcome,
) -> None:
    orchestrator, store, runner, queued = _fifo_environment(
        tmp_path,
        **environment_options,
    )
    expected = queued[-1]

    assert orchestrator.run_until(expected_job_id=expected.job_id) is None
    first = next(job for job in store.list_jobs_for_maintenance() if job.job_id == queued[0].job_id)
    assert first.execution.state is ExecutionState.TERMINAL
    assert first.outcome is not None
    assert first.outcome.kind is expected_outcome

    assert orchestrator.run_until(expected_job_id=expected.job_id) is None
    completed = orchestrator.run_until(expected_job_id=expected.job_id)
    assert completed is not None
    assert completed.job_id == expected.job_id
    assert runner.calls[-1] == expected.job_id


def test_run_until_exposes_only_the_expected_jobs_own_bundle_failure(tmp_path: Path) -> None:
    orchestrator, _store, runner, queued = _fifo_environment(
        tmp_path,
        missing_bundle_indexes=frozenset({0}),
    )

    _expect_error(
        lambda: orchestrator.run_until(expected_job_id=queued[0].job_id),
        AnalysisOrchestratorErrorCode.BUNDLE_NOT_AVAILABLE,
    )
    assert runner.calls == []


def test_run_until_exposes_only_the_expected_jobs_own_runner_failure(tmp_path: Path) -> None:
    orchestrator, _store, runner, queued = _fifo_environment(
        tmp_path,
        failing_runner_indexes=frozenset({0}),
    )

    _expect_error(
        lambda: orchestrator.run_until(expected_job_id=queued[0].job_id),
        AnalysisOrchestratorErrorCode.OPERATION_FAILED,
    )
    assert runner.calls == [queued[0].job_id]


def test_run_until_rejects_an_invalid_expected_identity_content_free(tmp_path: Path) -> None:
    environment = _environment(tmp_path)

    _expect_error(
        lambda: environment.orchestrator.run_until(expected_job_id="not-a-job-id"),
        AnalysisOrchestratorErrorCode.OPERATION_FAILED,
    )


def test_run_next_rejects_an_empty_internal_attempt_content_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment(tmp_path)
    monkeypatch.setattr(
        AnalysisOrchestrator,
        "_run_next_attempt",
        lambda _self, *, expected_job_id=None: orchestrator_module._RunAttempt(
            job_id=expected_job_id or "empty-internal-attempt"
        ),
    )

    _expect_error(
        environment.orchestrator.run_next,
        AnalysisOrchestratorErrorCode.OPERATION_FAILED,
    )


def test_run_until_rejects_an_empty_expected_attempt_content_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = _environment(tmp_path)
    expected = JobId.generate(lambda size: b"j" * size).to_urlsafe()

    def empty_attempt(
        _self: AnalysisOrchestrator,
        *,
        expected_job_id: str | None = None,
    ) -> orchestrator_module._RunAttempt:
        del expected_job_id
        return orchestrator_module._RunAttempt(job_id=expected)

    monkeypatch.setattr(
        AnalysisOrchestrator,
        "_run_next_attempt",
        empty_attempt,
    )

    _expect_error(
        lambda: environment.orchestrator.run_until(expected_job_id=expected),
        AnalysisOrchestratorErrorCode.OPERATION_FAILED,
    )


def test_missing_bundle_is_terminalized_without_calling_runner(tmp_path: Path) -> None:
    environment = _environment(tmp_path, with_bundle=False)

    _expect_error(
        environment.orchestrator.run_next,
        AnalysisOrchestratorErrorCode.BUNDLE_NOT_AVAILABLE,
    )

    [terminal] = environment.store.list_jobs_for_maintenance()
    assert terminal.execution.state is ExecutionState.TERMINAL
    assert terminal.outcome is not None
    assert terminal.outcome.kind is TerminalOutcome.CRASHED
    assert environment.runner.calls == []


def test_semantically_rebound_request_is_rejected_even_with_matching_index_digest(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path, with_bundle=False)
    changed = environment.request.model_copy(
        update={"cells": tuple(reversed(environment.request.cells))}
    )
    _write_bundle(
        environment.workspaces,
        environment.layout,
        environment.config,
        changed,
    )

    _expect_error(
        environment.orchestrator.run_next,
        AnalysisOrchestratorErrorCode.BUNDLE_INTEGRITY,
    )
    assert environment.runner.calls == []


def test_constructor_and_operation_failures_are_content_free(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    _expect_error(
        lambda: AnalysisOrchestrator(
            store=object(),  # type: ignore[arg-type]
            workspaces=environment.workspaces,
            runner=environment.runner,
            clock=environment.clock,
        ),
        AnalysisOrchestratorErrorCode.INVALID_CONFIGURATION,
    )
    broken = AnalysisOrchestrator(
        store=environment.store,
        workspaces=environment.workspaces,
        runner=environment.runner,
        clock=environment.clock,
        operation_id_factory=lambda: "invalid",
    )
    _expect_error(
        broken.run_next,
        AnalysisOrchestratorErrorCode.INVALID_OPERATION,
    )

    exploding = AnalysisOrchestrator(
        store=environment.store,
        workspaces=environment.workspaces,
        runner=environment.runner,
        clock=environment.clock,
        operation_id_factory=lambda: (_ for _ in ()).throw(RuntimeError("private")),
    )
    _expect_error(
        exploding._operation_id,
        AnalysisOrchestratorErrorCode.INVALID_OPERATION,
    )

    non_string = AnalysisOrchestrator(
        store=environment.store,
        workspaces=environment.workspaces,
        runner=environment.runner,
        clock=environment.clock,
        operation_id_factory=lambda: None,  # type: ignore[arg-type,return-value]
    )
    _expect_error(
        non_string._operation_id,
        AnalysisOrchestratorErrorCode.INVALID_OPERATION,
    )

    class BrokenClock:
        def now(self) -> datetime:
            raise RuntimeError("private")

    broken_clock = AnalysisOrchestrator(
        store=environment.store,
        workspaces=environment.workspaces,
        runner=environment.runner,
        clock=BrokenClock(),
    )
    _expect_error(
        broken_clock._now,
        AnalysisOrchestratorErrorCode.INVALID_CONFIGURATION,
    )

    generated = orchestrator_module._default_operation_id()
    assert generated.startswith("op_")
    assert len(generated) == 67


def test_missing_workspace_is_terminalized_before_private_reads(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    environment.workspaces.cleanup(environment.layout)

    _expect_error(
        environment.orchestrator.run_next,
        AnalysisOrchestratorErrorCode.BUNDLE_NOT_AVAILABLE,
    )

    [terminal] = environment.store.list_jobs_for_maintenance()
    assert terminal.execution.state is ExecutionState.TERMINAL
    assert terminal.outcome is not None
    assert terminal.outcome.kind is TerminalOutcome.CRASHED


def test_invalid_cell_reference_is_rejected_by_the_semantic_binding() -> None:
    config = _workflow()
    request = _request(config)
    changed_cell = request.cells[0].model_copy(update={"fit_id": "fit_" + "f" * 64})
    changed_request = request.model_copy(update={"cells": (changed_cell, *request.cells[1:])})

    _expect_error(
        lambda: AnalysisOrchestrator._verify_semantic_binding(config, changed_request),
        AnalysisOrchestratorErrorCode.BUNDLE_INTEGRITY,
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "malformed-index",
        "noncanonical-index",
        "digest-mismatch",
        "invalid-config",
        "noncanonical-config",
        "noncanonical-request",
    ],
)
def test_private_bundle_structural_mutations_fail_closed(
    tmp_path: Path,
    mutation: str,
) -> None:
    environment = _environment(tmp_path)
    index_path = environment.layout.work / PREPARED_REQUEST_INDEX_COMPONENT
    index = _index(environment)
    config_path = environment.layout.work / index.workflow_config_component
    request_path = environment.layout.work / index.request_component

    if mutation == "malformed-index":
        index_path.write_bytes(b"{}")
    elif mutation == "noncanonical-index":
        index_path.write_bytes(index_path.read_bytes() + b"\n")
    elif mutation == "digest-mismatch":
        changed_index = index.model_copy(update={"request_sha256": "f" * 64})
        index_path.write_bytes(canonical_prepared_request_index(changed_index))
    elif mutation in {"invalid-config", "noncanonical-config"}:
        config_payload = b"{}" if mutation == "invalid-config" else b" " + config_path.read_bytes()
        config_path.write_bytes(config_payload)
        changed_index = index.model_copy(
            update={
                "workflow_config_byte_count": len(config_payload),
                "workflow_config_sha256": hashlib.sha256(config_payload).hexdigest(),
            }
        )
        index_path.write_bytes(canonical_prepared_request_index(changed_index))
    else:
        request_payload = b" " + request_path.read_bytes()
        request_path.write_bytes(request_payload)
        changed_index = index.model_copy(
            update={
                "request_byte_count": len(request_payload),
                "request_sha256": hashlib.sha256(request_payload).hexdigest(),
            }
        )
        index_path.write_bytes(canonical_prepared_request_index(changed_index))

    _expect_error(
        environment.orchestrator.run_next,
        AnalysisOrchestratorErrorCode.BUNDLE_INTEGRITY,
    )
    assert environment.runner.calls == []


def test_unexpected_runner_failure_is_content_free_after_verified_handoff(
    tmp_path: Path,
) -> None:
    environment = _environment(tmp_path)

    class RaisingRunner:
        def run(
            self,
            *,
            job: JobRecord,
            layout: WorkspaceLayout,
            request: WorkerInputV1,
        ) -> JobRecord:
            del job, layout, request
            raise RuntimeError("private runner detail")

    values = iter((_op(20), _op(21)))
    orchestrator = AnalysisOrchestrator(
        store=environment.store,
        workspaces=environment.workspaces,
        runner=RaisingRunner(),
        clock=environment.clock,
        operation_id_factory=lambda: next(values),
    )

    _expect_error(
        orchestrator.run_next,
        AnalysisOrchestratorErrorCode.OPERATION_FAILED,
    )
