from __future__ import annotations

import hashlib
import stat
from collections.abc import Callable
from functools import partial
from pathlib import Path

import pytest

from delta_lemmata.ingestion import ArchiveMemberReceipt, IntakeReceipt, IntakeRole
from delta_lemmata.job_staging import (
    StagingError,
    StagingErrorCode,
    ValidatedPayload,
    materialize_validated_payloads,
)
from delta_lemmata.job_workspace import (
    WorkspaceError,
    WorkspaceErrorCode,
    WorkspaceLayout,
    WorkspaceManager,
)

OWNER = "1" * 64
JOB = "2" * 64


def receipt(role: IntakeRole, content: bytes, number: int) -> IntakeReceipt:
    extension = {
        IntakeRole.CORPUS_TEXT: ".txt",
        IntakeRole.CORPUS_ARCHIVE: ".zip",
        IntakeRole.METADATA_CSV: ".csv",
    }[role]
    archive = role is IntakeRole.CORPUS_ARCHIVE
    members = (
        ArchiveMemberReceipt(
            display_label="archive-member.txt",
            byte_size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            line_count=1,
            token_count=1,
            limit_profile="ingestion-limits-v1",
        ),
    )
    return IntakeReceipt(
        asset_id="asset_" + f"{number:032x}",
        role=role,
        display_label=f"private-label-{number}{extension}",
        storage_name="asset_" + f"{number:032x}" + extension,
        byte_size=len(content),
        expanded_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        line_count=1,
        token_count=1,
        row_count=1 if role is IntakeRole.METADATA_CSV else None,
        column_count=2 if role is IntakeRole.METADATA_CSV else None,
        member_count=1 if archive else None,
        archive_members=members if archive else (),
        limit_profile="ingestion-limits-v1",
    )


@pytest.fixture
def workspace(tmp_path: Path) -> tuple[WorkspaceManager, WorkspaceLayout]:
    root = tmp_path / "jobs"
    root.mkdir(mode=0o700)
    manager = WorkspaceManager(root)
    return manager, manager.create(OWNER, JOB)


def assert_code(code: StagingErrorCode, action: Callable[[], object]) -> None:
    with pytest.raises(StagingError) as caught:
        action()
    assert caught.value.code is code
    assert str(caught.value) == code.value
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None


def test_materializes_validated_batch_under_opaque_private_names(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
) -> None:
    manager, layout = workspace
    text = b"first validated text"
    metadata = b"asset_id,group\na,b\n"
    payloads = (
        ValidatedPayload(receipt(IntakeRole.CORPUS_TEXT, text, 1), text),
        ValidatedPayload(receipt(IntakeRole.METADATA_CSV, metadata, 2), metadata),
    )
    identifiers = iter(("a" * 64, "b" * 64))

    result = materialize_validated_payloads(
        manager,
        layout,
        payloads,
        component_factory=lambda: next(identifiers),
    )

    assert result.file_count == 2
    assert result.byte_count == len(text) + len(metadata)
    assert tuple(asset.file_component for asset in result.assets) == ("a" * 64, "b" * 64)
    assert (layout.input / ("a" * 64)).read_bytes() == text
    assert (layout.input / ("b" * 64)).read_bytes() == metadata
    assert stat.S_IMODE((layout.input / ("a" * 64)).stat().st_mode) == 0o600
    names = {path.name for path in layout.input.iterdir()}
    assert all("private-label" not in name for name in names)
    assert all(payload.receipt.storage_name not in names for payload in payloads)


@pytest.mark.parametrize(
    ("role", "content_mutation", "code"),
    [
        (IntakeRole.CORPUS_ARCHIVE, b"valid", StagingErrorCode.UNSUPPORTED_ROLE),
        (IntakeRole.CORPUS_TEXT, b"changed", StagingErrorCode.RECEIPT_MISMATCH),
    ],
)
def test_rejection_writes_nothing(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
    role: IntakeRole,
    content_mutation: bytes,
    code: StagingErrorCode,
) -> None:
    manager, layout = workspace
    original = b"valid"
    item = ValidatedPayload(receipt(role, original, 1), content_mutation)

    assert_code(code, lambda: materialize_validated_payloads(manager, layout, (item,)))
    assert list(layout.input.iterdir()) == []


def test_non_bytes_content_is_rejected_without_leaking(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
) -> None:
    manager, layout = workspace
    content = b"valid"
    item = ValidatedPayload(receipt(IntakeRole.CORPUS_TEXT, content, 1), content)
    object.__setattr__(item, "content", bytearray(content))

    assert_code(
        StagingErrorCode.RECEIPT_MISMATCH,
        lambda: materialize_validated_payloads(manager, layout, (item,)),
    )


def test_empty_and_invalid_identifiers_allocate_no_files(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
) -> None:
    manager, layout = workspace
    assert_code(
        StagingErrorCode.EMPTY,
        lambda: materialize_validated_payloads(manager, layout, ()),
    )
    content = b"valid"
    item = ValidatedPayload(receipt(IntakeRole.CORPUS_TEXT, content, 1), content)

    def fail_factory() -> str:
        raise RuntimeError("private")

    factories: tuple[Callable[[], str], ...] = (
        lambda: "short",
        lambda: "A" * 64,
        fail_factory,
    )
    for factory in factories:
        assert_code(
            StagingErrorCode.INVALID_IDENTIFIER,
            partial(
                materialize_validated_payloads,
                manager,
                layout,
                (item,),
                component_factory=factory,
            ),
        )
    assert list(layout.input.iterdir()) == []


def test_duplicate_identifiers_are_rejected_before_writing(
    workspace: tuple[WorkspaceManager, WorkspaceLayout],
) -> None:
    manager, layout = workspace
    content = b"valid"
    items = tuple(
        ValidatedPayload(receipt(IntakeRole.CORPUS_TEXT, content, number), content)
        for number in (1, 2)
    )
    assert_code(
        StagingErrorCode.INVALID_IDENTIFIER,
        lambda: materialize_validated_payloads(
            manager, layout, items, component_factory=lambda: "a" * 64
        ),
    )
    assert list(layout.input.iterdir()) == []


def test_write_failure_rolls_back_the_complete_workspace(
    workspace: tuple[WorkspaceManager, WorkspaceLayout], monkeypatch: pytest.MonkeyPatch
) -> None:
    manager, layout = workspace
    content = b"valid"
    items = tuple(
        ValidatedPayload(receipt(IntakeRole.CORPUS_TEXT, content, number), content)
        for number in (1, 2)
    )
    original = manager.create_file
    calls = 0

    def fail_second(*args: object, **kwargs: object) -> Path:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise WorkspaceError(WorkspaceErrorCode.WRITE_FAILED)
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(manager, "create_file", fail_second)
    identifiers = iter(("a" * 64, "b" * 64))
    assert_code(
        StagingErrorCode.MATERIALIZATION_FAILED,
        lambda: materialize_validated_payloads(
            manager, layout, items, component_factory=lambda: next(identifiers)
        ),
    )
    assert not layout.job.exists()


def test_cleanup_failure_still_returns_only_content_free_staging_error(
    workspace: tuple[WorkspaceManager, WorkspaceLayout], monkeypatch: pytest.MonkeyPatch
) -> None:
    manager, layout = workspace
    content = b"valid"
    item = ValidatedPayload(receipt(IntakeRole.CORPUS_TEXT, content, 1), content)

    def fail_write(*_args: object, **_kwargs: object) -> Path:
        raise OSError("private path")

    def fail_cleanup(*_args: object, **_kwargs: object) -> object:
        raise WorkspaceError(WorkspaceErrorCode.CLEANUP_FAILED)

    monkeypatch.setattr(manager, "create_file", fail_write)
    monkeypatch.setattr(manager, "cleanup", fail_cleanup)
    assert_code(
        StagingErrorCode.MATERIALIZATION_FAILED,
        lambda: materialize_validated_payloads(
            manager, layout, (item,), component_factory=lambda: "a" * 64
        ),
    )
