"""Deterministic, content-free P007 corpus-health assessment."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Literal

from delta_lemmata.corpus_health_models import (
    CorpusHealthFinding,
    CorpusHealthFindingCode,
    CorpusHealthReadiness,
    CorpusHealthReportV1,
    GroupCount,
    HealthSeverity,
    MfwCapacity,
)
from delta_lemmata.corpus_models import PurposeId
from delta_lemmata.preprocessing import CandidateInventory, PreparedDocument
from delta_lemmata.preprocessing_models import (
    MAX_P006_DOCUMENTS,
    AnalysisRole,
    CorpusAnalysisAnnotationsV1,
    PreprocessingConfigV1,
    PreprocessingManifestV1,
    TextUnit,
    canonical_p007_json,
)

NEAR_DUPLICATE_THRESHOLD = 0.90
SHARED_PASSAGE_TOKEN_THRESHOLD = 200
SHARED_PASSAGE_RATIO_THRESHOLD = 0.20
LENGTH_RATIO_THRESHOLD = 4.0
GROUP_RATIO_THRESHOLD = 3.0
MIN_INDEPENDENT_WORKS = 6
MIN_CHRONOLOGY_POINTS = 3
MIN_KNOWN_WORKS = 2
GUIDED_MFW: tuple[Literal[100, 300, 500, 1000], ...] = (100, 300, 500, 1000)


@dataclass(frozen=True, slots=True)
class WorkHealthContext:
    work_id: str
    group_label: str | None = None
    chronology_point: str | None = None
    chronology_certainty: str | None = None
    edition_context: str | None = None
    genre: str | None = None
    audience: str | None = None
    source_type: str | None = None
    adaptation: str | None = None
    collection: str | None = None
    ocr_status: str | None = None
    paratext_status: str | None = None
    curation_state: str | None = None


_CONFOUND_FACTORS: tuple[tuple[CorpusHealthFindingCode, str, frozenset[str]], ...] = (
    (CorpusHealthFindingCode.OCR_CONFOUND, "ocr_status", frozenset({"unknown", "unreviewed"})),
    (CorpusHealthFindingCode.PARATEXT_CONFOUND, "paratext_status", frozenset({"unknown"})),
    (CorpusHealthFindingCode.CURATION_CONFOUND, "curation_state", frozenset()),
    (CorpusHealthFindingCode.EDITION_CONFOUND, "edition_context", frozenset({"unknown"})),
    (CorpusHealthFindingCode.GENRE_CONFOUND, "genre", frozenset({"unknown"})),
    (CorpusHealthFindingCode.AUDIENCE_CONFOUND, "audience", frozenset({"unknown"})),
    (CorpusHealthFindingCode.SOURCE_CONFOUND, "source_type", frozenset({"unknown"})),
    (CorpusHealthFindingCode.ADAPTATION_CONFOUND, "adaptation", frozenset({"unknown"})),
    (CorpusHealthFindingCode.COLLECTION_CONFOUND, "collection", frozenset({"unknown"})),
)


def _shingle_digest(tokens: tuple[str, ...]) -> bytes:
    encoded = bytearray()
    for token in tokens:
        value = token.encode("utf-8")
        encoded.extend(len(value).to_bytes(4, byteorder="big"))
        encoded.extend(value)
    return hashlib.sha256(encoded).digest()


def _shingle_set(tokens: tuple[str, ...], *, width: int = 5) -> frozenset[bytes]:
    if len(tokens) < width:
        return frozenset()
    return frozenset(
        _shingle_digest(tokens[index : index + width]) for index in range(len(tokens) - width + 1)
    )


def near_duplicate_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    """Return Jaccard similarity over unique SHA-256 token 5-shingles."""

    left_shingles = _shingle_set(left)
    right_shingles = _shingle_set(right)
    if not left_shingles or not right_shingles:
        return 0.0
    return len(left_shingles & right_shingles) / len(left_shingles | right_shingles)


def _token_symbols(
    left: tuple[str, ...], right: tuple[str, ...]
) -> tuple[list[bytes], list[bytes]]:
    digest_to_token: dict[bytes, str] = {}
    for token in (*left, *right):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        previous = digest_to_token.setdefault(digest, token)
        if previous != token:  # pragma: no cover - cryptographic collision guard
            raise RuntimeError("TOKEN_DIGEST_COLLISION")
    return (
        [hashlib.sha256(token.encode("utf-8")).digest() for token in left],
        [hashlib.sha256(token.encode("utf-8")).digest() for token in right],
    )


def longest_common_contiguous_run(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    """Return exact longest contiguous token overlap using a suffix automaton."""

    if not left or not right:
        return 0
    left_symbols, right_symbols = _token_symbols(left, right)
    transitions: list[dict[bytes, int]] = [{}]
    links = [-1]
    lengths = [0]
    last = 0
    for symbol in left_symbols:
        current = len(transitions)
        transitions.append({})
        lengths.append(lengths[last] + 1)
        links.append(0)
        pointer = last
        while pointer >= 0 and symbol not in transitions[pointer]:
            transitions[pointer][symbol] = current
            pointer = links[pointer]
        if pointer < 0:
            links[current] = 0
        else:
            target = transitions[pointer][symbol]
            if lengths[pointer] + 1 == lengths[target]:
                links[current] = target
            else:
                clone = len(transitions)
                transitions.append(dict(transitions[target]))
                lengths.append(lengths[pointer] + 1)
                links.append(links[target])
                while pointer >= 0 and transitions[pointer].get(symbol) == target:
                    transitions[pointer][symbol] = clone
                    pointer = links[pointer]
                links[target] = clone
                links[current] = clone
        last = current

    state = 0
    matched = 0
    longest = 0
    for symbol in right_symbols:
        while state and symbol not in transitions[state]:
            state = links[state]
            matched = lengths[state]
        if symbol in transitions[state]:
            state = transitions[state][symbol]
            matched += 1
        else:
            state = 0
            matched = 0
        longest = max(longest, matched)
    return longest


def _finding_id(
    code: CorpusHealthFindingCode,
    subjects: tuple[str, ...],
    *,
    observed_count: int | None = None,
    threshold_count: int | None = None,
    observed_ratio: float | None = None,
    threshold_ratio: float | None = None,
) -> str:
    payload = json.dumps(
        {
            "code": code.value,
            "observed_count": observed_count,
            "observed_ratio": observed_ratio,
            "subjects": subjects,
            "threshold_count": threshold_count,
            "threshold_ratio": threshold_ratio,
        },
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return "finding_" + hashlib.sha256(payload).hexdigest()


def _finding(
    code: CorpusHealthFindingCode,
    severity: HealthSeverity,
    subjects: tuple[str, ...] = (),
    *,
    observed_count: int | None = None,
    threshold_count: int | None = None,
    observed_ratio: float | None = None,
    threshold_ratio: float | None = None,
) -> CorpusHealthFinding:
    rounded_observed = None if observed_ratio is None else round(observed_ratio, 6)
    rounded_threshold = None if threshold_ratio is None else round(threshold_ratio, 6)
    return CorpusHealthFinding(
        finding_id=_finding_id(
            code,
            subjects,
            observed_count=observed_count,
            threshold_count=threshold_count,
            observed_ratio=rounded_observed,
            threshold_ratio=rounded_threshold,
        ),
        code=code,
        severity=severity,
        subject_refs=subjects,
        observed_count=observed_count,
        threshold_count=threshold_count,
        observed_ratio=rounded_observed,
        threshold_ratio=rounded_threshold,
    )


def _group_ref(label: str) -> str:
    return "group_" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _factor_subjects(
    contexts: tuple[WorkHealthContext, ...],
    field_name: str,
    *,
    risky_values: frozenset[str],
) -> tuple[str, ...]:
    values = tuple((context.work_id, getattr(context, field_name)) for context in contexts)
    if not any(value is not None for _work_id, value in values):
        return ()
    normalized = tuple(
        (work_id, "__missing__" if value is None else value) for work_id, value in values
    )
    distinct = {value for _work_id, value in normalized}
    if len(distinct) > 1:
        return tuple(sorted(work_id for work_id, _value in normalized))
    return tuple(
        sorted(
            work_id
            for work_id, value in normalized
            if value == "__missing__" or value in risky_values
        )
    )


def _metadata_confound_findings(
    *,
    purpose: PurposeId,
    known_work_ids: frozenset[str],
    context_by_work: dict[str, WorkHealthContext],
) -> tuple[CorpusHealthFinding, ...]:
    contexts = tuple(
        context_by_work[work_id] for work_id in sorted(known_work_ids) if work_id in context_by_work
    )
    findings: list[CorpusHealthFinding] = []
    for code, field_name, risky_values in _CONFOUND_FACTORS:
        subjects = _factor_subjects(contexts, field_name, risky_values=risky_values)
        if subjects:
            findings.append(
                _finding(
                    code,
                    HealthSeverity.STRONG_WARNING,
                    subjects,
                    observed_count=len(subjects),
                )
            )

    certainty_subjects = _factor_subjects(
        contexts,
        "chronology_certainty",
        risky_values=frozenset({"unknown", "approximate", "range"}),
    )
    points = {
        context.chronology_point for context in contexts if context.chronology_point is not None
    }
    if purpose is not PurposeId.STYLE_OVER_TIME and len(points) > 1:
        chronology_subjects = tuple(context.work_id for context in contexts)
    else:
        chronology_subjects = certainty_subjects
    if chronology_subjects:
        findings.append(
            _finding(
                CorpusHealthFindingCode.CHRONOLOGY_CONFOUND,
                HealthSeverity.STRONG_WARNING,
                tuple(sorted(chronology_subjects)),
                observed_count=len(chronology_subjects),
            )
        )
    return tuple(findings)


def assess_corpus_health(
    *,
    purpose: PurposeId,
    config: PreprocessingConfigV1,
    annotations: CorpusAnalysisAnnotationsV1,
    manifest: PreprocessingManifestV1,
    documents: tuple[PreparedDocument, ...],
    candidate_inventory: CandidateInventory,
    work_contexts: tuple[WorkHealthContext, ...] = (),
) -> CorpusHealthReportV1:
    """Assess the accepted P007 v1 gates without exporting source text."""

    if tuple(document.annotation for document in documents) != annotations.annotations:
        raise ValueError("P007_HEALTH_BINDING_MISMATCH")
    if tuple(item.document_id for item in manifest.works) != tuple(
        document.annotation.document_id for document in documents
    ):
        raise ValueError("P007_HEALTH_BINDING_MISMATCH")
    context_by_work = {context.work_id: context for context in work_contexts}
    if len(context_by_work) != len(work_contexts):
        raise ValueError("P007_HEALTH_CONTEXT_DUPLICATE")

    findings: list[CorpusHealthFinding] = []
    independent = tuple(
        document
        for document in documents
        if document.annotation.text_unit is TextUnit.INDEPENDENT_WORK
    )
    known_independent = tuple(
        document
        for document in independent
        if document.annotation.analysis_role is AnalysisRole.KNOWN
    )
    independent_keys = {document.independence_key for document in independent}
    known_keys = {document.independence_key for document in known_independent}

    for document in documents:
        work_ref = (document.annotation.work_id,)
        if document.prepared.token_count == 0:
            findings.append(
                _finding(
                    CorpusHealthFindingCode.EMPTY_PREPARED_WORK, HealthSeverity.BLOCKER, work_ref
                )
            )
        if document.annotation.text_unit is not TextUnit.INDEPENDENT_WORK:
            findings.append(
                _finding(
                    CorpusHealthFindingCode.NON_INDEPENDENT_UNIT,
                    HealthSeverity.BLOCKER,
                    work_ref,
                )
            )

    duplicate_key_counts = Counter(document.independence_key for document in known_independent)
    for key, count in sorted(duplicate_key_counts.items()):
        if count > 1:
            findings.append(
                _finding(
                    CorpusHealthFindingCode.DUPLICATE_INDEPENDENCE_UNIT,
                    HealthSeverity.BLOCKER,
                    (key,),
                    observed_count=count,
                    threshold_count=1,
                )
            )
    if len(known_keys) < MIN_KNOWN_WORKS:
        findings.append(
            _finding(
                CorpusHealthFindingCode.TOO_FEW_KNOWN_WORKS,
                HealthSeverity.BLOCKER,
                observed_count=len(known_keys),
                threshold_count=MIN_KNOWN_WORKS,
            )
        )
    if len(documents) > MAX_P006_DOCUMENTS:
        findings.append(
            _finding(
                CorpusHealthFindingCode.TOO_MANY_DOCUMENTS,
                HealthSeverity.BLOCKER,
                observed_count=len(documents),
                threshold_count=MAX_P006_DOCUMENTS,
            )
        )
    if len(candidate_inventory.features) < 2:
        findings.append(
            _finding(
                CorpusHealthFindingCode.NO_RUNNABLE_FEATURES,
                HealthSeverity.BLOCKER,
                observed_count=len(candidate_inventory.features),
                threshold_count=2,
            )
        )

    pair_documents = tuple(
        sorted(independent, key=lambda document: document.annotation.document_id)
    )
    for left, right in combinations(pair_documents, 2):
        if left.independence_key == right.independence_key:
            continue
        subjects = tuple(sorted((left.annotation.work_id, right.annotation.work_id)))
        if left.prepared.prepared_sha256 == right.prepared.prepared_sha256:
            findings.append(
                _finding(
                    CorpusHealthFindingCode.EXACT_DUPLICATE,
                    HealthSeverity.BLOCKER,
                    subjects,
                )
            )
            continue
        similarity = near_duplicate_similarity(left.prepared.tokens, right.prepared.tokens)
        if similarity >= NEAR_DUPLICATE_THRESHOLD:
            findings.append(
                _finding(
                    CorpusHealthFindingCode.NEAR_DUPLICATE,
                    HealthSeverity.STRONG_WARNING,
                    subjects,
                    observed_ratio=similarity,
                    threshold_ratio=NEAR_DUPLICATE_THRESHOLD,
                )
            )
        longest_run = longest_common_contiguous_run(left.prepared.tokens, right.prepared.tokens)
        shorter = min(left.prepared.token_count, right.prepared.token_count)
        shared_ratio = longest_run / shorter if shorter else 0.0
        if (
            longest_run >= SHARED_PASSAGE_TOKEN_THRESHOLD
            or shared_ratio >= SHARED_PASSAGE_RATIO_THRESHOLD
        ):
            findings.append(
                _finding(
                    CorpusHealthFindingCode.SHARED_PASSAGE,
                    HealthSeverity.STRONG_WARNING,
                    subjects,
                    observed_count=longest_run,
                    threshold_count=SHARED_PASSAGE_TOKEN_THRESHOLD,
                    observed_ratio=shared_ratio,
                    threshold_ratio=SHARED_PASSAGE_RATIO_THRESHOLD,
                )
            )

    if len(independent_keys) < MIN_INDEPENDENT_WORKS:
        findings.append(
            _finding(
                CorpusHealthFindingCode.TOO_FEW_INDEPENDENT_WORKS,
                HealthSeverity.STRONG_WARNING,
                observed_count=len(independent_keys),
                threshold_count=MIN_INDEPENDENT_WORKS,
            )
        )

    chronology_points = {
        context_by_work[document.annotation.work_id].chronology_point
        for document in known_independent
        if document.annotation.work_id in context_by_work
        and context_by_work[document.annotation.work_id].chronology_point is not None
    }
    if purpose is PurposeId.STYLE_OVER_TIME and len(chronology_points) < MIN_CHRONOLOGY_POINTS:
        findings.append(
            _finding(
                CorpusHealthFindingCode.TOO_FEW_CHRONOLOGY_POINTS,
                HealthSeverity.STRONG_WARNING,
                observed_count=len(chronology_points),
                threshold_count=MIN_CHRONOLOGY_POINTS,
            )
        )

    findings.extend(
        _metadata_confound_findings(
            purpose=purpose,
            known_work_ids=frozenset(document.annotation.work_id for document in known_independent),
            context_by_work=context_by_work,
        )
    )

    non_empty = tuple(document for document in known_independent if document.prepared.token_count)
    if len(non_empty) >= 2:
        shortest = min(non_empty, key=lambda document: document.prepared.token_count)
        longest = max(non_empty, key=lambda document: document.prepared.token_count)
        length_ratio = longest.prepared.token_count / shortest.prepared.token_count
        if length_ratio > LENGTH_RATIO_THRESHOLD:
            findings.append(
                _finding(
                    CorpusHealthFindingCode.LENGTH_IMBALANCE,
                    HealthSeverity.STRONG_WARNING,
                    (longest.annotation.work_id, shortest.annotation.work_id),
                    observed_ratio=length_ratio,
                    threshold_ratio=LENGTH_RATIO_THRESHOLD,
                )
            )

    group_counter = Counter(
        context_by_work[document.annotation.work_id].group_label
        for document in known_independent
        if document.annotation.work_id in context_by_work
        and context_by_work[document.annotation.work_id].group_label is not None
    )
    group_counts = tuple(
        GroupCount(group_ref=_group_ref(label), independent_work_count=count)
        for label, count in sorted(group_counter.items())
        if label is not None
    )
    if len(group_counter) >= 2:
        group_ratio = max(group_counter.values()) / min(group_counter.values())
        if group_ratio > GROUP_RATIO_THRESHOLD:
            findings.append(
                _finding(
                    CorpusHealthFindingCode.GROUP_IMBALANCE,
                    HealthSeverity.STRONG_WARNING,
                    observed_ratio=group_ratio,
                    threshold_ratio=GROUP_RATIO_THRESHOLD,
                )
            )

    mfw_capacity = tuple(
        MfwCapacity(
            requested_mfw=value,
            available_features=len(candidate_inventory.features),
            available=len(candidate_inventory.features) >= value,
        )
        for value in GUIDED_MFW
    )
    unavailable = tuple(item.requested_mfw for item in mfw_capacity if not item.available)
    if unavailable:
        findings.append(
            _finding(
                CorpusHealthFindingCode.MFW_UNAVAILABLE,
                HealthSeverity.STRONG_WARNING,
                observed_count=len(candidate_inventory.features),
                threshold_count=min(unavailable),
            )
        )
    if candidate_inventory.transport_excluded_feature_count:
        findings.append(
            _finding(
                CorpusHealthFindingCode.TRANSPORT_FEATURE_EXCLUDED,
                HealthSeverity.NOTE,
                observed_count=candidate_inventory.transport_excluded_feature_count,
                threshold_count=64,
            )
        )
    findings.append(
        _finding(
            CorpusHealthFindingCode.PREPARATION_SUMMARY,
            HealthSeverity.NOTE,
            observed_count=sum(document.prepared.token_count for document in documents),
        )
    )

    severity_order = {
        HealthSeverity.BLOCKER: 0,
        HealthSeverity.STRONG_WARNING: 1,
        HealthSeverity.NOTE: 2,
    }
    ordered_findings = tuple(
        sorted(
            findings,
            key=lambda item: (
                severity_order[item.severity],
                item.code.value,
                item.subject_refs,
                item.finding_id,
            ),
        )
    )
    blocker_count = sum(item.severity is HealthSeverity.BLOCKER for item in ordered_findings)
    warning_count = sum(item.severity is HealthSeverity.STRONG_WARNING for item in ordered_findings)
    note_count = sum(item.severity is HealthSeverity.NOTE for item in ordered_findings)
    config_sha256 = hashlib.sha256(canonical_p007_json(config)).hexdigest()
    manifest_sha256 = hashlib.sha256(canonical_p007_json(manifest)).hexdigest()
    report_seed = json.dumps(
        {
            "annotations_sha256": manifest.annotations_sha256,
            "candidate_inventory_sha256": candidate_inventory.sha256,
            "config_sha256": config_sha256,
            "findings": [item.finding_id for item in ordered_findings],
            "inventory_sha256": annotations.inventory_sha256,
            "manifest_sha256": manifest_sha256,
            "purpose": purpose.value,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return CorpusHealthReportV1(
        schema_version="corpus-health-report-v1",
        report_id="health_" + hashlib.sha256(report_seed).hexdigest(),
        severity_profile="delta-corpus-health-v1",
        purpose=purpose,
        config_sha256=config_sha256,
        inventory_sha256=annotations.inventory_sha256,
        annotations_sha256=manifest.annotations_sha256,
        manifest_sha256=manifest_sha256,
        candidate_inventory_sha256=candidate_inventory.sha256,
        candidate_feature_count=len(candidate_inventory.features),
        independent_work_count=len(independent_keys),
        known_independent_work_count=len(known_keys),
        chronology_point_count=len(chronology_points),
        readiness=(
            CorpusHealthReadiness.READY if blocker_count == 0 else CorpusHealthReadiness.BLOCKED
        ),
        blocker_count=blocker_count,
        strong_warning_count=warning_count,
        note_count=note_count,
        group_counts=group_counts,
        mfw_capacity=mfw_capacity,
        findings=ordered_findings,
    )


__all__ = [
    "GROUP_RATIO_THRESHOLD",
    "GUIDED_MFW",
    "LENGTH_RATIO_THRESHOLD",
    "MIN_CHRONOLOGY_POINTS",
    "MIN_INDEPENDENT_WORKS",
    "MIN_KNOWN_WORKS",
    "NEAR_DUPLICATE_THRESHOLD",
    "SHARED_PASSAGE_RATIO_THRESHOLD",
    "SHARED_PASSAGE_TOKEN_THRESHOLD",
    "WorkHealthContext",
    "assess_corpus_health",
    "longest_common_contiguous_run",
    "near_duplicate_similarity",
]
