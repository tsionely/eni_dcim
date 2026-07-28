"""Image-based visual servo (IBVS) terminal centering — mount-pitch correct.

Ported from the alternative "AIGP Autonomy Stack" FunnelPassController
(gate_pass_controller.py IBVS mode), adapted for THIS airframe's fixed,
UP-TILTED FPV camera.

Why the port is not verbatim: the source IBVS centers the gate at the
IMAGE center (img_cy) on the assumption of a forward-facing camera. Our
camera is mounted mount_pitch_deg (~29-34) NOSE-UP, so a gate straight
ahead at our own altitude projects BELOW the image center; centering it in
the image would command a steady descent and fly us under every gate.

The correct primitive is a BEARING servo: back-project the gate's pixel
center through the intrinsics AND the mount rotation into the BODY frame,
then null the body-frame azimuth/elevation. Driving the gate toward
body-forward (not image-center) keeps it in the lower-middle of the
up-tilted FOV — exactly where it stays visible — and pulls a high, close
gate DOWN in the frame before it exits the top (the R2C run-1 gate-2
dropout: detection collapsed as the off-axis gate drifted out of frame).

Pure numpy; no 3D pose / PnP needed — only the pixel center, the image
size, and the two camera constants. Config-gated in the planner
(planner.ibvs.enable), default OFF: unpatched flights never call this.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class IbvsConfig:
    enable: bool = False
    lat_gain: float = 1.6       # body-right fraction -> lateral vel [m/s]
    vert_gain: float = 1.2      # body-down fraction  -> vertical vel [m/s]
    yaw_gain: float = 1.5       # azimuth [rad]       -> yaw rate [rad/s]
    max_lat_mps: float = 1.5
    max_vert_mps: float = 1.0
    yaw_cap_rps: float = 0.8
    aim_up_frac: float = 0.0    # bias the vertical target this far ABOVE center


def gate_dir_body(center_px: tuple[float, float],
                  image_size: tuple[int, int],
                  fov_deg: float, mount_pitch_deg: float) -> np.ndarray:
    """Unit direction to the gate in BODY axes [forward, right, down].

    Back-projects the pixel center to a camera ray, applies the +pitch
    mount rotation (same convention as PinholeCamera._mount_rot), then
    permutes camera->body. The result is mount-corrected: a gate straight
    ahead at our altitude yields [~1, ~0, ~0] regardless of camera tilt.
    """
    w, h = image_size
    u, v = center_px
    fx = (w / 2.0) / math.tan(math.radians(fov_deg) / 2.0)
    # Camera axes: x right, y down, z forward.
    ray = np.array([(u - w / 2.0) / fx, (v - h / 2.0) / fx, 1.0])
    theta = math.radians(mount_pitch_deg)
    if abs(theta) > 1e-9:
        c, s = math.cos(theta), math.sin(theta)
        # Rotation about camera x (right) by +theta (up-tilt de-rotation).
        ray = np.array([ray[0],
                        c * ray[1] - s * ray[2],
                        s * ray[1] + c * ray[2]])
    # cam -> body: body x (fwd)=cam z, body y (right)=cam x, body z (down)=cam y
    d_body = np.array([ray[2], ray[0], ray[1]])
    n = float(np.linalg.norm(d_body))
    if n < 1e-9:
        return np.array([1.0, 0.0, 0.0])
    return d_body / n


def ibvs_centering(center_px: tuple[float, float],
                   image_size: tuple[int, int],
                   fov_deg: float, mount_pitch_deg: float,
                   cfg: IbvsConfig) -> tuple[float, float, float]:
    """Return (vy_body, vz_body, yaw_rate) that center the gate at body-fwd.

    vy_body: body-right velocity [m/s] (NED y), pulls the gate's azimuth
             to zero. vz_body: body-down velocity [m/s] (NED z), pulls the
             gate's elevation to the aim point (climb when the gate rides
             high). yaw_rate: turns the fixed camera onto the gate bearing.
    """
    d = gate_dir_body(center_px, image_size, fov_deg, mount_pitch_deg)
    fwd, right, down = float(d[0]), float(d[1]), float(d[2])
    az = math.atan2(right, max(fwd, 1e-3))
    vy = float(np.clip(cfg.lat_gain * right, -cfg.max_lat_mps, cfg.max_lat_mps))
    # aim_up_frac raises the vertical target ABOVE center (NED down-positive:
    # a positive aim biases the command to climb slightly).
    vz = float(np.clip(cfg.vert_gain * (down - cfg.aim_up_frac),
                       -cfg.max_vert_mps, cfg.max_vert_mps))
    yaw = float(np.clip(cfg.yaw_gain * az, -cfg.yaw_cap_rps, cfg.yaw_cap_rps))
    return vy, vz, yaw


@dataclass(frozen=True)
class VisibilityConfig:
    enable: bool = False
    fresh_full_s: float = 0.15   # below this age: no visibility penalty
    stale_age_s: float = 0.5     # at/above this age: full penalty (min_frac)
    min_frac: float = 0.35       # never scale speed below this fraction
    min_speed_mps: float = 0.8   # absolute floor
    panic_ttc_s: float = 0.6     # time-to-contact panic-brake threshold
    panic_scale: float = 0.5     # multiply speed by this when panicking


def visibility_speed(base_speed: float, gate_age_s: float,
                     dist: float, cur_speed: float,
                     cfg: VisibilityConfig) -> float:
    """Scale forward speed down as the gate detection weakens.

    Ported from RacingIntelligence.VisibilitySpeedController. Uses
    detection FRESHNESS (age since last fix) as the confidence proxy we
    have, plus a time-to-contact panic brake: closing fast on a gate whose
    fix is going stale is exactly the R2 forward-into-structure death
    (run4/run5). Slower blind meters cost time; they do not cost the frame.
    """
    speed = base_speed
    if gate_age_s > cfg.fresh_full_s:
        span = max(cfg.stale_age_s - cfg.fresh_full_s, 1e-3)
        f = 1.0 - (gate_age_s - cfg.fresh_full_s) / span
        f = max(cfg.min_frac, min(1.0, f))
        speed *= f
    ttc = dist / max(cur_speed, 0.1)
    if ttc < cfg.panic_ttc_s and gate_age_s > cfg.fresh_full_s:
        speed *= cfg.panic_scale
    return max(cfg.min_speed_mps, min(speed, base_speed))
