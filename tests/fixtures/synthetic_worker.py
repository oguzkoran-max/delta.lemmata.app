"""Deterministic worker behaviors used only by P005 process-control tests."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

MEMORY_LIMIT_EXIT = 73
PROCESS_LIMIT_EXIT = 74
PAYLOAD_CANARY = "SYNTHETIC_PAYLOAD_MUST_NOT_ESCAPE"


def _spawn(mode: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        (sys.executable, str(Path(__file__).resolve()), mode),
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        cwd=Path.cwd(),
        env=dict(os.environ),
        start_new_session=False,
    )


def _hold(*, ignore_term: bool) -> int:
    if ignore_term:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        time.sleep(60)


def _contract(expected_cwd: str) -> int:
    valid = (
        Path.cwd() == Path(expected_cwd)
        and sys.stdin.buffer.read(1) == b""
        and os.getpid() == os.getpgrp() == os.getsid(0)
        and "DELTA_SECRET_CANARY" not in os.environ
        and os.environ
        == {
            "LANG": "C",
            "LC_ALL": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "TZ": "UTC",
        }
    )
    print(PAYLOAD_CANARY, flush=True)
    print(PAYLOAD_CANARY, file=sys.stderr, flush=True)
    return 0 if valid else 2


def _memory_limit() -> int:
    allocations: list[bytearray] = []
    try:
        while True:
            allocations.append(bytearray(8 * 1024 * 1024))
    except MemoryError:
        return MEMORY_LIMIT_EXIT


def _process_limit() -> int:
    children: list[subprocess.Popen[bytes]] = []
    try:
        while True:
            children.append(_spawn("ignore-term"))
            time.sleep(0.05)
    except (OSError, subprocess.SubprocessError):
        return PROCESS_LIMIT_EXIT


def _nested_child() -> int:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    _spawn("ignore-term")
    return _hold(ignore_term=True)


def main() -> int:
    if len(sys.argv) < 2:
        return 2
    mode = sys.argv[1]
    if mode == "success":
        return 0
    if mode == "contract" and len(sys.argv) == 3:
        return _contract(sys.argv[2])
    if mode == "failure":
        return 9
    if mode == "traceback":
        raise RuntimeError(PAYLOAD_CANARY)
    if mode == "crash":
        os.abort()
    if mode == "delay" and len(sys.argv) == 3:
        time.sleep(float(sys.argv[2]))
        return 0
    if mode == "cpu-limit":
        while True:
            pass
    if mode == "memory-limit":
        return _memory_limit()
    if mode == "process-limit":
        return _process_limit()
    if mode == "sleep":
        return _hold(ignore_term=False)
    if mode == "ignore-term":
        return _hold(ignore_term=True)
    if mode == "nested":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        _spawn("nested-child")
        return _hold(ignore_term=True)
    if mode == "nested-child":
        return _nested_child()
    if mode == "orphan":
        _spawn("ignore-term")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
