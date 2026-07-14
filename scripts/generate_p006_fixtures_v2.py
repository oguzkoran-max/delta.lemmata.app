#!/usr/bin/env python3
"""Generate or verify the adversarial CC0 P006 whole-text fixture suite."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
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
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v2"
LICENSE_TEXT = """SPDX-License-Identifier: CC0-1.0

P006 v2 synthetic fixture data are dedicated to the public domain under the
Creative Commons CC0 1.0 Universal Public Domain Dedication.

The fixture counts are project-authored synthetic data. They contain no
literary text and are not derived from a research corpus.

Legal code: https://creativecommons.org/publicdomain/zero/1.0/legalcode
"""

CANDIDATE_FEATURES = (
    "unknown_a_only",
    "beta",
    "alpha",
    "gamma",
    "delta",
    "epsilon",
    "zeta",
    "unknown_b_only",
)
KNOWN_ROWS = {
    "known-1": (80, (0, 16, 24, 8, 4, 2, 0, 0)),
    "known-2": (120, (0, 30, 18, 12, 0, 6, 3, 0)),
    "known-3": (200, (0, 20, 40, 50, 10, 0, 5, 0)),
    "known-4": (320, (0, 80, 32, 16, 20, 8, 0, 0)),
}
BASE_UNKNOWN_ROWS = {
    "unknown-a": (150, (60, 10, 30, 5, 0, 0, 0, 0)),
    "unknown-b": (240, (0, 48, 12, 24, 12, 6, 3, 100)),
}
CANARY_UNKNOWN_ROWS = {
    "unknown-a": (150, (0, 60, 6, 15, 6, 3, 0, 60)),
    "unknown-b": (240, (80, 12, 72, 6, 0, 0, 0, 50)),
}
BASE_ORDER = ("known-1", "unknown-a", "known-2", "known-3", "unknown-b", "known-4")
PERMUTED_ORDER = (
    "unknown-b",
    "known-3",
    "known-1",
    "unknown-a",
    "known-4",
    "known-2",
)
FIT_SPECS = ((6, 0), (5, 50), (4, 75), (3, 100))


def opaque(prefix: str, semantic_key: str) -> str:
    digest = hashlib.sha256(f"p006-v2:{semantic_key}".encode()).hexdigest()
    return f"{prefix}_{digest}"


def _documents(
    unknown_rows: Mapping[str, tuple[int, tuple[int, ...]]],
    order: tuple[str, ...],
) -> tuple[DocumentCounts, ...]:
    rows = {
        **{
            key: (DocumentRole.KNOWN, token_total, counts)
            for key, (token_total, counts) in KNOWN_ROWS.items()
        },
        **{
            key: (DocumentRole.UNKNOWN, token_total, counts)
            for key, (token_total, counts) in unknown_rows.items()
        },
    }
    return tuple(
        DocumentCounts(
            document_id=opaque("doc", semantic_key),
            asset_ref=opaque("asset", semantic_key),
            work_ref=opaque("work", semantic_key),
            role=rows[semantic_key][0],
            token_total=rows[semantic_key][1],
            counts=rows[semantic_key][2],
        )
        for semantic_key in order
    )


def _fit(mfw: int, culling_percent: int) -> FitRequest:
    semantic_key = f"mfw-{mfw}-culling-{culling_percent}"
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
    unknown_rows: Mapping[str, tuple[int, tuple[int, ...]]],
    order: tuple[str, ...],
) -> WorkerInputV1:
    fits = tuple(_fit(mfw, culling_percent) for mfw, culling_percent in FIT_SPECS)
    return WorkerInputV1(
        schema_version="stylo-worker-input-v1",
        request_id=opaque("request", semantic_key),
        limit_profile="stylo-worker-contract-limits-v1",
        analysis_unit="whole_text",
        seed=20260713,
        candidate_features=CANDIDATE_FEATURES,
        documents=_documents(unknown_rows, order),
        fits=fits,
        cells=tuple(_cell(fit, distance) for fit in fits for distance in DistanceMeasure),
    )


def fixture_records() -> tuple[tuple[str, str, str, WorkerInputV1], ...]:
    return (
        (
            "normalization-base.input.json",
            "normalization-base",
            "Unequal document totals and two interleaved unknown documents.",
            _request("normalization-base", BASE_UNKNOWN_ROWS, BASE_ORDER),
        ),
        (
            "normalization-canary.input.json",
            "normalization-canary",
            "Known rows fixed while both interleaved unknown rows are altered.",
            _request("normalization-canary", CANARY_UNKNOWN_ROWS, BASE_ORDER),
        ),
        (
            "order-permutation.input.json",
            "order-permutation",
            "The base documents are reordered without changing roles, totals, or counts.",
            _request("order-permutation", BASE_UNKNOWN_ROWS, PERMUTED_ORDER),
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
                "expected_outcome": "complete",
                "fixture_ref": opaque("fixture", semantic_key),
                "input_file": filename,
                "input_sha256": digest,
                "purpose": purpose,
            }
        )
    manifest = {
        "description": ("Adversarial whole-text counts for normalization and role-order parity."),
        "fixtures": fixtures,
        "license": "CC0-1.0",
        "license_file": "LICENSE",
        "origin": "project-authored synthetic integer counts; no literary text",
        "schema_version": "p006-fixture-manifest-v1",
        "suite_id": "p006-whole-text-v2",
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
