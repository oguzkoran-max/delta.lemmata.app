"""Opaque session capabilities and job identifiers for server-side ownership checks."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar, Self

IDENTIFIER_BYTES = 32
OWNER_DIGEST_BYTES = hashlib.sha256().digest_size
MINIMUM_OWNER_SECRET_BYTES = 32

EntropyFactory = Callable[[int], bytes]

_ENCODED_IDENTIFIER_LENGTH = 43
_CANONICAL_BASE64URL = re.compile(r"^[A-Za-z0-9_-]{43}$", flags=re.ASCII)
_CAPABILITY_DIGEST_DOMAIN = b"delta-lemmata\x00session-owner-digest\x00v1\x00"
_WORKSPACE_COMPONENT_DOMAIN = b"delta-lemmata\x00workspace-component\x00v1\x00"
_SUPPORT_REFERENCE_DOMAIN = b"delta-lemmata\x00support-reference\x00v1\x00"
_SUPPORT_REFERENCE_BYTES = 9


class SessionIdentityErrorCode(StrEnum):
    """Stable content-free codes for identity boundary failures."""

    INVALID_ENTROPY = "SESSION_IDENTITY_INVALID_ENTROPY"
    INVALID_SERIALIZATION = "SESSION_IDENTITY_INVALID_SERIALIZATION"
    OWNER_SECRET_TOO_SHORT = "SESSION_IDENTITY_OWNER_SECRET_TOO_SHORT"
    INVALID_OWNER_DIGEST = "SESSION_IDENTITY_INVALID_OWNER_DIGEST"


class SessionIdentityError(ValueError):
    """An identity failure that never includes capability, job, or secret content."""

    def __init__(self, code: SessionIdentityErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


def _generate_entropy(entropy_factory: EntropyFactory) -> bytes:
    try:
        value = entropy_factory(IDENTIFIER_BYTES)
    except Exception:
        value = None
    if not isinstance(value, bytes) or len(value) != IDENTIFIER_BYTES:
        raise SessionIdentityError(SessionIdentityErrorCode.INVALID_ENTROPY)
    return value


def _serialize(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _deserialize(serialized: str) -> bytes:
    if (
        not isinstance(serialized, str)
        or len(serialized) != _ENCODED_IDENTIFIER_LENGTH
        or _CANONICAL_BASE64URL.fullmatch(serialized) is None
    ):
        raise SessionIdentityError(SessionIdentityErrorCode.INVALID_SERIALIZATION)
    value = base64.b64decode(serialized + "=", altchars=b"-_", validate=True)
    if _serialize(value) != serialized:
        raise SessionIdentityError(SessionIdentityErrorCode.INVALID_SERIALIZATION)
    return value


@dataclass(frozen=True, slots=True)
class SessionCapability:
    """A server-generated 256-bit bearer capability for one session."""

    _value: bytes = field(repr=False)
    byte_length: ClassVar[int] = IDENTIFIER_BYTES

    def __post_init__(self) -> None:
        if not isinstance(self._value, bytes) or len(self._value) != IDENTIFIER_BYTES:
            raise SessionIdentityError(SessionIdentityErrorCode.INVALID_ENTROPY)

    @classmethod
    def generate(cls, entropy_factory: EntropyFactory | None = None) -> Self:
        """Generate a capability from exactly 256 bits of server-side entropy."""

        factory = secrets.token_bytes if entropy_factory is None else entropy_factory
        return cls(_generate_entropy(factory))

    @classmethod
    def from_urlsafe(cls, serialized: str) -> Self:
        """Parse only the canonical unpadded Base64URL representation."""

        return cls(_deserialize(serialized))

    def to_urlsafe(self) -> str:
        """Return the canonical unpadded Base64URL representation."""

        return _serialize(self._value)


@dataclass(frozen=True, slots=True)
class JobId:
    """A server-generated 256-bit public locator that grants no authority."""

    _value: bytes = field(repr=False)
    byte_length: ClassVar[int] = IDENTIFIER_BYTES

    def __post_init__(self) -> None:
        if not isinstance(self._value, bytes) or len(self._value) != IDENTIFIER_BYTES:
            raise SessionIdentityError(SessionIdentityErrorCode.INVALID_ENTROPY)

    @classmethod
    def generate(cls, entropy_factory: EntropyFactory | None = None) -> Self:
        """Generate a job identifier from exactly 256 bits of server-side entropy."""

        factory = secrets.token_bytes if entropy_factory is None else entropy_factory
        return cls(_generate_entropy(factory))

    @classmethod
    def from_urlsafe(cls, serialized: str) -> Self:
        """Parse only the canonical unpadded Base64URL representation."""

        return cls(_deserialize(serialized))

    def to_urlsafe(self) -> str:
        """Return the canonical unpadded Base64URL representation."""

        return _serialize(self._value)


def owner_digest(
    *,
    owner_secret: bytes,
    capability: SessionCapability,
    job_id: JobId,
) -> bytes:
    """Bind a job to its session capability with a domain-separated keyed digest."""

    if not isinstance(owner_secret, bytes) or len(owner_secret) < MINIMUM_OWNER_SECRET_BYTES:
        raise SessionIdentityError(SessionIdentityErrorCode.OWNER_SECRET_TOO_SHORT)
    if not isinstance(capability, SessionCapability) or not isinstance(job_id, JobId):
        raise SessionIdentityError(SessionIdentityErrorCode.INVALID_ENTROPY)
    message = _CAPABILITY_DIGEST_DOMAIN + job_id._value + capability._value
    return hmac.digest(owner_secret, message, "sha256")


def verify_owner_digest(
    *,
    owner_secret: bytes,
    capability: SessionCapability,
    job_id: JobId,
    expected_digest: bytes,
) -> bool:
    """Verify ownership without treating the public job identifier as authority."""

    if not isinstance(expected_digest, bytes) or len(expected_digest) != OWNER_DIGEST_BYTES:
        raise SessionIdentityError(SessionIdentityErrorCode.INVALID_OWNER_DIGEST)
    calculated_digest = owner_digest(
        owner_secret=owner_secret,
        capability=capability,
        job_id=job_id,
    )
    return hmac.compare_digest(calculated_digest, expected_digest)


def workspace_component(job_id: JobId) -> str:
    """Derive a non-secret fixed-width path component from a public job id."""

    if not isinstance(job_id, JobId):
        raise SessionIdentityError(SessionIdentityErrorCode.INVALID_ENTROPY)
    return hashlib.sha256(_WORKSPACE_COMPONENT_DOMAIN + job_id._value).hexdigest()


def support_reference(digest: bytes) -> str:
    """Derive a short non-secret reference that cannot be used as owner proof."""

    if not isinstance(digest, bytes) or len(digest) != OWNER_DIGEST_BYTES:
        raise SessionIdentityError(SessionIdentityErrorCode.INVALID_OWNER_DIGEST)
    reference = hashlib.sha256(_SUPPORT_REFERENCE_DOMAIN + digest).digest()
    encoded = base64.urlsafe_b64encode(reference[:_SUPPORT_REFERENCE_BYTES])
    return f"SUP-{encoded.rstrip(b'=').decode('ascii')}"


__all__ = [
    "IDENTIFIER_BYTES",
    "MINIMUM_OWNER_SECRET_BYTES",
    "OWNER_DIGEST_BYTES",
    "EntropyFactory",
    "JobId",
    "SessionCapability",
    "SessionIdentityError",
    "SessionIdentityErrorCode",
    "owner_digest",
    "support_reference",
    "verify_owner_digest",
    "workspace_component",
]
