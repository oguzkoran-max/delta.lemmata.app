#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class SbomNormalizationError(ValueError):
    pass


def _component_list(document: dict[str, Any]) -> list[dict[str, Any]]:
    raw_components = document.get("components")
    if not isinstance(raw_components, list):
        raise SbomNormalizationError("components must be an array")
    components: list[dict[str, Any]] = []
    for raw_component in raw_components:
        if not isinstance(raw_component, dict):
            raise SbomNormalizationError("each component must be an object")
        components.append(raw_component)
    metadata = document.get("metadata")
    if isinstance(metadata, dict):
        root_component = metadata.get("component")
        if isinstance(root_component, dict):
            components.append(root_component)
    return components


def normalize(document: dict[str, Any]) -> int:
    removed = 0
    for component in _component_list(document):
        raw_references = component.get("externalReferences")
        if raw_references is None:
            continue
        if not isinstance(raw_references, list):
            raise SbomNormalizationError("externalReferences must be an array")
        references: list[Any] = []
        for reference in raw_references:
            if not isinstance(reference, dict):
                raise SbomNormalizationError("each external reference must be an object")
            url = reference.get("url")
            if isinstance(url, str) and url.startswith("file://"):
                removed += 1
                continue
            references.append(reference)
        if references:
            component["externalReferences"] = references
        else:
            component.pop("externalReferences", None)
    return removed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("sbom", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        loaded = json.loads(args.sbom.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise SbomNormalizationError("SBOM root must be an object")
        removed = normalize(loaded)
        args.sbom.write_text(
            json.dumps(loaded, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (json.JSONDecodeError, OSError, SbomNormalizationError) as exc:
        print(f"python-sbom-normalization-error: {exc}", file=sys.stderr)
        return 1
    print(f"python-sbom-normalized removed_local_references={removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
