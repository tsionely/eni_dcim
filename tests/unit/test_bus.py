from aigp.core.bus import Bus, EventQueue, LatestValue


def test_latest_value_freshness():
    cell = LatestValue()
    assert cell.get() == (None, 0)
    assert cell.get_if_newer(0) is None

    cell.set("a")
    value, seq = cell.get()
    assert value == "a" and seq == 1
    assert cell.get_if_newer(0) == ("a", 1)
    assert cell.get_if_newer(1) is None

    cell.set("b")
    assert cell.get_if_newer(1) == ("b", 2)


def test_latest_value_no_backlog():
    cell = LatestValue()
    for i in range(100):
        cell.set(i)
    value, seq = cell.get()
    assert value == 99 and seq == 100


def test_event_queue_drain_and_overflow():
    q = EventQueue(maxsize=3)
    for i in range(5):
        q.put(i)
    assert q.drops == 2
    assert q.drain() == [2, 3, 4]   # oldest dropped, order preserved
    assert q.drain() == []


def test_bus_tap_sees_everything():
    bus = Bus()
    seen = []
    bus.set_tap(lambda topic, msg: seen.append((topic, msg)))
    bus.publish_latest("imu", 1)
    bus.publish_event("collision", 2)
    assert seen == [("imu", 1), ("collision", 2)]
    assert bus.cell("imu").get() == (1, 1)
    assert bus.events("collision").drain() == [2]
