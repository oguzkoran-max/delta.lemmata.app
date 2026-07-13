from __future__ import annotations

import os
import stat
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

import delta_lemmata.recovery_receipt as recovery
from delta_lemmata.job_events import MAX_EVENT_TTL_SECONDS
from delta_lemmata.recovery_receipt import (
    RecoveryReceipt,
    RecoveryReceiptError,
    RecoveryReceiptErrorCode,
    RecoveryReceiptStore,
    new_recovery_receipt,
)
from delta_lemmata.session_identity import JobId, SessionCapability

NOW = datetime(2026, 7, 13, 18, tzinfo=UTC)
SECRET = b"guardian-receipt-secret-v1-32bytes"
EXECUTION_REF = "op_" + "1" * 64


def job_id(number: int = 1) -> JobId:
    return JobId.generate(lambda size: bytes([number]) * size)


def root(tmp_path: Path) -> Path:
    target = tmp_path / "receipts"
    target.mkdir(mode=0o700, parents=True)
    return target


def receipt(
    *,
    identifier: JobId | None = None,
    execution_reference: str = EXECUTION_REF,
    verified: bool = True,
    file_count: int = 2,
    byte_count: int = 32,
) -> RecoveryReceipt:
    return new_recovery_receipt(
        job_id=identifier or job_id(),
        execution_reference=execution_reference,
        occurred_at_utc=NOW,
        workspace_verified_absent=verified,
        file_count=file_count if verified else 0,
        byte_count=byte_count if verified else 0,
        signing_secret=SECRET,
        event_ttl_seconds=MAX_EVENT_TTL_SECONDS,
    )


def expect_error(code: RecoveryReceiptErrorCode, action: object) -> RecoveryReceiptError:
    with pytest.raises(RecoveryReceiptError) as captured:
        assert callable(action)
        action()
    error = captured.value
    assert error.code is code
    assert str(error) == code.value
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert "/" not in str(error)
    return error


def test_receipt_is_signed_bounded_immutable_and_content_free() -> None:
    item = receipt()
    encoded = item.model_dump_json().casefold()
    assert item.worker_group_verified_absent is True
    assert item.outcome == "recovery_required"
    assert item.expires_at_utc == NOW + timedelta(days=7)
    assert len(item.signature) == 64
    assert job_id().to_urlsafe() not in encoded
    assert all(
        forbidden not in encoded
        for forbidden in (
            "filename",
            "metadata",
            "absolute_path",
            "stdout",
            "stderr",
            "traceback",
            "corpus",
            "pid",
            "pgid",
        )
    )
    with pytest.raises(ValidationError):
        item.file_count = 3


@pytest.mark.parametrize(
    "payload",
    [
        {"worker_group_verified_absent": False},
        {"workspace_verified_absent": False, "file_count": 1},
        {"workspace_verified_absent": False, "byte_count": 1},
        {"expires_at_utc": NOW},
        {"expires_at_utc": NOW + timedelta(days=7, seconds=1)},
        {"occurred_at_utc": NOW.replace(tzinfo=None)},
        {"signature": "short"},
        {"payload": "forbidden"},
    ],
)
def test_receipt_model_rejects_unbounded_or_payload_bearing_records(
    payload: dict[str, object],
) -> None:
    data = receipt().model_dump(mode="python")
    data.update(payload)
    with pytest.raises(ValidationError):
        RecoveryReceipt.model_validate(data)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"job_id": cast(Any, SessionCapability.generate())},
        {"execution_reference": "bad"},
        {"signing_secret": b"short"},
        {"event_ttl_seconds": 0},
        {"event_ttl_seconds": MAX_EVENT_TTL_SECONDS + 1},
    ],
)
def test_factory_rejects_invalid_inputs(kwargs: dict[str, object]) -> None:
    arguments: dict[str, object] = {
        "job_id": job_id(),
        "execution_reference": EXECUTION_REF,
        "occurred_at_utc": NOW,
        "workspace_verified_absent": True,
        "file_count": 0,
        "byte_count": 0,
        "signing_secret": SECRET,
        "event_ttl_seconds": 1,
    }
    arguments.update(kwargs)
    with pytest.raises(ValueError, match="invalid recovery receipt inputs"):
        new_recovery_receipt(**arguments)  # type: ignore[arg-type]

    arguments["job_id"] = job_id()
    arguments["execution_reference"] = EXECUTION_REF
    arguments["signing_secret"] = SECRET
    arguments["event_ttl_seconds"] = 1
    arguments["occurred_at_utc"] = NOW.astimezone(timezone(timedelta(hours=3)))
    with pytest.raises(ValueError, match="occurred_at_utc"):
        new_recovery_receipt(**arguments)  # type: ignore[arg-type]


def test_store_round_trip_proof_idempotency_and_expiry_purge(tmp_path: Path) -> None:
    receipt_root = root(tmp_path)
    store = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    item = receipt()
    assert store.signing_secret_for_guardian() == SECRET
    assert store.read(job_id(), EXECUTION_REF) is None
    assert store.write(item) is True
    assert store.write(item) is False
    assert store.read(job_id(), EXECUTION_REF) == item
    assert store.read(job_id(2), EXECUTION_REF) is None
    assert store.proves_recovery(
        job_id(), EXECUTION_REF, at_utc=item.expires_at_utc - timedelta(microseconds=1)
    )
    assert not store.proves_recovery(job_id(), EXECUTION_REF, at_utc=item.expires_at_utc)
    assert stat.S_IMODE(next(receipt_root.iterdir()).stat().st_mode) == 0o600
    assert store.purge_expired(at_utc=item.expires_at_utc - timedelta(microseconds=1)) == 0
    assert store.purge_expired(at_utc=item.expires_at_utc) == 1
    assert store.read(job_id(), EXECUTION_REF) is None


def test_unverified_workspace_never_proves_recovery(tmp_path: Path) -> None:
    store = RecoveryReceiptStore(root(tmp_path), signing_secret=SECRET)
    item = receipt(verified=False)
    assert store.write(item)
    assert not store.proves_recovery(job_id(), EXECUTION_REF, at_utc=NOW)


def test_receipt_is_bound_to_one_execution_reference(tmp_path: Path) -> None:
    store = RecoveryReceiptStore(root(tmp_path), signing_secret=SECRET)
    second_reference = "op_" + "2" * 64
    first = receipt()
    second = receipt(execution_reference=second_reference)
    assert first.execution_reference_digest != second.execution_reference_digest
    assert store.write(first)
    assert store.proves_recovery(job_id(), EXECUTION_REF, at_utc=NOW)
    assert not store.proves_recovery(job_id(), second_reference, at_utc=NOW)
    assert store.write(second)
    assert store.proves_recovery(job_id(), second_reference, at_utc=NOW)


def test_store_rejects_wrong_signature_conflict_and_tampering(tmp_path: Path) -> None:
    receipt_root = root(tmp_path)
    store = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    item = receipt()
    forged = item.model_copy(update={"signature": "f" * 64})
    expect_error(RecoveryReceiptErrorCode.INVALID_RECORD, lambda: store.write(forged))
    assert store.write(item)

    conflicting = receipt(file_count=3)
    expect_error(RecoveryReceiptErrorCode.INVALID_RECORD, lambda: store.write(conflicting))
    target = next(receipt_root.iterdir())
    encoded = target.read_bytes().replace(b'"file_count":2', b'"file_count":3')
    target.write_bytes(encoded)
    os.chmod(target, 0o600)
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: store.read(job_id(), EXECUTION_REF),
    )


def test_store_rejects_unsafe_root_and_entries(tmp_path: Path) -> None:
    receipt_root = root(tmp_path)
    expect_error(
        RecoveryReceiptErrorCode.INVALID_CONFIGURATION,
        lambda: RecoveryReceiptStore(Path("relative"), signing_secret=SECRET),
    )
    expect_error(
        RecoveryReceiptErrorCode.INVALID_CONFIGURATION,
        lambda: RecoveryReceiptStore(receipt_root, signing_secret=b"short"),
    )
    missing = tmp_path / "missing"
    expect_error(
        RecoveryReceiptErrorCode.INVALID_ROOT,
        lambda: RecoveryReceiptStore(missing, signing_secret=SECRET),
    )
    os.chmod(receipt_root, 0o755)
    expect_error(
        RecoveryReceiptErrorCode.INVALID_ROOT,
        lambda: RecoveryReceiptStore(receipt_root, signing_secret=SECRET),
    )
    os.chmod(receipt_root, 0o700)
    link = tmp_path / "link"
    link.symlink_to(receipt_root, target_is_directory=True)
    expect_error(
        RecoveryReceiptErrorCode.INVALID_ROOT,
        lambda: RecoveryReceiptStore(link, signing_secret=SECRET),
    )

    store = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    unknown = receipt_root / "unexpected"
    unknown.write_text("x", encoding="utf-8")
    os.chmod(unknown, 0o600)
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: store.purge_expired(at_utc=NOW),
    )


def test_store_rechecks_root_identity_and_rejects_linked_or_oversize_record(
    tmp_path: Path,
) -> None:
    receipt_root = root(tmp_path)
    store = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    item = receipt()
    assert store.write(item)
    target = next(receipt_root.iterdir())
    external = tmp_path / "external"
    external.write_bytes(target.read_bytes())
    os.chmod(external, 0o600)
    target.unlink()
    os.link(external, target)
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: store.read(job_id(), EXECUTION_REF),
    )
    target.unlink()
    external.unlink()

    target.write_bytes(b"x" * (recovery._MAX_RECEIPT_BYTES + 1))
    os.chmod(target, 0o600)
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: store.read(job_id(), EXECUTION_REF),
    )
    target.unlink()

    moved = tmp_path / "moved"
    receipt_root.rename(moved)
    receipt_root.mkdir(mode=0o700)
    expect_error(
        RecoveryReceiptErrorCode.INVALID_ROOT,
        lambda: store.read(job_id(), EXECUTION_REF),
    )


def test_store_write_failures_are_content_free_and_remove_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt_root = root(tmp_path)
    store = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    item = receipt()
    real_write = os.write

    monkeypatch.setattr(os, "write", lambda _fd, _view: 0)
    expect_error(RecoveryReceiptErrorCode.WRITE_FAILED, lambda: store.write(item))
    assert not tuple(receipt_root.iterdir())
    monkeypatch.setattr(os, "write", real_write)

    monkeypatch.setattr(os, "link", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    expect_error(RecoveryReceiptErrorCode.WRITE_FAILED, lambda: store.write(item))
    assert not tuple(receipt_root.iterdir())


def test_unsigned_payload_rejects_non_datetime_values() -> None:
    with pytest.raises(ValueError):
        recovery._unsigned_payload(
            {
                "occurred_at_utc": "not-a-datetime",
                "expires_at_utc": NOW,
                "signature": "f" * 64,
            }
        )
    with pytest.raises(ValueError, match="execution reference"):
        recovery._execution_digest(job_id(), "bad")


def test_store_maps_unexpected_os_error_and_rejects_invalid_job_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = RecoveryReceiptStore(root(tmp_path), signing_secret=SECRET)
    monkeypatch.setattr(store, "_open_root", lambda: (_ for _ in ()).throw(OSError()))
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: store.read(job_id(), EXECUTION_REF),
    )
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: store.read(cast(Any, SessionCapability.generate()), EXECUTION_REF),
    )
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: store.read(job_id(), "bad"),
    )


def test_store_rejects_encoded_receipt_over_local_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = RecoveryReceiptStore(root(tmp_path), signing_secret=SECRET)
    monkeypatch.setattr(recovery, "_MAX_RECEIPT_BYTES", 1)
    expect_error(RecoveryReceiptErrorCode.INVALID_RECORD, lambda: store.write(receipt()))


def test_store_rejects_private_file_and_final_readback_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unsafe_root = root(tmp_path / "unsafe")
    unsafe_store = RecoveryReceiptStore(unsafe_root, signing_secret=SECRET)
    monkeypatch.setattr(unsafe_store, "_private_file", lambda _info: False)
    expect_error(RecoveryReceiptErrorCode.WRITE_FAILED, lambda: unsafe_store.write(receipt()))

    mismatch_root = root(tmp_path / "mismatch")
    mismatch_store = RecoveryReceiptStore(mismatch_root, signing_secret=SECRET)
    reads = iter((None, receipt(identifier=job_id(2))))
    monkeypatch.setattr(mismatch_store, "_read_name", lambda _root_fd, _name: next(reads))
    expect_error(RecoveryReceiptErrorCode.WRITE_FAILED, lambda: mismatch_store.write(receipt()))


def test_read_rejects_digest_mismatch_from_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = RecoveryReceiptStore(root(tmp_path), signing_secret=SECRET)
    monkeypatch.setattr(store, "_read_name", lambda _root_fd, _name: receipt(identifier=job_id(2)))
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: store.read(job_id(), EXECUTION_REF),
    )


def test_purge_handles_disappeared_record_and_rejects_unsafe_expired_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disappeared_root = root(tmp_path / "disappeared")
    disappeared_store = RecoveryReceiptStore(disappeared_root, signing_secret=SECRET)
    (disappeared_root / ("a" * 64 + "." + "b" * 64)).write_bytes(b"")
    monkeypatch.setattr(disappeared_store, "_read_name", lambda _root_fd, _name: None)
    assert disappeared_store.purge_expired(at_utc=NOW) == 0

    unsafe_root = root(tmp_path / "expired")
    unsafe_store = RecoveryReceiptStore(unsafe_root, signing_secret=SECRET)
    (unsafe_root / ("b" * 64 + "." + "c" * 64)).write_bytes(b"")
    expired = receipt().model_copy(update={"expires_at_utc": NOW})
    monkeypatch.setattr(unsafe_store, "_read_name", lambda _root_fd, _name: expired)
    monkeypatch.setattr(unsafe_store, "_private_file", lambda _info: False)
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: unsafe_store.purge_expired(at_utc=NOW),
    )


def test_store_rejects_root_open_and_record_open_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt_root = root(tmp_path)
    store = RecoveryReceiptStore(receipt_root, signing_secret=SECRET)
    real_open = os.open

    monkeypatch.setattr(os, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    with pytest.raises(RecoveryReceiptError) as captured:
        store._open_root()
    assert captured.value.code is RecoveryReceiptErrorCode.INVALID_ROOT

    def fail_record_open(path: object, *args: object, **kwargs: object) -> int:
        if isinstance(path, str):
            raise PermissionError
        return real_open(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "open", fail_record_open)
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: store.read(job_id(), EXECUTION_REF),
    )


def test_store_rejects_short_read_and_invalid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    short_root = root(tmp_path / "short")
    short_store = RecoveryReceiptStore(short_root, signing_secret=SECRET)
    assert short_store.write(receipt())
    real_read = os.read
    monkeypatch.setattr(os, "read", lambda _descriptor, _size: b"")
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: short_store.read(job_id(), EXECUTION_REF),
    )
    monkeypatch.setattr(os, "read", real_read)

    invalid_root = root(tmp_path / "invalid")
    invalid_store = RecoveryReceiptStore(invalid_root, signing_secret=SECRET)
    target = invalid_root / recovery._record_name(job_id(), EXECUTION_REF)
    target.write_bytes(b"not-json")
    os.chmod(target, 0o600)
    expect_error(
        RecoveryReceiptErrorCode.INVALID_RECORD,
        lambda: invalid_store.read(job_id(), EXECUTION_REF),
    )
