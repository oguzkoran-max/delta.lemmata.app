"""Private, confined filesystem workspaces for ephemeral jobs."""

from __future__ import annotations

import os
import re
import stat
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from functools import wraps
from pathlib import Path
from typing import NoReturn


class WorkspaceArea(StrEnum):
    """Fixed directories available inside one job workspace."""

    INPUT = "input"
    WORK = "work"
    RESULT = "result"
    EXPORT = "export"
    CONTROL = "control"


class WorkspaceErrorCode(StrEnum):
    """Stable rejection codes that contain no filesystem or research content."""

    INVALID_ROOT = "WORKSPACE_INVALID_ROOT"
    INVALID_COMPONENT = "WORKSPACE_INVALID_COMPONENT"
    CREATE_FAILED = "WORKSPACE_CREATE_FAILED"
    INVALID_LAYOUT = "WORKSPACE_INVALID_LAYOUT"
    UNSAFE_ENTRY = "WORKSPACE_UNSAFE_ENTRY"
    WRITE_FAILED = "WORKSPACE_WRITE_FAILED"
    CLEANUP_FAILED = "WORKSPACE_CLEANUP_FAILED"


class WorkspaceError(RuntimeError):
    """A content-free workspace rejection."""

    def __init__(self, code: WorkspaceErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class _Identity:
    device: int
    inode: int


@dataclass(frozen=True, slots=True)
class WorkspaceLayout:
    """Server-named paths and creation identities for one workspace."""

    root: Path
    owner: Path
    job: Path
    input: Path
    work: Path
    result: Path
    export: Path
    control: Path
    _owner_identity: _Identity
    _job_identity: _Identity
    _area_identities: tuple[tuple[WorkspaceArea, _Identity], ...]

    def area(self, area: WorkspaceArea) -> Path:
        """Return one fixed area path without accepting an arbitrary name."""

        areas = {
            WorkspaceArea.INPUT: self.input,
            WorkspaceArea.WORK: self.work,
            WorkspaceArea.RESULT: self.result,
            WorkspaceArea.EXPORT: self.export,
            WorkspaceArea.CONTROL: self.control,
        }
        return areas[area]


@dataclass(frozen=True, slots=True)
class CleanupReport:
    """Content-free proof that a cleanup attempt reached an absent workspace."""

    file_count: int
    byte_count: int
    already_absent: bool
    verified_absent: bool = True


_COMPONENT = re.compile(r"[0-9a-f]{64}\Z")
_DIRECTORY_MODE = 0o700
_FILE_MODE = 0o600
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
_FILE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)


def _reject(code: WorkspaceErrorCode) -> NoReturn:
    raise WorkspaceError(code)


def _detach(error: WorkspaceError) -> None:
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True


def _content_free[**P, T](method: Callable[P, T]) -> Callable[P, T]:
    @wraps(method)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return method(*args, **kwargs)
        except WorkspaceError as error:
            _detach(error)
            raise

    return wrapped


def _identity(info: os.stat_result) -> _Identity:
    return _Identity(info.st_dev, info.st_ino)


def _private_directory(info: os.stat_result) -> bool:
    return (
        stat.S_ISDIR(info.st_mode)
        and stat.S_IMODE(info.st_mode) == _DIRECTORY_MODE
        and info.st_uid == os.getuid()
    )


def _private_file(info: os.stat_result) -> bool:
    return (
        stat.S_ISREG(info.st_mode)
        and stat.S_IMODE(info.st_mode) == _FILE_MODE
        and info.st_uid == os.getuid()
        and info.st_nlink == 1
    )


class WorkspaceManager:
    """Create and remove job workspaces beneath one trusted private root."""

    @_content_free
    def __init__(self, trusted_root: Path) -> None:
        try:
            try:
                if not trusted_root.is_absolute() or trusted_root != Path(
                    os.path.abspath(trusted_root)
                ):
                    _reject(WorkspaceErrorCode.INVALID_ROOT)
                lexical = trusted_root
                root_info = os.lstat(lexical)
                resolved = lexical.resolve(strict=True)
                if lexical.is_symlink() or not _private_directory(root_info):
                    _reject(WorkspaceErrorCode.INVALID_ROOT)
                resolved_info = os.stat(resolved, follow_symlinks=False)
                if _identity(root_info) != _identity(resolved_info):
                    _reject(WorkspaceErrorCode.INVALID_ROOT)
            except OSError:
                raise WorkspaceError(WorkspaceErrorCode.INVALID_ROOT) from None
        except WorkspaceError as error:
            _detach(error)
            raise
        self.root = resolved
        self._root_identity = _identity(root_info)

    @_content_free
    def create(self, owner_component: str, job_component: str) -> WorkspaceLayout:
        """Create a private fixed-layout workspace from two opaque server identifiers."""

        try:
            owner_name = self._component(owner_component)
            job_name = self._component(job_component)
            root_fd = self._open_root()
            try:
                owner_fd, owner_identity, owner_created = self._open_or_create_owner(
                    root_fd, owner_name
                )
                try:
                    try:
                        os.mkdir(job_name, _DIRECTORY_MODE, dir_fd=owner_fd)
                    except OSError:
                        _reject(WorkspaceErrorCode.CREATE_FAILED)
                    job_fd = self._open_directory(owner_fd, job_name, None)
                    job_identity = _identity(os.fstat(job_fd))
                    area_identities: list[tuple[WorkspaceArea, _Identity]] = []
                    try:
                        for area in WorkspaceArea:
                            os.mkdir(area.value, _DIRECTORY_MODE, dir_fd=job_fd)
                            area_fd = self._open_directory(job_fd, area.value, None)
                            try:
                                area_identities.append((area, _identity(os.fstat(area_fd))))
                            finally:
                                os.close(area_fd)
                    except (OSError, WorkspaceError):
                        os.close(job_fd)
                        self._remove_created_job(owner_fd, job_name, tuple(area_identities))
                        _reject(WorkspaceErrorCode.CREATE_FAILED)
                    os.close(job_fd)
                finally:
                    os.close(owner_fd)
                owner_path = self.root / owner_name
                job_path = owner_path / job_name
                return WorkspaceLayout(
                    root=self.root,
                    owner=owner_path,
                    job=job_path,
                    input=job_path / WorkspaceArea.INPUT.value,
                    work=job_path / WorkspaceArea.WORK.value,
                    result=job_path / WorkspaceArea.RESULT.value,
                    export=job_path / WorkspaceArea.EXPORT.value,
                    control=job_path / WorkspaceArea.CONTROL.value,
                    _owner_identity=owner_identity,
                    _job_identity=job_identity,
                    _area_identities=tuple(area_identities),
                )
            finally:
                os.close(root_fd)
                if "owner_created" in locals() and owner_created:
                    self._remove_owner_if_empty(owner_name, owner_identity)
        except WorkspaceError as error:
            _detach(error)
            raise
        except OSError:
            rejection = WorkspaceError(WorkspaceErrorCode.CREATE_FAILED)
            _detach(rejection)
            raise rejection from None

    @_content_free
    def create_file(
        self,
        layout: WorkspaceLayout,
        area: WorkspaceArea,
        file_component: str,
        content: bytes,
    ) -> Path:
        """Atomically create one private file without following any path component."""

        descriptor = -1
        area_fd = -1
        created_identity: _Identity | None = None
        name = ""
        try:
            name = self._component(file_component)
            area_fd = self._open_layout_area(layout, area)
            try:
                descriptor = os.open(name, _FILE_FLAGS, _FILE_MODE, dir_fd=area_fd)
                os.fchmod(descriptor, _FILE_MODE)
                created_identity = _identity(os.fstat(descriptor))
                view = memoryview(content)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        _reject(WorkspaceErrorCode.WRITE_FAILED)
                    view = view[written:]
                os.fsync(descriptor)
                info = os.fstat(descriptor)
                if _identity(info) != created_identity or not _private_file(info):
                    _reject(WorkspaceErrorCode.WRITE_FAILED)
            except OSError:
                _reject(WorkspaceErrorCode.WRITE_FAILED)
            finally:
                if descriptor >= 0:  # pragma: no branch - only entered after os.open succeeds
                    os.close(descriptor)
            path_info = os.stat(name, dir_fd=area_fd, follow_symlinks=False)
            if _identity(path_info) != created_identity or not _private_file(path_info):
                _reject(WorkspaceErrorCode.WRITE_FAILED)
            return layout.area(area) / name
        except WorkspaceError as error:
            if area_fd >= 0 and created_identity is not None:  # pragma: no branch
                self._unlink_if_same(area_fd, name, created_identity)
            _detach(error)
            raise
        except OSError:
            if area_fd >= 0 and created_identity is not None:  # pragma: no branch
                self._unlink_if_same(area_fd, name, created_identity)
            rejection = WorkspaceError(WorkspaceErrorCode.WRITE_FAILED)
            _detach(rejection)
            raise rejection from None
        finally:
            if area_fd >= 0:
                os.close(area_fd)

    @_content_free
    def load(self, owner_component: str, job_component: str) -> WorkspaceLayout:
        """Open an existing fixed layout and capture fresh trusted identities."""

        try:
            owner_name = self._component(owner_component)
            job_name = self._component(job_component)
            root_fd = self._open_root()
            try:
                owner_info = self._optional_stat(root_fd, owner_name)
                if owner_info is None or not _private_directory(owner_info):
                    _reject(WorkspaceErrorCode.INVALID_LAYOUT)
                owner_identity = _identity(owner_info)
                owner_fd = self._open_directory(root_fd, owner_name, owner_identity)
                try:
                    job_info = self._optional_stat(owner_fd, job_name)
                    if job_info is None or not _private_directory(job_info):
                        _reject(WorkspaceErrorCode.INVALID_LAYOUT)
                    job_identity = _identity(job_info)
                    job_fd = self._open_directory(owner_fd, job_name, job_identity)
                    try:
                        if set(os.listdir(job_fd)) != {area.value for area in WorkspaceArea}:
                            _reject(WorkspaceErrorCode.INVALID_LAYOUT)
                        area_identities: list[tuple[WorkspaceArea, _Identity]] = []
                        for area in WorkspaceArea:
                            area_fd = self._open_directory(job_fd, area.value, None)
                            try:
                                area_identities.append((area, _identity(os.fstat(area_fd))))
                            finally:
                                os.close(area_fd)
                    finally:
                        os.close(job_fd)
                finally:
                    os.close(owner_fd)
            finally:
                os.close(root_fd)
            owner_path = self.root / owner_name
            job_path = owner_path / job_name
            return WorkspaceLayout(
                root=self.root,
                owner=owner_path,
                job=job_path,
                input=job_path / WorkspaceArea.INPUT.value,
                work=job_path / WorkspaceArea.WORK.value,
                result=job_path / WorkspaceArea.RESULT.value,
                export=job_path / WorkspaceArea.EXPORT.value,
                control=job_path / WorkspaceArea.CONTROL.value,
                _owner_identity=owner_identity,
                _job_identity=job_identity,
                _area_identities=tuple(area_identities),
            )
        except WorkspaceError as error:
            _detach(error)
            raise
        except OSError:
            rejection = WorkspaceError(WorkspaceErrorCode.INVALID_LAYOUT)
            _detach(rejection)
            raise rejection from None

    @_content_free
    def verify(self, layout: WorkspaceLayout) -> None:
        """Verify confinement, identities, modes, and the complete fixed layout."""

        try:
            job_fd = self._open_layout_job(layout)
            try:
                names = set(os.listdir(job_fd))
                if names != {area.value for area in WorkspaceArea} or {
                    area for area, _identity_value in layout._area_identities
                } != set(WorkspaceArea):
                    _reject(WorkspaceErrorCode.INVALID_LAYOUT)
                for area, expected in layout._area_identities:
                    area_fd = self._open_directory(job_fd, area.value, expected)
                    os.close(area_fd)
            finally:
                os.close(job_fd)
        except WorkspaceError as error:
            _detach(error)
            raise
        except OSError:
            rejection = WorkspaceError(WorkspaceErrorCode.INVALID_LAYOUT)
            _detach(rejection)
            raise rejection from None

    @_content_free
    def cleanup(self, layout: WorkspaceLayout) -> CleanupReport:
        """Remove a verified workspace once, then prove the job path is absent."""

        try:
            root_fd = self._open_root()
            try:
                owner_name, job_name = self._layout_names(layout)
                owner_info = self._optional_stat(root_fd, owner_name)
                if owner_info is None:
                    return CleanupReport(0, 0, True)
                if _identity(owner_info) != layout._owner_identity:
                    _reject(WorkspaceErrorCode.CLEANUP_FAILED)
                owner_fd = self._open_directory(root_fd, owner_name, layout._owner_identity)
                try:
                    job_info = self._optional_stat(owner_fd, job_name)
                    if job_info is None:
                        return CleanupReport(0, 0, True)
                    if _identity(job_info) != layout._job_identity:
                        _reject(WorkspaceErrorCode.CLEANUP_FAILED)
                    job_fd = self._open_directory(owner_fd, job_name, layout._job_identity)
                    try:
                        inventory = self._preflight(job_fd, layout)
                        for area, entries in inventory:
                            expected = dict(layout._area_identities)[area]
                            area_fd = self._open_directory(job_fd, area.value, expected)
                            try:
                                for name, identity, _size in entries:
                                    current = os.stat(name, dir_fd=area_fd, follow_symlinks=False)
                                    if _identity(current) != identity or not _private_file(current):
                                        _reject(WorkspaceErrorCode.CLEANUP_FAILED)
                                    os.unlink(name, dir_fd=area_fd)
                            finally:
                                os.close(area_fd)
                            os.rmdir(area.value, dir_fd=job_fd)
                    finally:
                        os.close(job_fd)
                    os.rmdir(job_name, dir_fd=owner_fd)
                    if self._optional_stat(owner_fd, job_name) is not None:
                        _reject(WorkspaceErrorCode.CLEANUP_FAILED)
                    file_count = sum(len(entries) for _area, entries in inventory)
                    byte_count = sum(
                        size
                        for _area, entries in inventory
                        for _name, _identity_value, size in entries
                    )
                finally:
                    os.close(owner_fd)
                self._remove_owner_if_empty_fd(root_fd, owner_name, layout._owner_identity)
                return CleanupReport(file_count, byte_count, False)
            finally:
                os.close(root_fd)
        except WorkspaceError as error:
            _detach(error)
            raise
        except OSError:
            rejection = WorkspaceError(WorkspaceErrorCode.CLEANUP_FAILED)
            _detach(rejection)
            raise rejection from None

    @_content_free
    def clear_areas(
        self,
        layout: WorkspaceLayout,
        areas: Sequence[WorkspaceArea],
    ) -> CleanupReport:
        """Remove files from selected areas while preserving the verified layout."""

        if not areas or any(not isinstance(area, WorkspaceArea) for area in areas):
            _reject(WorkspaceErrorCode.INVALID_LAYOUT)
        selected = frozenset(areas)
        try:
            job_fd = self._open_layout_job(layout)
            try:
                inventory = self._preflight(job_fd, layout)
                selected_inventory = tuple(
                    (area, entries) for area, entries in inventory if area in selected
                )
                for area, entries in selected_inventory:
                    expected = dict(layout._area_identities)[area]
                    area_fd = self._open_directory(job_fd, area.value, expected)
                    try:
                        for name, identity, _size in entries:
                            current = os.stat(name, dir_fd=area_fd, follow_symlinks=False)
                            if _identity(current) != identity or not _private_file(current):
                                _reject(WorkspaceErrorCode.CLEANUP_FAILED)
                            os.unlink(name, dir_fd=area_fd)
                        if os.listdir(area_fd):
                            _reject(WorkspaceErrorCode.CLEANUP_FAILED)
                    finally:
                        os.close(area_fd)
            finally:
                os.close(job_fd)
            self.verify(layout)
            file_count = sum(len(entries) for _area, entries in selected_inventory)
            byte_count = sum(
                size
                for _area, entries in selected_inventory
                for _name, _identity_value, size in entries
            )
            return CleanupReport(file_count, byte_count, file_count == 0)
        except WorkspaceError as error:
            _detach(error)
            raise
        except OSError:
            rejection = WorkspaceError(WorkspaceErrorCode.CLEANUP_FAILED)
            _detach(rejection)
            raise rejection from None

    def _component(self, value: str) -> str:
        if _COMPONENT.fullmatch(value) is None:
            _reject(WorkspaceErrorCode.INVALID_COMPONENT)
        return value

    def _open_root(self) -> int:
        descriptor = os.open(self.root, _DIRECTORY_FLAGS)
        info = os.fstat(descriptor)
        if _identity(info) != self._root_identity or not _private_directory(info):
            os.close(descriptor)
            _reject(WorkspaceErrorCode.INVALID_ROOT)
        return descriptor

    def _open_directory(self, parent_fd: int, name: str, expected: _Identity | None) -> int:
        descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
        info = os.fstat(descriptor)
        if not _private_directory(info) or (expected is not None and _identity(info) != expected):
            os.close(descriptor)
            _reject(WorkspaceErrorCode.INVALID_LAYOUT)
        return descriptor

    def _open_or_create_owner(self, root_fd: int, owner_name: str) -> tuple[int, _Identity, bool]:
        created = False
        try:
            os.mkdir(owner_name, _DIRECTORY_MODE, dir_fd=root_fd)
            created = True
        except FileExistsError:
            pass
        owner_fd = self._open_directory(root_fd, owner_name, None)
        return owner_fd, _identity(os.fstat(owner_fd)), created

    def _layout_names(self, layout: WorkspaceLayout) -> tuple[str, str]:
        if (
            layout.root != self.root
            or layout.owner.parent != self.root
            or layout.job.parent != layout.owner
        ):
            _reject(WorkspaceErrorCode.INVALID_LAYOUT)
        owner_name = self._component(layout.owner.name)
        job_name = self._component(layout.job.name)
        expected_job = self.root / owner_name / job_name
        if layout.job != expected_job or any(
            layout.area(area) != expected_job / area.value for area in WorkspaceArea
        ):
            _reject(WorkspaceErrorCode.INVALID_LAYOUT)
        return owner_name, job_name

    def _open_layout_job(self, layout: WorkspaceLayout) -> int:
        root_fd = self._open_root()
        try:
            owner_name, job_name = self._layout_names(layout)
            owner_fd = self._open_directory(root_fd, owner_name, layout._owner_identity)
            try:
                return self._open_directory(owner_fd, job_name, layout._job_identity)
            finally:
                os.close(owner_fd)
        finally:
            os.close(root_fd)

    def _open_layout_area(self, layout: WorkspaceLayout, area: WorkspaceArea) -> int:
        job_fd = self._open_layout_job(layout)
        try:
            expected = dict(layout._area_identities).get(area)
            if expected is None:
                _reject(WorkspaceErrorCode.INVALID_LAYOUT)
            return self._open_directory(job_fd, area.value, expected)
        finally:
            os.close(job_fd)

    def _preflight(
        self, job_fd: int, layout: WorkspaceLayout
    ) -> tuple[tuple[WorkspaceArea, tuple[tuple[str, _Identity, int], ...]], ...]:
        if set(os.listdir(job_fd)) != {area.value for area in WorkspaceArea}:
            _reject(WorkspaceErrorCode.CLEANUP_FAILED)
        inventory: list[tuple[WorkspaceArea, tuple[tuple[str, _Identity, int], ...]]] = []
        expected_areas = dict(layout._area_identities)
        for area in WorkspaceArea:
            expected = expected_areas.get(area)
            if expected is None:
                _reject(WorkspaceErrorCode.CLEANUP_FAILED)
            area_fd = self._open_directory(job_fd, area.value, expected)
            try:
                entries: list[tuple[str, _Identity, int]] = []
                for name in os.listdir(area_fd):
                    info = os.stat(name, dir_fd=area_fd, follow_symlinks=False)
                    if _COMPONENT.fullmatch(name) is None or not _private_file(info):
                        _reject(WorkspaceErrorCode.UNSAFE_ENTRY)
                    entries.append((name, _identity(info), info.st_size))
                inventory.append((area, tuple(entries)))
            finally:
                os.close(area_fd)
        return tuple(inventory)

    def _optional_stat(self, parent_fd: int, name: str) -> os.stat_result | None:
        try:
            return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None

    def _unlink_if_same(self, parent_fd: int, name: str, expected: _Identity) -> None:
        try:
            info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if _identity(info) == expected and _private_file(info):
                os.unlink(name, dir_fd=parent_fd)
        except OSError:
            return

    def _remove_created_job(
        self,
        owner_fd: int,
        job_name: str,
        created_areas: tuple[tuple[WorkspaceArea, _Identity], ...],
    ) -> None:
        try:
            job_fd = self._open_directory(owner_fd, job_name, None)
            try:
                for area, expected in reversed(created_areas):
                    info = os.stat(area.value, dir_fd=job_fd, follow_symlinks=False)
                    if _identity(info) == expected:
                        os.rmdir(area.value, dir_fd=job_fd)
            finally:
                os.close(job_fd)
            os.rmdir(job_name, dir_fd=owner_fd)
        except (OSError, WorkspaceError):
            return

    def _remove_owner_if_empty(self, owner_name: str, expected: _Identity) -> None:
        try:
            root_fd = self._open_root()
            try:
                self._remove_owner_if_empty_fd(root_fd, owner_name, expected)
            finally:
                os.close(root_fd)
        except (OSError, WorkspaceError):
            return

    def _remove_owner_if_empty_fd(self, root_fd: int, owner_name: str, expected: _Identity) -> None:
        info = self._optional_stat(root_fd, owner_name)
        if info is None or _identity(info) != expected:
            return
        owner_fd = self._open_directory(root_fd, owner_name, expected)
        try:
            empty = not os.listdir(owner_fd)
        finally:
            os.close(owner_fd)
        if empty:
            os.rmdir(owner_name, dir_fd=root_fd)
