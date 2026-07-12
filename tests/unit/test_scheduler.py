import time

from aigp.core.scheduler import RateLoop


def test_rate_loop_holds_rate():
    loop = RateLoop(200)
    t0 = time.monotonic()
    for _ in range(50):
        loop.wait_next_tick()
    elapsed = time.monotonic() - t0
    # 50 ticks at 200Hz = 0.25s. Generous CI tolerance.
    assert 0.2 < elapsed < 0.6
    assert loop.ticks == 50


def test_rate_loop_counts_overruns():
    loop = RateLoop(1000)
    loop.wait_next_tick()
    time.sleep(0.05)   # blow through ~50 deadlines
    loop.wait_next_tick()
    assert loop.overruns >= 1
    assert loop.max_late_ns > 0
    assert 0 < loop.overrun_frac <= 1
