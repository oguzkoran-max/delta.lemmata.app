"""Authenticated, content-free recovery evidence for guardian-managed jobs."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import stat
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import StrEnum
from functools import wraps
from pathlib import Path
from typing import Annotated, Literal, NoReturn, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from delta_lemmata.clock import require_utc
from delta_lemmata.job_events import MAX_EVENT_TTL_SECONDS
from delta_lemmata.job_models import (
    CleanupState,
    ExecutionState,
    JobRecord,
    TerminalOutcome,
    terminal_operation_version,
)
from delta_lemmata.session_identity import (
    MINIMUM_OWNER_SECRET_BYTES,
    JobId,
    workspace_component,
)

ReceiptDigest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ReceiptSignature = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

_DIRECTORY_MODE = 0o700
_FILE_MODE = 0o600
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
_FILE_READ_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
_FILE_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
_MAX_RECEIPT_BYTES = 4096
_SIGNATURE_DOMAIN = b"delta-lemmata\x00guardian-recovery-receipt\x00v1\x00"
_EXECUTION_DOMAIN = b"delta-lemmata\x00guardian-execution-reference\x00v1\x00"
_EXECUTION_REFERENCE = re.compile(r"^op_[0-9a-f]{64}$", flags=re.ASCII)
_RECORD_NAME = re.compile(r"^[0-9a-f]{64}\.[0-9a-f]{64}$", flags=re.ASCII)


class RecoveryReceiptErrorCode(StrEnum):
    INVALID_CONFIGURATION = "RECOVERY_RECEIPT_INVALID_CONFIGURATION"
    INVALID_ROOT = "RECOVERY_RECEIPT_INVALID_ROOT"
    INVALID_RECORD = "RECOVERY_RECEIPT_INVALID_RECORD"
    WRITE_FAILED = "RECOVERY_RECEIPT_WRITE_FAILED"


class ScientificRecoveryDisposition(StrEnum):
    """Closed startup decision for one pending scientific result."""

    ACCEPTED = "accepted"
    RECOVERY_REQUIRED = "recovery_required"
    UNRESOLVED = "unresolved"


class RecoveryReceiptError(RuntimeError):
    def __init__(self, code: RecoveryReceiptErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


def _reject(code: RecoveryReceiptErrorCode) -> NoReturn:
    error = RecoveryReceiptError(code)
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True
    raise error from None


def _content_free[**P, T](method: Callable[P, T]) -> Callable[P, T]:
    @wraps(method)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return method(*args, **kwargs)
        except RecoveryReceiptError as error:
            rejection = error
        except OSError:
            rejection = RecoveryReceiptError(RecoveryReceiptErrorCode.INVALID_RECORD)
        rejection.__context__ = None
        rejection.__cause__ = None
        rejection.__suppress_context__ = True
        raise rejection

    return wrapped


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


class RecoveryReceipt(BaseModel):
    """One signed guardian fact with no process or research payload identifiers."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    schema_version: Literal[
        "guardian-recovery-receipt-v1",
        "guardian-disposition-receipt-v2",
    ] = "guardian-recovery-receipt-v1"
    job_reference_digest: ReceiptDigest
    execution_reference_digest: ReceiptDigest
    outcome: Literal["recovery_required", "accepted"] = "recovery_required"
    occurred_at_utc: datetime
    worker_group_verified_absent: Literal[True] = True
    workspace_verified_absent: bool
    file_count: int = Field(ge=0)
    byte_count: int = Field(ge=0)
    policy_version: Literal["job-policy-v1"]
    expires_at_utc: datetime
    terminal_version: int | None = Field(default=None, strict=True, ge=0)
    terminal_outcome: TerminalOutcome | None = None
    artifact_sha256: ReceiptDigest | None = None
    artifact_byte_size: int | None = Field(
        default=None,
        strict=True,
        ge=1,
        le=32 * 1024 * 1024,
    )
    signature: ReceiptSignature

    @field_validator("occurred_at_utc", "expires_at_utc")
    @classmethod
    def require_utc_timestamps(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def require_bounded_consistent_evidence(self) -> Self:
        lifetime = self.expires_at_utc - self.occurred_at_utc
        if lifetime <= timedelta(0) or lifetime > timedelta(seconds=MAX_EVENT_TTL_SECONDS):
            raise ValueError("recovery receipt must expire within seven days")
        if not self.workspace_verified_absent and (self.file_count or self.byte_count):
            raise ValueError("unverified cleanup cannot publish deletion counts")
        commitment = (self.artifact_sha256 is not None) == (self.artifact_byte_size is not None)
        if not commitment:
            raise ValueError("artifact digest and size must agree")
        if self.outcome == "recovery_required":
            if (
                self.schema_version != "guardian-recovery-receipt-v1"
                or self.terminal_version is not None
                or self.terminal_outcome is not None
                or self.artifact_sha256 is not None
            ):
                raise ValueError("recovery receipt cannot carry an accepted commitment")
        elif (
            self.schema_version != "guardian-disposition-receipt-v2"
            or self.terminal_version is None
            or self.terminal_outcome is None
            or self.workspace_verified_absent
            or (
                (self.terminal_outcome is TerminalOutcome.SUCCEEDED)
                != (self.artifact_sha256 is not None)
            )
        ):
            raise ValueError("accepted receipt requires one consistent terminal commitment")
        return self


def _unsigned_payload(receipt: RecoveryReceipt | dict[str, object]) -> bytes:
    source = (
        receipt.model_dump(mode="python", exclude_none=True)
        if isinstance(receipt, RecoveryReceipt)
        else receipt
    )
    payload = {
        key: value for key, value in source.items() if key != "signature" and value is not None
    }
    for key in ("occurred_at_utc", "expires_at_utc"):
        value = payload[key]
        if not isinstance(value, datetime):
            raise ValueError
        payload[key] = _timestamp(value)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "ascii"
    )


def _execution_digest(job_id: JobId, execution_reference: str) -> str:
    if (
        not isinstance(job_id, JobId)
        or not isinstance(execution_reference, str)
        or _EXECUTION_REFERENCE.fullmatch(execution_reference) is None
    ):
        raise ValueError("invalid recovery receipt execution reference")
    return hashlib.sha256(
        _EXECUTION_DOMAIN
        + job_id.to_urlsafe().encode("ascii")
        + b"\x00"
        + execution_reference.encode("ascii")
    ).hexdigest()


def _record_name(job_id: JobId, execution_reference: str) -> str:
    return f"{workspace_component(job_id)}.{_execution_digest(job_id, execution_reference)}"


def new_recovery_receipt(
    *,
    job_id: JobId,
    execution_reference: str,
    occurred_at_utc: datetime,
    workspace_verified_absent: bool,
    file_count: int,
    byte_count: int,
    signing_secret: bytes,
    event_ttl_seconds: int,
) -> RecoveryReceipt:
    """Create one signed app-loss receipt from allowlisted values."""

    occurred_at_utc = require_utc(occurred_at_utc, field_name="occurred_at_utc")
    if (
        not isinstance(job_id, JobId)
        or not isinstance(execution_reference, str)
        or _EXECUTION_REFERENCE.fullmatch(execution_reference) is None
        or not isinstance(signing_secret, bytes)
        or len(signing_secret) < MINIMUM_OWNER_SECRET_BYTES
        or event_ttl_seconds <= 0
        or event_ttl_seconds > MAX_EVENT_TTL_SECONDS
    ):
        raise ValueError("invalid recovery receipt inputs")
    payload: dict[str, object] = {
        "schema_version": "guardian-recovery-receipt-v1",
        "job_reference_digest": workspace_component(job_id),
        "execution_reference_digest": _execution_digest(job_id, execution_reference),
        "outcome": "recovery_required",
        "occurred_at_utc": occurred_at_utc,
        "worker_group_verified_absent": True,
        "workspace_verified_absent": workspace_verified_absent,
        "file_count": file_count,
        "byte_count": byte_count,
        "policy_version": "job-policy-v1",
        "expires_at_utc": occurred_at_utc + timedelta(seconds=event_ttl_seconds),
    }
    signature = hmac.digest(
        signing_secret,
        _SIGNATURE_DOMAIN + _unsigned_payload(payload),
        "sha256",
    )
    payload["signature"] = signature.hex()
    return RecoveryReceipt.model_validate(payload)


def new_acceptance_receipt(
    *,
    job_id: JobId,
    execution_reference: str,
    occurred_at_utc: datetime,
    terminal_version: int,
    terminal_outcome: TerminalOutcome,
    artifact_sha256: str | None,
    artifact_byte_size: int | None,
    signing_secret: bytes,
    event_ttl_seconds: int,
) -> RecoveryReceipt:
    """Create one signed proof before a scientific guardian confirms release."""

    occurred_at_utc = require_utc(occurred_at_utc, field_name="occurred_at_utc")
    if (
        not isinstance(job_id, JobId)
        or not isinstance(execution_reference, str)
        or _EXECUTION_REFERENCE.fullmatch(execution_reference) is None
        or isinstance(terminal_version, bool)
        or not isinstance(terminal_version, int)
        or terminal_version < 0
        or not isinstance(terminal_outcome, TerminalOutcome)
        or not isinstance(signing_secret, bytes)
        or len(signing_secret) < MINIMUM_OWNER_SECRET_BYTES
        or event_ttl_seconds <= 0
        or event_ttl_seconds > MAX_EVENT_TTL_SECONDS
    ):
        raise ValueError("invalid acceptance receipt inputs")
    payload: dict[str, object] = {
        "schema_version": "guardian-disposition-receipt-v2",
        "job_reference_digest": workspace_component(job_id),
        "execution_reference_digest": _execution_digest(job_id, execution_reference),
        "outcome": "accepted",
        "occurred_at_utc": occurred_at_utc,
        "worker_group_verified_absent": True,
        "workspace_verified_absent": False,
        "file_count": 0,
        "byte_count": 0,
        "policy_version": "job-policy-v1",
        "expires_at_utc": occurred_at_utc + timedelta(seconds=event_ttl_seconds),
        "terminal_version": terminal_version,
        "terminal_outcome": terminal_outcome,
        "artifact_sha256": artifact_sha256,
        "artifact_byte_size": artifact_byte_size,
    }
    signature = hmac.digest(
        signing_secret,
        _SIGNATURE_DOMAIN + _unsigned_payload(payload),
        "sha256",
    )
    payload["signature"] = signature.hex()
    return RecoveryReceipt.model_validate(payload)


class RecoveryReceiptStore:
    """Private receipt namespace with identity-pinned, no-follow file operations."""

    @_content_free
    def __init__(self, root: Path, *, signing_secret: bytes) -> None:
        if (
            not isinstance(root, Path)
            or not root.is_absolute()
            or root != Path(os.path.abspath(root))
            or not isinstance(signing_secret, bytes)
            or len(signing_secret) < MINIMUM_OWNER_SECRET_BYTES
        ):
            _reject(RecoveryReceiptErrorCode.INVALID_CONFIGURATION)
        try:
            info = os.lstat(root)
            resolved = root.resolve(strict=True)
            resolved_info = os.stat(resolved, follow_symlinks=False)
        except OSError:
            _reject(RecoveryReceiptErrorCode.INVALID_ROOT)
        if (
            root != resolved
            or not stat.S_ISDIR(info.st_mode)
            or stat.S_IMODE(info.st_mode) != _DIRECTORY_MODE
            or info.st_uid != os.getuid()
            or (info.st_dev, info.st_ino) != (resolved_info.st_dev, resolved_info.st_ino)
        ):
            _reject(RecoveryReceiptErrorCode.INVALID_ROOT)
        self.root = root
        self._signing_secret = signing_secret
        self._root_identity = (info.st_dev, info.st_ino)

    @_content_free
    def write(self, receipt: RecoveryReceipt) -> bool:
        """Atomically create one immutable receipt; identical retries are no-ops."""

        if not isinstance(receipt, RecoveryReceipt) or not self._valid_signature(receipt):
            _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
        encoded = receipt.model_dump_json().encode("utf-8")
        if len(encoded) > _MAX_RECEIPT_BYTES:
            _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
        root_fd = self._open_root()
        temporary = secrets.token_hex(32)
        descriptor = -1
        try:
            record_name = f"{receipt.job_reference_digest}.{receipt.execution_reference_digest}"
            existing = self._read_name(root_fd, record_name)
            if existing is not None:
                if existing != receipt:
                    _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
                return False
            descriptor = os.open(temporary, _FILE_CREATE_FLAGS, _FILE_MODE, dir_fd=root_fd)
            os.fchmod(descriptor, _FILE_MODE)
            view = memoryview(encoded)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    _reject(RecoveryReceiptErrorCode.WRITE_FAILED)
                view = view[written:]
            os.fsync(descriptor)
            info = os.fstat(descriptor)
            if not self._private_file(info):
                _reject(RecoveryReceiptErrorCode.WRITE_FAILED)
            os.close(descriptor)
            descriptor = -1
            os.link(
                temporary,
                record_name,
                src_dir_fd=root_fd,
                dst_dir_fd=root_fd,
                follow_symlinks=False,
            )
            os.unlink(temporary, dir_fd=root_fd)
            os.fsync(root_fd)
            stored = self._read_name(root_fd, record_name)
            if stored != receipt:
                _reject(RecoveryReceiptErrorCode.WRITE_FAILED)
            return True
        except RecoveryReceiptError:
            raise
        except OSError:
            _reject(RecoveryReceiptErrorCode.WRITE_FAILED)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=root_fd)
            except OSError:
                pass
            os.close(root_fd)

    @_content_free
    def read(self, job_id: JobId, execution_reference: str) -> RecoveryReceipt | None:
        if not isinstance(job_id, JobId):
            _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
        try:
            record_name = _record_name(job_id, execution_reference)
        except ValueError:
            _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
        root_fd = self._open_root()
        try:
            receipt = self._read_name(root_fd, record_name)
        finally:
            os.close(root_fd)
        if receipt is None:
            return None
        if receipt.job_reference_digest != workspace_component(
            job_id
        ) or receipt.execution_reference_digest != _execution_digest(job_id, execution_reference):
            _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
        return receipt

    @_content_free
    def proves_recovery(
        self,
        job_id: JobId,
        execution_reference: str,
        *,
        at_utc: datetime,
    ) -> bool:
        at_utc = require_utc(at_utc, field_name="at_utc")
        receipt = self.read(job_id, execution_reference)
        return bool(
            receipt is not None
            and receipt.outcome == "recovery_required"
            and receipt.expires_at_utc > at_utc
            and receipt.worker_group_verified_absent
            and receipt.workspace_verified_absent
        )

    @_content_free
    def proves_job_recovery(self, job: JobRecord, *, at_utc: datetime) -> bool:
        if not isinstance(job, JobRecord):
            _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
        references = tuple(
            operation.operation_id
            for operation in job.operations
            if operation.action == "execution:running:none"
        )
        if len(references) != 1:
            _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
        return self.proves_recovery(
            JobId.from_urlsafe(job.job_id),
            references[0],
            at_utc=at_utc,
        )

    @_content_free
    def proves_acceptance(
        self,
        job_id: JobId,
        execution_reference: str,
        *,
        terminal_version: int,
        terminal_outcome: TerminalOutcome,
        artifact_sha256: str | None,
        artifact_byte_size: int | None,
        at_utc: datetime,
    ) -> bool:
        at_utc = require_utc(at_utc, field_name="at_utc")
        receipt = self.read(job_id, execution_reference)
        return bool(
            receipt is not None
            and receipt.outcome == "accepted"
            and receipt.expires_at_utc > at_utc
            and receipt.worker_group_verified_absent
            and not receipt.workspace_verified_absent
            and receipt.terminal_version == terminal_version
            and receipt.terminal_outcome is terminal_outcome
            and receipt.artifact_sha256 == artifact_sha256
            and receipt.artifact_byte_size == artifact_byte_size
        )

    @_content_free
    def scientific_disposition(
        self,
        job: JobRecord,
        *,
        at_utc: datetime,
    ) -> ScientificRecoveryDisposition:
        """Classify signed guardian evidence for one pending scientific success."""

        at_utc = require_utc(at_utc, field_name="at_utc")
        if (
            not isinstance(job, JobRecord)
            or job.execution.state is not ExecutionState.TERMINAL
            or job.outcome is None
            or job.outcome.kind is not TerminalOutcome.SUCCEEDED
            or job.scientific_result is None
            or job.scientific_result_confirmed
            or job.artifacts.result.state is not CleanupState.PRESENT
        ):
            _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
        references = tuple(
            operation.operation_id
            for operation in job.operations
            if operation.action == "execution:running:none"
        )
        terminal_version = terminal_operation_version(job)
        if len(references) != 1 or terminal_version is None:
            _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
        receipt = self.read(JobId.from_urlsafe(job.job_id), references[0])
        if receipt is None or receipt.expires_at_utc <= at_utc:
            return ScientificRecoveryDisposition.UNRESOLVED
        if receipt.outcome == "recovery_required":
            if receipt.worker_group_verified_absent and receipt.workspace_verified_absent:
                return ScientificRecoveryDisposition.RECOVERY_REQUIRED
            return ScientificRecoveryDisposition.UNRESOLVED
        result = job.scientific_result
        if (
            receipt.worker_group_verified_absent
            and not receipt.workspace_verified_absent
            and receipt.terminal_version == terminal_version
            and receipt.terminal_outcome is TerminalOutcome.SUCCEEDED
            and receipt.artifact_sha256 == result.sha256
            and receipt.artifact_byte_size == result.byte_size
        ):
            return ScientificRecoveryDisposition.ACCEPTED
        return ScientificRecoveryDisposition.UNRESOLVED

    @_content_free
    def purge_expired(self, *, at_utc: datetime) -> int:
        at_utc = require_utc(at_utc, field_name="at_utc")
        root_fd = self._open_root()
        deleted = 0
        try:
            for name in os.listdir(root_fd):
                if _RECORD_NAME.fullmatch(name) is None:
                    _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
                receipt = self._read_name(root_fd, name)
                if receipt is None:
                    continue
                if receipt.expires_at_utc <= at_utc:
                    info = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
                    if not self._private_file(info):
                        _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
                    os.unlink(name, dir_fd=root_fd)
                    deleted += 1
            os.fsync(root_fd)
            return deleted
        finally:
            os.close(root_fd)

    def signing_secret_for_guardian(self) -> bytes:
        """Return a copy for transfer through a private inherited pipe only."""

        return bytes(self._signing_secret)

    def _open_root(self) -> int:
        try:
            descriptor = os.open(self.root, _DIRECTORY_FLAGS)
            info = os.fstat(descriptor)
        except OSError:
            _reject(RecoveryReceiptErrorCode.INVALID_ROOT)
        if (
            not stat.S_ISDIR(info.st_mode)
            or stat.S_IMODE(info.st_mode) != _DIRECTORY_MODE
            or info.st_uid != os.getuid()
            or (info.st_dev, info.st_ino) != self._root_identity
        ):
            os.close(descriptor)
            _reject(RecoveryReceiptErrorCode.INVALID_ROOT)
        return descriptor

    def _read_name(self, root_fd: int, name: str) -> RecoveryReceipt | None:
        try:
            descriptor = os.open(name, _FILE_READ_FLAGS, dir_fd=root_fd)
        except FileNotFoundError:
            return None
        except OSError:
            _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
        try:
            info = os.fstat(descriptor)
            if not self._private_file(info) or info.st_size > _MAX_RECEIPT_BYTES:
                _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
            encoded = os.read(descriptor, _MAX_RECEIPT_BYTES + 1)
            if len(encoded) != info.st_size:
                _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
            try:
                receipt = RecoveryReceipt.model_validate_json(encoded)
            except (ValidationError, ValueError):
                _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
            if not self._valid_signature(receipt):
                _reject(RecoveryReceiptErrorCode.INVALID_RECORD)
            return receipt
        finally:
            os.close(descriptor)

    @staticmethod
    def _private_file(info: os.stat_result) -> bool:
        return (
            stat.S_ISREG(info.st_mode)
            and stat.S_IMODE(info.st_mode) == _FILE_MODE
            and info.st_uid == os.getuid()
            and info.st_nlink == 1
        )

    def _valid_signature(self, receipt: RecoveryReceipt) -> bool:
        expected = hmac.digest(
            self._signing_secret,
            _SIGNATURE_DOMAIN + _unsigned_payload(receipt),
            "sha256",
        )
        return hmac.compare_digest(expected.hex(), receipt.signature)


__all__ = [
    "RecoveryReceipt",
    "RecoveryReceiptError",
    "RecoveryReceiptErrorCode",
    "RecoveryReceiptStore",
    "ScientificRecoveryDisposition",
    "new_acceptance_receipt",
    "new_recovery_receipt",
]
