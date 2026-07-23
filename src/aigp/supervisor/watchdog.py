"""Staleness watchdogs.

The app feeds a channel whenever fresh data arrives; check() reports channels
whose last feed is older than their threshold. Channels are only armed after
their first feed, so startup order doesn't trip them.
"""
from __future__ import annotations

import time


class Watchdog:
    def __init__(self) -> None:
        self._thresholds: dict[str, float] = {}
        self._last_feed: dict[str, float] = {}

    def register(self, name: str, timeout_s: float) -> None:
        self._thresholds[name] = timeout_s

    def feed(self, name: str, now: float | None = None) -> None:
        self._last_feed[name] = now if now is not None else time.monotonic()

    def arm_all(self, now: float | None = None) -> None:
        """Arm every registered channel as if just fed.

        A channel that NEVER feeds must still trip (phase4b: a no-race
        launch produced ZERO imu samples and the pilot 'flew' search for
        300s on nothing — the never-fed channel was never armed).
        """
        if now is None:
            now = time.monotonic()
        for name in self._thresholds:
            self._last_feed.setdefault(name, now)

    def gap_s(self, name: str, now: float | None = None) -> float | None:
        """Observed staleness gap for a channel (diagnostic; T2a forensics:
        six stale-imu aborts whose logs show a continuous stream — the
        abort message must carry the gap the watchdog actually saw)."""
        if now is None:
            now = time.monotonic()
        last = self._last_feed.get(name)
        return None if last is None else now - last

    def stale_channels(self, now: float | None = None) -> list[str]:
        if now is None:
            now = time.monotonic()
        stale = []
        for name, timeout in self._thresholds.items():
            last = self._last_feed.get(name)
            if last is not None and (now - last) > timeout:
                stale.append(name)
        return stale
