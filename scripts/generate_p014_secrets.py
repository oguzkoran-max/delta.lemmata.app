#!/usr/bin/env python3
"""Create one private P014 runtime-secret file without printing secret material."""

from __future__ import annotations

import argparse
import os
import secrets
import stat
from collections.abc import Callable, Sequence
from pathlib import Path

SECRET_NAMES = (
    "DELTA_JOB_OWNER_SECRET_HEX",
    "DELTA_PREPARATION_AUTHORITY_SECRET_HEX",
    "DELTA_RECOVERY_RECEIPT_SECRET_HEX",
)


class SecretFileError(RuntimeError):
    """A content-free secret-file creation failure."""


def _private_parent(path: Path) -> Path:
    if not path.is_absolute():
        raise SecretFileError("P014_SECRET_PATH_NOT_ABSOLUTE")
    try:
        parent = path.parent.resolve(strict=True)
        info = parent.stat()
    except OSError as error:
        raise SecretFileError("P014_SECRET_PARENT_INVALID") from error
    if parent != path.parent or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise SecretFileError("P014_SECRET_PARENT_NOT_PRIVATE")
    return parent


def generate_values(
    token_hex: Callable[[int], str] = secrets.token_hex,
) -> tuple[str, str, str]:
    """Generate three distinct 256-bit lowercase hexadecimal values."""

    values = tuple(token_hex(32) for _ in SECRET_NAMES)
    if len(set(values)) != len(SECRET_NAMES) or any(
        len(value) != 64 or value.casefold() != value for value in values
    ):
        raise SecretFileError("P014_SECRET_GENERATION_FAILED")
    try:
        if any(bytes.fromhex(value).hex() != value for value in values):
            raise ValueError
    except ValueError as error:
        raise SecretFileError("P014_SECRET_GENERATION_FAILED") from error
    return values  # type: ignore[return-value]


def create_secret_file(path: Path) -> None:
    """Atomically reserve and write one owner-private environment file."""

    _private_parent(path)
    values = generate_values()
    payload = "".join(
        f"{name}={value}\n" for name, value in zip(SECRET_NAMES, values, strict=True)
    ).encode("ascii")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags, 0o600)
        os.fchmod(descriptor, 0o600)
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError
            view = view[written:]
        os.fsync(descriptor)
    except FileExistsError as error:
        raise SecretFileError("P014_SECRET_FILE_EXISTS") from error
    except OSError as error:
        if descriptor is not None:
            try:
                os.unlink(path)
            except OSError:
                pass
        raise SecretFileError("P014_SECRET_WRITE_FAILED") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
    info = os.lstat(path)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        try:
            os.unlink(path)
        except OSError:
            pass
        raise SecretFileError("P014_SECRET_FILE_NOT_PRIVATE")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_args(argv)
    try:
        create_secret_file(arguments.output)
    except SecretFileError as error:
        print(str(error), file=os.sys.stderr)
        return 1
    print("p014-secrets-created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
