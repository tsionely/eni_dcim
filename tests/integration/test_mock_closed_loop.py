"""Closed-loop integration tests: the full pilot stack against the mock sim.

These exercise connection, arming, the FSM, the 250Hz loop, watchdogs,
telemetry logging — and (in the gate test) the entire
perception -> estimation -> planning -> control chain.

Non-default ports are used so tests don't collide with anything else on the
machine.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from aigp.app import App, SimConfig
from aigp.core.params import ParamSet
from simtools.mock_sim import Gate, MockSim

MAV_PORT = 24550
VIDEO_PORT = 25600


def make_cfg(tmp_path: Path) -> SimConfig:
    return SimConfig(
        mavlink_ip="127.0.0.1", mavlink_port=MAV_PORT,
        heartbeat_timeout_s=10.0,
        vision_ip="127.0.0.1", vision_port=VIDEO_PORT,
        control_hz=250, planner_div=5, timesync_hz=10.0,
        log_dir=str(tmp_path / "logs"),
    )


def base_params() -> ParamSet:
    return ParamSet.load("config/params_default.json")


@pytest.fixture
def sim_and_app(tmp_path):
    """Yields a factory: call with gates to get (sim, app)."""
    created = []

    def factory(gates: list[Gate]):
        sim = MockSim(mav_addr=("127.0.0.1", MAV_PORT),
                      video_addr=("127.0.0.1", VIDEO_PORT),
                      gates=gates)
        sim.start()
        app = App(make_cfg(tmp_path))
        app.connect()
        created.append((sim, app))
        return sim, app

    yield factory
    for sim, app in created:
        app.close()
        sim.stop()


def test_hover_flight_clean(sim_and_app, tmp_path):
    """Phase-0 acceptance: connect -> arm -> takeoff -> hover -> reset,
    no watchdog trips, no crashes, telemetry written."""
    # Far-away gate the drone won't reach while hovering/searching.
    sim, app = sim_and_app([Gate(pos=np.array([50.0, 0.0, -1.5]), travel_yaw=0.0)])

    params = base_params().patch({
        "planner.search.yaw_rate_rps": 0.4,
        # Keep the searcher from approaching: kill detections via threshold.
        "perception.detector.threshold": 256,
    })
    result = app.fly(params, max_duration_s=6.0)

    assert result["aborted"]
    assert result["abort_reason"] == "max duration"      # NOT a watchdog/collision
    assert result["gates_passed"] == 0
    assert result["env_hits"] == 0
    assert result["gate_clips"] == 0
    assert result["loop_stats"]["ticks"] > 500
    assert result["loop_stats"]["overrun_frac"] < 0.5    # generous for CI

    # Telemetry artifacts exist and are well-formed.
    flight_dir = Path(result["log_dir"])
    assert (flight_dir / "params.json").exists()
    assert (flight_dir / "result.json").exists()
    log = flight_dir / "flight.jsonl"
    assert log.exists()
    topics = set()
    with open(log) as f:
        for line in f:
            topics.add(json.loads(line)["topic"])
    assert {"imu", "heartbeat", "race", "fsm", "setpoint", "state"} <= topics

    # Clock synced against the mock's TIMESYNC echo.
    assert app.clock.synced

    # Sim reset works and disarms.
    app.mavlink.sim_reset()
    import time
    time.sleep(0.5)
    assert not sim.drone.armed
    assert sim.active_gate == 0


def test_single_gate_pass(sim_and_app):
    """Full chain: detect the gate, approach, commit, pass -> race finished."""
    gate = Gate(pos=np.array([7.0, 0.0, -1.5]), travel_yaw=0.0,
                width=1.6, height=1.6)
    sim, app = sim_and_app([gate])

    params = base_params().patch({
        "planner.takeoff.duration_s": 1.6,     # climb to ~gate height
        "planner.approach.speed_far_mps": 2.0,
        "safety.flight_timeout_s": 30.0,
    })
    result = app.fly(params, max_duration_s=30.0)

    assert result["gates_passed"] >= 1, f"never passed the gate: {result}"
    assert result["finished"], f"race did not finish: {result}"
    assert result["env_hits"] == 0


def test_campaign_loop_against_mock(sim_and_app, tmp_path):
    """The flight-to-flight tuning loop end to end: 3 flights, sim reset
    between, results recorded and scored."""
    from aigp.learning.campaign import Campaign
    from aigp.learning.optimizers import RandomSearch
    from aigp.learning.results_db import ResultsDB

    gate = Gate(pos=np.array([7.0, 0.0, -1.5]), travel_yaw=0.0,
                width=1.6, height=1.6)
    sim, app = sim_and_app([gate])

    params = base_params().patch({"planner.takeoff.duration_s": 1.6})
    db = ResultsDB(tmp_path / "results.sqlite")
    optimizer = RandomSearch({
        "planner.approach.speed_far_mps": (1.5, 3.0),
        "planner.commit.distance_m": (1.5, 3.0),
    }, seed=42)
    campaign = Campaign("test-camp", params, optimizer, db,
                        fly_fn=lambda p: app.reset_and_fly(
                            p, settle_s=0.5, max_duration_s=20.0),
                        log_fn=lambda s: None)
    campaign.run(3)

    flights = db.flights("test-camp")
    assert len(flights) == 3
    assert all(f["param_hash"] for f in flights)
    assert len({f["param_hash"] for f in flights}) == 3   # different params flew
    assert db.best_flight("test-camp") is not None
    assert len(optimizer.history) == 3
    db.close()
