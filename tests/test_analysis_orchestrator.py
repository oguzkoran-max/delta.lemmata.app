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
from delta_lemmata.job_models import ExecutionState, JobRecord, TerminalOutcome
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

    running = environment.orchestrator.run_next()

    assert running is not None
    assert running.execution.state is ExecutionState.RUNNING
    assert environment.runner.calls == [(running, environment.layout, environment.request)]
    assert environment.orchestrator.run_next() is None


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
