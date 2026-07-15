#!/usr/bin/env python3
"""Generate or verify the closed P008 workflow JSON Schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from delta_lemmata.workflow_models import ResolvedWorkflowConfigV1, export_p008_schema

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
NAME = "resolved-workflow-config-v1"


def _schema_bytes() -> bytes:
    schema_id = f"https://delta.lemmata.app/schemas/{NAME}.schema.json"
    schema: dict[str, Any] = export_p008_schema(ResolvedWorkflowConfigV1, schema_id)
    return (json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = SCHEMAS / f"{NAME}.schema.json"
    expected = _schema_bytes()
    if args.check:
        if not target.is_file() or target.read_bytes() != expected:
            print(f"stale-p008-schema: {target.relative_to(ROOT).as_posix()}")
            return 1
    else:
        target.write_bytes(expected)
    print("p008-schemas-ok count=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
