import time

import pytest

from aigp.core.bus import Bus
from aigp.core.clock import SimClock
from aigp.core.messages import CollisionEvent, Heartbeat, RaceStatus
from aigp.core.params import ParamSet
from aigp.supervisor.race_manager import FlightState, RaceManager


class FakeIO:
    def __init__(self):
        self.arm_calls = 0
        self.reset_calls = 0
        self.throttle_down_sends = 0

    def arm(self):
        self.arm_calls += 1

    def sim_reset(self):
        self.reset_calls += 1

    def send_attitude_rates(self, roll_rate, pitch_rate, yaw_rate, thrust):
        assert thrust == 0.0
        self.throttle_down_sends += 1


@pytest.fixture
def params():
    return ParamSet.load("config/params_default.json").patch({
        "planner.takeoff.duration_s": 0.05,
        "control.throttle_down_s": 0.05,
        "control.go_timeout_s": 2.0,
        "safety.flight_timeout_s": 10.0,
        # These tests exercise the FSM with NO data streams; watchdogs are
        # armed at flight start now (never-fed channels must trip in real
        # flights), so keep them out of the way here.
        "safety.imu_stale_s": 30.0,
        "safety.frame_stale_s": 30.0,
    })


@pytest.fixture
def manager(params):
    return RaceManager(FakeIO(), Bus(), params, SimClock())


def hb(armed: bool) -> Heartbeat:
    return Heartbeat(ts_ns=0, armed=armed)


def race(active=0, start=-1, finish=-1, boot=10_000) -> RaceStatus:
    return RaceStatus(ts_ns=0, sim_boot_time_ms=boot, race_start_boot_time_ms=start,
                      race_finish_time_ns=finish, active_gate_index=active,
                      last_gate_race_time=-1)


def test_happy_path(manager):
    manager.start_flight()
    assert manager.state == FlightState.ARMING
    assert manager.io.arm_calls == 1

    # Race not started yet (countdown): baseline start = -1.
    manager.tick(hb(True), race(active=0, start=-1), [])
    assert manager.state == FlightState.THROTTLE_DOWN
    assert manager.io.throttle_down_sends >= 1

    # Handshake elapsed but race still counting down -> stay put (early-start
    # protection).
    time.sleep(0.06)
    manager.tick(hb(True), race(active=0, start=-1), [])
    assert manager.state == FlightState.THROTTLE_DOWN

    # Countdown: race_start changes to a FUTURE timestamp -> still hold
    # (phase2b: launching here earned an early-start DSQ).
    manager.tick(hb(True), race(active=0, start=5000, boot=3000), [])
    assert manager.state == FlightState.THROTTLE_DOWN

    # GO: the sim clock reaches the scheduled start.
    manager.tick(hb(True), race(active=0, start=5000, boot=5001), [])
    assert manager.state == FlightState.TAKEOFF
    assert manager.planner_mode() == "takeoff"

    time.sleep(0.06)
    manager.tick(hb(True), race(active=0, start=100), [])
    assert manager.state == FlightState.RACING
    assert manager.planner_mode() == "race"

    # Pass two gates.
    manager.tick(hb(True), race(active=1, start=100), [])
    assert manager.gate_passed_flag
    manager.tick(hb(True), race(active=2, start=100), [])
    assert manager.result.gates_passed == 2

    # Finish.
    manager.tick(hb(True), race(active=2, start=100, finish=9_000_000_000), [])
    assert manager.state == FlightState.FINISHED
    assert manager.result.finished

    time.sleep(1.05)
    manager.tick(hb(True), race(active=2, start=100, finish=9_000_000_000), [])
    assert manager.done


def to_flying(manager):
    manager.tick(hb(True), race(start=-1), [])         # ARMING -> THROTTLE_DOWN
    time.sleep(0.06)
    manager.tick(hb(True), race(start=1), [])          # GO -> TAKEOFF


def test_env_collision_aborts(manager):
    manager.start_flight()
    to_flying(manager)
    event = CollisionEvent(ts_ns=0, collision_id=CollisionEvent.ENVIRONMENT,
                           threat_level=2, impulse=5.0)
    manager.tick(hb(True), race(start=1), [event])
    assert manager.done
    assert manager.result.aborted
    assert "environment" in manager.result.abort_reason


def test_gate_clips_tolerated_up_to_budget(manager):
    manager.start_flight()
    to_flying(manager)
    clip = CollisionEvent(ts_ns=0, collision_id=CollisionEvent.GATE,
                          threat_level=1, impulse=0.5)
    for _ in range(10):   # max_gate_clips = 10
        manager.tick(hb(True), race(start=1), [clip])
    assert not manager.result.aborted
    manager.tick(hb(True), race(start=1), [clip])      # 11th
    assert manager.result.aborted


def test_watchdog_abort(manager):
    manager.start_flight()
    to_flying(manager)
    manager.watchdog.feed("imu", now=time.monotonic() - 31.0)   # stale
    manager.tick(hb(True), race(start=1), [])
    assert manager.result.aborted
    assert "stale" in manager.result.abort_reason


def test_arming_retries_then_times_out(manager):
    manager.start_flight()
    time.sleep(1.05)
    manager.tick(hb(False), None, [])
    assert manager.io.arm_calls == 2   # initial + one retry


def test_watchdog_gap_reported_in_stale_abort_reason():
    # T2a forensics: the abort reason must carry the measured gap.
    from aigp.supervisor.watchdog import Watchdog
    w = Watchdog()
    w.register("imu", 0.25)
    w.feed("imu", now=100.0)
    assert w.gap_s("imu", now=100.4) == pytest.approx(0.4)
    assert w.stale_channels(now=100.4) == ["imu"]
    assert w.stale_channels(now=100.2) == []
