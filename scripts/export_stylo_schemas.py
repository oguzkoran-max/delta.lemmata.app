#!/usr/bin/env python3
"""Export checked-in JSON Schemas from the canonical P006 wire models."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from delta_lemmata.stylo_contracts import (
    DirectStyloOracleV1,
    WorkerFatalErrorV1,
    WorkerInputV1,
    WorkerResultV1,
    export_stylo_schema,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
SCHEMAS: dict[str, type[BaseModel]] = {
    "direct-stylo-oracle-v1.schema.json": DirectStyloOracleV1,
    "stylo-worker-input-v1.schema.json": WorkerInputV1,
    "stylo-worker-result-v1.schema.json": WorkerResultV1,
    "stylo-worker-fatal-error-v1.schema.json": WorkerFatalErrorV1,
}


def main() -> None:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMAS.items():
        schema = export_stylo_schema(
            model,
            f"https://delta.lemmata.app/schemas/{filename}",
        )
        (SCHEMA_DIR / filename).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
