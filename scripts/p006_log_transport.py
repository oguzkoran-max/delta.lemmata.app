#!/usr/bin/env python3
"""Move a small checksum-bound P006 evidence package through CI job logs."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, TextIO

SCHEMA_VERSION = "p006-log-transport-v1"
BEGIN_MARKER = "P006_LOG_TRANSPORT_BEGIN "
CHUNK_MARKER = "P006_LOG_TRANSPORT_CHUNK "
END_MARKER = "P006_LOG_TRANSPORT_END "
CHUNK_SIZE = 768
MAX_FILE_COUNT = 64
MAX_RAW_BYTES = 2 * 1024 * 1024
MAX_ENVELOPE_BYTES = 4 * 1024 * 1024
MAX_LOG_BYTES = 8 * 1024 * 1024
HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def _fail(code: str) -> NoReturn:
    raise ValueError(code)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            _fail("P006_LOG_TRANSPORT_DUPLICATE_KEY")
        value[key] = item
    return value


def _reject_constant(_: str) -> NoReturn:
    _fail("P006_LOG_TRANSPORT_JSON_INVALID")


def _load_json(payload: bytes) -> Any:
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("P006_LOG_TRANSPORT_JSON_INVALID")
    if payload != _canonical_json(value):
        _fail("P006_LOG_TRANSPORT_JSON_INVALID")
    return value


def _safe_relative_path(raw: Any) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw or "\x00" in raw:
        _fail("P006_LOG_TRANSPORT_PATH_INVALID")
    path = PurePosixPath(raw)
    if (
        path.is_absolute()
        or path.as_posix() != raw
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        _fail("P006_LOG_TRANSPORT_PATH_INVALID")
    return raw


def _validate_checksum_manifest(files: dict[str, bytes]) -> None:
    checksum_name = "oracle-freeze.sha256"
    if checksum_name not in files:
        _fail("P006_LOG_TRANSPORT_CHECKSUM_INVALID")
    expected = "".join(
        f"{_sha256_bytes(files[path])}  {path}\n" for path in sorted(files) if path != checksum_name
    ).encode()
    if files[checksum_name] != expected:
        _fail("P006_LOG_TRANSPORT_CHECKSUM_INVALID")


def _read_directory(directory: Path) -> dict[str, bytes]:
    if directory.is_symlink() or not directory.is_dir():
        _fail("P006_LOG_TRANSPORT_DIRECTORY_INVALID")
    files: dict[str, bytes] = {}
    total = 0
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            _fail("P006_LOG_TRANSPORT_FILE_INVALID")
        if path.is_dir():
            continue
        if not path.is_file():
            _fail("P006_LOG_TRANSPORT_FILE_INVALID")
        relative = _safe_relative_path(path.relative_to(directory).as_posix())
        payload = path.read_bytes()
        total += len(payload)
        if len(files) >= MAX_FILE_COUNT or total > MAX_RAW_BYTES:
            _fail("P006_LOG_TRANSPORT_LIMIT_EXCEEDED")
        files[relative] = payload
    if not files:
        _fail("P006_LOG_TRANSPORT_FILE_INVALID")
    _validate_checksum_manifest(files)
    return files


def _bundle(files: dict[str, bytes]) -> bytes:
    envelope = {
        "files": [
            {
                "byte_count": len(payload),
                "content_base64": base64.b64encode(payload).decode("ascii"),
                "path": path,
                "sha256": _sha256_bytes(payload),
            }
            for path, payload in sorted(files.items())
        ],
        "schema_version": SCHEMA_VERSION,
    }
    payload = _canonical_json(envelope)
    if len(payload) > MAX_ENVELOPE_BYTES:
        _fail("P006_LOG_TRANSPORT_LIMIT_EXCEEDED")
    return payload


def emit(directory: Path, stream: TextIO) -> tuple[str, int, int]:
    payload = _bundle(_read_directory(directory))
    digest = _sha256_bytes(payload)
    encoded = base64.b64encode(payload).decode("ascii")
    chunks = [
        encoded[offset : offset + CHUNK_SIZE] for offset in range(0, len(encoded), CHUNK_SIZE)
    ]
    metadata = {
        "byte_count": len(payload),
        "chunk_count": len(chunks),
        "schema_version": SCHEMA_VERSION,
        "sha256": digest,
    }
    stream.write(BEGIN_MARKER + _canonical_json(metadata).decode().rstrip("\n") + "\n")
    for index, chunk in enumerate(chunks, start=1):
        stream.write(f"{CHUNK_MARKER}{index:06d}/{len(chunks):06d} {chunk}\n")
    stream.write(f"{END_MARKER}{digest}\n")
    stream.flush()
    return digest, len(chunks), len(payload)


def _marker_value(line: str, marker: str) -> str | None:
    offset = line.find(marker)
    if offset < 0:
        return None
    return line[offset + len(marker) :].strip()


def _transport_payload(log_payload: bytes) -> tuple[bytes, str]:
    if not log_payload or len(log_payload) > MAX_LOG_BYTES:
        _fail("P006_LOG_TRANSPORT_LOG_INVALID")
    try:
        lines = log_payload.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        _fail("P006_LOG_TRANSPORT_LOG_INVALID")

    begins = [value for line in lines if (value := _marker_value(line, BEGIN_MARKER)) is not None]
    ends = [value for line in lines if (value := _marker_value(line, END_MARKER)) is not None]
    if len(begins) != 1 or len(ends) != 1:
        _fail("P006_LOG_TRANSPORT_MARKER_INVALID")
    metadata = _load_json((begins[0] + "\n").encode())
    if not isinstance(metadata, dict) or set(metadata) != {
        "byte_count",
        "chunk_count",
        "schema_version",
        "sha256",
    }:
        _fail("P006_LOG_TRANSPORT_METADATA_INVALID")
    byte_count = metadata["byte_count"]
    chunk_count = metadata["chunk_count"]
    digest = metadata["sha256"]
    if (
        metadata["schema_version"] != SCHEMA_VERSION
        or type(byte_count) is not int
        or not 0 < byte_count <= MAX_ENVELOPE_BYTES
        or type(chunk_count) is not int
        or chunk_count <= 0
        or not isinstance(digest, str)
        or not HEX_64.fullmatch(digest)
        or ends[0] != digest
    ):
        _fail("P006_LOG_TRANSPORT_METADATA_INVALID")

    chunks: dict[int, str] = {}
    pattern = re.compile(r"^(\d{6})/(\d{6}) ([A-Za-z0-9+/=]+)$")
    for line in lines:
        value = _marker_value(line, CHUNK_MARKER)
        if value is None:
            continue
        match = pattern.fullmatch(value)
        if match is None or int(match.group(2)) != chunk_count:
            _fail("P006_LOG_TRANSPORT_CHUNK_INVALID")
        index = int(match.group(1))
        if index in chunks or not 1 <= index <= chunk_count:
            _fail("P006_LOG_TRANSPORT_CHUNK_INVALID")
        chunks[index] = match.group(3)
    if set(chunks) != set(range(1, chunk_count + 1)):
        _fail("P006_LOG_TRANSPORT_CHUNK_INVALID")
    try:
        payload = base64.b64decode(
            "".join(chunks[index] for index in sorted(chunks)), validate=True
        )
    except (binascii.Error, ValueError):
        _fail("P006_LOG_TRANSPORT_CHUNK_INVALID")
    if len(payload) != byte_count or _sha256_bytes(payload) != digest:
        _fail("P006_LOG_TRANSPORT_DIGEST_INVALID")
    return payload, digest


def _files_from_bundle(payload: bytes) -> dict[str, bytes]:
    envelope = _load_json(payload)
    if (
        not isinstance(envelope, dict)
        or set(envelope) != {"files", "schema_version"}
        or envelope["schema_version"] != SCHEMA_VERSION
        or not isinstance(envelope["files"], list)
        or not 0 < len(envelope["files"]) <= MAX_FILE_COUNT
    ):
        _fail("P006_LOG_TRANSPORT_BUNDLE_INVALID")
    files: dict[str, bytes] = {}
    total = 0
    for record in envelope["files"]:
        if not isinstance(record, dict) or set(record) != {
            "byte_count",
            "content_base64",
            "path",
            "sha256",
        }:
            _fail("P006_LOG_TRANSPORT_BUNDLE_INVALID")
        path = _safe_relative_path(record["path"])
        byte_count = record["byte_count"]
        digest = record["sha256"]
        content = record["content_base64"]
        if (
            path in files
            or type(byte_count) is not int
            or byte_count < 0
            or not isinstance(digest, str)
            or not HEX_64.fullmatch(digest)
            or not isinstance(content, str)
        ):
            _fail("P006_LOG_TRANSPORT_BUNDLE_INVALID")
        try:
            decoded = base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError):
            _fail("P006_LOG_TRANSPORT_BUNDLE_INVALID")
        total += len(decoded)
        if len(decoded) != byte_count or _sha256_bytes(decoded) != digest or total > MAX_RAW_BYTES:
            _fail("P006_LOG_TRANSPORT_BUNDLE_INVALID")
        files[path] = decoded
    _validate_checksum_manifest(files)
    return files


def extract(log_path: Path, destination: Path) -> tuple[str, int, int]:
    if log_path.is_symlink() or not log_path.is_file():
        _fail("P006_LOG_TRANSPORT_LOG_INVALID")
    if destination.exists() or destination.is_symlink():
        _fail("P006_LOG_TRANSPORT_DESTINATION_INVALID")
    parent = destination.parent
    if parent.is_symlink() or not parent.is_dir():
        _fail("P006_LOG_TRANSPORT_DESTINATION_INVALID")
    payload, digest = _transport_payload(log_path.read_bytes())
    files = _files_from_bundle(payload)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=parent))
    try:
        for relative, content in sorted(files.items()):
            target = staging.joinpath(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(0o644)
        os.replace(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return digest, len(files), sum(len(content) for content in files.values())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    emit_parser = subparsers.add_parser("emit")
    emit_parser.add_argument("directory", type=Path)
    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("log_path", type=Path)
    extract_parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    if args.command == "emit":
        digest, chunks, byte_count = emit(args.directory, stream=sys.stdout)
        print(
            f"p006-log-transport-emit-ok sha256={digest} chunks={chunks} bytes={byte_count}",
            file=sys.stderr,
        )
    else:
        digest, files, byte_count = extract(args.log_path, args.destination)
        print(f"p006-log-transport-extract-ok sha256={digest} files={files} bytes={byte_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
