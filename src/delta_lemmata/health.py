"""Public-safe health information for the workbench shell."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

from delta_lemmata import __version__

_BUILD_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def _safe_build_id(candidate: str | None) -> str:
    value = candidate or "development"
    if _BUILD_ID.fullmatch(value):
        return value
    return "invalid"


def public_health(build_id: str | None = None) -> Mapping[str, str | bool]:
    """Return an allowlisted status record with no path or environment dump."""

    resolved_build = build_id if build_id is not None else os.getenv("DELTA_BUILD_ID")
    return {
        "schema_version": "1.0.0",
        "status": "public-alpha",
        "version": __version__,
        "build_id": _safe_build_id(resolved_build),
        "analysis_engine": "r-stylo-connected",
        "runtime_ai": False,
        "analytics": False,
        "login": False,
        "permanent_storage": False,
    }
