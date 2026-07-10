from __future__ import annotations

import tomllib
from pathlib import Path

from delta_lemmata.workbench import RUNTIME_POLICY

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_policy_has_no_ai_analytics_login_or_storage() -> None:
    assert RUNTIME_POLICY.runtime_ai is False
    assert RUNTIME_POLICY.analytics is False
    assert RUNTIME_POLICY.login is False
    assert RUNTIME_POLICY.permanent_storage is False
    assert RUNTIME_POLICY.external_endpoints == ()


def test_runtime_dependencies_contain_no_external_ai_or_analytics_client() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    dependencies = "\n".join(project["dependencies"]).casefold()
    prohibited = ("openai", "anthropic", "google-analytics", "sentry", "auth0", "mixpanel")
    assert all(name not in dependencies for name in prohibited)


def test_streamlit_usage_telemetry_is_disabled() -> None:
    with (ROOT / ".streamlit" / "config.toml").open("rb") as handle:
        config = tomllib.load(handle)
    assert config["browser"]["gatherUsageStats"] is False


def test_application_source_declares_no_remote_endpoint() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "src" / "delta_lemmata").glob("*.py")
    )
    assert "https://" not in source
    assert "http://" not in source
