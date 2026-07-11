"""Fail-closed intake boundary for untrusted text, CSV, and ZIP uploads."""

from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import secrets
import shutil
import stat
import struct
import unicodedata
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field


class IntakeRole(StrEnum):
    """Role declared by the user before content validation."""

    CORPUS_TEXT = "corpus_text"
    CORPUS_ARCHIVE = "corpus_archive"
    METADATA_CSV = "metadata_csv"


class IntakeErrorCode(StrEnum):
    """Stable content-free rejection codes."""

    EMPTY = "INGEST_EMPTY"
    UPLOAD_LIMIT = "INGEST_UPLOAD_LIMIT"
    BATCH_LIMIT = "INGEST_BATCH_LIMIT"
    DISPLAY_LABEL = "INGEST_DISPLAY_LABEL"
    DUPLICATE_LABEL = "INGEST_DUPLICATE_LABEL"
    ROLE_MISMATCH = "INGEST_ROLE_MISMATCH"
    MIME_MISMATCH = "INGEST_MIME_MISMATCH"
    TYPE_MISMATCH = "INGEST_TYPE_MISMATCH"
    INVALID_UTF8 = "INGEST_INVALID_UTF8"
    NON_NFC = "INGEST_NON_NFC"
    CONTROL_CHARACTER = "INGEST_CONTROL_CHARACTER"
    MARKUP_DOCUMENT = "INGEST_MARKUP_DOCUMENT"
    TEXT_EMPTY = "INGEST_TEXT_EMPTY"
    TEXT_LIMIT = "INGEST_TEXT_LIMIT"
    CSV_INVALID = "INGEST_CSV_INVALID"
    CSV_INJECTION = "INGEST_CSV_INJECTION"
    ARCHIVE_INVALID = "INGEST_ARCHIVE_INVALID"
    ARCHIVE_UNSUPPORTED = "INGEST_ARCHIVE_UNSUPPORTED"
    ARCHIVE_ENCRYPTED = "INGEST_ARCHIVE_ENCRYPTED"
    ARCHIVE_UNSAFE_PATH = "INGEST_ARCHIVE_UNSAFE_PATH"
    ARCHIVE_UNSAFE_TYPE = "INGEST_ARCHIVE_UNSAFE_TYPE"
    ARCHIVE_DUPLICATE = "INGEST_ARCHIVE_DUPLICATE"
    ARCHIVE_LIMIT = "INGEST_ARCHIVE_LIMIT"
    NESTED_ARCHIVE = "INGEST_NESTED_ARCHIVE"
    WORKSPACE_INVALID = "INGEST_WORKSPACE_INVALID"
    EXTRACTION_FAILED = "INGEST_EXTRACTION_FAILED"
    CLEANUP_FAILED = "INGEST_CLEANUP_FAILED"
    INTERNAL_ID = "INGEST_INTERNAL_ID"


class IntakeError(ValueError):
    """A rejection that never includes payload, filename, cell, or system path."""

    def __init__(self, code: IntakeErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class IngestionLimits(BaseModel):
    """Versioned resource policy loaded from the packaged JSON profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_version: str = Field(pattern=r"^ingestion-limits-v[0-9]+$")
    max_upload_bytes: int = Field(gt=0)
    max_batch_bytes: int = Field(gt=0)
    max_batch_expanded_bytes: int = Field(gt=0)
    max_batch_files: int = Field(gt=0)
    max_display_label_bytes: int = Field(gt=0)
    max_text_chars: int = Field(gt=0)
    max_lines: int = Field(gt=0)
    max_tokens: int = Field(gt=0)
    max_token_chars: int = Field(gt=0)
    max_archive_members: int = Field(gt=0)
    max_central_directory_bytes: int = Field(gt=0)
    max_member_bytes: int = Field(gt=0)
    max_archive_expanded_bytes: int = Field(gt=0)
    max_compression_ratio: float = Field(gt=1.0)
    max_path_depth: int = Field(gt=0)
    max_path_bytes: int = Field(gt=0)
    max_csv_rows: int = Field(gt=0)
    max_csv_columns: int = Field(gt=1)
    max_csv_cell_chars: int = Field(gt=0)
    read_chunk_bytes: int = Field(gt=0)


DEFAULT_LIMITS = IngestionLimits.model_validate_json(
    files("delta_lemmata").joinpath("data/ingestion-limits-v1.json").read_text(encoding="utf-8")
)


class IntakeReceipt(BaseModel):
    """Content-free result safe to retain or render after validation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    asset_id: str = Field(pattern=r"^asset_[0-9a-f]{32}$")
    role: IntakeRole
    display_label: str = Field(min_length=1)
    storage_name: str = Field(pattern=r"^asset_[0-9a-f]{32}\.(txt|csv|zip)$")
    byte_size: int = Field(ge=0)
    expanded_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    line_count: int | None = Field(default=None, ge=1)
    token_count: int | None = Field(default=None, ge=1)
    row_count: int | None = Field(default=None, ge=1)
    column_count: int | None = Field(default=None, ge=2)
    member_count: int | None = Field(default=None, ge=1)
    limit_profile: str
    status: Literal["validated-for-intake"] = "validated-for-intake"


@dataclass(frozen=True, slots=True)
class IncomingUpload:
    """Untrusted request bytes with an explicit intake role."""

    role: IntakeRole
    display_label: str
    data: bytes = field(repr=False)
    declared_mime: str | None = None


@dataclass(frozen=True, slots=True)
class _TextStats:
    line_count: int
    token_count: int


@dataclass(frozen=True, slots=True)
class _CsvStats:
    line_count: int
    token_count: int
    row_count: int
    column_count: int


@dataclass(frozen=True, slots=True)
class _ArchiveMember:
    index: int
    display_label: str
    file_size: int
    line_count: int
    token_count: int
    sha256: str


@dataclass(frozen=True, slots=True)
class _CentralEntry:
    index: int
    decoded_name: str
    flags: int
    compression: int
    version_needed: int
    modified_time: int
    modified_date: int
    crc32: int
    compressed_size: int
    file_size: int
    local_offset: int
    create_system: int
    external_attr: int


@dataclass(frozen=True, slots=True)
class _ArchiveInspection:
    members: tuple[_ArchiveMember, ...]
    expanded_bytes: int


@dataclass(frozen=True, slots=True)
class ExtractedArchive:
    """Application-owned extracted workspace. P005 will own lifecycle policy."""

    workspace: Path
    members: tuple[IntakeReceipt, ...]

    def cleanup(self) -> None:
        try:
            _cleanup_workspace(self.workspace)
        except IntakeError as error:
            _detach_error_context(error)
            raise

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.cleanup()


AssetIdFactory = Callable[[], str]

_ROLE_EXTENSION = {
    IntakeRole.CORPUS_TEXT: ".txt",
    IntakeRole.CORPUS_ARCHIVE: ".zip",
    IntakeRole.METADATA_CSV: ".csv",
}
_ROLE_MIME = {
    IntakeRole.CORPUS_TEXT: frozenset({"text/plain", "application/octet-stream"}),
    IntakeRole.CORPUS_ARCHIVE: frozenset(
        {"application/zip", "application/x-zip-compressed", "application/octet-stream"}
    ),
    IntakeRole.METADATA_CSV: frozenset(
        {"text/csv", "text/plain", "application/vnd.ms-excel", "application/octet-stream"}
    ),
}
_ALLOWED_TEXT_CONTROLS = frozenset({"\t", "\n", "\r"})
_UNICODE_LINE_CATEGORIES = frozenset({"Zl", "Zp"})
_UNSAFE_LABEL_CATEGORIES = frozenset({"Cc", "Cf"}) | _UNICODE_LINE_CATEGORIES
_BIDI_CONTROLS = frozenset(
    {
        "\u061c",
        "\u200e",
        "\u200f",
        *map(chr, range(0x202A, 0x202F)),
        *map(chr, range(0x2066, 0x206A)),
    }
)
_MARKUP_PREFIXES = ("<!doctype", "<html", "<?xml", "<tei", "<script")
_BINARY_DOCUMENT_SIGNATURES = (
    b"%PDF-",
    b"{\\rtf",
    b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
    b"\x1f\x8b",
    b"7z\xbc\xaf\x27\x1c",
    b"Rar!\x1a\x07",
    b"\x89PNG\r\n\x1a\n",
    b"\xff\xd8\xff",
    b"GIF87a",
    b"GIF89a",
    b"SQLite format 3\x00",
)
_FORMULA_PREFIXES = ("=", "+", "-", "@")
_HTML_TAG = re.compile(r"<\s*/?\s*[A-Za-z!][^>]*>")
_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_RESERVED_PARTS = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
)
_ZIP_EOCD = struct.Struct("<4s4H2LH")
_ZIP_CENTRAL = struct.Struct("<4s6H3L5H2L")
_ZIP_LOCAL = struct.Struct("<4s5H3L2H")
_ZIP_EOCD_SIGNATURE = b"PK\x05\x06"
_ZIP_CENTRAL_SIGNATURE = b"PK\x01\x02"
_ZIP_LOCAL_SIGNATURE = b"PK\x03\x04"
_ZIP64_SENTINEL_16 = 0xFFFF
_ZIP64_SENTINEL_32 = 0xFFFFFFFF
_SUPPORTED_COMPRESSION = frozenset({zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})
_ALLOWED_ZIP_FLAGS = 0x0806
_SUPERSCRIPT_DIGITS = str.maketrans({"¹": "1", "²": "2", "³": "3"})


def _reject(code: IntakeErrorCode) -> None:
    raise IntakeError(code)


def _detach_error_context(error: IntakeError) -> None:
    error.__context__ = None
    error.__cause__ = None
    error.__suppress_context__ = True


def _token(factory: AssetIdFactory | None) -> str:
    value = factory() if factory is not None else secrets.token_hex(16)
    if re.fullmatch(r"[0-9a-f]{32}", value) is None:
        _reject(IntakeErrorCode.INTERNAL_ID)
    return value


def _asset_id(factory: AssetIdFactory | None) -> str:
    return f"asset_{_token(factory)}"


def _safe_part(part: str) -> bool:
    if not part or part in {".", ".."} or part[-1] in {" ", "."}:
        return False
    if part.startswith(".") or part.casefold() == "__macosx":
        return False
    base = part.split(".", 1)[0].casefold().translate(_SUPERSCRIPT_DIGITS)
    return base not in _RESERVED_PARTS


def _validate_display_label(label: str, role: IntakeRole, limits: IngestionLimits) -> str:
    try:
        encoded = label.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        _reject(IntakeErrorCode.DISPLAY_LABEL)
    if (
        not label
        or label != label.strip()
        or label != unicodedata.normalize("NFC", label)
        or len(encoded) > limits.max_display_label_bytes
        or any(character in label for character in ("/", "\\", ":", "<", ">", "\x00"))
        or any(unicodedata.category(character) in _UNSAFE_LABEL_CATEGORIES for character in label)
    ):
        _reject(IntakeErrorCode.DISPLAY_LABEL)
    if not _safe_part(label):
        _reject(IntakeErrorCode.DISPLAY_LABEL)
    if not label.casefold().endswith(_ROLE_EXTENSION[role]):
        _reject(IntakeErrorCode.ROLE_MISMATCH)
    return label


def _validate_mime(role: IntakeRole, declared_mime: str | None) -> None:
    if declared_mime is None:
        return
    normalized = declared_mime.partition(";")[0].strip().casefold()
    if normalized not in _ROLE_MIME[role]:
        _reject(IntakeErrorCode.MIME_MISMATCH)


def _looks_like_zip(data: bytes) -> bool:
    return data.startswith((_ZIP_LOCAL_SIGNATURE, _ZIP_EOCD_SIGNATURE)) or zipfile.is_zipfile(
        io.BytesIO(data)
    )


def _looks_like_binary_document(data: bytes) -> bool:
    probe = data.removeprefix(b"\xef\xbb\xbf")
    return probe.startswith(_BINARY_DOCUMENT_SIGNATURES)


def _validate_common(request: IncomingUpload, limits: IngestionLimits) -> str:
    label = _validate_display_label(request.display_label, request.role, limits)
    _validate_mime(request.role, request.declared_mime)
    if not request.data:
        _reject(IntakeErrorCode.EMPTY)
    if len(request.data) > limits.max_upload_bytes:
        _reject(IntakeErrorCode.UPLOAD_LIMIT)
    return label


def _decode_text(data: bytes, limits: IngestionLimits) -> tuple[str, _TextStats]:
    if _looks_like_zip(data) or _looks_like_binary_document(data):
        _reject(IntakeErrorCode.TYPE_MISMATCH)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        _reject(IntakeErrorCode.INVALID_UTF8)
    if "\ufeff" in text:
        _reject(IntakeErrorCode.CONTROL_CHARACTER)
    if text != unicodedata.normalize("NFC", text):
        _reject(IntakeErrorCode.NON_NFC)
    for character in text:
        if (
            unicodedata.category(character) == "Cc" and character not in _ALLOWED_TEXT_CONTROLS
        ) or character in _BIDI_CONTROLS:
            _reject(IntakeErrorCode.CONTROL_CHARACTER)
    stripped = text.strip()
    if not stripped:
        _reject(IntakeErrorCode.TEXT_EMPTY)
    if stripped[:32].casefold().startswith(_MARKUP_PREFIXES):
        _reject(IntakeErrorCode.MARKUP_DOCUMENT)
    line_count = max(1, len(text.splitlines()))
    if len(text) > limits.max_text_chars or line_count > limits.max_lines:
        _reject(IntakeErrorCode.TEXT_LIMIT)
    token_count = 0
    for token in re.finditer(r"\S+", text):
        token_count += 1
        if token.end() - token.start() > limits.max_token_chars:
            _reject(IntakeErrorCode.TEXT_LIMIT)
        if token_count > limits.max_tokens:
            _reject(IntakeErrorCode.TEXT_LIMIT)
    return text, _TextStats(line_count=line_count, token_count=token_count)


def _csv_cell_is_unsafe(value: str, limits: IngestionLimits) -> bool:
    stripped = value.lstrip()
    return (
        len(value) > limits.max_csv_cell_chars
        or "\n" in value
        or "\r" in value
        or any(unicodedata.category(character) in _UNICODE_LINE_CATEGORIES for character in value)
        or bool(stripped)
        and stripped.startswith(_FORMULA_PREFIXES)
        or _HTML_TAG.search(value) is not None
        or "../" in stripped
        or "..\\" in stripped
        or stripped.startswith(("/", "\\"))
        or _DRIVE_PATH.match(stripped) is not None
        or stripped.casefold().startswith("file:")
    )


def csv_cell_is_safe(
    value: str,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
) -> bool:
    """Apply the exact P003 CSV-cell policy to an already decoded scalar value."""

    return (
        value == unicodedata.normalize("NFC", value)
        and "\ufeff" not in value
        and all(
            not (
                unicodedata.category(character) == "Cc" and character not in _ALLOWED_TEXT_CONTROLS
            )
            and character not in _BIDI_CONTROLS
            for character in value
        )
        and not _csv_cell_is_unsafe(value, limits)
    )


def _validate_csv(text: str, base: _TextStats, limits: IngestionLimits) -> _CsvStats:
    try:
        reader = csv.reader(io.StringIO(text, newline=""), dialect="excel", strict=True)
        header = next(reader)
        if not 2 <= len(header) <= limits.max_csv_columns:
            _reject(IntakeErrorCode.CSV_INVALID)
        normalized_header = [value.strip().casefold() for value in header]
        if any(not value for value in normalized_header) or len(set(normalized_header)) != len(
            normalized_header
        ):
            _reject(IntakeErrorCode.CSV_INVALID)
        if any(_csv_cell_is_unsafe(value, limits) for value in header):
            _reject(IntakeErrorCode.CSV_INJECTION)
        row_count = 0
        for row in reader:
            row_count += 1
            if row_count > limits.max_csv_rows or len(row) != len(header):
                _reject(IntakeErrorCode.CSV_INVALID)
            if any(_csv_cell_is_unsafe(value, limits) for value in row):
                _reject(IntakeErrorCode.CSV_INJECTION)
        if row_count == 0:
            _reject(IntakeErrorCode.CSV_INVALID)
    except (csv.Error, StopIteration):
        _reject(IntakeErrorCode.CSV_INVALID)
    return _CsvStats(
        line_count=base.line_count,
        token_count=base.token_count,
        row_count=row_count,
        column_count=len(header),
    )


def _exact_zip_container(data: bytes, limits: IngestionLimits) -> tuple[int, int, int]:
    if not data.startswith((_ZIP_LOCAL_SIGNATURE, _ZIP_EOCD_SIGNATURE)):
        _reject(IntakeErrorCode.TYPE_MISMATCH)
    offset = data.rfind(_ZIP_EOCD_SIGNATURE)
    if offset < 0 or offset + _ZIP_EOCD.size > len(data):
        _reject(IntakeErrorCode.ARCHIVE_INVALID)
    (
        signature,
        disk_number,
        central_disk,
        disk_entries,
        total_entries,
        central_size,
        central_offset,
        comment_length,
    ) = _ZIP_EOCD.unpack_from(data, offset)
    if (
        signature != _ZIP_EOCD_SIGNATURE
        or comment_length != 0
        or offset + _ZIP_EOCD.size != len(data)
    ):
        _reject(IntakeErrorCode.ARCHIVE_INVALID)
    if disk_number != 0 or central_disk != 0 or disk_entries != total_entries:
        _reject(IntakeErrorCode.ARCHIVE_UNSUPPORTED)
    if (
        total_entries == _ZIP64_SENTINEL_16
        or central_size == _ZIP64_SENTINEL_32
        or central_offset == _ZIP64_SENTINEL_32
    ):
        _reject(IntakeErrorCode.ARCHIVE_UNSUPPORTED)
    if central_offset + central_size != offset:
        _reject(IntakeErrorCode.ARCHIVE_INVALID)
    if (
        central_size > limits.max_central_directory_bytes
        or total_entries > limits.max_archive_members
    ):
        _reject(IntakeErrorCode.ARCHIVE_LIMIT)
    return total_entries, central_offset, central_size


def _validate_zip_flags(flags: int, compression: int) -> None:
    if flags & 0x2041:
        _reject(IntakeErrorCode.ARCHIVE_ENCRYPTED)
    if flags & ~_ALLOWED_ZIP_FLAGS or flags & 0x8:
        _reject(IntakeErrorCode.ARCHIVE_UNSUPPORTED)
    if compression == zipfile.ZIP_STORED and flags & 0x6:
        _reject(IntakeErrorCode.ARCHIVE_UNSUPPORTED)


def _decode_zip_name(raw_name: bytes, flags: int) -> str:
    try:
        decoded = raw_name.decode("utf-8" if flags & 0x800 else "cp437")
    except UnicodeDecodeError:
        _reject(IntakeErrorCode.ARCHIVE_UNSAFE_PATH)
    if any(byte >= 0x80 for byte in raw_name) and not flags & 0x800:
        _reject(IntakeErrorCode.ARCHIVE_UNSAFE_PATH)
    return decoded


def _parse_central_entries(
    data: bytes,
    total_entries: int,
    central_offset: int,
    central_size: int,
    limits: IngestionLimits,
) -> tuple[_CentralEntry, ...]:
    entries: list[_CentralEntry] = []
    position = central_offset
    central_end = central_offset + central_size
    for index in range(total_entries):
        if position + _ZIP_CENTRAL.size > central_end:
            _reject(IntakeErrorCode.ARCHIVE_INVALID)
        (
            signature,
            version_made,
            version_needed,
            flags,
            compression,
            modified_time,
            modified_date,
            crc32,
            compressed_size,
            file_size,
            filename_length,
            extra_length,
            comment_length,
            disk_start,
            _internal_attr,
            external_attr,
            local_offset,
        ) = _ZIP_CENTRAL.unpack_from(data, position)
        if signature != _ZIP_CENTRAL_SIGNATURE:
            _reject(IntakeErrorCode.ARCHIVE_INVALID)
        variable_start = position + _ZIP_CENTRAL.size
        variable_end = variable_start + filename_length + extra_length + comment_length
        if variable_end > central_end or extra_length != 0 or comment_length != 0:
            _reject(IntakeErrorCode.ARCHIVE_UNSUPPORTED)
        if (
            disk_start != 0
            or compressed_size == _ZIP64_SENTINEL_32
            or file_size == _ZIP64_SENTINEL_32
            or local_offset == _ZIP64_SENTINEL_32
        ):
            _reject(IntakeErrorCode.ARCHIVE_UNSUPPORTED)
        _validate_zip_flags(flags, compression)
        if compression not in _SUPPORTED_COMPRESSION:
            _reject(IntakeErrorCode.ARCHIVE_UNSUPPORTED)
        raw_name = data[variable_start : variable_start + filename_length]
        decoded_name = _decode_zip_name(raw_name, flags)
        _validate_archive_path(decoded_name, decoded_name.endswith("/"), limits)
        entries.append(
            _CentralEntry(
                index=index,
                decoded_name=decoded_name,
                flags=flags,
                compression=compression,
                version_needed=version_needed,
                modified_time=modified_time,
                modified_date=modified_date,
                crc32=crc32,
                compressed_size=compressed_size,
                file_size=file_size,
                local_offset=local_offset,
                create_system=version_made >> 8,
                external_attr=external_attr,
            )
        )
        position = variable_end
    if position != central_end:
        _reject(IntakeErrorCode.ARCHIVE_INVALID)
    return tuple(entries)


def _validate_local_headers(data: bytes, entries: tuple[_CentralEntry, ...], central: int) -> None:
    ranges: list[tuple[int, int]] = []
    for entry in entries:
        if entry.local_offset + _ZIP_LOCAL.size > central:
            _reject(IntakeErrorCode.ARCHIVE_INVALID)
        (
            signature,
            version_needed,
            flags,
            compression,
            modified_time,
            modified_date,
            crc32,
            compressed_size,
            file_size,
            filename_length,
            extra_length,
        ) = _ZIP_LOCAL.unpack_from(data, entry.local_offset)
        name_start = entry.local_offset + _ZIP_LOCAL.size
        name_end = name_start + filename_length
        data_start = name_end + extra_length
        data_end = data_start + compressed_size
        if (
            signature != _ZIP_LOCAL_SIGNATURE
            or version_needed != entry.version_needed
            or flags != entry.flags
            or compression != entry.compression
            or modified_time != entry.modified_time
            or modified_date != entry.modified_date
            or crc32 != entry.crc32
            or compressed_size != entry.compressed_size
            or file_size != entry.file_size
            or extra_length != 0
            or data_end > central
            or _decode_zip_name(data[name_start:name_end], flags) != entry.decoded_name
        ):
            _reject(IntakeErrorCode.ARCHIVE_INVALID)
        ranges.append((entry.local_offset, data_end))
    ordered = sorted(ranges)
    expected_start = 0
    for start, end in ordered:
        if start != expected_start or end < start:
            _reject(IntakeErrorCode.ARCHIVE_INVALID)
        expected_start = end
    if expected_start != central:
        _reject(IntakeErrorCode.ARCHIVE_INVALID)


def _validate_archive_path(name: str, is_directory: bool, limits: IngestionLimits) -> str:
    candidate = name[:-1] if is_directory and name.endswith("/") else name
    try:
        encoded = name.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        _reject(IntakeErrorCode.ARCHIVE_UNSAFE_PATH)
    if (
        not candidate
        or name != unicodedata.normalize("NFC", name)
        or "\\" in name
        or ":" in name
        or "<" in name
        or ">" in name
        or "\x00" in name
        or any(unicodedata.category(character) in _UNSAFE_LABEL_CATEGORIES for character in name)
        or name.startswith("/")
        or "//" in name
        or len(encoded) > limits.max_path_bytes
    ):
        _reject(IntakeErrorCode.ARCHIVE_UNSAFE_PATH)
    path = PurePosixPath(candidate)
    if (
        path.as_posix() != candidate
        or len(path.parts) > limits.max_path_depth
        or any(not _safe_part(part) for part in path.parts)
    ):
        _reject(IntakeErrorCode.ARCHIVE_UNSAFE_PATH)
    return path.as_posix()


def _member_is_regular(entry: _CentralEntry, is_directory: bool) -> bool:
    mode = (entry.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    if entry.create_system != 3:
        return True
    if is_directory:
        return file_type in {0, stat.S_IFDIR}
    return file_type in {0, stat.S_IFREG}


def _read_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limits: IngestionLimits) -> bytes:
    payload = bytearray()
    try:
        with archive.open(info, mode="r") as source:
            while True:
                chunk = source.read(limits.read_chunk_bytes)
                if not chunk:
                    break
                payload.extend(chunk)
                if len(payload) > limits.max_member_bytes:
                    _reject(IntakeErrorCode.ARCHIVE_LIMIT)
    except IntakeError:
        raise
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, EOFError):
        _reject(IntakeErrorCode.ARCHIVE_INVALID)
    if len(payload) != info.file_size:
        _reject(IntakeErrorCode.ARCHIVE_INVALID)
    return bytes(payload)


def _inspect_archive(
    data: bytes,
    limits: IngestionLimits,
    batch_expanded_budget: int | None = None,
) -> _ArchiveInspection:
    declared_entries, central_offset, central_size = _exact_zip_container(data, limits)
    central_entries = _parse_central_entries(
        data, declared_entries, central_offset, central_size, limits
    )
    _validate_local_headers(data, central_entries, central_offset)
    try:
        archive = zipfile.ZipFile(io.BytesIO(data), mode="r")
    except (zipfile.BadZipFile, OSError):
        _reject(IntakeErrorCode.ARCHIVE_INVALID)
    with archive:
        infos = archive.infolist()
        if len(infos) != declared_entries or len(infos) != len(central_entries):
            _reject(IntakeErrorCode.ARCHIVE_INVALID)
        seen: set[str] = set()
        file_paths: set[str] = set()
        plans: list[tuple[int, str, zipfile.ZipInfo]] = []
        expanded_bytes = 0
        for index, (entry, info) in enumerate(zip(central_entries, infos, strict=True)):
            if (
                info.orig_filename != entry.decoded_name
                or info.filename != entry.decoded_name
                or info.flag_bits != entry.flags
                or info.compress_type != entry.compression
                or info.CRC != entry.crc32
                or info.compress_size != entry.compressed_size
                or info.file_size != entry.file_size
                or info.header_offset != entry.local_offset
            ):
                _reject(IntakeErrorCode.ARCHIVE_INVALID)
            if not _member_is_regular(entry, info.is_dir()):
                _reject(IntakeErrorCode.ARCHIVE_UNSAFE_TYPE)
            safe_path = _validate_archive_path(info.filename, info.is_dir(), limits)
            normalized = unicodedata.normalize(
                "NFC", unicodedata.normalize("NFC", safe_path).casefold()
            )
            if normalized in seen:
                _reject(IntakeErrorCode.ARCHIVE_DUPLICATE)
            seen.add(normalized)
            if info.is_dir():
                if info.file_size != 0:
                    _reject(IntakeErrorCode.ARCHIVE_INVALID)
                continue
            if any(normalized.startswith(f"{file_path}/") for file_path in file_paths):
                _reject(IntakeErrorCode.ARCHIVE_UNSAFE_PATH)
            if safe_path.casefold().endswith(".zip"):
                _reject(IntakeErrorCode.NESTED_ARCHIVE)
            if not safe_path.casefold().endswith(".txt"):
                _reject(IntakeErrorCode.ARCHIVE_UNSUPPORTED)
            if info.file_size > limits.max_member_bytes:
                _reject(IntakeErrorCode.ARCHIVE_LIMIT)
            if info.file_size > 0 and (
                info.compress_size == 0
                or info.file_size / info.compress_size > limits.max_compression_ratio
            ):
                _reject(IntakeErrorCode.ARCHIVE_LIMIT)
            expanded_bytes += info.file_size
            if expanded_bytes > limits.max_archive_expanded_bytes:
                _reject(IntakeErrorCode.ARCHIVE_LIMIT)
            if batch_expanded_budget is not None and expanded_bytes > batch_expanded_budget:
                _reject(IntakeErrorCode.BATCH_LIMIT)
            file_paths.add(normalized)
            plans.append((index, safe_path, info))
        if any(
            other.startswith(f"{file_path}/")
            for file_path in file_paths
            for other in seen
            if other != file_path
        ):
            _reject(IntakeErrorCode.ARCHIVE_UNSAFE_PATH)
        if not plans:
            _reject(IntakeErrorCode.ARCHIVE_INVALID)
        members: list[_ArchiveMember] = []
        actual_expanded = 0
        for index, safe_path, info in plans:
            member_data = _read_member(archive, info, limits)
            if _looks_like_zip(member_data):
                _reject(IntakeErrorCode.NESTED_ARCHIVE)
            _, stats = _decode_text(member_data, limits)
            actual_expanded += len(member_data)
            if actual_expanded > limits.max_archive_expanded_bytes:
                _reject(IntakeErrorCode.ARCHIVE_LIMIT)
            if batch_expanded_budget is not None and actual_expanded > batch_expanded_budget:
                _reject(IntakeErrorCode.BATCH_LIMIT)
            members.append(
                _ArchiveMember(
                    index=index,
                    display_label=safe_path,
                    file_size=len(member_data),
                    line_count=stats.line_count,
                    token_count=stats.token_count,
                    sha256=hashlib.sha256(member_data).hexdigest(),
                )
            )
    return _ArchiveInspection(members=tuple(members), expanded_bytes=actual_expanded)


def _validated_upload(
    request: IncomingUpload,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
    id_factory: AssetIdFactory | None = None,
    batch_expanded_budget: int | None = None,
) -> tuple[IntakeReceipt, _ArchiveInspection | None]:

    label = _validate_common(request, limits)
    asset_id = _asset_id(id_factory)
    digest = hashlib.sha256(request.data).hexdigest()
    extension = _ROLE_EXTENSION[request.role]
    if request.role is IntakeRole.CORPUS_ARCHIVE:
        inspection = _inspect_archive(request.data, limits, batch_expanded_budget)
        return (
            IntakeReceipt(
                asset_id=asset_id,
                role=request.role,
                display_label=label,
                storage_name=f"{asset_id}{extension}",
                byte_size=len(request.data),
                expanded_bytes=inspection.expanded_bytes,
                sha256=digest,
                member_count=len(inspection.members),
                limit_profile=limits.profile_version,
            ),
            inspection,
        )
    if batch_expanded_budget is not None and len(request.data) > batch_expanded_budget:
        _reject(IntakeErrorCode.BATCH_LIMIT)
    text, text_stats = _decode_text(request.data, limits)
    if request.role is IntakeRole.METADATA_CSV:
        csv_stats = _validate_csv(text, text_stats, limits)
        return (
            IntakeReceipt(
                asset_id=asset_id,
                role=request.role,
                display_label=label,
                storage_name=f"{asset_id}{extension}",
                byte_size=len(request.data),
                expanded_bytes=len(request.data),
                sha256=digest,
                line_count=csv_stats.line_count,
                token_count=csv_stats.token_count,
                row_count=csv_stats.row_count,
                column_count=csv_stats.column_count,
                limit_profile=limits.profile_version,
            ),
            None,
        )
    return (
        IntakeReceipt(
            asset_id=asset_id,
            role=request.role,
            display_label=label,
            storage_name=f"{asset_id}{extension}",
            byte_size=len(request.data),
            expanded_bytes=len(request.data),
            sha256=digest,
            line_count=text_stats.line_count,
            token_count=text_stats.token_count,
            limit_profile=limits.profile_version,
        ),
        None,
    )


def validate_upload(
    request: IncomingUpload,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
    id_factory: AssetIdFactory | None = None,
) -> IntakeReceipt:
    """Validate one role-declared upload without writing payload bytes."""

    try:
        receipt, _inspection = _validated_upload(
            request,
            limits=limits,
            id_factory=id_factory,
        )
    except IntakeError as error:
        _detach_error_context(error)
        raise
    return receipt


def _validated_batch(
    requests: Sequence[IncomingUpload],
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
    id_factory: AssetIdFactory | None = None,
) -> tuple[IntakeReceipt, ...]:
    if not requests:
        _reject(IntakeErrorCode.EMPTY)
    if (
        len(requests) > limits.max_batch_files
        or sum(len(item.data) for item in requests) > limits.max_batch_bytes
    ):
        _reject(IntakeErrorCode.BATCH_LIMIT)
    if sum(item.role is IntakeRole.METADATA_CSV for item in requests) > 1:
        _reject(IntakeErrorCode.ROLE_MISMATCH)
    labels = [unicodedata.normalize("NFC", item.display_label).casefold() for item in requests]
    if len(set(labels)) != len(labels):
        _reject(IntakeErrorCode.DUPLICATE_LABEL)
    receipts: list[IntakeReceipt] = []
    identifiers: set[str] = set()
    expanded = 0
    for item in requests:
        remaining = limits.max_batch_expanded_bytes - expanded
        receipt, _inspection = _validated_upload(
            item,
            limits=limits,
            id_factory=id_factory,
            batch_expanded_budget=remaining,
        )
        if receipt.asset_id in identifiers:
            _reject(IntakeErrorCode.INTERNAL_ID)
        identifiers.add(receipt.asset_id)
        expanded += receipt.expanded_bytes
        if expanded > limits.max_batch_expanded_bytes:
            _reject(IntakeErrorCode.BATCH_LIMIT)
        receipts.append(receipt)
    return tuple(receipts)


def validate_batch(
    requests: Sequence[IncomingUpload],
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
    id_factory: AssetIdFactory | None = None,
) -> tuple[IntakeReceipt, ...]:
    """Validate an all-or-nothing upload batch without retaining payloads."""

    try:
        return _validated_batch(requests, limits=limits, id_factory=id_factory)
    except IntakeError as error:
        _detach_error_context(error)
        raise


def _cleanup_workspace(workspace: Path) -> None:
    if not workspace.exists():
        return
    try:
        shutil.rmtree(workspace)
    except OSError:
        _reject(IntakeErrorCode.CLEANUP_FAILED)


def _secure_extract_archive(
    request: IncomingUpload,
    trusted_root: Path,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
    id_factory: AssetIdFactory | None = None,
) -> ExtractedArchive:
    if request.role is not IntakeRole.CORPUS_ARCHIVE:
        _reject(IntakeErrorCode.ROLE_MISMATCH)
    if not trusted_root.is_dir() or trusted_root.is_symlink():
        _reject(IntakeErrorCode.WORKSPACE_INVALID)
    _receipt, maybe_inspection = _validated_upload(
        request,
        limits=limits,
        id_factory=id_factory,
    )
    inspection = cast(_ArchiveInspection, maybe_inspection)
    workspace = trusted_root / f"workspace_{_token(id_factory)}"
    try:
        workspace.mkdir(mode=0o700, exist_ok=False)
    except OSError:
        _reject(IntakeErrorCode.WORKSPACE_INVALID)
    receipts: list[IntakeReceipt] = []
    try:
        with zipfile.ZipFile(io.BytesIO(request.data), mode="r") as archive:
            infos = archive.infolist()
            for member in inspection.members:
                info = infos[member.index]
                payload = _read_member(archive, info, limits)
                if hashlib.sha256(payload).hexdigest() != member.sha256:
                    _reject(IntakeErrorCode.EXTRACTION_FAILED)
                asset_id = _asset_id(id_factory)
                storage_name = f"{asset_id}.txt"
                target = workspace / storage_name
                flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
                descriptor = os.open(target, flags, 0o600)
                with os.fdopen(descriptor, "wb") as handle:
                    written = handle.write(payload)
                    if written != len(payload):
                        _reject(IntakeErrorCode.EXTRACTION_FAILED)
                receipts.append(
                    IntakeReceipt(
                        asset_id=asset_id,
                        role=IntakeRole.CORPUS_TEXT,
                        display_label=member.display_label,
                        storage_name=storage_name,
                        byte_size=len(payload),
                        expanded_bytes=len(payload),
                        sha256=hashlib.sha256(payload).hexdigest(),
                        line_count=member.line_count,
                        token_count=member.token_count,
                        limit_profile=limits.profile_version,
                    )
                )
    except IntakeError:
        _cleanup_workspace(workspace)
        raise
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, EOFError):
        _cleanup_workspace(workspace)
        _reject(IntakeErrorCode.EXTRACTION_FAILED)
    return ExtractedArchive(workspace=workspace, members=tuple(receipts))


def secure_extract_archive(
    request: IncomingUpload,
    trusted_root: Path,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
    id_factory: AssetIdFactory | None = None,
) -> ExtractedArchive:
    """Validate and extract a corpus archive into server-generated flat storage names."""

    try:
        return _secure_extract_archive(
            request,
            trusted_root,
            limits=limits,
            id_factory=id_factory,
        )
    except IntakeError as error:
        _detach_error_context(error)
        raise
