from __future__ import annotations

import os
import resource
import signal
import subprocess
import sys
import threading
import time
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import pytest

import delta_lemmata.process_controller as process_control
from delta_lemmata.job_policy import WorkerLimitProfile
from delta_lemmata.process_controller import (
    PROCESS_CONTROL_BOUNDARY,
    ProcessController,
    ProcessControllerError,
    ProcessControllerErrorCode,
    ProcessLimit,
    ProcessOutcome,
    ProcessResult,
)

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_worker.py"
PAYLOAD_CANARY = "SYNTHETIC_PAYLOAD_MUST_NOT_ESCAPE"


def limits(
    *,
    wall: int = 5,
    cpu: int = 4,
    memory: int = 128 * 1024 * 1024,
    processes: int = 8,
    grace: int = 1,
) -> WorkerLimitProfile:
    return WorkerLimitProfile(
        profile_version="synthetic-worker-limits-v1",
        wall_time_seconds=wall,
        cpu_time_seconds=cpu,
        memory_bytes=memory,
        max_processes=processes,
        terminate_grace_seconds=grace,
    )


def controller(
    tmp_path: Path,
    mode: str,
    *arguments: str,
    profile: WorkerLimitProfile | None = None,
) -> ProcessController:
    return ProcessController(
        argv=(sys.executable, str(FIXTURE), mode, *arguments),
        cwd=tmp_path,
        limits=profile or limits(),
    )


def wait_for_group_size(process_group_id: int, expected: int) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if process_control._count_process_group("/bin/ps", process_group_id) >= expected:
            return
        time.sleep(0.01)
    raise AssertionError("synthetic process group did not reach expected size")


def expect_error(
    code: ProcessControllerErrorCode,
    action: object,
) -> ProcessControllerError:
    with pytest.raises(ProcessControllerError) as captured:
        assert callable(action)
        action()
    error = captured.value
    assert error.code is code
    assert str(error) == code.value
    assert repr(error) == f"ProcessControllerError('{code.value}')"
    assert error.__cause__ is None
    assert error.__context__ is None
    return error


def test_fixed_posix_launch_contract_is_content_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("DELTA_SECRET_CANARY", PAYLOAD_CANARY)
    result = controller(tmp_path, "contract", str(tmp_path)).run()

    assert result == ProcessResult(ProcessOutcome.SUCCEEDED)
    assert result.boundary == PROCESS_CONTROL_BOUNDARY == "local_posix_app_managed"
    assert capfd.readouterr() == ("", "")
    assert not hasattr(result, "stdout")
    assert not hasattr(result, "stderr")
    assert not hasattr(result, "traceback")
    assert PAYLOAD_CANARY not in repr(result)
    assert not tuple(tmp_path.iterdir())


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("success", ProcessResult(ProcessOutcome.SUCCEEDED)),
        ("failure", ProcessResult(ProcessOutcome.FAILED)),
        ("traceback", ProcessResult(ProcessOutcome.FAILED)),
        ("crash", ProcessResult(ProcessOutcome.CRASHED)),
        (
            "memory-limit",
            ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.MEMORY),
        ),
    ],
)
def test_completion_failure_crash_and_memory_limit_are_stable(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    mode: str,
    expected: ProcessResult,
) -> None:
    runner = controller(tmp_path, mode)
    assert runner.run() == expected
    assert runner.wait() is runner.result
    assert runner.cancel() is runner.result
    captured = capfd.readouterr()
    assert PAYLOAD_CANARY not in captured.out + captured.err
    assert PAYLOAD_CANARY not in repr(runner.result)


def test_actual_cpu_rlimit_has_stable_limit_outcome(tmp_path: Path) -> None:
    result = controller(
        tmp_path,
        "cpu-limit",
        profile=limits(wall=4, cpu=1),
    ).run()
    assert result == ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.CPU)


def test_wall_timeout_uses_term_and_reaps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[signal.Signals | int] = []
    real_killpg = os.killpg

    def record(process_group_id: int, signal_number: signal.Signals | int) -> None:
        sent.append(signal_number)
        real_killpg(process_group_id, signal_number)

    monkeypatch.setattr(os, "killpg", record)
    runner = controller(tmp_path, "sleep", profile=limits(wall=1))
    runner.start()
    process_group_id = runner.process_group_id
    assert runner.wait() == ProcessResult(ProcessOutcome.TIMED_OUT, ProcessLimit.WALL)
    assert signal.SIGTERM in sent
    assert signal.SIGKILL not in sent
    assert not process_control._group_exists(process_group_id)


def test_timeout_escalates_from_term_to_kill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[signal.Signals | int] = []
    real_killpg = os.killpg

    def record(process_group_id: int, signal_number: signal.Signals | int) -> None:
        sent.append(signal_number)
        real_killpg(process_group_id, signal_number)

    monkeypatch.setattr(os, "killpg", record)
    runner = controller(tmp_path, "ignore-term", profile=limits(wall=1))
    runner.start()
    assert runner.wait() == ProcessResult(ProcessOutcome.TIMED_OUT, ProcessLimit.WALL)
    assert sent.index(signal.SIGTERM) < sent.index(signal.SIGKILL)


def test_nested_tree_cancel_is_idempotent_and_reaped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[signal.Signals | int] = []
    real_killpg = os.killpg

    def record(process_group_id: int, signal_number: signal.Signals | int) -> None:
        sent.append(signal_number)
        real_killpg(process_group_id, signal_number)

    monkeypatch.setattr(os, "killpg", record)
    runner = controller(tmp_path, "nested")
    runner.start()
    process_group_id = runner.process_group_id
    wait_for_group_size(process_group_id, 3)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(runner.cancel) for _ in range(2)]
    first, second = (future.result() for future in futures)

    assert first is second is runner.result
    assert first == ProcessResult(ProcessOutcome.CANCELLED)
    assert sent.index(signal.SIGTERM) < sent.index(signal.SIGKILL)
    assert not process_control._group_exists(process_group_id)


def test_pid_limit_terminates_and_reaps_group(tmp_path: Path) -> None:
    runner = controller(
        tmp_path,
        "process-limit",
        profile=limits(processes=2),
    )
    runner.start()
    process_group_id = runner.process_group_id
    assert runner.wait() == ProcessResult(
        ProcessOutcome.LIMIT_EXCEEDED,
        ProcessLimit.PROCESSES,
    )
    assert not process_control._group_exists(process_group_id)


def test_successful_parent_cleans_unexpected_remaining_child(tmp_path: Path) -> None:
    runner = controller(tmp_path, "orphan")
    runner.start()
    process_group_id = runner.process_group_id
    assert runner.wait() == ProcessResult(ProcessOutcome.SUCCEEDED)
    assert not process_control._group_exists(process_group_id)


def test_completion_cancel_timeout_race_publishes_one_result(tmp_path: Path) -> None:
    runner = controller(
        tmp_path,
        "delay",
        "1.0",
        profile=limits(wall=1),
    )
    runner.start()
    barrier = threading.Barrier(3)

    def wait_at_boundary(action: Callable[[], ProcessResult]) -> ProcessResult:
        barrier.wait()
        return action()

    with ThreadPoolExecutor(max_workers=2) as executor:
        waiting = executor.submit(wait_at_boundary, runner.wait)
        cancelling = executor.submit(wait_at_boundary, runner.cancel)
        barrier.wait()
    results = (waiting.result(), cancelling.result(), runner.wait(), runner.cancel())

    assert all(result is results[0] for result in results)
    assert results[0].outcome in {
        ProcessOutcome.SUCCEEDED,
        ProcessOutcome.CANCELLED,
        ProcessOutcome.TIMED_OUT,
    }


@pytest.mark.parametrize(
    ("argv", "cwd"),
    [
        (cast(tuple[str, ...], [sys.executable]), Path.cwd()),
        ((), Path.cwd()),
        (("python",), Path.cwd()),
        ((sys.executable, ""), Path.cwd()),
        ((sys.executable, "bad\0arg"), Path.cwd()),
        ((sys.executable,), Path("relative")),
    ],
)
def test_invalid_fixed_configuration_is_rejected(
    argv: tuple[str, ...],
    cwd: Path,
) -> None:
    expect_error(
        ProcessControllerErrorCode.INVALID_CONFIGURATION,
        lambda: ProcessController(argv=argv, cwd=cwd, limits=limits()),
    )


def test_invalid_profile_cwd_and_platform_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expect_error(
        ProcessControllerErrorCode.INVALID_CONFIGURATION,
        lambda: ProcessController(
            argv=(sys.executable,),
            cwd=tmp_path,
            limits=cast(WorkerLimitProfile, None),
        ),
    )
    expect_error(
        ProcessControllerErrorCode.INVALID_CONFIGURATION,
        lambda: ProcessController(
            argv=(sys.executable,),
            cwd=tmp_path / "missing",
            limits=limits(),
        ),
    )
    regular_file = tmp_path / "file"
    regular_file.touch()
    expect_error(
        ProcessControllerErrorCode.INVALID_CONFIGURATION,
        lambda: ProcessController(argv=(sys.executable,), cwd=regular_file, limits=limits()),
    )
    target = tmp_path / "target"
    target.mkdir()
    symlink = tmp_path / "link"
    symlink.symlink_to(target, target_is_directory=True)
    expect_error(
        ProcessControllerErrorCode.INVALID_CONFIGURATION,
        lambda: ProcessController(argv=(sys.executable,), cwd=symlink, limits=limits()),
    )

    monkeypatch.setattr(os, "name", "nt")
    expect_error(
        ProcessControllerErrorCode.POSIX_REQUIRED,
        lambda: ProcessController(argv=(sys.executable,), cwd=tmp_path, limits=limits()),
    )


def test_ps_discovery_and_group_count_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", lambda _path: False)
    expect_error(ProcessControllerErrorCode.POSIX_REQUIRED, process_control._find_ps)

    def bad_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess((), 0, b"not-a-process-group\n")

    monkeypatch.setattr(subprocess, "run", bad_run)
    with pytest.raises(process_control._ControlFailure):
        process_control._count_process_group("/bin/ps", 1)


def test_resource_limits_disable_core_and_clamp_hard_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applied: list[tuple[int, tuple[int, int]]] = []
    hard_limits = {
        resource.RLIMIT_CPU: resource.RLIM_INFINITY,
        resource.RLIMIT_AS: 50,
    }

    def getrlimit(limit_id: int) -> tuple[int, int]:
        return (10, hard_limits[limit_id])

    def setrlimit(limit_id: int, value: tuple[int, int]) -> None:
        applied.append((limit_id, value))

    monkeypatch.setattr(resource, "getrlimit", getrlimit)
    monkeypatch.setattr(resource, "setrlimit", setrlimit)
    monkeypatch.setattr(sys, "platform", "linux")
    process_control._apply_worker_limits(20, 100)

    assert applied == [
        (resource.RLIMIT_CORE, (0, 0)),
        (resource.RLIMIT_CPU, (20, 21)),
        (resource.RLIMIT_AS, (50, 50)),
    ]

    applied.clear()
    monkeypatch.setattr(sys, "platform", "darwin")
    process_control._apply_worker_limits(20, 100)
    assert applied == [
        (resource.RLIMIT_CORE, (0, 0)),
        (resource.RLIMIT_CPU, (20, 21)),
    ]


def test_lifecycle_state_and_start_failure_are_content_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "success")
    expect_error(ProcessControllerErrorCode.INVALID_STATE, runner.wait)
    expect_error(ProcessControllerErrorCode.INVALID_STATE, runner.cancel)
    expect_error(ProcessControllerErrorCode.INVALID_STATE, lambda: runner.process_group_id)
    runner.start()
    expect_error(ProcessControllerErrorCode.INVALID_STATE, runner.start)
    assert runner.wait() == ProcessResult(ProcessOutcome.SUCCEEDED)

    failed = controller(tmp_path, "success")

    def fail_start(*_args: object, **_kwargs: object) -> subprocess.Popen[bytes]:
        raise OSError(PAYLOAD_CANARY)

    monkeypatch.setattr(subprocess, "Popen", fail_start)
    error = expect_error(ProcessControllerErrorCode.START_FAILED, failed.start)
    assert PAYLOAD_CANARY not in "".join(traceback.format_exception(error))


def test_private_stable_classification_and_signal_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert ProcessController._classify_completion(
        process_control.SYNTHETIC_PROCESS_LIMIT_EXIT
    ) == ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.PROCESSES)
    assert process_control._group_exists(os.getpgrp())

    def denied(_group: int, _signal: signal.Signals | int) -> None:
        raise PermissionError

    monkeypatch.setattr(os, "killpg", denied)
    assert process_control._group_exists(123)
    with pytest.raises(process_control._ReapFailure):
        process_control._signal_group(123, signal.SIGTERM)

    def missing(_group: int, _signal: signal.Signals | int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(os, "killpg", missing)
    assert not process_control._group_exists(123)
    process_control._signal_group(123, signal.SIGTERM)


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["wrong", "1", "1", sys.executable],
        [process_control._LAUNCHER_MARKER, "bad", "1", sys.executable],
        [process_control._LAUNCHER_MARKER, "0", "1", sys.executable],
        [process_control._LAUNCHER_MARKER, "1", "0", sys.executable],
        [process_control._LAUNCHER_MARKER, "1", "1", "relative"],
    ],
)
def test_launcher_rejects_malformed_contract(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        process_control._run_launcher(arguments)
    assert caught.value.code == 126


def test_launcher_applies_limits_and_fails_closed_if_exec_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applied: list[tuple[int, int]] = []

    def record_limits(cpu: int, memory: int) -> None:
        applied.append((cpu, memory))

    def fail_exec(*_args: object, **_kwargs: object) -> None:
        raise OSError(PAYLOAD_CANARY)

    monkeypatch.setattr(process_control, "_apply_worker_limits", record_limits)
    monkeypatch.setattr(os, "execve", fail_exec)
    with pytest.raises(SystemExit) as caught:
        process_control._run_launcher(
            [process_control._LAUNCHER_MARKER, "2", "1024", sys.executable]
        )
    assert caught.value.code == 126
    assert applied == [(2, 1024)]


def test_cancel_and_wait_surface_stored_errors_and_completion_race(tmp_path: Path) -> None:
    runner = controller(tmp_path, "success")
    runner._started = True
    runner._process = cast(subprocess.Popen[bytes], Mock(poll=Mock(return_value=None)))
    runner._error = ProcessControllerError(ProcessControllerErrorCode.CONTROL_FAILED)
    expect_error(ProcessControllerErrorCode.CONTROL_FAILED, runner.cancel)
    expect_error(ProcessControllerErrorCode.CONTROL_FAILED, runner.wait)

    completed = controller(tmp_path, "success")
    completed._started = True
    completed._process = cast(subprocess.Popen[bytes], Mock(poll=Mock(return_value=0)))
    expected = ProcessResult(ProcessOutcome.SUCCEEDED)
    completed._wait_locked = Mock(return_value=expected)  # type: ignore[method-assign]
    assert completed.cancel() is expected
    assert completed._winner is process_control._Winner.COMPLETION


def test_monitor_fail_closed_paths_publish_stable_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = controller(tmp_path, "success")
    missing._monitor()
    assert missing._error is not None
    assert missing._error.code is ProcessControllerErrorCode.CONTROL_FAILED

    def seeded() -> ProcessController:
        item = controller(tmp_path, "success")
        item._process = cast(subprocess.Popen[bytes], Mock())
        item._process_group_id = 123
        item._deadline = time.monotonic() + 1
        return item

    reap = seeded()
    monkeypatch.setattr(
        reap, "_choose_winner", Mock(return_value=process_control._Winner.COMPLETION)
    )
    monkeypatch.setattr(reap, "_settle", Mock(side_effect=process_control._ReapFailure))
    reap._monitor()
    assert reap._error is not None
    assert reap._error.code is ProcessControllerErrorCode.REAP_FAILED

    controlled = seeded()
    monkeypatch.setattr(
        controlled, "_choose_winner", Mock(side_effect=process_control._ControlFailure)
    )
    monkeypatch.setattr(controlled, "_force_reap", Mock(return_value=None))
    controlled._monitor()
    assert controlled._error is not None
    assert controlled._error.code is ProcessControllerErrorCode.CONTROL_FAILED

    unreaped = seeded()
    monkeypatch.setattr(unreaped, "_choose_winner", Mock(side_effect=OSError))
    monkeypatch.setattr(unreaped, "_force_reap", Mock(side_effect=process_control._ReapFailure))
    unreaped._monitor()
    assert unreaped._error is not None
    assert unreaped._error.code is ProcessControllerErrorCode.REAP_FAILED


def test_completion_detected_after_usage_sample_wins_deterministically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "success")
    process = cast(
        subprocess.Popen[bytes],
        Mock(poll=Mock(side_effect=(None, 0))),
    )
    monkeypatch.setattr(process_control, "_process_group_usage", Mock(return_value=(1, 1024)))

    assert (
        runner._choose_winner(process, 123, time.monotonic() + 1)
        is process_control._Winner.COMPLETION
    )


def test_private_settlement_and_reap_failure_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "success")
    process = cast(subprocess.Popen[bytes], Mock())
    monkeypatch.setattr(runner, "_terminate_and_reap", Mock(return_value=None))
    with pytest.raises(process_control._ControlFailure):
        runner._settle(process, 123, process_control._Winner.CONTROL_FAILURE)
    assert ProcessController._classify_completion(
        process_control.SYNTHETIC_MEMORY_LIMIT_EXIT
    ) == ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.MEMORY)

    monkeypatch.setattr(process_control, "_signal_group", Mock(return_value=None))
    monkeypatch.setattr(process_control, "_group_exists", Mock(return_value=False))
    successful = cast(subprocess.Popen[bytes], Mock(wait=Mock(return_value=0)))
    runner._force_reap(successful, 123)

    timed_out = cast(
        subprocess.Popen[bytes],
        Mock(wait=Mock(side_effect=subprocess.TimeoutExpired(("worker",), 1))),
    )
    with pytest.raises(process_control._ReapFailure):
        runner._force_reap(timed_out, 123)

    monkeypatch.setattr(process_control, "_group_exists", Mock(return_value=True))
    still_present = cast(subprocess.Popen[bytes], Mock(wait=Mock(return_value=0)))
    with pytest.raises(process_control._ReapFailure):
        runner._force_reap(still_present, 123)

    terminating = controller(tmp_path, "success")
    monkeypatch.setattr(terminating, "_wait_for_group_absence", Mock(return_value=False))
    with pytest.raises(process_control._ReapFailure):
        terminating._terminate_and_reap(still_present, 123)
