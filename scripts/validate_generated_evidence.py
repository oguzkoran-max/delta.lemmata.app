#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED_FILES = (
    "checksums.sha256",
    "detect-secrets.json",
    "pip-audit.json",
    "python-environment.txt",
    "python-sbom.cdx.json",
    "r-sbom.cdx.json",
    "r-session-info.txt",
    "runtime-requirements.txt",
)
JSON_FILES = (
    "detect-secrets.json",
    "pip-audit.json",
    "python-sbom.cdx.json",
    "r-sbom.cdx.json",
)
SOURCE_CHECKSUM_PATHS = (
    "VERSION",
    "uv.lock",
    "renv.lock",
    "CITATION.cff",
    "codemeta.json",
    "containers/base-images.lock.json",
    "containers/ci-actions.lock.json",
)
PRIVATE_MARKERS = (
    "/" + "Users/",
    "/" + "home/runner/work/",
    "file://",
    "CloudStorage",
    "oguzkoran@gmail.com",
)
WINDOWS_USER_PATH = re.compile(r"[A-Za-z]:\\\\Users\\\\", re.IGNORECASE)
CHECKSUM_LINE = re.compile(r"([0-9a-f]{64})  (.+)")


class EvidencePackageError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise EvidencePackageError(f"not UTF-8: {path.name}") from exc
    if "\x00" in text:
        raise EvidencePackageError(f"NUL byte found: {path.name}")
    return text


def _validate_source_checksums(text: str) -> None:
    parsed: list[str] = []
    for line in text.splitlines():
        match = CHECKSUM_LINE.fullmatch(line)
        if match is None:
            raise EvidencePackageError("invalid source checksum line")
        parsed.append(match.group(2))
    if tuple(parsed) != SOURCE_CHECKSUM_PATHS:
        raise EvidencePackageError("source checksum inventory mismatch")


def validate_package(directory: Path) -> None:
    if not directory.is_dir():
        raise EvidencePackageError("evidence package directory is missing")
    entries = tuple(sorted(path.name for path in directory.iterdir()))
    if entries != EXPECTED_FILES:
        raise EvidencePackageError("evidence package inventory mismatch")

    texts: dict[str, str] = {}
    for name in EXPECTED_FILES:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise EvidencePackageError(f"not a regular file: {name}")
        if path.stat().st_size == 0:
            raise EvidencePackageError(f"empty evidence file: {name}")
        text = _read_text(path)
        texts[name] = text
        for marker in PRIVATE_MARKERS:
            if marker in text:
                raise EvidencePackageError(f"private path marker in {name}: {marker}")
        if WINDOWS_USER_PATH.search(text):
            raise EvidencePackageError(f"private Windows user path in {name}")

    for name in JSON_FILES:
        try:
            loaded = json.loads(texts[name])
        except json.JSONDecodeError as exc:
            raise EvidencePackageError(f"invalid JSON: {name}") from exc
        if not isinstance(loaded, dict):
            raise EvidencePackageError(f"JSON root is not an object: {name}")

    _validate_source_checksums(texts["checksums.sha256"])


def manifest_text(directory: Path) -> str:
    validate_package(directory)
    return "".join(f"{_sha256(directory / name)}  {name}\n" for name in EXPECTED_FILES)


def verify_manifest(directory: Path, manifest: Path) -> None:
    if not manifest.is_file() or manifest.is_symlink():
        raise EvidencePackageError("evidence manifest is missing or unsafe")
    if _read_text(manifest) != manifest_text(directory):
        raise EvidencePackageError("evidence manifest mismatch")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--manifest", type=Path)
    group.add_argument("--write-manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_package(args.directory)
        if args.write_manifest is not None:
            args.write_manifest.write_text(manifest_text(args.directory), encoding="utf-8")
            verify_manifest(args.directory, args.write_manifest)
        elif args.manifest is not None:
            verify_manifest(args.directory, args.manifest)
    except (EvidencePackageError, OSError) as exc:
        print(f"evidence-package-error: {exc}", file=sys.stderr)
        return 1
    print(f"evidence-package-ok path={args.directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
