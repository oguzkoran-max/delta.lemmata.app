#!/usr/bin/env python3
"""Generate or verify the deterministic CC0 P006 whole-text fixture suite."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from delta_lemmata.stylo_contracts import (
    CellRequest,
    DistanceMeasure,
    DocumentCounts,
    DocumentRole,
    FitRequest,
    WorkerInputV1,
    canonical_worker_json,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v1"
LICENSE_TEXT = """SPDX-License-Identifier: CC0-1.0

P006 synthetic fixture data are dedicated to the public domain under the
Creative Commons CC0 1.0 Universal Public Domain Dedication.

The fixture counts are project-authored synthetic data. They contain no
literary text and are not derived from a research corpus.

Legal code: https://creativecommons.org/publicdomain/zero/1.0/legalcode
"""

CANDIDATE_FEATURES = (
    "canary_only",
    "delta",
    "éclair",
    "epsilon",
    "zeta",
    "gamma",
    "cafe",
)
KNOWN_ROWS = {
    "known-1": (0, 5, 10, 0, 40, 9, 20),
    "known-2": (0, 10, 20, 0, 30, 8, 15),
    "known-3": (0, 0, 30, 5, 20, 7, 10),
    "known-4": (0, 0, 40, 0, 10, 0, 5),
}
BASE_UNKNOWN = (100, 0, 0, 0, 0, 0, 0)
CANARY_UNKNOWN = (0, 0, 0, 0, 100, 0, 0)


def opaque(prefix: str, semantic_key: str) -> str:
    digest = hashlib.sha256(f"p006-v1:{semantic_key}".encode()).hexdigest()
    return f"{prefix}_{digest}"


def _documents(unknown_counts: tuple[int, ...]) -> tuple[DocumentCounts, ...]:
    rows = tuple(
        (semantic_key, DocumentRole.KNOWN, counts) for semantic_key, counts in KNOWN_ROWS.items()
    ) + (("unknown", DocumentRole.UNKNOWN, unknown_counts),)
    return tuple(
        DocumentCounts(
            document_id=opaque("doc", semantic_key),
            asset_ref=opaque("asset", semantic_key),
            work_ref=opaque("work", semantic_key),
            role=role,
            token_total=100,
            counts=counts,
        )
        for semantic_key, role, counts in rows
    )


def _fit(semantic_key: str, mfw: int, culling_percent: int) -> FitRequest:
    return FitRequest(
        fit_id=opaque("fit", semantic_key),
        mfw=mfw,
        culling_percent=culling_percent,
    )


def _cell(fit: FitRequest, distance: DistanceMeasure) -> CellRequest:
    return CellRequest(
        cell_id=opaque("cell", f"{fit.fit_id}:{distance.value}"),
        fit_id=fit.fit_id,
        distance=distance,
    )


def _request(
    semantic_key: str,
    unknown_counts: tuple[int, ...],
    fit_specs: tuple[tuple[int, int], ...],
    distances: tuple[DistanceMeasure, ...],
) -> WorkerInputV1:
    fits = tuple(
        _fit(f"mfw-{mfw}-culling-{culling_percent}", mfw, culling_percent)
        for mfw, culling_percent in fit_specs
    )
    return WorkerInputV1(
        schema_version="stylo-worker-input-v1",
        request_id=opaque("request", semantic_key),
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        candidate_features=CANDIDATE_FEATURES,
        documents=_documents(unknown_counts),
        fits=fits,
        cells=tuple(_cell(fit, distance) for fit in fits for distance in distances),
    )


def fixture_records() -> tuple[tuple[str, str, str, WorkerInputV1], ...]:
    complete_fits = ((6, 25), (5, 50), (4, 75), (3, 100))
    partial_fits = ((6, 25), (6, 26), (5, 50), (5, 51), (4, 75), (4, 76), (3, 100))
    all_distances = tuple(DistanceMeasure)
    return (
        (
            "complete-base.input.json",
            "complete-base",
            "Complete three-distance reference with an unknown-only feature canary.",
            _request("complete-base", BASE_UNKNOWN, complete_fits, all_distances),
        ),
        (
            "complete-canary.input.json",
            "complete-canary",
            "Known rows unchanged while the unknown row is deliberately altered.",
            _request("complete-canary", CANARY_UNKNOWN, complete_fits, all_distances),
        ),
        (
            "partial-boundaries.input.json",
            "partial-boundaries",
            "Culling boundary fixture with four complete and three insufficient fits.",
            _request(
                "partial-boundaries",
                BASE_UNKNOWN,
                partial_fits,
                (DistanceMeasure.CLASSIC_DELTA,),
            ),
        ),
    )


def generated_files() -> dict[str, bytes]:
    files: dict[str, bytes] = {"LICENSE": LICENSE_TEXT.encode()}
    fixtures: list[dict[str, str]] = []
    for filename, semantic_key, purpose, request in fixture_records():
        content = canonical_worker_json(request)
        digest = hashlib.sha256(content).hexdigest()
        files[filename] = content
        fixtures.append(
            {
                "expected_outcome": "partial"
                if semantic_key == "partial-boundaries"
                else "complete",
                "fixture_ref": opaque("fixture", semantic_key),
                "input_file": filename,
                "input_sha256": digest,
                "purpose": purpose,
            }
        )
    manifest = {
        "description": "Deterministic whole-text counts for P006 direct-stylo parity.",
        "fixtures": fixtures,
        "license": "CC0-1.0",
        "license_file": "LICENSE",
        "origin": "project-authored synthetic integer counts; no literary text",
        "schema_version": "p006-fixture-manifest-v1",
        "suite_id": "p006-whole-text-v1",
    }
    files["fixture-manifest.json"] = (
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if checked-in fixture bytes differ instead of writing them",
    )
    args = parser.parse_args()
    expected = generated_files()
    if args.check:
        actual_names = (
            {path.name for path in FIXTURE_DIR.iterdir()} if FIXTURE_DIR.is_dir() else set()
        )
        if actual_names != set(expected):
            return 1
        return int(
            any((FIXTURE_DIR / name).read_bytes() != content for name, content in expected.items())
        )
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in expected.items():
        (FIXTURE_DIR / name).write_bytes(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
