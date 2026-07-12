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

    def stale_channels(self, now: float | None = None) -> list[str]:
        if now is None:
            now = time.monotonic()
        stale = []
        for name, timeout in self._thresholds.items():
            last = self._last_feed.get(name)
            if last is not None and (now - last) > timeout:
                stale.append(name)
        return stale
