"""Application wiring and the 250Hz hot loop.

App owns the session-level pieces (connection, bus, clock). Each call to
fly() builds the param-dependent components fresh (planner, estimator,
backend, detector, supervisor) so a tuning campaign can change the ParamSet
between flights without reconnecting.

Hot-loop budget: 4ms per tick. The loop only does scalar math on latest-value
cells — no allocation-heavy work, no blocking calls, no I/O (logging goes
through the non-blocking bus tap).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from aigp.core.bus import Bus
from aigp.core.clock import SimClock
from aigp.core.messages import LoopStats, Topic
from aigp.core.params import ParamSet
from aigp.core.scheduler import RateLoop
from aigp.io.mavlink_io import MavlinkIO
from aigp.io.timesync import TimeSyncTX
from aigp.io.vision_rx import VisionRX
from aigp.control.attitude_rate_backend import AttitudeRateBackend
from aigp.control.velocity_backend import VelocityBackend
from aigp.estimation.state_estimator import StateEstimator
from aigp.learning import flight_log
from aigp.perception.gate_detector_hsv import HsvGateDetector
from aigp.perception.pipeline import PerceptionAgent
from aigp.planning.race_planner import RacePlanner
from aigp.supervisor.race_manager import RaceManager
from aigp.telemetry.logger import TelemetryLogger


@dataclass
class SimConfig:
    mavlink_ip: str = "127.0.0.1"
    mavlink_port: int = 14550
    heartbeat_timeout_s: float = 30.0
    vision_ip: str = "0.0.0.0"
    vision_port: int = 5600
    control_hz: int = 250
    planner_div: int = 5
    timesync_hz: float = 10.0
    log_dir: str = "logs"
    save_frames_every_n: int = 0

    @classmethod
    def load(cls, path: str | Path) -> "SimConfig":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return cls(
            mavlink_ip=raw["mavlink"]["listen_ip"],
            mavlink_port=raw["mavlink"]["listen_port"],
            heartbeat_timeout_s=raw["mavlink"].get("heartbeat_timeout_s", 30.0),
            vision_ip=raw["vision"]["listen_ip"],
            vision_port=raw["vision"]["listen_port"],
            control_hz=raw["rates"].get("control_hz", 250),
            planner_div=raw["rates"].get("planner_div", 5),
            timesync_hz=raw["rates"].get("timesync_hz", 10.0),
            log_dir=raw["logging"].get("dir", "logs"),
            save_frames_every_n=raw["logging"].get("save_frames_every_n", 0),
        )


BACKENDS = {
    "velocity": VelocityBackend,
    "att_rate": AttitudeRateBackend,
}


class App:
    def __init__(self, cfg: SimConfig) -> None:
        self.cfg = cfg
        self.bus = Bus()
        self.clock = SimClock()
        self.mavlink = MavlinkIO(self.bus, self.clock, cfg.mavlink_ip, cfg.mavlink_port)
        self.vision = VisionRX(self.bus, cfg.vision_ip, cfg.vision_port)
        self.timesync = TimeSyncTX(self.mavlink, cfg.timesync_hz)
        self._connected = False

    # ------------------------------------------------------------- lifecycle

    def connect(self) -> None:
        print("Waiting for sim heartbeat...", flush=True)
        self.mavlink.connect(timeout_s=self.cfg.heartbeat_timeout_s)
        print("Connected. Starting IO agents...", flush=True)
        self.mavlink.start()
        self.vision.start()
        self.timesync.start()
        self._connected = True

    def close(self) -> None:
        for agent in (self.timesync, self.vision, self.mavlink):
            agent.stop()
        self._connected = False

    # ----------------------------------------------------------------- flight

    def fly(self, params: ParamSet, max_duration_s: float | None = None,
            flight_id: str | None = None) -> dict:
        """Run one flight to completion. Returns the result dict."""
        if not self._connected:
            raise RuntimeError("call connect() first")

        if flight_id is None:
            flight_id = flight_log.new_flight_id(params)
        flight_dir = flight_log.prepare_flight_dir(self.cfg.log_dir, flight_id, params)

        logger = TelemetryLogger(flight_dir, self.cfg.save_frames_every_n)
        logger.start()
        self.bus.set_tap(logger.tap)

        detector = HsvGateDetector(params)
        perception = PerceptionAgent(self.bus, detector)
        estimator = StateEstimator(params)
        planner = RacePlanner(params)
        backend = BACKENDS[params.get("control.backend")](self.mavlink, params)
        supervisor = RaceManager(self.mavlink, self.bus, params, self.clock)

        perception.start()
        try:
            result = self._hot_loop(supervisor, estimator, planner, backend,
                                    max_duration_s)
        finally:
            perception.stop()
            self.bus.set_tap(None)
            logger.stop(timeout=5.0)

        result["flight_id"] = flight_id
        result["log_dir"] = str(flight_dir)
        flight_log.write_result(flight_dir, result)
        return result

    def reset_and_fly(self, params: ParamSet, settle_s: float = 1.5,
                      max_duration_s: float | None = None) -> dict:
        """Campaign entry point: reset the sim, wait for it to settle, fly."""
        self.mavlink.sim_reset()
        time.sleep(settle_s)
        return self.fly(params, max_duration_s=max_duration_s)

    # ---------------------------------------------------------------- hot loop

    def _hot_loop(self, supervisor: RaceManager, estimator: StateEstimator,
                  planner: RacePlanner, backend, max_duration_s: float | None) -> dict:
        bus = self.bus
        hb_cell = bus.cell(Topic.HEARTBEAT)
        race_cell = bus.cell(Topic.RACE)
        imu_cell = bus.cell(Topic.IMU)
        det_cell = bus.cell(Topic.DETECTION)
        frame_cell = bus.cell(Topic.FRAME)
        collision_q = bus.events(Topic.COLLISION)

        loop = RateLoop(self.cfg.control_hz)
        planner_div = self.cfg.planner_div
        imu_seq = det_seq = frame_seq = 0
        setpoint = None
        state = estimator.state
        t_start = time.monotonic()

        supervisor.start_flight()
        while not supervisor.done:
            dt = loop.wait_next_tick()
            now_ns = self.clock.sim_now_ns()

            heartbeat, _ = hb_cell.get()
            race, _ = race_cell.get()
            collisions = collision_q.drain()
            mode = supervisor.tick(heartbeat, race, collisions)

            if supervisor.gate_passed_flag:
                estimator.on_gate_passed()
                planner.on_gate_passed()
            if supervisor.collision_flag:
                planner.on_collision(now_ns)

            fresh = imu_cell.get_if_newer(imu_seq)
            if fresh is not None:
                imu, imu_seq = fresh
                estimator.predict(imu)
                supervisor.watchdog.feed("imu")

            fresh = frame_cell.get_if_newer(frame_seq)
            if fresh is not None:
                _, frame_seq = fresh
                supervisor.watchdog.feed("frame")

            fresh = det_cell.get_if_newer(det_seq)
            if fresh is not None:
                detection, det_seq = fresh
                estimator.update_vision(detection)

            if loop.ticks % planner_div == 0 or setpoint is None:
                state = estimator.state
                setpoint = planner.plan(now_ns, mode, state, race)
                bus.publish_latest(Topic.STATE, state)
                bus.publish_latest(Topic.SETPOINT, setpoint)

            if supervisor.commands_active():
                backend.update(setpoint, state, dt)

            if max_duration_s is not None and time.monotonic() - t_start > max_duration_s:
                supervisor.stop_flight("max duration")

        supervisor.set_loop_overrun_frac(loop.overrun_frac)
        stats = loop.stats()
        bus.publish_latest(Topic.LOOP_STATS, LoopStats(
            ts_ns=self.clock.sim_now_ns(), ticks=stats["ticks"],
            overruns=stats["overruns"], max_late_us=stats["max_late_us"],
        ))
        result = supervisor.result.as_dict()
        result["loop_stats"] = stats
        return result
