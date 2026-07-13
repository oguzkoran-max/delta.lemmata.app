"""App-loss guardian for the P005 local POSIX synthetic worker boundary."""

from __future__ import annotations

import base64
import json
import os
import queue
import re
import select
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from functools import wraps
from pathlib import Path

from delta_lemmata.job_models import TerminalOutcome
from delta_lemmata.job_policy import DEFAULT_JOB_POLICY, WorkerLimitProfile
from delta_lemmata.job_store import JobStoreError, SQLiteJobStore
from delta_lemmata.job_workspace import CleanupReport, WorkspaceError, WorkspaceManager
from delta_lemmata.process_controller import (
    ProcessController,
    ProcessControllerError,
    ProcessLimit,
    ProcessOutcome,
    ProcessResult,
)
from delta_lemmata.recovery_receipt import (
    RecoveryReceiptError,
    RecoveryReceiptStore,
    new_recovery_receipt,
)
from delta_lemmata.session_identity import JobId, workspace_component

GUARDIAN_PROCESS_BOUNDARY = "guardian_managed_local_posix"

_GUARDIAN_MARKER = "__delta_guardian_v1__"
_CLEAN_ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "TZ": "UTC",
}
_COMPONENT = re.compile(r"^[0-9a-f]{64}$", flags=re.ASCII)
_OPERATION_REFERENCE = re.compile(r"^op_[0-9a-f]{64}$", flags=re.ASCII)
_START_TIMEOUT_SECONDS = 5.0
_ACK_TIMEOUT_SECONDS = 5.0
_POLL_SECONDS = 0.025
_MAX_PROTOCOL_LINE = 160
_MAX_SECRET_BYTES = 4096


class GuardianControllerErrorCode(StrEnum):
    INVALID_CONFIGURATION = "GUARDIAN_INVALID_CONFIGURATION"
    INVALID_STATE = "GUARDIAN_INVALID_STATE"
    START_FAILED = "GUARDIAN_START_FAILED"
    CONTROL_FAILED = "GUARDIAN_CONTROL_FAILED"


class GuardianControllerError(RuntimeError):
    def __init__(self, code: GuardianControllerErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


def _content_free[**P, T](method: Callable[P, T]) -> Callable[P, T]:
    @wraps(method)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return method(*args, **kwargs)
        except GuardianControllerError as error:
            rejection = error
        rejection.__context__ = None
        rejection.__cause__ = None
        rejection.__suppress_context__ = True
        raise rejection

    return wrapped


def _encoded_argv(argv: tuple[str, ...]) -> str:
    encoded = json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return base64.urlsafe_b64encode(encoded).decode("ascii")


def _decoded_argv(encoded: str) -> tuple[str, ...]:
    try:
        raw = base64.b64decode(encoded.encode("ascii"), altchars=b"-_", validate=True)
        value = json.loads(raw)
    except (UnicodeError, ValueError, json.JSONDecodeError):
        raise ValueError from None
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item or "\0" in item for item in value)
    ):
        raise ValueError
    return tuple(value)


def _write_all(descriptor: int, content: bytes) -> None:
    view = memoryview(content)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError
        view = view[written:]


def _safe_close(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except OSError:
        return


def _read_secret(descriptor: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, min(1024, _MAX_SECRET_BYTES + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > _MAX_SECRET_BYTES:
            raise ValueError
    secret = b"".join(chunks)
    if not secret:
        raise ValueError
    return secret


def _safe_protocol_write(descriptor: int, content: bytes) -> None:
    try:
        _write_all(descriptor, content)
    except OSError:
        return


def _result_line(result: ProcessResult) -> bytes:
    limit = "none" if result.limit is None else result.limit.value
    return f"F {result.outcome.value} {limit}\n".encode("ascii")


def _terminal_outcome(result: ProcessResult) -> TerminalOutcome:
    mapping = {
        ProcessOutcome.SUCCEEDED: TerminalOutcome.SUCCEEDED,
        ProcessOutcome.FAILED: TerminalOutcome.FAILED,
        ProcessOutcome.CANCELLED: TerminalOutcome.CANCELLED,
        ProcessOutcome.TIMED_OUT: TerminalOutcome.TIMED_OUT,
        ProcessOutcome.CRASHED: TerminalOutcome.CRASHED,
        ProcessOutcome.LIMIT_EXCEEDED: TerminalOutcome.FAILED,
    }
    return mapping[result.outcome]


@_content_free
def _parse_result_line(line: bytes) -> ProcessResult:
    try:
        marker, raw_outcome, raw_limit = line.decode("ascii").strip().split()
        if marker != "F":
            raise ValueError
        outcome = ProcessOutcome(raw_outcome)
        limit = None if raw_limit == "none" else ProcessLimit(raw_limit)
        result = ProcessResult(outcome, limit)
    except (UnicodeError, ValueError):
        raise GuardianControllerError(GuardianControllerErrorCode.CONTROL_FAILED) from None
    valid_limit = (
        (outcome is ProcessOutcome.TIMED_OUT and limit is ProcessLimit.WALL)
        or (
            outcome is ProcessOutcome.LIMIT_EXCEEDED
            and limit in {ProcessLimit.CPU, ProcessLimit.MEMORY, ProcessLimit.PROCESSES}
        )
        or (
            outcome
            in {
                ProcessOutcome.SUCCEEDED,
                ProcessOutcome.FAILED,
                ProcessOutcome.CANCELLED,
                ProcessOutcome.CRASHED,
            }
            and limit is None
        )
    )
    if not valid_limit:
        raise GuardianControllerError(GuardianControllerErrorCode.CONTROL_FAILED)
    return result


class GuardianController:
    """Keep worker ownership alive after the calling application process disappears."""

    @_content_free
    def __init__(
        self,
        *,
        argv: tuple[str, ...],
        cwd: Path,
        limits: WorkerLimitProfile,
        job_id: JobId,
        execution_reference: str,
        store: SQLiteJobStore,
        workspace_root: Path,
        owner_component: str,
        job_component: str,
        receipt_store: RecoveryReceiptStore,
    ) -> None:
        try:
            ProcessController._validate_configuration(argv=argv, cwd=cwd, limits=limits)
            WorkspaceManager(workspace_root)
        except (ProcessControllerError, WorkspaceError):
            raise GuardianControllerError(
                GuardianControllerErrorCode.INVALID_CONFIGURATION
            ) from None
        if (
            not isinstance(job_id, JobId)
            or _COMPONENT.fullmatch(owner_component) is None
            or _COMPONENT.fullmatch(job_component) is None
            or job_component != workspace_component(job_id)
            or not isinstance(execution_reference, str)
            or _OPERATION_REFERENCE.fullmatch(execution_reference) is None
            or not isinstance(store, SQLiteJobStore)
            or not isinstance(receipt_store, RecoveryReceiptStore)
        ):
            raise GuardianControllerError(GuardianControllerErrorCode.INVALID_CONFIGURATION)
        self._argv = argv
        self._cwd = cwd
        self._limits = limits
        self._job_id = job_id
        self._execution_reference = execution_reference
        self._store = store
        self._workspace_root = workspace_root
        self._owner_component = owner_component
        self._job_component = job_component
        self._receipt_store = receipt_store
        self._condition = threading.Condition(threading.Lock())
        self._started = False
        self._control_write = -1
        self._result_read = -1
        self._guardian: subprocess.Popen[bytes] | None = None
        self._process_group_id: int | None = None
        self._result: ProcessResult | None = None
        self._error: GuardianControllerError | None = None
        self._guardian_finished = False
        self._acknowledged = False

    @property
    def boundary(self) -> str:
        return GUARDIAN_PROCESS_BOUNDARY

    @property
    def process_group_id(self) -> int:
        with self._condition:
            if self._process_group_id is None:
                raise GuardianControllerError(GuardianControllerErrorCode.INVALID_STATE)
            return self._process_group_id

    @property
    def result(self) -> ProcessResult | None:
        with self._condition:
            return self._result

    @_content_free
    def start(self) -> None:
        with self._condition:
            if self._started:
                raise GuardianControllerError(GuardianControllerErrorCode.INVALID_STATE)
            self._started = True
            control_read, control_write = os.pipe()
            result_read, result_write = os.pipe()
            secret_read, secret_write = os.pipe()
            arguments = (
                sys.executable,
                "-m",
                "delta_lemmata.guardian_controller",
                _GUARDIAN_MARKER,
                str(control_read),
                str(result_write),
                str(secret_read),
                self._job_id.to_urlsafe(),
                str(self._workspace_root),
                self._owner_component,
                self._job_component,
                str(self._receipt_store.root),
                self._limits.model_dump_json(),
                _encoded_argv(self._argv),
                self._execution_reference,
            )
            guardian: subprocess.Popen[bytes] | None = None
            try:
                _write_all(secret_write, self._receipt_store.signing_secret_for_guardian())
                _safe_close(secret_write)
                guardian = subprocess.Popen(
                    arguments,
                    shell=False,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    close_fds=True,
                    pass_fds=(control_read, result_write, secret_read),
                    cwd=self._cwd,
                    env=_CLEAN_ENVIRONMENT,
                    restore_signals=True,
                    start_new_session=True,
                )
                _safe_close(control_read)
                _safe_close(result_write)
                _safe_close(secret_read)
            except (OSError, subprocess.SubprocessError):
                for descriptor in (
                    control_read,
                    control_write,
                    result_read,
                    result_write,
                    secret_read,
                    secret_write,
                ):
                    _safe_close(descriptor)
                raise GuardianControllerError(GuardianControllerErrorCode.START_FAILED) from None
            if guardian is None:  # pragma: no cover - Popen success invariant
                raise GuardianControllerError(GuardianControllerErrorCode.START_FAILED)
            self._control_write = control_write
            self._result_read = result_read
            self._guardian = guardian
            monitor = threading.Thread(
                target=self._monitor_protocol,
                name="delta-guardian-protocol-monitor",
                daemon=True,
            )
            try:
                monitor.start()
            except RuntimeError:
                _safe_close(self._control_write)
                self._control_write = -1
                guardian.wait()
                _safe_close(self._result_read)
                self._result_read = -1
                raise GuardianControllerError(GuardianControllerErrorCode.START_FAILED) from None
            deadline = time.monotonic() + _START_TIMEOUT_SECONDS
            while self._process_group_id is None and self._error is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._error = GuardianControllerError(GuardianControllerErrorCode.START_FAILED)
                    _safe_close(self._control_write)
                    self._control_write = -1
                    self._condition.notify_all()
                    break
                self._condition.wait(timeout=remaining)
            if self._error is not None:
                raise GuardianControllerError(self._error.code)

    @_content_free
    def wait(self) -> ProcessResult:
        with self._condition:
            if not self._started:
                raise GuardianControllerError(GuardianControllerErrorCode.INVALID_STATE)
            while self._result is None and self._error is None:
                self._condition.wait()
            if self._error is not None:
                raise GuardianControllerError(self._error.code)
            if self._result is None:  # pragma: no cover - condition-loop invariant
                raise GuardianControllerError(GuardianControllerErrorCode.CONTROL_FAILED)
            return self._result

    @_content_free
    def acknowledge_terminal_persisted(self, *, expected_version: int) -> None:
        """Release the guardian only after the terminal job transition is durable."""

        with self._condition:
            if not self._started or self._result is None:
                raise GuardianControllerError(GuardianControllerErrorCode.INVALID_STATE)
            if self._error is not None:
                raise GuardianControllerError(self._error.code)
            try:
                persisted = self._store.terminal_transition_matches(
                    job_id=self._job_id,
                    execution_reference=self._execution_reference,
                    expected_version=expected_version,
                    expected_outcome=_terminal_outcome(self._result),
                )
            except JobStoreError:
                persisted = False
            if not persisted:
                raise GuardianControllerError(GuardianControllerErrorCode.CONTROL_FAILED)
            if not self._acknowledged:
                if self._control_write < 0 or self._guardian_finished:
                    raise GuardianControllerError(GuardianControllerErrorCode.CONTROL_FAILED)
                try:
                    _write_all(self._control_write, b"A")
                except OSError:
                    self._error = GuardianControllerError(
                        GuardianControllerErrorCode.CONTROL_FAILED
                    )
                    self._condition.notify_all()
                    raise GuardianControllerError(self._error.code) from None
                self._acknowledged = True
            while not self._guardian_finished and self._error is None:
                self._condition.wait()
            if self._error is not None:
                raise GuardianControllerError(self._error.code)

    @_content_free
    def cancel(self) -> ProcessResult:
        with self._condition:
            if not self._started:
                raise GuardianControllerError(GuardianControllerErrorCode.INVALID_STATE)
            if self._result is not None:
                return self._result
            if self._control_write < 0:
                raise GuardianControllerError(GuardianControllerErrorCode.INVALID_STATE)
            try:
                _write_all(self._control_write, b"C")
            except OSError:
                if self._error is None:
                    self._error = GuardianControllerError(
                        GuardianControllerErrorCode.CONTROL_FAILED
                    )
                    self._condition.notify_all()
            while self._result is None and self._error is None:
                self._condition.wait()
            if self._error is not None:
                raise GuardianControllerError(self._error.code)
            if self._result is None:  # pragma: no cover - condition-loop invariant
                raise GuardianControllerError(GuardianControllerErrorCode.CONTROL_FAILED)
            return self._result

    def _monitor_protocol(self) -> None:
        guardian = self._guardian
        descriptor = self._result_read
        if guardian is None or descriptor < 0:
            self._publish_error(GuardianControllerErrorCode.CONTROL_FAILED)
            return
        try:
            with os.fdopen(descriptor, "rb", buffering=0) as stream:
                ready = stream.readline(_MAX_PROTOCOL_LINE)
                marker, raw_group = ready.decode("ascii").strip().split()
                if marker != "R":
                    raise ValueError
                process_group_id = int(raw_group)
                if process_group_id <= 0:
                    raise ValueError
                with self._condition:
                    self._process_group_id = process_group_id
                    self._condition.notify_all()
                line = stream.readline(_MAX_PROTOCOL_LINE)
                if not line or len(line) >= _MAX_PROTOCOL_LINE:
                    raise ValueError
                result = _parse_result_line(line)
                with self._condition:
                    self._result = result
                    self._condition.notify_all()
            if (
                guardian.wait(
                    timeout=_ACK_TIMEOUT_SECONDS + self._limits.terminate_grace_seconds + 2
                )
                != 0
            ):
                raise ValueError
        except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
            if self._control_write >= 0:
                _safe_close(self._control_write)
                self._control_write = -1
            self._publish_error(GuardianControllerErrorCode.CONTROL_FAILED)
            try:
                guardian.wait()
            except (OSError, subprocess.SubprocessError):
                pass
            return
        finally:
            self._result_read = -1
            if self._control_write >= 0:
                _safe_close(self._control_write)
                self._control_write = -1
            with self._condition:
                self._guardian_finished = True
                self._condition.notify_all()

    def _publish_error(self, code: GuardianControllerErrorCode) -> None:
        with self._condition:
            if self._error is None:
                self._error = GuardianControllerError(code)
            self._condition.notify_all()


def _guardian_cleanup(
    *,
    job_id: JobId,
    execution_reference: str,
    workspace_root: Path,
    owner_component: str,
    job_component: str,
    receipt_root: Path,
    signing_secret: bytes,
) -> None:
    verified = False
    report = CleanupReport(0, 0, True)
    try:
        manager = WorkspaceManager(workspace_root)
        layout = manager.load_optional(owner_component, job_component)
        if layout is not None:
            report = manager.cleanup(layout)
        verified = True
    except WorkspaceError:
        report = CleanupReport(0, 0, True)
    receipt = new_recovery_receipt(
        job_id=job_id,
        execution_reference=execution_reference,
        occurred_at_utc=datetime.now(UTC),
        workspace_verified_absent=verified,
        file_count=report.file_count,
        byte_count=report.byte_count,
        signing_secret=signing_secret,
        event_ttl_seconds=DEFAULT_JOB_POLICY.event_ttl_seconds,
    )
    RecoveryReceiptStore(receipt_root, signing_secret=signing_secret).write(receipt)


def _guardian_wait(
    controller: ProcessController,
    control_descriptor: int,
) -> tuple[ProcessResult, bool]:
    outcomes: queue.Queue[ProcessResult | ProcessControllerError] = queue.Queue(maxsize=1)

    def wait_for_worker() -> None:
        try:
            outcomes.put(controller.wait())
        except ProcessControllerError as error:
            outcomes.put(error)

    wait_thread = threading.Thread(target=wait_for_worker, daemon=True)
    try:
        wait_thread.start()
    except RuntimeError:
        return controller.cancel(), True
    while True:
        try:
            outcome = outcomes.get_nowait()
        except queue.Empty:
            outcome = None
        if isinstance(outcome, ProcessControllerError):
            raise outcome
        if isinstance(outcome, ProcessResult):
            return outcome, False
        readable, _writable, _exceptional = select.select(
            (control_descriptor,), (), (), _POLL_SECONDS
        )
        if not readable:
            continue
        command = os.read(control_descriptor, 1)
        if not command:
            return controller.cancel(), True
        if command == b"C":
            return controller.cancel(), False
        return controller.cancel(), True


def _await_persistence_ack(control_descriptor: int) -> bool:
    deadline = time.monotonic() + _ACK_TIMEOUT_SECONDS
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        readable, _writable, _exceptional = select.select((control_descriptor,), (), (), remaining)
        if not readable:
            return False
        command = os.read(control_descriptor, 1)
        if command == b"A":
            return True
        if command == b"C":
            continue
        return False


def _run_guardian(arguments: list[str]) -> int:
    if len(arguments) != 12 or arguments[0] != _GUARDIAN_MARKER:
        return 126
    controller: ProcessController | None = None
    recovery_attempted = False
    try:
        control_descriptor = int(arguments[1])
        result_descriptor = int(arguments[2])
        secret_descriptor = int(arguments[3])
        job_id = JobId.from_urlsafe(arguments[4])
        workspace_root = Path(arguments[5])
        owner_component = arguments[6]
        job_component = arguments[7]
        receipt_root = Path(arguments[8])
        limits = WorkerLimitProfile.model_validate_json(arguments[9])
        argv = _decoded_argv(arguments[10])
        execution_reference = arguments[11]
        if _OPERATION_REFERENCE.fullmatch(execution_reference) is None:
            raise ValueError
        signing_secret = _read_secret(secret_descriptor)
        os.close(secret_descriptor)
        if job_component != workspace_component(job_id):
            raise ValueError
        controller = ProcessController(argv=argv, cwd=Path.cwd(), limits=limits)
        controller.start()
        _safe_protocol_write(
            result_descriptor,
            f"R {controller.process_group_id}\n".encode("ascii"),
        )
        result, recovery_required = _guardian_wait(controller, control_descriptor)
        _safe_protocol_write(result_descriptor, _result_line(result))
        if not recovery_required:
            recovery_required = not _await_persistence_ack(control_descriptor)
        if recovery_required:
            recovery_attempted = True
            _guardian_cleanup(
                job_id=job_id,
                execution_reference=execution_reference,
                workspace_root=workspace_root,
                owner_component=owner_component,
                job_component=job_component,
                receipt_root=receipt_root,
                signing_secret=signing_secret,
            )
        return 0
    except (OSError, RuntimeError, ValueError):
        reaped = False
        if controller is not None:
            try:
                controller.cancel()
                reaped = True
            except ProcessControllerError:
                controller.reap_until_absent()
                reaped = True
        if reaped and not recovery_attempted and "signing_secret" in locals():
            try:
                _guardian_cleanup(
                    job_id=job_id,
                    execution_reference=execution_reference,
                    workspace_root=workspace_root,
                    owner_component=owner_component,
                    job_component=job_component,
                    receipt_root=receipt_root,
                    signing_secret=signing_secret,
                )
            except (OSError, ValueError, RecoveryReceiptError):
                pass
        _safe_protocol_write(result_descriptor if "result_descriptor" in locals() else -1, b"E\n")
        return 126
    finally:
        for name in ("control_descriptor", "result_descriptor", "secret_descriptor"):
            descriptor = locals().get(name)
            if isinstance(descriptor, int) and descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


__all__ = [
    "GUARDIAN_PROCESS_BOUNDARY",
    "GuardianController",
    "GuardianControllerError",
    "GuardianControllerErrorCode",
]


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess integration tests
    raise SystemExit(_run_guardian(sys.argv[1:]))
