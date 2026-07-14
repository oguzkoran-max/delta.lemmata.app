"""Capability-owned P007 staging with payload-free public lease receipts."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from functools import wraps

from delta_lemmata.clock import Clock, require_utc
from delta_lemmata.ingestion import IntakeReceipt, IntakeRole, ValidatedCorpusPayload
from delta_lemmata.job_service import JobAdmission, JobService
from delta_lemmata.job_staging import ValidatedPayload
from delta_lemmata.job_workspace import CleanupReport, WorkspaceArea, WorkspaceManager
from delta_lemmata.session_identity import JobId, SessionCapability, workspace_component

LeaseIdFactory = Callable[[], str]
CapabilityFactory = Callable[[], SessionCapability]

_LEASE_ID = re.compile(r"^[0-9a-f]{64}$", flags=re.ASCII)
_OWNER_DOMAIN = b"delta-lemmata\x00p007-materialization-owner\x00v1\x00"
_CATALOG_DOMAIN = b"delta-lemmata\x00p007-materialized-catalog\x00v1\x00"


class CorpusMaterializationErrorCode(StrEnum):
    INVALID_CONFIGURATION = "P007_MATERIALIZATION_INVALID_CONFIGURATION"
    INVALID_REQUEST = "P007_MATERIALIZATION_INVALID_REQUEST"
    INVALID_IDENTIFIER = "P007_MATERIALIZATION_INVALID_IDENTIFIER"
    ADMISSION_REJECTED = "P007_MATERIALIZATION_ADMISSION_REJECTED"
    NOT_AVAILABLE = "P007_MATERIALIZATION_NOT_AVAILABLE"
    EXPIRED = "P007_MATERIALIZATION_EXPIRED"
    INTEGRITY = "P007_MATERIALIZATION_INTEGRITY"
    PREPARATION_FAILED = "P007_MATERIALIZATION_PREPARATION_FAILED"
    CLEANUP_FAILED = "P007_MATERIALIZATION_CLEANUP_FAILED"
    OPERATION_FAILED = "P007_MATERIALIZATION_OPERATION_FAILED"


class CorpusMaterializationError(RuntimeError):
    """Content-free P007 private-workspace failure."""

    def __init__(self, code: CorpusMaterializationErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class CorpusMaterializationReceipt:
    """Payload-free locator safe for the server-side presentation workflow."""

    schema_version: str
    lease_id: str
    job_id: str
    source_catalog_sha256: str
    source_count: int
    byte_count: int
    expires_at_utc: datetime


@dataclass(frozen=True, slots=True)
class _StagedBinding:
    receipt: IntakeReceipt
    file_component: str


@dataclass(slots=True)
class _LeaseState:
    owner_reference: str
    capability: SessionCapability
    job_owner_digest: str
    receipt: CorpusMaterializationReceipt
    bindings: tuple[_StagedBinding, ...]
    visiting: bool = False


def _detach(error: CorpusMaterializationError) -> None:
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True


def _error(code: CorpusMaterializationErrorCode) -> CorpusMaterializationError:
    error = CorpusMaterializationError(code)
    _detach(error)
    return error


def _content_free[**P, ResultT](method: Callable[P, ResultT]) -> Callable[P, ResultT]:
    @wraps(method)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> ResultT:
        try:
            return method(*args, **kwargs)
        except CorpusMaterializationError as error:
            rejection = error
        except Exception:
            rejection = CorpusMaterializationError(CorpusMaterializationErrorCode.OPERATION_FAILED)
        _detach(rejection)
        raise rejection

    return wrapped


def _owner_reference(owner_key: str) -> str:
    if not isinstance(owner_key, str) or not 1 <= len(owner_key) <= 512:
        raise _error(CorpusMaterializationErrorCode.INVALID_REQUEST)
    try:
        encoded = owner_key.encode("utf-8", errors="strict")
    except UnicodeError:
        raise _error(CorpusMaterializationErrorCode.INVALID_REQUEST) from None
    return hashlib.sha256(_OWNER_DOMAIN + encoded).hexdigest()


def _source_catalog_sha256(payloads: Sequence[ValidatedCorpusPayload]) -> str:
    records = tuple(
        {
            "byte_count": item.receipt.byte_size,
            "display_label_sha256": hashlib.sha256(
                item.receipt.display_label.encode("utf-8")
            ).hexdigest(),
            "intake_profile": item.receipt.limit_profile,
            "raw_sha256": item.receipt.sha256,
        }
        for item in payloads
    )
    encoded = json.dumps(records, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(_CATALOG_DOMAIN + encoded).hexdigest()


class CorpusMaterializationService:
    """Keep capabilities and private file bindings outside Streamlit state."""

    @_content_free
    def __init__(
        self,
        *,
        jobs: JobService,
        workspaces: WorkspaceManager,
        clock: Clock,
        lease_id_factory: LeaseIdFactory,
        capability_factory: CapabilityFactory = SessionCapability.generate,
    ) -> None:
        if (
            not isinstance(jobs, JobService)
            or not isinstance(workspaces, WorkspaceManager)
            or not hasattr(clock, "now")
            or not callable(lease_id_factory)
            or not callable(capability_factory)
        ):
            raise _error(CorpusMaterializationErrorCode.INVALID_CONFIGURATION)
        self._jobs = jobs
        self._workspaces = workspaces
        self._clock = clock
        self._lease_id_factory = lease_id_factory
        self._capability_factory = capability_factory
        self._leases: dict[str, _LeaseState] = {}
        self._reserved: set[str] = set()
        self._lock = threading.RLock()

    def _now(self) -> datetime:
        try:
            return require_utc(self._clock.now(), field_name="materialization clock")
        except Exception:
            raise _error(CorpusMaterializationErrorCode.INVALID_CONFIGURATION) from None

    def _reserve_lease_id(self) -> str:
        try:
            lease_id = self._lease_id_factory()
        except Exception:
            raise _error(CorpusMaterializationErrorCode.INVALID_IDENTIFIER) from None
        if not isinstance(lease_id, str) or _LEASE_ID.fullmatch(lease_id) is None:
            raise _error(CorpusMaterializationErrorCode.INVALID_IDENTIFIER)
        with self._lock:
            if lease_id in self._leases or lease_id in self._reserved:
                raise _error(CorpusMaterializationErrorCode.INVALID_IDENTIFIER)
            self._reserved.add(lease_id)
        return lease_id

    def _release_reservation(self, lease_id: str) -> None:
        with self._lock:
            self._reserved.discard(lease_id)

    @_content_free
    def materialize(
        self,
        *,
        owner_key: str,
        payloads: Sequence[ValidatedCorpusPayload],
    ) -> CorpusMaterializationReceipt:
        """Stage one validated corpus while retaining no source bytes in the registry."""

        owner_reference = _owner_reference(owner_key)
        if not payloads or any(
            not isinstance(item, ValidatedCorpusPayload)
            or item.receipt.role is not IntakeRole.CORPUS_TEXT
            for item in payloads
        ):
            raise _error(CorpusMaterializationErrorCode.INVALID_REQUEST)
        lease_id = self._reserve_lease_id()
        admission: JobAdmission | None = None
        try:
            try:
                capability = self._capability_factory()
                if not isinstance(capability, SessionCapability):
                    raise TypeError
                admission = self._jobs.admit(
                    capability=capability,
                    payloads=tuple(
                        ValidatedPayload(receipt=item.receipt, content=item.content)
                        for item in payloads
                    ),
                    queued=False,
                )
            except Exception:
                raise _error(CorpusMaterializationErrorCode.ADMISSION_REJECTED) from None
            deadline = admission.job.execution.deadline_at_utc
            if deadline is None:
                raise _error(CorpusMaterializationErrorCode.INTEGRITY)
            expires_at = require_utc(deadline, field_name="materialization expiry")
            staged_assets = admission.materialization.assets
            if len(staged_assets) != len(payloads):
                raise _error(CorpusMaterializationErrorCode.INTEGRITY)
            bindings: list[_StagedBinding] = []
            for item, staged in zip(payloads, staged_assets, strict=True):
                if (
                    staged.role is not IntakeRole.CORPUS_TEXT
                    or staged.byte_size != item.receipt.byte_size
                    or staged.sha256 != item.receipt.sha256
                ):
                    raise _error(CorpusMaterializationErrorCode.INTEGRITY)
                bindings.append(
                    _StagedBinding(
                        receipt=item.receipt,
                        file_component=staged.file_component,
                    )
                )
            receipt = CorpusMaterializationReceipt(
                schema_version="corpus-materialization-receipt-v1",
                lease_id=lease_id,
                job_id=admission.job.job_id,
                source_catalog_sha256=_source_catalog_sha256(payloads),
                source_count=len(payloads),
                byte_count=sum(item.receipt.byte_size for item in payloads),
                expires_at_utc=expires_at,
            )
            state = _LeaseState(
                owner_reference=owner_reference,
                capability=capability,
                job_owner_digest=admission.job.owner_digest,
                receipt=receipt,
                bindings=tuple(bindings),
            )
            with self._lock:
                self._leases[lease_id] = state
            return receipt
        except CorpusMaterializationError as rejection:
            if admission is not None:
                try:
                    self._jobs.cleanup(
                        job_id=admission.job.job_id,
                        capability=capability,
                    )
                except Exception:
                    raise _error(CorpusMaterializationErrorCode.CLEANUP_FAILED) from None
            raise rejection
        finally:
            self._release_reservation(lease_id)

    def _begin_visit(
        self,
        owner_reference: str,
        receipt: CorpusMaterializationReceipt,
    ) -> _LeaseState:
        with self._lock:
            state = self._leases.get(receipt.lease_id)
            if (
                state is None
                or state.owner_reference != owner_reference
                or state.receipt != receipt
                or state.visiting
            ):
                raise _error(CorpusMaterializationErrorCode.NOT_AVAILABLE)
            state.visiting = True
            return state

    def _finish_visit(self, state: _LeaseState) -> None:
        with self._lock:
            current = self._leases.get(state.receipt.lease_id)
            if current is state:
                current.visiting = False

    def _remove(self, state: _LeaseState) -> None:
        with self._lock:
            current = self._leases.get(state.receipt.lease_id)
            if current is state:
                del self._leases[state.receipt.lease_id]

    def _cleanup_state(self, state: _LeaseState) -> CleanupReport:
        try:
            report = self._jobs.cleanup(
                job_id=state.receipt.job_id,
                capability=state.capability,
            )
        except Exception:
            self._finish_visit(state)
            raise _error(CorpusMaterializationErrorCode.CLEANUP_FAILED) from None
        self._remove(state)
        return report

    @_content_free
    def visit[ResultT](
        self,
        *,
        owner_key: str,
        receipt: CorpusMaterializationReceipt,
        visitor: Callable[[tuple[ValidatedCorpusPayload, ...]], ResultT],
    ) -> ResultT:
        """Reauthorize, re-read, and revalidate private sources for one preparation call."""

        owner_reference = _owner_reference(owner_key)
        if not isinstance(receipt, CorpusMaterializationReceipt) or not callable(visitor):
            raise _error(CorpusMaterializationErrorCode.INVALID_REQUEST)
        state = self._begin_visit(owner_reference, receipt)
        try:
            expired = self._now() > receipt.expires_at_utc
        except CorpusMaterializationError:
            self._cleanup_state(state)
            raise
        if expired:
            self._cleanup_state(state)
            raise _error(CorpusMaterializationErrorCode.EXPIRED)
        try:
            self._jobs.status(job_id=receipt.job_id, capability=state.capability)
            layout = self._workspaces.load(
                state.job_owner_digest,
                workspace_component(JobId.from_urlsafe(receipt.job_id)),
            )
            loaded: list[ValidatedCorpusPayload] = []
            for binding in state.bindings:
                content = self._workspaces.read_file(
                    layout,
                    WorkspaceArea.INPUT,
                    binding.file_component,
                    maximum_bytes=binding.receipt.byte_size,
                )
                if (
                    content is None
                    or len(content) != binding.receipt.byte_size
                    or hashlib.sha256(content).hexdigest() != binding.receipt.sha256
                ):
                    raise ValueError
                loaded.append(ValidatedCorpusPayload(receipt=binding.receipt, content=content))
        except Exception:
            self._cleanup_state(state)
            raise _error(CorpusMaterializationErrorCode.INTEGRITY) from None
        try:
            result = visitor(tuple(loaded))
        except Exception:
            self._cleanup_state(state)
            raise _error(CorpusMaterializationErrorCode.PREPARATION_FAILED) from None
        self._finish_visit(state)
        return result

    @_content_free
    def cleanup(
        self,
        *,
        owner_key: str,
        receipt: CorpusMaterializationReceipt,
    ) -> CleanupReport:
        """Remove one owned materialization and prove the workspace absent."""

        owner_reference = _owner_reference(owner_key)
        if not isinstance(receipt, CorpusMaterializationReceipt):
            raise _error(CorpusMaterializationErrorCode.INVALID_REQUEST)
        state = self._begin_visit(owner_reference, receipt)
        return self._cleanup_state(state)


__all__ = [
    "CorpusMaterializationError",
    "CorpusMaterializationErrorCode",
    "CorpusMaterializationReceipt",
    "CorpusMaterializationService",
]
