"""Payload-free presentation adapter for the secure ingestion boundary."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from delta_lemmata.ingestion import (
    DEFAULT_LIMITS,
    AssetIdFactory,
    IncomingUpload,
    IngestionLimits,
    IntakeError,
    IntakeErrorCode,
    IntakeReceipt,
    IntakeRole,
    ValidatedCorpusPayload,
    validate_batch,
    visit_validated_corpus_payloads,
)


class CorpusInputMode(StrEnum):
    """Explicit corpus role selected before any browser bytes are inspected."""

    TEXT_FILES = "text_files"
    ZIP_ARCHIVE = "zip_archive"


CORPUS_MODE_LABEL_KEYS = {
    CorpusInputMode.TEXT_FILES: "corpus.mode.text",
    CorpusInputMode.ZIP_ARCHIVE: "corpus.mode.archive",
}

_CORPUS_ROLE = {
    CorpusInputMode.TEXT_FILES: IntakeRole.CORPUS_TEXT,
    CorpusInputMode.ZIP_ARCHIVE: IntakeRole.CORPUS_ARCHIVE,
}

INTAKE_ERROR_MESSAGE_KEYS = {
    IntakeErrorCode.EMPTY: "corpus.error.empty",
    IntakeErrorCode.UPLOAD_LIMIT: "corpus.error.limit",
    IntakeErrorCode.BATCH_LIMIT: "corpus.error.limit",
    IntakeErrorCode.DISPLAY_LABEL: "corpus.error.role",
    IntakeErrorCode.DUPLICATE_LABEL: "corpus.error.role",
    IntakeErrorCode.ROLE_MISMATCH: "corpus.error.role",
    IntakeErrorCode.MIME_MISMATCH: "corpus.error.role",
    IntakeErrorCode.TYPE_MISMATCH: "corpus.error.role",
    IntakeErrorCode.INVALID_UTF8: "corpus.error.text_utf8",
    IntakeErrorCode.NON_NFC: "corpus.error.text",
    IntakeErrorCode.CONTROL_CHARACTER: "corpus.error.text",
    IntakeErrorCode.MARKUP_DOCUMENT: "corpus.error.text_markup",
    IntakeErrorCode.TEXT_EMPTY: "corpus.error.text",
    IntakeErrorCode.TEXT_LIMIT: "corpus.error.limit",
    IntakeErrorCode.CSV_INVALID: "corpus.error.csv",
    IntakeErrorCode.CSV_INJECTION: "corpus.error.csv",
    IntakeErrorCode.ARCHIVE_INVALID: "corpus.error.archive",
    IntakeErrorCode.ARCHIVE_UNSUPPORTED: "corpus.error.archive",
    IntakeErrorCode.ARCHIVE_ENCRYPTED: "corpus.error.archive",
    IntakeErrorCode.ARCHIVE_UNSAFE_PATH: "corpus.error.archive",
    IntakeErrorCode.ARCHIVE_UNSAFE_TYPE: "corpus.error.archive",
    IntakeErrorCode.ARCHIVE_DUPLICATE: "corpus.error.archive",
    IntakeErrorCode.ARCHIVE_LIMIT: "corpus.error.limit",
    IntakeErrorCode.NESTED_ARCHIVE: "corpus.error.archive",
    IntakeErrorCode.WORKSPACE_INVALID: "corpus.error.internal",
    IntakeErrorCode.EXTRACTION_FAILED: "corpus.error.internal",
    IntakeErrorCode.CLEANUP_FAILED: "corpus.error.internal",
    IntakeErrorCode.INTERNAL_ID: "corpus.error.internal",
}


@dataclass(frozen=True, slots=True)
class BrowserUpload:
    """One browser upload held only for the duration of validation."""

    display_label: str
    data: bytes = field(repr=False)
    declared_mime: str | None = None


@dataclass(frozen=True, slots=True)
class IntakeOutcome:
    """Payload-free state safe to render after an intake attempt."""

    submitted_count: int = 0
    receipts: tuple[IntakeReceipt, ...] = ()
    error_code: IntakeErrorCode | None = None

    @property
    def has_inputs(self) -> bool:
        return self.submitted_count > 0

    @property
    def accepted(self) -> bool:
        return self.has_inputs and self.error_code is None

    @property
    def corpus_ready(self) -> bool:
        return self.accepted and any(
            receipt.role in {IntakeRole.CORPUS_TEXT, IntakeRole.CORPUS_ARCHIVE}
            for receipt in self.receipts
        )

    @property
    def metadata_ready(self) -> bool:
        return self.accepted and any(
            receipt.role is IntakeRole.METADATA_CSV for receipt in self.receipts
        )

    @property
    def total_bytes(self) -> int:
        return sum(receipt.byte_size for receipt in self.receipts)

    @property
    def corpus_units(self) -> int:
        return sum(
            receipt.member_count or 1
            for receipt in self.receipts
            if receipt.role is not IntakeRole.METADATA_CSV
        )


def validate_browser_uploads(
    mode: CorpusInputMode,
    corpus_files: Sequence[BrowserUpload],
    metadata_file: BrowserUpload | None,
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
    id_factory: AssetIdFactory | None = None,
) -> IntakeOutcome:
    """Validate browser uploads and return no payload-bearing object."""

    submitted_count = len(corpus_files) + int(metadata_file is not None)
    if mode is CorpusInputMode.ZIP_ARCHIVE and len(corpus_files) > 1:
        return IntakeOutcome(
            submitted_count=submitted_count,
            error_code=IntakeErrorCode.ROLE_MISMATCH,
        )
    requests = [
        IncomingUpload(
            role=_CORPUS_ROLE[mode],
            display_label=upload.display_label,
            data=upload.data,
            declared_mime=upload.declared_mime,
        )
        for upload in corpus_files
    ]
    if metadata_file is not None:
        requests.append(
            IncomingUpload(
                role=IntakeRole.METADATA_CSV,
                display_label=metadata_file.display_label,
                data=metadata_file.data,
                declared_mime=metadata_file.declared_mime,
            )
        )
    if not requests:
        return IntakeOutcome()
    try:
        receipts = validate_batch(requests, limits=limits, id_factory=id_factory)
    except IntakeError as error:
        return IntakeOutcome(submitted_count=submitted_count, error_code=error.code)
    return IntakeOutcome(submitted_count=submitted_count, receipts=receipts)


def visit_browser_corpus_payloads[ResultT](
    mode: CorpusInputMode,
    corpus_files: Sequence[BrowserUpload],
    visitor: Callable[[tuple[ValidatedCorpusPayload, ...]], ResultT],
    *,
    limits: IngestionLimits = DEFAULT_LIMITS,
    id_factory: AssetIdFactory | None = None,
) -> ResultT:
    """Revalidate browser corpus bytes and expose them only to a trusted callback."""

    requests = tuple(
        IncomingUpload(
            role=_CORPUS_ROLE[mode],
            display_label=upload.display_label,
            data=upload.data,
            declared_mime=upload.declared_mime,
        )
        for upload in corpus_files
    )
    return visit_validated_corpus_payloads(
        requests,
        visitor,
        limits=limits,
        id_factory=id_factory,
    )
