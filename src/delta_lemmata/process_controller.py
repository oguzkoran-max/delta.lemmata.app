"""Bounded process control for the P005 synthetic POSIX worker.

This module is an application-managed local POSIX boundary.  It sets inherited
per-process CPU and virtual-memory limits, samples process-group membership for
the PID limit, and owns wall timeout plus process-group termination.  It is not a
cgroup, container, host-isolation, or production-containment claim.

Worker stdin is closed and worker stdout/stderr are always discarded.  Public
results contain only stable content-free enums; argv, paths, environment values,
return codes, output, tracebacks, and payloads are never copied into a result.
"""

from __future__ import annotations

import os
import resource
import signal
import stat
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from pathlib import Path
from typing import NoReturn

from delta_lemmata.job_policy import WorkerLimitProfile

PROCESS_CONTROL_BOUNDARY = "local_posix_app_managed"

_CLEAN_WORKER_ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "TZ": "UTC",
}
_CONTROL_ENVIRONMENT = {"LC_ALL": "C"}
_MONITOR_INTERVAL_SECONDS = 0.025
_PS_TIMEOUT_SECONDS = 1.0

# The synthetic fixture uses these content-free exit codes to make simulated
# memory/PID exhaustion deterministic across the macOS and Linux evidence runs.
SYNTHETIC_MEMORY_LIMIT_EXIT = 73
SYNTHETIC_PROCESS_LIMIT_EXIT = 74
_LAUNCHER_MARKER = "__delta_worker_launcher_v1__"


class ProcessOutcome(StrEnum):
    """Stable terminal classifications without worker-controlled detail."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    CRASHED = "crashed"
    LIMIT_EXCEEDED = "limit_exceeded"


class ProcessLimit(StrEnum):
    """Finite profile dimension responsible for a bounded termination."""

    WALL = "wall"
    CPU = "cpu"
    MEMORY = "memory"
    PROCESSES = "processes"


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Content-free result published only after process-tree reap verification."""

    outcome: ProcessOutcome
    limit: ProcessLimit | None = None

    @property
    def boundary(self) -> str:
        return PROCESS_CONTROL_BOUNDARY


class ProcessControllerErrorCode(StrEnum):
    """Stable errors that expose no argv, path, payload, or OS detail."""

    INVALID_CONFIGURATION = "PROCESS_INVALID_CONFIGURATION"
    INVALID_STATE = "PROCESS_INVALID_STATE"
    START_FAILED = "PROCESS_START_FAILED"
    CONTROL_FAILED = "PROCESS_CONTROL_FAILED"
    REAP_FAILED = "PROCESS_REAP_FAILED"
    POSIX_REQUIRED = "PROCESS_POSIX_REQUIRED"


class ProcessControllerError(RuntimeError):
    """Content-free controller failure."""

    def __init__(self, code: ProcessControllerErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class _Winner(Enum):
    COMPLETION = auto()
    CANCELLATION = auto()
    WALL_LIMIT = auto()
    PROCESS_LIMIT = auto()
    MEMORY_LIMIT = auto()
    CONTROL_FAILURE = auto()


class _ControlFailure(RuntimeError):
    pass


class _ReapFailure(RuntimeError):
    pass


def _bounded_limit(limit: int, requested_soft: int, requested_hard: int) -> None:
    _current_soft, current_hard = resource.getrlimit(limit)
    if current_hard != resource.RLIM_INFINITY:
        requested_hard = min(requested_hard, current_hard)
        requested_soft = min(requested_soft, requested_hard)
    resource.setrlimit(limit, (requested_soft, requested_hard))


def _apply_worker_limits(cpu_time_seconds: int, memory_bytes: int) -> None:
    """Apply inherited limits inside the dedicated child launcher."""

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    _bounded_limit(resource.RLIMIT_CPU, cpu_time_seconds, cpu_time_seconds + 1)
    if sys.platform != "darwin":
        _bounded_limit(resource.RLIMIT_AS, memory_bytes, memory_bytes)


def _launcher_argv(argv: tuple[str, ...], limits: WorkerLimitProfile) -> tuple[str, ...]:
    return (
        sys.executable,
        "-m",
        "delta_lemmata.process_controller",
        _LAUNCHER_MARKER,
        str(limits.cpu_time_seconds),
        str(limits.memory_bytes),
        *argv,
    )


def _run_launcher(arguments: list[str]) -> NoReturn:
    """Set limits after fork in a single-threaded interpreter, then replace it."""

    if len(arguments) < 4 or arguments[0] != _LAUNCHER_MARKER:
        raise SystemExit(126)
    try:
        cpu_time_seconds = int(arguments[1])
        memory_bytes = int(arguments[2])
    except ValueError:
        raise SystemExit(126) from None
    target = tuple(arguments[3:])
    if (
        cpu_time_seconds <= 0
        or memory_bytes <= 0
        or not target
        or not Path(target[0]).is_absolute()
    ):
        raise SystemExit(126)
    try:
        _apply_worker_limits(cpu_time_seconds, memory_bytes)
        os.execve(target[0], target, _CLEAN_WORKER_ENVIRONMENT)
    except (OSError, ValueError):
        raise SystemExit(126) from None


def _find_ps() -> str:
    for candidate in ("/bin/ps", "/usr/bin/ps"):
        if Path(candidate).is_file():
            return candidate
    raise ProcessControllerError(ProcessControllerErrorCode.POSIX_REQUIRED)


def _process_group_usage(ps_path: str, process_group_id: int) -> tuple[int, int]:
    try:
        completed = subprocess.run(
            (ps_path, "-e", "-o", "pgid=,rss="),
            check=True,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            env=_CONTROL_ENVIRONMENT,
            timeout=_PS_TIMEOUT_SECONDS,
        )
        count = 0
        resident_kib = 0
        for raw_row in completed.stdout.splitlines():
            raw_group, raw_resident = raw_row.split()
            if int(raw_group) == process_group_id:
                count += 1
                resident_kib += int(raw_resident)
        return count, resident_kib * 1024
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise _ControlFailure from error


def _count_process_group(ps_path: str, process_group_id: int) -> int:
    return _process_group_usage(ps_path, process_group_id)[0]


def _group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_group(process_group_id: int, signal_number: signal.Signals) -> None:
    try:
        os.killpg(process_group_id, signal_number)
    except ProcessLookupError:
        return
    except OSError as error:
        raise _ReapFailure from error


class ProcessController:
    """Run one immutable argv under one mandatory finite worker profile."""

    def __init__(
        self,
        *,
        argv: tuple[str, ...],
        cwd: Path,
        limits: WorkerLimitProfile,
    ) -> None:
        self._validate_configuration(argv=argv, cwd=cwd, limits=limits)
        self._argv = argv
        self._cwd = cwd
        self._limits = limits
        self._ps_path = _find_ps()
        self._condition = threading.Condition(threading.Lock())
        self._started = False
        self._process: subprocess.Popen[bytes] | None = None
        self._process_group_id: int | None = None
        self._deadline: float | None = None
        self._winner: _Winner | None = None
        self._result: ProcessResult | None = None
        self._error: ProcessControllerError | None = None

    @staticmethod
    def _validate_configuration(
        *,
        argv: tuple[str, ...],
        cwd: Path,
        limits: WorkerLimitProfile,
    ) -> None:
        if os.name != "posix" or not hasattr(os, "killpg"):
            raise ProcessControllerError(ProcessControllerErrorCode.POSIX_REQUIRED)
        if not isinstance(limits, WorkerLimitProfile):
            raise ProcessControllerError(ProcessControllerErrorCode.INVALID_CONFIGURATION)
        if (
            not isinstance(argv, tuple)
            or not argv
            or any(not isinstance(item, str) or not item or "\0" in item for item in argv)
            or not Path(argv[0]).is_absolute()
        ):
            raise ProcessControllerError(ProcessControllerErrorCode.INVALID_CONFIGURATION)
        if not isinstance(cwd, Path) or not cwd.is_absolute():
            raise ProcessControllerError(ProcessControllerErrorCode.INVALID_CONFIGURATION)
        try:
            info = cwd.lstat()
            fixed_cwd = cwd.resolve(strict=True)
        except OSError:
            invalid_cwd = True
        else:
            invalid_cwd = False
        if invalid_cwd:
            raise ProcessControllerError(ProcessControllerErrorCode.INVALID_CONFIGURATION)
        if not stat.S_ISDIR(info.st_mode) or fixed_cwd != cwd:
            raise ProcessControllerError(ProcessControllerErrorCode.INVALID_CONFIGURATION)

    @property
    def result(self) -> ProcessResult | None:
        with self._condition:
            return self._result

    @property
    def process_group_id(self) -> int:
        with self._condition:
            if self._process_group_id is None:
                raise ProcessControllerError(ProcessControllerErrorCode.INVALID_STATE)
            return self._process_group_id

    def start(self) -> None:
        """Start exactly once with no shell, inherited descriptors, or output pipes."""

        with self._condition:
            if self._started:
                raise ProcessControllerError(ProcessControllerErrorCode.INVALID_STATE)
            self._started = True
            try:
                process = subprocess.Popen(
                    _launcher_argv(self._argv, self._limits),
                    shell=False,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                    cwd=self._cwd,
                    env=_CLEAN_WORKER_ENVIRONMENT,
                    restore_signals=True,
                    start_new_session=True,
                )
            except (OSError, subprocess.SubprocessError):
                process = None
            if process is None:
                raise ProcessControllerError(ProcessControllerErrorCode.START_FAILED)
            self._process = process
            self._process_group_id = process.pid
            self._deadline = time.monotonic() + self._limits.wall_time_seconds
            monitor = threading.Thread(
                target=self._monitor,
                name="delta-synthetic-worker-monitor",
                daemon=True,
            )
            monitor.start()

    def run(self) -> ProcessResult:
        """Start and wait for the single content-free terminal result."""

        self.start()
        return self.wait()

    def wait(self) -> ProcessResult:
        """Wait for a verified reap; repeated callers receive the same result object."""

        with self._condition:
            if not self._started:
                raise ProcessControllerError(ProcessControllerErrorCode.INVALID_STATE)
            return self._wait_locked()

    def cancel(self) -> ProcessResult:
        """Request cancellation once; repeats and post-completion calls are idempotent."""

        with self._condition:
            if not self._started or self._process is None:
                raise ProcessControllerError(ProcessControllerErrorCode.INVALID_STATE)
            if self._result is not None:
                return self._result
            if self._error is not None:
                raise ProcessControllerError(self._error.code)
            if self._winner is None:
                if self._process.poll() is None:
                    self._winner = _Winner.CANCELLATION
                else:
                    self._winner = _Winner.COMPLETION
                self._condition.notify_all()
            return self._wait_locked()

    def _wait_locked(self) -> ProcessResult:
        while self._result is None and self._error is None:
            self._condition.wait()
        if self._error is not None:
            raise ProcessControllerError(self._error.code)
        if self._result is None:  # pragma: no cover - loop invariant guard
            raise ProcessControllerError(ProcessControllerErrorCode.CONTROL_FAILED)
        return self._result

    def _monitor(self) -> None:
        process = self._process
        process_group_id = self._process_group_id
        deadline = self._deadline
        if process is None or process_group_id is None or deadline is None:
            self._publish_error(ProcessControllerErrorCode.CONTROL_FAILED)
            return
        try:
            winner = self._choose_winner(process, process_group_id, deadline)
            result = self._settle(process, process_group_id, winner)
        except _ReapFailure:
            self._publish_error(ProcessControllerErrorCode.REAP_FAILED)
            return
        except (OSError, subprocess.SubprocessError, _ControlFailure):
            try:
                self._force_reap(process, process_group_id)
            except _ReapFailure:
                self._publish_error(ProcessControllerErrorCode.REAP_FAILED)
                return
            self._publish_error(ProcessControllerErrorCode.CONTROL_FAILED)
            return
        with self._condition:
            self._result = result
            self._condition.notify_all()

    def _choose_winner(
        self,
        process: subprocess.Popen[bytes],
        process_group_id: int,
        deadline: float,
    ) -> _Winner:
        while True:
            with self._condition:
                if self._winner is not None:
                    return self._winner
                if process.poll() is not None:
                    self._winner = _Winner.COMPLETION
                    return self._winner
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._winner = _Winner.WALL_LIMIT
                    return self._winner
            process_count, resident_bytes = _process_group_usage(self._ps_path, process_group_id)
            with self._condition:
                if self._winner is not None:
                    return self._winner
                if process.poll() is not None:
                    self._winner = _Winner.COMPLETION
                    return self._winner
                if process_count > self._limits.max_processes:
                    self._winner = _Winner.PROCESS_LIMIT
                    return self._winner
                if resident_bytes > self._limits.memory_bytes:
                    self._winner = _Winner.MEMORY_LIMIT
                    return self._winner
                self._condition.wait(timeout=min(_MONITOR_INTERVAL_SECONDS, remaining))

    def _settle(
        self,
        process: subprocess.Popen[bytes],
        process_group_id: int,
        winner: _Winner,
    ) -> ProcessResult:
        if winner is _Winner.COMPLETION:
            return_code = process.wait()
            self._remove_remaining_group(process, process_group_id)
            return self._classify_completion(return_code)
        self._terminate_and_reap(process, process_group_id)
        if winner is _Winner.CANCELLATION:
            return ProcessResult(ProcessOutcome.CANCELLED)
        if winner is _Winner.WALL_LIMIT:
            return ProcessResult(ProcessOutcome.TIMED_OUT, ProcessLimit.WALL)
        if winner is _Winner.PROCESS_LIMIT:
            return ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.PROCESSES)
        if winner is _Winner.MEMORY_LIMIT:
            return ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.MEMORY)
        raise _ControlFailure

    @staticmethod
    def _classify_completion(return_code: int) -> ProcessResult:
        if return_code == 0:
            return ProcessResult(ProcessOutcome.SUCCEEDED)
        if return_code == SYNTHETIC_MEMORY_LIMIT_EXIT:
            return ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.MEMORY)
        if return_code == SYNTHETIC_PROCESS_LIMIT_EXIT:
            return ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.PROCESSES)
        if return_code == -signal.SIGXCPU:
            return ProcessResult(ProcessOutcome.LIMIT_EXCEEDED, ProcessLimit.CPU)
        if return_code < 0:
            return ProcessResult(ProcessOutcome.CRASHED)
        return ProcessResult(ProcessOutcome.FAILED)

    def _remove_remaining_group(
        self,
        process: subprocess.Popen[bytes],
        process_group_id: int,
    ) -> None:
        if _group_exists(process_group_id):
            self._terminate_and_reap(process, process_group_id)

    def _terminate_and_reap(
        self,
        process: subprocess.Popen[bytes],
        process_group_id: int,
    ) -> None:
        _signal_group(process_group_id, signal.SIGTERM)
        if not self._wait_for_group_absence(process, process_group_id):
            _signal_group(process_group_id, signal.SIGKILL)
            if not self._wait_for_group_absence(process, process_group_id):
                raise _ReapFailure
        process.wait(timeout=self._limits.terminate_grace_seconds)

    def _force_reap(
        self,
        process: subprocess.Popen[bytes],
        process_group_id: int,
    ) -> None:
        _signal_group(process_group_id, signal.SIGKILL)
        try:
            process.wait(timeout=self._limits.terminate_grace_seconds)
        except subprocess.TimeoutExpired as error:
            raise _ReapFailure from error
        if _group_exists(process_group_id):
            raise _ReapFailure

    def _wait_for_group_absence(
        self,
        process: subprocess.Popen[bytes],
        process_group_id: int,
    ) -> bool:
        deadline = time.monotonic() + self._limits.terminate_grace_seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                process.wait()
            if not _group_exists(process_group_id):
                return True
            time.sleep(_MONITOR_INTERVAL_SECONDS)
        return not _group_exists(process_group_id)

    def _publish_error(self, code: ProcessControllerErrorCode) -> None:
        with self._condition:
            self._error = ProcessControllerError(code)
            self._condition.notify_all()


__all__ = [
    "PROCESS_CONTROL_BOUNDARY",
    "ProcessController",
    "ProcessControllerError",
    "ProcessControllerErrorCode",
    "ProcessLimit",
    "ProcessOutcome",
    "ProcessResult",
]


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess fixtures
    _run_launcher(sys.argv[1:])
