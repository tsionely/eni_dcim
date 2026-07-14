"""Mahony-style complementary attitude filter.

Gyro integration corrected toward the accelerometer's gravity direction.
Yaw is unobservable from gravity, so the quaternion's yaw is relative to the
takeoff heading — consistent with the gate-relative design (we never need
absolute yaw).

Quaternion convention: (w, x, y, z), body-to-world (NED).
"""
from __future__ import annotations

import numpy as np

GRAVITY = 9.80665


def quat_multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ])


def quat_normalize(q: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(q)
    if n < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0])
    return q / n


def quat_rotate(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Rotate vector v from body to world by quaternion q."""
    qv = np.array([0.0, v[0], v[1], v[2]])
    q_conj = np.array([q[0], -q[1], -q[2], -q[3]])
    return quat_multiply(quat_multiply(q, qv), q_conj)[1:]


def quat_rotate_inv(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Rotate vector v from world to body."""
    q_conj = np.array([q[0], -q[1], -q[2], -q[3]])
    return quat_rotate(q_conj, v)


def yaw_from_quat(q: np.ndarray) -> float:
    """Yaw angle [rad] of quaternion (w, x, y, z), NED convention."""
    return float(np.arctan2(2.0 * (q[0] * q[3] + q[1] * q[2]),
                            1.0 - 2.0 * (q[2] ** 2 + q[3] ** 2)))


class MahonyFilter:
    def __init__(self, kp: float = 2.0) -> None:
        self.kp = kp
        self.q = np.array([1.0, 0.0, 0.0, 0.0])

    def reset(self) -> None:
        self.q = np.array([1.0, 0.0, 0.0, 0.0])

    def set_attitude_euler(self, roll: float, pitch: float, yaw: float = 0.0) -> None:
        """Anchor the attitude (used with kp=0: gyro-only integration from a
        known resting attitude, immune to thrust-direction aliasing)."""
        cr, sr = np.cos(roll / 2), np.sin(roll / 2)
        cp, sp = np.cos(pitch / 2), np.sin(pitch / 2)
        cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)
        self.q = quat_normalize(np.array([
            cy * cp * cr + sy * sp * sr,
            cy * cp * sr - sy * sp * cr,
            cy * sp * cr + sy * cp * sr,
            sy * cp * cr - cy * sp * sr,
        ]))

    def update(self, gyro: np.ndarray, accel: np.ndarray, dt: float) -> np.ndarray:
        """gyro [rad/s] and accel (specific force) [m/s^2] in body frame."""
        omega = gyro.astype(np.float64).copy()

        # Accelerometer correction: ONLY when quasi-static. During coordinated
        # acceleration the specific force aligns with the thrust axis, and a
        # loose gate here pulls the estimate toward "level" while the true
        # tilt runs away (observed in the mock at approach speeds). Tight
        # bands: near-1g magnitude and low rotation.
        a_norm = np.linalg.norm(accel)
        if (0.85 * GRAVITY < a_norm < 1.15 * GRAVITY
                and np.linalg.norm(gyro) < 1.0):
            # Measured "down" in body frame (gravity direction).
            down_meas = -accel / a_norm
            # Predicted "down": world +z (NED) rotated into body.
            down_pred = quat_rotate_inv(self.q, np.array([0.0, 0.0, 1.0]))
            # Error rotation axis (small-angle): steers the estimate so the
            # predicted down converges onto the measured down.
            err = np.cross(down_meas, down_pred)
            omega += self.kp * err

        dq = 0.5 * quat_multiply(self.q, np.array([0.0, *omega])) * dt
        self.q = quat_normalize(self.q + dq)
        return self.q

    def gravity_body(self) -> np.ndarray:
        """Gravity vector expressed in the body frame [m/s^2]."""
        return quat_rotate_inv(self.q, np.array([0.0, 0.0, GRAVITY]))
