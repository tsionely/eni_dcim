"""Unified sim/client timeline.

The simulator stamps IMU samples, camera frames and race status on its own
clock. The client only has time.monotonic_ns(). SimClock estimates
offset = sim_time - client_monotonic from TIMESYNC round trips (median of the
last N samples) so all inputs can be placed on one timeline.

TIMESYNC exchange (matching the official template):
  client sends  TIMESYNC(tc1=client_mono_ns, ts1=0)
  server replies TIMESYNC(tc1=server_time_ns, ts1=original client stamp)
  offset ~= tc1_server - (ts1 + rtt/2)
"""
from __future__ import annotations

import statistics
import threading
import time
from collections import deque


class SimClock:
    def __init__(self, window: int = 21) -> None:
        self._offsets: deque[int] = deque(maxlen=window)
        self._offset_ns = 0
        self._lock = threading.Lock()
        self._have_sync = False

    @staticmethod
    def mono_ns() -> int:
        return time.monotonic_ns()

    def on_timesync(self, server_ns: int, request_client_ns: int, recv_client_ns: int) -> None:
        rtt = recv_client_ns - request_client_ns
        if rtt < 0:
            return
        offset = server_ns - (request_client_ns + rtt // 2)
        with self._lock:
            self._offsets.append(offset)
            self._offset_ns = int(statistics.median(self._offsets))
            self._have_sync = True

    @property
    def synced(self) -> bool:
        return self._have_sync

    @property
    def offset_ns(self) -> int:
        with self._lock:
            return self._offset_ns

    def offset_std_ns(self) -> float:
        with self._lock:
            if len(self._offsets) < 2:
                return float("inf")
            return statistics.pstdev(self._offsets)

    def sim_now_ns(self) -> int:
        """Current time on the sim timeline (client mono if not synced yet)."""
        return time.monotonic_ns() + self.offset_ns

    def to_sim_ns(self, client_mono_ns: int) -> int:
        return client_mono_ns + self.offset_ns
