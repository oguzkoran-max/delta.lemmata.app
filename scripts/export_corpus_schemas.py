#!/usr/bin/env python3
"""Export checked-in JSON Schemas from the canonical P004 Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path

from delta_lemmata.corpus import (
    AssetRightsRecord,
    CorpusInventory,
    ValidationReport,
    VocabularyProfile,
    export_json_schema,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
SCHEMAS = {
    "asset-rights-v2.schema.json": (
        AssetRightsRecord,
        "https://delta.lemmata.app/schemas/asset-rights-v2.schema.json",
    ),
    "corpus-inventory.schema.json": (
        CorpusInventory,
        "https://delta.lemmata.app/schemas/corpus-inventory.schema.json",
    ),
    "corpus-validation-report.schema.json": (
        ValidationReport,
        "https://delta.lemmata.app/schemas/corpus-validation-report.schema.json",
    ),
    "corpus-vocabularies.schema.json": (
        VocabularyProfile,
        "https://delta.lemmata.app/schemas/corpus-vocabularies.schema.json",
    ),
}


def main() -> None:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for filename, (model, schema_id) in SCHEMAS.items():
        schema = export_json_schema(model, schema_id)
        target = SCHEMA_DIR / filename
        target.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
