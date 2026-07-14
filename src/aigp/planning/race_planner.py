"""Race planner: behavior selection and setpoint generation.

Behaviors within a flight (the supervisor decides the outer mode):

    search   - no fresh gate fix: slow yaw spin until the detector fires
    approach - fly toward the gate center, speed shaped by distance,
               yaw to keep the gate centered in the image
    commit   - inside the blind window (gate about to leave the FOV):
               lock the through-gate velocity vector for commit.duration_s;
               the pass is confirmed externally by active_gate_index
    recover  - after a collision: brake to hover, then re-search

Everything numeric here is a ParamSet entry — this is the main surface the
flight-to-flight tuner optimizes.

TODO(phase-4): racing-line shaping between consecutive gates (approach offset
toward the NEXT gate instead of stopping the optimization at gate center).
"""
from __future__ import annotations

import numpy as np

from aigp.core.messages import RaceStatus, Setpoint, StateEstimate
from aigp.core.params import ParamSet
from aigp.planning import approach as ap


class RacePlanner:
    def __init__(self, params: ParamSet) -> None:
        p = params
        self.takeoff_climb = float(p.get("planner.takeoff.climb_mps"))
        self.search_yaw_rate = float(p.get("planner.search.yaw_rate_rps"))
        self.search_climb = float(p.get("planner.search.climb_mps"))
        self.speed_far = float(p.get("planner.approach.speed_far_mps"))
        self.speed_near = float(p.get("planner.approach.speed_near_mps"))
        self.near_distance = float(p.get("planner.approach.near_distance_m"))
        self.yaw_center_gain = float(p.get("planner.approach.yaw_center_gain"))
        self.commit_distance = float(p.get("planner.commit.distance_m"))
        self.commit_duration_s = float(p.get("planner.commit.duration_s"))
        self.commit_speed = float(p.get("planner.commit.speed_mps"))
        self.recover_brake_s = float(p.get("planner.recover.brake_s"))
        self.force_hover = bool(p.get("planner.force_hover", default=False))

        self._commit_until_ns: int | None = None
        self._commit_v_body: np.ndarray | None = None
        self._recover_until_ns: int | None = None

    def reset(self) -> None:
        self._commit_until_ns = None
        self._commit_v_body = None
        self._recover_until_ns = None

    # -- external events ------------------------------------------------------

    def on_gate_passed(self) -> None:
        self._commit_until_ns = None
        self._commit_v_body = None

    def on_collision(self, now_ns: int) -> None:
        self._recover_until_ns = now_ns + int(self.recover_brake_s * 1e9)
        self._commit_until_ns = None
        self._commit_v_body = None

    # -- planning --------------------------------------------------------------

    def plan(self, now_ns: int, mode: str, state: StateEstimate,
             race: RaceStatus | None) -> Setpoint:
        if mode == "takeoff":
            return Setpoint(phase="takeoff",
                            v_body=np.array([0.0, 0.0, -self.takeoff_climb]),
                            yaw_rate=0.0)
        if mode != "race" or self.force_hover:
            # force_hover (planner.force_hover, via --patch) isolates pure
            # stabilization: no search spin, no approach — hold still.
            return Setpoint(phase="hover", v_body=np.zeros(3), yaw_rate=0.0)

        # -- recover: brake after a collision
        if self._recover_until_ns is not None:
            if now_ns < self._recover_until_ns:
                return Setpoint(phase="recover", v_body=np.zeros(3), yaw_rate=0.0)
            self._recover_until_ns = None

        # -- commit: blind-window lock
        if self._commit_until_ns is not None:
            if now_ns < self._commit_until_ns and self._commit_v_body is not None:
                return Setpoint(phase="commit", v_body=self._commit_v_body, yaw_rate=0.0)
            self._commit_until_ns = None
            self._commit_v_body = None

        gate = state.gate_rel
        if gate is None:
            # -- search
            return Setpoint(
                phase="search",
                v_body=np.array([0.0, 0.0, -self.search_climb]),
                yaw_rate=self.search_yaw_rate,
            )

        # -- approach
        direction, dist = ap.gate_direction_body(gate)
        if dist <= self.commit_distance:
            # Enter the blind window: lock the through-gate vector.
            v = direction * self.commit_speed
            self._commit_v_body = v
            self._commit_until_ns = now_ns + int(self.commit_duration_s * 1e9)
            return Setpoint(phase="commit", v_body=v, yaw_rate=0.0)

        speed = ap.approach_speed(dist, self.speed_far, self.speed_near, self.near_distance)
        yaw_rate = 0.0
        if state.gate_center_px is not None and state.image_size is not None:
            yaw_rate = ap.yaw_rate_to_center(
                state.gate_center_px, state.image_size, self.yaw_center_gain
            )
        return Setpoint(phase="approach", v_body=direction * speed, yaw_rate=yaw_rate)
