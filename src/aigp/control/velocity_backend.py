"""Velocity-setpoint backend (default).

Shapes the planner's desired body-frame velocity (slew limiting + speed
clamps) and sends it via set_position_target_local_ned. The sim's internal
flight controller handles attitude stabilization.

Frame handling (resolved empirically — see fixtures/ Phase-1 runs and docs/02):
- frame="body": send as MAV_FRAME_BODY_NED, no rotation.
- frame="ned": the sim interprets velocities in LOCAL_NED (world frame), so
  rotate the body-frame setpoint to world using the estimator's yaw plus
  control.velocity.world_yaw_offset_rad (the unknown spawn heading; measured
  by scripts/frame_probe.py, 0 until calibrated).

The v1.0.3385 probe pointed at LOCAL_NED but the measurement was noisy
(uncommanded spin during the step); re-verify with frame_probe v2 before
trusting either mode at speed.
"""
from __future__ import annotations

import math

import numpy as np

from aigp.core.messages import Setpoint, StateEstimate
from aigp.core.params import ParamSet
from aigp.control.interface import ControlBackend
from aigp.estimation.attitude_filter import yaw_from_quat


class VelocityBackend(ControlBackend):
    def __init__(self, mavlink_io, params: ParamSet) -> None:
        self.io = mavlink_io
        self.body_frame = params.get("control.velocity.frame") == "body"
        self.world_yaw_offset = float(
            params.get("control.velocity.world_yaw_offset_rad", default=0.0))
        self.max_speed = float(params.get("control.velocity.max_speed_mps"))
        self.max_climb = float(params.get("control.velocity.max_climb_mps"))
        self.slew = float(params.get("control.velocity.slew_mps2"))
        self.max_yaw_rate = float(params.get("control.velocity.yaw_rate_max_rps"))
        self._v_cmd = np.zeros(3)

    def reset(self) -> None:
        self._v_cmd = np.zeros(3)

    def update(self, sp: Setpoint, state: StateEstimate, dt: float) -> None:
        target = sp.v_body.astype(np.float64)

        # Speed clamps.
        horiz = np.linalg.norm(target[:2])
        if horiz > self.max_speed:
            target[:2] *= self.max_speed / horiz
        target[2] = np.clip(target[2], -self.max_climb, self.max_climb)

        # Slew limit toward the target (in body frame).
        delta = target - self._v_cmd
        max_step = self.slew * max(dt, 1e-4)
        step = np.linalg.norm(delta)
        if step > max_step:
            delta *= max_step / step
        self._v_cmd = self._v_cmd + delta

        yaw_rate = float(np.clip(sp.yaw_rate, -self.max_yaw_rate, self.max_yaw_rate))

        vx, vy, vz = float(self._v_cmd[0]), float(self._v_cmd[1]), float(self._v_cmd[2])
        if not self.body_frame:
            # Rotate body-frame setpoint into the sim's world frame.
            psi = yaw_from_quat(state.q_att) + self.world_yaw_offset
            c, s = math.cos(psi), math.sin(psi)
            vx, vy = c * vx - s * vy, s * vx + c * vy

        self.io.send_velocity(vx, vy, vz, yaw_rate, body_frame=self.body_frame)
