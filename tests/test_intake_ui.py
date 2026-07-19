from __future__ import annotations

import io
import zipfile
from collections.abc import Callable, Iterator

from delta_lemmata.ingestion import IntakeErrorCode, IntakeRole
from delta_lemmata.intake_ui import (
    CORPUS_MODE_LABEL_KEYS,
    INTAKE_ERROR_MESSAGE_KEYS,
    BrowserUpload,
    CorpusInputMode,
    IntakeOutcome,
    validate_browser_uploads,
)


def id_sequence() -> Callable[[], str]:
    iterator: Iterator[str] = iter(f"{index:032x}" for index in range(20))
    return lambda: next(iterator)


def make_zip(entries: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return output.getvalue()


def test_intake_ui_contracts_cover_every_mode_and_error() -> None:
    assert set(CORPUS_MODE_LABEL_KEYS) == set(CorpusInputMode)
    assert set(INTAKE_ERROR_MESSAGE_KEYS) == set(IntakeErrorCode)


def test_every_intake_error_message_resolves_to_a_nonempty_catalog_string() -> None:
    from delta_lemmata.catalog import text

    for message_key in INTAKE_ERROR_MESSAGE_KEYS.values():
        assert text(message_key).strip()
    assert text("corpus.error.retry").strip()


def test_common_beginner_rejections_get_cause_specific_guidance() -> None:
    from delta_lemmata.catalog import text

    # A wrong-encoding TXT and a markup/document file are the two rejections a
    # non-developer actually hits; each must name its cause and how to fix it,
    # not a single lumped message.
    assert INTAKE_ERROR_MESSAGE_KEYS[IntakeErrorCode.INVALID_UTF8] == "corpus.error.text_utf8"
    assert INTAKE_ERROR_MESSAGE_KEYS[IntakeErrorCode.MARKUP_DOCUMENT] == "corpus.error.text_markup"
    utf8_message = text("corpus.error.text_utf8")
    markup_message = text("corpus.error.text_markup")
    assert "UTF-8" in utf8_message and "again" in utf8_message
    assert "plain .txt" in markup_message and "again" in markup_message
    assert utf8_message != markup_message != text("corpus.error.text")


def test_recovery_guidance_separates_user_input_from_system_errors() -> None:
    from delta_lemmata.catalog import text
    from delta_lemmata.intake_ui import intake_recovery_guidance_key

    # Recoverable user-input rejections invite trying another file without a
    # reload; internal/workspace/cleanup faults must not, because the file is
    # not the problem.
    for recoverable in (
        IntakeErrorCode.INVALID_UTF8,
        IntakeErrorCode.MARKUP_DOCUMENT,
        IntakeErrorCode.UPLOAD_LIMIT,
        IntakeErrorCode.ARCHIVE_UNSAFE_PATH,
    ):
        assert intake_recovery_guidance_key(recoverable) == "corpus.error.retry"
    for system_fault in (
        IntakeErrorCode.WORKSPACE_INVALID,
        IntakeErrorCode.EXTRACTION_FAILED,
        IntakeErrorCode.CLEANUP_FAILED,
        IntakeErrorCode.INTERNAL_ID,
    ):
        assert intake_recovery_guidance_key(system_fault) == "corpus.error.retry_system"
    # Every intake error resolves to one of the two guidance strings.
    for code in IntakeErrorCode:
        assert text(intake_recovery_guidance_key(code)).strip()
    reload_message = text("corpus.error.retry")
    system_message = text("corpus.error.retry_system")
    assert "without reloading" in reload_message
    assert "system error" in system_message and reload_message != system_message


def test_empty_outcome_is_payload_free_and_not_ready() -> None:
    upload = BrowserUpload("work.txt", b"SECRET_PAYLOAD", "text/plain")
    assert "SECRET_PAYLOAD" not in repr(upload)
    outcome = validate_browser_uploads(CorpusInputMode.TEXT_FILES, (), None)
    assert outcome == IntakeOutcome()
    assert outcome.has_inputs is False
    assert outcome.accepted is False
    assert outcome.corpus_ready is False
    assert outcome.metadata_ready is False
    assert outcome.total_bytes == 0
    assert outcome.corpus_units == 0


def test_text_and_metadata_are_validated_without_retaining_payloads() -> None:
    outcome = validate_browser_uploads(
        CorpusInputMode.TEXT_FILES,
        (
            BrowserUpload("one.txt", b"one text", "text/plain"),
            BrowserUpload("two.txt", b"two text", "text/plain"),
        ),
        BrowserUpload("metadata.csv", b"title,year\nOne,1883", "text/csv"),
        id_factory=id_sequence(),
    )
    assert outcome.has_inputs is True
    assert outcome.accepted is True
    assert outcome.error_code is None
    assert outcome.corpus_ready is True
    assert outcome.metadata_ready is True
    assert outcome.total_bytes == 35
    assert outcome.corpus_units == 2
    assert [receipt.role for receipt in outcome.receipts] == [
        IntakeRole.CORPUS_TEXT,
        IntakeRole.CORPUS_TEXT,
        IntakeRole.METADATA_CSV,
    ]
    assert "one text" not in repr(outcome)


def test_archive_mode_counts_members_and_rejects_multiple_archives() -> None:
    archive = BrowserUpload(
        "corpus.zip",
        make_zip([("one.txt", b"one"), ("two.txt", b"two")]),
        "application/zip",
    )
    outcome = validate_browser_uploads(
        CorpusInputMode.ZIP_ARCHIVE,
        (archive,),
        None,
        id_factory=id_sequence(),
    )
    assert outcome.accepted is True
    assert outcome.corpus_ready is True
    assert outcome.metadata_ready is False
    assert outcome.corpus_units == 2
    receipt = outcome.receipts[0]
    assert [member.display_label for member in receipt.archive_members] == [
        "one.txt",
        "two.txt",
    ]
    assert all(not hasattr(member, "data") for member in receipt.archive_members)

    rejected = validate_browser_uploads(
        CorpusInputMode.ZIP_ARCHIVE,
        (archive, archive),
        None,
    )
    assert rejected.accepted is False
    assert rejected.error_code is IntakeErrorCode.ROLE_MISMATCH
    assert rejected.receipts == ()


def test_metadata_only_is_valid_but_does_not_make_a_corpus_ready() -> None:
    outcome = validate_browser_uploads(
        CorpusInputMode.TEXT_FILES,
        (),
        BrowserUpload("metadata.csv", b"title,year\nOne,1883", "text/csv"),
        id_factory=id_sequence(),
    )
    assert outcome.accepted is True
    assert outcome.corpus_ready is False
    assert outcome.metadata_ready is True
    assert outcome.corpus_units == 0


def test_validation_failure_returns_only_a_stable_code() -> None:
    outcome = validate_browser_uploads(
        CorpusInputMode.TEXT_FILES,
        (BrowserUpload("secret.txt", b"SECRET_PAYLOAD\xff", "text/plain"),),
        None,
        id_factory=id_sequence(),
    )
    assert outcome.has_inputs is True
    assert outcome.accepted is False
    assert outcome.corpus_ready is False
    assert outcome.metadata_ready is False
    assert outcome.error_code is IntakeErrorCode.INVALID_UTF8
    assert outcome.receipts == ()
    assert "SECRET_PAYLOAD" not in repr(outcome)
