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
        self.center_gain = float(p.get("planner.approach.center_gain"))
        self.alt_gain = float(p.get("planner.approach.alt_gain", default=0.8))
        self.aim_up_m = float(p.get("planner.approach.aim_up_m", default=0.25))
        self.aim_up_floor_m = float(p.get("planner.approach.aim_up_floor_m",
                                          default=0.3))
        self.commit_distance = float(p.get("planner.commit.distance_m"))
        self.commit_duration_s = float(p.get("planner.commit.duration_s"))
        self.commit_speed = float(p.get("planner.commit.speed_mps"))
        # Miss-recovery (phase3g): per-attempt pass probability is finally
        # meaningful, so multiply attempts instead of demanding a perfect
        # first arrow. If the opening escapes the corridor mid-commit,
        # abort and RETREAT (backward, altitude held) until the gate is
        # back in view at a sane range — instead of clipping the frame and
        # flailing into walls, which is how most R2 flights actually died.
        self.abort_offset_m = float(p.get("planner.commit.abort_offset_m",
                                          default=0.45))
        self.retreat_speed = float(p.get("planner.retreat.speed_mps", default=1.2))
        self.retreat_s = float(p.get("planner.retreat.duration_s", default=2.0))
        self.retreat_enabled = bool(p.get("planner.retreat.enabled", default=True))
        self.recover_brake_s = float(p.get("planner.recover.brake_s"))
        self.force_hover = bool(p.get("planner.force_hover", default=False))

        self._commit_until_ns: int | None = None
        self._commit_v_body: np.ndarray | None = None
        self._recover_until_ns: int | None = None
        self._retreat_until_ns: int | None = None
        self._abort_breach = 0
        self._last_seen_side = 1.0   # search toward the last known bearing

    def reset(self) -> None:
        self._commit_until_ns = None
        self._commit_v_body = None
        self._recover_until_ns = None
        self._retreat_until_ns = None
        self._abort_breach = 0
        self._last_seen_side = 1.0

    # -- external events ------------------------------------------------------

    def on_gate_passed(self) -> None:
        self._commit_until_ns = None
        self._commit_v_body = None
        self._retreat_until_ns = None

    def on_collision(self, now_ns: int) -> None:
        self._recover_until_ns = now_ns + int(self.recover_brake_s * 1e9)
        self._commit_until_ns = None
        self._commit_v_body = None
        self._retreat_until_ns = None

    def _aim_up(self, dist: float) -> float:
        """Aim-above-center insurance, tapered toward a FLOOR near the gate.

        Far out it counters the systematic altitude sag. It used to taper to
        zero at the gate — phase3h then crossed consistently LOW by
        0.2-0.45m (F1: dead-centered laterally, caught the bottom bar). The
        floor keeps the crossing ~0.3m above center: safely inside the
        +/-0.8m opening, clear of the measured low bias.
        """
        floor = float(min(self.aim_up_m, self.aim_up_floor_m))
        return max(floor, self.aim_up_m * float(np.clip(dist / 4.0, 0.0, 1.0)))

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

        # -- retreat: back away after a blown attempt until the gate is in
        # view again at a sane range, then re-approach (multiply attempts).
        if self._retreat_until_ns is not None:
            if now_ns < self._retreat_until_ns:
                return Setpoint(phase="retreat",
                                v_body=np.array([-self.retreat_speed, 0.0, 0.0]),
                                yaw_rate=0.0)
            self._retreat_until_ns = None

        # -- commit: LIVE-STEERED through-gate window (phase3b flight 1
        # clipped the top bar because the vector was locked 0.5s/1.5m before
        # the crossing while fresh fixes still existed; gate_rel is
        # dead-reckoned through dropouts, so keep steering on it and only
        # fall back to the last vector once the gate is truly gone/behind).
        if self._commit_until_ns is not None:
            if now_ns < self._commit_until_ns and self._commit_v_body is not None:
                gate = state.gate_rel
                # Geometric termination: the dead-reckoned gate went well
                # BEHIND us — the attempt is decided either way, and only
                # the sim's pass event says which. Do not let the wall-clock
                # window cut a good crossing short (phase3h F3: retreat
                # fired 0.21m from a dead-centered plane because the 1.2s
                # default window expired just before the crossing).
                if gate is not None and gate.t[2] < -0.4:
                    self._commit_until_ns = None
                    self._commit_v_body = None
                    if self.retreat_enabled:
                        self._retreat_until_ns = now_ns + int(self.retreat_s * 1e9)
                        return Setpoint(phase="retreat",
                                        v_body=np.array([-self.retreat_speed, 0.0, 0.0]),
                                        yaw_rate=0.0)
                elif gate is not None and gate.t[2] > 0.3:
                    d_body = ap.cam_to_body(gate.t)
                    dist = float(np.linalg.norm(d_body))
                    au = self._aim_up(dist)
                    # Abort the attempt if the opening is escaping the
                    # corridor — a frame clip is now certain; retreating
                    # for another pass beats plowing into the bar. Debounced:
                    # a single noisy blend sample must not kill a good run.
                    off = float(np.hypot(d_body[1], d_body[2] - au))
                    if dist < 1.5 and off > self.abort_offset_m:
                        self._abort_breach += 1
                    else:
                        self._abort_breach = 0
                    if self._abort_breach >= 4 and self.retreat_enabled:
                        self._abort_breach = 0
                        self._commit_until_ns = None
                        self._commit_v_body = None
                        self._retreat_until_ns = now_ns + int(self.retreat_s * 1e9)
                        return Setpoint(phase="retreat",
                                        v_body=np.array([-self.retreat_speed, 0.0, 0.0]),
                                        yaw_rate=0.0)
                    direction, dist = ap.gate_direction_body(gate, au)
                    extra = ap.crosstrack_velocity(gate, au, self.center_gain)
                    extra[2] += ap.altitude_hold_velocity(
                        gate, state.q_att, au, self.alt_gain)
                    self._commit_v_body = direction * self.commit_speed + extra
                return Setpoint(phase="commit", v_body=self._commit_v_body, yaw_rate=0.0)
            # Window expired without a gate-passed event: we are past the
            # plane outside the opening (or stalled) — back off and retry
            # instead of the blind flail that ended most R2 flights.
            self._commit_until_ns = None
            self._commit_v_body = None
            if self.retreat_enabled:
                self._retreat_until_ns = now_ns + int(self.retreat_s * 1e9)
                return Setpoint(phase="retreat",
                                v_body=np.array([-self.retreat_speed, 0.0, 0.0]),
                                yaw_rate=0.0)

        gate = state.gate_rel
        if gate is None:
            # -- search: spin toward the side the gate was last seen on.
            return Setpoint(
                phase="search",
                v_body=np.array([0.0, 0.0, -self.search_climb]),
                yaw_rate=self.search_yaw_rate * self._last_seen_side,
            )

        # -- approach
        dist = float(np.linalg.norm(gate.t))
        au = self._aim_up(dist)
        direction, dist = ap.gate_direction_body(gate, au)
        crosstrack = ap.crosstrack_velocity(gate, au, self.center_gain)
        crosstrack[2] += ap.altitude_hold_velocity(
            gate, state.q_att, au, self.alt_gain)
        if abs(direction[1]) > 0.05:
            self._last_seen_side = 1.0 if direction[1] > 0 else -1.0
        if dist <= self.commit_distance:
            # Enter the through-gate window.
            v = direction * self.commit_speed + crosstrack
            self._commit_v_body = v
            self._commit_until_ns = now_ns + int(self.commit_duration_s * 1e9)
            return Setpoint(phase="commit", v_body=v, yaw_rate=0.0)

        speed = ap.approach_speed(dist, self.speed_far, self.speed_near, self.near_distance)
        yaw_rate = 0.0
        if state.gate_center_px is not None and state.image_size is not None:
            yaw_rate = ap.yaw_rate_to_center(
                state.gate_center_px, state.image_size, self.yaw_center_gain
            )
        return Setpoint(phase="approach", v_body=direction * speed + crosstrack,
                        yaw_rate=yaw_rate)
