from __future__ import annotations

import io
import zipfile
from dataclasses import replace

import pytest

import delta_lemmata.ingestion as ingestion_module
from delta_lemmata.ingestion import (
    IncomingUpload,
    IntakeError,
    IntakeErrorCode,
    IntakeRole,
    ValidatedCorpusPayload,
    validate_batch,
    visit_validated_corpus_payloads,
)


class Ids:
    def __init__(self) -> None:
        self.value = 0

    def __call__(self) -> str:
        self.value += 1
        return f"{self.value:032x}"


def _archive(files: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return output.getvalue()


def test_trusted_handoff_unifies_individual_text_and_safe_zip_members() -> None:
    requests = (
        IncomingUpload(
            role=IntakeRole.CORPUS_TEXT,
            display_label="c.txt",
            data=b"third accepted text",
            declared_mime="text/plain",
        ),
        IncomingUpload(
            role=IntakeRole.CORPUS_ARCHIVE,
            display_label="corpus.zip",
            data=_archive(
                {
                    "b.txt": b"second accepted text",
                    "a.txt": b"first accepted text",
                }
            ),
            declared_mime="application/zip",
        ),
    )
    observed: tuple[ValidatedCorpusPayload, ...] = ()

    def capture(payloads: tuple[ValidatedCorpusPayload, ...]) -> tuple[str, ...]:
        nonlocal observed
        observed = payloads
        return tuple(item.receipt.display_label for item in payloads)

    labels = visit_validated_corpus_payloads(requests, capture, id_factory=Ids())

    assert labels == ("a.txt", "b.txt", "c.txt")
    assert [item.content for item in observed] == [
        b"first accepted text",
        b"second accepted text",
        b"third accepted text",
    ]
    assert all(item.receipt.role is IntakeRole.CORPUS_TEXT for item in observed)
    assert all(item.receipt.sha256 not in repr(item.content) for item in observed)
    assert "accepted text" not in repr(observed)


def test_trusted_handoff_never_calls_sink_for_invalid_or_metadata_only_input() -> None:
    calls = 0

    def sink(_payloads: tuple[ValidatedCorpusPayload, ...]) -> None:
        nonlocal calls
        calls += 1

    bad_archive = IncomingUpload(
        role=IntakeRole.CORPUS_ARCHIVE,
        display_label="private.zip",
        data=b"not a zip",
        declared_mime="application/zip",
    )
    with pytest.raises(IntakeError) as captured:
        visit_validated_corpus_payloads((bad_archive,), sink)
    assert captured.value.code is IntakeErrorCode.TYPE_MISMATCH
    assert calls == 0

    metadata = IncomingUpload(
        role=IntakeRole.METADATA_CSV,
        display_label="metadata.csv",
        data=b"work_id,title\nwork_one,One\n",
        declared_mime="text/csv",
    )
    with pytest.raises(IntakeError) as captured:
        visit_validated_corpus_payloads((metadata,), sink)
    assert captured.value.code is IntakeErrorCode.ROLE_MISMATCH
    assert calls == 0

    valid_text = IncomingUpload(
        role=IntakeRole.CORPUS_TEXT,
        display_label="work.txt",
        data=b"accepted text",
        declared_mime="text/plain",
    )
    with pytest.raises(IntakeError) as captured:
        visit_validated_corpus_payloads((valid_text,), None)  # type: ignore[arg-type]
    assert captured.value.code is IntakeErrorCode.INTERNAL_ID


def test_trusted_handoff_rejects_reused_server_ids_before_sink() -> None:
    request = IncomingUpload(
        role=IntakeRole.CORPUS_ARCHIVE,
        display_label="corpus.zip",
        data=_archive({"a.txt": b"first text", "b.txt": b"second text"}),
        declared_mime="application/zip",
    )
    called = False

    def sink(_payloads: tuple[ValidatedCorpusPayload, ...]) -> None:
        nonlocal called
        called = True

    with pytest.raises(IntakeError) as captured:
        visit_validated_corpus_payloads(
            (request,),
            sink,
            id_factory=lambda: "0" * 32,
        )
    assert captured.value.code is IntakeErrorCode.INTERNAL_ID
    assert called is False


def test_trusted_handoff_rechecks_member_digest_and_archive_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = IncomingUpload(
        role=IntakeRole.CORPUS_ARCHIVE,
        display_label="corpus.zip",
        data=_archive({"a.txt": b"first text"}),
        declared_mime="application/zip",
    )
    original_inspect = ingestion_module._inspect_archive
    calls = 0

    def tampered_inspection(data: bytes, limits, batch_expanded_budget=None):
        nonlocal calls
        calls += 1
        inspection = original_inspect(data, limits, batch_expanded_budget)
        if calls == 2:
            member = replace(inspection.members[0], sha256="0" * 64)
            return replace(inspection, members=(member,))
        return inspection

    monkeypatch.setattr(ingestion_module, "_inspect_archive", tampered_inspection)
    with pytest.raises(IntakeError) as captured:
        visit_validated_corpus_payloads((request,), lambda _payloads: None, id_factory=Ids())
    assert captured.value.code is IntakeErrorCode.EXTRACTION_FAILED

    monkeypatch.setattr(ingestion_module, "_inspect_archive", original_inspect)
    receipts = validate_batch((request,), id_factory=Ids())
    inspection = original_inspect(request.data, ingestion_module.DEFAULT_LIMITS)
    monkeypatch.setattr(ingestion_module, "_inspect_archive", lambda *_args: inspection)

    class BrokenArchive:
        def __init__(self, *_args, **_kwargs) -> None:
            raise zipfile.BadZipFile

    monkeypatch.setattr(ingestion_module.zipfile, "ZipFile", BrokenArchive)
    with pytest.raises(IntakeError) as captured:
        ingestion_module._corpus_payloads_from_validated_batch(
            (request,),
            receipts,
            limits=ingestion_module.DEFAULT_LIMITS,
            id_factory=Ids(),
        )
    assert captured.value.code is IntakeErrorCode.EXTRACTION_FAILED
