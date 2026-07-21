#!/usr/bin/env python3
"""Build the frozen literary corpus without computing stylometric results."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import statistics
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "DATA-ENDTOEND-LIT-V1"
PROFILE_ID = "delta-surface-words-v1"
MFW_GRID = (100, 300, 500, 1000)
MIN_TOKENS = 25_000
MAX_CANDIDATE_FEATURES = 20_000
MAX_FEATURE_BYTES = 64
PG_START_PREFIX = "*** START OF THE PROJECT GUTENBERG EBOOK"
PG_END_PREFIX = "*** END OF THE PROJECT GUTENBERG EBOOK"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def stable_token_sort(token: str) -> bytes:
    return token.encode("utf-8")


def tokenize_surface_words(text: str) -> list[str]:
    lowered = unicodedata.normalize("NFC", text.lower())
    tokens: list[str] = []
    current: list[str] = []

    for char in lowered:
        category = unicodedata.category(char)
        if current:
            if category.startswith("L") or category.startswith("M"):
                current.append(char)
            else:
                tokens.append("".join(current))
                current = []
        elif category.startswith("L"):
            current.append(char)

    if current:
        tokens.append("".join(current))
    return tokens


def exact_line_positions(lines: list[str], marker: str) -> list[int]:
    return [index for index, line in enumerate(lines) if line.strip() == marker]


def wrapper_positions(lines: list[str], prefix: str) -> list[int]:
    return [index for index, line in enumerate(lines) if line.strip().startswith(prefix)]


def remove_illustration_blocks(lines: list[str]) -> tuple[list[str], int, int]:
    output: list[str] = []
    block_count = 0
    line_count = 0
    index = 0

    while index < len(lines):
        line = lines[index]
        if not line.lstrip().startswith("[Illustrazione:"):
            output.append(line)
            index += 1
            continue

        block_count += 1
        block_lines = 0
        while True:
            if index >= len(lines):
                raise ValueError("Unclosed [Illustrazione: ...] block")
            current = lines[index]
            block_lines += 1
            line_count += 1
            if "]" in current:
                trailing = current.split("]", 1)[1]
                if trailing.strip():
                    raise ValueError("Illustration block closes before non-whitespace text")
                index += 1
                break
            if block_lines > 50:
                raise ValueError("Illustration block exceeds the 50-line safety limit")
            index += 1

    return output, block_count, line_count


def clean_document(row: dict[str, str]) -> tuple[str, dict[str, object]]:
    raw_path = ROOT / row["raw_path"]
    raw_bytes = raw_path.read_bytes()
    actual_sha = sha256_bytes(raw_bytes)
    if actual_sha != row["expected_raw_sha256"]:
        raise ValueError(
            f"{row['document_id']}: raw SHA mismatch: {actual_sha} != "
            f"{row['expected_raw_sha256']}"
        )

    crlf_count = raw_bytes.count(b"\r\n")
    lone_cr_count = raw_bytes.count(b"\r") - crlf_count
    leading_bom_removed = False
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raw_bytes = raw_bytes[3:]
        leading_bom_removed = True

    text = raw_bytes.decode("utf-8", errors="strict")
    if "\ufeff" in text:
        raise ValueError(f"{row['document_id']}: embedded BOM detected")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    nfc_text = unicodedata.normalize("NFC", text)
    nfc_changed = nfc_text != text
    lines = nfc_text.split("\n")

    pg_starts = wrapper_positions(lines, PG_START_PREFIX)
    pg_ends = wrapper_positions(lines, PG_END_PREFIX)
    if len(pg_starts) != 1 or len(pg_ends) != 1:
        raise ValueError(
            f"{row['document_id']}: expected one PG start/end marker, got "
            f"{len(pg_starts)}/{len(pg_ends)}"
        )

    starts = exact_line_positions(lines, row["body_start_marker"])
    ends = exact_line_positions(lines, row["body_end_marker"])
    if len(starts) != 1 or len(ends) != 1:
        raise ValueError(
            f"{row['document_id']}: body markers are not unique exact stripped lines: "
            f"start={starts}, end={ends}"
        )
    start_index = starts[0]
    end_index = ends[0]
    if not (pg_starts[0] < start_index <= end_index < pg_ends[0]):
        raise ValueError(f"{row['document_id']}: body markers fall outside PG wrapper")

    body_lines = lines[start_index : end_index + 1]
    cleaned_lines, illustration_blocks, illustration_lines = remove_illustration_blocks(
        body_lines
    )
    clean_text = "\n".join(cleaned_lines).strip("\n") + "\n"
    if unicodedata.normalize("NFC", clean_text) != clean_text:
        raise ValueError(f"{row['document_id']}: clean text is not NFC")

    audit = {
        "raw_sha256": actual_sha,
        "raw_bytes": len(raw_path.read_bytes()),
        "crlf_replaced": crlf_count,
        "lone_cr_replaced": lone_cr_count,
        "leading_bom_removed": leading_bom_removed,
        "nfc_normalization_changed_text": nfc_changed,
        "source_start_line_1_based": start_index + 1,
        "source_end_line_1_based": end_index + 1,
        "source_body_line_count": end_index - start_index + 1,
        "illustration_blocks_removed": illustration_blocks,
        "illustration_lines_removed": illustration_lines,
    }
    return clean_text, audit


def relative_frequency(count: int, total: int) -> float:
    return count / total * 100.0


def build_overlap_rows(
    ordered_rows: list[dict[str, str]], tokens_by_id: dict[str, list[str]]
) -> list[dict[str, object]]:
    ngram_sets: dict[str, set[tuple[str, ...]]] = {}
    for row in ordered_rows:
        document_id = row["document_id"]
        tokens = tokens_by_id[document_id]
        ngram_sets[document_id] = {
            tuple(tokens[index : index + 10]) for index in range(max(0, len(tokens) - 9))
        }

    output: list[dict[str, object]] = []
    for left, right in itertools.combinations(ordered_rows, 2):
        left_id = left["document_id"]
        right_id = right["document_id"]
        left_grams = ngram_sets[left_id]
        right_grams = ngram_sets[right_id]
        shared = len(left_grams.intersection(right_grams))
        denominator = min(len(left_grams), len(right_grams))
        fraction = shared / denominator if denominator else 0.0
        output.append(
            {
                "left_document_id": left_id,
                "right_document_id": right_id,
                "left_unique_token_10grams": len(left_grams),
                "right_unique_token_10grams": len(right_grams),
                "shared_exact_token_10grams": shared,
                "shared_over_smaller_fraction": f"{fraction:.12f}",
                "review_status": (
                    "pending_human_review" if shared else "not_required_no_shared_10grams"
                ),
            }
        )
    return output


def manifest_candidates() -> list[Path]:
    excluded = {"package_manifest.csv"}
    candidates = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name in excluded:
            continue
        relative = path.relative_to(ROOT)
        if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
            continue
        candidates.append(path)
    return sorted(candidates, key=lambda item: item.relative_to(ROOT).as_posix())


def main() -> int:
    register_path = ROOT / "source" / "source_register.csv"
    rows = read_csv(register_path)
    if len(rows) != 6:
        raise ValueError(f"Expected 6 source records, found {len(rows)}")
    if {row["dataset_id"] for row in rows} != {DATASET_ID}:
        raise ValueError("Source register contains an unexpected dataset_id")

    raw_manifest: list[dict[str, object]] = []
    clean_manifest: list[dict[str, object]] = []
    metadata_rows: list[dict[str, object]] = []
    cleaning_rows: list[dict[str, object]] = []
    tokens_by_id: dict[str, list[str]] = {}
    counters_by_id: dict[str, Counter[str]] = {}
    clean_hashes: list[str] = []

    for order, row in enumerate(rows, start=1):
        for source_field in ("metadata_html_path", "metadata_rdf_path", "headers_path"):
            if not (ROOT / row[source_field]).is_file():
                raise FileNotFoundError(f"Missing source artifact: {row[source_field]}")

        raw_path = ROOT / row["raw_path"]
        clean_relative = Path("clean") / f"{raw_path.stem}.clean.txt"
        clean_path = ROOT / clean_relative
        clean_text, audit = clean_document(row)
        clean_path.write_text(clean_text, encoding="utf-8", newline="\n")

        clean_bytes = clean_path.read_bytes()
        clean_sha = sha256_bytes(clean_bytes)
        tokens = tokenize_surface_words(clean_text)
        counter = Counter(tokens)
        tokens_by_id[row["document_id"]] = tokens
        counters_by_id[row["document_id"]] = counter
        clean_hashes.append(clean_sha)

        raw_manifest.append(
            {
                "document_id": row["document_id"],
                "path": row["raw_path"],
                "bytes": audit["raw_bytes"],
                "sha256": audit["raw_sha256"],
                "source_text_url": row["source_text_url"],
                "retrieved_on": row["retrieved_on"],
            }
        )
        clean_manifest.append(
            {
                "document_id": row["document_id"],
                "path": clean_relative.as_posix(),
                "bytes": len(clean_bytes),
                "sha256": clean_sha,
                "line_count": clean_text.count("\n"),
                "token_count": len(tokens),
                "unique_token_count": len(counter),
                "illustration_blocks_removed": audit["illustration_blocks_removed"],
            }
        )
        metadata_rows.append(
            {
                "document_order": order,
                "dataset_id": DATASET_ID,
                "document_id": row["document_id"],
                "author": row["author"],
                "author_birth_year": row["author_birth_year"],
                "author_death_year": row["author_death_year"],
                "title": row["title"],
                "language": row["language"],
                "pg_ebook_id": row["pg_ebook_id"],
                "analysis_unit": "whole_text",
                "corpus_role": "known_engine_parity",
                "clean_path": clean_relative.as_posix(),
                "token_count": len(tokens),
                "unique_token_count": len(counter),
            }
        )
        cleaning_rows.append(
            {
                "document_id": row["document_id"],
                "raw_path": row["raw_path"],
                "clean_path": clean_relative.as_posix(),
                "body_start_marker": row["body_start_marker"],
                "body_end_marker": row["body_end_marker"],
                **audit,
                "modernization": "none",
                "stopword_removal": "none",
                "lemmatization_or_stemming": "none",
                "terminal_newline": "single_lf",
            }
        )

    if len(set(clean_hashes)) != len(clean_hashes):
        raise ValueError("Exact duplicate clean files detected")

    aggregate: Counter[str] = Counter()
    for counter in counters_by_id.values():
        aggregate.update(counter)
    ranked = sorted(aggregate.items(), key=lambda item: (-item[1], stable_token_sort(item[0])))
    eligible_ranked = [
        (token, count)
        for token, count in ranked
        if len(token.encode("utf-8")) <= MAX_FEATURE_BYTES
    ][:MAX_CANDIDATE_FEATURES]

    top_limit = max(MFW_GRID)
    feature_rows: list[dict[str, object]] = []
    for rank, (token, aggregate_count) in enumerate(eligible_ranked[:top_limit], start=1):
        frequencies = [
            relative_frequency(counters_by_id[row["document_id"]][token], len(tokens_by_id[row["document_id"]]))
            for row in rows
        ]
        sample_sd = statistics.stdev(frequencies)
        feature_rows.append(
            {
                "rank": rank,
                "token": token,
                "token_utf8_bytes": len(token.encode("utf-8")),
                "aggregate_count": aggregate_count,
                "sample_standard_deviation": format(sample_sd, ".17g"),
                "finite_sample_standard_deviation": str(math.isfinite(sample_sd)).lower(),
                "positive_sample_standard_deviation": str(sample_sd > 0).lower(),
            }
        )

    eligibility_rows: list[dict[str, object]] = []
    for mfw in MFW_GRID:
        selected = feature_rows[:mfw]
        non_positive = sum(
            1 for item in selected if item["positive_sample_standard_deviation"] != "true"
        )
        non_finite = sum(
            1 for item in selected if item["finite_sample_standard_deviation"] != "true"
        )
        eligible = len(selected) == mfw and non_positive == 0 and non_finite == 0
        eligibility_rows.append(
            {
                "mfw": mfw,
                "available_candidate_features": len(eligible_ranked),
                "selected_features": len(selected),
                "non_positive_standard_deviation_features": non_positive,
                "non_finite_standard_deviation_features": non_finite,
                "eligible": str(eligible).lower(),
            }
        )

    overlap_rows = build_overlap_rows(rows, tokens_by_id)
    minimum_tokens = min(len(tokens_by_id[row["document_id"]]) for row in rows)
    all_mfw_eligible = all(item["eligible"] == "true" for item in eligibility_rows)
    checks = {
        "document_count_is_six": len(rows) == 6,
        "unique_author_count_is_six": len({row["author"] for row in rows}) == 6,
        "all_documents_at_least_25000_tokens": minimum_tokens >= MIN_TOKENS,
        "all_clean_files_have_unique_sha256": len(set(clean_hashes)) == len(clean_hashes),
        "at_least_1000_candidate_features": len(eligible_ranked) >= top_limit,
        "all_preregistered_mfw_settings_eligible": all_mfw_eligible,
    }
    eligible_for_grid = all(checks.values())

    write_csv(
        ROOT / "raw_manifest.csv",
        ["document_id", "path", "bytes", "sha256", "source_text_url", "retrieved_on"],
        raw_manifest,
    )
    write_csv(
        ROOT / "clean_manifest.csv",
        [
            "document_id",
            "path",
            "bytes",
            "sha256",
            "line_count",
            "token_count",
            "unique_token_count",
            "illustration_blocks_removed",
        ],
        clean_manifest,
    )
    write_csv(
        ROOT / "metadata.csv",
        [
            "document_order",
            "dataset_id",
            "document_id",
            "author",
            "author_birth_year",
            "author_death_year",
            "title",
            "language",
            "pg_ebook_id",
            "analysis_unit",
            "corpus_role",
            "clean_path",
            "token_count",
            "unique_token_count",
        ],
        metadata_rows,
    )
    cleaning_fields = [
        "document_id",
        "raw_path",
        "clean_path",
        "body_start_marker",
        "body_end_marker",
        "raw_sha256",
        "raw_bytes",
        "crlf_replaced",
        "lone_cr_replaced",
        "leading_bom_removed",
        "nfc_normalization_changed_text",
        "source_start_line_1_based",
        "source_end_line_1_based",
        "source_body_line_count",
        "illustration_blocks_removed",
        "illustration_lines_removed",
        "modernization",
        "stopword_removal",
        "lemmatization_or_stemming",
        "terminal_newline",
    ]
    write_csv(ROOT / "cleaning_log.csv", cleaning_fields, cleaning_rows)
    write_csv(
        ROOT / "feature_eligibility.csv",
        [
            "mfw",
            "available_candidate_features",
            "selected_features",
            "non_positive_standard_deviation_features",
            "non_finite_standard_deviation_features",
            "eligible",
        ],
        eligibility_rows,
    )
    write_csv(
        ROOT / "ranked_feature_qc.csv",
        [
            "rank",
            "token",
            "token_utf8_bytes",
            "aggregate_count",
            "sample_standard_deviation",
            "finite_sample_standard_deviation",
            "positive_sample_standard_deviation",
        ],
        feature_rows,
    )
    write_csv(
        ROOT / "overlap_report.csv",
        [
            "left_document_id",
            "right_document_id",
            "left_unique_token_10grams",
            "right_unique_token_10grams",
            "shared_exact_token_10grams",
            "shared_over_smaller_fraction",
            "review_status",
        ],
        overlap_rows,
    )

    corpus_qc = {
        "dataset_id": DATASET_ID,
        "profile_id": PROFILE_ID,
        "document_count": len(rows),
        "unique_author_count": len({row["author"] for row in rows}),
        "minimum_document_token_count": minimum_tokens,
        "aggregate_unique_token_count": len(aggregate),
        "candidate_feature_count_after_64_byte_limit": len(eligible_ranked),
        "preregistered_mfw_grid": list(MFW_GRID),
        "checks": checks,
        "eligible_for_preregistered_mfw_grid": eligible_for_grid,
        "distance_computed": False,
        "mds_computed": False,
        "stylo_run": False,
        "delta_run": False,
        "selection_based_on_results": False,
    }
    write_json(ROOT / "corpus_qc.json", corpus_qc)

    lines = [
        "# Deterministik temizleme gunlugu",
        "",
        f"**Veri:** `{DATASET_ID}`  ",
        f"**Profil:** `{PROFILE_ID}`  ",
        "**Sonuc siniri:** Uzaklik, MDS, Delta ve R stylo sonucu uretilmedi.",
        "",
        "| Belge | Kaynak satirlari | CRLF | NFC degisti | Gorsel blogu | Token |",
        "|---|---:|---:|---|---:|---:|",
    ]
    token_totals = {item["document_id"]: item["token_count"] for item in clean_manifest}
    for item in cleaning_rows:
        lines.append(
            "| {document_id} | {source_start_line_1_based}-{source_end_line_1_based} | "
            "{crlf_replaced} | {nfc_normalization_changed_text} | "
            "{illustration_blocks_removed} | {tokens} |".format(
                tokens=token_totals[item["document_id"]], **item
            )
        )
    lines.extend(
        [
            "",
            "Uygulanan islemler: kayitli govde sinirini alma; CRLF/CR satir "
            "sonlarini LF'ye cevirme; Unicode NFC; acik `[Illustrazione: ...]` "
            "bloklarini cikarma; tek son LF yazma.",
            "",
            "Uygulanmayan islemler: imla modernlestirme, stopword cikarma, "
            "lemmatization, stemming, konuya gore secim, uzaklik veya grafik "
            "sonucuna gore belge degistirme.",
            "",
            f"On kayitli MFW izgara uygunlugu: `{str(eligible_for_grid).lower()}`.",
            "Bu deger motor parity testinin gectigi anlamina gelmez.",
            "",
        ]
    )
    (ROOT / "cleaning_log.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")

    package_rows = []
    for path in manifest_candidates():
        relative = path.relative_to(ROOT).as_posix()
        package_rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    write_csv(ROOT / "package_manifest.csv", ["path", "bytes", "sha256"], package_rows)

    print(f"dataset={DATASET_ID}")
    print(f"documents={len(rows)}")
    print(f"minimum_tokens={minimum_tokens}")
    print(f"candidate_features={len(eligible_ranked)}")
    print(f"eligible_for_preregistered_mfw_grid={str(eligible_for_grid).lower()}")
    print("stylometric_results_computed=false")
    return 0 if eligible_for_grid else 1


if __name__ == "__main__":
    raise SystemExit(main())
