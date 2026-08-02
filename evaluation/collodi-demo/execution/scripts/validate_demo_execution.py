#!/usr/bin/env python3
"""Freeze and verify the results-blind Collodi demo execution overlay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COMMIT = "31e09782ba07e6709cbdcca48bc9db22e6c49723"
EXPECTED_IMAGE = (
    "ghcr.io/oguzkoran-max/delta.lemmata.app@"
    "sha256:80836f174cf24707082cb41f5937cf3169710683e8a2f50bd00110cdb1072faa"
)
EXPECTED_MFW = (100, 300, 500, 1000)
EXPECTED_LOCK_MANIFEST = "f740e4c57c11d376346d4c7a8cc5d23fbea5c28544167de3ee2f0d496f7f4292"
EXPECTED_OUTCOMES_AT_LOCK = "135d2951d8df399d9f7e659209d3c876b1ca2cad5f4df8417f95b73e3321dd96"
EXPECTED_COMPARATOR_SHA = "70e3c9ef9801eb4af52854aae9c4bd4f8b67de20ed7e3fc768e5ecaebd566836"
EXPECTED_FROZEN_HASHES = {
    "containers/Dockerfile": "7e3812352e11f43f345f2a21886ab708e1737b910882efe096fde33cb181a996",
    "renv.lock": "bb792d224470650053412194edc35f3fd866673bd78d30ca756fcec3ad86ea1d",
    "scripts/oracles/p006-direct-stylo-v1.R": "61c08e25831a54df6bb25a3f96ce90908be181241bcc3165d09f1be8773e0630",
    "scripts/validate_p006_worker_parity.py": "53c4f71e8fc0d6fc405f5c54ea49571f43ab38e23d17fbebab3a8adac6a7432d",
    "scripts/workers/p006-stylo-worker-v1.R": "4cf9866a8a2c0fdf6011f711654f481e4b74326f518d1676fcf0a5b7eb2d2eb2",
    "src/delta_lemmata/data/stylo-worker-limits-v1.json": "6b7ccff1af42cdcc89ee5d62a2f6d179f3bd372ed1d2660d327f2cd6abf79702",
    "src/delta_lemmata/stylo_contracts.py": "1668d676d1dfff658778f7f0391b4457a8786b549b9c093efb43a54800ae5969",
    "uv.lock": "c6b6aa3d8e07cefff89f1072080fc7d9daa055692be8e02b10d224853986a385",
}
LOCAL_EXECUTION_FILES = (
    "README.md",
    "config/collodi_demo_execution_config.json",
    "config/results_blind_run_register.csv",
    "config/software_freeze_amendment.md",
    "scripts/build_demo_worker_request.py",
    "scripts/compare_collodi_parity.py",
    "scripts/direct_oracle_harness.R",
    "scripts/validate_demo_execution.py",
    "workflow/collodi-demo.yml",
)


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


def add_check(
    checks: list[dict[str, Any]], name: str, condition: bool, detail: Any
) -> None:
    checks.append(
        {"check": name, "detail": detail, "status": "pass" if condition else "fail"}
    )


def inventory(folder: Path) -> dict[str, str]:
    return {
        path.relative_to(folder).as_posix(): sha256_file(path)
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def result_like_files(root: Path) -> list[str]:
    markers = (
        "worker_result",
        "direct_oracle_result",
        "distance_matrix",
        "comparison_summary",
        "mds_coordinate",
        "cluster",
    )
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == "input":
            continue
        lowered = relative.as_posix().lower()
        if any(marker in lowered for marker in markers):
            findings.append(relative.as_posix())
    for name in ("results", "outcomes", "evidence"):
        folder = root / name
        if folder.exists():
            findings.extend(
                path.relative_to(root).as_posix()
                for path in folder.rglob("*")
                if path.is_file()
            )
    return sorted(set(findings))


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Collodi demo execution preflight",
        "",
        f"- Checked at UTC: `{report['checked_at_utc']}`",
        f"- Status: `{report['status']}`",
        f"- Passed checks: `{report['passed_checks']}/{report['total_checks']}`",
        f"- Request SHA-256: `{report['request_sha256']}`",
        f"- Frozen source commit: `{report['frozen_source_commit']}`",
        f"- Frozen image: `{report['frozen_image']}`",
        "",
        "This is a results-blind readiness record. It contains no Delta distance,",
        "MDS coordinate, cluster, authorship claim or diachronic inference.",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for item in report["checks"]:
        detail = json.dumps(item["detail"], ensure_ascii=False, sort_keys=True)
        lines.append(f"| `{item['check']}` | `{item['status']}` | `{detail}` |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-repo", type=Path, required=True)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--checked-at-utc")
    args = parser.parse_args()

    frozen_repo = args.frozen_repo.resolve()
    project_root = (args.project_root or ROOT.parent).resolve()
    output_dir = (args.output_dir or (ROOT / "config")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    checked_at = args.checked_at_utc or (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )

    config_path = ROOT / "config" / "collodi_demo_execution_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    request_path = ROOT / "input" / "collodi_demo_worker_request.json"
    metadata_path = ROOT / "input" / "request_metadata.json"
    request_payload = request_path.read_bytes()
    request_sha = sha256_bytes(request_payload)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    components = config["request_components"]
    component_path = ROOT / "input" / components["request"]
    checks: list[dict[str, Any]] = []

    add_check(checks, "dataset_identity", config["dataset_id"] == "DATA-COLLODI-DEMO-V1", config["dataset_id"])
    add_check(checks, "protocol_identity", config["protocol_id"] == "PROTO-EVAL-DELTA-1.1", config["protocol_id"])
    add_check(checks, "results_blind_state", config["state"] == "results_blind_prepared", config["state"])
    add_check(checks, "document_count", len(config["documents"]) == 3, len(config["documents"]))
    add_check(checks, "mfw_grid", tuple(config["mfw_grid"]) == EXPECTED_MFW, config["mfw_grid"])
    add_check(checks, "culling", config["culling_percent"] == 0, config["culling_percent"])
    add_check(checks, "distance", config["distance"] == "classic_delta", config["distance"])
    add_check(checks, "display_mfw", config["scientific_scope"]["display_mfw"] == 500, config["scientific_scope"]["display_mfw"])
    add_check(checks, "claim_restrictions", len(config["scientific_scope"]["forbidden"]) == 5, config["scientific_scope"]["forbidden"])
    lock = config["upstream_dataset_lock"]
    add_check(checks, "upstream_lock_manifest", lock["manifest_sha256"] == EXPECTED_LOCK_MANIFEST and lock["validation_status"] == "PASS", lock)
    add_check(checks, "outcomes_state_at_lock", lock["outcomes_sha256_at_lock"] == EXPECTED_OUTCOMES_AT_LOCK, lock["outcomes_sha256_at_lock"])
    add_check(checks, "frozen_commit", config["release"]["software_commit"] == EXPECTED_COMMIT, config["release"]["software_commit"])
    add_check(checks, "frozen_image", config["release"]["image_digest_reference"] == EXPECTED_IMAGE, config["release"]["image_digest_reference"])
    add_check(checks, "request_component_exact", component_path.read_bytes() == request_payload, components["request"])
    add_check(checks, "request_hash_bound", metadata["request_sha256"] == request_sha, request_sha)
    add_check(checks, "candidate_feature_range", 1000 <= metadata["candidate_feature_count"] <= 20000, metadata["candidate_feature_count"])
    add_check(checks, "results_blind_files", not result_like_files(ROOT), result_like_files(ROOT))

    frozen_hashes = {
        name: sha256_file(frozen_repo / name) for name in EXPECTED_FROZEN_HASHES
    }
    add_check(checks, "frozen_source_file_hashes", frozen_hashes == EXPECTED_FROZEN_HASHES, frozen_hashes)
    local_hashes = {name: sha256_file(ROOT / name) for name in LOCAL_EXECUTION_FILES}
    add_check(checks, "accepted_comparator_unchanged", local_hashes["scripts/compare_collodi_parity.py"] == EXPECTED_COMPARATOR_SHA, local_hashes["scripts/compare_collodi_parity.py"])

    workflow = (ROOT / "workflow" / "collodi-demo.yml").read_text(encoding="utf-8")
    workflow_pins = all(
        value in workflow
        for value in (
            EXPECTED_COMMIT,
            EXPECTED_IMAGE,
            components["request"],
            components["result"],
            components["fatal"],
            "--network none",
            "--read-only",
            "--cap-drop ALL",
        )
    )
    add_check(checks, "workflow_security_and_identity_pins", workflow_pins, "commit+image+components+network-none+read-only+cap-drop")

    environment = dict(os.environ)
    environment["PYTHONPYCACHEPREFIX"] = "/tmp/delta-collodi-pycache"
    with tempfile.TemporaryDirectory(prefix="collodi-demo-regenerated-") as folder:
        generated = Path(folder)
        command = [
            sys.executable,
            str(ROOT / "scripts" / "build_demo_worker_request.py"),
            "--root",
            str(ROOT),
            "--project-root",
            str(project_root),
            "--output-dir",
            str(generated),
            "--repo",
            str(frozen_repo),
        ]
        subprocess.run(command, check=True, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        regenerated = inventory(generated)
        locked = inventory(ROOT / "input")
    add_check(checks, "deterministic_input_tree", regenerated == locked, {"file_count": len(locked), "tree_sha256": sha256_bytes(canonical_json(locked))})

    sys.path.insert(0, str(frozen_repo / "src"))
    from delta_lemmata.stylo_contracts import canonical_worker_json, parse_worker_input

    parsed = parse_worker_input(request_payload)
    canonical = canonical_worker_json(parsed)
    add_check(checks, "frozen_request_contract", canonical == request_payload, request_sha)
    add_check(checks, "request_document_count", len(parsed.documents) == 3, len(parsed.documents))
    add_check(checks, "request_mfw_grid", tuple(fit.mfw for fit in parsed.fits) == EXPECTED_MFW, [fit.mfw for fit in parsed.fits])
    add_check(checks, "request_distance_grid", [cell.distance.value for cell in parsed.cells] == ["classic_delta"] * 4, [cell.distance.value for cell in parsed.cells])

    passed = sum(item["status"] == "pass" for item in checks)
    contract = {
        "analysis_unit": "whole_text",
        "candidate_feature_count": metadata["candidate_feature_count"],
        "culling_percent": 0,
        "dataset_id": config["dataset_id"],
        "display_mfw": 500,
        "distance": "classic_delta",
        "fatal_component": components["fatal"],
        "forbidden_claims": config["scientific_scope"]["forbidden"],
        "frozen_file_sha256": frozen_hashes,
        "frozen_image": EXPECTED_IMAGE,
        "frozen_source_commit": EXPECTED_COMMIT,
        "local_execution_file_sha256": local_hashes,
        "mfw_grid": list(EXPECTED_MFW),
        "request_component": components["request"],
        "request_sha256": request_sha,
        "result_component": components["result"],
        "schema_version": "collodi-demo-execution-contract-v1",
        "seed": config["seed"],
        "state": "results_blind_frozen",
        "success_rules": config["comparison"],
        "upstream_dataset_lock_manifest_sha256": EXPECTED_LOCK_MANIFEST,
        "upstream_outcomes_sha256_at_lock": EXPECTED_OUTCOMES_AT_LOCK,
    }
    contract_path = output_dir / "execution_contract.json"
    contract_path.write_bytes(canonical_json(contract))
    report = {
        "checked_at_utc": checked_at,
        "checks": checks,
        "contract_sha256": sha256_file(contract_path),
        "frozen_image": EXPECTED_IMAGE,
        "frozen_source_commit": EXPECTED_COMMIT,
        "passed_checks": passed,
        "request_sha256": request_sha,
        "schema_version": "collodi-demo-execution-preflight-v1",
        "status": "ready_for_execution" if passed == len(checks) else "blocked",
        "total_checks": len(checks),
    }
    (output_dir / "execution_preflight.json").write_bytes(canonical_json(report))
    (output_dir / "execution_preflight.md").write_text(markdown_report(report), encoding="utf-8")
    print(f"execution_preflight={report['status']}")
    print(f"checks={passed}/{len(checks)}")
    print(f"request_sha256={request_sha}")
    print(f"contract_sha256={report['contract_sha256']}")
    return 0 if report["status"] == "ready_for_execution" else 1


if __name__ == "__main__":
    raise SystemExit(main())
