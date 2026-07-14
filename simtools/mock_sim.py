"""Mock AI-GP simulator.

A deliberately simple stand-in for FlightSim.exe so the full pilot stack can
run closed-loop in this repo and in CI:

- kinematic point-mass quad with first-order velocity-command response
  (supports SET_POSITION_TARGET_LOCAL_NED velocity commands, BODY or LOCAL
  frame; attitude-rate commands are acknowledged but not simulated yet)
- speaks the sim's MAVLink subset over local UDP: HEARTBEAT, HIGHRES_IMU
  (with noise), TIMESYNC echo, ENCAPSULATED_DATA race status, COLLISION,
  arm / disarm, sim-reset command 31000
- renders synthetic camera frames of the active gate (pinhole projection,
  JPEG, chunked with the real "<IHHIIQ" header) to the vision UDP port

What it validates: FSM, wire formats, timing, estimator plumbing, gate
geometry math, the full tuning-campaign loop. What it deliberately does NOT
validate: flight dynamics fidelity, visual realism.
"""
from __future__ import annotations

import math
import socket
import struct
import threading
import time
from dataclasses import dataclass, field

import cv2
import numpy as np
from pymavlink import mavutil

MAVLINK_CMD_SIM_RESET = 31000
VISION_HEADER = "<IHHIIQ"
VISION_CHUNK_PAYLOAD = 1400

GRAVITY = 9.80665


@dataclass
class Gate:
    pos: np.ndarray            # NED [m]
    travel_yaw: float          # direction of travel THROUGH the gate [rad]
    width: float = 1.4         # opening [m]
    height: float = 1.4
    frame_thickness: float = 0.15


def default_track() -> list[Gate]:
    return [
        Gate(pos=np.array([8.0, 0.0, -1.5]), travel_yaw=0.0),
        Gate(pos=np.array([16.0, 4.0, -1.5]), travel_yaw=math.radians(45.0)),
    ]


@dataclass
class DroneState:
    pos: np.ndarray = field(default_factory=lambda: np.zeros(3))
    vel: np.ndarray = field(default_factory=lambda: np.zeros(3))
    yaw: float = 0.0
    yaw_rate: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    rates: np.ndarray = field(default_factory=lambda: np.zeros(3))   # p, q, r
    armed: bool = False


def euler_matrix(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """Body-to-world rotation, ZYX (yaw-pitch-roll) convention, NED."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return np.array([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ])


class MockSim:
    def __init__(self, mav_addr: tuple[str, int] = ("127.0.0.1", 14550),
                 video_addr: tuple[str, int] = ("127.0.0.1", 5600),
                 gates: list[Gate] | None = None,
                 physics_hz: float = 250.0, imu_hz: float = 200.0,
                 video_hz: float = 30.0, race_status_hz: float = 10.0,
                 heartbeat_hz: float = 2.0,
                 vel_tau_s: float = 0.25, imu_noise: float = 0.05,
                 rate_tau_s: float = 0.06, hover_thrust: float = 0.5,
                 drag: float = 0.35, honor_velocity: bool = True,
                 image_size: tuple[int, int] = (640, 360), fov_deg: float = 90.0,
                 seed: int = 0) -> None:
        self.mav_addr = mav_addr
        self.video_addr = video_addr
        self.gates = gates if gates is not None else default_track()
        self.physics_hz = physics_hz
        # Video runs on its own thread — JPEG encode must never block IMU
        # pacing (it tripped the pilot's 50ms imu watchdog under load).
        self.video_period = 1.0 / video_hz
        self.periods = {
            "imu": 1.0 / imu_hz,
            "race": 1.0 / race_status_hz,
            "heartbeat": 1.0 / heartbeat_hz,
        }
        self.vel_tau_s = vel_tau_s
        self.imu_noise = imu_noise
        # Attitude-rate dynamics (the interface the REAL sim honors).
        self.rate_tau_s = rate_tau_s
        self.hover_thrust = hover_thrust
        self.drag = drag
        # The real v1.0.3385 sim ignores velocity setpoints (phase1f mode B);
        # set False to mirror that behavior in tests.
        self.honor_velocity = honor_velocity
        # Mirror the real sim's inverted rate-command convention (phase2b).
        self.rate_cmd_sign = -1.0
        self.image_w, self.image_h = image_size
        self.fx = (self.image_w / 2.0) / math.tan(math.radians(fov_deg) / 2.0)
        self.rng = np.random.default_rng(seed)

        self.drone = DroneState()
        self.ctrl_mode = "velocity"          # last-command-wins: velocity | att_rate
        self.v_cmd = np.zeros(3)
        self.v_cmd_body_frame = True
        self.yaw_rate_cmd = 0.0
        self.rate_cmd = np.zeros(3)          # p, q, r [rad/s]
        self.thrust_cmd = 0.0                # 0..1
        self.active_gate = 0
        self.race_start_ms = -1
        self.race_finish_ns = -1
        self.last_gate_race_time = -1
        self._was_airborne = False
        self._track_accel = np.zeros(3)
        self._pending_collisions: list[tuple[int, int, float]] = []

        self._thread: threading.Thread | None = None
        self._running = False
        self._boot_mono_ns = 0
        self._frame_id = 0
        self._seqnr = 0

    # ------------------------------------------------------------- lifecycle

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, name="mock_sim", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    # ------------------------------------------------------------------ time

    def _sim_now_ns(self) -> int:
        return time.monotonic_ns() - self._boot_mono_ns

    # ------------------------------------------------------------------- run

    def _run(self) -> None:
        self._boot_mono_ns = time.monotonic_ns()
        conn = mavutil.mavlink_connection(
            f"udpout:{self.mav_addr[0]}:{self.mav_addr[1]}",
            source_system=1, source_component=1,
        )
        video_thread = threading.Thread(target=self._video_loop, name="mock_video",
                                        daemon=True)
        video_thread.start()

        dt = 1.0 / self.physics_hz
        next_tick = time.monotonic()
        last_sent = {k: 0.0 for k in self.periods}
        try:
            while self._running:
                now = time.monotonic()
                if now < next_tick:
                    time.sleep(min(0.001, next_tick - now))
                    continue
                next_tick += dt

                self._receive(conn)
                self._step_physics(dt)
                self._flush_collisions(conn)

                for kind, period in self.periods.items():
                    if now - last_sent[kind] >= period:
                        last_sent[kind] = now
                        if kind == "imu":
                            self._send_imu(conn)
                        elif kind == "race":
                            self._send_race_status(conn)
                        elif kind == "heartbeat":
                            self._send_heartbeat(conn)
        finally:
            video_thread.join(timeout=1.0)
            conn.close()

    def _video_loop(self) -> None:
        video_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            while self._running:
                t0 = time.monotonic()
                self._send_frame(video_sock)
                remaining = self.video_period - (time.monotonic() - t0)
                if remaining > 0:
                    time.sleep(remaining)
        finally:
            video_sock.close()

    # ---------------------------------------------------------------- mavlink

    def _receive(self, conn) -> None:
        while True:
            try:
                msg = conn.recv_match(blocking=False)
            except (ConnectionResetError, OSError):
                return
            if msg is None:
                return
            mtype = msg.get_type()
            if mtype == "COMMAND_LONG":
                if msg.command == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
                    self._set_armed(msg.param1 > 0.5)
                elif msg.command == MAVLINK_CMD_SIM_RESET:
                    self._reset()
            elif mtype == "SET_POSITION_TARGET_LOCAL_NED":
                if self.honor_velocity:
                    self.ctrl_mode = "velocity"
                    self.v_cmd = np.array([msg.vx, msg.vy, msg.vz])
                    self.v_cmd_body_frame = msg.coordinate_frame in (
                        mavutil.mavlink.MAV_FRAME_BODY_NED,
                        mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
                    )
                    ignore_yaw_rate = msg.type_mask & mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_RATE_IGNORE
                    self.yaw_rate_cmd = 0.0 if ignore_yaw_rate else msg.yaw_rate
            elif mtype == "SET_ATTITUDE_TARGET":
                self.ctrl_mode = "att_rate"
                # The real v1.0.3385 sim applies rate commands with the sign
                # INVERTED vs the MAVLink convention (phase2b probe D, all
                # three axes); the mock mirrors that so the same config flies
                # both.
                self.rate_cmd = self.rate_cmd_sign * np.array([
                    msg.body_roll_rate, msg.body_pitch_rate, msg.body_yaw_rate])
                self.thrust_cmd = float(np.clip(msg.thrust, 0.0, 1.0))
            elif mtype == "TIMESYNC" and msg.ts1 == 0:
                # Echo protocol: reply with our time in tc1, requester stamp in ts1.
                conn.mav.timesync_send(self._sim_now_ns(), msg.tc1)

    def _send_heartbeat(self, conn) -> None:
        base_mode = mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED if self.drone.armed else 0
        conn.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_QUADROTOR,
            mavutil.mavlink.MAV_AUTOPILOT_GENERIC,
            base_mode, 0, mavutil.mavlink.MAV_STATE_ACTIVE,
        )

    def _send_imu(self, conn) -> None:
        # Specific force f = a - g rotated into the (full-attitude) body frame.
        a_world = (self._track_accel if self._track_accel is not None else np.zeros(3))
        f_world = a_world - np.array([0.0, 0.0, GRAVITY])
        rot = euler_matrix(self.drone.roll, self.drone.pitch, self.drone.yaw)
        f_body = rot.T @ f_world
        f_body += self.rng.normal(0.0, self.imu_noise, 3)
        if self.ctrl_mode == "att_rate":
            gyro = self.drone.rates.copy()
        else:
            gyro = np.array([0.0, 0.0, self.drone.yaw_rate])
        gyro += self.rng.normal(0.0, self.imu_noise * 0.2, 3)
        conn.mav.highres_imu_send(
            self._sim_now_ns() // 1000,
            f_body[0], f_body[1], f_body[2],
            gyro[0], gyro[1], gyro[2],
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0xFFFF, 0,
        )

    def _send_race_status(self, conn) -> None:
        payload = struct.pack(
            "<BQqqIq", 1,
            self._sim_now_ns() // 1_000_000,
            self.race_start_ms,
            self.race_finish_ns,
            self.active_gate,
            self.last_gate_race_time,
        )
        data = payload + bytes(253 - len(payload))
        self._seqnr = (self._seqnr + 1) % 65536
        conn.mav.encapsulated_data_send(self._seqnr, list(data))

    def _flush_collisions(self, conn) -> None:
        while self._pending_collisions:
            collision_id, threat, impulse = self._pending_collisions.pop(0)
            conn.mav.collision_send(
                0,                # src
                collision_id,     # 1001 gate / 1002 environment
                0,                # action
                threat,           # threat_level
                0.0,
                0.0,
                impulse,          # repurposed: impulse magnitude [kg m/s]
            )

    # ---------------------------------------------------------------- physics

    def _set_armed(self, armed: bool) -> None:
        self.drone.armed = armed
        if armed and self.race_start_ms < 0:
            self.race_start_ms = self._sim_now_ns() // 1_000_000

    def _reset(self) -> None:
        self.drone = DroneState()
        self.ctrl_mode = "velocity"
        self.v_cmd = np.zeros(3)
        self.yaw_rate_cmd = 0.0
        self.rate_cmd = np.zeros(3)
        self.thrust_cmd = 0.0
        self.active_gate = 0
        self.race_start_ms = -1
        self.race_finish_ns = -1
        self.last_gate_race_time = -1
        self._was_airborne = False

    def _step_physics(self, dt: float) -> None:
        drone = self.drone
        if not drone.armed:
            self._track_accel = np.zeros(3)
            return

        prev_pos = drone.pos.copy()
        prev_vel = drone.vel.copy()

        if self.ctrl_mode == "velocity":
            # Legacy kinematic mode (the real v1.0.3385 sim ignores this;
            # kept for tests with honor_velocity=True).
            v_cmd = self.v_cmd
            if self.v_cmd_body_frame:
                c, s = math.cos(drone.yaw), math.sin(drone.yaw)
                v_cmd = np.array([
                    c * v_cmd[0] - s * v_cmd[1],
                    s * v_cmd[0] + c * v_cmd[1],
                    v_cmd[2],
                ])
            accel = (v_cmd - drone.vel) / self.vel_tau_s
            drone.vel = drone.vel + accel * dt
            drone.yaw_rate = self.yaw_rate_cmd
            drone.yaw += drone.yaw_rate * dt
        else:
            # Attitude-rate + thrust dynamics (the interface the real sim
            # honors): first-order body rates, Euler integration, thrust
            # along body -z with hover at `hover_thrust`, linear drag.
            drone.rates = drone.rates + (self.rate_cmd - drone.rates) * (dt / self.rate_tau_s)
            drone.roll += drone.rates[0] * dt
            drone.pitch += drone.rates[1] * dt
            drone.yaw += drone.rates[2] * dt
            drone.yaw_rate = drone.rates[2]
            rot = euler_matrix(drone.roll, drone.pitch, drone.yaw)
            thrust_acc = GRAVITY * self.thrust_cmd / self.hover_thrust
            accel = rot @ np.array([0.0, 0.0, -thrust_acc]) \
                + np.array([0.0, 0.0, GRAVITY]) - self.drag * drone.vel
            drone.vel = drone.vel + accel * dt

        drone.pos = drone.pos + drone.vel * dt

        # Ground contact (NED: ground at z=0, airborne is z<0).
        if drone.pos[2] < -0.3:
            self._was_airborne = True
        if drone.pos[2] >= 0.0:
            if self._was_airborne:
                impact = abs(drone.vel[2])
                self._was_airborne = False
                self._emit_collision(1002, 2 if impact > 1.0 else 1, impact * 1.2)
            # Sitting on the pad: no sinking, ground friction.
            drone.pos[2] = 0.0
            if drone.vel[2] > 0.0:
                drone.vel[2] = 0.0
            drone.vel[:2] *= max(0.0, 1.0 - 5.0 * dt)

        # The IMU reports the ACHIEVED acceleration (post ground clamp).
        self._track_accel = (drone.vel - prev_vel) / dt if dt > 0 else np.zeros(3)

        # Gate crossing.
        if self.active_gate < len(self.gates):
            self._check_gate_crossing(prev_pos)

    def _emit_collision(self, collision_id: int, threat: int, impulse: float) -> None:
        self._pending_collisions.append((collision_id, threat, impulse))

    def _check_gate_crossing(self, prev_pos: np.ndarray) -> None:
        gate = self.gates[self.active_gate]
        c, s = math.cos(gate.travel_yaw), math.sin(gate.travel_yaw)
        travel = np.array([c, s, 0.0])
        lateral = np.array([-s, c, 0.0])

        s_prev = float(travel @ (prev_pos - gate.pos))
        s_now = float(travel @ (self.drone.pos - gate.pos))
        if not (s_prev < 0.0 <= s_now):
            return
        lat = float(lateral @ (self.drone.pos - gate.pos))
        vert = float(self.drone.pos[2] - gate.pos[2])
        half_w, half_h = gate.width / 2.0, gate.height / 2.0

        if abs(lat) <= half_w and abs(vert) <= half_h:
            self.active_gate += 1
            self.last_gate_race_time = self._sim_now_ns() // 1_000_000
            if self.active_gate >= len(self.gates):
                self.race_finish_ns = self._sim_now_ns()
        elif abs(lat) <= half_w * 1.5 and abs(vert) <= half_h * 1.5:
            # Clipped the frame.
            speed = float(np.linalg.norm(self.drone.vel))
            self._emit_collision(1001, 1, speed * 0.5)

    # ----------------------------------------------------------------- vision

    def _project(self, point: np.ndarray) -> tuple[float, float] | None:
        rel = point - self.drone.pos
        c, s = math.cos(self.drone.yaw), math.sin(self.drone.yaw)
        # World -> body (yaw only): x fwd, y right, z down.
        bx = c * rel[0] + s * rel[1]
        by = -s * rel[0] + c * rel[1]
        bz = rel[2]
        if bx < 0.2:
            return None
        u = self.image_w / 2.0 + self.fx * (by / bx)
        v = self.image_h / 2.0 + self.fx * (bz / bx)
        return (u, v)

    def _gate_corners(self, gate: Gate, grow: float = 0.0) -> list[np.ndarray]:
        c, s = math.cos(gate.travel_yaw), math.sin(gate.travel_yaw)
        lateral = np.array([-s, c, 0.0])
        up = np.array([0.0, 0.0, -1.0])
        hw = gate.width / 2.0 + grow
        hh = gate.height / 2.0 + grow
        center = gate.pos
        return [
            center - lateral * hw - up * hh,
            center + lateral * hw - up * hh,
            center + lateral * hw + up * hh,
            center - lateral * hw + up * hh,
        ]

    def _send_frame(self, sock: socket.socket) -> None:
        img = np.full((self.image_h, self.image_w, 3), 40, dtype=np.uint8)

        if self.active_gate < len(self.gates):
            gate = self.gates[self.active_gate]
            outer = [self._project(p) for p in
                     self._gate_corners(gate, grow=gate.frame_thickness)]
            inner = [self._project(p) for p in self._gate_corners(gate)]
            if all(p is not None for p in outer) and all(p is not None for p in inner):
                outer_px = np.array(outer, dtype=np.int32)
                inner_px = np.array(inner, dtype=np.int32)
                # Red ring, matching the real Round-1 gates (phase1e frames).
                cv2.fillPoly(img, [outer_px], (30, 30, 230))
                cv2.fillPoly(img, [inner_px], (40, 40, 40))

        ok, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            return
        data = jpeg.tobytes()
        self._frame_id += 1
        total_chunks = max(1, math.ceil(len(data) / VISION_CHUNK_PAYLOAD))
        sim_time_ns = self._sim_now_ns()
        for chunk_id in range(total_chunks):
            payload = data[chunk_id * VISION_CHUNK_PAYLOAD:(chunk_id + 1) * VISION_CHUNK_PAYLOAD]
            header = struct.pack(VISION_HEADER, self._frame_id, chunk_id, total_chunks,
                                 len(data), len(payload), sim_time_ns)
            sock.sendto(header + payload, self.video_addr)


def main() -> None:
    sim = MockSim()
    sim.start()
    print("Mock sim running (MAVLink -> 127.0.0.1:14550, video -> 127.0.0.1:5600). "
          "Ctrl+C to stop.", flush=True)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        sim.stop()


if __name__ == "__main__":
    main()
