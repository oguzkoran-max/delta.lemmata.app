#!/usr/bin/env python3
"""Audit the running P014 gateway, Streamlit WebSocket, and alpha status."""

from __future__ import annotations

import argparse
import json
import select
import socket
import socketserver
import ssl
import threading
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from types import TracebackType
from typing import Self
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

VIEWPORTS = (
    ("desktop", 1280, 900),
    ("mobile", 390, 844),
    ("reflow", 320, 720),
)
PUBLIC_HOST = "delta.lemmata.app"
PUBLIC_PORT = 9443
UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 8502


def _validate_browser_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != PUBLIC_HOST or parsed.port != PUBLIC_PORT:
        raise ValueError("P014_BROWSER_URL_INVALID")


class _TLSProxyServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, tls: ssl.SSLContext) -> None:
        self.tls = tls
        self._metrics = Counter[str]({"tls_connections": 0, "upstream_connections": 0})
        self._metrics_lock = threading.Lock()
        super().__init__((UPSTREAM_HOST, PUBLIC_PORT), _TLSProxyHandler)

    def get_request(self) -> tuple[ssl.SSLSocket, tuple[str, int]]:
        request, address = super().get_request()
        try:
            wrapped = self.tls.wrap_socket(
                request,
                server_side=True,
                do_handshake_on_connect=False,
            )
        except OSError:
            request.close()
            raise
        return wrapped, address

    def count(self, key: str) -> None:
        with self._metrics_lock:
            self._metrics[key] += 1

    def metrics(self) -> dict[str, int]:
        with self._metrics_lock:
            return dict(sorted(self._metrics.items()))


class _TLSProxyHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        server = self.server
        assert isinstance(server, _TLSProxyServer)
        assert isinstance(self.request, ssl.SSLSocket)
        try:
            self.request.settimeout(10)
            self.request.do_handshake()
            self.request.settimeout(None)
            server.count("tls_connections")
            with socket.create_connection((UPSTREAM_HOST, UPSTREAM_PORT), timeout=5) as upstream:
                server.count("upstream_connections")
                peers = {self.request: upstream, upstream: self.request}
                while True:
                    pending = [
                        source
                        for source in peers
                        if isinstance(source, ssl.SSLSocket) and source.pending() > 0
                    ]
                    readable = pending
                    if not readable:
                        readable, _, _ = select.select(tuple(peers), (), (), 30)
                    if not readable:
                        continue
                    for source in readable:
                        payload = source.recv(65536)
                        if not payload:
                            return
                        peers[source].sendall(payload)
        except OSError:
            return


class _TLSForwarder:
    def __init__(self, certificate: Path, private_key: Path) -> None:
        if not certificate.is_file() or not private_key.is_file():
            raise ValueError("P014_BROWSER_TLS_FILE_INVALID")
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(certificate, private_key)
        self._server = _TLSProxyServer(tls)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def metrics(self) -> dict[str, int]:
        return self._server.metrics()


def _geometry(page) -> dict[str, int]:
    measured = page.evaluate(
        """() => {
          const release = document.querySelector('.delta-release-status');
          const bounds = release.getBoundingClientRect();
          return {
            clientWidth: document.documentElement.clientWidth,
            scrollWidth: document.documentElement.scrollWidth,
            releaseRight: Math.ceil(bounds.right),
            releaseLeft: Math.floor(bounds.left)
          };
        }"""
    )
    return {key: int(value) for key, value in measured.items()}


def audit(url: str, certificate: Path, private_key: Path) -> dict[str, object]:
    _validate_browser_url(url)

    requests: set[str] = set()
    blocked_requests = 0
    websockets: list[str] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[str] = []
    response_statuses: Counter[int] = Counter()
    viewport_records: list[dict[str, object]] = []
    entry_status: int | None = None
    entry_rendered = False
    ready_state = "unavailable"
    body_text_length = 0
    with _TLSForwarder(certificate, private_key) as forwarder, sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[f"--host-resolver-rules=MAP {PUBLIC_HOST} {UPSTREAM_HOST}"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )
        page = context.new_page()

        def guard_request(route) -> None:
            nonlocal blocked_requests
            if urlparse(route.request.url).hostname != PUBLIC_HOST:
                blocked_requests += 1
                route.abort("blockedbyclient")
                return
            route.continue_()

        context.route("**/*", guard_request)
        page.on(
            "request",
            lambda request: requests.add(urlparse(request.url).hostname or "unknown"),
        )
        page.on("websocket", lambda socket: websockets.append(socket.url))
        page.on(
            "console",
            lambda message: (
                console_errors.append(message.text) if message.type == "error" else None
            ),
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: request_failures.append(request.failure or "unknown"),
        )
        page.on("response", lambda response: response_statuses.update([response.status]))
        response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        entry_status = response.status if response is not None else None
        if entry_status == 200:
            try:
                page.get_by_text("Discover patterns in writing style.", exact=True).wait_for(
                    timeout=60_000
                )
                page.get_by_text("Public alpha", exact=True).wait_for(timeout=10_000)
                page.get_by_text("Experimental", exact=True).wait_for(timeout=10_000)
                page.get_by_role("region", name="Corpus texts (.txt)").wait_for(timeout=10_000)
                entry_rendered = True
            except PlaywrightTimeoutError:
                entry_rendered = False
        ready_state = str(page.evaluate("document.readyState"))
        body_text_length = int(page.locator("body").evaluate("element => element.innerText.length"))

        if entry_rendered:
            page.wait_for_timeout(500)
            for name, width, height in VIEWPORTS:
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(250)
                alpha_visible = page.get_by_text("Public alpha", exact=True).is_visible()
                experimental_visible = page.get_by_text("Experimental", exact=True).is_visible()
                geometry = _geometry(page)
                viewport_records.append(
                    {
                        "name": name,
                        "width": width,
                        "height": height,
                        "alpha_visible": alpha_visible,
                        "experimental_visible": experimental_visible,
                        "horizontal_overflow": geometry["scrollWidth"] > geometry["clientWidth"],
                        "release_inside_viewport": (
                            geometry["releaseLeft"] >= 0 and geometry["releaseRight"] <= width
                        ),
                    }
                )
        context.close()
        browser.close()
        proxy_metrics = forwarder.metrics()

    websocket_pass = any("/_stcore/stream" in value for value in websockets)
    viewport_pass = len(viewport_records) == len(VIEWPORTS) and all(
        item["alpha_visible"]
        and item["experimental_visible"]
        and not item["horizontal_overflow"]
        and item["release_inside_viewport"]
        for item in viewport_records
    )
    hosts = sorted(requests)
    websocket_hosts = sorted({urlparse(value).hostname or "unknown" for value in websockets})
    strict_host_pass = (
        hosts == [PUBLIC_HOST] and websocket_hosts == [PUBLIC_HOST] and blocked_requests == 0
    )
    return {
        "schema_version": "p014-gateway-browser-audit-v1",
        "url": url,
        "entry_status": entry_status,
        "entry_rendered": entry_rendered,
        "document_ready_state": ready_state,
        "body_text_length": body_text_length,
        "strict_expected_host_only": strict_host_pass,
        "observed_hosts": hosts,
        "websocket_hosts": websocket_hosts,
        "blocked_request_count": blocked_requests,
        "websocket_pass": websocket_pass,
        "websocket_count": len(websockets),
        "console_error_count": len(console_errors),
        "page_error_count": len(page_errors),
        "request_failure_count": len(request_failures),
        "response_status_counts": {
            str(status): count for status, count in sorted(response_statuses.items())
        },
        "proxy_metrics": proxy_metrics,
        "viewports": viewport_records,
        "result": (
            "passed"
            if entry_status == 200
            and entry_rendered
            and strict_host_pass
            and websocket_pass
            and not console_errors
            and not page_errors
            and viewport_pass
            else "failed"
        ),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=f"https://{PUBLIC_HOST}:{PUBLIC_PORT}")
    parser.add_argument("--tls-cert", required=True, type=Path)
    parser.add_argument("--tls-key", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_args(argv)
    record = audit(arguments.url, arguments.tls_cert, arguments.tls_key)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(record, sort_keys=True))
    return 0 if record["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
