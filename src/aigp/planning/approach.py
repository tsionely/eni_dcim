"""Gate-approach geometry.

Pure functions: gate-relative pose (camera frame) -> desired body-frame
velocity direction and speed. All shaping constants come from the ParamSet so
the flight-to-flight tuner can adjust the racing behavior.
"""
from __future__ import annotations

import numpy as np

from aigp.core.messages import RelPose
from aigp.estimation.attitude_filter import quat_rotate
from aigp.perception.camera import cam_to_body


def altitude_hold_velocity(rel: RelPose, q_att: np.ndarray, aim_up_m: float,
                           gain: float, cap_mps: float = 0.8) -> float:
    """Vertical velocity command from the ABSOLUTE gate-relative height.

    vz estimation drifts (no altimeter; at slow approach speeds the
    vision-velocity SNR collapses — phase3e/3f flights sagged into the
    ground). The gate itself is a drift-free altitude reference: rotate
    the gate vector to world and hold "gate aim_up_m below me". Returns a
    body-z (NED, down-positive) velocity addition.
    """
    world_dz = float(quat_rotate(q_att, cam_to_body(rel.t))[2])   # +: gate below me
    return float(np.clip(gain * (world_dz - aim_up_m), -cap_mps, cap_mps))


def crosstrack_velocity(rel: RelPose, aim_up_m: float, gain: float,
                        cap_mps: float = 0.6) -> np.ndarray:
    """Meter-proportional LATERAL nulling toward the aim point.

    The LOS-direction command alone is geometrically weak up close: a
    constant 0.25m lateral offset at 1.5m range contributes only
    speed*0.16 of correction, and phase3d flights carried exactly such
    offsets into the frame. This term adds v = gain * offset (capped) on
    the body y axis so residual meters get nulled regardless of range.
    Vertical is deliberately excluded: it is already served by aim_up and
    its estimate is the weakest axis — an extra vertical P-term measured
    worse on the mock.
    """
    d_body = cam_to_body(rel.t)
    vy = float(np.clip(gain * d_body[1], -cap_mps, cap_mps))
    return np.array([0.0, vy, 0.0])


def gate_direction_body(rel: RelPose, aim_up_m: float = 0.0) -> tuple[np.ndarray, float]:
    """Unit vector toward the gate center in body axes, and the distance.

    aim_up_m raises the aim point above the gate center (NED: -z is up):
    with no altitude sensor the approach systematically sags, and flights
    that reached the gate plane were passing UNDER the ring. The distance
    returned is to the true center (commit trigger stays geometric).
    """
    d_body = cam_to_body(rel.t)
    dist = float(np.linalg.norm(d_body))
    if dist < 1e-6:
        return np.array([1.0, 0.0, 0.0]), 0.0
    aim = d_body - np.array([0.0, 0.0, aim_up_m])
    norm = float(np.linalg.norm(aim))
    if norm < 1e-6:
        return np.array([1.0, 0.0, 0.0]), dist
    return aim / norm, dist


def approach_speed(dist: float, speed_far: float, speed_near: float,
                   near_distance: float) -> float:
    """Speed profile: slow down as the gate gets close."""
    if dist >= near_distance:
        return speed_far
    frac = max(0.0, dist / near_distance)
    return speed_near + (speed_far - speed_near) * frac


def yaw_rate_to_center(center_px: tuple[float, float], image_size: tuple[int, int],
                       gain: float) -> float:
    """Yaw rate that brings the gate center toward the image center.

    Positive yaw rate turns right (NED body z-down), which moves the image of
    the world left — so a target right of center needs a positive rate.
    """
    width = image_size[0]
    offset = (center_px[0] - width / 2.0) / (width / 2.0)   # -1 .. 1
    return gain * offset
