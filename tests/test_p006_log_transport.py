from __future__ import annotations

import hashlib
import importlib
import io
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def transport() -> Any:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    return importlib.import_module("p006_log_transport")


def _package(root: Path) -> Path:
    package = root / "package"
    direct = package / "direct-reference"
    direct.mkdir(parents=True)
    (direct / "base.direct.json").write_bytes(b'{"value":1}\n')
    (package / "oracle-freeze.json").write_bytes(b'{"schema_version":"test"}\n')
    (package / "session-info.json").write_bytes(b'{"platform":"linux/amd64"}\n')
    retained = sorted(path for path in package.rglob("*") if path.is_file())
    (package / "oracle-freeze.sha256").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
            f"{path.relative_to(package).as_posix()}\n"
            for path in retained
        ),
        encoding="utf-8",
    )
    return package


def _log(transport: Any, package: Path, *, prefixed: bool = False) -> str:
    stream = io.StringIO()
    transport.emit(package, stream)
    payload = stream.getvalue()
    if prefixed:
        return "".join(
            f"job\tstep\t2026-07-14T00:00:00Z {line}" for line in payload.splitlines(True)
        )
    return payload


def test_checksum_bound_log_transport_round_trip_with_github_prefixes(
    tmp_path: Path, transport: Any
) -> None:
    package = _package(tmp_path)
    log_path = tmp_path / "job.log"
    log_path.write_text(_log(transport, package, prefixed=True), encoding="utf-8")
    destination = tmp_path / "extracted"

    digest, file_count, byte_count = transport.extract(log_path, destination)

    assert len(digest) == 64
    assert file_count == 4
    assert byte_count == sum(path.stat().st_size for path in package.rglob("*") if path.is_file())
    assert {
        path.relative_to(destination).as_posix(): path.read_bytes()
        for path in destination.rglob("*")
        if path.is_file()
    } == {
        path.relative_to(package).as_posix(): path.read_bytes()
        for path in package.rglob("*")
        if path.is_file()
    }


def test_emit_rejects_symlinks_and_invalid_internal_checksum(
    tmp_path: Path, transport: Any
) -> None:
    package = _package(tmp_path)
    (package / "unsafe").symlink_to(package / "session-info.json")
    with pytest.raises(ValueError, match="P006_LOG_TRANSPORT_FILE_INVALID"):
        transport.emit(package, io.StringIO())
    (package / "unsafe").unlink()
    (package / "session-info.json").write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="P006_LOG_TRANSPORT_CHECKSUM_INVALID"):
        transport.emit(package, io.StringIO())


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "corrupt", "wrong-end"])
def test_extract_rejects_incomplete_or_corrupt_transport(
    tmp_path: Path, transport: Any, mutation: str
) -> None:
    package = _package(tmp_path)
    lines = _log(transport, package).splitlines()
    chunk_index = next(index for index, line in enumerate(lines) if transport.CHUNK_MARKER in line)
    if mutation == "missing":
        del lines[chunk_index]
    elif mutation == "duplicate":
        lines.insert(chunk_index, lines[chunk_index])
    elif mutation == "corrupt":
        replacement = "A" if lines[chunk_index][-1] != "A" else "B"
        lines[chunk_index] = lines[chunk_index][:-1] + replacement
    else:
        lines[-1] = transport.END_MARKER + "0" * 64
    log_path = tmp_path / f"{mutation}.log"
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="P006_LOG_TRANSPORT_"):
        transport.extract(log_path, tmp_path / f"out-{mutation}")


def test_extract_rejects_unsafe_bundle_path(tmp_path: Path, transport: Any) -> None:
    content = b"content\n"
    checksum = f"{hashlib.sha256(content).hexdigest()}  ../outside\n".encode()
    files = [
        {
            "byte_count": len(content),
            "content_base64": transport.base64.b64encode(content).decode(),
            "path": "../outside",
            "sha256": hashlib.sha256(content).hexdigest(),
        },
        {
            "byte_count": len(checksum),
            "content_base64": transport.base64.b64encode(checksum).decode(),
            "path": "oracle-freeze.sha256",
            "sha256": hashlib.sha256(checksum).hexdigest(),
        },
    ]
    payload = transport._canonical_json(
        {"files": files, "schema_version": transport.SCHEMA_VERSION}
    )
    encoded = transport.base64.b64encode(payload).decode()
    digest = hashlib.sha256(payload).hexdigest()
    metadata = (
        transport._canonical_json(
            {
                "byte_count": len(payload),
                "chunk_count": 1,
                "schema_version": transport.SCHEMA_VERSION,
                "sha256": digest,
            }
        )
        .decode()
        .strip()
    )
    log_path = tmp_path / "unsafe.log"
    log_path.write_text(
        f"{transport.BEGIN_MARKER}{metadata}\n"
        f"{transport.CHUNK_MARKER}000001/000001 {encoded}\n"
        f"{transport.END_MARKER}{digest}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="P006_LOG_TRANSPORT_PATH_INVALID"):
        transport.extract(log_path, tmp_path / "out")


def test_extract_refuses_existing_destination(tmp_path: Path, transport: Any) -> None:
    package = _package(tmp_path)
    log_path = tmp_path / "job.log"
    log_path.write_text(_log(transport, package), encoding="utf-8")
    destination = tmp_path / "existing"
    destination.mkdir()

    with pytest.raises(ValueError, match="P006_LOG_TRANSPORT_DESTINATION_INVALID"):
        transport.extract(log_path, destination)


def test_transport_envelope_is_canonical_and_schema_bound(tmp_path: Path, transport: Any) -> None:
    package = _package(tmp_path)
    payload = transport._bundle(transport._read_directory(package))
    envelope = json.loads(payload)

    assert payload == transport._canonical_json(envelope)
    assert envelope["schema_version"] == "p006-log-transport-v1"
    assert [record["path"] for record in envelope["files"]] == sorted(
        record["path"] for record in envelope["files"]
    )
