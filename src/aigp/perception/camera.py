"""Pinhole camera model and gate PnP.

Camera intrinsics are NOT provided by the dev kit. We model a symmetric
pinhole whose horizontal FOV lives in the ParamSet
(perception.camera.fov_deg) so it can be calibrated empirically in Phase 1/3
and refined by the tuning loop. Focal length is derived from the actual image
size of each frame, so resolution changes are harmless.

Camera axes follow OpenCV convention: x right, y down, z forward.
Body-to-camera: body x (forward) = cam z, body y (right) = cam x,
body z (down) = cam y.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from aigp.core.messages import RelPose


class PinholeCamera:
    def __init__(self, fov_deg: float, mount_pitch_deg: float = 0.0) -> None:
        self.fov_deg = fov_deg
        # Camera-to-IMU-body pitch offset (up-positive). The pilot's "body"
        # frame IS the IMU frame; an FPV camera is typically up-tilted, and
        # phase3b rest frames suggest a substantial camera-vs-IMU pitch
        # offset. PnP outputs are de-rotated by this angle so that the
        # cam->body axis permutation downstream is exact. 0 = old behavior;
        # calibration owns the real value (--patch perception.camera.mount_pitch_deg).
        theta = math.radians(mount_pitch_deg)
        c, s = math.cos(theta), math.sin(theta)
        # Rotation about the camera x (right) axis by +theta.
        self._mount_rot = np.array([[1.0, 0.0, 0.0],
                                    [0.0, c, -s],
                                    [0.0, s, c]]) if abs(theta) > 1e-9 else None

    def matrix(self, width: int, height: int) -> np.ndarray:
        fx = (width / 2.0) / math.tan(math.radians(self.fov_deg) / 2.0)
        # Square pixels assumed: fy = fx.
        return np.array(
            [[fx, 0.0, width / 2.0],
             [0.0, fx, height / 2.0],
             [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )

    def solve_gate_pnp(self, corners_px: np.ndarray, image_size: tuple[int, int],
                       gate_w: float, gate_h: float) -> RelPose | None:
        """Recover the gate pose relative to the camera from its 4 corners.

        corners_px must be ordered tl, tr, br, bl. Returns None when the
        geometry is degenerate.
        """
        width, height = image_size
        # Degenerate quads (near-collinear corners) make solvePnP return
        # garbage rather than fail; reject them by pixel area first.
        x, y = corners_px[:, 0], corners_px[:, 1]
        area = 0.5 * abs(
            (x[0] * y[1] - x[1] * y[0]) + (x[1] * y[2] - x[2] * y[1])
            + (x[2] * y[3] - x[3] * y[2]) + (x[3] * y[0] - x[0] * y[3])
        )
        if area < 20.0:
            return None

        # Gate corners in the gate frame: origin at center, x right, y down,
        # z out of the gate plane (toward the camera on approach).
        half_w, half_h = gate_w / 2.0, gate_h / 2.0
        object_points = np.array(
            [[-half_w, -half_h, 0.0],
             [half_w, -half_h, 0.0],
             [half_w, half_h, 0.0],
             [-half_w, half_h, 0.0]],
            dtype=np.float64,
        )
        image_points = corners_px.astype(np.float64).reshape(4, 1, 2)
        try:
            ok, rvec, tvec = cv2.solvePnP(
                object_points, image_points, self.matrix(width, height), None,
                flags=cv2.SOLVEPNP_IPPE,
            )
        except cv2.error:
            return None
        if not ok:
            return None
        t = tvec.reshape(3)
        if not np.isfinite(t).all() or t[2] <= 0.05 or np.linalg.norm(t) > 150.0:
            return None
        rot, _ = cv2.Rodrigues(rvec)
        normal = rot[:, 2]
        # Orient the normal toward the camera side we approach from.
        if normal[2] > 0:
            normal = -normal
        if self._mount_rot is not None:
            t = self._mount_rot @ t
            normal = self._mount_rot @ normal
        return RelPose(t=t, normal=normal)


def body_to_cam(v_body: np.ndarray) -> np.ndarray:
    """Rotate a body-frame vector (x fwd, y right, z down) into camera axes."""
    return np.array([v_body[1], v_body[2], v_body[0]], dtype=np.float64)


def cam_to_body(v_cam: np.ndarray) -> np.ndarray:
    """Rotate a camera-frame vector into body axes."""
    return np.array([v_cam[2], v_cam[0], v_cam[1]], dtype=np.float64)
