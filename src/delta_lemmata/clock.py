"""UTC-only clocks for deterministic job lifecycle behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


def require_utc(value: datetime, *, field_name: str = "timestamp") -> datetime:
    """Return an aware UTC datetime or reject it without implicit conversion."""

    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be an aware UTC datetime")
    return value


class Clock(Protocol):
    """Minimal clock boundary used by lifecycle and retention code."""

    def now(self) -> datetime:
        """Return the current aware UTC time."""


class SystemClock:
    """Production clock backed by the system UTC clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeClock:
    """Explicitly advanced UTC clock for deterministic tests."""

    def __init__(self, current: datetime) -> None:
        self._current = require_utc(current, field_name="current")

    def now(self) -> datetime:
        return self._current

    def set(self, current: datetime) -> None:
        candidate = require_utc(current, field_name="current")
        if candidate < self._current:
            raise ValueError("fake clock cannot move backwards")
        self._current = candidate

    def advance(self, delta: timedelta) -> datetime:
        if delta <= timedelta(0):
            raise ValueError("fake clock advance must be positive")
        self._current += delta
        return self._current


__all__ = ["Clock", "FakeClock", "SystemClock", "require_utc"]
