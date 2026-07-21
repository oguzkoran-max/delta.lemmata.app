#!/usr/bin/env python3
"""Build the results-blind literary worker request and prepared-matrix bindings."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
MFW_GRID = (100, 300, 500, 1000)
MAX_CANDIDATE_FEATURES = 20_000
REQUEST_COMPONENT = "28e9d3d83efa686b8b51b80eccd9b4f3439aeb56141e459abd97729c9c5b9184"


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
    payload = f"delta-paper-literary-parity-v1\0{prefix}\0{semantic_key}".encode()
    return f"{prefix}_{sha256_bytes(payload)}"


def load_tokenizer(root: Path):
    module_path = root / "scripts" / "build_corpus.py"
    spec = importlib.util.spec_from_file_location("literary_build_corpus", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("request-build-tokenizer-load-failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.tokenize_surface_words


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def build_request(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config_path = root / "config" / "parity_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    metadata = sorted(read_csv(root / "metadata.csv"), key=lambda row: int(row["document_order"]))
    expected_order = [row["document_id"] for row in metadata]
    if expected_order != config["document_order"]:
        raise ValueError("request-build-document-order-mismatch")
    if tuple(config["mfw_grid"]) != MFW_GRID or config["culling_percent"] != 0:
        raise ValueError("request-build-configuration-mismatch")

    tokenize = load_tokenizer(root)
    counters: dict[str, Counter[str]] = {}
    token_totals: dict[str, int] = {}
    aggregate: Counter[str] = Counter()
    for row in metadata:
        clean_path = root / row["clean_path"]
        tokens = tokenize(clean_path.read_text(encoding="utf-8"))
        if len(tokens) != int(row["token_count"]):
            raise ValueError(f"request-build-token-count-mismatch:{row['document_id']}")
        counter = Counter(tokens)
        counters[row["document_id"]] = counter
        token_totals[row["document_id"]] = len(tokens)
        aggregate.update(counter)

    ranked = sorted(aggregate, key=lambda token: (-aggregate[token], token.encode("utf-8")))
    candidate_features = [
        token for token in ranked if len(token.encode("utf-8")) <= 64
    ][:MAX_CANDIDATE_FEATURES]
    if len(candidate_features) != MAX_CANDIDATE_FEATURES:
        raise ValueError("request-build-candidate-feature-shortfall")

    config_sha = sha256_file(config_path)
    request_id = opaque("request", f"{config['dataset_id']}:{config_sha}")
    documents: list[dict[str, Any]] = []
    bindings: list[dict[str, str]] = []
    for row in metadata:
        logical_id = row["document_id"]
        document_id = opaque("doc", logical_id)
        asset_ref = opaque("asset", f"{logical_id}:{sha256_file(root / row['clean_path'])}")
        work_ref = opaque("work", f"{row['author']}:{row['title']}:{row['pg_ebook_id']}")
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
        "seed": 20260713,
    }
    metadata_record = {
        "bindings": bindings,
        "candidate_feature_count": len(candidate_features),
        "config_sha256": config_sha,
        "dataset_id": config["dataset_id"],
        "document_count": len(documents),
        "mfw_grid": list(MFW_GRID),
        "schema_version": "literary-parity-request-metadata-v1",
    }
    return request, metadata_record


def prepared_matrix(
    request: dict[str, Any], mfw: int
) -> tuple[list[str], list[list[float]], list[float], list[float]]:
    selected = request["candidate_features"][:mfw]
    frequencies = [
        [count * 100.0 / document["token_total"] for count in document["counts"][:mfw]]
        for document in request["documents"]
    ]
    means = [math.fsum(row[index] for row in frequencies) / len(frequencies) for index in range(mfw)]
    deviations = []
    for index, mean in enumerate(means):
        variance = math.fsum(
            (row[index] - mean) ** 2 for row in frequencies
        ) / (len(frequencies) - 1)
        deviations.append(math.sqrt(variance))
    if any(not math.isfinite(value) or value <= 0 for value in deviations):
        raise ValueError(f"request-build-nonpositive-standard-deviation:{mfw}")
    z_scores = [
        [(value - means[index]) / deviations[index] for index, value in enumerate(row)]
        for row in frequencies
    ]
    if any(not math.isfinite(value) for row in z_scores for value in row):
        raise ValueError(f"request-build-nonfinite-z-score:{mfw}")
    return selected, z_scores, means, deviations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = (args.output_dir or (root / "input")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    request, metadata_record = build_request(root)
    request_bytes = canonical_json(request)
    request_path = output_dir / "literary_worker_request.json"
    request_path.write_bytes(request_bytes)
    (output_dir / REQUEST_COMPONENT).write_bytes(request_bytes)

    if args.repo is not None:
        import sys

        sys.path.insert(0, str(args.repo.resolve() / "src"))
        from delta_lemmata.stylo_contracts import canonical_worker_json, parse_worker_input

        parsed = parse_worker_input(request_bytes)
        if canonical_worker_json(parsed) != request_bytes:
            raise ValueError("request-build-frozen-contract-canonicalization-mismatch")

    metadata_record["request_bytes"] = len(request_bytes)
    metadata_record["request_sha256"] = sha256_bytes(request_bytes)
    label_bytes = canonical_json([item["document_id"] for item in request["documents"]])
    metadata_record["ordered_document_ids_sha256"] = sha256_bytes(label_bytes)
    candidate_bytes = canonical_json(request["candidate_features"])
    metadata_record["candidate_features_sha256"] = sha256_bytes(candidate_bytes)

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
    metadata_record["prepared_matrices"] = matrix_records
    write_json(output_dir / "request_metadata.json", metadata_record)
    print(f"request_sha256={metadata_record['request_sha256']}")
    print(f"request_bytes={len(request_bytes)}")
    print("request_contract_validated=" + str(args.repo is not None).lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
