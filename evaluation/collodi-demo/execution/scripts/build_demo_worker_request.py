#!/usr/bin/env python3
"""Build the deterministic, results-blind Collodi teaching-demo request."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
MFW_GRID = (100, 300, 500, 1000)
OPAQUE_NAMESPACE = "delta-paper-collodi-demo-v1"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def opaque(prefix: str, semantic_key: str) -> str:
    payload = f"{OPAQUE_NAMESPACE}\0{prefix}\0{semantic_key}".encode()
    return f"{prefix}_{sha256_bytes(payload)}"


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


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def build_request(
    root: Path, project_root: Path | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    config_path = root / "config" / "collodi_demo_execution_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    documents_config = sorted(config["documents"], key=lambda item: item["order"])
    expected_order = list(range(1, len(documents_config) + 1))
    if [item["order"] for item in documents_config] != expected_order:
        raise ValueError("collodi-request-document-order-invalid")
    if tuple(config["mfw_grid"]) != MFW_GRID or config["culling_percent"] != 0:
        raise ValueError("collodi-request-configuration-mismatch")
    if config["distance"] != "classic_delta" or config["analysis_unit"] != "whole_text":
        raise ValueError("collodi-request-analysis-contract-mismatch")

    project_root = (project_root or root.parent).resolve()
    counters: dict[str, Counter[str]] = {}
    token_totals: dict[str, int] = {}
    clean_records: list[dict[str, Any]] = []
    aggregate: Counter[str] = Counter()
    for item in documents_config:
        clean_path = project_root / item["clean_path"]
        payload = clean_path.read_bytes()
        if sha256_bytes(payload) != item["expected_clean_sha256"]:
            raise ValueError(f"collodi-request-clean-sha-mismatch:{item['document_id']}")
        text = payload.decode("utf-8")
        if unicodedata.normalize("NFC", text) != text:
            raise ValueError(f"collodi-request-clean-not-nfc:{item['document_id']}")
        tokens = tokenize_surface_words(text)
        counter = Counter(tokens)
        if len(tokens) != item["expected_token_count"]:
            raise ValueError(f"collodi-request-token-count-mismatch:{item['document_id']}")
        if len(counter) != item["expected_unique_token_count"]:
            raise ValueError(f"collodi-request-unique-token-count-mismatch:{item['document_id']}")
        counters[item["document_id"]] = counter
        token_totals[item["document_id"]] = len(tokens)
        aggregate.update(counter)
        clean_records.append(
            {
                "clean_path": item["clean_path"],
                "clean_sha256": sha256_bytes(payload),
                "document_id": item["document_id"],
                "token_count": len(tokens),
                "unique_token_count": len(counter),
            }
        )

    feature_contract = config["feature_contract"]
    limit = int(feature_contract["candidate_feature_limit"])
    minimum = int(feature_contract["minimum_candidate_features"])
    maximum_bytes = int(feature_contract["maximum_feature_utf8_bytes"])
    ranked = sorted(aggregate, key=lambda token: (-aggregate[token], token.encode("utf-8")))
    candidate_features = [
        token for token in ranked if len(token.encode("utf-8")) <= maximum_bytes
    ][:limit]
    if not minimum <= len(candidate_features) <= limit:
        raise ValueError("collodi-request-candidate-feature-count-invalid")
    if len(candidate_features) < max(MFW_GRID):
        raise ValueError("collodi-request-candidate-feature-shortfall")

    config_sha = sha256_file(config_path)
    request_id = opaque("request", f"{config['dataset_id']}:{config_sha}")
    documents: list[dict[str, Any]] = []
    bindings: list[dict[str, str]] = []
    for item in documents_config:
        logical_id = item["document_id"]
        document_id = opaque("doc", logical_id)
        asset_ref = opaque("asset", f"{logical_id}:{item['expected_clean_sha256']}")
        work_ref = opaque(
            "work",
            f"{item['author']}:{item['title']}:{item['first_publication_candidate']}",
        )
        documents.append(
            {
                "asset_ref": asset_ref,
                "counts": [counters[logical_id][feature] for feature in candidate_features],
                "document_id": document_id,
                "role": "known",
                "token_total": token_totals[logical_id],
                "work_ref": work_ref,
            }
        )
        bindings.append(
            {
                "asset_ref": asset_ref,
                "document_id": document_id,
                "logical_document_id": logical_id,
                "work_ref": work_ref,
            }
        )

    fits: list[dict[str, Any]] = []
    cells: list[dict[str, str]] = []
    for mfw in MFW_GRID:
        fit_id = opaque("fit", f"{request_id}:{mfw}:0")
        fits.append({"culling_percent": 0, "fit_id": fit_id, "mfw": mfw})
        cells.append(
            {
                "cell_id": opaque("cell", f"{request_id}:{fit_id}:classic_delta"),
                "distance": "classic_delta",
                "fit_id": fit_id,
            }
        )

    request = {
        "analysis_unit": "whole_text",
        "candidate_features": candidate_features,
        "cells": cells,
        "documents": documents,
        "fits": fits,
        "limit_profile": "stylo-worker-contract-limits-v1",
        "request_id": request_id,
        "schema_version": "stylo-worker-input-v1",
        "seed": config["seed"],
    }
    metadata = {
        "bindings": bindings,
        "candidate_feature_count": len(candidate_features),
        "candidate_features_sha256": sha256_bytes(canonical_json(candidate_features)),
        "clean_documents": clean_records,
        "config_sha256": config_sha,
        "dataset_id": config["dataset_id"],
        "document_count": len(documents),
        "mfw_grid": list(MFW_GRID),
        "ordered_document_ids_sha256": sha256_bytes(
            canonical_json([item["document_id"] for item in documents])
        ),
        "schema_version": "collodi-demo-request-metadata-v1",
    }
    return request, metadata


def prepared_matrix(
    request: dict[str, Any], mfw: int
) -> tuple[list[str], list[list[float]], list[float], list[float]]:
    selected = request["candidate_features"][:mfw]
    frequencies = [
        [count * 100.0 / document["token_total"] for count in document["counts"][:mfw]]
        for document in request["documents"]
    ]
    means = [
        math.fsum(row[index] for row in frequencies) / len(frequencies)
        for index in range(mfw)
    ]
    deviations: list[float] = []
    for index, mean in enumerate(means):
        variance = math.fsum(
            (row[index] - mean) ** 2 for row in frequencies
        ) / (len(frequencies) - 1)
        deviations.append(math.sqrt(variance))
    if any(not math.isfinite(value) or value <= 0 for value in deviations):
        raise ValueError(f"collodi-request-nonpositive-standard-deviation:{mfw}")
    z_scores = [
        [(value - means[index]) / deviations[index] for index, value in enumerate(row)]
        for row in frequencies
    ]
    if any(not math.isfinite(value) for row in z_scores for value in row):
        raise ValueError(f"collodi-request-nonfinite-z-score:{mfw}")
    return selected, z_scores, means, deviations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = (args.output_dir or (root / "input")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    project_root = args.project_root.resolve() if args.project_root else None
    request, metadata = build_request(root, project_root)
    request_bytes = canonical_json(request)
    request_path = output_dir / "collodi_demo_worker_request.json"
    request_path.write_bytes(request_bytes)
    component = json.loads(
        (root / "config" / "collodi_demo_execution_config.json").read_text(encoding="utf-8")
    )["request_components"]["request"]
    (output_dir / component).write_bytes(request_bytes)

    if args.repo is not None:
        sys.path.insert(0, str(args.repo.resolve() / "src"))
        from delta_lemmata.stylo_contracts import canonical_worker_json, parse_worker_input

        parsed = parse_worker_input(request_bytes)
        if canonical_worker_json(parsed) != request_bytes:
            raise ValueError("collodi-request-frozen-contract-canonicalization-mismatch")

    metadata["request_bytes"] = len(request_bytes)
    metadata["request_sha256"] = sha256_bytes(request_bytes)
    matrix_records: list[dict[str, Any]] = []
    for mfw in MFW_GRID:
        selected, z_scores, means, deviations = prepared_matrix(request, mfw)
        mfw_dir = output_dir / f"mfw-{mfw:04d}"
        features_path = mfw_dir / "selected_features.json"
        matrix_path = mfw_dir / "prepared_z_scores.csv"
        stats_path = mfw_dir / "fit_statistics.csv"
        write_json(features_path, selected)
        write_csv(
            matrix_path,
            [["document_id", *selected]]
            + [
                [document["document_id"], *(format(value, ".17g") for value in row)]
                for document, row in zip(request["documents"], z_scores, strict=True)
            ],
        )
        write_csv(
            stats_path,
            [["feature", "mean", "sample_standard_deviation"]]
            + [
                [feature, format(mean, ".17g"), format(deviation, ".17g")]
                for feature, mean, deviation in zip(selected, means, deviations, strict=True)
            ],
        )
        matrix_records.append(
            {
                "fit_statistics_sha256": sha256_file(stats_path),
                "mfw": mfw,
                "prepared_z_scores_sha256": sha256_file(matrix_path),
                "selected_features_sha256": sha256_file(features_path),
            }
        )
    metadata["prepared_matrices"] = matrix_records
    write_json(output_dir / "request_metadata.json", metadata)
    print(f"request_sha256={metadata['request_sha256']}")
    print(f"request_bytes={len(request_bytes)}")
    print(f"candidate_features={metadata['candidate_feature_count']}")
    print("request_contract_validated=" + str(args.repo is not None).lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
