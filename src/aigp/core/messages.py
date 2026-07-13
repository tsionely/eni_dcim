"""Typed messages exchanged on the bus.

All messages are frozen dataclasses. numpy arrays inside messages are treated
as immutable by convention: publishers must not mutate an array after
publishing it.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Bus topics
# ---------------------------------------------------------------------------

class Topic:
    # Latest-value streams (high rate, only newest matters)
    IMU = "imu"
    FRAME = "frame"
    DETECTION = "detection"
    STATE = "state"
    SETPOINT = "setpoint"
    RACE = "race"
    HEARTBEAT = "heartbeat"
    ACTUATOR = "actuator"
    LOOP_STATS = "loop_stats"
    # Event queues (discrete, every occurrence matters)
    COLLISION = "collision"
    FSM = "fsm"
    COMMAND = "command"


# ---------------------------------------------------------------------------
# Sensor / sim inputs
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ImuSample:
    ts_ns: int                 # sim timeline, ns
    accel: np.ndarray          # specific force, body frame [m/s^2], shape (3,)
    gyro: np.ndarray           # body rates [rad/s], shape (3,)


@dataclass(frozen=True, slots=True)
class CameraFrame:
    frame_id: int
    ts_ns: int                 # sim timeline, ns
    image: np.ndarray          # BGR, shape (H, W, 3)


@dataclass(frozen=True, slots=True)
class Heartbeat:
    ts_ns: int
    armed: bool
    # MAVLink source ids — the real sim emits heartbeats from more than one
    # component (observed in Phase 1: two sources alternating armed state).
    src_system: int = 0
    src_component: int = 0


@dataclass(frozen=True, slots=True)
class RaceStatus:
    ts_ns: int
    sim_boot_time_ms: int
    race_start_boot_time_ms: int   # < 0 if race has not started
    race_finish_time_ns: int       # < 0 if race is ongoing
    active_gate_index: int
    last_gate_race_time: int

    @property
    def started(self) -> bool:
        return self.race_start_boot_time_ms >= 0

    @property
    def finished(self) -> bool:
        return self.race_finish_time_ns >= 0


@dataclass(frozen=True, slots=True)
class CollisionEvent:
    ts_ns: int
    collision_id: int          # 1001 = gate, 1002 = environment
    threat_level: int          # 1-2, 2 = higher impact
    impulse: float             # impulse magnitude [kg m/s]

    GATE = 1001
    ENVIRONMENT = 1002


@dataclass(frozen=True, slots=True)
class ActuatorStatus:
    ts_ns: int
    motors: tuple[float, float, float, float]   # FL, FR, BL, BR


# ---------------------------------------------------------------------------
# Perception / estimation
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RelPose:
    """Pose of a target (gate) relative to the camera/body frame.

    t is the translation camera->gate center in camera coordinates
    (x right, y down, z forward), in meters. normal is the gate plane
    normal expressed in camera coordinates (unit vector).
    """
    t: np.ndarray              # shape (3,)
    normal: np.ndarray         # shape (3,)

    @property
    def distance(self) -> float:
        return float(np.linalg.norm(self.t))


@dataclass(frozen=True, slots=True)
class GateDetection:
    ts_ns: int                 # frame timestamp on sim timeline
    corners_px: np.ndarray     # shape (4, 2), ordered tl, tr, br, bl
    center_px: tuple[float, float]
    image_size: tuple[int, int]      # (width, height)
    rel_pose: RelPose | None   # None if PnP was degenerate
    confidence: float          # 0..1


@dataclass(frozen=True, slots=True)
class StateEstimate:
    ts_ns: int
    q_att: np.ndarray          # attitude quaternion (w, x, y, z), gravity-referenced
    omega: np.ndarray          # body rates [rad/s]
    v_world: np.ndarray        # velocity estimate in yaw-anchored world frame [m/s]
    gate_rel: RelPose | None   # pose relative to current target gate
    gate_rel_age_s: float      # time since last vision fix
    gate_center_px: tuple[float, float] | None
    image_size: tuple[int, int] | None
    healthy: bool


# ---------------------------------------------------------------------------
# Planning / control
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Setpoint:
    phase: str                 # "idle" | "takeoff" | "search" | "approach" | "commit" | "recover" | "hover"
    v_body: np.ndarray         # desired velocity, body frame [m/s], shape (3,)
    yaw_rate: float            # desired yaw rate [rad/s]


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FsmTransition:
    ts_ns: int
    src: str
    dst: str
    reason: str


@dataclass(frozen=True, slots=True)
class LoopStats:
    ts_ns: int
    ticks: int
    overruns: int
    max_late_us: int


# ---------------------------------------------------------------------------
# Serialization (for the flight log)
# ---------------------------------------------------------------------------

def to_jsonable(msg: Any) -> Any:
    """Convert a message (or nested value) to JSON-serializable data."""
    if dataclasses.is_dataclass(msg) and not isinstance(msg, type):
        return {f.name: to_jsonable(getattr(msg, f.name)) for f in dataclasses.fields(msg)}
    if isinstance(msg, np.ndarray):
        return msg.tolist()
    if isinstance(msg, (np.floating, np.integer)):
        return msg.item()
    if isinstance(msg, (list, tuple)):
        return [to_jsonable(v) for v in msg]
    if isinstance(msg, dict):
        return {k: to_jsonable(v) for k, v in msg.items()}
    return msg
