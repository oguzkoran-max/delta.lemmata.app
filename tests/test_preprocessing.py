from __future__ import annotations

import hashlib

import pytest

import delta_lemmata.preprocessing as preprocessing_module
from delta_lemmata.preprocessing import (
    CandidateInventory,
    CandidateInventoryError,
    PreprocessingError,
    PreprocessingErrorCode,
    build_candidate_inventory,
    build_preprocessing_config,
    build_preprocessing_manifest,
    parse_custom_exclusions,
    prepare_document,
    prepare_text,
)
from delta_lemmata.preprocessing_models import (
    AnalysisRole,
    CorpusAnalysisAnnotation,
    CorpusAnalysisAnnotationsV1,
    OcrStatus,
    ParatextStatus,
    TextUnit,
    canonical_p007_json,
)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _annotation(
    index: int,
    *,
    role: AnalysisRole = AnalysisRole.KNOWN,
    text_unit: TextUnit = TextUnit.INDEPENDENT_WORK,
    parent_work_id: str | None = None,
) -> CorpusAnalysisAnnotation:
    return CorpusAnalysisAnnotation(
        document_id=f"doc_{index:064x}",
        asset_id=f"asset_work_{index:02d}",
        work_id=f"work_{index:02d}",
        analysis_role=role,
        text_unit=text_unit,
        parent_work_id=parent_work_id,
        ocr_status=OcrStatus.NOT_OCR,
        paratext_status=ParatextStatus.ABSENT,
    )


def test_surface_word_profile_is_unicode_deterministic_and_explainable() -> None:
    raw = "L'amore co-operare PERCHÉ perché 2026 😊 À İ\r\nFine\r".encode()
    expected_raw_sha256 = _sha(raw)

    prepared = prepare_text(raw, expected_raw_sha256=expected_raw_sha256)

    assert prepared.tokens == (
        "l",
        "amore",
        "co",
        "operare",
        "perché",
        "perché",
        "à",
        "i\u0307",
        "fine",
    )
    assert prepared.prepared_bytes == ("l amore co operare perché perché à i\u0307 fine\n".encode())
    assert prepared.raw_sha256 == expected_raw_sha256
    assert prepared.prepared_sha256 == _sha(prepared.prepared_bytes)
    assert prepared.token_count == 9
    assert prepared.unique_token_count == 8
    assert prepared.newline_replacement_count == 2
    assert prepared.lowercase_source_count == 10
    assert prepared.bom_removed is False

    repeated = prepare_text(raw, expected_raw_sha256=expected_raw_sha256)
    assert repeated == prepared


def test_bom_and_newline_variants_share_prepared_hash_but_keep_raw_evidence() -> None:
    plain = b"Uno\nDue\n"
    variant = b"\xef\xbb\xbfUno\r\nDue\r"

    plain_result = prepare_text(plain, expected_raw_sha256=_sha(plain))
    variant_result = prepare_text(variant, expected_raw_sha256=_sha(variant))

    assert plain_result.raw_sha256 != variant_result.raw_sha256
    assert plain_result.prepared_bytes == variant_result.prepared_bytes == b"uno due\n"
    assert plain_result.prepared_sha256 == variant_result.prepared_sha256
    assert variant_result.bom_removed is True


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b"\xff", PreprocessingErrorCode.INVALID_UTF8),
        ("e\u0301".encode(), PreprocessingErrorCode.INPUT_NOT_NFC),
        ("uno\ufeffdue".encode(), PreprocessingErrorCode.EMBEDDED_BOM),
    ],
)
def test_preparation_rechecks_the_p003_unicode_boundary(
    raw: bytes,
    code: PreprocessingErrorCode,
) -> None:
    with pytest.raises(PreprocessingError) as captured:
        prepare_text(raw, expected_raw_sha256=_sha(raw))
    assert captured.value.code is code
    assert str(captured.value) == code.value


def test_preparation_rejects_digest_mismatch_without_echoing_content() -> None:
    with pytest.raises(PreprocessingError) as captured:
        prepare_text(b"private corpus text", expected_raw_sha256="0" * 64)
    assert captured.value.code is PreprocessingErrorCode.RAW_DIGEST_MISMATCH
    assert "private" not in str(captured.value)


def test_empty_stylometric_output_is_represented_for_health_blocking() -> None:
    prepared = prepare_text(b"123 -- !!!", expected_raw_sha256=_sha(b"123 -- !!!"))
    assert prepared.tokens == ()
    assert prepared.prepared_bytes == b"\n"
    assert prepared.token_count == 0


def test_custom_exclusions_are_exact_candidate_only_and_deterministic() -> None:
    payload = "perché\namore\nperché\n".encode()
    exclusions = parse_custom_exclusions(payload)
    assert exclusions.tokens == ("amore", "perché")
    assert exclusions.source_sha256 == _sha(payload)

    config = build_preprocessing_config(exclusions)
    assert config.custom_exclusions_sha256 == _sha(payload)
    assert config.custom_exclusion_count == 2

    raw = "Amore perché amore resta".encode()
    prepared = prepare_document(
        raw,
        expected_raw_sha256=_sha(raw),
        annotation=_annotation(1),
    )
    inventory = build_candidate_inventory((prepared,), exclusions=exclusions)
    assert inventory.features == ("resta",)
    assert prepared.prepared.tokens == ("amore", "perché", "amore", "resta")
    assert prepared.prepared.prepared_bytes == b"amore perch\xc3\xa9 amore resta\n"


@pytest.mark.parametrize(
    "payload",
    [
        b"Amore\n",
        b"two words\n",
        b"word*\n",
        b"#comment\n",
        b" leading\n",
        b"word\r\n",
        b"\xef\xbb\xbfword\n",
        "e\u0301\n".encode(),
        b"123\n",
        b"\xff",
    ],
)
def test_custom_exclusions_reject_invisible_or_non_token_syntax(payload: bytes) -> None:
    with pytest.raises(PreprocessingError):
        parse_custom_exclusions(payload)


def test_candidate_inventory_uses_known_independent_works_only() -> None:
    known_a_raw = b"alpha alpha beta gamma"
    known_b_raw = b"alpha beta beta delta"
    unknown_a_raw = b"unknownonly unknownonly alpha"
    unknown_b_raw = b"changedonly changedonly beta"
    known_a = prepare_document(
        known_a_raw,
        expected_raw_sha256=_sha(known_a_raw),
        annotation=_annotation(1),
    )
    known_b = prepare_document(
        known_b_raw,
        expected_raw_sha256=_sha(known_b_raw),
        annotation=_annotation(2),
    )
    unknown_a = prepare_document(
        unknown_a_raw,
        expected_raw_sha256=_sha(unknown_a_raw),
        annotation=_annotation(3, role=AnalysisRole.UNKNOWN),
    )
    unknown_b = prepare_document(
        unknown_b_raw,
        expected_raw_sha256=_sha(unknown_b_raw),
        annotation=_annotation(3, role=AnalysisRole.UNKNOWN),
    )

    first = build_candidate_inventory((known_a, unknown_a, known_b))
    second = build_candidate_inventory((known_a, unknown_b, known_b))

    assert first == second
    assert first.features == ("alpha", "beta", "delta", "gamma")
    assert "unknownonly" not in first.features
    assert "changedonly" not in second.features


def test_candidate_inventory_rejects_duplicate_known_independence_units() -> None:
    raw = b"alpha beta"
    first = prepare_document(
        raw,
        expected_raw_sha256=_sha(raw),
        annotation=_annotation(1),
    )
    duplicate_binding = first.__class__(
        annotation=_annotation(2).model_copy(update={"work_id": "work_01"}),
        prepared=first.prepared,
    )
    with pytest.raises(CandidateInventoryError):
        build_candidate_inventory((first, duplicate_binding))


def test_manifest_is_content_free_and_binds_config_annotations_and_inventory() -> None:
    raw_a = b"alpha alpha beta"
    raw_b = b"alpha gamma gamma"
    documents = (
        prepare_document(
            raw_a,
            expected_raw_sha256=_sha(raw_a),
            annotation=_annotation(1),
        ),
        prepare_document(
            raw_b,
            expected_raw_sha256=_sha(raw_b),
            annotation=_annotation(2),
        ),
    )
    annotations = CorpusAnalysisAnnotationsV1(
        schema_version="corpus-analysis-annotations-v1",
        inventory_sha256="a" * 64,
        annotations=tuple(document.annotation for document in documents),
    )
    config = build_preprocessing_config(parse_custom_exclusions(None))
    candidates = build_candidate_inventory(documents)

    manifest = build_preprocessing_manifest(
        config=config,
        annotations=annotations,
        documents=documents,
        candidate_inventory=candidates,
    )
    payload = canonical_p007_json(manifest)

    assert manifest.inventory_sha256 == "a" * 64
    assert manifest.candidate_feature_count == 3
    assert manifest.works[0].raw_sha256 == _sha(raw_a)
    assert manifest.works[0].token_count == 3
    assert b"alpha" not in payload
    assert raw_a not in payload
    assert b"/Users/" not in payload
    assert canonical_p007_json(manifest) == payload


def test_preparation_rejects_wrong_type_and_each_resource_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(PreprocessingError) as captured:
        prepare_text("not-bytes", expected_raw_sha256="0" * 64)  # type: ignore[arg-type]
    assert captured.value.code is PreprocessingErrorCode.PAYLOAD_TYPE

    limit_cases = (
        ("MAX_RAW_BYTES", 2, b"abc", PreprocessingErrorCode.INPUT_TOO_LARGE),
        ("MAX_TEXT_CHARACTERS", 2, b"abc", PreprocessingErrorCode.TEXT_TOO_LONG),
        ("MAX_TOKEN_COUNT", 1, b"alpha beta", PreprocessingErrorCode.TOKEN_LIMIT),
        ("MAX_PREPARED_BYTES", 3, b"alpha", PreprocessingErrorCode.PREPARED_TOO_LARGE),
    )
    for name, limit, raw, code in limit_cases:
        with monkeypatch.context() as scoped:
            scoped.setattr(preprocessing_module, name, limit)
            with pytest.raises(PreprocessingError) as captured:
                prepare_text(raw, expected_raw_sha256=_sha(raw))
            assert captured.value.code is code


def test_exclusion_parser_rejects_wrong_type_size_and_transport_width(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(PreprocessingError) as captured:
        parse_custom_exclusions("alpha")  # type: ignore[arg-type]
    assert captured.value.code is PreprocessingErrorCode.PAYLOAD_TYPE

    with monkeypatch.context() as scoped:
        scoped.setattr(preprocessing_module, "MAX_EXCLUSION_BYTES", 2)
        with pytest.raises(PreprocessingError) as captured:
            parse_custom_exclusions(b"abc")
        assert captured.value.code is PreprocessingErrorCode.EXCLUSIONS_TOO_LARGE

    with pytest.raises(PreprocessingError) as captured:
        parse_custom_exclusions(("a" * 65 + "\n").encode())
    assert captured.value.code is PreprocessingErrorCode.EXCLUSIONS_INVALID


def test_candidate_and_manifest_builders_fail_closed_on_invalid_bindings() -> None:
    raw = ("a" * 65 + " alpha beta").encode()
    first = prepare_document(
        raw,
        expected_raw_sha256=_sha(raw),
        annotation=_annotation(1),
    )
    second_raw = b"alpha gamma"
    second = prepare_document(
        second_raw,
        expected_raw_sha256=_sha(second_raw),
        annotation=_annotation(2),
    )
    candidates = build_candidate_inventory((first, second))
    assert candidates.transport_excluded_feature_count == 1

    with pytest.raises(CandidateInventoryError):
        build_candidate_inventory((first, second), max_features=1)

    annotations = CorpusAnalysisAnnotationsV1(
        schema_version="corpus-analysis-annotations-v1",
        inventory_sha256="b" * 64,
        annotations=(first.annotation, second.annotation),
    )
    config = build_preprocessing_config(parse_custom_exclusions(None))
    with pytest.raises(CandidateInventoryError):
        build_preprocessing_manifest(
            config=config,
            annotations=annotations,
            documents=(second, first),
            candidate_inventory=CandidateInventory(
                features=candidates.features,
                sha256=candidates.sha256,
                known_independent_work_count=2,
                transport_excluded_feature_count=1,
            ),
        )
