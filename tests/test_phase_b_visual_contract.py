from __future__ import annotations

import hashlib
import tomllib
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from unittest.mock import Mock

import pytest

from delta_lemmata import webapp as webapp_module
from delta_lemmata.catalog import text
from delta_lemmata.stylo_contracts import STRUCTURAL_TOLERANCE
from delta_lemmata.ui_theme import APP_CSS

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "src" / "delta_lemmata" / "data" / "fonts" / "InterVariable.woff2"
FONT_LICENSE = ROOT / "src" / "delta_lemmata" / "data" / "fonts" / "LICENSE-Inter.txt"
FONT_RECORD = ROOT / "src" / "delta_lemmata" / "data" / "fonts" / "VENDORED.md"


def test_phase_b_theme_uses_the_approved_a51_tokens_and_dimensions() -> None:
    required = {
        "--delta-tertiary: #6f6f6f;",
        "--delta-control-line: #6f7d78;",
        "--delta-mint-soft: #f4faf7;",
        "--delta-slate: #5e6f86;",
        "--delta-coral-text: #a33d1c;",
        "--delta-amber-text: #6b4d00;",
        "max-width: 1240px;",
        ".delta-header {",
        "min-height: 64px;",
        ".delta-skip-link {",
        "min-height: 44px;",
        ".delta-tech summary",
        ".delta-footer {",
        '.st-key-p009_mds_square [data-testid="stVegaLiteChart"] {',
        "height: auto !important;",
        "aspect-ratio: 60 / 61;",
        "aspect-ratio: 60 / 61.3;",
        "aspect-ratio: 60 / 61.18;",
        ".delta-mds-legend {",
        ".delta-mds-unknown {",
        ".delta-purpose-guide-mobile {",
        ".delta-readiness-band {",
        ".delta-readiness-band.is-exploratory {",
        ".delta-review-metrics {",
        '[data-testid="stVegaLiteChart"] details > summary',
        'button[data-testid="stBaseButton-elementToolbar"]',
    }
    assert required <= set(APP_CSS.splitlines()) | {item for item in required if item in APP_CSS}
    assert "@media (max-width: 760px)" in APP_CSS
    assert '.st-key-p009_result_cell_selector [data-testid="stRadioGroup"]' in APP_CSS
    assert 'label[data-testid="stRadioOption"]:has(input:checked)' in APP_CSS
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in APP_CSS


def test_inter_is_self_hosted_with_recorded_provenance_and_no_runtime_font_request() -> None:
    assert FONT.is_file()
    assert FONT_LICENSE.is_file()
    assert hashlib.sha256(FONT.read_bytes()).hexdigest() == (
        "693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3"
    )
    assert 'src: url("data:font/woff2;base64,' in APP_CSS
    assert "http://" not in APP_CSS
    assert "https://" not in APP_CSS
    record = FONT_RECORD.read_text(encoding="utf-8")
    assert "rsms/inter" in record
    assert "693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3" in record
    with (ROOT / "pyproject.toml").open("rb") as handle:
        configuration = tomllib.load(handle)
    assert "data/fonts/*" in configuration["tool"]["setuptools"]["package-data"]["delta_lemmata"]
    packaged_fonts = files("delta_lemmata").joinpath("data", "fonts")
    assert packaged_fonts.joinpath("InterVariable.woff2").read_bytes() == FONT.read_bytes()
    assert packaged_fonts.joinpath("LICENSE-Inter.txt").read_text(encoding="utf-8") == (
        FONT_LICENSE.read_text(encoding="utf-8")
    )
    assert packaged_fonts.joinpath("VENDORED.md").read_text(encoding="utf-8") == record


def test_streamlit_source_sans_assets_are_pinned_and_recorded() -> None:
    assert version("streamlit") == "1.59.1"
    media = files("streamlit").joinpath("static", "static", "media")
    upright = media.joinpath("SourceSansVF-Upright.ttf.BsWL4Kly.woff2").read_bytes()
    italic = media.joinpath("SourceSansVF-Italic.ttf.Bt9VkdQ3.woff2").read_bytes()
    assert hashlib.sha256(upright).hexdigest() == (
        "5f16566f7a40d39b339ad26be151fa5a1ab1f0c2574c7a2e619765584a1acbd8"
    )
    assert hashlib.sha256(italic).hexdigest() == (
        "b4959abc0569392f87c6c6ac612f90e3fe0104d283724189b7d8b6f61af347d3"
    )
    record = FONT_RECORD.read_text(encoding="utf-8")
    assert "Source Sans 3 runtime asset" in record
    assert "Source Sans 3.052" in record
    assert "SIL Open Font License 1.1" in record
    assert "streamlit==1.59.1" in record


def test_main_landmark_bridge_promotes_the_real_streamlit_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    render = Mock()
    monkeypatch.setattr(webapp_module.st, "html", render)

    webapp_module._render_main_landmark_bridge()

    script = render.call_args.args[0]
    assert "document.querySelector('[data-testid=\"stMain\"]')" in script
    assert "main.id = 'delta-main-landmark'" in script
    assert "main.setAttribute('role', 'main')" in script
    assert "root.dataset.deltaSkipHandler" in script
    assert "document.getElementById('delta-content-start')" in script
    assert "target.focus({preventScroll: true})" in script
    assert "target.scrollIntoView({block: 'start'})" in script
    assert render.call_args.kwargs == {
        "width": "content",
        "unsafe_allow_javascript": True,
    }


def test_skip_target_is_a_separate_focusable_content_anchor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    render = Mock()
    monkeypatch.setattr(webapp_module.st, "markdown", render)

    webapp_module._render_content_anchor()

    assert render.call_args.args[0] == (
        '<span id="delta-content-start" class="delta-main-anchor" tabindex="-1"></span>'
    )
    assert render.call_args.kwargs == {"unsafe_allow_html": True}
    monkeypatch.setattr(webapp_module.st, "html", Mock())
    render.reset_mock()
    webapp_module._render_header(
        {"version": "test", "build_id": "test"},
        webapp_module.CorpusSubstage.UPLOAD,
        evidence_active=False,
    )
    assert 'href="#delta-content-start"' in render.call_args.args[0]


def test_results_copy_matches_the_scientific_display_contract() -> None:
    assert text("results.selector.reference_suffix") == ""
    assert text("results.reference_note").startswith("500 MFW opens first")
    assert text("results.reference_unavailable_note").startswith("500 MFW was unavailable")
    assert text("results.method.delta.definition") == (
        "The mean absolute difference between word-frequency profiles standardized with means "
        "and standard deviations estimated from the known reference texts in the frozen fitting "
        "basis; an unknown holdout is projected only after fitting."
    )
    assert "known reference texts" in text("results.method.mfw.definition")
    assert "displayed to six decimal places" in text("results.matrix.body")
    assert "canonical record retains the stored numerical values" in text("results.matrix.body")
    neighbour_copy = text("results.neighbour.body")
    assert "1e-12" in neighbour_copy
    assert "Nearness need not be mutual" in neighbour_copy
    assert STRUCTURAL_TOLERANCE == 1e-12
    mds_copy = text("results.mds.body")
    assert "matrix remains the authoritative evidence" in mds_copy
    assert "projection artefacts" in mds_copy


def test_review_and_results_expose_accessible_table_and_technical_detail_language() -> None:
    assert text("review.table_scroll") == "Wide table: scroll sideways if columns are cut off."
    assert text("results.table_scroll") == "Wide table: scroll sideways if columns are cut off."
    assert text("review.technical_details") == "Technical details"
    assert text("review.selected_purpose", purpose="Text proximity").startswith("Selected purpose:")
    assert text("results.title") == "Explore the relative distances"
    assert text("results.method.title") == "Method key"


def test_parameter_method_explanation_precedes_confirmation_and_starts_exposed() -> None:
    source = (ROOT / "src" / "delta_lemmata" / "webapp.py").read_text(encoding="utf-8")
    parameters = source[source.index("def _render_parameters_stage") :]
    explanation = parameters.index("_render_parameter_explanations()")
    confirmation = parameters.index("confirmed = st.checkbox(")
    run_control = parameters.index("run_clicked = st.button(")

    assert explanation < confirmation < run_control
    helper = source[
        source.index("def _render_parameter_explanations") : source.index("def _result_descriptors")
    ]
    assert 'st.expander(text("parameters.learn.title"), expanded=True)' in helper
