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
                                          default=0.0))
        # The final stretch can go blind and the drone historically sank
        # through it (phase3h/3i). But the F1 overfly showed the inverse
        # failure: sink insurance ARMING mid-coast on top of an altitude
        # hold already climbing = double compensation, +1m HIGH. The rule
        # that deletes the class (think-tank adv.3 T3): NO compensation
        # may arm during blind coast — the arming decision is taken ONCE
        # at gap entry from the last measured state, which can veto it,
        # and then holds frozen. Retreat keeps its own (phase4a
        # ground-scrape) compensation separately.
        self.blind_climb_bias = float(p.get("planner.commit.blind_climb_bias_mps",
                                            default=0.1))
        self.blind_age_s = float(p.get("planner.commit.blind_age_s", default=0.3))
        self.retreat_climb_bias = float(p.get("planner.retreat.climb_bias_mps",
                                              default=0.2))
        self.commit_distance = float(p.get("planner.commit.distance_m"))
        self.commit_duration_s = float(p.get("planner.commit.duration_s"))
        self.commit_speed = float(p.get("planner.commit.speed_mps"))
        # Mid-commit relock guard (phase6a dash-F2): after slipping past
        # gate 1 the estimator legitimately relocked the NEXT gate at 7m
        # while the commit kept flying on a timer sized for THIS gate. A
        # believed-z jump UP of this magnitude cannot be the target we
        # were 1-2m from — the attempt is over either way.
        self.relock_jump_m = float(p.get("planner.commit.relock_jump_m",
                                         default=2.0))
        # Vertical pre-alignment gate on commit entry: the dash may not
        # start while the TRUE height error exceeds align.max_dz_m —
        # close it first (climb/descend, creeping forward), then commit
        # level. The in-commit hold (0.8 m/s cap) can only trim small
        # residuals within the window. (Phase6b note: the original
        # "3.11m opening" that motivated this was the rest-tilt phantom;
        # the true opening center is ~1.3m above the pad camera and the
        # gate matters mainly for overshoot/undershoot after takeoff.)
        self.align_dz_max = float(p.get("planner.align.max_dz_m", default=0.5))
        self.align_forward = float(p.get("planner.align.forward_mps",
                                         default=0.4))
        self.align_climb_gain = float(p.get("planner.align.climb_gain",
                                            default=1.0))
        self.align_climb_cap = float(p.get("planner.align.climb_cap_mps",
                                           default=1.2))
        self.align_max_s = float(p.get("planner.align.max_s", default=4.0))
        # Miss-recovery (phase3g): per-attempt pass probability is finally
        # meaningful, so multiply attempts instead of demanding a perfect
        # first arrow. If the opening escapes the corridor mid-commit,
        # abort and RETREAT (backward, altitude held) until the gate is
        # back in view at a sane range — instead of clipping the frame and
        # flailing into walls, which is how most R2 flights actually died.
        self.abort_offset_m = float(p.get("planner.commit.abort_offset_m",
                                          default=0.45))
        # No-retreat braking band (phase6b F2): a retreat commanded at
        # 1.31m with 2.5 m/s of forward momentum cannot reverse before
        # the plane — the drone pitched back and coasted INTO the gate
        # (clip, impulse 4.3) on an arrival that was actually centered.
        # Inside this distance the attempt is committed: carry through.
        self.abort_min_dist_m = float(p.get("planner.commit.abort_min_dist_m",
                                            default=1.2))
        # Post-miss reacquisition discipline (phase6b F1: after the blown
        # attempt the estimator relocked a believed 40m target and the
        # planner chased it across the obstacle field into three hits).
        self.reacquire_window_s = float(p.get(
            "planner.approach.reacquire_window_s", default=6.0))
        self.reacquire_max_m = float(p.get(
            "planner.approach.reacquire_max_m", default=9.0))
        # Camera-on-target yaw during commit/retreat (phase5 frames: with
        # yaw pinned at 0 the lateral strafe walks the gate out the side
        # of the fixed camera's FOV — edge_clip/no_red at 3-5m).
        self.commit_yaw_gain = float(p.get("planner.commit.yaw_track_gain",
                                           default=1.2))
        self.retreat_speed = float(p.get("planner.retreat.speed_mps", default=1.2))
        self.retreat_s = float(p.get("planner.retreat.duration_s", default=2.0))
        self.retreat_enabled = bool(p.get("planner.retreat.enabled", default=True))
        self.recover_brake_s = float(p.get("planner.recover.brake_s"))
        self.force_hover = bool(p.get("planner.force_hover", default=False))

        self._commit_until_ns: int | None = None
        self._commit_v_body: np.ndarray | None = None
        self._commit_prev_z: float | None = None
        self._recover_until_ns: int | None = None
        self._retreat_until_ns: int | None = None
        self._align_until_ns: int | None = None
        self._abort_breach = 0
        self._last_seen_side = 1.0   # search toward the last known bearing
        self._gap_bias: float | None = None   # frozen at gap entry (no-arm rule)
        self._reacquire_until_ns: int | None = None   # post-miss range guard

    def reset(self) -> None:
        self._commit_until_ns = None
        self._commit_v_body = None
        self._commit_prev_z = None
        self._recover_until_ns = None
        self._retreat_until_ns = None
        self._align_until_ns = None
        self._abort_breach = 0
        self._last_seen_side = 1.0
        self._gap_bias = None
        self._reacquire_until_ns = None

    def _note_attempt_failed(self, now_ns: int) -> None:
        """A commit ended without a pass event: arm the post-miss
        reacquisition guard so the next approach stays on THIS gate's
        neighborhood instead of chasing a far relock into steel."""
        self._reacquire_until_ns = now_ns + int(self.reacquire_window_s * 1e9)

    # -- external events ------------------------------------------------------

    def on_gate_passed(self) -> None:
        self._commit_until_ns = None
        self._commit_v_body = None
        self._commit_prev_z = None
        self._retreat_until_ns = None
        self._align_until_ns = None
        self._gap_bias = None
        self._reacquire_until_ns = None

    def on_collision(self, now_ns: int) -> None:
        self._recover_until_ns = now_ns + int(self.recover_brake_s * 1e9)
        self._commit_until_ns = None
        self._commit_v_body = None
        self._commit_prev_z = None
        self._retreat_until_ns = None
        self._align_until_ns = None

    def _retreat_setpoint(self, state: StateEstimate,
                          climb_bias: float = 0.0) -> Setpoint:
        """Back away for another attempt, camera held on the gate.

        Keeping the nose turned onto the (dead-reckoned) gate means
        re-acquisition happens on THIS gate — phase4c died relocking onto
        far gates after a blown attempt and chasing them into steel.
        """
        yaw = 0.0
        if state.gate_rel is not None:
            yaw = ap.yaw_rate_to_bearing(state.gate_rel, self.commit_yaw_gain)
        return Setpoint(phase="retreat",
                        v_body=np.array([-self.retreat_speed, 0.0, -climb_bias]),
                        yaw_rate=yaw)

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
                # Retreat is semi-blind (no altitude anchor): phase4a
                # flights bled height across retry cycles — 8-35 ground
                # scrapes per flight — until a hard hit ended them.
                return self._retreat_setpoint(state, self.retreat_climb_bias)
            self._retreat_until_ns = None

        # -- commit: LIVE-STEERED through-gate window (phase3b flight 1
        # clipped the top bar because the vector was locked 0.5s/1.5m before
        # the crossing while fresh fixes still existed; gate_rel is
        # dead-reckoned through dropouts, so keep steering on it and only
        # fall back to the last vector once the gate is truly gone/behind).
        if self._commit_until_ns is not None:
            if now_ns < self._commit_until_ns and self._commit_v_body is not None:
                gate = state.gate_rel
                # Relock guard (phase6a dash-F2): the believed target
                # jumped several meters AWAY mid-commit — that is the
                # estimator legitimately relocking the NEXT gate after we
                # slipped past this one outside the opening. Continuing
                # the dash on a timer sized for the old range chases the
                # far gate at commit speed; end the attempt and retreat.
                if (gate is not None and self._commit_prev_z is not None
                        and float(gate.t[2]) > self._commit_prev_z
                        + self.relock_jump_m):
                    self._commit_until_ns = None
                    self._commit_v_body = None
                    self._commit_prev_z = None
                    self._note_attempt_failed(now_ns)
                    if self.retreat_enabled:
                        self._retreat_until_ns = now_ns + int(self.retreat_s * 1e9)
                        return self._retreat_setpoint(state)
                    return Setpoint(phase="search",
                                    v_body=np.zeros(3),
                                    yaw_rate=self.search_yaw_rate
                                    * self._last_seen_side)
                if gate is not None:
                    self._commit_prev_z = float(gate.t[2])
                # Geometric termination: the dead-reckoned gate went well
                # BEHIND us — the attempt is decided either way, and only
                # the sim's pass event says which. Do not let the wall-clock
                # window cut a good crossing short (phase3h F3: retreat
                # fired 0.21m from a dead-centered plane because the 1.2s
                # default window expired just before the crossing).
                if gate is not None and gate.t[2] < -0.4:
                    self._commit_until_ns = None
                    self._commit_v_body = None
                    self._commit_prev_z = None
                    self._note_attempt_failed(now_ns)
                    if self.retreat_enabled:
                        self._retreat_until_ns = now_ns + int(self.retreat_s * 1e9)
                        return self._retreat_setpoint(state)
                elif gate is not None and gate.t[2] > 0.3:
                    d_body = ap.cam_to_body(gate.t)
                    dist = float(np.linalg.norm(d_body))
                    au = self._aim_up(dist)
                    # Abort the attempt if the opening is escaping the
                    # corridor — a frame clip is now certain; retreating
                    # for another pass beats plowing into the bar. Debounced:
                    # a single noisy blend sample must not kill a good run.
                    # Measured against TRUE vertical (phase6b F2: the
                    # rest-tilt phantom pushed a centered arrival over the
                    # threshold) and only OUTSIDE the braking band — a
                    # retreat inside abort_min_dist_m cannot reverse the
                    # momentum and coasts into the gate instead.
                    tdz = ap.true_world_dz(gate, state.q_att,
                                           state.level_roll,
                                           state.level_pitch)
                    off = float(np.hypot(d_body[1], tdz - au))
                    if (self.abort_min_dist_m < dist < 1.5
                            and off > self.abort_offset_m):
                        self._abort_breach += 1
                    else:
                        self._abort_breach = 0
                    if self._abort_breach >= 4 and self.retreat_enabled:
                        self._abort_breach = 0
                        self._commit_until_ns = None
                        self._commit_v_body = None
                        self._commit_prev_z = None
                        self._note_attempt_failed(now_ns)
                        self._retreat_until_ns = now_ns + int(self.retreat_s * 1e9)
                        return self._retreat_setpoint(state)
                    direction, dist = ap.gate_direction_body(gate, au)
                    extra = ap.crosstrack_velocity(gate, au, self.center_gain)
                    extra[2] += ap.altitude_hold_velocity(
                        gate, state.q_att, au, self.alt_gain,
                        level_roll=state.level_roll,
                        level_pitch=state.level_pitch)
                    # No-arm rule: the sink insurance is decided ONCE, at
                    # gap entry, by the state the last fixes left behind —
                    # if the altitude hold is already commanding a climb
                    # there, insurance is VETOED (F1's +1m overfly was
                    # exactly hold-climb + insurance-climb stacking blind).
                    if state.gate_rel_age_s <= self.blind_age_s:
                        self._gap_bias = None            # seeing: disarmed
                    elif self._gap_bias is None:
                        # TOP-UP, not binary veto (phase5c: the binary
                        # veto killed insurance whenever the hold climbed
                        # at all, and all three flights arrived LOW):
                        # insurance only fills the gap between the hold's
                        # climb at entry and the insured sink rate. F1's
                        # overfly case still gets zero (hold -0.72 >> 0.1).
                        climb = max(0.0, -float(extra[2]))   # NED: -z up
                        self._gap_bias = max(0.0, self.blind_climb_bias - climb)
                    if self._gap_bias:
                        extra[2] -= self._gap_bias
                    self._commit_v_body = direction * self.commit_speed + extra
                yaw = 0.0
                if gate is not None and gate.t[2] > 0.3:
                    yaw = ap.yaw_rate_to_bearing(gate, self.commit_yaw_gain)
                return Setpoint(phase="commit", v_body=self._commit_v_body,
                                yaw_rate=yaw)
            # Window expired without a gate-passed event: we are past the
            # plane outside the opening (or stalled) — back off and retry
            # instead of the blind flail that ended most R2 flights.
            self._commit_until_ns = None
            self._commit_v_body = None
            self._commit_prev_z = None
            self._note_attempt_failed(now_ns)
            if self.retreat_enabled:
                self._retreat_until_ns = now_ns + int(self.retreat_s * 1e9)
                return self._retreat_setpoint(state)

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
        # Post-miss reacquisition guard: right after a blown attempt, a
        # "fresh" far target is almost certainly a relock onto the NEXT
        # gate (or fiction) seen while tumbling/retreating — phase6b F1
        # chased a believed 40m gate across the obstacle field into three
        # env hits. Stay searching until a target in THIS gate's
        # neighborhood reappears or the window expires.
        if (self._reacquire_until_ns is not None
                and now_ns < self._reacquire_until_ns
                and dist > self.reacquire_max_m):
            return Setpoint(
                phase="search",
                v_body=np.array([0.0, 0.0, -self.search_climb]),
                yaw_rate=self.search_yaw_rate * self._last_seen_side,
            )
        au = self._aim_up(dist)
        direction, dist = ap.gate_direction_body(gate, au)
        crosstrack = ap.crosstrack_velocity(gate, au, self.center_gain)
        crosstrack[2] += ap.altitude_hold_velocity(
            gate, state.q_att, au, self.alt_gain,
            level_roll=state.level_roll, level_pitch=state.level_pitch)
        if abs(direction[1]) > 0.05:
            self._last_seen_side = 1.0 if direction[1] > 0 else -1.0
        if dist <= self.commit_distance:
            # Vertical pre-alignment (phase6a keystone): the opening
            # center sits 3.11m above the pad camera while takeoff tops
            # out ~1.6m lower, and the in-commit hold (0.8 m/s cap over
            # the window) cannot close that — dash-F2 reached R=0.88m
            # still 0.61m LOW and never registered the pass. Close the
            # height gap FIRST, creeping forward, then dash level.
            world_dz = ap.true_world_dz(gate, state.q_att,
                                        state.level_roll, state.level_pitch)
            misaligned = abs(world_dz - au) > self.align_dz_max
            if misaligned and state.gate_rel_age_s <= 0.5:
                if self._align_until_ns is None:
                    self._align_until_ns = now_ns + int(self.align_max_s * 1e9)
                if now_ns < self._align_until_ns:
                    vz = float(np.clip(
                        self.align_climb_gain * (world_dz - au),
                        -self.align_climb_cap, self.align_climb_cap))
                    # crosstrack[2] already carries the (0.8-capped) hold
                    # term — the align climb REPLACES it (single owner),
                    # keeping only the lateral nulling component.
                    v = np.array([self.align_forward,
                                  float(crosstrack[1]), vz])
                    yaw = ap.yaw_rate_to_bearing(gate, self.commit_yaw_gain)
                    return Setpoint(phase="align", v_body=v, yaw_rate=yaw)
                # Budget spent and still misaligned: commit anyway — a
                # capped attempt beats hovering out the flight clock.
            self._align_until_ns = None
            # Enter the through-gate window, sized by PHYSICS: the timer
            # must outlive the crossing at commit speed from THIS entry
            # range (phase6a dash-F1: the fixed 2.5s window expired at
            # believed z=+1.09m and retreat yanked a centered dash back).
            v = direction * self.commit_speed + crosstrack
            self._commit_v_body = v
            self._commit_prev_z = float(gate.t[2])
            duration_s = max(self.commit_duration_s,
                             dist / max(self.commit_speed, 0.1) + 1.0)
            self._commit_until_ns = now_ns + int(duration_s * 1e9)
            return Setpoint(phase="commit", v_body=v, yaw_rate=0.0)

        speed = ap.approach_speed(dist, self.speed_far, self.speed_near, self.near_distance)
        yaw_rate = 0.0
        if state.gate_center_px is not None and state.image_size is not None:
            yaw_rate = ap.yaw_rate_to_center(
                state.gate_center_px, state.image_size, self.yaw_center_gain
            )
        return Setpoint(phase="approach", v_body=direction * speed + crosstrack,
                        yaw_rate=yaw_rate)
