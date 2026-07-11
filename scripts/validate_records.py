#!/usr/bin/env python3
"""Validate Delta's JSON and JSONL provenance records."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

from delta_lemmata.provenance import validate_record

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
PLACEHOLDER = re.compile(r"<[^>]+>")


def jsonl_records(path: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            loaded: dict[str, Any] = json.loads(line)
            yield f"{path}:{line_number}", loaded


def json_records(directory: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    if not directory.exists():
        return
    for path in sorted(directory.glob("*.json")):
        with path.open(encoding="utf-8") as handle:
            loaded: dict[str, Any] = json.load(handle)
        yield str(path), loaded


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit_exists(commit_id: str) -> bool:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit_id}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def _repo_path(relative_path: str) -> Path | None:
    path = PurePosixPath(relative_path)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in relative_path
        or ":" in relative_path
        or path.as_posix() != relative_path
    ):
        return None
    target = (ROOT / Path(*path.parts)).resolve()
    root = ROOT.resolve()
    if target != root and root not in target.parents:
        return None
    return target


def _git_blob_sha256(commit_id: str, relative_path: str) -> str | None:
    completed = subprocess.run(
        ["git", "show", f"{commit_id}:{relative_path}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return hashlib.sha256(completed.stdout).hexdigest()


def artifact_errors(run_id: str, run: dict[str, Any]) -> list[str]:
    """Validate v1.1 artifact paths and hashes against the tested commit or filesystem."""

    errors: list[str] = []
    commit_id = run["git_commit"]
    for artifact in run["input_artifacts"]:
        relative_path = artifact["path"]
        if _repo_path(relative_path) is None:
            errors.append(f"{run_id}: input artifact path is not repo-relative: {relative_path}")
            continue
        actual_hash = _git_blob_sha256(commit_id, relative_path)
        if actual_hash is None:
            errors.append(f"{run_id}: input artifact is absent from {commit_id}: {relative_path}")
        elif actual_hash != artifact["sha256"]:
            errors.append(f"{run_id}: input artifact hash mismatch: {relative_path}")

    for artifact in run["output_artifacts"]:
        relative_path = artifact["path"]
        target = _repo_path(relative_path)
        if target is None:
            errors.append(f"{run_id}: output artifact path is not repo-relative: {relative_path}")
        elif not target.is_file():
            errors.append(f"{run_id}: output artifact does not exist: {relative_path}")
        elif _sha256_file(target) != artifact["sha256"]:
            errors.append(f"{run_id}: output artifact hash mismatch: {relative_path}")
    return errors


def _manifest_errors(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    manifest_path = _repo_path(manifest["path"])
    if manifest_path is None:
        return [f"evidence manifest path is not repo-relative: {manifest['path']}"]
    if not manifest_path.is_file():
        return [f"evidence manifest does not exist: {manifest['path']}"]
    actual_manifest_hash = _sha256_file(manifest_path)
    if actual_manifest_hash != manifest["sha256"]:
        errors.append(f"evidence manifest hash mismatch: {manifest['path']}")

    entries: dict[str, str] = {}
    for line_number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        digest, separator, relative_path = line.partition("  ")
        if not separator or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"invalid manifest line {line_number}: {manifest['path']}")
            continue
        if _repo_path(relative_path) is None:
            errors.append(f"manifest artifact path is not repo-relative: {relative_path}")
            continue
        entries[relative_path] = digest

    expected: set[str] = set()
    for covered_path in manifest["covers"]:
        target = _repo_path(covered_path)
        if target is None:
            errors.append(f"manifest coverage path is not repo-relative: {covered_path}")
            continue
        if target.is_dir():
            expected.update(
                str(path.relative_to(ROOT)) for path in target.rglob("*") if path.is_file()
            )
        elif target.is_file():
            expected.add(covered_path)
        else:
            errors.append(f"manifest coverage target does not exist: {covered_path}")

    if set(entries) != expected:
        missing = sorted(expected - set(entries))
        extra = sorted(set(entries) - expected)
        errors.append(f"manifest coverage mismatch: missing={missing}, extra={extra}")
    if str(manifest_path.relative_to(ROOT)) in entries:
        errors.append(f"manifest must not cover itself: {manifest['path']}")
    for relative_path, expected_hash in entries.items():
        target = ROOT / relative_path
        if not target.is_file() or _sha256_file(target) != expected_hash:
            errors.append(f"manifest artifact hash mismatch: {relative_path}")
    return errors


def integrity_errors() -> list[str]:
    """Return cross-record and artifact-integrity failures."""

    prompt_events = {
        record["event_id"]: record
        for _, record in jsonl_records(ROOT / "provenance" / "prompt-events.jsonl")
    }
    decisions = {
        record["decision_id"]: record
        for _, record in jsonl_records(ROOT / "provenance" / "human-decision-ledger.jsonl")
    }
    tickets = {
        record["ticket_id"]: record for _, record in json_records(ROOT / "provenance" / "tickets")
    }
    runs = {record["run_id"]: record for _, record in json_records(ROOT / "provenance" / "runs")}
    errors: list[str] = []

    for ticket_id, ticket in tickets.items():
        for event_id in ticket["prompt_event_ids"]:
            if event_id not in prompt_events:
                errors.append(f"{ticket_id}: unresolved PromptEvent {event_id}")
        for decision_id in ticket["decision_ids"]:
            if decision_id not in decisions:
                errors.append(f"{ticket_id}: unresolved HumanDecision {decision_id}")
        for commit_id in ticket["commit_ids"]:
            if not _git_commit_exists(commit_id):
                errors.append(f"{ticket_id}: unresolved commit {commit_id}")
        for run_id in ticket.get("run_ids", []):
            if run_id not in runs:
                errors.append(f"{ticket_id}: unresolved Run {run_id}")
        for evidence_path in ticket.get("supplemental_evidence", []):
            target = _repo_path(evidence_path)
            if target is None:
                errors.append(f"{ticket_id}: supplemental evidence path is not repo-relative")
            elif not target.exists():
                errors.append(f"{ticket_id}: missing supplemental evidence {evidence_path}")

    supersession_graph: dict[str, set[str]] = {}
    for run_id, run in runs.items():
        for ticket_id in run["ticket_ids"]:
            if ticket_id not in tickets:
                errors.append(f"{run_id}: unresolved Ticket {ticket_id}")
        commit_id = run["git_commit"]
        if commit_id is not None and not _git_commit_exists(commit_id):
            errors.append(f"{run_id}: unresolved commit {commit_id}")
        if run["schema_version"] != "1.1.0":
            continue

        errors.extend(artifact_errors(run_id, run))

        configuration = {(item["path"], item["sha256"]) for item in run["configuration_artifacts"]}
        inputs = {(item["path"], item["sha256"]) for item in run["input_artifacts"]}
        if not configuration <= inputs:
            errors.append(f"{run_id}: configuration artifacts must also be input artifacts")
        if run["command"] != run["replay"]["command"]:
            errors.append(f"{run_id}: command and replay.command differ")
        if PLACEHOLDER.search(run["replay"]["command"]):
            errors.append(f"{run_id}: replay command contains a placeholder")
        own_path = f"provenance/runs/{run_id}.json"
        if any(item["path"] == own_path for item in run["output_artifacts"]):
            errors.append(f"{run_id}: Run record must not hash itself")

        targets: set[str] = set()
        for superseded in run["supersedes"]:
            target = superseded["run_id"]
            if target not in runs:
                errors.append(f"{run_id}: unresolved superseded Run {target}")
            if target == run_id:
                errors.append(f"{run_id}: Run cannot supersede itself")
            targets.add(target)
        supersession_graph[run_id] = targets
        if "evidence_manifest" in run:
            errors.extend(
                f"{run_id}: {error}" for error in _manifest_errors(run["evidence_manifest"])
            )

    def visit(run_id: str, path: set[str]) -> None:
        if run_id in path:
            errors.append(f"supersession cycle includes {run_id}")
            return
        for target in supersession_graph.get(run_id, set()):
            visit(target, {*path, run_id})

    for run_id in supersession_graph:
        visit(run_id, set())
    return errors


def main() -> int:
    sources = [
        (jsonl_records(ROOT / "provenance" / "prompt-events.jsonl"), "prompt-event"),
        (
            jsonl_records(ROOT / "provenance" / "human-decision-ledger.jsonl"),
            "human-decision",
        ),
        (json_records(ROOT / "provenance" / "tickets"), "ticket"),
        (json_records(ROOT / "provenance" / "runs"), "run"),
    ]
    count = 0
    errors: list[str] = []
    for records, schema_name in sources:
        schema_path = SCHEMAS / f"{schema_name}.schema.json"
        try:
            for label, record in records:
                try:
                    validate_record(record, schema_path)
                    count += 1
                except Exception as exc:  # report all validation failures together
                    errors.append(f"{label}: {exc}")
        except Exception as exc:
            errors.append(f"{schema_name}: {exc}")

    if not errors:
        errors.extend(integrity_errors())

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"records-ok count={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
