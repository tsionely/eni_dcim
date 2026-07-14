"""VIO-lite state estimator.

Not a full EKF (deliberately — see docs/02): a Mahony attitude filter plus
leaky velocity integration, corrected by vision. The pilot's contract is
gate-relative: what the planner consumes is `gate_rel` (pose relative to the
current target gate, from the detector) plus its age, and the smoothed
attitude/velocity for control damping.

Upgrade slot: everything that fuses signals lives here; swapping in an EKF or
a real VIO later does not touch planner/control code.

TODO(phase-3): propagate gate_rel between vision fixes using the velocity
estimate (dead-reckoning in the gate frame) instead of only aging it.
"""
from __future__ import annotations

import numpy as np

from aigp.core.messages import GateDetection, ImuSample, RelPose, StateEstimate
from aigp.core.params import ParamSet
from aigp.estimation.attitude_filter import MahonyFilter, quat_rotate
from aigp.perception.camera import cam_to_body


class StateEstimator:
    def __init__(self, params: ParamSet) -> None:
        self.attitude = MahonyFilter(kp=float(params.get("estimation.mahony_kp")))
        # Gyro convention correction: the real sim is suspected of reporting
        # angular velocity with INVERTED sign (and ~2.4x scale) relative to
        # the MAVLink convention — probe E settles it; these params apply the
        # fix without code changes (--patch estimation.gyro_sign=-1 ...).
        self.gyro_sign = float(params.get("estimation.gyro_sign", default=1.0))
        self.gyro_scale = float(params.get("estimation.gyro_scale", default=1.0))
        self.vel_leak = float(params.get("estimation.vel_leak"))
        self.vision_blend = float(params.get("estimation.vision_blend"))
        self.vision_vel_blend = float(params.get("estimation.vision_vel_blend", default=0.35))
        # World-frame differentiation cancels the drone's own rotation
        # (needed on the real sim during search yaw); the camera-frame path
        # is kept as default pending mock retuning.
        self.vision_vel_world = bool(params.get("estimation.vision_vel_world_frame",
                                                default=False))
        self.max_age_s = float(params.get("estimation.gate_rel_max_age_s"))

        self.v_world = np.zeros(3)
        self._omega = np.zeros(3)
        self._gyro_bias = np.zeros(3)
        self._level_roll = 0.0
        self._level_pitch = 0.0
        self._last_imu_ts_ns: int | None = None
        self._gate_rel: RelPose | None = None
        self._gate_rel_ts_ns: int | None = None
        self._gate_center_px: tuple[float, float] | None = None
        self._image_size: tuple[int, int] | None = None
        # Fix history for the vision-velocity derivative. At 224Hz the
        # frame-to-frame motion (~5cm) drowns in PnP noise (~±18cm), so the
        # derivative uses a ~0.2s baseline instead of consecutive frames.
        from collections import deque
        self._fix_history: deque = deque(maxlen=64)   # (ts_ns, t_vec)
        self._now_ns = 0

    def set_level_reference(self, roll: float, pitch: float) -> None:
        """Resting attitude from the pre-arm accel (IMU mount tilt)."""
        self._level_roll = roll
        self._level_pitch = pitch

    def set_gyro_bias(self, bias: np.ndarray) -> None:
        """Gyro bias measured while stationary on the ground (pre-arm)."""
        self._gyro_bias = np.asarray(bias, dtype=np.float64)

    def reset(self) -> None:
        self.attitude.reset()
        self.v_world = np.zeros(3)
        self._omega = np.zeros(3)
        self._last_imu_ts_ns = None
        self._gate_rel = None
        self._gate_rel_ts_ns = None
        self._gate_center_px = None

    # ------------------------------------------------------------------ IMU

    def predict(self, imu: ImuSample) -> None:
        self._now_ns = imu.ts_ns
        if self._last_imu_ts_ns is None:
            self._last_imu_ts_ns = imu.ts_ns
            return
        dt = (imu.ts_ns - self._last_imu_ts_ns) / 1e9
        self._last_imu_ts_ns = imu.ts_ns
        if dt <= 0 or dt > 0.5:
            return

        gyro = (imu.gyro - self._gyro_bias) * (self.gyro_sign * self.gyro_scale)
        q = self.attitude.update(gyro, imu.accel, dt)
        self._omega = gyro

        # Specific force f = a - g  =>  a_world = R*f + g_world.
        a_world = quat_rotate(q, imu.accel) + np.array([0.0, 0.0, 9.80665])
        self.v_world = self.v_world + a_world * dt
        # Leak toward zero: bounds unavoidable accelerometer-integration drift.
        self.v_world *= max(0.0, 1.0 - self.vel_leak * dt)

    # --------------------------------------------------------------- vision

    def update_vision(self, det: GateDetection) -> None:
        self._gate_center_px = det.center_px
        self._image_size = det.image_size
        if det.rel_pose is not None:
            # Vision velocity: the gate is static, so the derivative of its
            # relative position IS our velocity. This is the only strong
            # velocity reference we have (accel integration drifts, and the
            # attitude filter is unreliable during coordinated acceleration).
            # Differentiate in the WORLD frame so the drone's own rotation
            # drops out — a yawing search otherwise turns gate pixel sweep
            # into huge fake translation (phase2k run 2: 207 km/h estimate).
            if self.vision_vel_world:
                t_stored = quat_rotate(self.attitude.q, cam_to_body(det.rel_pose.t))
            else:
                t_stored = det.rel_pose.t
            baseline = None
            for ts, t_vec in self._fix_history:
                if 0.15e9 <= det.ts_ns - ts <= 0.45e9:
                    baseline = (ts, t_vec)
                    break   # oldest fix inside the window
            if baseline is not None:
                dt = (det.ts_ns - baseline[0]) / 1e9
                delta = -(t_stored - baseline[1]) / dt
                if self.vision_vel_world:
                    v_world_meas = delta
                else:
                    v_world_meas = quat_rotate(self.attitude.q, cam_to_body(delta))
                k = self.vision_vel_blend
                self.v_world = (1.0 - k) * self.v_world + k * v_world_meas
            self._fix_history.append((det.ts_ns, t_stored))
        if det.rel_pose is not None:
            if self._gate_rel is not None and self._gate_rel_ts_ns is not None:
                # Blend positions to smooth detector jitter.
                b = self.vision_blend
                t = b * det.rel_pose.t + (1.0 - b) * self._gate_rel.t
                n = b * det.rel_pose.normal + (1.0 - b) * self._gate_rel.normal
                norm = np.linalg.norm(n)
                if norm > 1e-9:
                    n = n / norm
                self._gate_rel = RelPose(t=t, normal=n)
            else:
                self._gate_rel = det.rel_pose
            self._gate_rel_ts_ns = det.ts_ns

    def on_gate_passed(self) -> None:
        """Called when active_gate_index increments: current fix is obsolete."""
        self._gate_rel = None
        self._gate_rel_ts_ns = None
        self._gate_center_px = None
        self._fix_history.clear()

    # ---------------------------------------------------------------- state

    @property
    def state(self) -> StateEstimate:
        age = float("inf")
        gate_rel = None
        gate_center = None
        if self._gate_rel is not None and self._gate_rel_ts_ns is not None:
            age = max(0.0, (self._now_ns - self._gate_rel_ts_ns) / 1e9)
            if age <= self.max_age_s:
                gate_rel = self._gate_rel
                gate_center = self._gate_center_px
        return StateEstimate(
            ts_ns=self._now_ns,
            q_att=self.attitude.q,
            omega=self._omega,
            v_world=self.v_world,
            gate_rel=gate_rel,
            gate_rel_age_s=age,
            gate_center_px=gate_center,
            image_size=self._image_size,
            healthy=self._last_imu_ts_ns is not None,
            level_roll=self._level_roll,
            level_pitch=self._level_pitch,
        )
