from __future__ import annotations

import re
from pathlib import Path

from delta_lemmata.catalog import DEFAULT_LOCALE, SUPPORTED_LOCALES, UI_CATALOG, text
from delta_lemmata.corpus_health_models import CorpusHealthFindingCode
from delta_lemmata.workbench import MODE_BODY_KEYS, MODE_LABEL_KEYS, PURPOSES, STATE_PRESENTATIONS

ROOT = Path(__file__).resolve().parents[1]


def test_p002_ships_one_central_english_catalog() -> None:
    assert DEFAULT_LOCALE == "en"
    assert SUPPORTED_LOCALES == ("en",)
    assert len(UI_CATALOG["en"]) >= 70
    assert text("header.version", version="1.2.3") == "Version 1.2.3"


def test_every_shell_contract_key_exists_in_the_catalog() -> None:
    keys = set(UI_CATALOG["en"])
    for purpose in PURPOSES:
        assert {
            purpose.label_key,
            purpose.question_key,
            purpose.use_key,
            purpose.boundary_key,
        } <= keys
    for key in (*MODE_LABEL_KEYS.values(), *MODE_BODY_KEYS.values()):
        assert key in keys
    for presentation in STATE_PRESENTATIONS.values():
        assert {
            presentation.label_key,
            presentation.title_key,
            presentation.body_key,
        } <= keys


def test_every_corpus_health_finding_has_beginner_facing_copy() -> None:
    keys = set(UI_CATALOG["en"])
    for code in CorpusHealthFindingCode:
        prefix = f"prepare.finding.{code.value}"
        assert {f"{prefix}.title", f"{prefix}.body", f"{prefix}.action"} <= keys


def test_catalog_copy_avoids_prohibited_claims() -> None:
    copy = "\n".join(UI_CATALOG["en"].values()).casefold()
    prohibited = (
        "find the author",
        "confidence score",
        "probability of correctness",
        "easy for everyone",
        "no knowledge needed",
        "reproducible",
        "pre-registered",
        "fair-certified",
        "fair-compliant",
        "completely isolated",
    )
    assert all(phrase not in copy for phrase in prohibited)


def test_public_alpha_status_is_centralized_and_explicit() -> None:
    assert text("header.release_public_alpha") == "Public alpha"
    assert text("header.release_experimental") == "Experimental"
    assert text("header.release_status") == "Release status: Public alpha, experimental"


def test_user_facing_copy_does_not_expose_development_ticket_jargon() -> None:
    copy = "\n".join(UI_CATALOG["en"].values())
    assert re.search(r"\bP\d{3}\b|\btickets?\b", copy, flags=re.IGNORECASE) is None


def test_user_facing_copy_is_not_duplicated_in_app_modules() -> None:
    source = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in ("app.py", "src/delta_lemmata/webapp.py")
    )
    long_values = (value for value in UI_CATALOG["en"].values() if len(value) >= 20)
    assert all(value not in source for value in long_values)
