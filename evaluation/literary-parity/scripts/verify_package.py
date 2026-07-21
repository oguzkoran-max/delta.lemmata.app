#!/usr/bin/env python3
"""Verify the pre-run DATA-ENDTOEND-LIT-V1 evidence package."""

from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MFW_GRID = {100, 300, 500, 1000}
MIN_TOKENS = 25_000


def fail(message: str) -> None:
    raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def token_count(text: str) -> int:
    count = 0
    in_token = False
    for char in unicodedata.normalize("NFC", text.lower()):
        category = unicodedata.category(char)
        if in_token:
            if not (category.startswith("L") or category.startswith("M")):
                count += 1
                in_token = False
        elif category.startswith("L"):
            in_token = True
    return count + int(in_token)


def manifest_candidates() -> list[Path]:
    output = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name == "package_manifest.csv":
            continue
        relative = path.relative_to(ROOT)
        if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
            continue
        output.append(path)
    return sorted(output, key=lambda item: item.relative_to(ROOT).as_posix())


def main() -> int:
    required = [
        "README.md",
        "selection_protocol.md",
        "selection_log.csv",
        "source/source_register.csv",
        "rights/rights_record.md",
        "config/parity_contract.md",
        "config/parity_config.json",
        "raw_manifest.csv",
        "clean_manifest.csv",
        "metadata.csv",
        "cleaning_log.csv",
        "cleaning_log.md",
        "feature_eligibility.csv",
        "ranked_feature_qc.csv",
        "overlap_report.csv",
        "corpus_qc.json",
        "package_manifest.csv",
    ]
    for relative in required:
        if not (ROOT / relative).is_file():
            fail(f"Missing required file: {relative}")

    sources = read_csv(ROOT / "source" / "source_register.csv")
    raw_manifest = read_csv(ROOT / "raw_manifest.csv")
    clean_manifest = read_csv(ROOT / "clean_manifest.csv")
    metadata = read_csv(ROOT / "metadata.csv")
    if not (len(sources) == len(raw_manifest) == len(clean_manifest) == len(metadata) == 6):
        fail("Source, raw, clean and metadata registers must each contain six rows")
    if len({row["author"] for row in sources}) != 6:
        fail("One-author-one-document rule failed")
    if len({row["document_id"] for row in sources}) != 6:
        fail("Document identifiers are not unique")

    source_by_id = {row["document_id"]: row for row in sources}
    raw_by_id = {row["document_id"]: row for row in raw_manifest}
    clean_by_id = {row["document_id"]: row for row in clean_manifest}
    metadata_by_id = {row["document_id"]: row for row in metadata}
    if not (source_by_id.keys() == raw_by_id.keys() == clean_by_id.keys() == metadata_by_id.keys()):
        fail("Document identifiers do not match across registers")

    clean_hashes: set[str] = set()
    for document_id, source in source_by_id.items():
        for key in ("raw_path", "metadata_html_path", "metadata_rdf_path", "headers_path"):
            if not (ROOT / source[key]).is_file():
                fail(f"{document_id}: missing source path {source[key]}")
        raw_path = ROOT / raw_by_id[document_id]["path"]
        actual_raw_sha = sha256_file(raw_path)
        if actual_raw_sha != source["expected_raw_sha256"]:
            fail(f"{document_id}: source-register raw SHA mismatch")
        if actual_raw_sha != raw_by_id[document_id]["sha256"]:
            fail(f"{document_id}: raw-manifest SHA mismatch")

        clean_path = ROOT / clean_by_id[document_id]["path"]
        clean_bytes = clean_path.read_bytes()
        if sha256_file(clean_path) != clean_by_id[document_id]["sha256"]:
            fail(f"{document_id}: clean-manifest SHA mismatch")
        if b"\r" in clean_bytes or clean_bytes.startswith(b"\xef\xbb\xbf"):
            fail(f"{document_id}: clean file contains CR or BOM")
        if not clean_bytes.endswith(b"\n") or clean_bytes.endswith(b"\n\n"):
            fail(f"{document_id}: clean file must end in exactly one LF")
        clean_text = clean_bytes.decode("utf-8", errors="strict")
        if unicodedata.normalize("NFC", clean_text) != clean_text:
            fail(f"{document_id}: clean file is not NFC")
        measured_tokens = token_count(clean_text)
        if measured_tokens != int(clean_by_id[document_id]["token_count"]):
            fail(f"{document_id}: token count mismatch")
        if measured_tokens < MIN_TOKENS:
            fail(f"{document_id}: fewer than {MIN_TOKENS} tokens")
        if metadata_by_id[document_id]["token_count"] != str(measured_tokens):
            fail(f"{document_id}: metadata token count mismatch")
        clean_hashes.add(clean_by_id[document_id]["sha256"])
    if len(clean_hashes) != 6:
        fail("Exact duplicate clean files detected")

    eligibility = read_csv(ROOT / "feature_eligibility.csv")
    if {int(row["mfw"]) for row in eligibility} != MFW_GRID:
        fail("MFW eligibility grid differs from the preregistered grid")
    if any(row["eligible"] != "true" for row in eligibility):
        fail("At least one preregistered MFW level is not technically eligible")

    overlap = read_csv(ROOT / "overlap_report.csv")
    if len(overlap) != 15:
        fail("Six documents must produce 15 pairwise overlap rows")

    qc = json.loads((ROOT / "corpus_qc.json").read_text(encoding="utf-8"))
    if not qc["eligible_for_preregistered_mfw_grid"]:
        fail("corpus_qc does not mark the preregistered grid eligible")
    for forbidden in ("distance_computed", "mds_computed", "stylo_run", "delta_run"):
        if qc[forbidden]:
            fail(f"Pre-run package improperly reports {forbidden}=true")

    parity_config = json.loads(
        (ROOT / "config" / "parity_config.json").read_text(encoding="utf-8")
    )
    if parity_config["dataset_id"] != "DATA-ENDTOEND-LIT-V1":
        fail("Parity configuration points to the wrong dataset")
    if set(parity_config["mfw_grid"]) != MFW_GRID:
        fail("Parity configuration MFW grid differs from the preregistered grid")
    if parity_config["reference"]["call"] != "stylo::dist.delta(z_scores, scale = FALSE)":
        fail("Parity configuration reference call changed")
    if parity_config["document_order"] != [row["document_id"] for row in sources]:
        fail("Parity configuration document order differs from the source register")

    for folder in ("mfw-0100", "mfw-0300", "mfw-0500", "mfw-1000"):
        files = [
            path
            for path in (ROOT / folder).iterdir()
            if path.is_file() and not path.name.startswith(".")
        ]
        if {path.name for path in files} != {"README.md"}:
            fail(f"{folder}: pre-run folder may contain only README.md")

    outcomes_path = ROOT.parents[1] / "00_manifest" / "evaluation_outcomes.csv"
    if outcomes_path.is_file() and read_csv(outcomes_path):
        fail("Main evaluation_outcomes.csv must remain empty before execution")

    package_rows = read_csv(ROOT / "package_manifest.csv")
    recorded = {row["path"]: row for row in package_rows}
    expected_paths = {
        path.relative_to(ROOT).as_posix(): path for path in manifest_candidates()
    }
    if recorded.keys() != expected_paths.keys():
        fail("Package manifest path set is stale")
    for relative, path in expected_paths.items():
        row = recorded[relative]
        if row["sha256"] != sha256_file(path) or row["bytes"] != str(path.stat().st_size):
            fail(f"Package manifest mismatch: {relative}")

    print("package_verification=ok")
    print("documents=6")
    print("mfw_grid=100,300,500,1000")
    print("evaluation_outcomes_rows=0")
    print("stylometric_results_present=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
