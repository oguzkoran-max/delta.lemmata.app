"""All-or-nothing materialization of P003-validated payloads into a job workspace."""

from __future__ import annotations

import hashlib
import re
import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from delta_lemmata.ingestion import IntakeReceipt, IntakeRole
from delta_lemmata.job_workspace import (
    WorkspaceArea,
    WorkspaceError,
    WorkspaceLayout,
    WorkspaceManager,
)

FileComponentFactory = Callable[[], str]
_FILE_COMPONENT = re.compile(r"^[0-9a-f]{64}$", flags=re.ASCII)
_MATERIALIZABLE_ROLES = frozenset({IntakeRole.CORPUS_TEXT, IntakeRole.METADATA_CSV})


class StagingErrorCode(StrEnum):
    EMPTY = "JOB_STAGING_EMPTY"
    UNSUPPORTED_ROLE = "JOB_STAGING_UNSUPPORTED_ROLE"
    RECEIPT_MISMATCH = "JOB_STAGING_RECEIPT_MISMATCH"
    INVALID_IDENTIFIER = "JOB_STAGING_INVALID_IDENTIFIER"
    MATERIALIZATION_FAILED = "JOB_STAGING_MATERIALIZATION_FAILED"


class StagingError(RuntimeError):
    """A content-free failure at the validated-payload boundary."""

    def __init__(self, code: StagingErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class ValidatedPayload:
    receipt: IntakeReceipt
    content: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class StagedAsset:
    file_component: str
    role: IntakeRole
    byte_size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class MaterializationReceipt:
    assets: tuple[StagedAsset, ...]
    file_count: int
    byte_count: int


def _reject(code: StagingErrorCode) -> None:
    error = StagingError(code)
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True
    raise error


def _validate_payload(item: ValidatedPayload) -> None:
    receipt = item.receipt
    if receipt.role not in _MATERIALIZABLE_ROLES:
        _reject(StagingErrorCode.UNSUPPORTED_ROLE)
    if (
        not isinstance(item.content, bytes)
        or len(item.content) != receipt.byte_size
        or len(item.content) != receipt.expanded_bytes
        or hashlib.sha256(item.content).hexdigest() != receipt.sha256
    ):
        _reject(StagingErrorCode.RECEIPT_MISMATCH)


def _components(count: int, factory: FileComponentFactory) -> tuple[str, ...]:
    try:
        values = tuple(factory() for _ in range(count))
    except Exception:
        _reject(StagingErrorCode.INVALID_IDENTIFIER)
    if any(
        not isinstance(value, str) or _FILE_COMPONENT.fullmatch(value) is None for value in values
    ):
        _reject(StagingErrorCode.INVALID_IDENTIFIER)
    if len(set(values)) != len(values):
        _reject(StagingErrorCode.INVALID_IDENTIFIER)
    return values


def _materialize_validated_payloads(
    manager: WorkspaceManager,
    layout: WorkspaceLayout,
    payloads: Sequence[ValidatedPayload],
    *,
    component_factory: FileComponentFactory | None = None,
) -> MaterializationReceipt:
    """Write an already admitted validated batch under opaque server file names."""

    if not payloads:
        _reject(StagingErrorCode.EMPTY)
    for item in payloads:
        _validate_payload(item)
    factory = component_factory or (lambda: secrets.token_hex(32))
    components = _components(len(payloads), factory)
    assets = tuple(
        StagedAsset(
            file_component=component,
            role=item.receipt.role,
            byte_size=item.receipt.byte_size,
            sha256=item.receipt.sha256,
        )
        for item, component in zip(payloads, components, strict=True)
    )
    try:
        for item, asset in zip(payloads, assets, strict=True):
            manager.create_file(
                layout,
                WorkspaceArea.INPUT,
                asset.file_component,
                item.content,
            )
    except (WorkspaceError, OSError):
        try:
            manager.cleanup(layout)
        except WorkspaceError:
            pass
        _reject(StagingErrorCode.MATERIALIZATION_FAILED)
    return MaterializationReceipt(
        assets=assets,
        file_count=len(assets),
        byte_count=sum(asset.byte_size for asset in assets),
    )


def materialize_validated_payloads(
    manager: WorkspaceManager,
    layout: WorkspaceLayout,
    payloads: Sequence[ValidatedPayload],
    *,
    component_factory: FileComponentFactory | None = None,
) -> MaterializationReceipt:
    """Write an admitted batch while detaching all private exception context."""

    try:
        return _materialize_validated_payloads(
            manager,
            layout,
            payloads,
            component_factory=component_factory,
        )
    except StagingError as error:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True
        raise


__all__ = [
    "FileComponentFactory",
    "MaterializationReceipt",
    "StagedAsset",
    "StagingError",
    "StagingErrorCode",
    "ValidatedPayload",
    "materialize_validated_payloads",
]
