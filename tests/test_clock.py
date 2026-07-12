from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from delta_lemmata.clock import Clock, FakeClock, SystemClock, require_utc


def test_require_utc_accepts_zero_offset_and_rejects_naive_or_non_utc() -> None:
    zero_offset = datetime(2026, 7, 12, 20, tzinfo=timezone(timedelta(0)))
    assert require_utc(zero_offset) is zero_offset
    with pytest.raises(ValueError, match="timestamp must be an aware UTC datetime"):
        require_utc(datetime(2026, 7, 12, 20))
    with pytest.raises(ValueError, match="observed must be an aware UTC datetime"):
        require_utc(
            datetime(2026, 7, 12, 23, tzinfo=timezone(timedelta(hours=3))),
            field_name="observed",
        )


def test_system_clock_satisfies_clock_protocol() -> None:
    clock: Clock = SystemClock()
    observed = clock.now()
    assert observed.tzinfo is UTC
    assert observed.utcoffset() == timedelta(0)


def test_fake_clock_advances_and_sets_forward_only() -> None:
    start = datetime(2026, 7, 12, 20, tzinfo=UTC)
    clock = FakeClock(start)
    assert clock.now() == start
    assert clock.advance(timedelta(seconds=15)) == start + timedelta(seconds=15)
    later = start + timedelta(minutes=1)
    clock.set(later)
    assert clock.now() == later

    with pytest.raises(ValueError, match="advance must be positive"):
        clock.advance(timedelta(0))
    with pytest.raises(ValueError, match="advance must be positive"):
        clock.advance(timedelta(seconds=-1))
    with pytest.raises(ValueError, match="cannot move backwards"):
        clock.set(start)
    with pytest.raises(ValueError, match="current must be an aware UTC datetime"):
        clock.set(datetime(2026, 7, 12, 21))
    with pytest.raises(ValueError, match="current must be an aware UTC datetime"):
        FakeClock(datetime(2026, 7, 12, 21))
