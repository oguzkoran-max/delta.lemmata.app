#!/usr/bin/env python3
"""Run results-blind preflight checks for the frozen literary parity study."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_ROOT = ROOT.parents[1]
EXPECTED_MFW = (100, 300, 500, 1000)
EXPECTED_RUN_IDS = {f"RUN-LIT-PARITY-MFW{mfw:04d}" for mfw in EXPECTED_MFW}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_key_values(text: str) -> dict[str, str]:
    output: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        output[key.strip()] = value.strip()
    return output


def check(checks: list[dict[str, str]], name: str, condition: bool, detail: str) -> None:
    checks.append({"check": name, "status": "pass" if condition else "fail", "detail": detail})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stylo-package-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "config" / "preflight_report.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=ROOT / "config" / "preflight_report.md",
    )
    parser.add_argument("--checked-at-utc")
    args = parser.parse_args()

    checked_at = args.checked_at_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    config_path = ROOT / "config" / "parity_config.json"
    freeze_path = ROOT / "config" / "release_freeze.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    config_sha = sha256_file(config_path)
    checks: list[dict[str, str]] = []

    check(checks, "dataset_identity", config.get("dataset_id") == "DATA-ENDTOEND-LIT-V1", str(config.get("dataset_id")))
    check(checks, "protocol_identity", config.get("protocol_id") == "PROTO-EVAL-DELTA-1.1", str(config.get("protocol_id")))
    check(checks, "mfw_grid", tuple(config.get("mfw_grid", [])) == EXPECTED_MFW, repr(config.get("mfw_grid")))
    check(checks, "configuration_state", config.get("state") == "preflight_blocked_exact_reference_execution_path", str(config.get("state")))
    check(checks, "release_freeze_state", freeze.get("state") == "frozen", str(freeze.get("state")))
    check(checks, "release_commit_match", config["release"]["software_commit"] == freeze.get("software_commit"), freeze.get("software_commit", ""))
    check(
        checks,
        "release_image_match",
        config["release"]["image_digest_reference"] == freeze.get("image", {}).get("immutable_reference"),
        freeze.get("image", {}).get("immutable_reference", ""),
    )
    check(checks, "release_ci_success", freeze.get("prerequisite_ci", {}).get("conclusion") == "success", str(freeze.get("prerequisite_ci", {}).get("run_id")))
    check(checks, "release_publication_success", freeze.get("image", {}).get("publication_run_conclusion") == "success", str(freeze.get("image", {}).get("publication_run_id")))
    check(checks, "no_release_result", freeze.get("analysis_result_created") is False, "analysis_result_created=false")

    run_rows = [
        row
        for row in read_csv(ARTICLE_ROOT / "00_manifest" / "evaluation_run_register.csv")
        if row["run_id"] in EXPECTED_RUN_IDS
    ]
    check(checks, "four_preregistered_runs", len(run_rows) == 4, f"rows={len(run_rows)}")
    check(checks, "run_mfw_grid", {int(row["mfw"]) for row in run_rows} == set(EXPECTED_MFW), repr(sorted(int(row["mfw"]) for row in run_rows)))
    check(checks, "run_config_hash", all(row["config_sha256"] == config_sha for row in run_rows), config_sha)
    check(checks, "run_release_commit", all(row["software_commit"] == freeze["software_commit"] for row in run_rows), freeze["software_commit"])
    check(checks, "run_release_image", all(row["image_digest"] == freeze["image"]["immutable_reference"] for row in run_rows), freeze["image"]["immutable_reference"])
    check(checks, "run_status", all(row["status"] == "preflight_blocked_exact_reference_execution_path" for row in run_rows), "preflight_blocked_exact_reference_execution_path")
    check(checks, "result_hashes_blank", all(not row["result_sha256"] for row in run_rows), "four blank result_sha256 fields")

    outcome_rows = read_csv(ARTICLE_ROOT / "00_manifest" / "evaluation_outcomes.csv")
    check(checks, "outcomes_empty", len(outcome_rows) == 0, f"rows={len(outcome_rows)}")
    result_files: list[str] = []
    for mfw in EXPECTED_MFW:
        folder = ROOT / f"mfw-{mfw:04d}"
        result_files.extend(
            path.relative_to(ROOT).as_posix()
            for path in folder.iterdir()
            if path.is_file() and path.name != "README.md" and not path.name.startswith(".")
        )
    check(checks, "result_folders_empty", not result_files, repr(result_files))

    r_version = subprocess.run(
        ["Rscript", "--vanilla", "-e", "cat(paste(R.version$major, R.version$minor, sep='.'))"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    check(checks, "local_r_version", r_version == config["reference"]["r_version"], r_version)

    smoke = subprocess.run(
        [
            "Rscript",
            "--vanilla",
            str(ROOT / "scripts" / "smoke_stylo_dist_delta.R"),
            str(args.stylo_package_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    smoke_values = parse_key_values(smoke.stdout)
    check(checks, "stylo_version", smoke_values.get("stylo_version") == config["reference"]["stylo_version"], smoke_values.get("stylo_version", "missing"))
    check(checks, "stylo_delta_kernel_smoke", smoke_values.get("smoke_test") == "pass", smoke_values.get("max_abs_difference", "missing"))

    failed = [item for item in checks if item["status"] == "fail"]
    report = {
        "schema_version": "1.0",
        "checked_at_utc": checked_at,
        "dataset_id": config["dataset_id"],
        "protocol_id": config["protocol_id"],
        "freeze_id": freeze["freeze_id"],
        "software_commit": freeze["software_commit"],
        "image_digest_reference": freeze["image"]["immutable_reference"],
        "configuration_sha256": config_sha,
        "machine": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "r_version": r_version,
        },
        "reference_kernel": {
            "package_source": "local_renv_cache",
            "package_directory": str(args.stylo_package_dir),
            "description_sha256": sha256_file(args.stylo_package_dir / "DESCRIPTION"),
            "rdb_sha256": sha256_file(args.stylo_package_dir / "R" / "stylo.rdb"),
            "rdx_sha256": sha256_file(args.stylo_package_dir / "R" / "stylo.rdx"),
            "loading_mode": smoke_values.get("loading_mode"),
            "smoke_max_abs_difference": smoke_values.get("max_abs_difference"),
            "smoke_status": smoke_values.get("smoke_test"),
        },
        "checks": checks,
        "limitations": [
            "The normal macOS stylo namespace was not attached because its imported GUI stack requires XQuartz; the exact 0.7.71 lazy-load object database was used only for this numerical-kernel smoke test.",
            "Direct readback from the live host remains unavailable because SSH timed out during banner exchange before authentication.",
            "No local Docker, Podman, Colima, nerdctl, or OrbStack runtime was available for executing the frozen OCI image.",
            "This preflight creates no stylometric result and does not test Delta-versus-R parity.",
        ],
        "execution_readiness": "blocked_exact_reference_execution_path" if not failed else "failed",
        "analysis_started": False,
        "stylometric_result_created": False,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Frozen Literary Parity Preflight",
        "",
        f"- Checked at (UTC): `{checked_at}`",
        f"- Freeze: `{freeze['freeze_id']}`",
        f"- Commit: `{freeze['software_commit']}`",
        f"- Image: `{freeze['image']['immutable_reference']}`",
        f"- Configuration SHA-256: `{config_sha}`",
        f"- Status: `{report['execution_readiness']}`",
        "- Analysis started: `false`",
        "- Stylometric result created: `false`",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    lines.extend(f"| `{item['check']}` | `{item['status']}` | {item['detail']} |" for item in checks)
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The frozen corpus, configuration, release identity, run-register rows, and exact `stylo 0.7.71` numerical kernel pass results-blind checks. Actual parity execution remains blocked until an auditable route can invoke the direct R reference and the frozen Delta release. No result or parity claim is created by this report.",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["limitations"])
    args.markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"preflight_checks={len(checks)}")
    print(f"preflight_failures={len(failed)}")
    print(f"execution_readiness={report['execution_readiness']}")
    print("analysis_started=false")
    print("stylometric_result_created=false")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
