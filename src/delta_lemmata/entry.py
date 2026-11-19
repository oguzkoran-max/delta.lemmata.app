"""Opening and read-only example views, shared by the workbench and portable preview."""

from __future__ import annotations

from html import escape
from importlib.resources import files
from itertools import combinations

from delta_lemmata.catalog import text
from delta_lemmata.result_view import ResultCellV1, ResultViewV1

_DATA = files("delta_lemmata").joinpath("data")
EXAMPLE_FILE = "example-synthetic-result-20261113.json"


def example_record() -> bytes:
    return _DATA.joinpath(EXAMPLE_FILE).read_bytes()


def entry_css() -> str:
    return _DATA.joinpath("entry.css").read_text(encoding="utf-8")


def link(url: str, label: str, css_class: str = "") -> str:
    return (
        f'<a class="{css_class}" href="{escape(url, quote=True)}" target="_self">'
        f"{escape(label)}</a>"
    )


def _masthead(home: str) -> str:
    return (
        '<header class="de-mast"><div class="de-lockup">'
        + link(home, "Δ  Delta", "de-wordmark")
        + f"<span>{text('entry.tagline')}</span></div>"
        + f'<span class="de-release">{text("header.release_public_alpha")}'
        + f" · {text('header.release_experimental')}</span></header>"
    )


def _pair_distances(cell: ResultCellV1) -> list[tuple[float, str, str]]:
    matrix = cell.matrix
    if matrix is None:
        raise ValueError("The recorded example requires a completed comparison.")
    keys = matrix.document_keys
    return sorted(
        (float(matrix.values[i][j]), keys[i], keys[j]) for i, j in combinations(range(len(keys)), 2)
    )


def _distance_table(cell: ResultCellV1) -> str:
    rows = "".join(
        f'<tr><th scope="row">{escape(left)} <span>↔</span> {escape(right)}</th>'
        f"<td>{distance:.6f}</td></tr>"
        for distance, left, right in _pair_distances(cell)
    )
    return (
        f'<table class="de-table"><caption>{text("entry.pairs")}</caption><thead><tr>'
        f'<th scope="col">{text("entry.pair")}</th>'
        f'<th scope="col">{text("entry.distance")}</th>'
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def landing(view: ResultViewV1, *, home: str, example: str, upload: str) -> str:
    reference = next(cell for cell in view.cells if cell.is_reference)
    return (
        '<article class="de-page">'
        + _masthead(home)
        + '<div class="de-hero"><div class="de-intro">'
        + f"<h1>{text('entry.title')}</h1><p>{text('entry.intro')}</p>"
        + '<nav class="de-actions">'
        + link(example, text("entry.example"), "de-primary")
        + link(upload, text("entry.upload"), "de-secondary")
        + '</nav></div><figure class="de-specimen">'
        + f"<figcaption>{text('entry.specimen')}</figcaption>"
        + f"<p>{text('entry.caption', mfw=reference.mfw)}</p>"
        + _distance_table(reference)
        + f'<p class="de-note">{text("entry.read")}</p></figure></div></article>'
    )


def example(
    view: ResultViewV1, cell: ResultCellV1, *, home: str, upload: str, setting_url: str
) -> str:
    setting_links = []
    for comparison in view.cells:
        mfw = comparison.mfw
        label = f"{mfw:,}"
        if mfw == cell.mfw:
            setting_links.append(f'<span aria-current="true">{label}</span>')
        else:
            setting_links.append(link(setting_url.format(mfw=mfw), label))
    docs = "".join(
        f"<li><strong>{escape(doc.key)}</strong><span>{escape(doc.title)}</span></li>"
        for doc in view.documents
    )
    distance, left, right = _pair_distances(cell)[0]
    closest_at = {
        comparison.mfw: _pair_distances(comparison)[0][1:]
        for comparison in view.cells
        if comparison.mfw in (100, 500) and comparison.matrix is not None
    }
    same_pair_note = (
        f'<p class="de-note">{text("entry.closest_both")}</p>'
        if closest_at.get(100) == closest_at.get(500) == (left, right)
        else ""
    )
    return (
        '<article class="de-page">'
        + _masthead(home)
        + '<div class="de-result">'
        + link(home, "← " + text("entry.home"), "de-back")
        + f'<p class="de-source">{text("entry.sample_source")}</p>'
        + f"<h1>{text('entry.sample_title')}</h1>"
        + f'<p class="de-lead">{text("entry.sample_intro")}</p>'
        + '<div class="de-setting">'
        + f"<strong>{text('entry.setting')}</strong>"
        + f'<nav aria-label="{text("entry.setting")}" class="de-switch">'
        + "".join(setting_links)
        + "</nav>"
        + f'<p class="de-setting-hint">{text("entry.setting_hint")}</p>'
        + '</div><div class="de-grid"><section class="de-pair">'
        + f'<h2>{text("entry.closest")}</h2><p class="de-bigpair">{left} ↔ {right}</p>'
        + f"<p>{text('entry.closest_scope')}</p>"
        + f'<p class="de-distance">{distance:.6f} <span>· {text("entry.distance")}</span></p>'
        + same_pair_note
        + '</section><section class="de-docs">'
        + f"<h2>{text('entry.documents')}</h2><ul>{docs}</ul></section></div>"
        + '<div class="de-grid de-evidence"><section>'
        + _distance_table(cell)
        + f'<p class="de-note">{text("entry.detail")}</p></section><aside>'
        + f"<h2>{text('evidence.limits')}</h2><p>{escape(view.interpretation.proximity)}</p>"
        + f"<p>{escape(view.interpretation.nearest_neighbour)}</p></aside></div>"
        + link(upload, text("entry.upload"), "de-secondary")
        + "</div></article>"
    )
