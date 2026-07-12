from aigp.core.clock import SimClock


def test_offset_estimation():
    clock = SimClock()
    assert not clock.synced
    # Server clock runs 1000ns ahead; symmetric 200ns RTT.
    for i in range(10):
        req = 1_000_000 + i * 1000
        recv = req + 200
        server = req + 100 + 1000     # at midpoint, server time = mid + offset
        clock.on_timesync(server, req, recv)
    assert clock.synced
    assert clock.offset_ns == 1000


def test_median_rejects_outliers():
    clock = SimClock()
    for i in range(9):
        clock.on_timesync(1_000_000 + 500, 1_000_000, 1_000_000 + 1000)
    # One delayed, asymmetric response.
    clock.on_timesync(2_000_000 + 999_500, 2_000_000, 2_000_000 + 1_000_000)
    assert clock.offset_ns == 0  # median holds


def test_negative_rtt_ignored():
    clock = SimClock()
    clock.on_timesync(100, 200, 100)   # recv before send: bogus
    assert not clock.synced
