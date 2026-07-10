#!/usr/bin/env python3
"""Validate Delta's JSON and JSONL provenance records."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from delta_lemmata.provenance import validate_record

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


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

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"records-ok count={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
