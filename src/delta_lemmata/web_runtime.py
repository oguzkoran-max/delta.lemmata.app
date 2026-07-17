"""Private runtime composition for the Streamlit presentation layer."""

from __future__ import annotations

import os
import re
import secrets
import stat
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, RLock, Thread

from delta_lemmata.analysis_orchestrator import AnalysisOrchestrator
from delta_lemmata.clock import SystemClock
from delta_lemmata.corpus_materialization import CorpusMaterializationService
from delta_lemmata.job_janitor import JobJanitor
from delta_lemmata.job_service import JobService
from delta_lemmata.job_store import SQLiteJobStore
from delta_lemmata.job_workspace import WorkspaceManager
from delta_lemmata.prepared_corpus_service import PreparedCorpusService
from delta_lemmata.recovery_receipt import RecoveryReceiptStore
from delta_lemmata.result_service import ResultPackageService
from delta_lemmata.session_identity import MINIMUM_OWNER_SECRET_BYTES
from delta_lemmata.stylo_job_runner import StyloJobRunner

_SECRET_HEX = re.compile(r"[0-9a-fA-F]+\Z")
_RUNTIME_PROFILES = frozenset({"development", "test", "production"})
_MAINTENANCE_INTERVAL_SECONDS = 60.0
_MAINTENANCE_JOIN_TIMEOUT_SECONDS = 5.0


class WebRuntimeErrorCode(StrEnum):
    """Stable, content-free startup failures for the web runtime."""

    INVALID_PROFILE = "WEB_RUNTIME_INVALID_PROFILE"
    INVALID_ROOT = "WEB_RUNTIME_INVALID_ROOT"
    MISSING_SECRET = "WEB_RUNTIME_MISSING_SECRET"
    INVALID_SECRET = "WEB_RUNTIME_INVALID_SECRET"
    SECRET_REUSE = "WEB_RUNTIME_SECRET_REUSE"
    MAINTENANCE_FAILED = "WEB_RUNTIME_MAINTENANCE_FAILED"
    INITIALIZATION_FAILED = "WEB_RUNTIME_INITIALIZATION_FAILED"


class WebRuntimeError(RuntimeError):
    """A web-runtime rejection that never contains a path or secret."""

    def __init__(self, code: WebRuntimeErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(slots=True)
class WebRuntime:
    """Server-only services; no instance belongs in Streamlit session state."""

    materializations: CorpusMaterializationService
    prepared_corpora: PreparedCorpusService
    analyses: AnalysisOrchestrator
    janitor: JobJanitor
    _temporary_directory: TemporaryDirectory[str] | None = field(default=None, repr=False)
    _maintenance_stop: Event | None = field(default=None, repr=False)
    _maintenance_thread: Thread | None = field(default=None, repr=False)
    _maintenance_lock: RLock = field(default_factory=RLock, repr=False)

    def maintain(self) -> None:
        """Reconcile expired in-memory and durable work before new admission."""

        failed = False
        with self._maintenance_lock:
            for operation in (self.materializations.reap_expired, self.janitor.run_once):
                try:
                    operation()
                except Exception:
                    failed = True
        if failed:
            rejection = _error(WebRuntimeErrorCode.MAINTENANCE_FAILED)
            rejection.__context__ = None
            rejection.__cause__ = None
            rejection.__suppress_context__ = True
            raise rejection

    def run_analysis_once[ResultT](
        self,
        *,
        finalize_result: Callable[[], ResultT],
    ) -> ResultT:
        """Run, verify, and publish one result before terminal cleanup."""

        with self._maintenance_lock:
            primary_failed = False
            try:
                self.analyses.run_next()
                return finalize_result()
            except Exception:
                primary_failed = True
                raise
            finally:
                try:
                    self.maintain()
                except WebRuntimeError:
                    if not primary_failed:
                        raise

    def start_periodic_maintenance(self) -> None:
        """Start process-local cleanup that does not depend on browser traffic."""

        if self._maintenance_thread is not None:
            return
        stop = Event()
        thread = Thread(
            target=self._maintenance_loop,
            args=(stop,),
            name="delta-job-maintenance",
            daemon=True,
        )
        self._maintenance_stop = stop
        self._maintenance_thread = thread
        thread.start()

    def _maintenance_loop(self, stop: Event) -> None:
        while not stop.wait(_MAINTENANCE_INTERVAL_SECONDS):
            try:
                self.maintain()
            except WebRuntimeError:
                continue

    def close(self) -> None:
        """Release a development-only temporary root during deterministic tests."""

        if self._maintenance_stop is not None and self._maintenance_thread is not None:
            self._maintenance_stop.set()
            self._maintenance_thread.join(timeout=_MAINTENANCE_JOIN_TIMEOUT_SECONDS)
            self._maintenance_stop = None
            self._maintenance_thread = None

        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
            self._temporary_directory = None


def _error(code: WebRuntimeErrorCode) -> WebRuntimeError:
    error = WebRuntimeError(code)
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True
    return error


def _secret(
    environment: Mapping[str, str],
    name: str,
    *,
    required: bool,
) -> bytes:
    value = environment.get(name)
    if value is None or not value.strip():
        if required:
            raise _error(WebRuntimeErrorCode.MISSING_SECRET)
        return secrets.token_bytes(MINIMUM_OWNER_SECRET_BYTES)
    candidate = value.strip()
    if (
        len(candidate) % 2 != 0
        or _SECRET_HEX.fullmatch(candidate) is None
        or len(candidate) < MINIMUM_OWNER_SECRET_BYTES * 2
    ):
        raise _error(WebRuntimeErrorCode.INVALID_SECRET)
    return bytes.fromhex(candidate)


def _private_directory(path: Path, *, create: bool) -> Path:
    if not path.is_absolute() or path != Path(os.path.abspath(path)):
        raise _error(WebRuntimeErrorCode.INVALID_ROOT)
    if create:
        creation_rejection: WebRuntimeError | None = None
        try:
            path.mkdir(mode=0o700, exist_ok=False)
        except FileExistsError:
            pass
        except OSError:
            creation_rejection = _error(WebRuntimeErrorCode.INVALID_ROOT)
        if creation_rejection is not None:
            raise creation_rejection
    inspection_rejection: WebRuntimeError | None = None
    try:
        info = os.lstat(path)
        resolved = path.resolve(strict=True)
        resolved_info = os.stat(resolved, follow_symlinks=False)
    except OSError:
        inspection_rejection = _error(WebRuntimeErrorCode.INVALID_ROOT)
    if inspection_rejection is not None:
        raise inspection_rejection
    if (
        path != resolved
        or not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077
        or (info.st_dev, info.st_ino) != (resolved_info.st_dev, resolved_info.st_ino)
    ):
        raise _error(WebRuntimeErrorCode.INVALID_ROOT)
    return resolved


def build_web_runtime(environment: Mapping[str, str] | None = None) -> WebRuntime:
    """Build one process runtime, requiring explicit production roots and secrets."""

    values = os.environ if environment is None else environment
    profile = values.get("DELTA_ENV", "development").strip().casefold()
    if profile not in _RUNTIME_PROFILES:
        raise _error(WebRuntimeErrorCode.INVALID_PROFILE)

    temporary: TemporaryDirectory[str] | None = None
    root_value = values.get("DELTA_RUNTIME_ROOT", "").strip()
    if not root_value:
        if profile == "production":
            raise _error(WebRuntimeErrorCode.INVALID_ROOT)
        temporary = TemporaryDirectory(prefix="delta-runtime-")
        root = Path(temporary.name).resolve(strict=True)
    else:
        root = Path(root_value)

    rejection: WebRuntimeError | None = None
    try:
        root = _private_directory(root, create=profile != "production")
        database_root = _private_directory(root / "database", create=True)
        workspace_root = _private_directory(root / "workspaces", create=True)
        recovery_receipt_root = _private_directory(
            root / "recovery-receipts",
            create=True,
        )
        store_secret = _secret(
            values,
            "DELTA_JOB_OWNER_SECRET_HEX",
            required=profile == "production",
        )
        authority_secret = _secret(
            values,
            "DELTA_PREPARATION_AUTHORITY_SECRET_HEX",
            required=profile == "production",
        )
        recovery_receipt_secret = _secret(
            values,
            "DELTA_RECOVERY_RECEIPT_SECRET_HEX",
            required=profile == "production",
        )
        secrets_are_distinct = (
            not secrets.compare_digest(store_secret, authority_secret)
            and not secrets.compare_digest(store_secret, recovery_receipt_secret)
            and not secrets.compare_digest(authority_secret, recovery_receipt_secret)
        )
        if not secrets_are_distinct:
            raise _error(WebRuntimeErrorCode.SECRET_REUSE)

        clock = SystemClock()
        store = SQLiteJobStore(
            database_root / "control.sqlite3",
            owner_secret=store_secret,
        )
        workspaces = WorkspaceManager(workspace_root)
        recovery_receipts = RecoveryReceiptStore(
            recovery_receipt_root,
            signing_secret=recovery_receipt_secret,
        )
        jobs = JobService(store=store, workspaces=workspaces, clock=clock)
        results = ResultPackageService(store=store, workspaces=workspaces, clock=clock)
        janitor = JobJanitor(
            store=store,
            workspaces=workspaces,
            clock=clock,
            recovery_receipts=recovery_receipts,
        )
        janitor.recover_startup()
        materializations = CorpusMaterializationService(
            jobs=jobs,
            workspaces=workspaces,
            clock=clock,
            lease_id_factory=lambda: secrets.token_hex(32),
            results=results,
        )
        prepared_corpora = PreparedCorpusService(
            materializations=materializations,
            workspaces=workspaces,
            clock=clock,
            authority_secret=authority_secret,
        )
        runner = StyloJobRunner(
            store=store,
            workspaces=workspaces,
            receipts=recovery_receipts,
            clock=clock,
        )
        analyses = AnalysisOrchestrator(
            store=store,
            workspaces=workspaces,
            runner=runner,
            clock=clock,
        )
    except WebRuntimeError as error:
        rejection = error
    except Exception:
        rejection = _error(WebRuntimeErrorCode.INITIALIZATION_FAILED)
    if rejection is not None:
        if temporary is not None:
            temporary.cleanup()
        rejection.__context__ = None
        rejection.__cause__ = None
        rejection.__suppress_context__ = True
        raise rejection
    runtime = WebRuntime(
        materializations=materializations,
        prepared_corpora=prepared_corpora,
        analyses=analyses,
        janitor=janitor,
        _temporary_directory=temporary,
    )
    if profile == "production":
        maintenance_rejection: WebRuntimeError | None = None
        try:
            runtime.start_periodic_maintenance()
        except Exception:
            runtime.close()
            maintenance_rejection = _error(WebRuntimeErrorCode.INITIALIZATION_FAILED)
        if maintenance_rejection is not None:
            maintenance_rejection.__context__ = None
            maintenance_rejection.__cause__ = None
            maintenance_rejection.__suppress_context__ = True
            raise maintenance_rejection
    return runtime


__all__ = [
    "WebRuntime",
    "WebRuntimeError",
    "WebRuntimeErrorCode",
    "build_web_runtime",
]
