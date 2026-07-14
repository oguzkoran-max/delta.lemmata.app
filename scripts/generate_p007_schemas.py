#!/usr/bin/env python3
"""Generate or verify the five closed P007 JSON Schemas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from delta_lemmata.corpus_health_models import CorpusHealthReportV1
from delta_lemmata.preprocessing_models import (
    AnalysisPreparationReceiptV1,
    CorpusAnalysisAnnotationsV1,
    PreprocessingConfigV1,
    PreprocessingManifestV1,
    export_p007_schema,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
MODELS: dict[str, type[BaseModel]] = {
    "analysis-preparation-receipt-v1": AnalysisPreparationReceiptV1,
    "corpus-analysis-annotations-v1": CorpusAnalysisAnnotationsV1,
    "corpus-health-report-v1": CorpusHealthReportV1,
    "preprocessing-config-v1": PreprocessingConfigV1,
    "preprocessing-manifest-v1": PreprocessingManifestV1,
}


def _schema_bytes(name: str, model: type[BaseModel]) -> bytes:
    schema_id = f"https://delta.lemmata.app/schemas/{name}.schema.json"
    schema: dict[str, Any] = export_p007_schema(model, schema_id)
    return (json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale: list[str] = []
    for name, model in MODELS.items():
        target = SCHEMAS / f"{name}.schema.json"
        expected = _schema_bytes(name, model)
        if args.check:
            if not target.is_file() or target.read_bytes() != expected:
                stale.append(target.relative_to(ROOT).as_posix())
        else:
            target.write_bytes(expected)
    if stale:
        for path in stale:
            print(f"stale-p007-schema: {path}")
        return 1
    print(f"p007-schemas-ok count={len(MODELS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
