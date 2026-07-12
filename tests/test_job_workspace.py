from __future__ import annotations

import os
import stat
import traceback
from dataclasses import replace
from pathlib import Path

import pytest

import delta_lemmata.job_workspace as workspace
from delta_lemmata.job_workspace import (
    CleanupReport,
    WorkspaceArea,
    WorkspaceError,
    WorkspaceErrorCode,
    WorkspaceLayout,
    WorkspaceManager,
)

OWNER = "a" * 64
JOB = "b" * 64
FILE = "c" * 64


def manager(tmp_path: Path) -> WorkspaceManager:
    os.chmod(tmp_path, 0o700)
    return WorkspaceManager(tmp_path)


def expect_code(code: WorkspaceErrorCode, action: object) -> WorkspaceError:
    with pytest.raises(WorkspaceError) as captured:
        assert callable(action)
        action()
    error = captured.value
    assert error.code is code
    assert str(error) == code.value
    assert repr(error) == f"WorkspaceError('{code.value}')"
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert "/" not in str(error)
    return error


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat(follow_symlinks=False).st_mode)


def test_create_verify_write_and_idempotent_cleanup(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)

    assert layout.root == tmp_path.resolve()
    assert layout.owner == layout.root / OWNER
    assert layout.job == layout.owner / JOB
    assert {path.name for path in layout.job.iterdir()} == {area.value for area in WorkspaceArea}
    assert all(mode(path) == 0o700 for path in (layout.owner, layout.job, *layout.job.iterdir()))
    assert layout.area(WorkspaceArea.INPUT) == layout.input

    first = workspaces.create_file(layout, WorkspaceArea.INPUT, FILE, b"private corpus")
    second = workspaces.create_file(layout, WorkspaceArea.CONTROL, "d" * 64, b"")
    assert first.read_bytes() == b"private corpus"
    assert mode(first) == 0o600
    assert mode(second) == 0o600
    workspaces.verify(layout)

    assert workspaces.cleanup(layout) == CleanupReport(2, len(b"private corpus"), False)
    assert not layout.job.exists()
    assert not layout.owner.exists()
    assert workspaces.cleanup(layout) == CleanupReport(0, 0, True)


def test_load_and_selective_area_cleanup_preserve_result_and_layout(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    work_file = "d" * 64
    result_file = "e" * 64
    workspaces.create_file(layout, WorkspaceArea.INPUT, FILE, b"input")
    workspaces.create_file(layout, WorkspaceArea.WORK, work_file, b"work")
    workspaces.create_file(layout, WorkspaceArea.RESULT, result_file, b"result")

    recovered = WorkspaceManager(tmp_path).load(OWNER, JOB)
    first = workspaces.clear_areas(recovered, (WorkspaceArea.INPUT, WorkspaceArea.WORK))

    assert first == CleanupReport(2, len(b"input") + len(b"work"), False)
    assert list(recovered.input.iterdir()) == []
    assert list(recovered.work.iterdir()) == []
    assert (recovered.result / result_file).read_bytes() == b"result"
    workspaces.verify(recovered)
    assert workspaces.clear_areas(
        recovered, (WorkspaceArea.INPUT, WorkspaceArea.WORK)
    ) == CleanupReport(0, 0, True)


def test_load_and_selective_cleanup_fail_closed_on_invalid_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    expect_code(
        WorkspaceErrorCode.INVALID_LAYOUT,
        lambda: workspaces.clear_areas(layout, ()),
    )
    expect_code(
        WorkspaceErrorCode.INVALID_LAYOUT,
        lambda: workspaces.clear_areas(layout, (object(),)),  # type: ignore[arg-type]
    )
    expect_code(
        WorkspaceErrorCode.INVALID_LAYOUT,
        lambda: workspaces.load(OWNER, "f" * 64),
    )
    expect_code(
        WorkspaceErrorCode.INVALID_LAYOUT,
        lambda: workspaces.load("f" * 64, JOB),
    )

    unexpected = layout.job / "unexpected"
    unexpected.mkdir()
    expect_code(
        WorkspaceErrorCode.INVALID_LAYOUT,
        lambda: workspaces.load(OWNER, JOB),
    )
    unexpected.rmdir()

    workspaces.create_file(layout, WorkspaceArea.INPUT, FILE, b"input")
    original_stat = os.stat

    def fail_stat(*args: object, **kwargs: object) -> os.stat_result:
        if kwargs.get("dir_fd") is not None and args[0] == FILE:
            raise OSError("private")
        return original_stat(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "stat", fail_stat)
    expect_code(
        WorkspaceErrorCode.CLEANUP_FAILED,
        lambda: workspaces.clear_areas(layout, (WorkspaceArea.INPUT,)),
    )


def test_load_detaches_os_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspaces = manager(tmp_path)
    workspaces.create(OWNER, JOB)

    def fail_listdir(_descriptor: int) -> list[str]:
        raise OSError("private")

    monkeypatch.setattr(os, "listdir", fail_listdir)
    expect_code(
        WorkspaceErrorCode.INVALID_LAYOUT,
        lambda: workspaces.load(OWNER, JOB),
    )


def test_selective_cleanup_rechecks_identity_and_empty_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    workspaces.create_file(layout, WorkspaceArea.INPUT, FILE, b"input")
    original_preflight = workspaces._preflight

    def tamper_mode(job_fd: int, current_layout: WorkspaceLayout) -> object:
        inventory = original_preflight(job_fd, current_layout)
        os.chmod(layout.input / FILE, 0o644)
        return inventory

    monkeypatch.setattr(workspaces, "_preflight", tamper_mode)
    expect_code(
        WorkspaceErrorCode.CLEANUP_FAILED,
        lambda: workspaces.clear_areas(layout, (WorkspaceArea.INPUT,)),
    )

    os.chmod(layout.input / FILE, 0o600)
    monkeypatch.setattr(workspaces, "_preflight", original_preflight)
    original_unlink = os.unlink

    def replace_after_unlink(name: str, *, dir_fd: int | None = None) -> None:
        original_unlink(name, dir_fd=dir_fd)
        descriptor = os.open(
            "f" * 64,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
            dir_fd=dir_fd,
        )
        os.close(descriptor)

    monkeypatch.setattr(os, "unlink", replace_after_unlink)
    expect_code(
        WorkspaceErrorCode.CLEANUP_FAILED,
        lambda: workspaces.clear_areas(layout, (WorkspaceArea.INPUT,)),
    )


def test_selective_cleanup_detaches_workspace_errors(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    external = tmp_path / "external"
    external.write_bytes(b"canary")
    (layout.input / FILE).symlink_to(external)

    expect_code(
        WorkspaceErrorCode.UNSAFE_ENTRY,
        lambda: workspaces.clear_areas(layout, (WorkspaceArea.INPUT,)),
    )
    assert external.read_bytes() == b"canary"


@pytest.mark.parametrize(
    "component",
    ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64, "../" + "a" * 61, "." * 64],
)
def test_components_are_exact_lowercase_256_bit_hex(tmp_path: Path, component: str) -> None:
    workspaces = manager(tmp_path)
    expect_code(
        WorkspaceErrorCode.INVALID_COMPONENT,
        lambda: workspaces.create(component, JOB),
    )
    assert not tuple(tmp_path.iterdir())


def test_invalid_job_and_file_components_allocate_nothing(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    expect_code(
        WorkspaceErrorCode.INVALID_COMPONENT,
        lambda: workspaces.create(OWNER, "B" * 64),
    )
    expect_code(
        WorkspaceErrorCode.INVALID_COMPONENT,
        lambda: workspaces.create_file(layout, WorkspaceArea.INPUT, "../escape", b"canary"),
    )
    assert not tuple(layout.input.iterdir())


def test_root_must_be_existing_absolute_private_real_directory(tmp_path: Path) -> None:
    original_mode = mode(tmp_path)
    os.chmod(tmp_path, 0o755)
    expect_code(WorkspaceErrorCode.INVALID_ROOT, lambda: WorkspaceManager(tmp_path))
    os.chmod(tmp_path, original_mode)

    missing = tmp_path / "missing"
    expect_code(WorkspaceErrorCode.INVALID_ROOT, lambda: WorkspaceManager(missing))
    expect_code(WorkspaceErrorCode.INVALID_ROOT, lambda: WorkspaceManager(Path("relative")))

    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    expect_code(WorkspaceErrorCode.INVALID_ROOT, lambda: WorkspaceManager(link))


def test_existing_private_owner_can_hold_multiple_jobs(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    first = workspaces.create(OWNER, JOB)
    second = workspaces.create(OWNER, "c" * 64)
    assert first.owner == second.owner
    assert workspaces.cleanup(first).verified_absent
    assert second.owner.exists()
    assert workspaces.cleanup(second).verified_absent
    assert not second.owner.exists()


def test_create_is_exclusive_and_rejects_unsafe_owner(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    expect_code(WorkspaceErrorCode.CREATE_FAILED, lambda: workspaces.create(OWNER, JOB))
    workspaces.cleanup(layout)

    external = tmp_path / "external"
    external.mkdir(mode=0o700)
    (tmp_path / OWNER).symlink_to(external, target_is_directory=True)
    expect_code(WorkspaceErrorCode.CREATE_FAILED, lambda: workspaces.create(OWNER, JOB))
    assert not tuple(external.iterdir())


def test_file_creation_is_exclusive_and_does_not_follow_symlink(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    workspaces.create_file(layout, WorkspaceArea.INPUT, FILE, b"first")
    expect_code(
        WorkspaceErrorCode.WRITE_FAILED,
        lambda: workspaces.create_file(layout, WorkspaceArea.INPUT, FILE, b"second"),
    )
    assert (layout.input / FILE).read_bytes() == b"first"

    canary = tmp_path / "canary"
    canary.write_bytes(b"outside")
    os.chmod(canary, 0o600)
    link_name = "d" * 64
    (layout.input / link_name).symlink_to(canary)
    expect_code(
        WorkspaceErrorCode.WRITE_FAILED,
        lambda: workspaces.create_file(layout, WorkspaceArea.INPUT, link_name, b"changed"),
    )
    assert canary.read_bytes() == b"outside"


def test_verify_rejects_extra_entry_and_tampered_layout_value(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    (layout.job / "extra").mkdir(mode=0o700)
    expect_code(WorkspaceErrorCode.INVALID_LAYOUT, lambda: workspaces.verify(layout))
    (layout.job / "extra").rmdir()

    tampered = replace(layout, input=tmp_path / "outside")
    expect_code(WorkspaceErrorCode.INVALID_LAYOUT, lambda: workspaces.verify(tampered))


def test_area_rename_swap_fails_closed(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    original = layout.input.with_name("saved")
    layout.input.rename(original)
    layout.input.mkdir(mode=0o700)

    expect_code(WorkspaceErrorCode.INVALID_LAYOUT, lambda: workspaces.verify(layout))
    expect_code(
        WorkspaceErrorCode.INVALID_LAYOUT,
        lambda: workspaces.create_file(layout, WorkspaceArea.INPUT, FILE, b"secret"),
    )
    expect_code(WorkspaceErrorCode.CLEANUP_FAILED, lambda: workspaces.cleanup(layout))
    assert original.exists()


def test_job_rename_swap_fails_closed_and_preserves_both_trees(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    moved = layout.job.with_name("d" * 64)
    layout.job.rename(moved)
    replacement = layout.job
    replacement.mkdir(mode=0o700)
    for area in WorkspaceArea:
        (replacement / area.value).mkdir(mode=0o700)

    expect_code(WorkspaceErrorCode.INVALID_LAYOUT, lambda: workspaces.verify(layout))
    expect_code(WorkspaceErrorCode.CLEANUP_FAILED, lambda: workspaces.cleanup(layout))
    assert moved.exists()
    assert replacement.exists()


def test_cleanup_rejects_symlink_without_touching_external_canary(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    canary = tmp_path / "external-canary"
    canary.write_bytes(b"preserve me")
    os.chmod(canary, 0o600)
    (layout.work / FILE).symlink_to(canary)

    error = expect_code(WorkspaceErrorCode.UNSAFE_ENTRY, lambda: workspaces.cleanup(layout))
    assert "preserve me" not in "".join(traceback.format_exception(error))
    assert canary.read_bytes() == b"preserve me"
    assert (layout.work / FILE).is_symlink()


def test_cleanup_rejects_hardlink_without_changing_link_count(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    canary = tmp_path / "external-canary"
    canary.write_bytes(b"preserve me")
    os.chmod(canary, 0o600)
    hardlink = layout.result / FILE
    os.link(canary, hardlink)
    before = canary.stat().st_nlink

    expect_code(WorkspaceErrorCode.UNSAFE_ENTRY, lambda: workspaces.cleanup(layout))
    assert canary.read_bytes() == b"preserve me"
    assert canary.stat().st_nlink == before
    assert hardlink.exists()


def test_cleanup_rejects_nonprivate_file_and_unknown_root_entry(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    unsafe = layout.export / FILE
    unsafe.write_bytes(b"x")
    os.chmod(unsafe, 0o644)
    expect_code(WorkspaceErrorCode.UNSAFE_ENTRY, lambda: workspaces.cleanup(layout))
    assert unsafe.exists()

    unsafe.unlink()
    (layout.job / "unexpected").mkdir(mode=0o700)
    expect_code(WorkspaceErrorCode.CLEANUP_FAILED, lambda: workspaces.cleanup(layout))


def test_root_identity_and_mode_are_rechecked_for_every_operation(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    os.chmod(tmp_path, 0o755)
    expect_code(WorkspaceErrorCode.INVALID_ROOT, lambda: workspaces.verify(layout))
    expect_code(WorkspaceErrorCode.INVALID_ROOT, lambda: workspaces.cleanup(layout))


def test_layout_with_foreign_root_is_rejected_without_external_change(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir(mode=0o700)
    try:
        foreign: WorkspaceLayout = replace(layout, root=outside)
        expect_code(WorkspaceErrorCode.INVALID_LAYOUT, lambda: workspaces.cleanup(foreign))
        assert outside.exists()
    finally:
        outside.rmdir()


def changed_inode(info: os.stat_result) -> os.stat_result:
    values = list(info)
    values[1] += 1
    return os.stat_result(values)


def test_root_rejects_realpath_identity_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    os.chmod(tmp_path, 0o700)
    real_stat = workspace.os.stat

    def mismatched(path: object, *, follow_symlinks: bool = True) -> os.stat_result:
        return changed_inode(real_stat(path, follow_symlinks=follow_symlinks))

    monkeypatch.setattr(workspace.os, "stat", mismatched)
    expect_code(WorkspaceErrorCode.INVALID_ROOT, lambda: WorkspaceManager(tmp_path))


@pytest.mark.parametrize("failed_area", [WorkspaceArea.INPUT.value, WorkspaceArea.RESULT.value])
def test_partial_layout_creation_is_rolled_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_area: str
) -> None:
    workspaces = manager(tmp_path)
    real_mkdir = workspace.os.mkdir

    def fail_one(name: object, mode: int = 0o777, *, dir_fd: int | None = None) -> None:
        if name == failed_area:
            raise OSError
        real_mkdir(name, mode, dir_fd=dir_fd)

    monkeypatch.setattr(workspace.os, "mkdir", fail_one)
    expect_code(WorkspaceErrorCode.CREATE_FAILED, lambda: workspaces.create(OWNER, JOB))
    assert not tuple(tmp_path.iterdir())


def test_write_zero_is_rejected_and_partial_file_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    monkeypatch.setattr(workspace.os, "write", lambda _fd, _data: 0)
    expect_code(
        WorkspaceErrorCode.WRITE_FAILED,
        lambda: workspaces.create_file(layout, WorkspaceArea.INPUT, FILE, b"secret"),
    )
    assert not tuple(layout.input.iterdir())


def test_descriptor_tamper_is_rejected_and_partial_file_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    real_fstat = workspace.os.fstat
    file_calls = 0

    def tampered(descriptor: int) -> os.stat_result:
        nonlocal file_calls
        info = real_fstat(descriptor)
        if stat.S_ISREG(info.st_mode):
            file_calls += 1
            if file_calls == 2:
                values = list(info)
                values[0] = stat.S_IFREG | 0o644
                return os.stat_result(values)
        return info

    monkeypatch.setattr(workspace.os, "fstat", tampered)
    expect_code(
        WorkspaceErrorCode.WRITE_FAILED,
        lambda: workspaces.create_file(layout, WorkspaceArea.INPUT, FILE, b"secret"),
    )
    assert not tuple(layout.input.iterdir())


def test_post_write_rename_swap_is_rejected_without_unlinking_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    real_stat = workspace.os.stat
    swapped = False

    def swap(name: object, **kwargs: object) -> os.stat_result:
        nonlocal swapped
        if name == FILE and not swapped:
            swapped = True
            (layout.input / FILE).rename(layout.input / ("e" * 64))
            (layout.input / FILE).write_bytes(b"replacement")
            os.chmod(layout.input / FILE, 0o600)
        return real_stat(name, **kwargs)

    monkeypatch.setattr(workspace.os, "stat", swap)
    expect_code(
        WorkspaceErrorCode.WRITE_FAILED,
        lambda: workspaces.create_file(layout, WorkspaceArea.INPUT, FILE, b"secret"),
    )
    assert (layout.input / FILE).read_bytes() == b"replacement"


def test_post_write_disappearance_and_verify_os_error_are_content_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    real_stat = workspace.os.stat

    def disappear(name: object, **kwargs: object) -> os.stat_result:
        if name == FILE:
            raise FileNotFoundError
        return real_stat(name, **kwargs)

    monkeypatch.setattr(workspace.os, "stat", disappear)
    expect_code(
        WorkspaceErrorCode.WRITE_FAILED,
        lambda: workspaces.create_file(layout, WorkspaceArea.INPUT, FILE, b"secret"),
    )
    monkeypatch.setattr(workspace.os, "stat", real_stat)
    monkeypatch.setattr(workspace.os, "listdir", lambda _fd: (_ for _ in ()).throw(OSError()))
    expect_code(WorkspaceErrorCode.INVALID_LAYOUT, lambda: workspaces.verify(layout))


def test_cleanup_detects_owner_identity_mismatch_and_absent_job(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    first = workspaces.create(OWNER, JOB)
    second = workspaces.create(OWNER, "d" * 64)
    foreign_owner = workspaces.create("e" * 64, "f" * 64)
    tampered = replace(first, _owner_identity=foreign_owner._owner_identity)
    expect_code(WorkspaceErrorCode.CLEANUP_FAILED, lambda: workspaces.cleanup(tampered))
    workspaces.cleanup(first)
    assert workspaces.cleanup(first).already_absent
    assert second.job.exists()


def test_cleanup_detects_file_swap_between_preflight_and_unlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    target = workspaces.create_file(layout, WorkspaceArea.RESULT, FILE, b"original")
    real_stat = workspace.os.stat
    calls = 0

    def swap(name: object, **kwargs: object) -> os.stat_result:
        nonlocal calls
        if name == FILE:
            calls += 1
            if calls == 2:
                target.rename(layout.result / ("e" * 64))
                target.write_bytes(b"replacement")
                os.chmod(target, 0o600)
        return real_stat(name, **kwargs)

    monkeypatch.setattr(workspace.os, "stat", swap)
    expect_code(WorkspaceErrorCode.CLEANUP_FAILED, lambda: workspaces.cleanup(layout))
    assert target.read_bytes() == b"replacement"


def test_missing_area_identity_is_rejected_by_all_operations(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    malformed = replace(layout, _area_identities=layout._area_identities[1:])
    expect_code(WorkspaceErrorCode.INVALID_LAYOUT, lambda: workspaces.verify(malformed))
    expect_code(
        WorkspaceErrorCode.INVALID_LAYOUT,
        lambda: workspaces.create_file(malformed, WorkspaceArea.INPUT, FILE, b"secret"),
    )
    expect_code(WorkspaceErrorCode.CLEANUP_FAILED, lambda: workspaces.cleanup(malformed))


def test_private_nonhex_file_is_unsafe(tmp_path: Path) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    unknown = layout.work / "worker-output"
    unknown.write_bytes(b"x")
    os.chmod(unknown, 0o600)
    expect_code(WorkspaceErrorCode.UNSAFE_ENTRY, lambda: workspaces.cleanup(layout))


def test_cleanup_rejects_os_removal_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    real_rmdir = workspace.os.rmdir

    def fail_area(name: object, *, dir_fd: int | None = None) -> None:
        if name == WorkspaceArea.INPUT.value:
            raise OSError
        real_rmdir(name, dir_fd=dir_fd)

    monkeypatch.setattr(workspace.os, "rmdir", fail_area)
    expect_code(WorkspaceErrorCode.CLEANUP_FAILED, lambda: workspaces.cleanup(layout))


def test_cleanup_verifies_job_name_remains_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    job_info = layout.job.stat(follow_symlinks=False)
    real_optional = WorkspaceManager._optional_stat

    def stale_stat(self: WorkspaceManager, parent_fd: int, name: str) -> os.stat_result | None:
        result = real_optional(self, parent_fd, name)
        if name == JOB and result is None:
            return job_info
        return result

    monkeypatch.setattr(WorkspaceManager, "_optional_stat", stale_stat)
    expect_code(WorkspaceErrorCode.CLEANUP_FAILED, lambda: workspaces.cleanup(layout))


def test_best_effort_rollback_helpers_do_not_cross_identity_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)
    root_fd = workspaces._open_root()
    try:
        owner_fd = workspaces._open_directory(root_fd, OWNER, layout._owner_identity)
        real_stat = workspace.os.stat

        def changed(name: object, **kwargs: object) -> os.stat_result:
            info = real_stat(name, **kwargs)
            if name == WorkspaceArea.INPUT.value:
                return changed_inode(info)
            return info

        monkeypatch.setattr(workspace.os, "stat", changed)
        workspaces._remove_created_job(
            owner_fd,
            JOB,
            ((WorkspaceArea.INPUT, dict(layout._area_identities)[WorkspaceArea.INPUT]),),
        )
        os.close(owner_fd)
        workspaces._remove_owner_if_empty_fd(root_fd, OWNER, layout._job_identity)
    finally:
        os.close(root_fd)
    assert layout.input.exists()


def test_best_effort_owner_removal_swallows_os_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspaces = manager(tmp_path)
    layout = workspaces.create(OWNER, JOB)

    def fail(*_args: object, **_kwargs: object) -> None:
        raise OSError

    monkeypatch.setattr(WorkspaceManager, "_remove_owner_if_empty_fd", fail)
    workspaces._remove_owner_if_empty(OWNER, layout._owner_identity)
    assert layout.owner.exists()
