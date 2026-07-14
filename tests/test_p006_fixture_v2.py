from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import pytest

import delta_lemmata.stylo_contracts as contracts
from delta_lemmata.stylo_contracts import DistanceMeasure, DocumentRole

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "stylo" / "p006-whole-text-v2"


@pytest.fixture(scope="module")
def validator() -> Any:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    return importlib.import_module("validate_p006_fixture_v2")


def test_v2_manifest_binds_exact_cc0_adversarial_inputs(validator: Any) -> None:
    manifest = json.loads((FIXTURE_DIR / "fixture-manifest.json").read_text(encoding="utf-8"))
    assert manifest == {
        "description": "Adversarial whole-text counts for normalization and role-order parity.",
        "fixtures": manifest["fixtures"],
        "license": "CC0-1.0",
        "license_file": "LICENSE",
        "origin": "project-authored synthetic integer counts; no literary text",
        "schema_version": "p006-fixture-manifest-v1",
        "suite_id": "p006-whole-text-v2",
    }
    assert tuple(entry["input_file"] for entry in manifest["fixtures"]) == (
        validator.BASE_NAME,
        validator.CANARY_NAME,
        validator.PERMUTATION_NAME,
    )
    assert (
        (FIXTURE_DIR / "LICENSE")
        .read_text(encoding="utf-8")
        .startswith("SPDX-License-Identifier: CC0-1.0\n")
    )
    for entry in manifest["fixtures"]:
        payload = (FIXTURE_DIR / entry["input_file"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == entry["input_sha256"]
        assert entry["expected_outcome"] == "complete"


def test_v2_topology_uses_explicit_roles_and_unequal_totals(validator: Any) -> None:
    requests = validator.validate_fixture_suite()
    base = requests[validator.BASE_NAME]
    assert tuple(document.role for document in base.documents) == validator.EXPECTED_ROLE_ORDER
    assert tuple(document.token_total for document in base.documents) == (
        80,
        150,
        120,
        200,
        240,
        320,
    )
    assert base.documents[-1].role is DocumentRole.KNOWN
    assert sum(document.role is DocumentRole.UNKNOWN for document in base.documents) == 2
    assert tuple((fit.mfw, fit.culling_percent) for fit in base.fits) == (
        (6, 0),
        (5, 50),
        (4, 75),
        (3, 100),
    )
    assert len(base.cells) == 12
    assert {cell.distance for cell in base.cells} == set(DistanceMeasure)

    ranked = contracts._ranked_features(base)
    assert tuple(
        (item.feature, item.known_total_count, item.known_document_count) for item in ranked
    ) == (
        ("beta", 146, 4),
        ("alpha", 114, 4),
        ("gamma", 86, 4),
        ("delta", 34, 3),
        ("epsilon", 16, 3),
        ("zeta", 8, 2),
    )
    assert "unknown_a_only" not in {item.feature for item in ranked}
    assert "unknown_b_only" not in {item.feature for item in ranked}


def test_v2_canary_and_permutation_are_bound_by_document_identity(validator: Any) -> None:
    requests = validator.validate_fixture_suite()
    base = requests[validator.BASE_NAME]
    canary = requests[validator.CANARY_NAME]
    permutation = requests[validator.PERMUTATION_NAME]
    base_by_id = {document.document_id: document for document in base.documents}
    canary_by_id = {document.document_id: document for document in canary.documents}
    permutation_by_id = {document.document_id: document for document in permutation.documents}

    assert base_by_id == permutation_by_id
    assert tuple(document.document_id for document in base.documents) != tuple(
        document.document_id for document in permutation.documents
    )
    assert permutation.documents[-1].role is DocumentRole.KNOWN
    for document_id, base_document in base_by_id.items():
        canary_document = canary_by_id[document_id]
        if base_document.role is DocumentRole.KNOWN:
            assert canary_document == base_document
        else:
            assert canary_document.token_total == base_document.token_total
            assert canary_document.counts != base_document.counts


def test_v2_raw_count_counterfactual_differs_for_every_fit_and_distance(
    validator: Any,
) -> None:
    base = validator.validate_fixture_suite()[validator.BASE_NAME]
    normalized = validator.counterfactual_matrices(base, relative=True)
    raw = validator.counterfactual_matrices(base, relative=False)
    gaps = {
        distance: tuple(
            validator._known_gap(
                base,
                normalized[(fit.fit_id, distance)],
                raw[(fit.fit_id, distance)],
            )
            for fit in base.fits
        )
        for distance in DistanceMeasure
    }
    assert gaps[DistanceMeasure.CLASSIC_DELTA] == pytest.approx(
        (0.522862167897, 0.563647469620, 0.625141828706, 0.732170088485),
        abs=1e-12,
    )
    assert gaps[DistanceMeasure.EDERS_DELTA] == pytest.approx(
        (2.359863334621, 2.364167867139, 2.733526696576, 2.883020899143),
        abs=1e-12,
    )
    assert gaps[DistanceMeasure.COSINE_DELTA] == pytest.approx(
        (0.799979768369, 0.892874968183, 1.220034209071, 1.207695047176),
        abs=1e-12,
    )


def test_v2_validator_rejects_position_total_and_canary_regressions(
    validator: Any,
) -> None:
    requests = validator.validate_fixture_suite()
    base = requests[validator.BASE_NAME]
    canary = requests[validator.CANARY_NAME]
    permutation = requests[validator.PERMUTATION_NAME]

    positional = base.model_copy(
        update={"documents": (*base.documents[:-2], base.documents[-1], base.documents[-2])}
    )
    with pytest.raises(ValueError, match="P006_V2_ROLE_ORDER_INVALID"):
        validator._require_fixture_topology(positional, canary, permutation)

    equal_totals = base.model_copy(
        update={
            "documents": tuple(
                document.model_copy(update={"token_total": 100}) for document in base.documents
            )
        }
    )
    with pytest.raises(ValueError, match="P006_V2_TOKEN_TOTALS_INVALID"):
        validator._require_fixture_topology(equal_totals, canary, permutation)
    with pytest.raises(ValueError, match="P006_V2_RAW_COUNTERFACTUAL_INACTIVE"):
        validator._require_counterfactual_separation(equal_totals)

    unchanged_canary = canary.model_copy(update={"documents": base.documents})
    with pytest.raises(ValueError, match="P006_V2_CANARY_INVALID"):
        validator._require_fixture_topology(base, unchanged_canary, permutation)

    unpermuted = permutation.model_copy(update={"documents": base.documents})
    with pytest.raises(ValueError, match="P006_V2_PERMUTATION_INVALID"):
        validator._require_fixture_topology(base, canary, unpermuted)
