from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_owner_walkthrough_bundle.py"


def _run(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(root.iterdir())}


def test_owner_walkthrough_bundle_is_deterministic_and_self_checking(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    assert _run(first).returncode == 0
    assert _run(second).returncode == 0
    assert _snapshot(first) == _snapshot(second)

    manifest = json.loads((first / "walkthrough-manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "owner-walkthrough-corpus-v1"
    assert manifest["purpose"] == "interface-owner-acceptance-only"
    assert manifest["feature_count"] == 1100
    assert len(manifest["documents"]) == 3
    assert {record["unique_feature_count"] for record in manifest["documents"]} == {1100}
    assert {record["documented_rights_state"] for record in manifest["documents"]} == {
        "analysis_only"
    }

    for line in (first / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, filename = line.split("  ", maxsplit=1)
        assert hashlib.sha256((first / filename).read_bytes()).hexdigest() == expected


def test_owner_walkthrough_bundle_refuses_to_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "bundle"
    assert _run(output).returncode == 0
    before = _snapshot(output)
    second = _run(output)
    assert second.returncode != 0
    assert "FileExistsError" in second.stderr
    assert _snapshot(output) == before
