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
        # Vertical axis gets its own, stiffer gains: with no altitude sensor,
        # vz comes from leaky accel integration, and a soft vertical loop
        # lets the drone sink slowly into the ground.
        vz_p = float(params.get("control.att_rate.vz_p", default=0.8))
        vz_i = float(params.get("control.att_rate.vz_i", default=0.4))
        self.tilt_max = float(params.get("control.att_rate.tilt_max_rad"))
        self.rate_p = float(params.get("control.att_rate.rate_p"))
        self.rate_max = float(params.get("control.att_rate.rate_max_rps", default=3.0))
        # Per-axis rate-command sign: phase2a measured an INVERTED pitch-rate
        # response on the real sim (commanded +0.40, measured -0.97). Standard
        # MAVLink convention is +1; flip per axis once the D probe confirms.
        self.sign_roll = float(params.get("control.att_rate.rate_sign_roll", default=1.0))
        self.sign_pitch = float(params.get("control.att_rate.rate_sign_pitch", default=1.0))
        self.sign_yaw = float(params.get("control.att_rate.rate_sign_yaw", default=1.0))
        # False -> hold world-level (pitch 0) instead of the resting attitude,
        # for the case where the launch pad itself is tilted (thrust along
        # body -z means hover needs IMU-level, not rest-attitude).
        self.use_level_ref = bool(params.get("control.att_rate.use_level_ref", default=True))
        self.hover_thrust = float(params.get("control.att_rate.hover_thrust"))
        self.pid_vx = PID(kp, ki, kd, out_limit=self.tilt_max)
        self.pid_vy = PID(kp, ki, kd, out_limit=self.tilt_max)
        self.pid_vz = PID(vz_p, vz_i, 0.0, i_limit=0.5, out_limit=0.45)

    def reset(self) -> None:
        self.pid_vx.reset()
        self.pid_vy.reset()
        self.pid_vz.reset()

    def update(self, sp: Setpoint, state: StateEstimate, dt: float) -> None:
        # Velocity error in body frame (estimated world velocity rotated back).
        v_body = quat_rotate_inv(state.q_att, state.v_world)
        err = sp.v_body - v_body

        # Desired tilt: pitch forward for +x error, roll right for +y error.
        ref_pitch = state.level_pitch if self.use_level_ref else 0.0
        ref_roll = state.level_roll if self.use_level_ref else 0.0
        pitch_des = ref_pitch - self.pid_vx.update(float(err[0]), dt)
        roll_des = ref_roll + self.pid_vy.update(float(err[1]), dt)

        # Current attitude (small-angle roll/pitch from quaternion).
        q = state.q_att
        roll = np.arctan2(2 * (q[0] * q[1] + q[2] * q[3]),
                          1 - 2 * (q[1] ** 2 + q[2] ** 2))
        pitch = np.arcsin(np.clip(2 * (q[0] * q[2] - q[3] * q[1]), -1.0, 1.0))

        # Thrust: hover + vertical-velocity correction, compensated for the
        # cosine loss when tilted (otherwise the drone sags in fast forward
        # flight and dives into gate frames).
        tilt_cos = max(0.35, float(np.cos(roll) * np.cos(pitch)))
        thrust = (self.hover_thrust - self.pid_vz.update(float(err[2]), dt)) / tilt_cos
        thrust = float(np.clip(thrust, 0.05, 0.95))
        roll_rate = np.clip(self.rate_p * (roll_des - roll),
                            -self.rate_max, self.rate_max)
        pitch_rate = np.clip(self.rate_p * (pitch_des - pitch),
                             -self.rate_max, self.rate_max)

        self.io.send_attitude_rates(self.sign_roll * float(roll_rate),
                                    self.sign_pitch * float(pitch_rate),
                                    self.sign_yaw * float(sp.yaw_rate), thrust)
