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

import sys
import time

# Windows sleeps at the system timer granularity — 15.6ms by default —
# which wrecks a 4ms control loop AND the mock sim's IMU pacing (Codex's
# Windows CI: overrun_frac 0.74, chronic stale-imu aborts in campaigns).
# timeBeginPeriod(1) alone measured NO effect on Windows 11 (identical
# overrun_frac to 4 decimals): modern Windows ignores it for background
# processes via timer coalescing. Defense in depth: also opt the process
# out of power throttling, and let RateLoop spin instead of sleeping for
# short waits (see _SPIN_NS below).
_SPIN_NS = 200_000
if sys.platform == "win32":                                # pragma: no cover
    _SPIN_NS = 2_500_000        # never trust sub-16ms sleeps on Windows
    try:
        import ctypes
        from ctypes import wintypes

        ctypes.WinDLL("winmm").timeBeginPeriod(1)

        class _PowerThrottling(ctypes.Structure):
            _fields_ = [("Version", wintypes.ULONG),
                        ("ControlMask", wintypes.ULONG),
                        ("StateMask", wintypes.ULONG)]

        # PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION = 0x4;
        # StateMask 0 -> do NOT throttle (honor the requested resolution).
        _state = _PowerThrottling(1, 0x4, 0)
        _k32 = ctypes.WinDLL("kernel32")
        _k32.SetProcessInformation(
            _k32.GetCurrentProcess(), 4,        # ProcessPowerThrottling
            ctypes.byref(_state), ctypes.sizeof(_state))
    except Exception:
        pass


class RateLoop:
    def __init__(self, hz: float, resync_periods: int = 5,
                 spin_ns: int = _SPIN_NS) -> None:
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
            # Coarse sleep, then a short spin for the final stretch. On
            # Windows ANY positive sleep can cost a full 15.6ms timer tick
            # (Codex v4: overrun_frac byte-identical after every resolution
            # request) — so only sleep when the wait comfortably exceeds
            # one tick, otherwise spin the whole remainder.
            sleep_ns = remaining - self.spin_ns
            if sleep_ns > (16_000_000 if sys.platform == "win32" else 0):
                time.sleep(sleep_ns / 1e9)
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
