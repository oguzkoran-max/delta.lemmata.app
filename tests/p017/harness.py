#!/usr/bin/env python3
"""P017 tracked browser harness: states, viewports, a11y semantics, perf, evidence.

Usage: .venv/bin/python tests/p017/harness.py --iteration 1
Outputs: provenance/evidence/P017/iterations/it-<N>/ (shots, report.json,
contact sheets, scroll walkthrough video). Reproducible from the repo root on
any machine with Playwright Chromium installed; no absolute paths.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import socket
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "prototypes" / "p017-delta-cinematic-narrative"
POSITIONS = [0, 8, 16, 25, 33, 42, 50, 58, 67, 75, 83, 92, 100]
WIDTHS = [(1440, 1000), (1280, 800), (1024, 768), (390, 844), (320, 800)]
DENY = re.compile(
    r"accura|reliab|confiden|best MFW|optimal|guarantee|topic model|semantic AI|"
    r"neural|award|\$[0-9]|winner|prove[sd]? authorship",
    re.I,
)
ALLOWED_NEGATIVE = (
    "not a best or optimal setting",
    "no winner-takes-all view and no confidence score",
)


def serve(directory: Path):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def settle(page, ms=650):
    page.evaluate("()=>document.fonts.ready")
    page.wait_for_timeout(ms)


def scroll_to_frac(page, frac):
    page.evaluate(
        "(f)=>window.scrollTo({top:(document.documentElement.scrollHeight-innerHeight)*f,"
        "behavior:'instant'})",
        frac,
    )


def audit(page):
    return page.evaluate(
        """()=>{
        const de=document.documentElement;
        const small=[...document.querySelectorAll('a,button,summary')].filter(e=>{
          const r=e.getBoundingClientRect();
          return r.width>0&&r.height>0&&(r.width<44||r.height<44);
        }).map(e=>(e.textContent||'').trim().slice(0,28));
        return {overflowX:de.scrollWidth>de.clientWidth,
                h1:document.querySelectorAll('h1').length,
                landmarks:{header:document.querySelectorAll('header').length,
                           main:document.querySelectorAll('main').length,
                           footer:document.querySelectorAll('footer').length},
                smallTargets:small,
                bodyChars:document.body.innerText.length,
                cta:document.querySelector('a[data-workbench]')?.getAttribute('href')};
      }"""
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iteration", type=int, required=True)
    args = ap.parse_args()
    out = REPO / "provenance" / "evidence" / "P017" / "iterations" / f"it-{args.iteration}"
    shots = out / "shots"
    shots.mkdir(parents=True, exist_ok=True)

    srv, port = serve(ROOT)
    base = f"http://127.0.0.1:{port}/index.html"
    report: dict = {
        "iteration": args.iteration,
        "base": base,
        "console": [],
        "network": {},
        "viewports": {},
        "states": {},
    }

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)

        # ---- desktop cine: perf, console, 13 positions, reverse/fast, resize, refresh
        ctx = b.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
        page = ctx.new_page()
        reqs: list = []
        page.on("response", lambda r: reqs.append((r.url, r.status)))
        page.on(
            "console",
            lambda m: (
                report["console"].append(f"{m.type}:{m.text[:140]}")
                if m.type in ("error", "warning")
                else None
            ),
        )
        page.on("pageerror", lambda e: report["console"].append(f"pageerror:{str(e)[:140]}"))
        page.goto(base, wait_until="networkidle")
        settle(page)
        perf = page.evaluate(
            """()=>new Promise(res=>{let lcp=null,cls=0;
              try{new PerformanceObserver(l=>{const e=l.getEntries();lcp=e[e.length-1].startTime;})
                .observe({type:'largest-contentful-paint',buffered:true});}catch(_){}
              try{new PerformanceObserver(l=>{for(const e of l.getEntries())
                if(!e.hadRecentInput)cls+=e.value;})
                .observe({type:'layout-shift',buffered:true});}catch(_){}
              setTimeout(()=>res({lcp_ms:lcp,cls:Math.round(cls*1000)/1000,
                dcl:performance.timing.domContentLoadedEventEnd-performance.timing.navigationStart}),700);})"""
        )
        report["perf"] = perf
        origins = sorted({u.split("/", 3)[2] for u, _ in reqs})
        report["network"] = {
            "requests": len(reqs),
            "failed": [(u, s) for u, s in reqs if s >= 400],
            "origins": origins,
            "third_party": [o for o in origins if not o.startswith("127.0.0.1")],
        }
        for frac in POSITIONS:
            scroll_to_frac(page, frac / 100)
            page.wait_for_timeout(240)
            page.screenshot(path=str(shots / f"d{frac:03d}.png"))
        # reverse determinism: return to 30% and to top
        scroll_to_frac(page, 0.30)
        page.wait_for_timeout(240)
        page.screenshot(path=str(shots / "d030-return.png"))
        scroll_to_frac(page, 0)
        page.wait_for_timeout(240)
        p_top = page.evaluate(
            "()=>getComputedStyle(document.documentElement).getPropertyValue('--p').trim()"
        )
        report["states"]["p_after_full_roundtrip"] = p_top
        # fast jump storm
        for f in (1.0, 0.1, 0.9, 0.2, 0.65, 0.0):
            scroll_to_frac(page, f)
            page.wait_for_timeout(60)
        page.wait_for_timeout(300)
        report["states"]["p_after_fast_jumps"] = page.evaluate(
            "()=>getComputedStyle(document.documentElement).getPropertyValue('--p').trim()"
        )
        # refresh mid-scroll
        scroll_to_frac(page, 0.5)
        page.wait_for_timeout(200)
        page.reload(wait_until="networkidle")
        settle(page, 500)
        report["states"]["p_after_mid_refresh"] = page.evaluate(
            "()=>getComputedStyle(document.documentElement).getPropertyValue('--p').trim()"
        )
        # resize during narrative
        scroll_to_frac(page, 0.4)
        page.set_viewport_size({"width": 1024, "height": 768})
        page.wait_for_timeout(300)
        report["states"]["overflow_after_resize"] = page.evaluate(
            "()=>document.documentElement.scrollWidth>document.documentElement.clientWidth"
        )
        # keyboard pass
        page.set_viewport_size({"width": 1440, "height": 1000})
        scroll_to_frac(page, 0)
        page.wait_for_timeout(200)
        stops = []
        for _ in range(6):
            page.keyboard.press("Tab")
            stops.append(
                page.evaluate(
                    "()=>{const e=document.activeElement;"
                    "return e?((e.className&&e.className.baseVal!==undefined"
                    "?e.className.baseVal:e.className)||e.tagName)"
                    "+'|'+(e.textContent||'').trim().slice(0,22):null}"
                )
            )
        report["states"]["tab_stops"] = stops
        # denylist over rendered text
        body = page.evaluate("()=>document.body.innerText")
        hits = [m.group(0) for m in DENY.finditer(body)]
        hits = [
            h
            for h in hits
            if not any(a in body and h.lower() in a.lower() for a in ALLOWED_NEGATIVE)
        ]
        report["states"]["denylist_hits"] = hits
        ctx.close()

        # ---- per-viewport audits (top + one mid state)
        for w, h in WIDTHS:
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2)
            page = ctx.new_page()
            page.goto(base, wait_until="networkidle")
            settle(page)
            a_top = audit(page)
            scroll_to_frac(page, 0.5)
            page.wait_for_timeout(240)
            a_mid = audit(page)
            report["viewports"][f"{w}x{h}"] = {"top": a_top, "mid": a_mid}
            if w in (390, 320):
                scroll_to_frac(page, 0)
                page.wait_for_timeout(240)
                page.screenshot(path=str(shots / f"m{w}-hero.png"))
                for frac, name in ((0.22, "act2"), (0.42, "act3"), (0.62, "act4"), (0.86, "act6")):
                    scroll_to_frac(page, frac)
                    page.wait_for_timeout(240)
                    page.screenshot(path=str(shots / f"m{w}-{name}.png"))
            ctx.close()

        # ---- reduced motion (stacked mode on desktop)
        ctx = b.new_context(
            viewport={"width": 1440, "height": 1000}, reduced_motion="reduce", device_scale_factor=2
        )
        page = ctx.new_page()
        page.goto(base, wait_until="networkidle")
        settle(page)
        report["states"]["rm_chars"] = page.evaluate("()=>document.body.innerText.length")
        page.screenshot(path=str(shots / "rm-top.png"))
        scroll_to_frac(page, 0.35)
        page.wait_for_timeout(240)
        page.screenshot(path=str(shots / "rm-mid.png"))
        ctx.close()

        # ---- no JS
        ctx = b.new_context(
            viewport={"width": 1440, "height": 1000},
            java_script_enabled=False,
            device_scale_factor=2,
        )
        page = ctx.new_page()
        page.goto(base, wait_until="load")
        page.wait_for_timeout(500)
        report["states"]["nojs"] = page.evaluate(
            """()=>({chars:document.body.innerText.length,
                    cta:document.querySelector('a[data-workbench]').getAttribute('href')})"""
        )
        page.screenshot(path=str(shots / "nojs-top.png"))
        ctx.close()

        # ---- scroll walkthrough video (cine)
        vdir = out / "video"
        vdir.mkdir(exist_ok=True)
        ctx = b.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(vdir),
            record_video_size={"width": 1440, "height": 900},
        )
        page = ctx.new_page()
        page.goto(base, wait_until="networkidle")
        settle(page)
        steps = 96
        for i in range(steps + 1):
            scroll_to_frac(page, i / steps)
            page.wait_for_timeout(50)
        page.wait_for_timeout(400)
        ctx.close()

        # ---- contact sheets
        def sheet(name, files, cols, width):
            figs = "".join(
                f'<figure><img src="shots/{f}"><figcaption>{f}</figcaption></figure>' for f in files
            )
            html = (
                "<!DOCTYPE html><meta charset='utf-8'><style>"
                "body{margin:0;background:#111;padding:24px;font-family:sans-serif}"
                f".g{{display:grid;grid-template-columns:repeat({cols},1fr);gap:14px}}"
                "img{width:100%;display:block;border:1px solid #333}"
                "figure{margin:0}figcaption{color:#999;font-size:11px;margin-top:4px}"
                f"</style><div class='g'>{figs}</div>"
            )
            f = out / f"_{name}.html"
            f.write_text(html)
            c = b.new_context(viewport={"width": width, "height": 900}, device_scale_factor=1)
            pg = c.new_page()
            pg.goto(f.as_uri(), wait_until="networkidle")
            pg.wait_for_timeout(600)
            pg.screenshot(path=str(out / f"contact-{name}.png"), full_page=True)
            c.close()

        sheet("desktop", [f"d{f:03d}.png" for f in POSITIONS], 3, 1700)
        sheet(
            "mobile",
            [
                "m390-hero.png",
                "m390-act2.png",
                "m390-act3.png",
                "m390-act4.png",
                "m390-act6.png",
                "m320-hero.png",
                "m320-act3.png",
                "m320-act6.png",
            ],
            4,
            1500,
        )
        b.close()

    srv.shutdown()
    (out / "report.json").write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "perf": report["perf"],
                "network": report["network"],
                "states": report["states"],
                "viewport_overflow": {
                    k: (v["top"]["overflowX"] or v["mid"]["overflowX"])
                    for k, v in report["viewports"].items()
                },
                "small_targets": {
                    k: v["top"]["smallTargets"] + v["mid"]["smallTargets"]
                    for k, v in report["viewports"].items()
                },
                "console": report["console"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
