from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest

import delta_lemmata.guardian_controller as guardian
import delta_lemmata.process_controller as process_control
from delta_lemmata.clock import FakeClock
from delta_lemmata.guardian_controller import (
    GUARDIAN_PROCESS_BOUNDARY,
    GuardianController,
    GuardianControllerError,
    GuardianControllerErrorCode,
)
from delta_lemmata.job_janitor import JobJanitor
from delta_lemmata.job_models import (
    ArtifactKind,
    CleanupState,
    ExecutionState,
    TerminalOutcome,
    request_cancellation,
    transition_execution,
)
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY, WorkerLimitProfile
from delta_lemmata.job_store import JobStoreError, JobStoreErrorCode, SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceArea, WorkspaceLayout, WorkspaceManager
from delta_lemmata.process_controller import (
    ProcessControllerError,
    ProcessControllerErrorCode,
    ProcessLimit,
    ProcessOutcome,
    ProcessResult,
)
from delta_lemmata.recovery_receipt import RecoveryReceiptStore
from delta_lemmata.session_identity import JobId, SessionCapability, workspace_component

WORKER = Path(__file__).parent / "fixtures" / "synthetic_worker.py"
APP = Path(__file__).parent / "fixtures" / "guardian_app.py"
SECRET = b"guardian-app-loss-secret-v1-32bytes"
OWNER_SECRET = b"guardian-job-owner-secret-v1-32bytes"


def operation(number: int) -> str:
    return "op_" + f"{number:064x}"


def limits(*, wall: int = 5, grace: int = 1) -> WorkerLimitProfile:
    payload = DEFAULT_JOB_POLICY.worker_limits.model_dump(mode="python")
    payload["wall_time_seconds"] = wall
    payload["terminate_grace_seconds"] = grace
    return WorkerLimitProfile.model_validate(payload)


def roots(tmp_path: Path) -> tuple[Path, Path]:
    workspace_root = tmp_path / "workspaces"
    receipt_root = tmp_path / "receipts"
    workspace_root.mkdir(mode=0o700)
    receipt_root.mkdir(mode=0o700)
    return workspace_root, receipt_root


def fixed_job(number: int = 1) -> JobId:
    return JobId.generate(lambda size: bytes([number]) * size)


def controller(
    tmp_path: Path,
    mode: str,
    *,
    profile: WorkerLimitProfile | None = None,
) -> tuple[
    GuardianController,
    WorkspaceManager,
    WorkspaceLayout,
    RecoveryReceiptStore,
    JobId,
]:
    workspace_root, receipt_root = roots(tmp_path)
    database_root = tmp_path / "database"
    database_root.mkdir(mode=0o700)
    job_id = fixed_job()
    capability = SessionCapability.generate(lambda size: b"q" * size)
    store = SQLiteJobStore(
        database_root / "control.sqlite3",
        owner_secret=OWNER_SECRET,
        job_id_factory=lambda: job_id,
    )
    started_at = datetime.now(UTC)
    staged = store.stage_job(capability=capability, at_utc=started_at)
    store.enqueue_job(
        job_id=staged.job_id,
        capability=capability,
        at_utc=started_at + timedelta(microseconds=1),
        expected_version=staged.version,
        operation_id=operation(1),
    )
    running = store.claim_next(
        at_utc=started_at + timedelta(microseconds=2),
        operation_id=operation(2),
    )
    assert running is not None
    owner = running.owner_digest
    component = workspace_component(job_id)
    workspaces = WorkspaceManager(workspace_root)
    layout = workspaces.create(owner, component)
    receipts = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    item = GuardianController(
        argv=(sys.executable, str(WORKER.resolve()), mode),
        cwd=tmp_path,
        limits=profile or limits(),
        job_id=job_id,
        execution_reference=operation(2),
        store=store,
        workspace_root=workspace_root,
        owner_component=owner,
        job_component=component,
        receipt_store=receipts,
    )
    return item, workspaces, layout, receipts, job_id


def persist_terminal(item: GuardianController, result: ProcessResult) -> int:
    job = next(
        job
        for job in item._store.list_jobs_for_maintenance()
        if job.job_id == item._job_id.to_urlsafe()
    )
    at_utc = datetime.now(UTC)
    if result.outcome is ProcessOutcome.CANCELLED:
        requested = request_cancellation(
            job,
            at_utc=at_utc,
            expected_version=job.version,
            operation_id=operation(90),
        )
        job = item._store.maintenance_compare_and_swap(
            job_id=job.job_id,
            expected_version=job.version,
            updated=requested,
            at_utc=at_utc,
        )
        at_utc += timedelta(microseconds=1)
    terminal = transition_execution(
        job,
        target=ExecutionState.TERMINAL,
        outcome=guardian._terminal_outcome(result),
        at_utc=at_utc,
        tombstone_expires_at_utc=at_utc + timedelta(days=7),
        expected_version=job.version,
        operation_id=operation(91),
    )
    saved = item._store.maintenance_compare_and_swap(
        job_id=job.job_id,
        expected_version=job.version,
        updated=terminal,
        at_utc=at_utc,
    )
    return saved.version


def expect_error(code: GuardianControllerErrorCode, action: object) -> GuardianControllerError:
    with pytest.raises(GuardianControllerError) as captured:
        assert callable(action)
        action()
    error = captured.value
    assert error.code is code
    assert str(error) == code.value
    assert error.__context__ is None
    assert error.__cause__ is None
    return error


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("success", ProcessResult(ProcessOutcome.SUCCEEDED)),
        ("failure", ProcessResult(ProcessOutcome.FAILED)),
        ("crash", ProcessResult(ProcessOutcome.CRASHED)),
    ],
)
def test_guardian_preserves_normal_content_free_results_without_cleanup(
    tmp_path: Path,
    mode: str,
    expected: ProcessResult,
) -> None:
    item, _workspaces, layout, receipts, job_id = controller(tmp_path, mode)
    item.start()
    assert item.wait() == expected
    terminal_version = persist_terminal(item, expected)
    item.acknowledge_terminal_persisted(expected_version=terminal_version)
    item.acknowledge_terminal_persisted(expected_version=terminal_version)
    assert item.wait() is item.result
    assert item.cancel() is item.result
    assert item.boundary == GUARDIAN_PROCESS_BOUNDARY
    assert layout.job.exists()
    assert receipts.read(job_id, operation(2)) is None


def test_guardian_cancel_and_wall_timeout_reap_before_return(tmp_path: Path) -> None:
    item, _workspaces, _layout, receipts, job_id = controller(tmp_path, "nested")
    item.start()
    expect_error(GuardianControllerErrorCode.INVALID_STATE, item.start)
    process_group_id = item.process_group_id
    cancelled = item.cancel()
    assert cancelled == ProcessResult(ProcessOutcome.CANCELLED)
    item.acknowledge_terminal_persisted(expected_version=persist_terminal(item, cancelled))
    assert not process_control._group_exists(process_group_id)
    assert receipts.read(job_id, operation(2)) is None

    timeout_root = tmp_path / "timeout"
    timeout_root.mkdir(mode=0o700)
    timed, _manager, _layout, _receipts, _job = controller(
        timeout_root,
        "sleep",
        profile=limits(wall=1),
    )
    timed.start()
    timeout_group = timed.process_group_id
    timed_out = timed.wait()
    assert timed_out == ProcessResult(ProcessOutcome.TIMED_OUT, ProcessLimit.WALL)
    timed.acknowledge_terminal_persisted(expected_version=persist_terminal(timed, timed_out))
    assert not process_control._group_exists(timeout_group)


def test_real_application_sigkill_reaps_nested_group_cleans_workspace_and_recovers_job(
    tmp_path: Path,
) -> None:
    database_root = tmp_path / "database"
    workspace_root = tmp_path / "workspaces"
    receipt_root = tmp_path / "receipts"
    for directory in (database_root, workspace_root, receipt_root):
        directory.mkdir(mode=0o700)
    identifier = fixed_job(7)
    owner = SessionCapability.generate(lambda size: b"o" * size)
    store = SQLiteJobStore(
        database_root / "control.sqlite3",
        owner_secret=OWNER_SECRET,
        job_id_factory=lambda: identifier,
    )
    started_at = datetime.now(UTC)
    staged = store.stage_job(capability=owner, at_utc=started_at)
    store.enqueue_job(
        job_id=staged.job_id,
        capability=owner,
        at_utc=started_at + timedelta(microseconds=1),
        expected_version=staged.version,
        operation_id=operation(1),
    )
    running = store.claim_next(
        at_utc=started_at + timedelta(microseconds=2),
        operation_id=operation(2),
    )
    assert running is not None and running.execution.state is ExecutionState.RUNNING
    component = workspace_component(identifier)
    workspaces = WorkspaceManager(workspace_root)
    layout = workspaces.create(running.owner_digest, component)
    workspaces.create_file(layout, WorkspaceArea.INPUT, "a" * 64, b"CANARY PRIVATE CORPUS")
    workspaces.create_file(layout, WorkspaceArea.WORK, "b" * 64, b"NORMALIZED CANARY")
    ready_file = tmp_path / "ready"
    app = subprocess.Popen(
        (
            sys.executable,
            str(APP),
            str(ready_file),
            str(WORKER.resolve()),
            str(workspace_root),
            running.owner_digest,
            component,
            str(receipt_root),
            identifier.to_urlsafe(),
            "nested",
            str(database_root / "control.sqlite3"),
            operation(2),
        ),
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        cwd=tmp_path,
        env=dict(os.environ),
        start_new_session=True,
    )
    deadline = time.monotonic() + 10
    while not ready_file.exists() and time.monotonic() < deadline:
        time.sleep(0.025)
    assert ready_file.exists()
    process_group_id = int(ready_file.read_text(encoding="ascii"))
    deadline = time.monotonic() + 5
    while (
        process_control._count_process_group("/bin/ps", process_group_id) < 3
        and time.monotonic() < deadline
    ):
        time.sleep(0.025)
    assert process_control._count_process_group("/bin/ps", process_group_id) >= 3

    os.killpg(app.pid, signal.SIGKILL)
    assert app.wait(timeout=5) == -signal.SIGKILL
    receipts = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    receipt = None
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        receipt = receipts.read(identifier, operation(2))
        if receipt is not None and not process_control._group_exists(process_group_id):
            break
        time.sleep(0.025)
    assert receipt is not None
    assert receipt.worker_group_verified_absent is True
    assert receipt.workspace_verified_absent is True
    assert receipt.file_count == 2
    assert not process_control._group_exists(process_group_id)
    assert not layout.job.exists()

    clock = FakeClock(datetime.now(UTC))
    janitor = JobJanitor(store=store, workspaces=workspaces, clock=clock)
    report = janitor.recover_startup(
        lambda job: receipts.proves_recovery(
            JobId.from_urlsafe(job.job_id),
            operation(2),
            at_utc=clock.now(),
        )
    )
    recovered = store.get_job(job_id=identifier, capability=owner)
    assert report.running_jobs_recovered == 1
    assert recovered.outcome is not None
    assert recovered.outcome.kind is TerminalOutcome.ABANDONED
    assert all(
        recovered.artifacts.for_kind(kind).state is CleanupState.VERIFIED_ABSENT
        for kind in ArtifactKind
    )
    raw_receipt = next(receipt_root.iterdir()).read_bytes()
    assert b"CANARY PRIVATE CORPUS" not in raw_receipt
    assert b"NORMALIZED CANARY" not in raw_receipt
    assert running.job_id.encode("ascii") not in raw_receipt


def test_application_loss_after_worker_completion_still_cleans_and_proves_recovery(
    tmp_path: Path,
) -> None:
    workspace_root, receipt_root = roots(tmp_path)
    database_root = tmp_path / "database"
    database_root.mkdir(mode=0o700)
    identifier = fixed_job(8)
    capability = SessionCapability.generate(lambda size: b"r" * size)
    store = SQLiteJobStore(
        database_root / "control.sqlite3",
        owner_secret=OWNER_SECRET,
        job_id_factory=lambda: identifier,
    )
    started_at = datetime.now(UTC)
    staged = store.stage_job(capability=capability, at_utc=started_at)
    store.enqueue_job(
        job_id=staged.job_id,
        capability=capability,
        at_utc=started_at + timedelta(microseconds=1),
        expected_version=staged.version,
        operation_id=operation(1),
    )
    running = store.claim_next(
        at_utc=started_at + timedelta(microseconds=2),
        operation_id=operation(2),
    )
    assert running is not None
    owner = running.owner_digest
    component = workspace_component(identifier)
    workspaces = WorkspaceManager(workspace_root)
    layout = workspaces.create(owner, component)
    workspaces.create_file(layout, WorkspaceArea.INPUT, "d" * 64, b"COMPLETION RACE CANARY")
    ready_file = tmp_path / "completion-ready"
    app = subprocess.Popen(
        (
            sys.executable,
            str(APP),
            str(ready_file),
            str(WORKER.resolve()),
            str(workspace_root),
            owner,
            component,
            str(receipt_root),
            identifier.to_urlsafe(),
            "success",
            str(database_root / "control.sqlite3"),
            operation(2),
        ),
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        cwd=tmp_path,
        env=dict(os.environ),
        start_new_session=True,
    )
    deadline = time.monotonic() + 10
    while not ready_file.exists() and time.monotonic() < deadline:
        time.sleep(0.025)
    assert ready_file.exists()
    process_group_id = int(ready_file.read_text(encoding="ascii"))
    deadline = time.monotonic() + 10
    while process_control._group_exists(process_group_id) and time.monotonic() < deadline:
        time.sleep(0.025)
    assert not process_control._group_exists(process_group_id)
    receipts = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    assert receipts.read(identifier, operation(2)) is None
    assert layout.job.exists()

    os.killpg(app.pid, signal.SIGKILL)
    assert app.wait(timeout=5) == -signal.SIGKILL
    recovered = None
    deadline = time.monotonic() + 10
    while recovered is None and time.monotonic() < deadline:
        recovered = receipts.read(identifier, operation(2))
        time.sleep(0.025)
    assert recovered is not None
    assert recovered.outcome == "recovery_required"
    assert recovered.workspace_verified_absent is True
    assert recovered.file_count == 1
    assert not layout.job.exists()


def test_invalid_configuration_and_state_are_content_free(tmp_path: Path) -> None:
    workspace_root, receipt_root = roots(tmp_path)
    database_root = tmp_path / "database"
    database_root.mkdir(mode=0o700)
    store = SQLiteJobStore(database_root / "control.sqlite3", owner_secret=OWNER_SECRET)
    receipts = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    identifier = fixed_job()
    valid = GuardianController(
        argv=(sys.executable, str(WORKER.resolve()), "success"),
        cwd=tmp_path,
        limits=limits(),
        job_id=identifier,
        execution_reference=operation(2),
        store=store,
        workspace_root=workspace_root,
        owner_component="a" * 64,
        job_component=workspace_component(identifier),
        receipt_store=receipts,
    )
    expect_error(GuardianControllerErrorCode.INVALID_STATE, valid.wait)
    expect_error(GuardianControllerErrorCode.INVALID_STATE, valid.cancel)
    expect_error(
        GuardianControllerErrorCode.INVALID_STATE,
        lambda: valid.acknowledge_terminal_persisted(expected_version=0),
    )
    expect_error(GuardianControllerErrorCode.INVALID_STATE, lambda: valid.process_group_id)
    expect_error(
        GuardianControllerErrorCode.INVALID_CONFIGURATION,
        lambda: GuardianController(
            argv=("relative",),
            cwd=tmp_path,
            limits=limits(),
            job_id=identifier,
            execution_reference=operation(2),
            store=store,
            workspace_root=workspace_root,
            owner_component="a" * 64,
            job_component=workspace_component(identifier),
            receipt_store=receipts,
        ),
    )
    expect_error(
        GuardianControllerErrorCode.INVALID_CONFIGURATION,
        lambda: GuardianController(
            argv=(sys.executable,),
            cwd=tmp_path,
            limits=limits(),
            job_id=identifier,
            execution_reference=operation(2),
            store=store,
            workspace_root=workspace_root,
            owner_component="bad",
            job_component="b" * 64,
            receipt_store=receipts,
        ),
    )


@pytest.mark.parametrize(
    "line",
    [
        b"bad\n",
        b"X succeeded none\n",
        b"F unknown none\n",
        b"F succeeded wall\n",
        b"F timed_out none\n",
        b"F limit_exceeded wall\n",
        b"F failed memory\n",
        b"\xff\n",
    ],
)
def test_result_protocol_rejects_malformed_combinations(line: bytes) -> None:
    expect_error(
        GuardianControllerErrorCode.CONTROL_FAILED,
        lambda: guardian._parse_result_line(line),
    )


def test_protocol_helpers_are_strict_and_content_free(monkeypatch: pytest.MonkeyPatch) -> None:
    argv = (sys.executable, "worker", "arg")
    assert guardian._decoded_argv(guardian._encoded_argv(argv)) == argv
    for invalid in ("!", guardian._encoded_argv(()), guardian._encoded_argv(("",))):
        with pytest.raises(ValueError):
            guardian._decoded_argv(invalid)

    read_fd, write_fd = os.pipe()
    os.write(write_fd, SECRET)
    os.close(write_fd)
    assert guardian._read_secret(read_fd) == SECRET
    os.close(read_fd)

    monkeypatch.setattr(os, "write", lambda _fd, _content: 0)
    with pytest.raises(OSError):
        guardian._write_all(1, b"x")
    guardian._safe_protocol_write(1, b"x")
    guardian._safe_close(999_999)
    assert guardian._result_line(ProcessResult(ProcessOutcome.SUCCEEDED)) == b"F succeeded none\n"
    assert guardian._parse_result_line(b"F timed_out wall\n") == ProcessResult(
        ProcessOutcome.TIMED_OUT,
        ProcessLimit.WALL,
    )
    empty_read, empty_write = os.pipe()
    os.close(empty_write)
    with pytest.raises(ValueError):
        guardian._read_secret(empty_read)
    os.close(empty_read)


def test_secret_reader_rejects_oversize_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guardian, "_MAX_SECRET_BYTES", 2)
    chunks = iter((b"ab", b"c"))
    monkeypatch.setattr(os, "read", lambda _fd, _size: next(chunks))
    with pytest.raises(ValueError):
        guardian._read_secret(1)


def test_guardian_cleanup_failure_writes_non_proving_receipt(tmp_path: Path) -> None:
    workspace_root, receipt_root = roots(tmp_path)
    identifier = fixed_job()
    component = workspace_component(identifier)
    owner = "a" * 64
    workspaces = WorkspaceManager(workspace_root)
    layout = workspaces.create(owner, component)
    external = tmp_path / "external"
    external.write_bytes(b"preserve")
    (layout.input / ("a" * 64)).symlink_to(external)

    guardian._guardian_cleanup(
        job_id=identifier,
        execution_reference=operation(2),
        workspace_root=workspace_root,
        owner_component=owner,
        job_component=component,
        receipt_root=receipt_root,
        signing_secret=SECRET,
    )
    receipts = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    item = receipts.read(identifier, operation(2))
    assert item is not None
    assert item.workspace_verified_absent is False
    assert not receipts.proves_recovery(
        identifier,
        operation(2),
        at_utc=datetime.now(UTC),
    )
    assert external.read_bytes() == b"preserve"


def test_private_guardian_entry_rejects_malformed_contract() -> None:
    assert guardian._run_guardian([]) == 126
    assert guardian._run_guardian([guardian._GUARDIAN_MARKER] + ["bad"] * 10) == 126
    assert (
        guardian._run_guardian([guardian._GUARDIAN_MARKER, "-1", "-1", "-1"] + ["bad"] * 9) == 126
    )


def test_private_guardian_entry_success_and_app_loss_cleanup_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_root, receipt_root = roots(tmp_path)
    identifier = fixed_job()
    component = workspace_component(identifier)
    owner = "a" * 64
    WorkspaceManager(workspace_root).create(owner, component)
    control_read, control_write = os.pipe()
    result_read, result_write = os.pipe()
    secret_read, secret_write = os.pipe()
    os.write(secret_write, SECRET)
    os.close(secret_write)

    fake = Mock()
    fake.process_group_id = 321
    fake.start.return_value = None
    monkeypatch.setattr(guardian, "ProcessController", Mock(return_value=fake))
    monkeypatch.setattr(
        guardian,
        "_guardian_wait",
        Mock(return_value=(ProcessResult(ProcessOutcome.CANCELLED), True)),
    )
    cleanup = Mock()
    monkeypatch.setattr(guardian, "_guardian_cleanup", cleanup)
    arguments = [
        guardian._GUARDIAN_MARKER,
        str(control_read),
        str(result_write),
        str(secret_read),
        identifier.to_urlsafe(),
        str(workspace_root),
        owner,
        component,
        str(receipt_root),
        limits().model_dump_json(),
        guardian._encoded_argv((sys.executable, str(WORKER.resolve()), "success")),
        operation(2),
        str(os.open(tmp_path, guardian._DIRECTORY_FLAGS)),
    ]
    assert guardian._run_guardian(arguments) == 0
    os.close(control_write)
    protocol = os.read(result_read, 1024)
    os.close(result_read)
    assert protocol == b"R 321\nF cancelled none\nX\n"
    cleanup.assert_called_once()

    control_read, control_write = os.pipe()
    result_read, result_write = os.pipe()
    secret_read, secret_write = os.pipe()
    os.write(secret_write, SECRET)
    os.close(secret_write)
    completed = list(arguments)
    completed[1:4] = [str(control_read), str(result_write), str(secret_read)]
    completed[12] = str(os.open(tmp_path, guardian._DIRECTORY_FLAGS))
    os.write(control_write, b"A")
    monkeypatch.setattr(
        guardian,
        "_guardian_wait",
        Mock(return_value=(ProcessResult(ProcessOutcome.SUCCEEDED), False)),
    )
    cleanup.reset_mock()
    assert guardian._run_guardian(completed) == 0
    os.close(control_write)
    assert os.read(result_read, 1024) == b"R 321\nF succeeded none\nA\n"
    os.close(result_read)
    cleanup.assert_not_called()

    bad_read, bad_write = os.pipe()
    bad_result_read, bad_result_write = os.pipe()
    bad_secret_read, bad_secret_write = os.pipe()
    os.write(bad_secret_write, SECRET)
    os.close(bad_secret_write)
    bad = list(arguments)
    bad[1:4] = [str(bad_read), str(bad_result_write), str(bad_secret_read)]
    bad[12] = str(os.open(tmp_path, guardian._DIRECTORY_FLAGS))
    bad[7] = "b" * 64
    assert guardian._run_guardian(bad) == 126
    os.close(bad_write)
    assert os.read(bad_result_read, 1024) == b"E\n"
    os.close(bad_result_read)

    invalid_reference_read, invalid_reference_write = os.pipe()
    invalid_result_read, invalid_result_write = os.pipe()
    invalid_secret_read, invalid_secret_write = os.pipe()
    os.write(invalid_secret_write, SECRET)
    os.close(invalid_secret_write)
    invalid_reference = list(arguments)
    invalid_reference[1:4] = [
        str(invalid_reference_read),
        str(invalid_result_write),
        str(invalid_secret_read),
    ]
    invalid_reference[11] = "bad"
    invalid_reference[12] = str(os.open(tmp_path, guardian._DIRECTORY_FLAGS))
    assert guardian._run_guardian(invalid_reference) == 126
    os.close(invalid_reference_write)
    assert os.read(invalid_result_read, 1024) == b"E\n"
    os.close(invalid_result_read)


def test_guardian_entry_reaps_worker_and_attempts_cleanup_after_control_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_root, receipt_root = roots(tmp_path)
    identifier = fixed_job()
    owner = "a" * 64
    component = workspace_component(identifier)
    WorkspaceManager(workspace_root).create(owner, component)
    fake = Mock()
    fake.process_group_id = 321
    fake.start.return_value = None
    fake.cancel.return_value = ProcessResult(ProcessOutcome.CANCELLED)
    monkeypatch.setattr(guardian, "ProcessController", Mock(return_value=fake))
    monkeypatch.setattr(
        guardian,
        "_guardian_wait",
        Mock(side_effect=ProcessControllerError(ProcessControllerErrorCode.CONTROL_FAILED)),
    )
    cleanup = Mock()
    monkeypatch.setattr(guardian, "_guardian_cleanup", cleanup)

    def invoke() -> tuple[int, bytes]:
        control_read, control_write = os.pipe()
        result_read, result_write = os.pipe()
        secret_read, secret_write = os.pipe()
        os.write(secret_write, SECRET)
        os.close(secret_write)
        arguments = [
            guardian._GUARDIAN_MARKER,
            str(control_read),
            str(result_write),
            str(secret_read),
            identifier.to_urlsafe(),
            str(workspace_root),
            owner,
            component,
            str(receipt_root),
            limits().model_dump_json(),
            guardian._encoded_argv((sys.executable, str(WORKER.resolve()), "success")),
            operation(2),
            str(os.open(tmp_path, guardian._DIRECTORY_FLAGS)),
        ]
        status = guardian._run_guardian(arguments)
        os.close(control_write)
        protocol = os.read(result_read, 1024)
        os.close(result_read)
        return status, protocol

    assert invoke() == (126, b"R 321\nE\n")
    fake.cancel.assert_called_once_with()
    cleanup.assert_called_once()

    fake.cancel.reset_mock(side_effect=True)
    fake.cancel.side_effect = ProcessControllerError(ProcessControllerErrorCode.REAP_FAILED)
    cleanup.reset_mock()
    assert invoke() == (126, b"R 321\nE\n")
    fake.reap_until_absent.assert_called_once_with()
    cleanup.assert_called_once()

    fake.cancel.reset_mock(side_effect=True)
    fake.reap_until_absent.reset_mock()
    fake.cancel.return_value = ProcessResult(ProcessOutcome.CANCELLED)
    cleanup.side_effect = OSError
    assert invoke() == (126, b"R 321\nE\n")

    monkeypatch.setattr(
        guardian,
        "_guardian_wait",
        Mock(return_value=(ProcessResult(ProcessOutcome.CANCELLED), True)),
    )
    assert invoke() == (126, b"R 321\nF cancelled none\nE\n")


def test_start_failure_and_protocol_monitor_failure_are_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item, _workspaces, _layout, _receipts, _job_id = controller(tmp_path, "success")

    def fail_start(*_args: object, **_kwargs: object) -> subprocess.Popen[bytes]:
        raise OSError("CANARY")

    monkeypatch.setattr(subprocess, "Popen", fail_start)
    expect_error(GuardianControllerErrorCode.START_FAILED, item.start)

    broken_root = tmp_path / "broken"
    broken_root.mkdir(mode=0o700)
    broken, _manager, _layout, _receipts, _identifier = controller(broken_root, "success")
    broken._started = True
    broken._result_read = -1
    broken._monitor_protocol()
    assert broken._error is not None
    assert broken._error.code is GuardianControllerErrorCode.CONTROL_FAILED


def test_guardian_start_rejects_cwd_rename_swap_before_spawning(tmp_path: Path) -> None:
    item, _workspaces, _layout, _receipts, _job_id = controller(tmp_path, "success")
    original = tmp_path.with_name(tmp_path.name + "-original")
    tmp_path.rename(original)
    tmp_path.mkdir()

    expect_error(GuardianControllerErrorCode.START_FAILED, item.start)
    assert item._guardian is None


def test_guardian_partial_pipe_failure_closes_every_allocated_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item, _workspaces, _layout, _receipts, _job_id = controller(tmp_path, "success")
    real_pipe = os.pipe
    allocated: list[int] = []
    calls = 0

    def fail_third_pipe() -> tuple[int, int]:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("CANARY_EMFILE")
        pair = real_pipe()
        allocated.extend(pair)
        return pair

    monkeypatch.setattr(guardian.os, "pipe", fail_third_pipe)
    error = expect_error(GuardianControllerErrorCode.START_FAILED, item.start)
    assert "CANARY" not in str(error)
    for descriptor in allocated:
        with pytest.raises(OSError):
            os.fstat(descriptor)


def test_monitor_thread_start_failure_closes_liveness_pipe_and_reaps_guardian(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item, _workspaces, _layout, _receipts, _job_id = controller(tmp_path, "success")
    guardian_process = Mock(wait=Mock(return_value=0))
    popen = Mock(return_value=guardian_process)
    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(
        threading.Thread,
        "start",
        Mock(side_effect=RuntimeError),
    )
    expect_error(GuardianControllerErrorCode.START_FAILED, item.start)
    guardian_process.wait.assert_called_once_with()
    assert item._control_write == item._result_read == -1
    assert popen.call_args.kwargs["start_new_session"] is True


@pytest.mark.parametrize(
    ("protocol", "guardian_status"),
    [
        (b"X 1\n", 0),
        (b"R -1\n", 0),
        (b"R 1\n", 0),
        (b"R 1\n" + b"x" * guardian._MAX_PROTOCOL_LINE, 0),
        (b"R 1\nF succeeded none\nX\n", 0),
        (b"R 1\nF succeeded none\nQ\n", 0),
        (b"R 1\nF succeeded none\nA\n", 1),
    ],
)
def test_protocol_monitor_rejects_malformed_ready_final_and_guardian_status(
    tmp_path: Path,
    protocol: bytes,
    guardian_status: int,
) -> None:
    item, _workspaces, _layout, _receipts, _job_id = controller(tmp_path, "success")
    read_fd, write_fd = os.pipe()
    os.write(write_fd, protocol)
    os.close(write_fd)
    item._started = True
    item._result_read = read_fd
    item._guardian = cast(Any, Mock(wait=Mock(return_value=guardian_status)))
    item._monitor_protocol()
    assert item._error is not None
    assert item._error.code is GuardianControllerErrorCode.CONTROL_FAILED


def test_protocol_monitor_accepts_confirmed_result_without_open_control_descriptor(
    tmp_path: Path,
) -> None:
    item, _workspaces, _layout, _receipts, _job_id = controller(tmp_path, "success")
    read_fd, write_fd = os.pipe()
    os.write(write_fd, b"R 321\nF succeeded none\nA\n")
    os.close(write_fd)
    item._started = True
    item._result_read = read_fd
    item._control_write = -1
    item._guardian = cast(Any, Mock(wait=Mock(return_value=0)))
    item._monitor_protocol()
    assert item.result == ProcessResult(ProcessOutcome.SUCCEEDED)
    assert item._ack_confirmed is True


def test_protocol_monitor_error_closes_control_reaps_child_and_preserves_prior_error(
    tmp_path: Path,
) -> None:
    item, _workspaces, _layout, _receipts, _job_id = controller(tmp_path, "success")
    result_read, result_write = os.pipe()
    control_read, control_write = os.pipe()
    os.write(result_write, b"bad\n")
    os.close(result_write)
    item._started = True
    item._result_read = result_read
    item._control_write = control_write
    item._error = GuardianControllerError(GuardianControllerErrorCode.START_FAILED)
    child = Mock(wait=Mock(side_effect=OSError))
    item._guardian = cast(Any, child)
    item._monitor_protocol()
    assert item._error.code is GuardianControllerErrorCode.START_FAILED
    assert item._guardian_finished is True
    assert item._control_write == -1
    child.wait.assert_called_once_with()
    os.close(control_read)


def test_wait_cancel_and_start_timeout_surface_stored_control_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item, _workspaces, _layout, _receipts, _job_id = controller(tmp_path, "success")
    item._started = True
    item._error = GuardianControllerError(GuardianControllerErrorCode.CONTROL_FAILED)
    expect_error(GuardianControllerErrorCode.CONTROL_FAILED, item.wait)
    item._control_write = 999_999
    expect_error(GuardianControllerErrorCode.CONTROL_FAILED, item.cancel)

    fresh_root = tmp_path / "fresh"
    fresh_root.mkdir(mode=0o700)
    fresh, _manager, _layout, _receipts, _identifier = controller(fresh_root, "success")
    fresh._started = True
    fresh._control_write = -1
    expect_error(GuardianControllerErrorCode.INVALID_STATE, fresh.cancel)

    write_error_root = tmp_path / "write-error"
    write_error_root.mkdir(mode=0o700)
    write_error, _manager, _layout, _receipts, _identifier = controller(write_error_root, "success")
    write_error._started = True
    write_error._control_write = 999_999
    expect_error(GuardianControllerErrorCode.CONTROL_FAILED, write_error.cancel)

    timeout_root = tmp_path / "start-timeout"
    timeout_root.mkdir(mode=0o700)
    timeout_item, _manager, _layout, _receipts, _identifier = controller(timeout_root, "success")
    guardian_process = Mock()
    monkeypatch.setattr(subprocess, "Popen", Mock(return_value=guardian_process))
    monkeypatch.setattr(guardian, "_write_all", lambda _descriptor, _content: None)
    monkeypatch.setattr(threading.Thread, "start", lambda _thread: None)
    monotonic = iter((0.0, 6.0))
    monkeypatch.setattr(time, "monotonic", lambda: next(monotonic))
    expect_error(GuardianControllerErrorCode.START_FAILED, timeout_item.start)
    assert timeout_item._error is not None
    assert timeout_item._control_write == -1


def test_terminal_ack_rejects_prior_error_late_ack_and_pipe_failure(tmp_path: Path) -> None:
    early_root = tmp_path / "early"
    early_root.mkdir(mode=0o700)
    early, _manager, _layout, _receipts, _identifier = controller(early_root, "success")
    early._started = True
    early._result = ProcessResult(ProcessOutcome.SUCCEEDED)
    early._control_write = 999_999
    running_version = early._store.list_jobs_for_maintenance()[0].version
    expect_error(
        GuardianControllerErrorCode.CONTROL_FAILED,
        lambda: early.acknowledge_terminal_persisted(expected_version=running_version),
    )
    assert early._error is None

    store_error_root = tmp_path / "store-error"
    store_error_root.mkdir(mode=0o700)
    store_error, _manager, _layout, _receipts, _identifier = controller(
        store_error_root,
        "success",
    )
    store_error._started = True
    store_error._result = ProcessResult(ProcessOutcome.SUCCEEDED)
    store_error._store.terminal_transition_matches = Mock(  # type: ignore[method-assign]
        side_effect=JobStoreError(JobStoreErrorCode.DATABASE_FAILURE)
    )
    expect_error(
        GuardianControllerErrorCode.CONTROL_FAILED,
        lambda: store_error.acknowledge_terminal_persisted(expected_version=1),
    )

    prior, _manager, _layout, _receipts, _identifier = controller(tmp_path, "success")
    prior._started = True
    prior._result = ProcessResult(ProcessOutcome.SUCCEEDED)
    prior._error = GuardianControllerError(GuardianControllerErrorCode.START_FAILED)
    expect_error(
        GuardianControllerErrorCode.START_FAILED,
        lambda: prior.acknowledge_terminal_persisted(expected_version=0),
    )

    late_root = tmp_path / "late"
    late_root.mkdir(mode=0o700)
    late, _manager, _layout, _receipts, _identifier = controller(late_root, "success")
    late._started = True
    late._result = ProcessResult(ProcessOutcome.SUCCEEDED)
    late_version = persist_terminal(late, late._result)
    late._guardian_finished = True
    expect_error(
        GuardianControllerErrorCode.CONTROL_FAILED,
        lambda: late.acknowledge_terminal_persisted(expected_version=late_version),
    )

    late._acknowledged = True
    expect_error(
        GuardianControllerErrorCode.CONTROL_FAILED,
        lambda: late.acknowledge_terminal_persisted(expected_version=late_version),
    )

    failed_root = tmp_path / "failed"
    failed_root.mkdir(mode=0o700)
    failed, _manager, _layout, _receipts, _identifier = controller(failed_root, "success")
    failed._started = True
    failed._result = ProcessResult(ProcessOutcome.SUCCEEDED)
    failed_version = persist_terminal(failed, failed._result)
    failed._control_write = 999_999
    expect_error(
        GuardianControllerErrorCode.CONTROL_FAILED,
        lambda: failed.acknowledge_terminal_persisted(expected_version=failed_version),
    )


def test_terminal_ack_surfaces_error_raised_while_waiting(tmp_path: Path) -> None:
    item, _manager, _layout, _receipts, _identifier = controller(tmp_path, "success")
    control_read, control_write = os.pipe()
    item._started = True
    item._result = ProcessResult(ProcessOutcome.SUCCEEDED)
    terminal_version = persist_terminal(item, item._result)
    item._control_write = control_write
    errors: list[GuardianControllerError] = []

    def acknowledge() -> None:
        try:
            item.acknowledge_terminal_persisted(expected_version=terminal_version)
        except GuardianControllerError as error:
            errors.append(error)

    thread = threading.Thread(target=acknowledge)
    thread.start()
    deadline = time.monotonic() + 2
    while not item._acknowledged and time.monotonic() < deadline:
        time.sleep(0.01)
    with item._condition:
        item._error = GuardianControllerError(GuardianControllerErrorCode.CONTROL_FAILED)
        item._condition.notify_all()
    thread.join(timeout=2)
    assert [error.code for error in errors] == [GuardianControllerErrorCode.CONTROL_FAILED]
    assert os.read(control_read, 1) == b"A"
    os.close(control_read)
    os.close(control_write)


class _FakeProcessController:
    def __init__(
        self,
        *,
        result: ProcessResult | None = None,
        error: ProcessControllerError | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.cancel_calls = 0

    def wait(self) -> ProcessResult:
        if self._error is not None:
            raise self._error
        if self._result is None:
            time.sleep(0.2)
            return ProcessResult(ProcessOutcome.SUCCEEDED)
        return self._result

    def cancel(self) -> ProcessResult:
        self.cancel_calls += 1
        return ProcessResult(ProcessOutcome.CANCELLED)


def test_guardian_wait_handles_worker_result_error_cancel_eof_and_invalid_command() -> None:
    read_fd, write_fd = os.pipe()
    successful = cast(
        Any,
        _FakeProcessController(result=ProcessResult(ProcessOutcome.SUCCEEDED)),
    )
    assert guardian._guardian_wait(successful, read_fd) == (
        ProcessResult(ProcessOutcome.SUCCEEDED),
        False,
    )
    os.close(read_fd)
    os.close(write_fd)

    read_fd, write_fd = os.pipe()
    failed = cast(
        Any,
        _FakeProcessController(
            error=ProcessControllerError(ProcessControllerErrorCode.CONTROL_FAILED)
        ),
    )
    with pytest.raises(ProcessControllerError):
        guardian._guardian_wait(failed, read_fd)
    os.close(read_fd)
    os.close(write_fd)

    for command, app_lost in ((b"C", False), (b"", True)):
        read_fd, write_fd = os.pipe()
        waiting = cast(Any, _FakeProcessController())
        if command:
            os.write(write_fd, command)
        os.close(write_fd)
        assert guardian._guardian_wait(waiting, read_fd) == (
            ProcessResult(ProcessOutcome.CANCELLED),
            app_lost,
        )
        assert waiting.cancel_calls == 1
        os.close(read_fd)

    read_fd, write_fd = os.pipe()
    os.write(write_fd, b"X")
    waiting = cast(Any, _FakeProcessController())
    assert guardian._guardian_wait(waiting, read_fd) == (
        ProcessResult(ProcessOutcome.CANCELLED),
        True,
    )
    assert waiting.cancel_calls == 1
    os.close(read_fd)
    os.close(write_fd)


def test_guardian_wait_repolls_when_control_pipe_is_idle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Outcomes:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self._reads = 0

        def put(self, _value: object) -> None:
            return

        def get_nowait(self) -> ProcessResult:
            self._reads += 1
            if self._reads == 1:
                raise guardian.queue.Empty
            return ProcessResult(ProcessOutcome.SUCCEEDED)

    monkeypatch.setattr(guardian.queue, "Queue", Outcomes)
    monkeypatch.setattr(threading.Thread, "start", lambda _thread: None)
    monkeypatch.setattr(guardian.select, "select", lambda *_args: ([], [], []))
    assert guardian._guardian_wait(cast(Any, Mock()), 1) == (
        ProcessResult(ProcessOutcome.SUCCEEDED),
        False,
    )


def test_guardian_wait_thread_start_failure_cancels_and_requires_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    waiting = cast(Any, _FakeProcessController())
    monkeypatch.setattr(threading.Thread, "start", Mock(side_effect=RuntimeError))
    assert guardian._guardian_wait(waiting, 1) == (
        ProcessResult(ProcessOutcome.CANCELLED),
        True,
    )
    assert waiting.cancel_calls == 1


@pytest.mark.parametrize(
    ("commands", "expected"),
    [
        (b"A", True),
        (b"CA", True),
        (b"X", False),
        (b"", False),
    ],
)
def test_persistence_ack_accepts_only_explicit_ack(commands: bytes, expected: bool) -> None:
    read_fd, write_fd = os.pipe()
    if commands:
        os.write(write_fd, commands)
    os.close(write_fd)
    assert guardian._await_persistence_ack(read_fd) is expected
    os.close(read_fd)


def test_persistence_ack_timeout_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    moments = iter((0.0, 6.0))
    monkeypatch.setattr(time, "monotonic", lambda: next(moments))
    assert not guardian._await_persistence_ack(1)


def test_persistence_ack_select_timeout_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guardian.select, "select", lambda *_args: ([], [], []))
    assert not guardian._await_persistence_ack(1)


def test_guardian_cleanup_missing_workspace_writes_zero_count_proof(tmp_path: Path) -> None:
    workspace_root, receipt_root = roots(tmp_path)
    identifier = fixed_job()
    guardian._guardian_cleanup(
        job_id=identifier,
        execution_reference=operation(2),
        workspace_root=workspace_root,
        owner_component="a" * 64,
        job_component=workspace_component(identifier),
        receipt_root=receipt_root,
        signing_secret=SECRET,
    )
    item = RecoveryReceiptStore(receipt_root, signing_secret=SECRET).read(
        identifier,
        operation(2),
    )
    assert item is not None
    assert item.workspace_verified_absent is True
    assert item.file_count == item.byte_count == 0


def test_constructor_rejects_type_confusion(tmp_path: Path) -> None:
    workspace_root, receipt_root = roots(tmp_path)
    database_root = tmp_path / "database"
    database_root.mkdir(mode=0o700)
    store = SQLiteJobStore(database_root / "control.sqlite3", owner_secret=OWNER_SECRET)
    receipts = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    identifier = fixed_job()
    expect_error(
        GuardianControllerErrorCode.INVALID_CONFIGURATION,
        lambda: GuardianController(
            argv=(sys.executable,),
            cwd=tmp_path,
            limits=limits(),
            job_id=cast(Any, object()),
            execution_reference=operation(2),
            store=store,
            workspace_root=workspace_root,
            owner_component="a" * 64,
            job_component=workspace_component(identifier),
            receipt_store=receipts,
        ),
    )
