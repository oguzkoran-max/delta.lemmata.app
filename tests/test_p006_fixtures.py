from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import pytest

import delta_lemmata.stylo_contracts as contracts
from delta_lemmata.stylo_contracts import DistanceMeasure, DocumentRole, parse_worker_input

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v1"


def _manifest() -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / "fixture-manifest.json").read_text(encoding="utf-8"))


def _requests_by_name() -> dict[str, contracts.WorkerInputV1]:
    return {
        entry["input_file"]: parse_worker_input((FIXTURE_DIR / entry["input_file"]).read_bytes())
        for entry in _manifest()["fixtures"]
    }


def test_p006_fixture_manifest_binds_cc0_synthetic_inputs() -> None:
    manifest = _manifest()
    assert manifest == {
        "description": "Deterministic whole-text counts for P006 direct-stylo parity.",
        "fixtures": manifest["fixtures"],
        "license": "CC0-1.0",
        "license_file": "LICENSE",
        "origin": "project-authored synthetic integer counts; no literary text",
        "schema_version": "p006-fixture-manifest-v1",
        "suite_id": "p006-whole-text-v1",
    }
    assert (
        (FIXTURE_DIR / "LICENSE")
        .read_text(encoding="utf-8")
        .startswith("SPDX-License-Identifier: CC0-1.0\n")
    )
    assert tuple(entry["input_file"] for entry in manifest["fixtures"]) == (
        "complete-base.input.json",
        "complete-canary.input.json",
        "partial-boundaries.input.json",
    )
    for entry in manifest["fixtures"]:
        content = (FIXTURE_DIR / entry["input_file"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == entry["input_sha256"]
        assert entry["fixture_ref"].startswith("fixture_")
        assert len(entry["fixture_ref"]) == len("fixture_") + 64
        parse_worker_input(content)


def test_complete_fixture_pair_changes_only_unknown_request_material() -> None:
    requests = _requests_by_name()
    base = requests["complete-base.input.json"]
    canary = requests["complete-canary.input.json"]
    assert base.candidate_features == canary.candidate_features
    assert base.fits == canary.fits
    assert base.cells == canary.cells
    assert base.documents[:-1] == canary.documents[:-1]
    assert base.documents[-1].role is DocumentRole.UNKNOWN
    assert canary.documents[-1].role is DocumentRole.UNKNOWN
    assert base.documents[-1].counts != canary.documents[-1].counts

    ranked = contracts._ranked_features(base)
    assert tuple(
        (item.feature, item.known_total_count, item.known_document_count) for item in ranked
    ) == (
        ("zeta", 100, 4),
        ("éclair", 100, 4),
        ("cafe", 50, 4),
        ("gamma", 24, 3),
        ("delta", 15, 2),
        ("epsilon", 5, 1),
    )
    assert contracts._ranked_features(canary) == ranked


def test_p006_fixture_cells_predeclare_complete_and_boundary_experiments() -> None:
    requests = _requests_by_name()
    complete = requests["complete-base.input.json"]
    assert tuple((fit.mfw, fit.culling_percent) for fit in complete.fits) == (
        (6, 25),
        (5, 50),
        (4, 75),
        (3, 100),
    )
    assert len(complete.cells) == 12
    assert {cell.distance for cell in complete.cells} == set(DistanceMeasure)

    partial = requests["partial-boundaries.input.json"]
    assert tuple((fit.mfw, fit.culling_percent) for fit in partial.fits) == (
        (6, 25),
        (6, 26),
        (5, 50),
        (5, 51),
        (4, 75),
        (4, 76),
        (3, 100),
    )
    assert len(partial.cells) == 7
    assert {cell.distance for cell in partial.cells} == {DistanceMeasure.CLASSIC_DELTA}

    ranked = contracts._ranked_features(partial)
    known_count = sum(document.role is DocumentRole.KNOWN for document in partial.documents)
    eligible_counts = tuple(
        len(
            contracts._eligible_features(
                ranked,
                known_count=known_count,
                culling_percent=fit.culling_percent,
            )
        )
        for fit in partial.fits
    )
    assert eligible_counts == (6, 5, 5, 4, 4, 3, 3)
    assert tuple(
        count >= fit.mfw for count, fit in zip(eligible_counts, partial.fits, strict=True)
    ) == (
        True,
        False,
        True,
        False,
        True,
        False,
        True,
    )


def test_direct_oracle_is_independent_and_calls_only_locked_stylo_distances() -> None:
    source = (ROOT / "scripts" / "oracles" / "p006-direct-stylo-v1.R").read_text(encoding="utf-8")
    assert "stylo::dist.delta(z_scores, scale = FALSE)" in source
    assert "stylo::dist.eder(z_scores, scale = FALSE)" in source
    assert "stylo::dist.cosine(z_scores)" in source
    assert 'Sys.chmod(temporary, mode = "0644")' in source
    assert 'Sys.chmod(temporary, mode = "0600")' not in source
    for forbidden in (
        "perform.delta",
        "dist.wurzburg",
        "stylo_worker",
        "delta_lemmata",
        "source(",
        "system(",
        "system2(",
    ):
        assert forbidden not in source


def test_oracle_freeze_requires_two_distinct_byte_identical_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    freeze_module = importlib.import_module("freeze_p006_oracle")
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "result.json").write_bytes(b"same\n")
    (second / "result.json").write_bytes(b"same\n")

    with pytest.raises(ValueError, match="P006_ORACLE_RUNS_NOT_DISTINCT"):
        freeze_module._require_byte_identical(first, first)
    first_snapshot, second_snapshot = freeze_module._require_byte_identical(first, second)
    assert first_snapshot == second_snapshot

    (second / "result.json").write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="P006_ORACLE_RUN_MISMATCH"):
        freeze_module._require_byte_identical(first, second)
