from __future__ import annotations

import csv
import io
import random
import struct
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from delta_lemmata.ingestion import (
    IncomingUpload,
    IntakeError,
    IntakeErrorCode,
    IntakeRole,
    secure_extract_archive,
    validate_upload,
)

FUZZ_SEEDS = (0xD311A, 0x5EC003, 0xC0FFEE)
CASES_PER_FAMILY = 128
FIXED_ID = "0" * 32


def make_zip(entries: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return output.getvalue()


def zip_positions(data: bytes) -> tuple[int, int]:
    eocd = data.rfind(b"PK\x05\x06")
    central = struct.unpack_from("<L", data, eocd + 16)[0]
    return central, eocd


def csv_payload(value: str, second_value: str = "1883") -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["title", "year"])
    writer.writerow([value, second_value])
    return output.getvalue().encode()


def assert_content_free_rejection(
    request: IncomingUpload,
    *,
    expected: IntakeErrorCode | None = None,
    marker: str,
) -> None:
    with pytest.raises(IntakeError) as captured:
        validate_upload(request, id_factory=lambda: FIXED_ID)
    error = captured.value
    if expected is not None:
        assert error.code is expected
    assert isinstance(error.code, IntakeErrorCode)
    assert str(error) == error.code.value
    assert repr(error) == f"IntakeError('{error.code.value}')"
    assert marker not in str(error)
    assert marker not in repr(error)
    assert request.display_label not in str(error)


def mutate_zip_header(data: bytes, operation: int, rng: random.Random) -> bytes:
    central, eocd = zip_positions(data)
    changed = bytearray(data)
    if operation == 0:
        return b"X" + data
    if operation == 1:
        return data + b"X"
    if operation == 2:
        return data[: eocd + 4 + rng.randrange(18)]
    if operation == 3:
        struct.pack_into("<H", changed, eocd + 4, 1)
    elif operation == 4:
        struct.pack_into("<H", changed, eocd + 10, 0xFFFF)
    elif operation == 5:
        struct.pack_into("<L", changed, eocd + 16, central + 1)
    elif operation == 6:
        changed[central : central + 4] = b"BAD!"
    elif operation == 7:
        struct.pack_into("<H", changed, central + 8, 0x8)
    elif operation == 8:
        struct.pack_into("<H", changed, central + 10, 99)
    elif operation == 9:
        struct.pack_into("<H", changed, central + 30, 1)
    elif operation == 10:
        struct.pack_into("<H", changed, central + 34, 1)
    elif operation == 11:
        struct.pack_into("<L", changed, 14, struct.unpack_from("<L", changed, 14)[0] ^ 1)
    elif operation == 12:
        struct.pack_into("<H", changed, 28, 1)
    elif operation == 13:
        changed[30] = 0
        changed[central + 46] = 0
    elif operation == 14:
        struct.pack_into(
            "<L", changed, central + 20, struct.unpack_from("<L", changed, central + 20)[0] ^ 1
        )
    else:
        changed[:4] = b"BAD!"
    return bytes(changed)


@pytest.mark.parametrize("seed", FUZZ_SEEDS)
def test_deterministic_text_hazard_fuzz(seed: int) -> None:
    rng = random.Random(seed)
    hazards: tuple[tuple[Callable[[str], bytes], IntakeErrorCode], ...] = (
        (lambda marker: marker.encode() + b"\xff", IntakeErrorCode.INVALID_UTF8),
        (lambda marker: f"{marker}\x00text".encode(), IntakeErrorCode.CONTROL_CHARACTER),
        (
            lambda marker: f"{marker}\u202etext".encode(),
            IntakeErrorCode.CONTROL_CHARACTER,
        ),
        (lambda marker: f"{marker} cafe\u0301".encode(), IntakeErrorCode.NON_NFC),
        (lambda marker: f"<html>{marker}</html>".encode(), IntakeErrorCode.MARKUP_DOCUMENT),
        (
            lambda marker: f"{marker}\ufefftext".encode(),
            IntakeErrorCode.CONTROL_CHARACTER,
        ),
        (lambda _marker: b" \n\t ", IntakeErrorCode.TEXT_EMPTY),
        (lambda marker: b"PK\x03\x04" + marker.encode(), IntakeErrorCode.TYPE_MISMATCH),
        (lambda marker: b"%PDF-1.7\n" + marker.encode(), IntakeErrorCode.TYPE_MISMATCH),
    )
    for case in range(CASES_PER_FAMILY):
        marker = f"TEXT_SECRET_{seed:x}_{case}"
        factory, expected = hazards[rng.randrange(len(hazards))]
        assert_content_free_rejection(
            IncomingUpload(
                role=IntakeRole.CORPUS_TEXT,
                display_label=f"fuzz_{seed:x}_{case}.txt",
                data=factory(marker),
                declared_mime="text/plain",
            ),
            expected=expected,
            marker=marker,
        )


@pytest.mark.parametrize("seed", FUZZ_SEEDS)
def test_deterministic_csv_injection_fuzz(seed: int) -> None:
    rng = random.Random(seed)
    attacks: tuple[Callable[[str], str], ...] = (
        lambda marker: f"={marker}",
        lambda marker: f" +{marker}",
        lambda marker: f"-{marker}",
        lambda marker: f"@{marker}",
        lambda marker: f"<script>{marker}</script>",
        lambda marker: f"../{marker}",
        lambda marker: f"..\\{marker}",
        lambda marker: f"/{marker}",
        lambda marker: f"\\\\server\\{marker}",
        lambda marker: f"C:\\temp\\{marker}",
        lambda marker: f"file:///tmp/{marker}",
        lambda marker: f"{marker}\ncontinuation",
    )
    for case in range(CASES_PER_FAMILY):
        marker = f"CSV_SECRET_{seed:x}_{case}"
        value = attacks[rng.randrange(len(attacks))](marker)
        assert_content_free_rejection(
            IncomingUpload(
                role=IntakeRole.METADATA_CSV,
                display_label=f"metadata_{seed:x}_{case}.csv",
                data=csv_payload(value),
                declared_mime="text/csv",
            ),
            expected=IntakeErrorCode.CSV_INJECTION,
            marker=marker,
        )


@pytest.mark.parametrize("seed", FUZZ_SEEDS)
def test_deterministic_zip_path_fuzz(seed: int) -> None:
    rng = random.Random(seed)
    attacks: tuple[Callable[[str], str], ...] = (
        lambda stem: f"../{stem}.txt",
        lambda stem: f"/{stem}.txt",
        lambda stem: f"C:/{stem}.txt",
        lambda stem: f"folder\\{stem}.txt",
        lambda stem: f"folder//{stem}.txt",
        lambda stem: f"./{stem}.txt",
        lambda stem: f".{stem}.txt",
        lambda stem: f"{stem}.txt:stream",
        lambda _stem: "CON.txt",
        lambda stem: f"__MACOSX/{stem}.txt",
        lambda stem: f"a/b/c/{stem}.txt",
        lambda stem: f"{stem}.txt.",
    )
    for case in range(CASES_PER_FAMILY):
        marker = f"ZIP_SECRET_{seed:x}_{case}"
        name = attacks[rng.randrange(len(attacks))](f"work_{seed:x}_{case}")
        assert_content_free_rejection(
            IncomingUpload(
                role=IntakeRole.CORPUS_ARCHIVE,
                display_label=f"corpus_{seed:x}_{case}.zip",
                data=make_zip([(name, marker.encode())]),
                declared_mime="application/zip",
            ),
            expected=IntakeErrorCode.ARCHIVE_UNSAFE_PATH,
            marker=marker,
        )


@pytest.mark.parametrize("seed", FUZZ_SEEDS)
def test_deterministic_raw_zip_header_fuzz(seed: int) -> None:
    rng = random.Random(seed)
    for case in range(CASES_PER_FAMILY):
        marker = f"RAW_ZIP_SECRET_{seed:x}_{case}"
        payload = make_zip([(f"work_{case}.txt", marker.encode())])
        operation = rng.randrange(16)
        assert_content_free_rejection(
            IncomingUpload(
                role=IntakeRole.CORPUS_ARCHIVE,
                display_label=f"raw_{seed:x}_{case}.zip",
                data=mutate_zip_header(payload, operation, rng),
                declared_mime="application/zip",
            ),
            marker=marker,
        )


@pytest.mark.parametrize("seed", FUZZ_SEEDS)
def test_deterministic_valid_payload_properties(seed: int) -> None:
    rng = random.Random(seed)
    vocabulary = ("author", "chapter", "dialogue", "narrator", "style", "text")
    for case in range(CASES_PER_FAMILY):
        words = [rng.choice(vocabulary) for _ in range(rng.randint(1, 12))]
        payload_marker = f"payloadmarker{seed:x}x{case}"
        words.append(payload_marker)
        text = (" ".join(words) + "\n").encode()
        text_receipt = validate_upload(
            IncomingUpload(IntakeRole.CORPUS_TEXT, f"valid_{seed:x}_{case}.txt", text),
            id_factory=lambda: FIXED_ID,
        )
        assert text_receipt.token_count == len(words)
        assert payload_marker not in repr(text_receipt)

        title = f"Work {rng.randint(1, 99999)}"
        metadata = csv_payload(title, str(rng.randint(1800, 2026)))
        csv_receipt = validate_upload(
            IncomingUpload(
                IntakeRole.METADATA_CSV,
                f"valid_{seed:x}_{case}.csv",
                metadata,
            ),
            id_factory=lambda: FIXED_ID,
        )
        assert csv_receipt.row_count == 1
        assert csv_receipt.column_count == 2

        member_count = rng.randint(1, 3)
        entries = [
            (f"author_{case}/work_{index}.txt", f"text {case} {index}".encode())
            for index in range(member_count)
        ]
        zip_receipt = validate_upload(
            IncomingUpload(
                IntakeRole.CORPUS_ARCHIVE,
                f"valid_{seed:x}_{case}.zip",
                make_zip(entries),
            ),
            id_factory=lambda: FIXED_ID,
        )
        assert zip_receipt.member_count == member_count


def test_zip_slip_fuzz_leaves_disk_canaries_untouched(tmp_path: Path) -> None:
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    outside_canary = tmp_path / "outside-canary.txt"
    outside_canary.write_text("unchanged", encoding="utf-8")
    attacks = (
        "../../outside-canary.txt",
        "/tmp/delta-lemmata-canary.txt",
        "C:/delta-lemmata-canary.txt",
        "\\\\server\\share\\delta-lemmata-canary.txt",
    )
    for index, name in enumerate(attacks):
        request = IncomingUpload(
            IntakeRole.CORPUS_ARCHIVE,
            f"disk_canary_{index}.zip",
            make_zip([(name, b"overwrite")]),
        )
        with pytest.raises(IntakeError) as captured:
            secure_extract_archive(request, trusted_root, id_factory=lambda: FIXED_ID)
        assert captured.value.code is IntakeErrorCode.ARCHIVE_UNSAFE_PATH
        assert list(trusted_root.iterdir()) == []
        assert outside_canary.read_text(encoding="utf-8") == "unchanged"
