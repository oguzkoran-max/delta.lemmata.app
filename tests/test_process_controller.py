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


def test_start_descriptor_close_failure_remains_content_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "success")
    monkeypatch.setattr(subprocess, "Popen", Mock(side_effect=OSError(PAYLOAD_CANARY)))
    real_close = os.close

    def close_then_fail(descriptor: int) -> None:
        real_close(descriptor)
        raise OSError(PAYLOAD_CANARY)

    monkeypatch.setattr(process_control.os, "close", close_then_fail)
    error = expect_error(ProcessControllerErrorCode.START_FAILED, runner.start)
    assert PAYLOAD_CANARY not in "".join(traceback.format_exception(error))


def test_start_cwd_descriptor_open_failure_never_spawns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "success")
    popen = Mock()
    monkeypatch.setattr(process_control.os, "open", Mock(side_effect=OSError(PAYLOAD_CANARY)))
    monkeypatch.setattr(subprocess, "Popen", popen)

    error = expect_error(ProcessControllerErrorCode.START_FAILED, runner.start)
    assert PAYLOAD_CANARY not in "".join(traceback.format_exception(error))
    popen.assert_not_called()


def test_start_rejects_working_directory_rename_swap(tmp_path: Path) -> None:
    runner = controller(tmp_path, "success")
    original = tmp_path.with_name(tmp_path.name + "-original")
    tmp_path.rename(original)
    tmp_path.mkdir()

    expect_error(ProcessControllerErrorCode.START_FAILED, runner.start)
    assert runner._process is None


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
        [process_control._LAUNCHER_MARKER, "1", "1", "bad", sys.executable],
        [process_control._LAUNCHER_MARKER, "1", "1", "-1", sys.executable],
        [process_control._LAUNCHER_MARKER, "1", "1", "1", "relative"],
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
    cwd_descriptor = os.open(Path.cwd(), process_control._DIRECTORY_FLAGS)
    with pytest.raises(SystemExit) as caught:
        process_control._run_launcher(
            [
                process_control._LAUNCHER_MARKER,
                "2",
                "1024",
                str(cwd_descriptor),
                sys.executable,
            ]
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
    assert unreaped._error.code is ProcessControllerErrorCode.CONTROL_FAILED


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


def test_preselected_winner_returns_before_process_sampling(tmp_path: Path) -> None:
    runner = controller(tmp_path, "success")
    runner._winner = process_control._Winner.CANCELLATION
    process = cast(subprocess.Popen[bytes], Mock())

    assert (
        runner._choose_winner(process, 123, time.monotonic() + 1)
        is process_control._Winner.CANCELLATION
    )
    process.poll.assert_not_called()


def test_memory_sample_and_settlement_are_platform_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "success")
    process = cast(
        subprocess.Popen[bytes],
        Mock(poll=Mock(side_effect=(None, None))),
    )
    monkeypatch.setattr(
        process_control,
        "_process_group_usage",
        Mock(return_value=(1, runner._limits.memory_bytes + 1)),
    )
    winner = runner._choose_winner(process, 123, time.monotonic() + 1)
    assert winner is process_control._Winner.MEMORY_LIMIT

    monkeypatch.setattr(runner, "_terminate_and_reap", Mock(return_value=None))
    assert runner._settle(process, 123, winner) == ProcessResult(
        ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.MEMORY
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


def test_descendant_count_and_leader_observation_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess((), 0, b"malformed\n"),
    )
    with pytest.raises(process_control._ControlFailure):
        process_control._count_group_descendants("/bin/ps", 123, 123)

    process = cast(subprocess.Popen[bytes], Mock(pid=123))
    monkeypatch.setattr(os, "waitid", Mock(side_effect=ChildProcessError))
    with pytest.raises(process_control._ReapFailure):
        process_control._leader_exited(process)


def test_completed_group_reap_escalation_and_postconditions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "success")
    process = cast(subprocess.Popen[bytes], Mock(pid=123, wait=Mock(return_value=0)))
    signals: list[signal.Signals] = []
    monkeypatch.setattr(
        process_control,
        "_signal_group",
        lambda _group, signal_number: signals.append(signal_number),
    )
    monkeypatch.setattr(process_control, "_count_group_descendants", Mock(return_value=1))

    monkeypatch.setattr(runner, "_wait_for_descendant_absence", Mock(return_value=True))
    monkeypatch.setattr(process_control, "_group_exists", Mock(return_value=False))
    assert runner._reap_completed_group(process, 123) == 0
    assert signals == [signal.SIGTERM]

    signals.clear()
    monkeypatch.setattr(runner, "_wait_for_descendant_absence", Mock(side_effect=(False, False)))
    with pytest.raises(process_control._ReapFailure):
        runner._reap_completed_group(process, 123)
    assert signals == [signal.SIGTERM, signal.SIGKILL]

    signals.clear()
    monkeypatch.setattr(runner, "_wait_for_descendant_absence", Mock(side_effect=(False, True)))
    monkeypatch.setattr(process_control, "_group_exists", Mock(return_value=False))
    assert runner._reap_completed_group(process, 123) == 0
    assert signals == [signal.SIGTERM, signal.SIGKILL]

    monkeypatch.setattr(process_control, "_count_group_descendants", Mock(return_value=0))
    timed_out = cast(
        subprocess.Popen[bytes],
        Mock(pid=123, wait=Mock(side_effect=subprocess.TimeoutExpired(("worker",), 1))),
    )
    with pytest.raises(process_control._ReapFailure):
        runner._reap_completed_group(timed_out, 123)

    monkeypatch.setattr(process_control, "_group_exists", Mock(return_value=True))
    with pytest.raises(process_control._ReapFailure):
        runner._reap_completed_group(process, 123)


def test_descendant_absence_performs_final_boundary_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "success", profile=limits(grace=1))
    moments = iter((0.0, 0.0, 2.0))
    monkeypatch.setattr(time, "monotonic", lambda: next(moments))
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    descendants = Mock(side_effect=(1, 0))
    monkeypatch.setattr(process_control, "_count_group_descendants", descendants)
    assert runner._wait_for_descendant_absence(123, 123)
    assert descendants.call_count == 2


def test_monitor_thread_start_failure_reaps_spawned_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "sleep")
    monkeypatch.setattr(threading.Thread, "start", Mock(side_effect=RuntimeError))
    expect_error(ProcessControllerErrorCode.START_FAILED, runner.start)
    assert runner._process_group_id is not None
    assert not process_control._group_exists(runner._process_group_id)
    expect_error(ProcessControllerErrorCode.START_FAILED, runner.wait)


def test_second_control_failure_uses_emergency_kill_and_reap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "sleep")
    monkeypatch.setattr(
        process_control,
        "_process_group_usage",
        Mock(side_effect=process_control._ControlFailure),
    )
    monkeypatch.setattr(
        process_control,
        "_count_group_descendants",
        Mock(side_effect=process_control._ControlFailure),
    )
    emergency = Mock(wraps=runner._emergency_kill_and_reap)
    monkeypatch.setattr(runner, "_emergency_kill_and_reap", emergency)
    runner.start()
    process_group_id = runner.process_group_id
    with pytest.raises(ProcessControllerError) as captured:
        runner.wait()
    assert captured.value.code in {
        ProcessControllerErrorCode.CONTROL_FAILED,
        ProcessControllerErrorCode.REAP_FAILED,
    }
    emergency.assert_called()
    assert runner._process is not None
    assert runner._process.returncode is not None
    deadline = time.monotonic() + 3
    while process_control._group_exists(process_group_id) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not process_control._group_exists(process_group_id)


def test_monitor_start_failure_reports_reap_failure_when_both_cleanup_paths_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "success")
    process = cast(subprocess.Popen[bytes], Mock(pid=123))
    monkeypatch.setattr(subprocess, "Popen", Mock(return_value=process))
    monkeypatch.setattr(threading.Thread, "start", Mock(side_effect=RuntimeError))
    monkeypatch.setattr(
        runner, "_terminate_and_reap", Mock(side_effect=process_control._ControlFailure)
    )
    monkeypatch.setattr(
        runner,
        "_emergency_kill_and_reap",
        Mock(side_effect=process_control._ReapFailure),
    )
    expect_error(ProcessControllerErrorCode.REAP_FAILED, runner.start)
    expect_error(ProcessControllerErrorCode.REAP_FAILED, runner.wait)


def test_monitor_reap_failures_publish_and_notify_even_when_emergency_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def seeded() -> ProcessController:
        item = controller(tmp_path, "success")
        item._process = cast(subprocess.Popen[bytes], Mock())
        item._process_group_id = 123
        item._deadline = time.monotonic() + 1
        return item

    direct = seeded()
    monkeypatch.setattr(direct, "_choose_winner", Mock(side_effect=process_control._ReapFailure))
    monkeypatch.setattr(
        direct,
        "_emergency_kill_and_reap",
        Mock(side_effect=process_control._ReapFailure),
    )
    direct._monitor()
    assert direct._error is not None
    assert direct._error.code is ProcessControllerErrorCode.REAP_FAILED

    secondary = seeded()
    monkeypatch.setattr(secondary, "_choose_winner", Mock(side_effect=OSError))
    monkeypatch.setattr(secondary, "_force_reap", Mock(side_effect=process_control._ReapFailure))
    monkeypatch.setattr(
        secondary,
        "_emergency_kill_and_reap",
        Mock(side_effect=process_control._ReapFailure),
    )
    secondary._monitor()
    assert secondary._error is not None
    assert secondary._error.code is ProcessControllerErrorCode.REAP_FAILED


def test_force_and_emergency_reap_fallback_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = controller(tmp_path, "success")
    process = cast(subprocess.Popen[bytes], Mock(pid=123, wait=Mock(return_value=0)))
    monkeypatch.setattr(
        process_control,
        "_signal_group",
        Mock(side_effect=process_control._ReapFailure),
    )
    monkeypatch.setattr(runner, "_wait_for_group_absence", Mock(return_value=True))
    process.kill.side_effect = ProcessLookupError
    runner._force_reap(process, 123)

    process.kill.side_effect = OSError
    with pytest.raises(process_control._ReapFailure):
        runner._force_reap(process, 123)

    process.kill.side_effect = OSError
    monkeypatch.setattr(process_control, "_leader_exited", Mock(return_value=True))
    monkeypatch.setattr(process_control, "_count_group_descendants", Mock(return_value=0))
    monkeypatch.setattr(process_control, "_group_exists", Mock(return_value=False))
    runner._emergency_kill_and_reap(process, 123)

    timed_out = cast(
        subprocess.Popen[bytes],
        Mock(
            pid=123,
            kill=Mock(side_effect=OSError),
            wait=Mock(side_effect=subprocess.TimeoutExpired(("worker",), 1)),
        ),
    )
    with pytest.raises(process_control._ReapFailure):
        runner._emergency_kill_and_reap(timed_out, 123)

    process.kill.side_effect = None
    monkeypatch.setattr(process_control, "_group_exists", Mock(return_value=True))
    with pytest.raises(process_control._ReapFailure):
        runner._emergency_kill_and_reap(process, 123)

    process.wait.reset_mock()
    monkeypatch.setattr(process_control, "_leader_exited", Mock(return_value=True))
    monkeypatch.setattr(
        process_control,
        "_count_group_descendants",
        Mock(side_effect=process_control._ControlFailure),
    )
    with pytest.raises(process_control._ReapFailure):
        runner._emergency_kill_and_reap(process, 123)
    process.wait.assert_called_once_with(timeout=runner._limits.terminate_grace_seconds)

    process.wait.reset_mock()
    monkeypatch.setattr(process_control, "_leader_exited", Mock(side_effect=(False, True)))
    monkeypatch.setattr(process_control, "_count_group_descendants", Mock(side_effect=(1, 0)))
    monkeypatch.setattr(process_control, "_group_exists", Mock(return_value=False))
    monkeypatch.setattr(time, "monotonic", lambda: 0.0)
    sleep = Mock()
    monkeypatch.setattr(time, "sleep", sleep)
    runner._emergency_kill_and_reap(process, 123)
    sleep.assert_called_once_with(process_control._MONITOR_INTERVAL_SECONDS)

    process.wait.reset_mock()
    monkeypatch.setattr(process_control, "_leader_exited", Mock(return_value=False))
    monkeypatch.setattr(
        process_control,
        "_count_group_descendants",
        Mock(side_effect=process_control._ControlFailure),
    )
    moments = iter((0.0, 0.0, 5.0))
    monkeypatch.setattr(time, "monotonic", lambda: next(moments))
    sleep.reset_mock()
    with pytest.raises(process_control._ReapFailure):
        runner._emergency_kill_and_reap(process, 123)
    sleep.assert_called_once_with(process_control._MONITOR_INTERVAL_SECONDS)
    process.wait.assert_not_called()

    process.wait.reset_mock()
    monkeypatch.setattr(
        process_control,
        "_leader_exited",
        Mock(side_effect=process_control._ReapFailure),
    )
    moments = iter((0.0, 0.0, 5.0))
    monkeypatch.setattr(time, "monotonic", lambda: next(moments))
    with pytest.raises(process_control._ReapFailure):
        runner._emergency_kill_and_reap(process, 123)
    process.wait.assert_not_called()


def test_owned_reap_retry_never_releases_a_live_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = controller(tmp_path, "success")
    expect_error(ProcessControllerErrorCode.INVALID_STATE, missing.reap_until_absent)

    runner = controller(tmp_path, "success")
    process = cast(subprocess.Popen[bytes], Mock(pid=123, returncode=None))
    runner._process = process
    runner._process_group_id = 123
    monkeypatch.setattr(process_control, "_signal_group", Mock(return_value=None))
    monkeypatch.setattr(
        runner,
        "_wait_for_group_absence",
        Mock(side_effect=(process_control._ControlFailure, True)),
    )
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    runner.reap_until_absent()

    monkeypatch.setattr(
        runner,
        "_wait_for_group_absence",
        Mock(side_effect=(False, True)),
    )
    runner.reap_until_absent()

    process.returncode = -signal.SIGKILL
    monkeypatch.setattr(process_control, "_group_exists", Mock(return_value=False))
    runner.reap_until_absent()

    monkeypatch.setattr(process_control, "_group_exists", Mock(return_value=True))
    expect_error(ProcessControllerErrorCode.REAP_FAILED, runner.reap_until_absent)
