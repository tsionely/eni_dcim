"""Gate-approach geometry.

Pure functions: gate-relative pose (camera frame) -> desired body-frame
velocity direction and speed. All shaping constants come from the ParamSet so
the flight-to-flight tuner can adjust the racing behavior.
"""
from __future__ import annotations

import numpy as np

from aigp.core.messages import RelPose
from aigp.perception.camera import cam_to_body


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
