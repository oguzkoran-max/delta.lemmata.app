#!/usr/bin/env python3
"""Freeze and verify the results-blind literary parity execution contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
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
EXPECTED_REQUEST_COMPONENT = (
    "28e9d3d83efa686b8b51b80eccd9b4f3439aeb56141e459abd97729c9c5b9184"
)
EXPECTED_RESULT_COMPONENT = (
    "053bf21e22c557bd2e9cc53b858b02603c19200680fe1cc2d885bd1b11d6987b"
)
EXPECTED_FATAL_COMPONENT = (
    "24ae13b5ee15a59e2f7924a480c4160907d13e900a8d879f1d81b0faab8f6548"
)
FROZEN_FILES = (
    "containers/Dockerfile",
    "renv.lock",
    "scripts/oracles/p006-direct-stylo-v1.R",
    "scripts/validate_p006_worker_parity.py",
    "scripts/workers/p006-stylo-worker-v1.R",
    "src/delta_lemmata/data/stylo-worker-limits-v1.json",
    "src/delta_lemmata/stylo_contracts.py",
    "uv.lock",
)
LOCAL_SCRIPTS = (
    "scripts/build_literary_worker_request.py",
    "scripts/compare_literary_parity.py",
    "scripts/direct_oracle_harness.R",
    "scripts/literary-parity-github-actions.yml",
    "scripts/prepare_execution.py",
)


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


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *arguments: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def add_check(
    checks: list[dict[str, Any]], name: str, condition: bool, detail: Any
) -> None:
    checks.append(
        {"check": name, "detail": detail, "status": "pass" if condition else "fail"}
    )


def validate_request_with_frozen_source(
    repo: Path, request_path: Path
) -> dict[str, Any]:
    python = repo / ".venv" / "bin" / "python"
    if not python.is_file():
        raise RuntimeError("execution-preflight-repo-python-missing")
    with tempfile.TemporaryDirectory(prefix="delta-literary-frozen-") as folder:
        folder_path = Path(folder)
        archive_path = folder_path / "source.tar"
        archive_path.write_bytes(
            git(repo, "archive", "--format=tar", EXPECTED_COMMIT, "src", binary=True)
        )
        with tarfile.open(archive_path) as archive:
            archive.extractall(folder_path, filter="data")
        program = """
import hashlib
from pathlib import Path
from delta_lemmata.stylo_contracts import canonical_worker_json, parse_worker_input
payload = Path(__import__('sys').argv[1]).read_bytes()
parsed = parse_worker_input(payload)
canonical = canonical_worker_json(parsed)
if canonical != payload:
    raise SystemExit('frozen-canonical-request-mismatch')
print(hashlib.sha256(canonical).hexdigest())
print(len(parsed.documents))
print(','.join(str(fit.mfw) for fit in parsed.fits))
print(','.join(cell.distance.value for cell in parsed.cells))
"""
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(folder_path / "src")
        result = subprocess.run(
            [str(python), "-c", program, str(request_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            text=True,
        )
    lines = result.stdout.splitlines()
    if len(lines) != 4:
        raise RuntimeError("execution-preflight-frozen-validation-output-invalid")
    return {
        "canonical_request_sha256": lines[0],
        "document_count": int(lines[1]),
        "mfw_grid": [int(value) for value in lines[2].split(",")],
        "distances": lines[3].split(","),
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Literary parity execution preflight",
        "",
        f"- Checked at UTC: `{report['checked_at_utc']}`",
        f"- Status: `{report['status']}`",
        f"- Passed checks: `{report['passed_checks']}/{report['total_checks']}`",
        f"- Request SHA-256: `{report['request_sha256']}`",
        f"- Frozen source commit: `{report['frozen_source_commit']}`",
        f"- Frozen image: `{report['frozen_image']}`",
        "",
        "This is a results-blind readiness record. It contains no Delta distance,",
        "direct R stylo result, MDS coordinate, cluster or authorship conclusion.",
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
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--checked-at-utc")
    args = parser.parse_args()
    repo = args.repo.resolve()
    checked_at = args.checked_at_utc or (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    config_path = ROOT / "config" / "parity_config.json"
    freeze_path = ROOT / "config" / "release_freeze.json"
    request_path = ROOT / "input" / "literary_worker_request.json"
    metadata_path = ROOT / "input" / "request_metadata.json"
    component_path = ROOT / "input" / EXPECTED_REQUEST_COMPONENT
    config = json.loads(config_path.read_text(encoding="utf-8"))
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    request_payload = request_path.read_bytes()
    request_sha = sha256_bytes(request_payload)
    checks: list[dict[str, Any]] = []

    add_check(checks, "dataset_identity", config.get("dataset_id") == "DATA-ENDTOEND-LIT-V1", config.get("dataset_id"))
    add_check(checks, "protocol_identity", config.get("protocol_id") == "PROTO-EVAL-DELTA-1.1", config.get("protocol_id"))
    add_check(checks, "frozen_commit", config["release"]["software_commit"] == EXPECTED_COMMIT == freeze.get("software_commit"), freeze.get("software_commit"))
    add_check(checks, "frozen_image", config["release"]["image_digest_reference"] == EXPECTED_IMAGE == freeze.get("image", {}).get("immutable_reference"), freeze.get("image", {}).get("immutable_reference"))
    add_check(checks, "release_freeze", freeze.get("state") == "frozen" and freeze.get("analysis_result_created") is False, freeze.get("state"))
    add_check(checks, "mfw_grid", tuple(config.get("mfw_grid", [])) == EXPECTED_MFW, config.get("mfw_grid"))
    add_check(checks, "culling", config.get("culling_percent") == 0, config.get("culling_percent"))
    add_check(checks, "distance", config.get("distance") == "classic_delta", config.get("distance"))
    add_check(checks, "matrix_threshold", config["comparison"]["matrix_max_abs_difference"] == 1e-6, config["comparison"]["matrix_max_abs_difference"])
    add_check(checks, "structural_threshold", config["comparison"]["structural_max_abs_difference"] == 1e-12, config["comparison"]["structural_max_abs_difference"])
    add_check(checks, "exact_feature_order", config["comparison"]["exact_ordered_features"] is True, config["comparison"]["exact_ordered_features"])
    add_check(checks, "exact_label_order", config["comparison"]["exact_ordered_document_labels"] is True, config["comparison"]["exact_ordered_document_labels"])
    add_check(checks, "exact_tie_groups", config["comparison"]["tie_groups_must_match_exactly"] is True, config["comparison"]["tie_groups_must_match_exactly"])
    add_check(checks, "request_component_exact", component_path.read_bytes() == request_payload, EXPECTED_REQUEST_COMPONENT)
    add_check(checks, "request_hash_bound", metadata.get("request_sha256") == request_sha, request_sha)
    frozen_validation = validate_request_with_frozen_source(repo, request_path)
    add_check(checks, "request_frozen_contract", frozen_validation["canonical_request_sha256"] == request_sha, frozen_validation)
    add_check(checks, "request_document_count", frozen_validation["document_count"] == 6, frozen_validation["document_count"])
    add_check(checks, "request_mfw_grid", tuple(frozen_validation["mfw_grid"]) == EXPECTED_MFW, frozen_validation["mfw_grid"])
    add_check(checks, "request_distance_grid", frozen_validation["distances"] == ["classic_delta"] * 4, frozen_validation["distances"])

    result_files = []
    for folder in [ROOT / "outcomes", *(ROOT / f"mfw-{mfw:04d}" for mfw in EXPECTED_MFW)]:
        if not folder.exists():
            continue
        if folder.name == "outcomes":
            result_files.extend(path.name for path in folder.iterdir() if path.is_file())
        else:
            result_files.extend(
                f"{folder.name}/{path.name}"
                for path in folder.iterdir()
                if path.is_file() and path.name != "README.md"
            )
    add_check(checks, "results_blind_directories", not result_files, sorted(result_files))

    local_hashes = {name: sha256_file(ROOT / name) for name in LOCAL_SCRIPTS}
    frozen_hashes = {
        name: sha256_bytes(git(repo, "show", f"{EXPECTED_COMMIT}:{name}", binary=True))
        for name in FROZEN_FILES
    }
    add_check(checks, "local_execution_files_present", len(local_hashes) == len(LOCAL_SCRIPTS), local_hashes)
    add_check(checks, "frozen_execution_files_bound", len(frozen_hashes) == len(FROZEN_FILES), frozen_hashes)
    workflow = (ROOT / "scripts" / "literary-parity-github-actions.yml").read_text(encoding="utf-8")
    add_check(checks, "workflow_commit_pin", EXPECTED_COMMIT in workflow, EXPECTED_COMMIT)
    add_check(checks, "workflow_image_pin", EXPECTED_IMAGE in workflow, EXPECTED_IMAGE)
    add_check(checks, "workflow_component_pins", all(value in workflow for value in (EXPECTED_REQUEST_COMPONENT, EXPECTED_RESULT_COMPONENT, EXPECTED_FATAL_COMPONENT)), {"request": EXPECTED_REQUEST_COMPONENT, "result": EXPECTED_RESULT_COMPONENT, "fatal": EXPECTED_FATAL_COMPONENT})
    add_check(
        checks,
        "workflow_fatal_is_failure",
        'if [[ -e "/tmp/worker/$FATAL_COMPONENT" ]]' in workflow,
        "fatal artifact rejected independently of process exit status",
    )
    add_check(checks, "repo_contains_frozen_commit", git(repo, "cat-file", "-t", EXPECTED_COMMIT) == "commit", EXPECTED_COMMIT)

    contract = {
        "analysis_unit": "whole_text",
        "candidate_feature_limit": 20000,
        "culling_percent": 0,
        "dataset_id": "DATA-ENDTOEND-LIT-V1",
        "distance": "classic_delta",
        "failure_rules": {
            "any_fatal_artifact": "automatic_failure_even_when_process_exit_status_is_zero",
            "any_nonfinite_value": "automatic_failure",
            "any_noncomplete_fit_or_cell": "automatic_failure",
            "mfw_substitution": "forbidden",
        },
        "frozen_file_sha256": frozen_hashes,
        "frozen_image": EXPECTED_IMAGE,
        "frozen_source_commit": EXPECTED_COMMIT,
        "local_execution_file_sha256": local_hashes,
        "mfw_grid": list(EXPECTED_MFW),
        "request_component": EXPECTED_REQUEST_COMPONENT,
        "request_sha256": request_sha,
        "result_component": EXPECTED_RESULT_COMPONENT,
        "fatal_component": EXPECTED_FATAL_COMPONENT,
        "schema_version": "literary-parity-execution-contract-v1",
        "seed": 20260713,
        "success_rules": {
            "diagonal_max_abs": 1e-12,
            "matrix_max_abs_difference": 1e-6,
            "ordered_document_labels": "exact",
            "ordered_features": "exact",
            "prepared_z_score_max_abs_difference": 1e-12,
            "structural_max_abs_difference": 1e-12,
            "symmetry_max_abs_residual": 1e-12,
            "tie_definition": "abs(distance-minimum)<=1e-12",
            "tie_groups": "exact",
        },
        "state": "results_blind_frozen",
    }
    contract_path = ROOT / "config" / "execution_contract.json"
    contract_path.write_bytes(canonical_json(contract))
    passed = sum(item["status"] == "pass" for item in checks)
    report = {
        "checked_at_utc": checked_at,
        "checks": checks,
        "contract_sha256": sha256_file(contract_path),
        "frozen_image": EXPECTED_IMAGE,
        "frozen_source_commit": EXPECTED_COMMIT,
        "passed_checks": passed,
        "request_sha256": request_sha,
        "schema_version": "literary-parity-execution-preflight-v1",
        "status": "ready_for_execution" if passed == len(checks) else "blocked",
        "total_checks": len(checks),
    }
    report_path = ROOT / "config" / "execution_preflight.json"
    report_path.write_bytes(canonical_json(report))
    (ROOT / "config" / "execution_preflight.md").write_text(
        markdown_report(report), encoding="utf-8"
    )
    print(f"execution_preflight={report['status']}")
    print(f"checks={passed}/{len(checks)}")
    print(f"request_sha256={request_sha}")
    print(f"contract_sha256={report['contract_sha256']}")
    return 0 if report["status"] == "ready_for_execution" else 1


if __name__ == "__main__":
    raise SystemExit(main())
