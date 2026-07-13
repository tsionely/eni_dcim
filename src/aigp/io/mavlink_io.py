"""MAVLink connection: RX thread + TX helpers.

Wire formats (typemasks, encapsulated-data structs, the sim-reset command id)
are carried over from the official PyAIPilotExample template. Differences from
the template:

- recv_match(blocking=True, timeout=...) instead of a 1ms-sleep poll
- dispatch table instead of an if/elif chain
- parsed messages are published as typed dataclasses on the bus
- TIMESYNC responses feed the SimClock offset estimator
"""
from __future__ import annotations

import struct
import time

from pymavlink import mavutil

from aigp.core.agent import Agent
from aigp.core.bus import Bus
from aigp.core.clock import SimClock
from aigp.core.messages import (
    ActuatorStatus,
    CollisionEvent,
    Heartbeat,
    ImuSample,
    RaceStatus,
    Topic,
)

import numpy as np

# Sim-specific MAVLink command: reset the simulator (from the template)
MAVLINK_CMD_SIM_RESET = 31000

# ENCAPSULATED_DATA payload type ids (from the template)
ENCAPSULATED_RACE_STATUS_MSG_ID = 1
ENCAPSULATED_TRACK_INFO_MSG_ID = 2

RACE_STATUS_STRUCT = "<BQqqIq"

# Attitude-rate control: command body rates + thrust, ignore the quaternion
RATES_ATTITUDE_MASK = mavutil.mavlink.ATTITUDE_TARGET_TYPEMASK_ATTITUDE_IGNORE

# Velocity control: command vx/vy/vz + yaw rate, ignore position/accel/yaw.
# (The template also ignored yaw_rate; we keep it active so the planner can
# rotate while translating, e.g. during gate search.)
VELOCITY_YAWRATE_MASK = (
    mavutil.mavlink.POSITION_TARGET_TYPEMASK_X_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_Y_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_Z_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AX_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AY_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_AZ_IGNORE
    | mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_IGNORE
)


class MavlinkIO(Agent):
    name = "mavlink_io"

    def __init__(self, bus: Bus, clock: SimClock, listen_ip: str, listen_port: int,
                 mode: str = "listen") -> None:
        super().__init__()
        self.bus = bus
        self.clock = clock
        # "listen": classic template topology — we bind the port, the sim
        # sends to us. "connect": v1.0.3385-style — the sim binds the port,
        # we send to it and it streams back to our source address.
        self.mode = mode
        prefix = "udpin" if mode == "listen" else "udpout"
        self.endpoint = f"{prefix}:{listen_ip}:{listen_port}"
        self.conn = None
        self._boot_mono_ms = int(time.monotonic() * 1000)
        self._pending_timesync: dict[int, int] = {}   # our tc1 stamp -> send mono ns
        self._track_chunks: dict[int, dict[int, bytes]] = {}
        self._expected_track_chunks: dict[int, int] = {}
        self._dispatch = {
            "HEARTBEAT": self._on_heartbeat,
            "TIMESYNC": self._on_timesync,
            "HIGHRES_IMU": self._on_highres_imu,
            "ACTUATOR_OUTPUT_STATUS": self._on_actuator_output_status,
            "COLLISION": self._on_collision,
            "ENCAPSULATED_DATA": self._on_encapsulated_data,
            "DATA_TRANSMISSION_HANDSHAKE": self._on_track_handshake,
        }

    # ------------------------------------------------------------------ setup

    def connect(self, timeout_s: float = 30.0) -> None:
        """Open the UDP endpoint and wait for the sim's heartbeat.

        In connect mode we announce ourselves with client heartbeats while
        waiting — the sim only learns our address from our first packet.
        """
        self.conn = mavutil.mavlink_connection(self.endpoint,
                                               source_system=245, source_component=190)
        deadline = time.monotonic() + timeout_s
        while True:
            if self.mode == "connect":
                self.send_client_heartbeat()
            msg = self.conn.wait_heartbeat(timeout=1.0)
            if msg is not None:
                return
            if time.monotonic() > deadline:
                raise TimeoutError(f"no heartbeat on {self.endpoint} within {timeout_s}s")

    def send_client_heartbeat(self) -> None:
        """Announce ourselves (GCS-style heartbeat)."""
        self.conn.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_GCS,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0, 0, 0,
        )

    # --------------------------------------------------------------- RX loop

    def _run(self) -> None:
        while self.should_run():
            try:
                msg = self.conn.recv_match(blocking=True, timeout=0.1)
            except ConnectionResetError:
                # Sim went away; keep trying until stopped.
                time.sleep(0.1)
                continue
            if msg is None:
                continue
            handler = self._dispatch.get(msg.get_type())
            if handler is not None:
                handler(msg)

    # ------------------------------------------------------------- handlers

    def _on_heartbeat(self, msg) -> None:
        armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        self.bus.publish_latest(Topic.HEARTBEAT, Heartbeat(
            self.clock.sim_now_ns(), armed,
            src_system=msg.get_srcSystem(), src_component=msg.get_srcComponent(),
        ))

    def _on_timesync(self, msg) -> None:
        # Response carries our original stamp in ts1 and the server time in tc1.
        if msg.ts1 == 0:
            return
        sent_mono = self._pending_timesync.pop(msg.ts1, None)
        if sent_mono is None:
            return
        self.clock.on_timesync(msg.tc1, sent_mono, time.monotonic_ns())

    def _on_highres_imu(self, msg) -> None:
        self.bus.publish_latest(
            Topic.IMU,
            ImuSample(
                ts_ns=int(msg.time_usec) * 1000,
                accel=np.array([msg.xacc, msg.yacc, msg.zacc], dtype=np.float64),
                gyro=np.array([msg.xgyro, msg.ygyro, msg.zgyro], dtype=np.float64),
            ),
        )

    def _on_actuator_output_status(self, msg) -> None:
        self.bus.publish_latest(
            Topic.ACTUATOR,
            ActuatorStatus(
                ts_ns=int(msg.time_usec) * 1000,
                motors=(msg.actuator[0], msg.actuator[1], msg.actuator[2], msg.actuator[3]),
            ),
        )

    def _on_collision(self, msg) -> None:
        # id: 1001 = gate, 1002 = environment; horizontal_minimum_delta is the
        # impulse magnitude in kg m/s (template-documented repurposing).
        self.bus.publish_event(
            Topic.COLLISION,
            CollisionEvent(
                ts_ns=self.clock.sim_now_ns(),
                collision_id=int(msg.id),
                threat_level=int(msg.threat_level),
                impulse=float(msg.horizontal_minimum_delta),
            ),
        )

    def _on_encapsulated_data(self, msg) -> None:
        raw = bytes(msg.data)
        if not raw:
            return
        data_type = raw[0]
        if data_type == ENCAPSULATED_RACE_STATUS_MSG_ID:
            self._on_race_status(raw)
        elif data_type == ENCAPSULATED_TRACK_INFO_MSG_ID:
            self._on_track_data_packet(msg, raw)

    def _on_race_status(self, raw: bytes) -> None:
        (_, sim_boot_time_ms, race_start_boot_time_ms, race_finish_time_ns,
         active_gate_index, last_gate_race_time) = struct.unpack_from(RACE_STATUS_STRUCT, raw)
        self.bus.publish_latest(
            Topic.RACE,
            RaceStatus(
                ts_ns=self.clock.sim_now_ns(),
                sim_boot_time_ms=sim_boot_time_ms,
                race_start_boot_time_ms=race_start_boot_time_ms,
                race_finish_time_ns=race_finish_time_ns,
                active_gate_index=active_gate_index,
                last_gate_race_time=last_gate_race_time,
            ),
        )

    # Track data plumbing kept from the template even though the current sim
    # nulls gate positions — a future sim version may re-enable it.
    def _on_track_handshake(self, msg) -> None:
        self._track_chunks[msg.width] = {}
        self._expected_track_chunks[msg.width] = msg.packets

    def _on_track_data_packet(self, msg, raw: bytes) -> None:
        _, transfer_id = struct.unpack_from("<BH", raw)
        if transfer_id not in self._expected_track_chunks:
            return
        self._track_chunks[transfer_id][msg.seqnr] = raw[3:]
        if len(self._track_chunks[transfer_id]) == self._expected_track_chunks[transfer_id]:
            chunks = self._track_chunks.pop(transfer_id)
            del self._expected_track_chunks[transfer_id]
            payload = b"".join(chunks[i] for i in range(len(chunks)))
            self._on_track_data(payload)

    def _on_track_data(self, payload: bytes) -> None:
        # Values are nulled by the current sim; parsed for forward compatibility.
        pass

    # ------------------------------------------------------------------- TX

    def _time_boot_ms(self) -> int:
        return int(time.monotonic() * 1000) - self._boot_mono_ms

    def send_timesync_request(self) -> None:
        stamp = time.monotonic_ns()
        self._pending_timesync[stamp] = stamp
        # Bound the pending map in case responses are lost.
        if len(self._pending_timesync) > 64:
            oldest = min(self._pending_timesync)
            del self._pending_timesync[oldest]
        self.conn.mav.timesync_send(stamp, 0)

    def send_velocity(self, vx: float, vy: float, vz: float, yaw_rate: float,
                      body_frame: bool) -> None:
        frame = (mavutil.mavlink.MAV_FRAME_BODY_NED if body_frame
                 else mavutil.mavlink.MAV_FRAME_LOCAL_NED)
        self.conn.mav.set_position_target_local_ned_send(
            self._time_boot_ms(),
            self.conn.target_system,
            self.conn.target_component,
            frame,
            VELOCITY_YAWRATE_MASK,
            0.0, 0.0, 0.0,
            vx, vy, vz,
            0.0, 0.0, 0.0,
            0.0,
            yaw_rate,
        )

    def send_attitude_rates(self, roll_rate: float, pitch_rate: float, yaw_rate: float,
                            thrust: float) -> None:
        self.conn.mav.set_attitude_target_send(
            self._time_boot_ms(),
            self.conn.target_system,
            self.conn.target_component,
            RATES_ATTITUDE_MASK,
            [1.0, 0.0, 0.0, 0.0],   # quaternion ignored via typemask
            roll_rate,
            pitch_rate,
            yaw_rate,
            thrust,
        )

    def send_motor_rpms(self, rpms: tuple[float, float, float, float]) -> None:
        controls = [rpms[0], rpms[1], rpms[2], rpms[3], 0.0, 0.0, 0.0, 0.0]
        self.conn.mav.set_actuator_control_target_send(
            int(time.time() * 1e6),
            self.conn.target_system,
            self.conn.target_component,
            0,
            controls,
        )

    def arm(self) -> None:
        self._arm_disarm(1)

    def disarm(self) -> None:
        self._arm_disarm(0)

    def _arm_disarm(self, value: int) -> None:
        self.conn.mav.command_long_send(
            self.conn.target_system,
            self.conn.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            value, 0, 0, 0, 0, 0, 0,
        )

    def sim_reset(self) -> None:
        self.conn.mav.command_long_send(
            self.conn.target_system,
            self.conn.target_component,
            MAVLINK_CMD_SIM_RESET,
            0,
            0, 0, 0, 0, 0, 0, 0,
        )
