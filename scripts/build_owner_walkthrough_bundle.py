#!/usr/bin/env python3
"""Build the deterministic, rights-safe corpus for the owner walkthrough."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

FEATURE_COUNT = 1_100
DOCUMENT_COUNT = 3
AUTHOR = "Delta Synthetic Author"
RIGHTS_STATE = "analysis_only"


def _word(index: int) -> str:
    value = index
    suffix = []
    for _ in range(4):
        value, remainder = divmod(value, 26)
        suffix.append(chr(ord("a") + remainder))
    return "lex" + "".join(reversed(suffix))


def _documents() -> tuple[tuple[str, bytes], ...]:
    features = tuple(_word(index) for index in range(FEATURE_COUNT))
    steps = (1, 7, 13)
    offsets = (0, 37, 83)
    documents = []
    for document_index, (step, offset) in enumerate(zip(steps, offsets, strict=True)):
        if math.gcd(step, FEATURE_COUNT) != 1:
            raise RuntimeError("Synthetic permutation step is not coprime")
        tokens = []
        for position in range(FEATURE_COUNT):
            feature_index = (position * step + offset) % FEATURE_COUNT
            repeat = 1 + ((feature_index + document_index) % DOCUMENT_COUNT)
            tokens.extend((features[feature_index],) * repeat)
        documents.append(
            (
                f"delta_owner_walkthrough_{document_index + 1}.txt",
                (" ".join(tokens) + "\n").encode(),
            )
        )
    return tuple(documents)


def _write_new(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_bundle(output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    documents = _documents()
    records = []
    for filename, payload in documents:
        _write_new(output / filename, payload)
        records.append(
            {
                "filename": filename,
                "sha256": _digest(payload),
                "bytes": len(payload),
                "token_count": len(payload.decode("utf-8").split()),
                "unique_feature_count": len(set(payload.decode("utf-8").split())),
                "primary_author_name": AUTHOR,
                "bibliographic_citation": (
                    f"Synthetic Delta owner-walkthrough source record for {filename}."
                ),
                "documented_rights_state": RIGHTS_STATE,
            }
        )

    manifest = {
        "schema_version": "owner-walkthrough-corpus-v1",
        "purpose": "interface-owner-acceptance-only",
        "feature_count": FEATURE_COUNT,
        "documents": records,
        "limitations": [
            "The texts are deterministic synthetic fixtures, not literary works.",
            "Their output is not a benchmark, literary finding, or usability result.",
            "Use the Analysis only rights state; do not treat this bundle as a public corpus.",
        ],
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=True, indent=2) + "\n").encode()
    _write_new(output / "walkthrough-manifest.json", manifest_bytes)

    readme = f"""# Delta Owner Walkthrough Corpus

This directory contains {DOCUMENT_COUNT} deterministic synthetic TXT files for the
owner acceptance walkthrough. They are fixtures, not literary or benchmark data.

For each document enter:

- Primary author name: `{AUTHOR}`
- Bibliographic citation: copy the document-specific value from
  `walkthrough-manifest.json`
- Documented rights state: `Analysis only`

Upload only the three `.txt` files. Keep the manifest and checksum file outside
the upload control. Do not interpret the resulting distances as literary findings.
""".encode()
    _write_new(output / "README.md", readme)

    checksum_names = sorted(
        [record["filename"] for record in records] + ["README.md", "walkthrough-manifest.json"]
    )
    checksum_lines = []
    for name in checksum_names:
        payload = (output / str(name)).read_bytes()
        checksum_lines.append(f"{_digest(payload)}  {name}\n")
    _write_new(output / "SHA256SUMS", "".join(checksum_lines).encode())
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    manifest = build_bundle(arguments.output)
    print(
        "owner-walkthrough-bundle-ok "
        f"documents={len(manifest['documents'])} features={manifest['feature_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
