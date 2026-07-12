from __future__ import annotations

import base64
import dataclasses
import hmac
import re
from collections.abc import Callable

import pytest

from delta_lemmata.session_identity import (
    IDENTIFIER_BYTES,
    JobId,
    SessionCapability,
    SessionIdentityError,
    SessionIdentityErrorCode,
    owner_digest,
    support_reference,
    verify_owner_digest,
    workspace_component,
)

SECRET = b"s" * 32


def _fixed_entropy(value: bytes) -> Callable[[int], bytes]:
    def factory(size: int) -> bytes:
        assert size == IDENTIFIER_BYTES
        return value

    return factory


@pytest.mark.parametrize("identity_type", [SessionCapability, JobId])
def test_identity_generation_is_deterministic_injectable_and_immutable(
    identity_type: type[SessionCapability] | type[JobId],
) -> None:
    raw = bytes(range(IDENTIFIER_BYTES))
    identity = identity_type.generate(_fixed_entropy(raw))

    assert identity.to_urlsafe() == "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8"
    assert identity_type.from_urlsafe(identity.to_urlsafe()) == identity
    assert len(identity.to_urlsafe()) == 43
    assert "=" not in identity.to_urlsafe()
    assert identity_type.byte_length == 32
    assert raw.hex() not in repr(identity)
    with pytest.raises(dataclasses.FrozenInstanceError):
        identity._value = b"changed"  # type: ignore[misc]


@pytest.mark.parametrize("identity_type", [SessionCapability, JobId])
def test_default_generation_requests_32_random_bytes(
    identity_type: type[SessionCapability] | type[JobId], monkeypatch: pytest.MonkeyPatch
) -> None:
    requested_sizes: list[int] = []

    def token_bytes(size: int) -> bytes:
        requested_sizes.append(size)
        return b"r" * size

    monkeypatch.setattr("delta_lemmata.session_identity.secrets.token_bytes", token_bytes)
    identity = identity_type.generate()

    assert requested_sizes == [32]
    assert identity == identity_type.from_urlsafe(identity.to_urlsafe())


@pytest.mark.parametrize("identity_type", [SessionCapability, JobId])
@pytest.mark.parametrize(
    "factory",
    [
        lambda _size: b"short",
        lambda _size: b"long" * 9,
        lambda _size: bytearray(32),
        lambda _size: (_ for _ in ()).throw(RuntimeError("sensitive entropy failure")),
    ],
)
def test_generation_rejects_invalid_entropy_without_leaking_details(
    identity_type: type[SessionCapability] | type[JobId], factory: Callable[[int], bytes]
) -> None:
    with pytest.raises(SessionIdentityError) as caught:
        identity_type.generate(factory)

    assert caught.value.code is SessionIdentityErrorCode.INVALID_ENTROPY
    assert str(caught.value) == "SESSION_IDENTITY_INVALID_ENTROPY"
    assert "sensitive" not in str(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


@pytest.mark.parametrize("identity_type", [SessionCapability, JobId])
@pytest.mark.parametrize("raw", [b"short", b"long" * 9, bytearray(32)])
def test_direct_construction_rejects_non_256_bit_values(
    identity_type: type[SessionCapability] | type[JobId], raw: object
) -> None:
    with pytest.raises(SessionIdentityError) as caught:
        identity_type(raw)  # type: ignore[arg-type]

    assert caught.value.code is SessionIdentityErrorCode.INVALID_ENTROPY


@pytest.mark.parametrize("identity_type", [SessionCapability, JobId])
@pytest.mark.parametrize(
    "serialized",
    [
        "",
        "A" * 42,
        "A" * 44,
        "A" * 42 + "=",
        "A" * 42 + "+",
        "A" * 42 + "/",
        "A" * 42 + "!",
        "A" * 42 + "é",
        123,
    ],
)
def test_parser_rejects_padding_bad_lengths_and_non_urlsafe_alphabets(
    identity_type: type[SessionCapability] | type[JobId], serialized: object
) -> None:
    with pytest.raises(SessionIdentityError) as caught:
        identity_type.from_urlsafe(serialized)  # type: ignore[arg-type]

    assert caught.value.code is SessionIdentityErrorCode.INVALID_SERIALIZATION


@pytest.mark.parametrize("identity_type", [SessionCapability, JobId])
def test_parser_rejects_noncanonical_pad_bits(
    identity_type: type[SessionCapability] | type[JobId],
) -> None:
    canonical = identity_type.generate(_fixed_entropy(b"\x00" * 32)).to_urlsafe()
    noncanonical = canonical[:-1] + "B"

    assert base64.b64decode(noncanonical + "=", altchars=b"-_", validate=True) == b"\x00" * 32
    with pytest.raises(SessionIdentityError) as caught:
        identity_type.from_urlsafe(noncanonical)

    assert caught.value.code is SessionIdentityErrorCode.INVALID_SERIALIZATION


def test_owner_digest_is_deterministic_keyed_and_domain_separated() -> None:
    capability = SessionCapability.generate(_fixed_entropy(b"c" * 32))
    job_id = JobId.generate(_fixed_entropy(b"j" * 32))
    digest = owner_digest(owner_secret=SECRET, capability=capability, job_id=job_id)
    raw_undomained = hmac.digest(SECRET, b"j" * 32 + b"c" * 32, "sha256")

    assert len(digest) == 32
    assert digest == owner_digest(owner_secret=SECRET, capability=capability, job_id=job_id)
    assert digest != raw_undomained
    assert capability.to_urlsafe().encode() not in digest
    assert job_id.to_urlsafe().encode() not in digest
    assert SECRET not in digest


def test_owner_verification_rejects_wrong_capability_key_and_job() -> None:
    capability = SessionCapability.generate(_fixed_entropy(b"c" * 32))
    job_id = JobId.generate(_fixed_entropy(b"j" * 32))
    digest = owner_digest(owner_secret=SECRET, capability=capability, job_id=job_id)

    assert verify_owner_digest(
        owner_secret=SECRET,
        capability=capability,
        job_id=job_id,
        expected_digest=digest,
    )
    assert not verify_owner_digest(
        owner_secret=b"k" * 32,
        capability=capability,
        job_id=job_id,
        expected_digest=digest,
    )
    assert not verify_owner_digest(
        owner_secret=SECRET,
        capability=SessionCapability.generate(_fixed_entropy(b"x" * 32)),
        job_id=job_id,
        expected_digest=digest,
    )
    assert not verify_owner_digest(
        owner_secret=SECRET,
        capability=capability,
        job_id=JobId.generate(_fixed_entropy(b"x" * 32)),
        expected_digest=digest,
    )


def test_job_id_possession_alone_cannot_reproduce_owner_proof() -> None:
    job_id = JobId.generate(_fixed_entropy(b"j" * 32))
    first = owner_digest(
        owner_secret=SECRET,
        capability=SessionCapability.generate(_fixed_entropy(b"a" * 32)),
        job_id=job_id,
    )
    second = owner_digest(
        owner_secret=SECRET,
        capability=SessionCapability.generate(_fixed_entropy(b"b" * 32)),
        job_id=job_id,
    )

    assert first != second


@pytest.mark.parametrize("secret", [b"", b"x" * 31, bytearray(32), "x" * 32])
def test_owner_secret_requires_at_least_32_bytes(secret: object) -> None:
    capability = SessionCapability.generate(_fixed_entropy(b"c" * 32))
    job_id = JobId.generate(_fixed_entropy(b"j" * 32))

    with pytest.raises(SessionIdentityError) as caught:
        owner_digest(owner_secret=secret, capability=capability, job_id=job_id)  # type: ignore[arg-type]

    assert caught.value.code is SessionIdentityErrorCode.OWNER_SECRET_TOO_SHORT


@pytest.mark.parametrize(
    ("capability", "job_id"),
    [(b"c" * 32, JobId(b"j" * 32)), (SessionCapability(b"c" * 32), b"j" * 32)],
)
def test_owner_digest_rejects_identity_type_confusion(capability: object, job_id: object) -> None:
    with pytest.raises(SessionIdentityError) as caught:
        owner_digest(
            owner_secret=SECRET,
            capability=capability,  # type: ignore[arg-type]
            job_id=job_id,  # type: ignore[arg-type]
        )

    assert caught.value.code is SessionIdentityErrorCode.INVALID_ENTROPY


@pytest.mark.parametrize("digest", [b"", b"x" * 31, b"x" * 33, bytearray(32), "x" * 32])
def test_digest_consumers_reject_invalid_digest_without_content(digest: object) -> None:
    capability = SessionCapability.generate(_fixed_entropy(b"c" * 32))
    job_id = JobId.generate(_fixed_entropy(b"j" * 32))

    with pytest.raises(SessionIdentityError) as verify_error:
        verify_owner_digest(
            owner_secret=SECRET,
            capability=capability,
            job_id=job_id,
            expected_digest=digest,  # type: ignore[arg-type]
        )
    with pytest.raises(SessionIdentityError) as reference_error:
        support_reference(digest)  # type: ignore[arg-type]

    assert verify_error.value.code is SessionIdentityErrorCode.INVALID_OWNER_DIGEST
    assert reference_error.value.code is SessionIdentityErrorCode.INVALID_OWNER_DIGEST
    assert str(verify_error.value) == "SESSION_IDENTITY_INVALID_OWNER_DIGEST"


def test_support_reference_is_stable_short_non_reversible_and_secret_free() -> None:
    capability = SessionCapability.generate(_fixed_entropy(b"c" * 32))
    job_id = JobId.generate(_fixed_entropy(b"j" * 32))
    digest = owner_digest(owner_secret=SECRET, capability=capability, job_id=job_id)
    reference = support_reference(digest)

    assert reference == support_reference(digest)
    assert re.fullmatch(r"SUP-[A-Za-z0-9_-]{12}", reference)
    assert len(reference) == 16
    assert digest.hex() not in reference
    assert capability.to_urlsafe() not in reference
    assert job_id.to_urlsafe() not in reference
    assert SECRET.decode() not in reference
    assert support_reference(bytes([digest[0] ^ 1]) + digest[1:]) != reference


def test_workspace_component_is_stable_fixed_width_and_not_the_public_identifier() -> None:
    job_id = JobId.generate(_fixed_entropy(b"j" * 32))
    component = workspace_component(job_id)

    assert component == workspace_component(job_id)
    assert re.fullmatch(r"[0-9a-f]{64}", component)
    assert component != job_id.to_urlsafe()
    assert component != (b"j" * 32).hex()
    assert workspace_component(JobId.generate(_fixed_entropy(b"x" * 32))) != component


def test_workspace_component_rejects_identity_type_confusion() -> None:
    with pytest.raises(SessionIdentityError) as caught:
        workspace_component(SessionCapability(b"c" * 32))  # type: ignore[arg-type]

    assert caught.value.code is SessionIdentityErrorCode.INVALID_ENTROPY
