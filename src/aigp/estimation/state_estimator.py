"""VIO-lite state estimator.

Not a full EKF (deliberately — see docs/02): a Mahony attitude filter plus
leaky velocity integration, corrected by vision. The pilot's contract is
gate-relative: what the planner consumes is `gate_rel` (pose relative to the
current target gate, from the detector) plus its age, and the smoothed
attitude/velocity for control damping.

Between vision fixes gate_rel is DEAD-RECKONED (gyro + velocity estimate):
detector dropouts cluster exactly where precision matters most — at close
range, when the ring clips the frame edge — and steering on a frozen fix
there is what pushed flights past the gate.

Upgrade slot: everything that fuses signals lives here; swapping in an EKF or
a real VIO later does not touch planner/control code.
"""
from __future__ import annotations

import math

import numpy as np

from aigp.core.messages import GateDetection, ImuSample, RelPose, StateEstimate
from aigp.core.params import ParamSet
from aigp.estimation.attitude_filter import MahonyFilter, quat_rotate, quat_rotate_inv
from aigp.perception.camera import body_to_cam, cam_to_body


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
        # Vision-yaw: the real sim's gyro z-axis is pinned (R10), so the
        # yaw the gyro misses is measured from the rotation of the static
        # gate's normal between fixes. Adds ~0 when the gyro is healthy.
        # Vision-yaw from the PnP gate normal proved too noisy to be a rate
        # source (planar-ambiguity flips + random-walk drift that leaks into
        # the velocity transport as phantom lateral motion) — OFF by default,
        # kept param-gated for A/B experiments. The default yaw source when
        # the z-gyro is dead is the COMMANDED rate: phase2k data shows the
        # sim executes yaw commands ~1:1 (pixel-sweep slope 68 px/(rad/s)
        # over ~0.2s windows = fx*dt at gain 1.0).
        self.vision_yaw = bool(params.get("estimation.vision_yaw", default=False))
        # R10: the sim's gyro z-axis is hard-pinned. When flagged dead, the
        # yaw channel is reconstructed instead of read: fresh vision-yaw when
        # a gate is tracked, otherwise the COMMANDED yaw rate (the sim's rate
        # loop executes commands faithfully, tau ~60ms). Without this, any
        # vision dropout leaves yaw fully unobserved — the yaw servo then
        # integrates open-loop and the drone spirals away from the gate.
        self.gyro_z_dead = bool(params.get("estimation.gyro_z_dead", default=True))
        # Reject vision-velocity pairs faster than a racing drone can go:
        # a bad PnP fix or an attitude glitch otherwise injects hundreds of
        # km/h into the blend (phase2l diverged to 454 km/h estimated).
        self.vision_vel_max = float(params.get("estimation.vision_vel_max_mps",
                                               default=15.0))
        self.max_age_s = float(params.get("estimation.gate_rel_max_age_s"))
        self._cam_fov_deg = float(params.get("perception.camera.fov_deg",
                                             default=90.0))

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
        # derivative uses a ~0.3-0.6s baseline instead of consecutive frames
        # (derivative noise scales with 1/baseline).
        from collections import deque
        self._fix_history: deque = deque(maxlen=64)   # (ts_ns, t_body, n_body, q)
        # Attitude history so vision fixes use the attitude AT THE FRAME
        # TIMESTAMP, not at processing time: with ~30ms vision latency a fast
        # pitch transient (takeoff, braking) otherwise puts degrees of
        # rotation error into the transport, which at a 5m gate distance
        # fabricates several m/s of phantom velocity (measured on the mock:
        # est vz +1.5 while truth was -3.2 during the brake).
        self._att_history: deque = deque(maxlen=256)  # (ts_ns, q) at IMU rate
        self._vision_yaw_rate = 0.0
        self._vision_yaw_ts_ns = 0
        self._cmd_yaw_rate = 0.0
        self._now_ns = 0
        # Frame timestamps and IMU timestamps live in DIFFERENT clock domains
        # on the real sim (frames: unix epoch; MAVLink IMU: sim boot time —
        # phase2k logs). Comparing them raw makes gate_rel age clamp to zero
        # (a stale fix never expires) and breaks the frame-time attitude
        # lookup. Track the offset (EMA over fixes) and rebase; when the two
        # clocks agree within 5s (mock), timestamps pass through untouched.
        self._det_offset_ns: float | None = None

    def set_level_reference(self, roll: float, pitch: float) -> None:
        """Resting attitude from the pre-arm accel (IMU mount tilt)."""
        self._level_roll = roll
        self._level_pitch = pitch

    def set_gyro_bias(self, bias: np.ndarray) -> None:
        """Gyro bias measured while stationary on the ground (pre-arm)."""
        self._gyro_bias = np.asarray(bias, dtype=np.float64)

    def set_cmd_yaw_rate(self, yaw_rate: float) -> None:
        """Commanded yaw rate — the yaw prediction input when gyro z is dead.
        Assumes the backend forwards it unsigned (rate_sign_yaw=+1)."""
        self._cmd_yaw_rate = float(yaw_rate)

    def reset(self) -> None:
        self.attitude.reset()
        self.v_world = np.zeros(3)
        self._omega = np.zeros(3)
        self._last_imu_ts_ns = None
        self._gate_rel = None
        self._gate_rel_ts_ns = None
        self._gate_center_px = None
        self._fix_history.clear()
        self._att_history.clear()
        self._vision_yaw_rate = 0.0
        self._vision_yaw_ts_ns = 0

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
        vision_yaw_fresh = (self.vision_yaw
                            and (imu.ts_ns - self._vision_yaw_ts_ns) < 0.5e9)
        if not vision_yaw_fresh:
            # No vision to correct against: relax the yaw-rate estimate
            # toward the feed-forward prior (commanded rate when the z-gyro
            # is dead, zero correction when it is healthy).
            prior = self._cmd_yaw_rate if self.gyro_z_dead else 0.0
            self._vision_yaw_rate += min(1.0, dt / 0.3) * (prior - self._vision_yaw_rate)
        if self.gyro_z_dead:
            # Reconstructed yaw channel (bias subtraction already zeroed the
            # pinned value).
            gyro = gyro.copy()
            gyro[2] = self._vision_yaw_rate
        elif self.vision_yaw:
            # Healthy gyro: vision-yaw is a residual correction (~0 normally).
            gyro = gyro.copy()
            gyro[2] += self._vision_yaw_rate
        q = self.attitude.update(gyro, imu.accel, dt)
        self._omega = gyro
        self._att_history.append((imu.ts_ns, q.copy()))

        # Specific force f = a - g  =>  a_world = R*f + g_world.
        a_world = quat_rotate(q, imu.accel) + np.array([0.0, 0.0, 9.80665])
        self.v_world = self.v_world + a_world * dt
        # Leak toward zero: bounds unavoidable accelerometer-integration drift.
        self.v_world *= max(0.0, 1.0 - self.vel_leak * dt)

        # Dead-reckon gate_rel between vision fixes. The gate is static, so
        # in camera coordinates:  dt/dt = -(omega x t) - v,  dn/dt = -(omega x n).
        # (cam and body differ by a fixed permutation, so body kinematics
        # hold with vectors expressed in camera axes.)
        if self._gate_rel is not None:
            omega_cam = body_to_cam(gyro)
            v_cam = body_to_cam(quat_rotate_inv(q, self.v_world))
            t = self._gate_rel.t - (np.cross(omega_cam, self._gate_rel.t) + v_cam) * dt
            n = self._gate_rel.normal - np.cross(omega_cam, self._gate_rel.normal) * dt
            norm = np.linalg.norm(n)
            if norm > 1e-9:
                n = n / norm
            self._gate_rel = RelPose(t=t, normal=n)
            # Reproject so yaw centering stays live through dropouts.
            if self._image_size is not None and t[2] > 0.05:
                w, h = self._image_size
                fx = (w / 2.0) / math.tan(math.radians(self._cam_fov_deg) / 2.0)
                self._gate_center_px = (w / 2.0 + fx * t[0] / t[2],
                                        h / 2.0 + fx * t[1] / t[2])

    # --------------------------------------------------------------- vision

    def _rebase_det_ts(self, det_ts_ns: int) -> int:
        """Frame timestamp expressed on the IMU timeline (see _det_offset_ns).

        The EMA offset absorbs the clock-domain gap minus average pipeline
        latency; residual error is latency jitter (~ms), good enough for the
        age check and the attitude lookup.
        """
        d = det_ts_ns - self._now_ns
        if abs(d) < 5e9:
            return det_ts_ns          # same clock domain: exact, keep it
        if self._det_offset_ns is None:
            self._det_offset_ns = float(d)
        else:
            self._det_offset_ns += 0.05 * (d - self._det_offset_ns)
        return int(det_ts_ns - self._det_offset_ns)

    def _attitude_at(self, ts_ns: int) -> np.ndarray:
        """Attitude at a (past) frame timestamp, from the IMU-rate history."""
        best = None
        for h_ts, h_q in reversed(self._att_history):
            if best is None or abs(h_ts - ts_ns) < abs(best[0] - ts_ns):
                best = (h_ts, h_q)
            if h_ts <= ts_ns:
                break   # history is time-ordered; no closer entry further back
        if best is None:
            return self.attitude.q.copy()
        return best[1]

    def update_vision(self, det: GateDetection) -> None:
        self._gate_center_px = det.center_px
        self._image_size = det.image_size
        if det.rel_pose is not None:
            # Vision velocity: the gate is static, so the derivative of its
            # relative position IS our velocity. This is the only strong
            # velocity reference we have (accel integration drifts, and the
            # attitude filter is unreliable during coordinated acceleration).
            # RELATIVE-transport differentiation: bring the old fix into the
            # current body frame via the RELATIVE rotation q_new^-1 * q_old
            # (absolute attitude error cancels — rotating a 10m gate vector
            # through an absolute attitude with a small error fabricates
            # meters of motion, which is what diverged both the mock and the
            # phase2l flight), then differentiate in the body frame.
            t_body = cam_to_body(det.rel_pose.t)
            n_body = cam_to_body(det.rel_pose.normal)
            q_now = self._attitude_at(self._rebase_det_ts(det.ts_ns))
            baseline = None
            for ts, t_old, n_old, q_old in self._fix_history:
                if 0.25e9 <= det.ts_ns - ts <= 0.6e9:
                    baseline = (ts, t_old, n_old, q_old)
                    break   # oldest fix inside the window
            # Skip the velocity update while rotating fast: transport error
            # (attitude error x gate lever arm) dominates the measurement in
            # exactly those samples, and blending them in is what kicked off
            # the takeoff vy/roll oscillation.
            if float(np.hypot(self._omega[0], self._omega[1])) > 1.0:
                baseline = None
            if baseline is not None:
                ts_old, t_old, n_old, q_old = baseline
                dt = (det.ts_ns - ts_old) / 1e9
                t_old_now = quat_rotate_inv(q_now, quat_rotate(q_old, t_old))
                v_body_meas = -(t_body - t_old_now) / dt
                if float(np.linalg.norm(v_body_meas)) <= self.vision_vel_max:
                    v_world_meas = quat_rotate(q_now, v_body_meas)
                    k = self.vision_vel_blend
                    self.v_world = (1.0 - k) * self.v_world + k * v_world_meas
                # Vision-yaw: residual rotation of the static gate's normal
                # AFTER the transport (which already contains every rate we
                # injected) is yaw the integrated attitude missed over the
                # window — an INCREMENTAL correction on the current estimate,
                # never an absolute rate (setting instead of adding turned
                # the loop into a bang-bang oscillator: est_wz alternated
                # -2/0 while the true rate was ~0).
                n_old_now = quat_rotate_inv(q_now, quat_rotate(q_old, n_old))
                phi_new = np.arctan2(n_body[1], n_body[0])
                phi_old = np.arctan2(n_old_now[1], n_old_now[0])
                dphi = (phi_new - phi_old + np.pi) % (2 * np.pi) - np.pi
                # Planar-PnP ambiguity flips jump the normal azimuth by
                # ~2x the viewing angle — far more than any real missed yaw
                # over a <=0.45s window. Reject instead of ingesting.
                if abs(dphi) < 0.5:
                    # Consecutive fixes share overlapping windows: scale the
                    # per-fix gain by fix spacing so one window's residual is
                    # absorbed once, not once per fix.
                    dt_fix = (det.ts_ns - self._fix_history[-1][0]) / 1e9 \
                        if self._fix_history else dt
                    k = min(1.0, 2.0 * max(dt_fix, 1e-3) / dt)
                    self._vision_yaw_rate = float(np.clip(
                        self._vision_yaw_rate + k * (-dphi / dt), -1.5, 1.5))
                    self._vision_yaw_ts_ns = self._rebase_det_ts(det.ts_ns)
            self._fix_history.append((det.ts_ns, t_body, n_body, q_now))
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
            self._gate_rel_ts_ns = self._rebase_det_ts(det.ts_ns)

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
