from __future__ import annotations

import json
from pathlib import PurePosixPath

from delta_lemmata.health import public_health


def test_public_health_is_allowlisted_and_reports_the_bounded_engine() -> None:
    health = dict(public_health("P002-test.1"))
    assert health == {
        "schema_version": "1.0.0",
        "status": "public-alpha",
        "version": "0.0.0.dev0",
        "build_id": "P002-test.1",
        "analysis_engine": "r-stylo-connected",
        "runtime_ai": False,
        "analytics": False,
        "login": False,
        "permanent_storage": False,
    }


def test_public_health_rejects_a_path_or_secret_shaped_build_id() -> None:
    malicious = f"{PurePosixPath('/', 'private', 'project')}?token=secret"
    serialized = json.dumps(dict(public_health(malicious)))
    assert malicious not in serialized
    assert "secret" not in serialized
    assert '"build_id": "invalid"' in serialized
