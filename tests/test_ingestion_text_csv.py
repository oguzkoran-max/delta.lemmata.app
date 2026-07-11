from __future__ import annotations

import hashlib
import traceback
import unicodedata
from collections.abc import Callable

import pytest
from pydantic import ValidationError

import delta_lemmata.ingestion as ingestion
from delta_lemmata.ingestion import (
    DEFAULT_LIMITS,
    IncomingUpload,
    IngestionLimits,
    IntakeError,
    IntakeErrorCode,
    IntakeRole,
    validate_batch,
    validate_upload,
)

FIXED_ID = "0" * 32


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


def request(
    role: IntakeRole,
    name: str,
    data: bytes,
    mime: str | None = None,
) -> IncomingUpload:
    return IncomingUpload(role=role, display_label=name, data=data, declared_mime=mime)


def test_packaged_limit_profile_is_valid_frozen_and_versioned() -> None:
    assert DEFAULT_LIMITS.model_dump() == {
        "profile_version": "ingestion-limits-v1",
        "max_upload_bytes": 25 * 1024 * 1024,
        "max_batch_bytes": 50 * 1024 * 1024,
        "max_batch_expanded_bytes": 100 * 1024 * 1024,
        "max_batch_files": 50,
        "max_display_label_bytes": 200,
        "max_text_chars": 20_000_000,
        "max_lines": 500_000,
        "max_tokens": 3_000_000,
        "max_token_chars": 4096,
        "max_archive_members": 200,
        "max_central_directory_bytes": 1024 * 1024,
        "max_member_bytes": 10 * 1024 * 1024,
        "max_archive_expanded_bytes": 50 * 1024 * 1024,
        "max_compression_ratio": 100.0,
        "max_path_depth": 3,
        "max_path_bytes": 240,
        "max_csv_rows": 20_000,
        "max_csv_columns": 64,
        "max_csv_cell_chars": 16_384,
        "read_chunk_bytes": 65_536,
    }
    with pytest.raises(ValidationError):
        DEFAULT_LIMITS.__setattr__("max_lines", 1)
    with pytest.raises(ValidationError):
        IngestionLimits.model_validate({**DEFAULT_LIMITS.model_dump(), "unknown": 1})
    with pytest.raises(ValidationError):
        IngestionLimits.model_validate({**DEFAULT_LIMITS.model_dump(), "max_lines": 0})


def test_valid_text_receipt_is_content_free_and_server_named() -> None:
    payload = "Caffè e città\nSeconda linea".encode()
    receipt = validate_upload(
        request(IntakeRole.CORPUS_TEXT, "romanzo.txt", payload, "text/plain; charset=utf-8"),
        id_factory=lambda: FIXED_ID,
    )
    assert receipt.asset_id == f"asset_{FIXED_ID}"
    assert receipt.storage_name == f"asset_{FIXED_ID}.txt"
    assert receipt.display_label == "romanzo.txt"
    assert receipt.sha256 == hashlib.sha256(payload).hexdigest()
    assert receipt.line_count == 2
    assert receipt.token_count == 5
    assert receipt.expanded_bytes == len(payload)
    assert payload.decode() not in repr(receipt)


def test_utf8_bom_is_accepted_only_at_the_start() -> None:
    receipt = validate_upload(
        request(IntakeRole.CORPUS_TEXT, "bom.txt", b"\xef\xbb\xbfText"),
        id_factory=lambda: FIXED_ID,
    )
    assert receipt.token_count == 1
    expect_code(
        IntakeErrorCode.CONTROL_CHARACTER,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, "embedded.txt", "A\ufeffB".encode()),
            id_factory=lambda: FIXED_ID,
        ),
    )


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"", IntakeErrorCode.EMPTY),
        (b"\xff", IntakeErrorCode.INVALID_UTF8),
        (b"A\x00B", IntakeErrorCode.CONTROL_CHARACTER),
        ("abc\u202edef".encode(), IntakeErrorCode.CONTROL_CHARACTER),
        (b" \n\t ", IntakeErrorCode.TEXT_EMPTY),
        (b"<html><p>text</p></html>", IntakeErrorCode.MARKUP_DOCUMENT),
        (b"<?xml version='1.0'?><TEI/>", IntakeErrorCode.MARKUP_DOCUMENT),
        (b"<script>alert(1)</script>", IntakeErrorCode.MARKUP_DOCUMENT),
        (b"%PDF-1.7\ntext", IntakeErrorCode.TYPE_MISMATCH),
        (b"\xef\xbb\xbf%PDF-1.7\ntext", IntakeErrorCode.TYPE_MISMATCH),
        (b"{\\rtf1 text}", IntakeErrorCode.TYPE_MISMATCH),
    ],
)
def test_invalid_text_is_rejected_content_free(data: bytes, code: IntakeErrorCode) -> None:
    canary = "SECRET_CANARY"
    try:
        validate_upload(
            request(IntakeRole.CORPUS_TEXT, f"{canary}.txt", data),
            id_factory=lambda: FIXED_ID,
        )
    except IntakeError as error:
        assert error.code is code
        assert error.__context__ is None
        assert error.__cause__ is None
        assert error.__suppress_context__ is True
        assert canary not in str(error)
        assert canary not in repr(error)
        assert canary not in traceback.format_exc()
    else:
        pytest.fail("payload was unexpectedly accepted")


def test_non_nfc_text_and_label_are_rejected() -> None:
    nfd = unicodedata.normalize("NFD", "caffè")
    expect_code(
        IntakeErrorCode.NON_NFC,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, "work.txt", nfd.encode()),
            id_factory=lambda: FIXED_ID,
        ),
    )
    expect_code(
        IntakeErrorCode.DISPLAY_LABEL,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, f"{nfd}.txt", b"text"),
            id_factory=lambda: FIXED_ID,
        ),
    )


def test_public_rejection_detaches_invalid_utf8_payload_context() -> None:
    payload = b"SECRET_CONTEXT_CANARY\xff"
    error = expect_code(
        IntakeErrorCode.INVALID_UTF8,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, "work.txt", payload),
            id_factory=lambda: FIXED_ID,
        ),
    )
    assert error.__context__ is None
    assert error.__cause__ is None
    assert error.__suppress_context__ is True
    assert "SECRET_CONTEXT_CANARY" not in "".join(traceback.format_exception(error))


@pytest.mark.parametrize(
    ("profile", "data"),
    [
        (limits(max_text_chars=3), b"four"),
        (limits(max_lines=1), b"one\ntwo"),
        (limits(max_tokens=1), b"one two"),
        (limits(max_token_chars=3), b"four"),
    ],
)
def test_text_limits_fail_at_one_over(profile: IngestionLimits, data: bytes) -> None:
    expect_code(
        IntakeErrorCode.TEXT_LIMIT,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, "limit.txt", data),
            limits=profile,
            id_factory=lambda: FIXED_ID,
        ),
    )


def test_upload_size_and_zip_masquerade_are_rejected() -> None:
    expect_code(
        IntakeErrorCode.UPLOAD_LIMIT,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, "large.txt", b"1234"),
            limits=limits(max_upload_bytes=3),
            id_factory=lambda: FIXED_ID,
        ),
    )
    expect_code(
        IntakeErrorCode.TYPE_MISMATCH,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, "fake.txt", b"PK\x03\x04not-text"),
            id_factory=lambda: FIXED_ID,
        ),
    )


@pytest.mark.parametrize(
    "name",
    [
        " ../work.txt",
        "../work.txt",
        "folder/work.txt",
        "folder\\work.txt",
        "work.txt:ads",
        "<b>.txt",
        "CON.txt",
        "COM¹.txt",
        ".hidden.txt",
        "work.txt\n",
        "work\u2028name.txt",
        "work\u2029name.txt",
    ],
)
def test_display_labels_are_never_paths_or_markup(name: str) -> None:
    expect_code(
        IntakeErrorCode.DISPLAY_LABEL,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, name, b"text"),
            id_factory=lambda: FIXED_ID,
        ),
    )


def test_surrogate_display_label_maps_to_content_free_rejection() -> None:
    error = expect_code(
        IntakeErrorCode.DISPLAY_LABEL,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, "bad\ud800.txt", b"text"),
            id_factory=lambda: FIXED_ID,
        ),
    )
    assert error.__context__ is None
    assert error.__cause__ is None


def test_role_extension_and_supplied_mime_must_agree() -> None:
    expect_code(
        IntakeErrorCode.ROLE_MISMATCH,
        lambda: validate_upload(
            request(IntakeRole.METADATA_CSV, "metadata.txt", b"a,b\n1,2"),
            id_factory=lambda: FIXED_ID,
        ),
    )
    expect_code(
        IntakeErrorCode.MIME_MISMATCH,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, "work.txt", b"text", "application/zip"),
            id_factory=lambda: FIXED_ID,
        ),
    )
    receipt = validate_upload(
        request(IntakeRole.CORPUS_TEXT, "work.TXT", b"text", None),
        id_factory=lambda: FIXED_ID,
    )
    assert receipt.role is IntakeRole.CORPUS_TEXT


def test_document_signature_is_scoped_to_the_start_of_text() -> None:
    receipt = validate_upload(
        request(IntakeRole.CORPUS_TEXT, "work.txt", b"A literal %PDF- token in prose"),
        id_factory=lambda: FIXED_ID,
    )
    assert receipt.token_count == 6


@pytest.mark.parametrize("signature", ingestion._BINARY_DOCUMENT_SIGNATURES)
def test_every_configured_binary_signature_is_rejected(signature: bytes) -> None:
    expect_code(
        IntakeErrorCode.TYPE_MISMATCH,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, "binary.txt", signature + b" synthetic"),
            id_factory=lambda: FIXED_ID,
        ),
    )


def test_invalid_server_id_is_rejected_without_using_the_label() -> None:
    expect_code(
        IntakeErrorCode.INTERNAL_ID,
        lambda: validate_upload(
            request(IntakeRole.CORPUS_TEXT, "work.txt", b"text"),
            id_factory=lambda: "../user-name",
        ),
    )


def test_valid_metadata_csv_is_structural_not_semantic() -> None:
    payload = b"title,year\nPinocchio,1883\nMinuzzolo,1878\n"
    receipt = validate_upload(
        request(IntakeRole.METADATA_CSV, "metadata.csv", payload, "text/csv"),
        id_factory=lambda: FIXED_ID,
    )
    assert receipt.role is IntakeRole.METADATA_CSV
    assert receipt.row_count == 2
    assert receipt.column_count == 2
    assert receipt.status == "validated-for-intake"


@pytest.mark.parametrize(
    "payload",
    [
        b"one\nvalue\n",
        b"title,title\nA,B\n",
        b",year\nA,1883\n",
        b"title,year\n",
        b'title,year\n"unclosed,1883\n',
        b"title,year\nA\n",
    ],
)
def test_malformed_csv_is_rejected(payload: bytes) -> None:
    expect_code(
        IntakeErrorCode.CSV_INVALID,
        lambda: validate_upload(
            request(IntakeRole.METADATA_CSV, "metadata.csv", payload),
            id_factory=lambda: FIXED_ID,
        ),
    )


@pytest.mark.parametrize(
    "value",
    [
        "=SUM(A1:A2)",
        " +cmd",
        "-1",
        "@formula",
        "<script>alert(1)</script>",
        "../secret",
        "\t../secret",
        "..\\secret",
        "/etc/passwd",
        " /etc/passwd",
        "\u00a0/etc/passwd",
        r" \root",
        "\\\\server\\share",
        "C:\\temp\\file",
        " C:\\temp\\file",
        "\u2007C:\\temp\\file",
        "file:///tmp/secret",
        " file:///tmp/secret",
        "\u202ffile:///tmp/secret",
        "line\nfeed",
        "line\u2028feed",
        "line\u2029feed",
    ],
)
def test_csv_injection_cells_fail_closed(value: str) -> None:
    output = io_csv("title", value)
    expect_code(
        IntakeErrorCode.CSV_INJECTION,
        lambda: validate_upload(
            request(IntakeRole.METADATA_CSV, "metadata.csv", output),
            id_factory=lambda: FIXED_ID,
        ),
    )


def io_csv(header: str, value: str) -> bytes:
    import csv
    import io

    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow([header, "year"])
    writer.writerow([value, "1883"])
    return stream.getvalue().encode()


def test_csv_row_column_and_cell_limits() -> None:
    for profile, payload, code in (
        (limits(max_csv_rows=1), b"a,b\n1,2\n3,4\n", IntakeErrorCode.CSV_INVALID),
        (limits(max_csv_columns=2), b"a,b,c\n1,2,3\n", IntakeErrorCode.CSV_INVALID),
        (limits(max_csv_cell_chars=3), b"title,year\nlong,1883\n", IntakeErrorCode.CSV_INJECTION),
    ):
        expect_code(
            code,
            lambda profile=profile, payload=payload: validate_upload(
                request(IntakeRole.METADATA_CSV, "metadata.csv", payload),
                limits=profile,
                id_factory=lambda: FIXED_ID,
            ),
        )


def test_private_csv_empty_iterator_maps_to_stable_code() -> None:
    expect_code(
        IntakeErrorCode.CSV_INVALID,
        lambda: ingestion._validate_csv("", ingestion._TextStats(1, 1), DEFAULT_LIMITS),
    )


def test_batch_is_all_or_nothing_and_enforces_aggregate_limits() -> None:
    ids = iter(("0" * 32, "1" * 32))
    receipts = validate_batch(
        [
            request(IntakeRole.CORPUS_TEXT, "one.txt", b"one"),
            request(IntakeRole.METADATA_CSV, "metadata.csv", b"title,year\nOne,1883"),
        ],
        id_factory=lambda: next(ids),
    )
    assert [receipt.asset_id for receipt in receipts] == [f"asset_{'0' * 32}", f"asset_{'1' * 32}"]

    checks = (
        ([], IntakeErrorCode.EMPTY, DEFAULT_LIMITS),
        (
            [request(IntakeRole.CORPUS_TEXT, "one.txt", b"one")] * 2,
            IntakeErrorCode.BATCH_LIMIT,
            limits(max_batch_files=1),
        ),
        (
            [request(IntakeRole.CORPUS_TEXT, "one.txt", b"1234")],
            IntakeErrorCode.BATCH_LIMIT,
            limits(max_batch_bytes=3),
        ),
        (
            [
                request(IntakeRole.METADATA_CSV, "a.csv", b"a,b\n1,2"),
                request(IntakeRole.METADATA_CSV, "b.csv", b"a,b\n1,2"),
            ],
            IntakeErrorCode.ROLE_MISMATCH,
            DEFAULT_LIMITS,
        ),
        (
            [
                request(IntakeRole.CORPUS_TEXT, "Same.txt", b"one"),
                request(IntakeRole.CORPUS_TEXT, "same.TXT", b"two"),
            ],
            IntakeErrorCode.DUPLICATE_LABEL,
            DEFAULT_LIMITS,
        ),
    )
    for batch, code, profile in checks:
        expect_code(
            code, lambda batch=batch, profile=profile: validate_batch(batch, limits=profile)
        )


def test_batch_rejects_duplicate_ids_and_expanded_total() -> None:
    batch = [
        request(IntakeRole.CORPUS_TEXT, "one.txt", b"one"),
        request(IntakeRole.CORPUS_TEXT, "two.txt", b"two"),
    ]
    expect_code(
        IntakeErrorCode.INTERNAL_ID,
        lambda: validate_batch(batch, id_factory=lambda: FIXED_ID),
    )
    ids = iter(("0" * 32, "1" * 32))
    expect_code(
        IntakeErrorCode.BATCH_LIMIT,
        lambda: validate_batch(
            batch,
            limits=limits(max_batch_expanded_bytes=5),
            id_factory=lambda: next(ids),
        ),
    )


def test_batch_text_budget_is_rejected_before_second_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_decode = ingestion._decode_text
    calls = 0

    def counted_decode(data: bytes, profile: IngestionLimits) -> tuple[str, ingestion._TextStats]:
        nonlocal calls
        calls += 1
        return real_decode(data, profile)

    monkeypatch.setattr(ingestion, "_decode_text", counted_decode)
    ids = iter(("0" * 32, "1" * 32))
    error = expect_code(
        IntakeErrorCode.BATCH_LIMIT,
        lambda: validate_batch(
            [
                request(IntakeRole.CORPUS_TEXT, "one.txt", b"one"),
                request(IntakeRole.CORPUS_TEXT, "two.txt", b"two"),
            ],
            limits=limits(max_batch_expanded_bytes=5),
            id_factory=lambda: next(ids),
        ),
    )
    assert calls == 1
    assert error.__context__ is None


def test_batch_post_validation_budget_defense_remains_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = validate_upload(
        request(IntakeRole.CORPUS_TEXT, "one.txt", b"one"),
        id_factory=lambda: FIXED_ID,
    ).model_copy(update={"expanded_bytes": 6})
    monkeypatch.setattr(
        ingestion,
        "_validated_upload",
        lambda *_args, **_kwargs: (receipt, None),
    )
    error = expect_code(
        IntakeErrorCode.BATCH_LIMIT,
        lambda: validate_batch(
            [request(IntakeRole.CORPUS_TEXT, "one.txt", b"one")],
            limits=limits(max_batch_expanded_bytes=5),
        ),
    )
    assert error.__context__ is None
