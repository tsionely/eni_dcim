"""Velocity-setpoint backend (default).

Shapes the planner's desired velocity (slew limiting + speed clamps) and
sends it via set_position_target_local_ned. The sim's internal flight
controller handles attitude stabilization.

Frame note: whether the sim interprets velocity in BODY or LOCAL_NED frame is
resolved empirically by scripts/frame_probe.py in Phase 1
(control.velocity.frame). TODO(phase-1): if only LOCAL_NED is honored, rotate
body-frame setpoints by the estimator's yaw before sending.
"""
from __future__ import annotations

import numpy as np

from aigp.core.messages import Setpoint, StateEstimate
from aigp.core.params import ParamSet
from aigp.control.interface import ControlBackend


class VelocityBackend(ControlBackend):
    def __init__(self, mavlink_io, params: ParamSet) -> None:
        self.io = mavlink_io
        self.body_frame = params.get("control.velocity.frame") == "body"
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

        # Slew limit toward the target.
        delta = target - self._v_cmd
        max_step = self.slew * max(dt, 1e-4)
        step = np.linalg.norm(delta)
        if step > max_step:
            delta *= max_step / step
        self._v_cmd = self._v_cmd + delta

        yaw_rate = float(np.clip(sp.yaw_rate, -self.max_yaw_rate, self.max_yaw_rate))
        self.io.send_velocity(
            float(self._v_cmd[0]), float(self._v_cmd[1]), float(self._v_cmd[2]),
            yaw_rate, body_frame=self.body_frame,
        )
