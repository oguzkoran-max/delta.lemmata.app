from __future__ import annotations

import hashlib

import pytest

from delta_lemmata.corpus import PurposeId
from delta_lemmata.corpus_health import (
    WorkHealthContext,
    assess_corpus_health,
    longest_common_contiguous_run,
    near_duplicate_similarity,
)
from delta_lemmata.corpus_health_models import (
    CorpusHealthFindingCode,
    CorpusHealthReadiness,
    HealthSeverity,
)
from delta_lemmata.preprocessing import (
    CandidateInventory,
    build_candidate_inventory,
    build_preprocessing_config,
    build_preprocessing_manifest,
    parse_custom_exclusions,
    prepare_document,
)
from delta_lemmata.preprocessing_models import (
    AnalysisRole,
    CorpusAnalysisAnnotation,
    CorpusAnalysisAnnotationsV1,
    OcrStatus,
    ParatextStatus,
    TextUnit,
)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _word(prefix: str, index: int) -> str:
    suffix = ""
    value = index
    while True:
        suffix = chr(ord("a") + (value % 26)) + suffix
        value = (value // 26) - 1
        if value < 0:
            return prefix + suffix


def _document(index: int, tokens: list[str], *, role: AnalysisRole = AnalysisRole.KNOWN):
    raw = " ".join(tokens).encode()
    annotation = CorpusAnalysisAnnotation(
        document_id=f"doc_{index:064x}",
        asset_id=f"asset_work_{index:02d}",
        work_id=f"work_{index:02d}",
        analysis_role=role,
        text_unit=TextUnit.INDEPENDENT_WORK,
        parent_work_id=None,
        ocr_status=OcrStatus.NOT_OCR,
        paratext_status=ParatextStatus.ABSENT,
    )
    return prepare_document(raw, expected_raw_sha256=_sha(raw), annotation=annotation)


def _health(
    documents: tuple,
    *,
    purpose: PurposeId = PurposeId.TEXT_PROXIMITY,
    contexts: tuple[WorkHealthContext, ...] | None = None,
):
    annotations, config, candidates, manifest = _inputs(documents)
    return assess_corpus_health(
        purpose=purpose,
        config=config,
        annotations=annotations,
        manifest=manifest,
        documents=documents,
        candidate_inventory=candidates,
        work_contexts=contexts or (),
    )


def _inputs(documents: tuple):
    annotations = CorpusAnalysisAnnotationsV1(
        schema_version="corpus-analysis-annotations-v1",
        inventory_sha256="1" * 64,
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
    return annotations, config, candidates, manifest


def _codes(report) -> set[CorpusHealthFindingCode]:
    return {finding.code for finding in report.findings}


def test_similarity_helpers_are_deterministic_and_use_exact_token_runs() -> None:
    base = tuple(_word("token", index) for index in range(100))
    changed = (*base[:50], "changed", *base[51:])
    assert near_duplicate_similarity(base, changed) == pytest.approx(91 / 101)
    assert near_duplicate_similarity(base, changed) >= 0.90
    assert near_duplicate_similarity(("short",), ("other",)) == 0.0

    shared = tuple(_word("shared", index) for index in range(200))
    left = ("left", *shared, "tail-left")
    right = ("right-a", "right-b", *shared, "tail-right")
    assert longest_common_contiguous_run(left, right) == 200
    assert longest_common_contiguous_run(left, ()) == 0
    assert longest_common_contiguous_run(("a", "a"), ("a", "a")) == 2
    assert longest_common_contiguous_run(("a", "b", "b"), ("b", "b")) == 2


def test_health_blocks_exact_duplicates_and_too_few_known_works() -> None:
    duplicate_a = _document(1, ["same", "text", "twice"])
    duplicate_b = _document(2, ["same", "text", "twice"])
    report = _health((duplicate_a, duplicate_b))

    assert report.readiness is CorpusHealthReadiness.BLOCKED
    assert report.blocker_count == 1
    assert CorpusHealthFindingCode.EXACT_DUPLICATE in _codes(report)

    one_known = _document(1, ["alpha", "beta"])
    unknown = _document(2, ["alpha", "gamma"], role=AnalysisRole.UNKNOWN)
    report = _health((one_known, unknown))
    assert CorpusHealthFindingCode.TOO_FEW_KNOWN_WORKS in _codes(report)
    assert report.blocker_count >= 1


def test_health_marks_empty_and_non_independent_units_as_blockers() -> None:
    empty = _document(1, ["123", "---"])
    normal = _document(2, ["alpha", "beta", "gamma"])
    excerpt_annotation = normal.annotation.model_copy(
        update={
            "text_unit": TextUnit.EXCERPT,
            "parent_work_id": "work_parent",
        }
    )
    excerpt = normal.__class__(annotation=excerpt_annotation, prepared=normal.prepared)

    report = _health((empty, excerpt))
    assert CorpusHealthFindingCode.EMPTY_PREPARED_WORK in _codes(report)
    assert CorpusHealthFindingCode.NON_INDEPENDENT_UNIT in _codes(report)
    assert report.readiness is CorpusHealthReadiness.BLOCKED


def test_health_warns_at_declared_similarity_length_and_group_boundaries() -> None:
    base = [_word("token", index) for index in range(100)]
    near = [*base[:50], "changed", *base[51:]]
    long = [_word("long", index) for index in range(401)]
    short = [_word("short", index) for index in range(100)]
    documents = (
        _document(1, base),
        _document(2, near),
        _document(3, long),
        _document(4, short),
        _document(5, [_word("five", index) for index in range(100)]),
    )
    contexts = (
        WorkHealthContext(work_id="work_01", group_label="large"),
        WorkHealthContext(work_id="work_02", group_label="large"),
        WorkHealthContext(work_id="work_03", group_label="large"),
        WorkHealthContext(work_id="work_04", group_label="large"),
        WorkHealthContext(work_id="work_05", group_label="small"),
    )
    report = _health(documents, contexts=contexts)
    codes = _codes(report)
    assert CorpusHealthFindingCode.NEAR_DUPLICATE in codes
    assert CorpusHealthFindingCode.LENGTH_IMBALANCE in codes
    assert CorpusHealthFindingCode.GROUP_IMBALANCE in codes
    assert report.strong_warning_count >= 3
    assert all(
        finding.severity is HealthSeverity.STRONG_WARNING
        for finding in report.findings
        if finding.code
        in {
            CorpusHealthFindingCode.NEAR_DUPLICATE,
            CorpusHealthFindingCode.LENGTH_IMBALANCE,
            CorpusHealthFindingCode.GROUP_IMBALANCE,
        }
    )


def test_exact_thresholds_do_not_warn_until_the_policy_is_crossed() -> None:
    documents = (
        _document(1, [_word("alpha", index) for index in range(400)]),
        _document(2, [_word("beta", index) for index in range(100)]),
        _document(3, [_word("gamma", index) for index in range(100)]),
        _document(4, [_word("delta", index) for index in range(100)]),
    )
    contexts = (
        WorkHealthContext(work_id="work_01", group_label="large"),
        WorkHealthContext(work_id="work_02", group_label="large"),
        WorkHealthContext(work_id="work_03", group_label="large"),
        WorkHealthContext(work_id="work_04", group_label="small"),
    )
    report = _health(documents, contexts=contexts)
    assert CorpusHealthFindingCode.LENGTH_IMBALANCE not in _codes(report)
    assert CorpusHealthFindingCode.GROUP_IMBALANCE not in _codes(report)


def test_shared_passage_warns_at_200_tokens_or_twenty_percent() -> None:
    shared_200 = [_word("shared", index) for index in range(200)]
    first = _document(1, ["first", *shared_200, "endfirst"])
    second = _document(2, ["second", *shared_200, "endsecond"])
    report = _health((first, second))
    finding = next(
        item for item in report.findings if item.code is CorpusHealthFindingCode.SHARED_PASSAGE
    )
    assert finding.observed_count == 200

    shared_20 = [_word("twenty", index) for index in range(20)]
    left = _document(1, [*shared_20, *[_word("left", index) for index in range(80)]])
    right = _document(2, [*shared_20, *[_word("right", index) for index in range(100)]])
    report = _health((left, right))
    assert CorpusHealthFindingCode.SHARED_PASSAGE in _codes(report)


def test_style_over_time_requires_three_chronology_points_and_six_works() -> None:
    documents = tuple(
        _document(index, [_word("word", index), "common", _word("extra", index)])
        for index in range(1, 6)
    )
    contexts = tuple(
        WorkHealthContext(
            work_id=f"work_{index:02d}",
            chronology_point="early" if index < 4 else "late",
        )
        for index in range(1, 6)
    )
    report = _health(
        documents,
        purpose=PurposeId.STYLE_OVER_TIME,
        contexts=contexts,
    )
    assert CorpusHealthFindingCode.TOO_FEW_INDEPENDENT_WORKS in _codes(report)
    assert CorpusHealthFindingCode.TOO_FEW_CHRONOLOGY_POINTS in _codes(report)


def test_mfw_capacity_is_visible_without_silent_substitution() -> None:
    documents = (
        _document(1, [_word("alpha", index) for index in range(150)]),
        _document(2, [_word("beta", index) for index in range(150)]),
    )
    report = _health(documents)
    assert [(item.requested_mfw, item.available) for item in report.mfw_capacity] == [
        (100, True),
        (300, True),
        (500, False),
        (1000, False),
    ]
    assert CorpusHealthFindingCode.MFW_UNAVAILABLE in _codes(report)


def test_health_report_is_content_free_and_reproducible() -> None:
    documents = (
        _document(1, ["privatealpha", "common", "one"]),
        _document(2, ["privatebeta", "common", "two"]),
    )
    first = _health(documents)
    second = _health(documents)
    assert first == second
    payload = first.model_dump_json()
    assert "privatealpha" not in payload
    assert "privatebeta" not in payload
    assert "/Users/" not in payload


def test_health_rejects_annotation_manifest_and_context_binding_mismatches() -> None:
    documents = (
        _document(1, ["alpha", "beta"]),
        _document(2, ["gamma", "delta"]),
    )
    annotations, config, candidates, manifest = _inputs(documents)

    wrong_annotations = annotations.model_copy(
        update={"annotations": tuple(reversed(annotations.annotations))}
    )
    with pytest.raises(ValueError, match="P007_HEALTH_BINDING_MISMATCH"):
        assess_corpus_health(
            purpose=PurposeId.TEXT_PROXIMITY,
            config=config,
            annotations=wrong_annotations,
            manifest=manifest,
            documents=documents,
            candidate_inventory=candidates,
        )

    wrong_manifest = manifest.model_copy(update={"works": tuple(reversed(manifest.works))})
    with pytest.raises(ValueError, match="P007_HEALTH_BINDING_MISMATCH"):
        assess_corpus_health(
            purpose=PurposeId.TEXT_PROXIMITY,
            config=config,
            annotations=annotations,
            manifest=wrong_manifest,
            documents=documents,
            candidate_inventory=candidates,
        )

    duplicate_contexts = (
        WorkHealthContext(work_id="work_01"),
        WorkHealthContext(work_id="work_01"),
    )
    with pytest.raises(ValueError, match="P007_HEALTH_CONTEXT_DUPLICATE"):
        assess_corpus_health(
            purpose=PurposeId.TEXT_PROXIMITY,
            config=config,
            annotations=annotations,
            manifest=manifest,
            documents=documents,
            candidate_inventory=candidates,
            work_contexts=duplicate_contexts,
        )


def test_health_blocks_duplicate_independence_keys_and_skips_self_comparison() -> None:
    first = _document(1, ["alpha", "beta"])
    second = _document(2, ["gamma", "delta"])
    duplicate = second.__class__(
        annotation=second.annotation.model_copy(update={"work_id": first.annotation.work_id}),
        prepared=second.prepared,
    )
    documents = (first, duplicate)
    annotations = CorpusAnalysisAnnotationsV1(
        schema_version="corpus-analysis-annotations-v1",
        inventory_sha256="1" * 64,
        annotations=tuple(document.annotation for document in documents),
    )
    config = build_preprocessing_config(parse_custom_exclusions(None))
    candidates = CandidateInventory(
        features=("alpha", "beta", "delta", "gamma"),
        sha256="a" * 64,
        known_independent_work_count=1,
        transport_excluded_feature_count=0,
    )
    manifest = build_preprocessing_manifest(
        config=config,
        annotations=annotations,
        documents=documents,
        candidate_inventory=candidates,
    )
    report = assess_corpus_health(
        purpose=PurposeId.TEXT_PROXIMITY,
        config=config,
        annotations=annotations,
        manifest=manifest,
        documents=documents,
        candidate_inventory=candidates,
    )

    assert CorpusHealthFindingCode.DUPLICATE_INDEPENDENCE_UNIT in _codes(report)
    assert CorpusHealthFindingCode.EXACT_DUPLICATE not in _codes(report)


def test_health_blocks_corpora_larger_than_the_worker_contract() -> None:
    documents = tuple(
        _document(
            index,
            [_word(f"work{_word('i', index)}", token) for token in range(3)],
        )
        for index in range(1, 52)
    )
    report = _health(documents)
    finding = next(
        item for item in report.findings if item.code is CorpusHealthFindingCode.TOO_MANY_DOCUMENTS
    )
    assert finding.observed_count == 51
    assert report.readiness is CorpusHealthReadiness.BLOCKED


def test_six_work_capacity_exposes_transport_exclusions_without_mfw_substitution() -> None:
    documents = []
    for index in range(1, 7):
        tokens = [_word(f"work{_word('i', index)}token", token) for token in range(200)]
        if index == 1:
            tokens.append("a" * 65)
        documents.append(_document(index, tokens))

    report = _health(tuple(documents))
    codes = _codes(report)
    assert CorpusHealthFindingCode.TOO_FEW_INDEPENDENT_WORKS not in codes
    assert CorpusHealthFindingCode.MFW_UNAVAILABLE not in codes
    assert CorpusHealthFindingCode.TRANSPORT_FEATURE_EXCLUDED in codes
    assert all(item.available for item in report.mfw_capacity)
