"""Attitude-rate backend (Phase 6 — structure in place, tuning pending).

Cascade: velocity error -> desired tilt + thrust -> body-rate commands.
Runs the full 250Hz path; this is where loop timing truly matters.

TODO(phase-6): tune gains via a campaign on the mock sim first, then the real
sim; validate the small-angle tilt mapping at racing speeds.
"""
from __future__ import annotations

import numpy as np

from aigp.core.messages import Setpoint, StateEstimate
from aigp.core.params import ParamSet
from aigp.control.interface import ControlBackend
from aigp.control.pid import PID
from aigp.estimation.attitude_filter import quat_rotate_inv


class AttitudeRateBackend(ControlBackend):
    def __init__(self, mavlink_io, params: ParamSet) -> None:
        self.io = mavlink_io
        kp = float(params.get("control.att_rate.vel_p"))
        ki = float(params.get("control.att_rate.vel_i"))
        kd = float(params.get("control.att_rate.vel_d"))
        self.tilt_max = float(params.get("control.att_rate.tilt_max_rad"))
        self.rate_p = float(params.get("control.att_rate.rate_p"))
        self.hover_thrust = float(params.get("control.att_rate.hover_thrust"))
        self.pid_vx = PID(kp, ki, kd, out_limit=self.tilt_max)
        self.pid_vy = PID(kp, ki, kd, out_limit=self.tilt_max)
        self.pid_vz = PID(kp, ki, kd, out_limit=0.4)

    def reset(self) -> None:
        self.pid_vx.reset()
        self.pid_vy.reset()
        self.pid_vz.reset()

    def update(self, sp: Setpoint, state: StateEstimate, dt: float) -> None:
        # Velocity error in body frame (estimated world velocity rotated back).
        v_body = quat_rotate_inv(state.q_att, state.v_world)
        err = sp.v_body - v_body

        # Desired tilt: pitch forward for +x error, roll right for +y error.
        pitch_des = -self.pid_vx.update(float(err[0]), dt)
        roll_des = self.pid_vy.update(float(err[1]), dt)
        thrust = self.hover_thrust - self.pid_vz.update(float(err[2]), dt)
        thrust = float(np.clip(thrust, 0.05, 0.95))

        # Rate P-loop on the tilt error (small-angle roll/pitch from quaternion).
        q = state.q_att
        roll = np.arctan2(2 * (q[0] * q[1] + q[2] * q[3]),
                          1 - 2 * (q[1] ** 2 + q[2] ** 2))
        pitch = np.arcsin(np.clip(2 * (q[0] * q[2] - q[3] * q[1]), -1.0, 1.0))
        roll_rate = self.rate_p * (roll_des - roll)
        pitch_rate = self.rate_p * (pitch_des - pitch)

        self.io.send_attitude_rates(float(roll_rate), float(pitch_rate),
                                    float(sp.yaw_rate), thrust)
