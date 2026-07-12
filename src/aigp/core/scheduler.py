"""Fixed-rate loop with absolute deadlines.

The template paced its loop with time.sleep(1/HZ) inside the tick, which
accumulates drift (tick work time adds to the period) and jitters. RateLoop
keeps an absolute next-deadline on time.monotonic_ns():

    loop = RateLoop(250)
    while running:
        dt = loop.wait_next_tick()   # sleeps until the deadline, returns dt
        ...tick work...

Overruns (tick work exceeding the period) are counted, and if the loop falls
behind by more than `resync_periods` it resynchronizes rather than trying to
catch up with a burst of back-to-back ticks.
"""
from __future__ import annotations

import time


class RateLoop:
    def __init__(self, hz: float, resync_periods: int = 5, spin_ns: int = 200_000) -> None:
        self.period_ns = int(1e9 / hz)
        self.resync_periods = resync_periods
        self.spin_ns = spin_ns
        self.ticks = 0
        self.overruns = 0
        self.max_late_ns = 0
        self._deadline = time.monotonic_ns() + self.period_ns
        self._last_tick_ns = time.monotonic_ns()

    def wait_next_tick(self) -> float:
        """Block until the next deadline. Returns dt (seconds) since last tick."""
        now = time.monotonic_ns()
        remaining = self._deadline - now
        if remaining > 0:
            # Coarse sleep, then a short spin for the final stretch.
            if remaining > self.spin_ns:
                time.sleep((remaining - self.spin_ns) / 1e9)
            while time.monotonic_ns() < self._deadline:
                pass
        else:
            late = -remaining
            self.overruns += 1
            if late > self.max_late_ns:
                self.max_late_ns = late
            if late > self.resync_periods * self.period_ns:
                self._deadline = time.monotonic_ns()

        self._deadline += self.period_ns
        now = time.monotonic_ns()
        dt = (now - self._last_tick_ns) / 1e9
        self._last_tick_ns = now
        self.ticks += 1
        return dt

    @property
    def overrun_frac(self) -> float:
        return self.overruns / self.ticks if self.ticks else 0.0

    def stats(self) -> dict:
        return {
            "ticks": self.ticks,
            "overruns": self.overruns,
            "overrun_frac": self.overrun_frac,
            "max_late_us": self.max_late_ns // 1000,
        }
