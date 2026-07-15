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
from delta_lemmata.job_service import (
    JobAdmission,
    JobService,
    JobServiceError,
    JobServiceErrorCode,
)
from delta_lemmata.job_staging import ValidatedPayload
from delta_lemmata.job_ui import JobPresentation
from delta_lemmata.job_workspace import (
    CleanupReport,
    WorkspaceArea,
    WorkspaceLayout,
    WorkspaceManager,
)
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
    READY_CONFLICT = "P007_MATERIALIZATION_READY_CONFLICT"
    READY_REJECTED = "P007_MATERIALIZATION_READY_REJECTED"
    READY_REUSED = "P007_MATERIALIZATION_READY_REUSED"
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
    job_version: int
    receipt: CorpusMaterializationReceipt
    bindings: tuple[_StagedBinding, ...]
    ready_receipt_hmac: str | None = None
    consumed: bool = False
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
        self._capabilities: dict[str, SessionCapability] = {}
        self._capability_claims: dict[str, int] = {}
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

    def _capability_for(self, owner_reference: str) -> SessionCapability:
        with self._lock:
            existing = self._capabilities.get(owner_reference)
            if existing is not None:
                self._capability_claims[owner_reference] = (
                    self._capability_claims.get(owner_reference, 0) + 1
                )
                return existing
            try:
                capability = self._capability_factory()
            except Exception:
                raise _error(CorpusMaterializationErrorCode.ADMISSION_REJECTED) from None
            if not isinstance(capability, SessionCapability):
                raise _error(CorpusMaterializationErrorCode.ADMISSION_REJECTED)
            self._capabilities[owner_reference] = capability
            self._capability_claims[owner_reference] = 1
            return capability

    def _release_capability_claim(self, owner_reference: str) -> None:
        with self._lock:
            claims = self._capability_claims.get(owner_reference)
            if claims is None:  # pragma: no cover - internal pairing invariant
                return
            if claims > 1:
                self._capability_claims[owner_reference] = claims - 1
                return
            del self._capability_claims[owner_reference]
            self._evict_unused_capability(owner_reference)

    def _evict_unused_capability(self, owner_reference: str) -> None:
        if owner_reference in self._capability_claims:
            return
        if any(state.owner_reference == owner_reference for state in self._leases.values()):
            return
        self._capabilities.pop(owner_reference, None)

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
        capability_claimed = False
        try:
            try:
                capability = self._capability_for(owner_reference)
                capability_claimed = True
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
                job_version=admission.job.version,
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
            if capability_claimed:
                self._release_capability_claim(owner_reference)
            self._release_reservation(lease_id)

    def _begin_visit(
        self,
        owner_reference: str,
        receipt: CorpusMaterializationReceipt,
        *,
        allow_consumed: bool = False,
    ) -> _LeaseState:
        with self._lock:
            state = self._leases.get(receipt.lease_id)
            if (
                state is None
                or state.owner_reference != owner_reference
                or state.receipt != receipt
                or state.visiting
                or (state.consumed and not allow_consumed)
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
                self._evict_unused_capability(state.owner_reference)

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
    def reap_expired(self) -> int:
        """Remove expired, idle leases before admitting more browser work."""

        now = self._now()
        removed = 0
        while True:
            with self._lock:
                state = next(
                    (
                        candidate
                        for candidate in self._leases.values()
                        if not candidate.visiting and now >= candidate.receipt.expires_at_utc
                    ),
                    None,
                )
                if state is None:
                    return removed
                state.visiting = True
            self._cleanup_state(state)
            removed += 1

    @_content_free
    def visit[ResultT](
        self,
        *,
        owner_key: str,
        receipt: CorpusMaterializationReceipt,
        visitor: Callable[[tuple[ValidatedCorpusPayload, ...]], ResultT],
    ) -> ResultT:
        """Reauthorize, re-read, and revalidate private sources for one preparation call."""

        if not callable(visitor):
            raise _error(CorpusMaterializationErrorCode.INVALID_REQUEST)
        return self._visit_workspace(
            owner_key=owner_key,
            receipt=receipt,
            visitor=lambda payloads, _layout: visitor(payloads),
        )

    @_content_free
    def _visit_workspace[ResultT](
        self,
        *,
        owner_key: str,
        receipt: CorpusMaterializationReceipt,
        visitor: Callable[
            [tuple[ValidatedCorpusPayload, ...], WorkspaceLayout],
            ResultT,
        ],
        ready_receipt_hmac: str | None = None,
    ) -> ResultT:
        """Visit verified sources with their private P005 workspace."""

        owner_reference = _owner_reference(owner_key)
        if (
            not isinstance(receipt, CorpusMaterializationReceipt)
            or not callable(visitor)
            or (
                ready_receipt_hmac is not None
                and (
                    not isinstance(ready_receipt_hmac, str)
                    or _LEASE_ID.fullmatch(ready_receipt_hmac) is None
                )
            )
        ):
            raise _error(CorpusMaterializationErrorCode.INVALID_REQUEST)
        state = self._begin_visit(owner_reference, receipt, allow_consumed=True)
        if state.consumed:
            self._finish_visit(state)
            if ready_receipt_hmac == state.ready_receipt_hmac:
                raise _error(CorpusMaterializationErrorCode.READY_REUSED)
            raise _error(CorpusMaterializationErrorCode.NOT_AVAILABLE)
        if ready_receipt_hmac is not None and state.ready_receipt_hmac != ready_receipt_hmac:
            self._finish_visit(state)
            raise _error(CorpusMaterializationErrorCode.READY_REJECTED)
        try:
            expired = self._now() >= receipt.expires_at_utc
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
            result = visitor(tuple(loaded), layout)
        except Exception:
            self._cleanup_state(state)
            raise _error(CorpusMaterializationErrorCode.PREPARATION_FAILED) from None
        self._finish_visit(state)
        return result

    @_content_free
    def bind_ready(
        self,
        *,
        owner_key: str,
        receipt: CorpusMaterializationReceipt,
        ready_receipt_hmac: str,
        expires_at_utc: datetime,
    ) -> None:
        """Bind one private READY authority to the staged P005 job."""

        owner_reference = _owner_reference(owner_key)
        if (
            not isinstance(receipt, CorpusMaterializationReceipt)
            or not isinstance(ready_receipt_hmac, str)
            or _LEASE_ID.fullmatch(ready_receipt_hmac) is None
            or not isinstance(expires_at_utc, datetime)
        ):
            raise _error(CorpusMaterializationErrorCode.INVALID_REQUEST)
        state = self._begin_visit(owner_reference, receipt)
        try:
            now = self._now()
            expiry = require_utc(expires_at_utc, field_name="READY expiry")
            if now >= expiry or expiry > receipt.expires_at_utc:
                self._cleanup_state(state)
                raise _error(CorpusMaterializationErrorCode.EXPIRED)
            if (
                state.ready_receipt_hmac is not None
                and state.ready_receipt_hmac != ready_receipt_hmac
            ):
                raise _error(CorpusMaterializationErrorCode.READY_CONFLICT)
            self._jobs.bind_analysis_admission(
                receipt_hmac=ready_receipt_hmac,
                job_id=receipt.job_id,
                capability=state.capability,
                at_utc=now,
                expires_at_utc=expiry,
                expected_job_version=state.job_version,
            )
            state.ready_receipt_hmac = ready_receipt_hmac
        except CorpusMaterializationError:
            raise
        except JobServiceError:
            raise _error(CorpusMaterializationErrorCode.READY_REJECTED) from None
        except Exception:
            raise _error(CorpusMaterializationErrorCode.READY_REJECTED) from None
        finally:
            self._finish_visit(state)

    @_content_free
    def consume_ready(
        self,
        *,
        owner_key: str,
        receipt: CorpusMaterializationReceipt,
        ready_receipt_hmac: str,
        operation_id: str,
    ) -> JobPresentation:
        """Consume one bound READY authority and release the local lease state."""

        owner_reference = _owner_reference(owner_key)
        if (
            not isinstance(receipt, CorpusMaterializationReceipt)
            or not isinstance(ready_receipt_hmac, str)
            or _LEASE_ID.fullmatch(ready_receipt_hmac) is None
            or not isinstance(operation_id, str)
        ):
            raise _error(CorpusMaterializationErrorCode.INVALID_REQUEST)
        state = self._begin_visit(owner_reference, receipt, allow_consumed=True)
        if state.ready_receipt_hmac != ready_receipt_hmac:
            self._finish_visit(state)
            raise _error(CorpusMaterializationErrorCode.READY_REJECTED)
        if state.consumed:
            self._finish_visit(state)
            raise _error(CorpusMaterializationErrorCode.READY_REUSED)
        try:
            now = self._now()
            if now >= receipt.expires_at_utc:
                self._cleanup_state(state)
                raise _error(CorpusMaterializationErrorCode.EXPIRED)
            presentation = self._jobs.consume_analysis_admission(
                receipt_hmac=ready_receipt_hmac,
                job_id=receipt.job_id,
                capability=state.capability,
                at_utc=now,
                operation_id=operation_id,
            )
        except CorpusMaterializationError:
            self._finish_visit(state)
            raise
        except JobServiceError as error:
            if error.code is JobServiceErrorCode.ANALYSIS_ADMISSION_REUSED:
                state.consumed = True
                self._finish_visit(state)
                raise _error(CorpusMaterializationErrorCode.READY_REUSED) from None
            self._finish_visit(state)
            raise _error(CorpusMaterializationErrorCode.READY_REJECTED) from None
        except Exception:
            self._finish_visit(state)
            raise _error(CorpusMaterializationErrorCode.READY_REJECTED) from None
        state.consumed = True
        self._finish_visit(state)
        return presentation

    @_content_free
    def status(
        self,
        *,
        owner_key: str,
        receipt: CorpusMaterializationReceipt,
    ) -> JobPresentation:
        """Return one owned P005 projection without exposing its capability."""

        owner_reference = _owner_reference(owner_key)
        if not isinstance(receipt, CorpusMaterializationReceipt):
            raise _error(CorpusMaterializationErrorCode.INVALID_REQUEST)
        state = self._begin_visit(owner_reference, receipt, allow_consumed=True)
        if not state.consumed:
            try:
                expired = self._now() >= receipt.expires_at_utc
            except CorpusMaterializationError:
                self._cleanup_state(state)
                raise
            if expired:
                self._cleanup_state(state)
                raise _error(CorpusMaterializationErrorCode.EXPIRED)
        try:
            presentation = self._jobs.status(
                job_id=receipt.job_id,
                capability=state.capability,
            )
        except Exception:
            raise _error(CorpusMaterializationErrorCode.NOT_AVAILABLE) from None
        finally:
            self._finish_visit(state)
        return presentation

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
        state = self._begin_visit(owner_reference, receipt, allow_consumed=True)
        return self._cleanup_state(state)


__all__ = [
    "CorpusMaterializationError",
    "CorpusMaterializationErrorCode",
    "CorpusMaterializationReceipt",
    "CorpusMaterializationService",
]
