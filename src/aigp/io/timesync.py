"""Periodic TIMESYNC requests (10Hz, matching the template's cadence).

Responses are handled by MavlinkIO's RX loop, which feeds SimClock.
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
        while self.should_run():
            self.mavlink_io.send_timesync_request()
            time.sleep(self.period)
