from __future__ import annotations

import io
import os
import stat
import struct
import traceback
import warnings
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

import delta_lemmata.ingestion as ingestion
from delta_lemmata.ingestion import (
    DEFAULT_LIMITS,
    ExtractedArchive,
    IncomingUpload,
    IngestionLimits,
    IntakeError,
    IntakeErrorCode,
    IntakeRole,
    secure_extract_archive,
    validate_batch,
    validate_upload,
)


def limits(**updates: int | float | str) -> IngestionLimits:
    values = DEFAULT_LIMITS.model_dump()
    values.update(updates)
    return IngestionLimits.model_validate(values)


def expect_code(code: IntakeErrorCode, action: Callable[[], object]) -> IntakeError:
    with pytest.raises(IntakeError) as captured:
        action()
    assert captured.value.code is code
    assert str(captured.value) == code.value
    return captured.value


def archive_request(data: bytes, name: str = "corpus.zip") -> IncomingUpload:
    return IncomingUpload(IntakeRole.CORPUS_ARCHIVE, name, data, "application/zip")


def make_zip(
    entries: list[tuple[str | zipfile.ZipInfo, bytes]],
    *,
    compression: int = zipfile.ZIP_DEFLATED,
    comment: bytes = b"",
) -> bytes:
    output = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(output, mode="w", compression=compression) as archive:
            archive.comment = comment
            for name, payload in entries:
                archive.writestr(name, payload)
    return output.getvalue()


def zip_positions(data: bytes) -> tuple[int, int]:
    eocd = data.rfind(b"PK\x05\x06")
    central = struct.unpack_from("<L", data, eocd + 16)[0]
    return central, eocd


def mutate_u16(data: bytes, offset: int, value: int) -> bytes:
    changed = bytearray(data)
    struct.pack_into("<H", changed, offset, value)
    return bytes(changed)


def mutate_u32(data: bytes, offset: int, value: int) -> bytes:
    changed = bytearray(data)
    struct.pack_into("<L", changed, offset, value)
    return bytes(changed)


def id_sequence(*values: str) -> Callable[[], str]:
    iterator: Iterator[str] = iter(values)
    return lambda: next(iterator)


def test_valid_archive_is_preflighted_and_content_free() -> None:
    payload = make_zip([("author/one.txt", b"one text\n"), ("author/two.txt", b"two text\n")])
    receipt = validate_upload(
        archive_request(payload),
        id_factory=lambda: "0" * 32,
    )
    assert receipt.role is IntakeRole.CORPUS_ARCHIVE
    assert receipt.member_count == 2
    assert receipt.expanded_bytes == 18
    assert receipt.storage_name == f"asset_{'0' * 32}.zip"
    assert "one text" not in repr(receipt)


def test_valid_directory_inventory_is_not_materialized(tmp_path: Path) -> None:
    directory = zipfile.ZipInfo("author/")
    directory.create_system = 3
    directory.external_attr = (stat.S_IFDIR | 0o755) << 16
    payload = make_zip([(directory, b""), ("author/work.txt", b"text")])
    ids = id_sequence("0" * 32, "1" * 32, "2" * 32)
    bundle = secure_extract_archive(archive_request(payload), tmp_path, id_factory=ids)
    assert bundle.workspace.name == f"workspace_{'1' * 32}"
    assert len(bundle.members) == 1
    member = bundle.members[0]
    assert member.display_label == "author/work.txt"
    assert member.storage_name == f"asset_{'2' * 32}.txt"
    assert (bundle.workspace / member.storage_name).read_bytes() == b"text"
    assert not (bundle.workspace / "author").exists()
    bundle.cleanup()
    bundle.cleanup()
    assert not bundle.workspace.exists()


def test_extracted_archive_context_cleans_successful_workspace(tmp_path: Path) -> None:
    payload = make_zip([("work.txt", b"content")])
    ids = id_sequence("0" * 32, "1" * 32, "2" * 32)
    with secure_extract_archive(archive_request(payload), tmp_path, id_factory=ids) as bundle:
        workspace = bundle.workspace
        assert workspace.exists()
    assert not workspace.exists()


@pytest.mark.parametrize(
    ("transform", "code"),
    [
        (lambda data: b"prefix" + data, IntakeErrorCode.TYPE_MISMATCH),
        (lambda data: data + b"suffix", IntakeErrorCode.ARCHIVE_INVALID),
        (
            lambda data: make_zip([("work.txt", b"text")], comment=b"comment"),
            IntakeErrorCode.ARCHIVE_INVALID,
        ),
    ],
)
def test_prefixed_suffixed_and_commented_archives_are_rejected(
    transform: Callable[[bytes], bytes], code: IntakeErrorCode
) -> None:
    original = make_zip([("work.txt", b"text")])
    expect_code(
        code,
        lambda: validate_upload(archive_request(transform(original)), id_factory=lambda: "0" * 32),
    )


def test_eocd_limits_split_and_zip64_are_rejected_before_zipfile() -> None:
    payload = make_zip([("work.txt", b"text")])
    _, eocd = zip_positions(payload)
    fixtures = (
        (mutate_u16(payload, eocd + 4, 1), IntakeErrorCode.ARCHIVE_UNSUPPORTED),
        (mutate_u16(payload, eocd + 10, 0xFFFF), IntakeErrorCode.ARCHIVE_UNSUPPORTED),
        (mutate_u32(payload, eocd + 16, 0xFFFFFFFF), IntakeErrorCode.ARCHIVE_UNSUPPORTED),
    )
    for fixture, code in fixtures:
        expect_code(
            code,
            lambda fixture=fixture: validate_upload(
                archive_request(fixture), id_factory=lambda: "0" * 32
            ),
        )
    expect_code(
        IntakeErrorCode.ARCHIVE_LIMIT,
        lambda: validate_upload(
            archive_request(payload),
            limits=limits(max_archive_members=0 + 1, max_central_directory_bytes=8),
            id_factory=lambda: "0" * 32,
        ),
    )


def test_raw_zip_parser_rejects_truncated_and_inexact_directory_structures() -> None:
    expect_code(
        IntakeErrorCode.ARCHIVE_INVALID,
        lambda: ingestion._exact_zip_container(b"PK\x05\x06", DEFAULT_LIMITS),
    )
    expect_code(
        IntakeErrorCode.ARCHIVE_INVALID,
        lambda: ingestion._parse_central_entries(b"", 1, 0, 0, DEFAULT_LIMITS),
    )
    expect_code(
        IntakeErrorCode.ARCHIVE_INVALID,
        lambda: ingestion._parse_central_entries(
            b"\x00" * ingestion._ZIP_CENTRAL.size,
            1,
            0,
            ingestion._ZIP_CENTRAL.size,
            DEFAULT_LIMITS,
        ),
    )

    payload = make_zip([("work.txt", b"text")])
    central, eocd = zip_positions(payload)
    central_record = payload[central:eocd]
    expect_code(
        IntakeErrorCode.ARCHIVE_INVALID,
        lambda: ingestion._parse_central_entries(
            central_record + b"x",
            1,
            0,
            len(central_record) + 1,
            DEFAULT_LIMITS,
        ),
    )


def test_central_disk_start_is_rejected_as_unsupported() -> None:
    payload = make_zip([("work.txt", b"text")])
    central, _ = zip_positions(payload)
    changed = mutate_u16(payload, central + 34, 1)
    expect_code(
        IntakeErrorCode.ARCHIVE_UNSUPPORTED,
        lambda: validate_upload(archive_request(changed), id_factory=lambda: "0" * 32),
    )


def test_central_member_count_limit_is_checked_before_zipfile() -> None:
    payload = make_zip([("one.txt", b"one"), ("two.txt", b"two")])
    expect_code(
        IntakeErrorCode.ARCHIVE_LIMIT,
        lambda: validate_upload(
            archive_request(payload),
            limits=limits(max_archive_members=1),
            id_factory=lambda: "0" * 32,
        ),
    )


def test_local_and_central_headers_must_match_exactly() -> None:
    payload = make_zip([("work.txt", b"text")])
    central, eocd = zip_positions(payload)
    mismatches = (
        mutate_u16(payload, 4, struct.unpack_from("<H", payload, 4)[0] ^ 1),
        mutate_u16(payload, 8, zipfile.ZIP_STORED),
        mutate_u16(payload, 10, struct.unpack_from("<H", payload, 10)[0] ^ 1),
        mutate_u16(payload, 12, struct.unpack_from("<H", payload, 12)[0] ^ 1),
        mutate_u32(payload, 14, 1234),
        mutate_u32(payload, eocd + 16, central - 1),
    )
    for fixture in mismatches:
        expect_code(
            IntakeErrorCode.ARCHIVE_INVALID,
            lambda fixture=fixture: validate_upload(
                archive_request(fixture), id_factory=lambda: "0" * 32
            ),
        )


def test_gap_between_members_and_central_directory_is_rejected() -> None:
    payload = make_zip([("work.txt", b"text")])
    central, eocd = zip_positions(payload)
    changed = bytearray(payload[:central] + b"x" + payload[central:])
    struct.pack_into("<L", changed, eocd + 1 + 16, central + 1)
    expect_code(
        IntakeErrorCode.ARCHIVE_INVALID,
        lambda: validate_upload(archive_request(bytes(changed)), id_factory=lambda: "0" * 32),
    )


def test_local_header_bounds_and_leading_gaps_are_rejected() -> None:
    entry = ingestion._CentralEntry(
        index=0,
        decoded_name="work.txt",
        flags=0,
        compression=zipfile.ZIP_STORED,
        version_needed=20,
        modified_time=0,
        modified_date=0,
        crc32=0,
        compressed_size=0,
        file_size=0,
        local_offset=0,
        create_system=0,
        external_attr=0,
    )
    expect_code(
        IntakeErrorCode.ARCHIVE_INVALID,
        lambda: ingestion._validate_local_headers(b"", (entry,), 0),
    )

    name = b"work.txt"
    local_header = ingestion._ZIP_LOCAL.pack(
        ingestion._ZIP_LOCAL_SIGNATURE,
        20,
        0,
        zipfile.ZIP_STORED,
        0,
        0,
        0,
        0,
        0,
        len(name),
        0,
    )
    gapped_data = b"x" + local_header + name
    gapped_entry = ingestion._CentralEntry(
        index=0,
        decoded_name="work.txt",
        flags=0,
        compression=zipfile.ZIP_STORED,
        version_needed=20,
        modified_time=0,
        modified_date=0,
        crc32=0,
        compressed_size=0,
        file_size=0,
        local_offset=1,
        create_system=0,
        external_attr=0,
    )
    expect_code(
        IntakeErrorCode.ARCHIVE_INVALID,
        lambda: ingestion._validate_local_headers(gapped_data, (gapped_entry,), len(gapped_data)),
    )


def test_zipfile_constructor_failure_is_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = make_zip([("work.txt", b"text")])

    def fail_zipfile(*_args: object, **_kwargs: object) -> None:
        sensitive_context = "SECRET_ARCHIVE_PATH"
        raise zipfile.BadZipFile(sensitive_context)

    monkeypatch.setattr(ingestion.zipfile, "ZipFile", fail_zipfile)
    error = expect_code(
        IntakeErrorCode.ARCHIVE_INVALID,
        lambda: validate_upload(archive_request(payload), id_factory=lambda: "0" * 32),
    )
    assert error.__context__ is None
    assert error.__cause__ is None
    assert "SECRET_ARCHIVE_PATH" not in "".join(traceback.format_exception(error))


@pytest.mark.parametrize(
    "infos",
    [(), (SimpleNamespace(orig_filename="different.txt"),)],
)
def test_zipfile_inventory_must_match_raw_headers(
    infos: tuple[object, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = make_zip([("work.txt", b"text")])

    class Archive:
        def __enter__(self) -> Archive:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def infolist(self) -> tuple[object, ...]:
            return infos

    monkeypatch.setattr(ingestion.zipfile, "ZipFile", lambda *_args, **_kwargs: Archive())
    expect_code(
        IntakeErrorCode.ARCHIVE_INVALID,
        lambda: validate_upload(archive_request(payload), id_factory=lambda: "0" * 32),
    )


@pytest.mark.parametrize(
    ("flag", "code"),
    [
        (0x1, IntakeErrorCode.ARCHIVE_ENCRYPTED),
        (0x40, IntakeErrorCode.ARCHIVE_ENCRYPTED),
        (0x2000, IntakeErrorCode.ARCHIVE_ENCRYPTED),
        (0x8, IntakeErrorCode.ARCHIVE_UNSUPPORTED),
        (0x10, IntakeErrorCode.ARCHIVE_UNSUPPORTED),
    ],
)
def test_encryption_data_descriptors_and_unknown_flags_are_rejected(
    flag: int, code: IntakeErrorCode
) -> None:
    payload = make_zip([("work.txt", b"text")])
    central, _ = zip_positions(payload)
    changed = mutate_u16(payload, central + 8, flag)
    expect_code(
        code,
        lambda: validate_upload(archive_request(changed), id_factory=lambda: "0" * 32),
    )


def test_stored_archive_cannot_claim_deflate_option_flags() -> None:
    payload = make_zip([("work.txt", b"text")], compression=zipfile.ZIP_STORED)
    central, _ = zip_positions(payload)
    changed = mutate_u16(payload, central + 8, 0x2)
    expect_code(
        IntakeErrorCode.ARCHIVE_UNSUPPORTED,
        lambda: validate_upload(archive_request(changed), id_factory=lambda: "0" * 32),
    )


def test_unsupported_compression_and_extra_fields_are_rejected() -> None:
    bzip = make_zip([("work.txt", b"text")], compression=zipfile.ZIP_BZIP2)
    extra = zipfile.ZipInfo("work.txt")
    extra.extra = struct.pack("<HH", 0x000D, 0)
    hardlink_like = make_zip([(extra, b"text")])
    for fixture in (bzip, hardlink_like):
        expect_code(
            IntakeErrorCode.ARCHIVE_UNSUPPORTED,
            lambda fixture=fixture: validate_upload(
                archive_request(fixture), id_factory=lambda: "0" * 32
            ),
        )


def test_central_comments_and_unknown_methods_are_rejected() -> None:
    payload = make_zip([("work.txt", b"text")])
    central, _ = zip_positions(payload)
    central_comment = mutate_u16(payload, central + 32, 1)
    unknown_method = mutate_u16(payload, central + 10, 99)
    expect_code(
        IntakeErrorCode.ARCHIVE_UNSUPPORTED,
        lambda: validate_upload(archive_request(central_comment), id_factory=lambda: "0" * 32),
    )
    expect_code(
        IntakeErrorCode.ARCHIVE_UNSUPPORTED,
        lambda: validate_upload(archive_request(unknown_method), id_factory=lambda: "0" * 32),
    )


@pytest.mark.parametrize(
    "name",
    [
        "../x.txt",
        "/x.txt",
        "C:x.txt",
        "C:/x.txt",
        "\\\\server\\x.txt",
        "\\\\?\\C:\\x.txt",
        "x.txt:stream",
        "good//x.txt",
        "./x.txt",
        ".hidden.txt",
        "CON.txt",
        "COM¹.txt",
        "trailing.txt.",
        "__MACOSX/x.txt",
        "a/b/c/d.txt",
        "<script>.txt",
        "bad\nname.txt",
        "bad\u202ename.txt",
        "bad\u2028name.txt",
        "bad\u2029name.txt",
    ],
)
def test_archive_paths_are_canonical_and_cross_platform_safe(name: str) -> None:
    payload = make_zip([(name, b"text")])
    expect_code(
        IntakeErrorCode.ARCHIVE_UNSAFE_PATH,
        lambda: validate_upload(archive_request(payload), id_factory=lambda: "0" * 32),
    )


def test_path_byte_limit_and_non_utf8_name_are_rejected() -> None:
    payload = make_zip([("longname.txt", b"text")])
    expect_code(
        IntakeErrorCode.ARCHIVE_UNSAFE_PATH,
        lambda: validate_upload(
            archive_request(payload),
            limits=limits(max_path_bytes=5),
            id_factory=lambda: "0" * 32,
        ),
    )
    central, _ = zip_positions(payload)
    changed = bytearray(payload)
    changed[30] = 0x82
    changed[central + 46] = 0x82
    expect_code(
        IntakeErrorCode.ARCHIVE_UNSAFE_PATH,
        lambda: validate_upload(archive_request(bytes(changed)), id_factory=lambda: "0" * 32),
    )
    expect_code(
        IntakeErrorCode.ARCHIVE_UNSAFE_PATH,
        lambda: ingestion._validate_archive_path("bad\ud800.txt", False, DEFAULT_LIMITS),
    )


def test_invalid_utf8_and_nul_raw_names_are_rejected_before_zipinfo_truncation() -> None:
    payload = make_zip([("work.txt", b"text")])
    central, _ = zip_positions(payload)
    invalid_utf8 = bytearray(payload)
    struct.pack_into("<H", invalid_utf8, 6, 0x800)
    struct.pack_into("<H", invalid_utf8, central + 8, 0x800)
    invalid_utf8[30] = 0xFF
    invalid_utf8[central + 46] = 0xFF
    expect_code(
        IntakeErrorCode.ARCHIVE_UNSAFE_PATH,
        lambda: validate_upload(archive_request(bytes(invalid_utf8)), id_factory=lambda: "0" * 32),
    )
    nul_name = bytearray(payload)
    nul_name[30] = 0
    nul_name[central + 46] = 0
    expect_code(
        IntakeErrorCode.ARCHIVE_UNSAFE_PATH,
        lambda: validate_upload(archive_request(bytes(nul_name)), id_factory=lambda: "0" * 32),
    )


@pytest.mark.parametrize(
    ("names", "code"),
    [
        (["same.txt", "same.txt"], IntakeErrorCode.ARCHIVE_DUPLICATE),
        (["A.txt", "a.txt"], IntakeErrorCode.ARCHIVE_DUPLICATE),
        (["Straße.txt", "STRASSE.txt"], IntakeErrorCode.ARCHIVE_DUPLICATE),
        (["café.txt", "café.txt"], IntakeErrorCode.ARCHIVE_UNSAFE_PATH),
        (["author.txt", "author.txt/work.txt"], IntakeErrorCode.ARCHIVE_UNSAFE_PATH),
        (["author.txt/work.txt", "author.txt"], IntakeErrorCode.ARCHIVE_UNSAFE_PATH),
    ],
)
def test_duplicate_normalized_names_and_prefix_collisions_fail(
    names: list[str], code: IntakeErrorCode
) -> None:
    payload = make_zip([(name, b"text") for name in names])
    expect_code(
        code,
        lambda: validate_upload(archive_request(payload), id_factory=lambda: "0" * 32),
    )


@pytest.mark.parametrize("mode", [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFBLK])
def test_non_regular_unix_members_are_rejected(mode: int) -> None:
    member = zipfile.ZipInfo("work.txt")
    member.create_system = 3
    member.external_attr = (mode | 0o777) << 16
    payload = make_zip([(member, b"target")])
    expect_code(
        IntakeErrorCode.ARCHIVE_UNSAFE_TYPE,
        lambda: validate_upload(archive_request(payload), id_factory=lambda: "0" * 32),
    )


def test_non_unix_regular_member_is_accepted() -> None:
    member = zipfile.ZipInfo("work.txt")
    member.create_system = 0
    payload = make_zip([(member, b"text")])
    receipt = validate_upload(archive_request(payload), id_factory=lambda: "0" * 32)
    assert receipt.member_count == 1


def test_empty_directory_payload_and_unsupported_members_are_rejected() -> None:
    directory_with_data = zipfile.ZipInfo("author/")
    directory_with_data.create_system = 3
    directory_with_data.external_attr = (stat.S_IFDIR | 0o755) << 16
    fixtures = (
        (make_zip([]), IntakeErrorCode.ARCHIVE_INVALID),
        (make_zip([("author/", b"")]), IntakeErrorCode.ARCHIVE_INVALID),
        (make_zip([(directory_with_data, b"x")]), IntakeErrorCode.ARCHIVE_INVALID),
        (make_zip([("metadata.csv", b"a,b\n1,2")]), IntakeErrorCode.ARCHIVE_UNSUPPORTED),
        (make_zip([("inner.zip", b"not-zip")]), IntakeErrorCode.NESTED_ARCHIVE),
    )
    for fixture, code in fixtures:
        expect_code(
            code,
            lambda fixture=fixture: validate_upload(
                archive_request(fixture), id_factory=lambda: "0" * 32
            ),
        )


def test_nested_zip_signature_and_invalid_member_text_are_rejected() -> None:
    inner = make_zip([("inside.txt", b"text")])
    fixtures = (
        (make_zip([("inner.txt", inner)]), IntakeErrorCode.NESTED_ARCHIVE),
        (make_zip([("bad.txt", b"\xff")]), IntakeErrorCode.INVALID_UTF8),
        (make_zip([("empty.txt", b"")]), IntakeErrorCode.TEXT_EMPTY),
    )
    for fixture, code in fixtures:
        expect_code(
            code,
            lambda fixture=fixture: validate_upload(
                archive_request(fixture), id_factory=lambda: "0" * 32
            ),
        )


def test_member_expanded_and_ratio_limits_are_enforced() -> None:
    payload = make_zip([("work.txt", b"a" * 1000)])
    profiles = (
        limits(max_member_bytes=999),
        limits(max_archive_expanded_bytes=999),
        limits(max_compression_ratio=2.0),
    )
    for profile in profiles:
        expect_code(
            IntakeErrorCode.ARCHIVE_LIMIT,
            lambda profile=profile: validate_upload(
                archive_request(payload), limits=profile, id_factory=lambda: "0" * 32
            ),
        )


def test_batch_archive_budget_is_rejected_before_member_decompression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = make_zip([("work.txt", b"four")])

    def forbidden_read(*_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("archive member decompressed before batch preflight")

    monkeypatch.setattr(ingestion, "_read_member", forbidden_read)
    ids = iter(("0" * 32, "1" * 32))
    error = expect_code(
        IntakeErrorCode.BATCH_LIMIT,
        lambda: validate_batch(
            [
                IncomingUpload(IntakeRole.CORPUS_TEXT, "one.txt", b"one"),
                archive_request(payload),
            ],
            limits=limits(max_batch_expanded_bytes=6),
            id_factory=lambda: next(ids),
        ),
    )
    assert error.__context__ is None


def test_runtime_expanded_counter_rechecks_declared_archive_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = make_zip([("work.txt", b"text")])
    real_read = ingestion._read_member

    def oversized_read(*args: Any, **kwargs: Any) -> bytes:
        return real_read(*args, **kwargs) + b"x"

    monkeypatch.setattr(ingestion, "_read_member", oversized_read)
    expect_code(
        IntakeErrorCode.ARCHIVE_LIMIT,
        lambda: validate_upload(
            archive_request(payload),
            limits=limits(max_archive_expanded_bytes=4),
            id_factory=lambda: "0" * 32,
        ),
    )


def test_runtime_expanded_counter_rechecks_batch_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = make_zip([("work.txt", b"text")])
    real_read = ingestion._read_member

    def oversized_read(*args: Any, **kwargs: Any) -> bytes:
        return real_read(*args, **kwargs) + b"x"

    monkeypatch.setattr(ingestion, "_read_member", oversized_read)
    error = expect_code(
        IntakeErrorCode.BATCH_LIMIT,
        lambda: validate_batch(
            [archive_request(payload)],
            limits=limits(max_batch_expanded_bytes=4),
            id_factory=lambda: "0" * 32,
        ),
    )
    assert error.__context__ is None


def test_read_member_enforces_runtime_limit_and_declared_size() -> None:
    class Source:
        def __init__(self, chunks: list[bytes] | None = None, error: Exception | None = None):
            self.chunks = iter(chunks or [])
            self.error = error

        def __enter__(self) -> Source:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def read(self, _size: int) -> bytes:
            if self.error is not None:
                raise self.error
            return next(self.chunks, b"")

    class Archive:
        def __init__(self, source: Source):
            self.source = source

        def open(self, _info: object, mode: str) -> Source:
            assert mode == "r"
            return self.source

    info = SimpleNamespace(file_size=2)
    expect_code(
        IntakeErrorCode.ARCHIVE_LIMIT,
        lambda: ingestion._read_member(
            cast(Any, Archive(Source([b"123"]))),
            cast(Any, info),
            limits(max_member_bytes=2, read_chunk_bytes=2),
        ),
    )
    expect_code(
        IntakeErrorCode.ARCHIVE_INVALID,
        lambda: ingestion._read_member(
            cast(Any, Archive(Source([b"1"]))), cast(Any, info), DEFAULT_LIMITS
        ),
    )
    expect_code(
        IntakeErrorCode.ARCHIVE_INVALID,
        lambda: ingestion._read_member(
            cast(Any, Archive(Source(error=OSError()))), cast(Any, info), DEFAULT_LIMITS
        ),
    )


def test_extraction_requires_archive_role_and_private_trusted_root(tmp_path: Path) -> None:
    text = IncomingUpload(IntakeRole.CORPUS_TEXT, "work.txt", b"text")
    expect_code(
        IntakeErrorCode.ROLE_MISMATCH,
        lambda: secure_extract_archive(text, tmp_path),
    )
    payload = make_zip([("work.txt", b"text")])
    expect_code(
        IntakeErrorCode.WORKSPACE_INVALID,
        lambda: secure_extract_archive(archive_request(payload), tmp_path / "missing"),
    )
    symlink = tmp_path / "link"
    symlink.symlink_to(tmp_path, target_is_directory=True)
    expect_code(
        IntakeErrorCode.WORKSPACE_INVALID,
        lambda: secure_extract_archive(archive_request(payload), symlink),
    )


def test_workspace_collision_is_content_free(tmp_path: Path) -> None:
    payload = make_zip([("work.txt", b"text")])
    (tmp_path / f"workspace_{'1' * 32}").mkdir()
    ids = id_sequence("0" * 32, "1" * 32)
    expect_code(
        IntakeErrorCode.WORKSPACE_INVALID,
        lambda: secure_extract_archive(archive_request(payload), tmp_path, id_factory=ids),
    )


def test_materialization_io_failure_removes_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = make_zip([("work.txt", b"text")])
    ids = id_sequence("0" * 32, "1" * 32, "2" * 32)

    real_open = os.open
    sensitive_context = "SECRET_SYSTEM_PATH"

    def fail_open(path: os.PathLike[str] | str, *args: Any, **kwargs: Any) -> int:
        if Path(path).name.startswith("asset_"):
            raise OSError(sensitive_context)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", fail_open)
    error = expect_code(
        IntakeErrorCode.EXTRACTION_FAILED,
        lambda: secure_extract_archive(archive_request(payload), tmp_path, id_factory=ids),
    )
    assert error.__context__ is None
    assert error.__cause__ is None
    assert sensitive_context not in "".join(traceback.format_exception(error))
    assert list(tmp_path.iterdir()) == []


def test_short_write_removes_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = make_zip([("work.txt", b"text")])
    ids = id_sequence("0" * 32, "1" * 32, "2" * 32)

    class ShortWriter:
        def __init__(self, descriptor: int):
            self.descriptor = descriptor

        def __enter__(self) -> ShortWriter:
            return self

        def __exit__(self, *_exc: object) -> None:
            os.close(self.descriptor)

        def write(self, data: bytes) -> int:
            return len(data) - 1

    monkeypatch.setattr(
        os,
        "fdopen",
        lambda descriptor, *_args, **_kwargs: ShortWriter(descriptor),
    )
    expect_code(
        IntakeErrorCode.EXTRACTION_FAILED,
        lambda: secure_extract_archive(archive_request(payload), tmp_path, id_factory=ids),
    )
    assert list(tmp_path.iterdir()) == []


def test_second_pass_hash_mismatch_is_rejected_and_cleaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = make_zip([("work.txt", b"text")])
    real_read = ingestion._read_member
    calls = 0

    def changed_read(*args: Any, **kwargs: Any) -> bytes:
        nonlocal calls
        calls += 1
        result = real_read(*args, **kwargs)
        return b"changed" if calls == 2 else result

    monkeypatch.setattr(ingestion, "_read_member", changed_read)
    ids = id_sequence("0" * 32, "1" * 32)
    expect_code(
        IntakeErrorCode.EXTRACTION_FAILED,
        lambda: secure_extract_archive(archive_request(payload), tmp_path, id_factory=ids),
    )
    assert calls == 2
    assert list(tmp_path.iterdir()) == []


def test_secure_extraction_reads_twice_and_scans_text_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = make_zip([("work.txt", b"text")])
    real_read = ingestion._read_member
    real_decode = ingestion._decode_text
    read_calls = 0
    text_scans = 0

    def counted_read(*args: Any, **kwargs: Any) -> bytes:
        nonlocal read_calls
        read_calls += 1
        return real_read(*args, **kwargs)

    def counted_decode(data: bytes, profile: IngestionLimits) -> tuple[str, ingestion._TextStats]:
        nonlocal text_scans
        text_scans += 1
        return real_decode(data, profile)

    monkeypatch.setattr(ingestion, "_read_member", counted_read)
    monkeypatch.setattr(ingestion, "_decode_text", counted_decode)
    ids = id_sequence("0" * 32, "1" * 32, "2" * 32)
    bundle = secure_extract_archive(archive_request(payload), tmp_path, id_factory=ids)
    assert read_calls == 2
    assert text_scans == 1
    bundle.cleanup()


def test_cleanup_failures_use_stable_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    bundle = ExtractedArchive(workspace=workspace, members=())
    monkeypatch.setattr(ingestion.shutil, "rmtree", lambda _path: (_ for _ in ()).throw(OSError()))
    error = expect_code(IntakeErrorCode.CLEANUP_FAILED, bundle.cleanup)
    assert error.__context__ is None
    assert error.__cause__ is None


def test_extraction_cleanup_failure_masks_payload_error_with_stable_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = make_zip([("work.txt", b"text")])
    ids = id_sequence("0" * 32, "1" * 32, "2" * 32)
    monkeypatch.setattr(os, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(ingestion.shutil, "rmtree", lambda _path: (_ for _ in ()).throw(OSError()))
    expect_code(
        IntakeErrorCode.CLEANUP_FAILED,
        lambda: secure_extract_archive(archive_request(payload), tmp_path, id_factory=ids),
    )


def test_cleanup_failure_masks_second_pass_integrity_error_with_stable_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = make_zip([("work.txt", b"text")])
    real_read = ingestion._read_member
    calls = 0

    def changed_read(*args: Any, **kwargs: Any) -> bytes:
        nonlocal calls
        calls += 1
        result = real_read(*args, **kwargs)
        return b"changed" if calls == 2 else result

    monkeypatch.setattr(ingestion, "_read_member", changed_read)
    monkeypatch.setattr(
        ingestion.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(OSError()),
    )
    ids = id_sequence("0" * 32, "1" * 32)
    error = expect_code(
        IntakeErrorCode.CLEANUP_FAILED,
        lambda: secure_extract_archive(archive_request(payload), tmp_path, id_factory=ids),
    )
    assert calls == 2
    assert error.__context__ is None
