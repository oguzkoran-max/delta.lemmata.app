#!/usr/bin/env python3
"""Fail on obvious secrets, local paths, or forbidden corpus directories."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".tools", ".venv", "generated", "library", "staging"}
TEXT_SUFFIXES = {
    "",
    ".cff",
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".r",
    ".R",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
PATTERNS = {
    "macOS absolute user path": re.compile(r"/" + r"Users/[A-Za-z0-9._-]+/"),
    "Linux absolute home path": re.compile(r"/" + r"home/[A-Za-z0-9._-]+/"),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "assigned API secret": re.compile(
        r"(?i)(?<![A-Za-z0-9_])(?:api[_-]?key|secret|token)\s*[:=]\s*"
        r"['\"][A-Za-z0-9_./+=-]{12,}['\"]"
    ),
}
FORBIDDEN_DIRECTORIES = {"data", "uploads", "workspaces", "exports", "secrets"}


def should_scan(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return not EXCLUDED_PARTS.intersection(relative.parts) and path.suffix in TEXT_SUFFIXES


def main() -> int:
    errors: list[str] = []
    for directory in FORBIDDEN_DIRECTORIES:
        candidate = ROOT / directory
        if candidate.exists() and any(candidate.iterdir()):
            errors.append(f"forbidden runtime/corpus directory is not empty: {directory}")

    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_scan(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{path.relative_to(ROOT)}: {name}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("repository-scan-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
