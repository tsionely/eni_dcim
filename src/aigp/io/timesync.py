"""Periodic TIMESYNC requests (10Hz, matching the template's cadence) plus a
1Hz client heartbeat so connect-mode sims keep streaming to our address.

TIMESYNC responses are handled by MavlinkIO's RX loop, which feeds SimClock.
"""
from __future__ import annotations

import time

from aigp.core.agent import Agent


class TimeSyncTX(Agent):
    name = "timesync_tx"

    def __init__(self, mavlink_io, hz: float = 10.0) -> None:
        super().__init__()
        self.mavlink_io = mavlink_io
        self.period = 1.0 / hz

    def _run(self) -> None:
        last_heartbeat = 0.0
        while self.should_run():
            self.mavlink_io.send_timesync_request()
            now = time.monotonic()
            if now - last_heartbeat >= 1.0:
                self.mavlink_io.send_client_heartbeat()
                last_heartbeat = now
            time.sleep(self.period)
