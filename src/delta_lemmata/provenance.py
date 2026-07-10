"""Validation and hashing primitives for Delta provenance records."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 hex digest."""

    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    """Hash UTF-8 text without altering whitespace or Unicode."""

    return sha256_bytes(value.encode("utf-8"))


def canonical_json_bytes(record: Mapping[str, Any]) -> bytes:
    """Serialize a mapping deterministically for integrity checks."""

    return json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_schema(schema_path: Path) -> dict[str, Any]:
    """Load one local JSON Schema document."""

    with schema_path.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = json.load(handle)
    Draft202012Validator.check_schema(loaded)
    return loaded


def validate_record(record: Mapping[str, Any], schema_path: Path) -> None:
    """Raise jsonschema.ValidationError when a record violates its schema."""

    validator = Draft202012Validator(
        load_schema(schema_path),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    validator.validate(dict(record))


def write_record_atomic(
    target: Path,
    record: Mapping[str, Any],
    schema_path: Path,
) -> None:
    """Validate and atomically write one JSON record.

    The caller remains responsible for assigning IDs and preventing concurrent
    writers from choosing the same target path.
    """

    validate_record(record, schema_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(canonical_json_bytes(record) + b"\n")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
