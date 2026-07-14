from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest

import delta_lemmata.stylo_worker as worker_module
from delta_lemmata.job_policy import STYLO_WORKER_LIMITS
from delta_lemmata.job_workspace import (
    WorkspaceArea,
    WorkspaceError,
    WorkspaceErrorCode,
    WorkspaceLayout,
    WorkspaceManager,
)
from delta_lemmata.process_controller import (
    ProcessControllerError,
    ProcessControllerErrorCode,
    ProcessEnvironmentProfile,
    ProcessOutcome,
    ProcessResult,
)
from delta_lemmata.scientific_finalizer import ScientificFinalizationCode
from delta_lemmata.stylo_contracts import (
    DirectStyloOracleV1,
    FatalErrorCode,
    FatalStage,
    StyloContractError,
    StyloContractErrorCode,
    WorkerFatalErrorV1,
    WorkerInputV1,
    WorkerResultV1,
    canonical_worker_json,
    parse_direct_stylo_oracle,
    parse_worker_input,
    validate_worker_result,
)
from delta_lemmata.stylo_worker import (
    FATAL_ERROR_COMPONENT,
    REQUEST_COMPONENT,
    RESULT_COMPONENT,
    STYLO_WORKER_ARGV,
    StyloWorkerAdapter,
    StyloWorkerAdapterError,
    StyloWorkerAdapterErrorCode,
    WorkerArtifactKind,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v2"
REFERENCE_DIR = ROOT / "provenance" / "evidence" / "P006" / "oracle-v2" / "direct-reference"
OWNER = "1" * 64
JOB = "2" * 64


@pytest.fixture
def workspace(tmp_path: Path) -> tuple[WorkspaceManager, WorkspaceLayout]:
    root = tmp_path / "jobs"
    root.mkdir(mode=0o700)
    manager = WorkspaceManager(root)
    return manager, manager.create(OWNER, JOB)


@pytest.fixture
def worker_request() -> WorkerInputV1:
    return parse_worker_input((FIXTURE_DIR / "normalization-base.input.json").read_bytes())


def worker_result(request: WorkerInputV1) -> WorkerResultV1:
    oracle: DirectStyloOracleV1 = parse_direct_stylo_oracle(
        (REFERENCE_DIR / "normalization-base.direct.json").read_bytes()
    )
    result = WorkerResultV1(
        schema_version="stylo-worker-result-v1",
        request_id=oracle.request_id,
        limit_profile=oracle.limit_profile,
        analysis_unit=oracle.analysis_unit,
        seed=oracle.seed,
        worker_version="stylo-worker-v1",
        outcome=oracle.outcome,
        fitting_basis=oracle.fitting_basis,
        fits=oracle.fits,
        cells=oracle.cells,
        session=oracle.session,
    )
    return validate_worker_result(request, result)


def expect_error(
    code: StyloWorkerAdapterErrorCode,
    action: Callable[[], object],
) -> StyloWorkerAdapterError:
    with pytest.raises(StyloWorkerAdapterError) as captured:
        action()
    error = captured.value
    assert error.code is code
    assert str(error) == code.value
    assert error.__context__ is None
    assert error.__cause__ is None
    return error


def fake_controller(
    monkeypatch: pytest.MonkeyPatch,
    callback: Callable[[], None],
    result: ProcessResult | None = None,
) -> list[dict[str, Any]]:
    configurations: list[dict[str, Any]] = []
    process_result = result or ProcessResult(ProcessOutcome.SUCCEEDED)

    class FakeController:
        def __init__(self, **configuration: Any) -> None:
            configurations.append(configuration)

        def run(self) -> ProcessResult:
            callback()
            return process_result

    monkeypatch.setattr(worker_module, "ProcessController", FakeController)
    return configurations


def test_fixed_adapter_writes_private_request_and_accepts_validated_result(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
    worker_request: WorkerInputV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, layout = workspace
    result_payload = canonical_worker_json(worker_result(worker_request))

    def publish() -> None:
        manager.create_file(
            layout,
            WorkspaceArea.WORK,
            RESULT_COMPONENT,
            result_payload,
        )

    configurations = fake_controller(monkeypatch, publish)
    execution = StyloWorkerAdapter(manager, layout).execute(worker_request)

    assert execution.accepted_result
    assert execution.finalization.code is ScientificFinalizationCode.RESULT_COMPLETE
    assert execution.finalization.result == worker_result(worker_request)
    assert execution.artifacts == (
        worker_module.WorkerArtifactReceipt(
            kind=WorkerArtifactKind.RESULT,
            component=RESULT_COMPONENT,
            byte_size=len(result_payload),
            sha256=hashlib.sha256(result_payload).hexdigest(),
        ),
    )
    assert configurations == [
        {
            "argv": STYLO_WORKER_ARGV,
            "cwd": layout.work,
            "limits": STYLO_WORKER_LIMITS,
            "environment_profile": ProcessEnvironmentProfile.R_STYLO,
        }
    ]
    request_path = layout.work / REQUEST_COMPONENT
    assert request_path.read_bytes() == canonical_worker_json(worker_request)
    assert stat.S_IMODE(request_path.stat().st_mode) == 0o600
    assert stat.S_IMODE((layout.work / RESULT_COMPONENT).stat().st_mode) == 0o600


def test_fixed_worker_source_has_no_user_controlled_execution_channel() -> None:
    source = (ROOT / "scripts" / "workers" / "p006-stylo-worker-v1.R").read_text(encoding="utf-8")
    assert STYLO_WORKER_ARGV == (
        "/usr/local/bin/Rscript",
        "--vanilla",
        str(ROOT / "scripts" / "workers" / "p006-stylo-worker-v1.R"),
    )
    assert REQUEST_COMPONENT in source
    assert RESULT_COMPONENT in source
    assert FATAL_ERROR_COMPONENT in source
    assert "stylo::dist.delta(z_scores, scale = FALSE)" in source
    assert "stylo::dist.eder(z_scores, scale = FALSE)" in source
    assert "stylo::dist.cosine(z_scores)" in source
    assert "length(commandArgs(trailingOnly = TRUE)) != 0L" in source
    assert 'Sys.umask("0077")' in source
    assert 'Sys.chmod(temporary, mode = "0600")' in source
    assert "source(activation, local = .GlobalEnv)" in source
    for forbidden in (
        "system(",
        "system2(",
        "shell(",
        "eval(parse",
        "parse(text",
        "download.file",
        "url(",
        "socketConnection",
    ):
        assert forbidden not in source


def test_request_values_never_enter_runtime_configuration(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
    worker_request: WorkerInputV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, layout = workspace
    sentinel = "system('touch SHOULD_NOT_EXIST')"
    payload = worker_request.model_dump(mode="python")
    features = list(payload["candidate_features"])
    features[0] = sentinel
    payload["candidate_features"] = tuple(features)
    injected = WorkerInputV1.model_validate(payload)
    configurations = fake_controller(monkeypatch, lambda: None)

    execution = StyloWorkerAdapter(manager, layout).execute(injected)

    assert execution.finalization.code is ScientificFinalizationCode.OUTPUT_MISSING
    assert not execution.accepted_result
    assert execution.artifacts == ()
    assert sentinel.encode() in (layout.work / REQUEST_COMPONENT).read_bytes()
    assert sentinel not in repr(configurations)
    assert not (layout.work / "SHOULD_NOT_EXIST").exists()


def test_invalid_configuration_runtime_and_request_are_content_free(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
    worker_request: WorkerInputV1,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manager, layout = workspace
    expect_error(
        StyloWorkerAdapterErrorCode.INVALID_CONFIGURATION,
        lambda: StyloWorkerAdapter(cast(WorkspaceManager, None), layout),
    )
    expect_error(
        StyloWorkerAdapterErrorCode.INVALID_CONFIGURATION,
        lambda: StyloWorkerAdapter(manager, cast(WorkspaceLayout, None)),
    )
    expect_error(
        StyloWorkerAdapterErrorCode.INVALID_REQUEST,
        lambda: StyloWorkerAdapter(manager, layout).execute(cast(WorkerInputV1, None)),
    )

    missing = tmp_path / "missing-rscript"
    monkeypatch.setattr(worker_module, "_RSCRIPT_PATH", missing)
    expect_error(
        StyloWorkerAdapterErrorCode.INVALID_CONFIGURATION,
        lambda: StyloWorkerAdapter(manager, layout),
    )
    invalid_executable = tmp_path / "not-executable"
    invalid_executable.write_text("not executable", encoding="ascii")
    monkeypatch.setattr(worker_module, "_RSCRIPT_PATH", invalid_executable)
    expect_error(
        StyloWorkerAdapterErrorCode.INVALID_CONFIGURATION,
        lambda: StyloWorkerAdapter(manager, layout),
    )
    assert worker_request.request_id.startswith("request_")


def test_prepare_execution_and_capture_failures_are_separate(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
    worker_request: WorkerInputV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, layout = workspace
    manager.create_file(layout, WorkspaceArea.WORK, RESULT_COMPONENT, b"occupied")
    expect_error(
        StyloWorkerAdapterErrorCode.PREPARE_FAILED,
        lambda: StyloWorkerAdapter(manager, layout).execute(worker_request),
    )

    second_layout = manager.create(OWNER, "3" * 64)

    class FailedController:
        def __init__(self, **_configuration: Any) -> None:
            pass

        def run(self) -> ProcessResult:
            raise ProcessControllerError(ProcessControllerErrorCode.CONTROL_FAILED)

    monkeypatch.setattr(worker_module, "ProcessController", FailedController)
    expect_error(
        StyloWorkerAdapterErrorCode.EXECUTION_FAILED,
        lambda: StyloWorkerAdapter(manager, second_layout).execute(worker_request),
    )

    third_layout = manager.create(OWNER, "4" * 64)
    fake_controller(monkeypatch, lambda: None)
    real_read = manager.read_file
    calls = 0

    def fail_during_capture(*args: Any, **kwargs: Any) -> bytes | None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise WorkspaceError(WorkspaceErrorCode.READ_FAILED)
        return real_read(*args, **kwargs)

    monkeypatch.setattr(manager, "read_file", fail_during_capture)
    expect_error(
        StyloWorkerAdapterErrorCode.CAPTURE_FAILED,
        lambda: StyloWorkerAdapter(manager, third_layout).execute(worker_request),
    )


def test_prepare_rejects_contract_serialization_failure(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
    worker_request: WorkerInputV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, layout = workspace
    monkeypatch.setattr(
        worker_module,
        "canonical_worker_json",
        Mock(side_effect=StyloContractError(StyloContractErrorCode.PAYLOAD_TOO_LARGE)),
    )
    expect_error(
        StyloWorkerAdapterErrorCode.PREPARE_FAILED,
        lambda: StyloWorkerAdapter(manager, layout).execute(worker_request),
    )


def test_conflicting_artifacts_are_both_receipted_but_never_accepted(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
    worker_request: WorkerInputV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, layout = workspace
    result_payload = canonical_worker_json(worker_result(worker_request))
    fatal_payload = canonical_worker_json(
        WorkerFatalErrorV1(
            schema_version="stylo-worker-fatal-error-v1",
            request_id=worker_request.request_id,
            worker_version="stylo-worker-v1",
            status="fatal_error",
            stage=FatalStage.ANALYSIS,
            error_code=FatalErrorCode.ANALYSIS_FAILED,
        )
    )

    def publish_conflict() -> None:
        manager.create_file(layout, WorkspaceArea.WORK, RESULT_COMPONENT, result_payload)
        manager.create_file(
            layout,
            WorkspaceArea.WORK,
            FATAL_ERROR_COMPONENT,
            fatal_payload,
        )

    fake_controller(monkeypatch, publish_conflict)
    execution = StyloWorkerAdapter(manager, layout).execute(worker_request)

    assert execution.finalization.code is ScientificFinalizationCode.OUTPUT_CONFLICT
    assert not execution.accepted_result
    assert tuple(artifact.kind for artifact in execution.artifacts) == (
        WorkerArtifactKind.RESULT,
        WorkerArtifactKind.FATAL_ERROR,
    )
    assert tuple(artifact.byte_size for artifact in execution.artifacts) == (
        len(result_payload),
        len(fatal_payload),
    )


def test_failed_process_with_no_artifact_remains_process_failure(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
    worker_request: WorkerInputV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, layout = workspace
    fake_controller(
        monkeypatch,
        lambda: None,
        result=ProcessResult(ProcessOutcome.FAILED),
    )
    execution = StyloWorkerAdapter(manager, layout).execute(worker_request)
    assert execution.finalization.code is ScientificFinalizationCode.PROCESS_FAILED
    assert execution.artifacts == ()
    assert not execution.accepted_result


def test_component_names_are_distinct_opaque_and_not_paths() -> None:
    components = (REQUEST_COMPONENT, RESULT_COMPONENT, FATAL_ERROR_COMPONENT)
    assert len(set(components)) == 3
    assert all(len(component) == 64 for component in components)
    assert all(set(component) <= set("0123456789abcdef") for component in components)
    assert all(Path(component).name == component for component in components)
    assert all(os.sep not in component for component in components)
