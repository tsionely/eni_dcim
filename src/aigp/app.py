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

import numpy as np

from aigp.core.bus import Bus
from aigp.core.clock import SimClock
from aigp.core.messages import LoopStats, Topic
from aigp.core.params import ParamSet
from aigp.core.scheduler import RateLoop
from aigp.io.mavlink_io import MavlinkIO
from aigp.io.timesync import TimeSyncTX
from aigp.io.udp_tap import STREAM_VISION, DatagramRecorder
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
    mavlink_mode: str = "listen"        # "listen" | "connect" (see MavlinkIO)
    heartbeat_timeout_s: float = 30.0
    vision_ip: str = "0.0.0.0"
    vision_port: int = 5600
    vision_mode: str = "listen"         # "listen" | "subscribe" (see VisionRX)
    vision_remote_ip: str = "127.0.0.1"
    vision_remote_port: int = 5601
    control_hz: int = 250
    planner_div: int = 5
    timesync_hz: float = 10.0
    log_dir: str = "logs"
    save_frames_every_n: int = 0
    record_vision: bool = True

    @classmethod
    def load(cls, path: str | Path) -> "SimConfig":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return cls(
            mavlink_ip=raw["mavlink"]["listen_ip"],
            mavlink_port=raw["mavlink"]["listen_port"],
            mavlink_mode=raw["mavlink"].get("mode", "listen"),
            heartbeat_timeout_s=raw["mavlink"].get("heartbeat_timeout_s", 30.0),
            vision_ip=raw["vision"]["listen_ip"],
            vision_port=raw["vision"]["listen_port"],
            vision_mode=raw["vision"].get("mode", "listen"),
            vision_remote_ip=raw["vision"].get("remote_ip", "127.0.0.1"),
            vision_remote_port=raw["vision"].get("remote_port", 5601),
            control_hz=raw["rates"].get("control_hz", 250),
            planner_div=raw["rates"].get("planner_div", 5),
            timesync_hz=raw["rates"].get("timesync_hz", 10.0),
            log_dir=raw["logging"].get("dir", "logs"),
            save_frames_every_n=raw["logging"].get("save_frames_every_n", 0),
            record_vision=raw["logging"].get("record_vision", True),
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
        self.mavlink = MavlinkIO(self.bus, self.clock, cfg.mavlink_ip, cfg.mavlink_port,
                                 mode=cfg.mavlink_mode)
        self.vision = VisionRX(self.bus, cfg.vision_ip, cfg.vision_port,
                               mode=cfg.vision_mode,
                               remote=(cfg.vision_remote_ip, cfg.vision_remote_port))
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

        # Raw vision recording per flight -> replayable regression fixture.
        recorder = None
        if self.cfg.record_vision:
            recorder = DatagramRecorder(flight_dir / "vision.aigprec")
            self.vision.raw_sink = recorder.sink_for(STREAM_VISION)

        detector = HsvGateDetector(params)
        perception = PerceptionAgent(self.bus, detector)
        estimator = StateEstimator(params)
        planner = RacePlanner(params)
        backend = BACKENDS[params.get("control.backend")](self.mavlink, params)
        supervisor = RaceManager(self.mavlink, self.bus, params, self.clock)

        # Pre-flight gyro-bias calibration: the drone sits on the start point
        # before arming, so a short stationary window measures the bias.
        self._calibrate_gyro_bias(estimator, params)

        perception.start()
        try:
            result = self._hot_loop(supervisor, estimator, planner, backend,
                                    max_duration_s)
        finally:
            perception.stop()
            self.bus.set_tap(None)
            logger.stop(timeout=5.0)
            if recorder is not None:
                self.vision.raw_sink = None
                recorder.close()

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

    def _calibrate_gyro_bias(self, estimator: StateEstimator, params: ParamSet) -> None:
        calib_s = float(params.get("estimation.gyro_bias_calib_s", default=0.0))
        if calib_s <= 0:
            return
        imu_cell = self.bus.cell(Topic.IMU)
        last_seq = 0
        gyros = []
        accels = []
        t_end = time.monotonic() + calib_s
        while time.monotonic() < t_end:
            fresh = imu_cell.get_if_newer(last_seq)
            if fresh is not None:
                imu, last_seq = fresh
                gyros.append(imu.gyro)
                accels.append(imu.accel)
            time.sleep(0.002)
        if len(gyros) >= 10:
            bias = np.mean(gyros, axis=0)
            estimator.set_gyro_bias(bias)
            ax, ay, az = np.mean(accels, axis=0)
            level_roll = float(np.arctan2(-ay, -az))
            level_pitch = float(np.arctan2(ax, np.sqrt(ay * ay + az * az)))
            estimator.set_level_reference(level_roll, level_pitch)
            print(f"gyro bias calibrated over {len(gyros)} samples: {bias}; "
                  f"level ref roll={level_roll:+.3f} pitch={level_pitch:+.3f}", flush=True)
        else:
            print("gyro bias calibration skipped: too few IMU samples", flush=True)

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
        # In-countdown calibration: pre-arm telemetry is a frozen idle
        # placeholder (phase2g), so bias + level reference are measured from
        # LIVE data while holding still in THROTTLE_DOWN, applied at TAKEOFF.
        from collections import deque
        calib_gyros: deque = deque(maxlen=180)   # last ~1.5s before GO only —
        calib_accels: deque = deque(maxlen=180)  # the long GO wait mixes stale
        # pre-race values into a full-window average (phase2h: +0.14 instead
        # of the true -0.31).
        prev_fsm_state = supervisor.state

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
                if supervisor.state == "THROTTLE_DOWN":
                    calib_gyros.append(imu.gyro)
                    calib_accels.append(imu.accel)
            if prev_fsm_state == "THROTTLE_DOWN" and supervisor.state == "TAKEOFF" \
                    and len(calib_gyros) >= 20:
                bias = np.mean(calib_gyros, axis=0)
                estimator.set_gyro_bias(bias)
                ax, ay, az = np.mean(calib_accels, axis=0)
                lr = float(np.arctan2(-ay, -az))
                lp = float(np.arctan2(ax, np.sqrt(ay * ay + az * az)))
                estimator.set_level_reference(lr, lp)
                estimator.attitude.set_attitude_euler(lr, lp)
                print(f"live calibration ({len(calib_gyros)} samples): "
                      f"bias={bias} level roll={lr:+.3f} pitch={lp:+.3f}", flush=True)
            prev_fsm_state = supervisor.state

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
