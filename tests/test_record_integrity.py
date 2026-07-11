from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_records", ROOT / "scripts" / "validate_records.py"
)
assert SPEC is not None and SPEC.loader is not None
VALIDATE_RECORDS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATE_RECORDS)


def test_provenance_links_commits_and_artifacts_are_resolvable() -> None:
    assert VALIDATE_RECORDS.integrity_errors() == []
