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
from aigp.planning.ibvs import (IbvsConfig, VisibilityConfig, ibvs_centering,
                                visibility_speed)
from aigp.planning.pilot_agent import PilotAgent


class RacePlanner:
    def __init__(self, params: ParamSet) -> None:
        p = params
        self.takeoff_climb = float(p.get("planner.takeoff.climb_mps"))
        self.search_yaw_rate = float(p.get("planner.search.yaw_rate_rps"))
        self.search_climb = float(p.get("planner.search.climb_mps"))
        # Blind-hold is CONFIG-GATED, default OFF: the r1j3390 validation
        # trio failed its registered harm-clean letter (val-run2: first
        # collision inside a blind_hold stretch), so per that protocol the
        # fix does not enter the default config. The mechanism stays
        # available for outcome-judged A/B under an explicit patch.
        self.search_blind_hold = bool(p.get(
            "planner.search.blind_hold_enable", default=False))
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
        # T2b lever, config-gated default OFF: level blind crossing —
        # zero the vertical target when commit evidence is stale instead
        # of chasing the fossil dead-reckoned dz (the measured +0.47m
        # blind climb in the t2r1-B-run2 stall vs near-level passes).
        self.blind_vz_zero = bool(p.get("planner.commit.blind_vz_zero",
                                        default=False))
        # T2f (final-meter ledger, 598bbe3): the scored pass fired at
        # BELIEVED s=+0.247m — the believed plane runs ~0.25-0.5m ahead
        # of the physical one — and the r1j class-A stall was OUR retreat
        # on a half-second-old dead-reckoned "cross" to believed -0.315.
        # Config-gated: defaults preserve today's behavior; the T2f block
        # patches z to -0.9 (bias-aware) and freshness to 0.3 (a stale DR
        # phantom may not end a crossing).
        self.geom_term_z_m = float(p.get("planner.commit.geom_term_z_m",
                                         default=-0.4))
        self.geom_term_fresh_s = float(p.get(
            "planner.commit.geom_term_fresh_s", default=0.6))
        # Commit exit reason (instrumentation for the crossing autopsy —
        # both channels' top ask): set at every commit-exit branch, read
        # and cleared by app.py into a commit_exit log record. Closed set:
        # stale_budget / relock_jump / geometric_behind / term_abort /
        # corridor_abort / timer_expired / pass.
        self.commit_exit_reason = None
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
        # Fiction guard (phase6c F2): after a blown attempt the believed
        # target read "4.9m above me" and ALIGN dutifully climbed into
        # the ceiling (impulse 6.1). No R2 gate ever legitimately needs
        # more than ~2m of pre-commit height closure — a bigger reading
        # is attitude/estimator fiction, and climbing on it is the one
        # thing align must never do.
        self.align_sane_max = float(p.get("planner.align.sane_max_m",
                                          default=2.0))
        # Entry freshness (phase6c F3): re-commits entered on 1.2s-old
        # dead-reckoned estimates after collisions — attitude fiction
        # steered them into floor-scrape loops. Committing/aligning is
        # an aggressive act; it requires a recent view of the target.
        self.entry_max_age_s = float(p.get("planner.commit.entry_max_age_s",
                                           default=0.6))
        # In-commit blind tolerance, separate from the entry gate above.
        # Defaults to entry_max_age_s so unpatched flights are unchanged;
        # the T8 block raises it to let the final-meter blind traverse
        # complete on dead-reckoning (T7 census: stale_budget cut crossings
        # short as the gate left the FOV).
        self.commit_blind_budget_s = float(p.get(
            "planner.commit.blind_budget_s", default=self.entry_max_age_s))
        # GATE CHAINING (autonomous next-gate seek after a pass). Fly
        # forward at this speed for advance_s, scanning, until a fresh gate
        # is seen ahead of advance_min_fwd_m. Replaces the retreat/spin that
        # threw away every gate-1 pass.
        # DISTANCE-based clearance (ADVISORY-37 guard 1): a time window under
        # variable speed manufactures blind overreach in a walled arena.
        # Terminate on integrated forward displacement (speed*elapsed), just
        # enough to clear gate-1's frame depth and earn room to acquire.
        self.advance_dist_m = float(p.get("planner.advance.distance_m",
                                          default=1.2))
        # Blind-speed cap (ADVISORY-37 guard 2): blind meters fly slow.
        self.advance_speed = float(p.get("planner.advance.speed_mps",
                                         default=1.2))
        # Outer time watchdog only (guard 6): if the distance isn't covered
        # in this, the integrator lied — end into normal search.
        self.advance_max_s = float(p.get("planner.advance.max_s", default=2.5))
        self.advance_min_fwd_m = float(p.get("planner.advance.min_fwd_m",
                                             default=1.0))
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
        # A FORMULA, not a number (advisory-6): R = v^2/(2a) + t_react*v
        # moves with commit speed instead of silently going stale. The
        # default decel reproduces the measured ~1.2m at 2.5 m/s; the
        # floor param is an absolute lower bound at low speeds. a_brake
        # awaits direct measurement from retreat-segment kinematics.
        self.brake_decel = float(p.get("planner.commit.brake_decel_mps2",
                                       default=2.6))
        self.brake_react_s = float(p.get("planner.commit.brake_react_s",
                                         default=0.0))
        floor = float(p.get("planner.commit.abort_min_dist_m", default=0.8))
        self.abort_min_dist_m = max(
            floor,
            self.commit_speed ** 2 / (2.0 * max(self.brake_decel, 0.1))
            + self.brake_react_s * self.commit_speed)
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
        # Blind-hover escalation (advisory-11 SS3): hover is not a fixed
        # point — it drifts at the velocity-estimate error near
        # structure. Look for a bounded time, then slow-retrace along
        # the inbound tangent; never loiter blind indefinitely.
        self.blind_hold_s = float(p.get("planner.search.blind_hold_s",
                                        default=4.5))
        # Commit vertical damper (P1 verdict, cohort-2: FOV-leave 5/6
        # with vz peak-to-peak 2.0-4.65 m/s at loss while the hold's
        # own cap is 0.8 — the vertical chain chasing the between-fix
        # velocity-estimate sawtooth bobs the airframe and walks the
        # gate out the BOTTOM of the +29deg-up camera's frame at
        # 3-4.5m. Commit is entered PRE-ALIGNED (align closed the gap
        # to <=0.5m): the in-commit vertical is a TRIM, not a chase —
        # deadbanded around the aim, hard-capped, slew-limited.
        self.commit_vz_deadband_m = float(p.get(
            "planner.commit.vz_deadband_m", default=0.15))
        self.commit_vz_cap = float(p.get(
            "planner.commit.vz_cap_mps", default=0.35))
        self.commit_vz_slew = float(p.get(
            "planner.commit.vz_slew_mps2", default=1.5))
        self.retrace_mps = float(p.get("planner.search.retrace_mps",
                                       default=0.5))
        self.retreat_enabled = bool(p.get("planner.retreat.enabled", default=True))
        self.recover_brake_s = float(p.get("planner.recover.brake_s"))
        self.force_hover = bool(p.get("planner.force_hover", default=False))
        # POST-PASS REGIME (transplanted from the team's parallel
        # "gates_slow" stack, the one that threads 3 gates): its doctrine
        # threads every gate FROM A STOP — stop, scan, aim, approach in
        # gentle pulses, re-aiming continuously; off-line means stop and
        # re-aim, never carry momentum at a gate. Our submission census
        # says the same thing from the other side: every gate-2 death was
        # momentum into structure 0.14-2m short. After the FIRST pass this
        # regime slows everything and demands fresh evidence to commit.
        # Config-gated, default OFF.
        self.postpass_enable = bool(p.get("planner.postpass.enable",
                                          default=False))
        self.pp_speed_far = float(p.get("planner.postpass.speed_far_mps",
                                        default=1.0))
        self.pp_speed_near = float(p.get("planner.postpass.speed_near_mps",
                                         default=0.6))
        self.pp_commit_speed = float(p.get("planner.postpass.commit_speed_mps",
                                           default=1.0))
        self.pp_entry_age_s = float(p.get("planner.postpass.entry_max_age_s",
                                          default=0.3))
        self.pp_brake_s = float(p.get("planner.postpass.brake_s", default=0.8))
        self._postpass_active = False
        # IBVS pixel-bearing fallback (ported from the owner-supplied
        # "aigp_stack" FunnelPassController, mount-pitch corrected — see
        # planning/ibvs.py). Steers lateral/vertical/yaw on the PIXEL
        # center while the 3D pose is stale but the blob is still
        # tracked (center-only detections refresh gate_center_px without
        # refreshing gate_rel). Config-gated, default OFF.
        self.ibvs = IbvsConfig(
            enable=bool(p.get("planner.ibvs.enable", default=False)),
            lat_gain=float(p.get("planner.ibvs.lat_gain", default=1.6)),
            vert_gain=float(p.get("planner.ibvs.vert_gain", default=1.2)),
            yaw_gain=float(p.get("planner.ibvs.yaw_gain", default=1.5)),
            max_lat_mps=float(p.get("planner.ibvs.max_lat_mps", default=1.5)),
            max_vert_mps=float(p.get("planner.ibvs.max_vert_mps", default=1.0)),
            yaw_cap_rps=float(p.get("planner.ibvs.yaw_cap_rps", default=0.8)),
            aim_up_frac=float(p.get("planner.ibvs.aim_up_frac", default=0.0)))
        self.ibvs_center_fresh_s = float(p.get(
            "planner.ibvs.center_fresh_s", default=0.3))
        # Visibility-based speed (ported from the aigp_stack
        # VisibilitySpeedController): forward speed scales DOWN as the
        # gate fix ages, with a time-to-contact panic brake. Applied to
        # APPROACH only — commit has its own blind budget and a physics-
        # sized window that a mid-dash slowdown would silently outlive.
        # Config-gated, default OFF.
        self.vis = VisibilityConfig(
            enable=bool(p.get("planner.visibility.enable", default=False)),
            fresh_full_s=float(p.get("planner.visibility.fresh_full_s",
                                     default=0.15)),
            stale_age_s=float(p.get("planner.visibility.stale_age_s",
                                    default=0.5)),
            min_frac=float(p.get("planner.visibility.min_frac", default=0.35)),
            min_speed_mps=float(p.get("planner.visibility.min_speed_mps",
                                      default=0.8)),
            panic_ttc_s=float(p.get("planner.visibility.panic_ttc_s",
                                    default=0.6)),
            panic_scale=float(p.get("planner.visibility.panic_scale",
                                    default=0.5)))
        self.cam_fov_deg = float(p.get("perception.camera.fov_deg"))
        self.cam_mount_pitch = float(p.get("perception.camera.mount_pitch_deg",
                                           default=0.0))
        # Embedded autonomous AI pilot (owner directive 2026-07-29): when
        # enabled, race-mode planning is DELEGATED to the PilotAgent —
        # utility-scored maneuver arbitration with forward rollout —
        # instead of the phase FSM below. Config-gated, default OFF.
        self.agent_enable = bool(p.get("planner.agent.enable", default=False))
        self.agent = PilotAgent(p) if self.agent_enable else None
        self.looming = 0.0     # latest looming score, fed by app each tick

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
        self._advance_start_ns: int | None = None   # post-pass next-gate seek
        self._advance_pending = False               # set by on_gate_passed
        self._blind_hold_ns: int | None = None  # blind-brake epoch (retrace)
        self._commit_vz_prev: float | None = None   # damper slew memory
        self._commit_vz_prev_ns: int | None = None
        self._search_last_ns: int | None = None
        self._search_prev_rate = 0.0
        self._search_yaw_accum = 0.0
        self._term_abort_request = False

    def request_commit_abort(self) -> None:
        """Terminal-channel abort request (RESPONSE32 disposition,
        pre-no-return branch): the rate model expired beyond its
        validated age while reversal was still schedulable. The flag
        is honored at the next commit tick ONLY outside the braking
        band — feasibility is decided here, by the same
        abort_min_dist_m geometry as the vision abort, because a
        retreat inside the band cannot reverse momentum and coasts
        into the gate. Inside the band the request is dropped and the
        terminal channel's neutral-decay floor governs instead."""
        self._term_abort_request = True

    def reset(self) -> None:
        self._postpass_active = False
        self._commit_until_ns = None
        self._commit_v_body = None
        self._commit_prev_z = None
        self._recover_until_ns = None
        self._retreat_until_ns = None
        self._align_until_ns = None
        self._advance_start_ns = None    # state hygiene (channel-2 ADVISORY-2 §6)
        self._advance_pending = False
        self._abort_breach = 0
        self._term_abort_request = False
        self._last_seen_side = 1.0
        self._gap_bias = None
        self._reacquire_until_ns = None
        self._blind_hold_ns = None
        self._search_last_ns = None
        self._search_prev_rate = 0.0
        self._search_yaw_accum = 0.0
        self._commit_vz_prev = None
        self._commit_vz_prev_ns = None

    def _note_attempt_failed(self, now_ns: int) -> None:
        """A commit ended without a pass event: arm the post-miss
        reacquisition guard so the next approach stays on THIS gate's
        neighborhood instead of chasing a far relock into steel."""
        self._reacquire_until_ns = now_ns + int(self.reacquire_window_s * 1e9)

    # -- external events ------------------------------------------------------

    def set_looming(self, score: float) -> None:
        self.looming = float(score)

    def on_gate_passed(self) -> None:
        if self._commit_until_ns is not None:
            self.commit_exit_reason = "pass"
        self._commit_until_ns = None
        self._commit_v_body = None
        self._commit_prev_z = None
        self._retreat_until_ns = None
        self._align_until_ns = None
        self._gap_bias = None
        self._reacquire_until_ns = None
        # GATE CHAINING (autonomous): a successful pass must ADVANCE toward
        # the next gate, never retreat/spin. The b1 trace showed the drone
        # passing gate 1 while already commanding a -1.2 m/s RETREAT, then
        # spinning blind and colliding — gate 2 never reached. Arm the
        # forward advance-and-seek state (started with now_ns in plan()).
        self._advance_pending = True
        self._agent_pass_pending = True

    def on_collision(self, now_ns: int) -> None:
        if self.agent is not None:
            self.agent.on_collision(now_ns)
        self._recover_until_ns = now_ns + int(self.recover_brake_s * 1e9)
        self._commit_until_ns = None
        self._commit_v_body = None
        self._commit_prev_z = None
        self._retreat_until_ns = None
        self._align_until_ns = None
        self._advance_start_ns = None   # a crash ends the forward advance
        self._advance_pending = False

    def _damp_commit_vz(self, vz: float, tdz_err: float,
                        now_ns: int, insurance: float = 0.0) -> float:
        """Deadband + cap + slew for the in-commit vertical (NED z).

        The commit vertical is a trim on a pre-aligned entry; chasing
        the velocity-estimate sawtooth at full hold authority is what
        bobbed the gate out of frame (cohort-2 P1). Inside the
        deadband the trim is ZERO. The cap and the slew bound the
        AGGREGATE legacy command — trim PLUS the once-decided sink
        insurance — per the signed damper invariant: the insurance
        consumes command budget, it must not silently turn the 0.35
        cap into 0.45 in a long blind gap with a saturated trim; and
        two separate slew limiters can compose into a larger physical
        slope than either. In the non-saturated regime (where the
        no-arm covered class actually lives) the insurance passes
        through unchanged."""
        if abs(tdz_err) < self.commit_vz_deadband_m:
            vz = 0.0
        vz = vz - insurance                    # NED: insurance climbs
        vz = float(np.clip(vz, -self.commit_vz_cap, self.commit_vz_cap))
        if (self._commit_vz_prev is not None
                and self._commit_vz_prev_ns is not None):
            step = self.commit_vz_slew * max(
                (now_ns - self._commit_vz_prev_ns) / 1e9, 0.0)
            vz = float(np.clip(vz, self._commit_vz_prev - step,
                               self._commit_vz_prev + step))
        self._commit_vz_prev = vz
        self._commit_vz_prev_ns = now_ns
        return vz

    def track_applied_vz(self, vz: float, now_ns: int) -> None:
        """Inactive-controller tracking (single-owner contract,
        signed damper invariant 2): while TERM owns the vertical the
        legacy damper contributes nothing AND tracks the APPLIED
        command, so a pre-no-return handback resumes bumplessly from
        the applied value instead of a latent accumulated trim."""
        self._commit_vz_prev = float(vz)
        self._commit_vz_prev_ns = now_ns

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
        """Aim-above-center insurance, tapered to ~zero at the gate.

        History matters here: phase3h "crossed consistently LOW" and the
        floor was added to counter it — but the true-vertical audit
        (0bf8fcd) proved those LOW labels were the tilted-frame phantom
        (49 of 88 attempts were truly HIGH, 8 truly LOW), and phase6d F1
        then grazed the TOP bar nine times while laterally dead-centered
        with the 0.25m floor active. The floor was phantom-era debris;
        default is now 0 (param retained for tuning).
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

        if self.agent is not None:
            # AI-pilot delegation: the pass event has no clock, so the
            # pending flag is converted to the agent's chain window here.
            if getattr(self, "_agent_pass_pending", False):
                self._agent_pass_pending = False
                self.agent.on_gate_passed(now_ns)
            return self.agent.decide(now_ns, state, self.looming)

        # POST-PASS REGIME switch: the sim's authoritative gate index
        # says at least one gate is behind us — thread the rest from a
        # stop (gates_slow doctrine). Speeds/freshness swap ONCE; the
        # brake-first entry replaces the ADVANCE momentum burst.
        if (self.postpass_enable and not self._postpass_active
                and race is not None and race.active_gate_index >= 1):
            self._postpass_active = True
            self.speed_far = self.pp_speed_far
            self.speed_near = self.pp_speed_near
            self.commit_speed = self.pp_commit_speed
            self.entry_max_age_s = self.pp_entry_age_s
            self._advance_pending = False        # no momentum burst
            self._advance_start_ns = None
            self._recover_until_ns = now_ns + int(self.pp_brake_s * 1e9)

        # Arm the post-pass advance (on_gate_passed has no clock).
        if self._advance_pending:
            self._advance_pending = False
            self._advance_start_ns = now_ns

        # -- recover: brake after a collision (safety first, even mid-advance)
        if self._recover_until_ns is not None:
            if now_ns < self._recover_until_ns:
                self._advance_start_ns = None
                return Setpoint(phase="recover", v_body=np.zeros(3), yaw_rate=0.0)
            self._recover_until_ns = None

        # -- advance: GATE CHAINING. Right after a pass, fly FORWARD toward
        # the next gate (courses flow forward) instead of retreating/spinning.
        # DISTANCE-capped clearance (ADVISORY-37): terminate on integrated
        # forward displacement (speed*elapsed) once gate-1's frame depth is
        # cleared; hand off to approach the instant a fresh gate is seen
        # AHEAD; ignore the just-passed gate (fwd <= 0). Outer time watchdog
        # guards a lying integrator. Vision-only, no map, autonomous.
        if self._advance_start_ns is not None:
            gate = state.gate_rel
            ahead = (gate is not None and gate.t is not None
                     and float(gate.t[2]) > self.advance_min_fwd_m
                     and state.gate_rel_age_s <= self.blind_age_s)
            elapsed_s = (now_ns - self._advance_start_ns) / 1e9
            covered_m = self.advance_speed * elapsed_s
            if ahead:
                self._advance_start_ns = None         # next gate acquired
            elif covered_m < self.advance_dist_m and elapsed_s < self.advance_max_s:
                yaw = self.search_yaw_rate * (self._last_seen_side or 1.0)
                return Setpoint(
                    phase="advance",
                    v_body=np.array([self.advance_speed, 0.0, 0.0]),
                    yaw_rate=yaw)
            else:
                self._advance_start_ns = None         # cleared / watchdog

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
                # BLINDNESS BUDGET (cohort-2 wipeout, F1 autopsy): when
                # commit evidence goes stale past the commit-grade
                # horizon, STOP — brake to hover and reacquire from
                # standstill. The freshness-gated termination alone
                # converted the phantom-abort class into a blind 3.7m
                # continuation on the locked vector followed by a blind
                # -1.2 m/s reverse into the structure just overflown
                # (impulse 7.2). The constitution's own rule decides
                # this: uncertainty while moving reduces speed and
                # eventually forces a stop — never a blind dash and
                # never a blind reverse. A good crossing is unaffected:
                # the wash runs ~0.5s and the pass event clears commit
                # before this budget expires.
                # T8 (T7 exit-census: reached-gate exits are now stale_budget
                # + timer_expired — the gate leaves FOV in the final meter,
                # EXPECTED physics, and this budget brakes the crossing
                # short). Separate the IN-COMMIT blind tolerance from the
                # ENTRY freshness gate so the final blind traverse can
                # complete on dead-reckoning without loosening how fresh a
                # commit must be to START (channel-2 ADVISORY-36 change #1).
                # Default equals entry_max_age_s -> unpatched behavior
                # identical.
                if state.gate_rel_age_s > self.commit_blind_budget_s:
                    self.commit_exit_reason = "stale_budget"
                    self._commit_until_ns = None
                    self._commit_v_body = None
                    self._commit_prev_z = None
                    self._note_attempt_failed(now_ns)
                    self._recover_until_ns = now_ns + int(
                        self.recover_brake_s * 1e9)
                    self._blind_hold_ns = now_ns
                    self._search_last_ns = None
                    self._search_prev_rate = 0.0
                    self._search_yaw_accum = 0.0
                    return Setpoint(phase="recover", v_body=np.zeros(3),
                                    yaw_rate=0.0)
                # Relock guard (phase6a dash-F2): the believed target
                # jumped several meters AWAY mid-commit — that is the
                # estimator legitimately relocking the NEXT gate after we
                # slipped past this one outside the opening. Continuing
                # the dash on a timer sized for the old range chases the
                # far gate at commit speed; end the attempt and retreat.
                if (gate is not None and self._commit_prev_z is not None
                        and float(gate.t[2]) > self._commit_prev_z
                        + self.relock_jump_m):
                    self.commit_exit_reason = "relock_jump"
                    self._commit_until_ns = None
                    self._commit_v_body = None
                    self._commit_prev_z = None
                    self._note_attempt_failed(now_ns)
                    if self.retreat_enabled:
                        self._retreat_until_ns = now_ns + int(self.retreat_s * 1e9)
                        return self._retreat_setpoint(state)
                    return Setpoint(phase="search",
                                    v_body=np.zeros(3),
                                    blind_hold=self.search_blind_hold,
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
                # FRESHNESS REQUIRED (the small difference between the
                # 4/4 passes and the 0/4 first-attempt aborts): every
                # early retreat in the 1.8 cohort fired this clause on a
                # believed that had been BLIND for 1.44-1.50s — a
                # PHANTOM crossing dead-reckoned through the plane while
                # the true closest approach was still 2.1-4.1m out.
                # Stale phantoms never reach here anymore (the blindness
                # budget above brakes first); this clause fires only on
                # a FRESH crossing — genuinely decided, retreat for the
                # next pass. The freshness condition stays as the
                # documented law even though the budget subsumes it.
                if gate is not None and gate.t[2] < self.geom_term_z_m \
                        and state.gate_rel_age_s <= self.geom_term_fresh_s:
                    self.commit_exit_reason = "geometric_behind"
                    self._commit_until_ns = None
                    self._commit_v_body = None
                    self._commit_prev_z = None
                    self._note_attempt_failed(now_ns)
                    if self.retreat_enabled:
                        self._retreat_until_ns = now_ns + int(self.retreat_s * 1e9)
                        return self._retreat_setpoint(state)
                    # No-retreat fallback (R2C census: 3/8 deaths were the
                    # blind BACKWARD leg into structure behind us — on the
                    # dense course a retreat is a blind maneuver by
                    # construction). Brake to a stop instead: momentum is
                    # forward, the space ahead was just inspected, and
                    # search resumes from a standstill. Without this branch
                    # the fall-through returned Setpoint(v_body=None) — a
                    # mid-flight crash the retreat default masked.
                    self._recover_until_ns = now_ns + int(
                        self.recover_brake_s * 1e9)
                    self._blind_hold_ns = now_ns
                    self._search_last_ns = None
                    self._search_prev_rate = 0.0
                    self._search_yaw_accum = 0.0
                    return Setpoint(phase="recover", v_body=np.zeros(3),
                                    yaw_rate=0.0)
                elif gate is not None and gate.t[2] > 0.3:
                    d_body = ap.cam_to_body(gate.t)
                    dist = float(np.linalg.norm(d_body))
                    au = self._aim_up(dist)
                    # Terminal-channel epistemic abort (RESPONSE32
                    # disposition, pre-no-return branch): honored only
                    # where reversal is feasible — outside the braking
                    # band, on a FRESH estimate (a band check on a
                    # fossil dist could retreat inside the real band).
                    # Consumed either way; the terminal channel
                    # re-raises it while the condition persists, and
                    # inside the band its neutral-decay floor governs.
                    if self._term_abort_request:
                        self._term_abort_request = False
                        if (self.retreat_enabled
                                and dist > self.abort_min_dist_m
                                and state.gate_rel_age_s <= self.blind_age_s):
                            self.commit_exit_reason = "term_abort"
                            self._commit_until_ns = None
                            self._commit_v_body = None
                            self._commit_prev_z = None
                            self._note_attempt_failed(now_ns)
                            self._retreat_until_ns = now_ns + int(
                                self.retreat_s * 1e9)
                            return self._retreat_setpoint(state)
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
                    # No irreversible maneuver on state-only evidence in
                    # the terminal zone (advisory-6, T3's twin): breaches
                    # count only while vision is FRESH — a dead-reckoned
                    # estimate may inform telemetry but must never fire
                    # the abort (F2's fossil abort ran on age 0.32s).
                    if (self.abort_min_dist_m < dist < 1.5
                            and off > self.abort_offset_m
                            and state.gate_rel_age_s <= self.blind_age_s):
                        self._abort_breach += 1
                    else:
                        self._abort_breach = 0
                    if self._abort_breach >= 4:
                        self._abort_breach = 0
                        self.commit_exit_reason = "corridor_abort"
                        self._commit_until_ns = None
                        self._commit_v_body = None
                        self._commit_prev_z = None
                        self._note_attempt_failed(now_ns)
                        if self.retreat_enabled:
                            self._retreat_until_ns = now_ns + int(
                                self.retreat_s * 1e9)
                            return self._retreat_setpoint(state)
                        # No-retreat corridor escape (R2D census): gating
                        # the abort itself on retreat_enabled starved the
                        # ONLY escape from a doomed commit — commit-phase
                        # env collisions went 1/8 -> 4/8 as breached
                        # corridors carried through into structure with
                        # fresh detections. Brake to a stop instead;
                        # run 6 proved the brake->reacquire loop chains.
                        self._recover_until_ns = now_ns + int(
                            self.recover_brake_s * 1e9)
                        self._blind_hold_ns = now_ns
                        self._search_last_ns = None
                        self._search_prev_rate = 0.0
                        self._search_yaw_accum = 0.0
                        return Setpoint(phase="recover", v_body=np.zeros(3),
                                        yaw_rate=0.0)
                    direction, dist = ap.gate_direction_body(gate, au)
                    extra = ap.crosstrack_velocity(gate, au, self.center_gain)
                    blind_now = state.gate_rel_age_s > self.blind_age_s
                    ibvs_now = (self.ibvs.enable and blind_now
                                and state.gate_center_px is not None
                                and state.image_size is not None
                                and state.gate_center_age_s
                                <= self.ibvs_center_fresh_s)
                    if ibvs_now:
                        # IBVS pixel-guided traverse (aigp_stack port):
                        # the 3D pose is fossil but the blob center is
                        # still tracked (center-only detections in the
                        # banner/bloom final meters refresh the pixel
                        # without refreshing gate_rel). Steer lateral +
                        # vertical + yaw on the mount-corrected pixel
                        # bearing instead of dead-reckoning the frozen
                        # vector — LIVE image evidence beats a fossil.
                        # The damper deadband is bypassed deliberately
                        # (it guards fossil-chasing; this input is
                        # fresh); cap and slew still bound the command.
                        vy, vz, ibvs_yaw = ibvs_centering(
                            state.gate_center_px, state.image_size,
                            self.cam_fov_deg, self.cam_mount_pitch,
                            self.ibvs)
                        self._gap_bias = None
                        vz = float(np.clip(vz, -self.commit_vz_cap,
                                           self.commit_vz_cap))
                        if (self._commit_vz_prev is not None
                                and self._commit_vz_prev_ns is not None):
                            step = self.commit_vz_slew * max(
                                (now_ns - self._commit_vz_prev_ns) / 1e9, 0.0)
                            vz = float(np.clip(
                                vz, self._commit_vz_prev - step,
                                self._commit_vz_prev + step))
                        self._commit_vz_prev = vz
                        self._commit_vz_prev_ns = now_ns
                        self._commit_v_body = np.array(
                            [self.commit_speed, vy, vz])
                        return Setpoint(phase="commit",
                                        v_body=self._commit_v_body,
                                        yaw_rate=ibvs_yaw, ibvs=True)
                    if self.blind_vz_zero and blind_now:
                        # T2b (ADVISORY-36 change #1, vertical member +
                        # the crossing autopsy 7cbce47): in the blind
                        # final traverse the dead-reckoned dz is FOSSIL —
                        # the hold chased it +0.47m upward in the t2r1
                        # stall's last blind 0.5s and clipped the frame,
                        # while every completed pass arrived near-level.
                        # Cross LEVEL on momentum: vertical target zero
                        # (slew decays residual trim), insurance disarmed.
                        self._gap_bias = None
                        v_next = direction * self.commit_speed + extra
                        v_next[2] = self._damp_commit_vz(0.0, 0.0, now_ns)
                    else:
                        extra[2] += ap.altitude_hold_velocity(
                            gate, state.q_att, au, self.alt_gain,
                            level_roll=state.level_roll,
                            level_pitch=state.level_pitch)
                        # No-arm rule: the sink insurance is decided ONCE, at
                        # gap entry, by the state the last fixes left behind —
                        # if the altitude hold is already commanding a climb
                        # there, insurance is VETOED (F1's +1m overfly was
                        # exactly hold-climb + insurance-climb stacking blind).
                        if not blind_now:
                            self._gap_bias = None        # seeing: disarmed
                        elif self._gap_bias is None:
                            # TOP-UP, not binary veto (phase5c: the binary
                            # veto killed insurance whenever the hold climbed
                            # at all, and all three flights arrived LOW):
                            # insurance only fills the gap between the hold's
                            # climb at entry and the insured sink rate. F1's
                            # overfly case still gets zero (hold -0.72 >> 0.1).
                            climb = max(0.0, -float(extra[2]))   # NED: -z up
                            self._gap_bias = max(0.0,
                                                 self.blind_climb_bias - climb)
                        v_next = direction * self.commit_speed + extra
                        v_next[2] = self._damp_commit_vz(
                            float(v_next[2]), tdz - au, now_ns,
                            insurance=self._gap_bias or 0.0)
                    self._commit_v_body = v_next
                yaw = 0.0
                if gate is not None and gate.t[2] > 0.3:
                    yaw = ap.yaw_rate_to_bearing(gate, self.commit_yaw_gain)
                return Setpoint(phase="commit", v_body=self._commit_v_body,
                                yaw_rate=yaw)
            # Window expired without a gate-passed event: we are past the
            # plane outside the opening (or stalled) — back off and retry
            # instead of the blind flail that ended most R2 flights.
            # Retreat-at-speed is an evidence maneuver: with a fresh
            # believed we know where the structure is and can back away
            # from it. With stale evidence, brake instead (cohort-2 F1
            # backed blind into the gate it had just blind-overflown).
            self.commit_exit_reason = "timer_expired"
            self._commit_until_ns = None
            self._commit_v_body = None
            self._commit_prev_z = None
            self._note_attempt_failed(now_ns)
            if state.gate_rel_age_s > self.entry_max_age_s:
                self._recover_until_ns = now_ns + int(
                    self.recover_brake_s * 1e9)
                self._blind_hold_ns = now_ns
                self._search_last_ns = None
                self._search_prev_rate = 0.0
                self._search_yaw_accum = 0.0
                return Setpoint(phase="recover", v_body=np.zeros(3),
                                yaw_rate=0.0)
            if self.retreat_enabled:
                self._retreat_until_ns = now_ns + int(self.retreat_s * 1e9)
                return self._retreat_setpoint(state)

        gate = state.gate_rel
        if gate is None:
            # -- search: spin toward the side the gate was last seen on.
            # After a BLIND brake (advisory-11 SS3): hover is not a fixed
            # point — the velocity-estimate error (~0.1-0.2 m/s) walks a
            # blind hover into structure. Look for blind_hold_s, then
            # slow-retrace along the INBOUND tangent (known-clear: we
            # just flew it) — retrace beats explore, and never loiter
            # blind near steel. The sweep's commanded yaw is integrated
            # so the retrace vector stays world-inbound however far the
            # sweep has rotated the body frame.
            if self._blind_hold_ns is not None:
                if self._search_last_ns is not None:
                    self._search_yaw_accum += self._search_prev_rate * (
                        now_ns - self._search_last_ns) / 1e9
                self._search_last_ns = now_ns
                v = np.array([0.0, 0.0, -self.search_climb])
                if now_ns - self._blind_hold_ns > int(self.blind_hold_s * 1e9):
                    a = self._search_yaw_accum
                    v = np.array([-self.retrace_mps * np.cos(a),
                                  self.retrace_mps * np.sin(a),
                                  0.0])
                    rate = (-self.search_yaw_rate * np.sign(a)
                            if abs(a) > 0.15 else 0.0)
                else:
                    rate = self.search_yaw_rate * self._last_seen_side
                self._search_prev_rate = float(rate)
                # The retrace variant commands real horizontal motion along
                # the known-clear inbound tangent — that one the velocity
                # loop must track; only the zero-horizontal hold is blind.
                hold = bool(abs(float(v[0])) < 1e-9 and abs(float(v[1])) < 1e-9)
                return Setpoint(phase="search", v_body=v, yaw_rate=float(rate),
                                blind_hold=hold and self.search_blind_hold)
            return Setpoint(
                phase="search",
                v_body=np.array([0.0, 0.0, -self.search_climb]),
                yaw_rate=self.search_yaw_rate * self._last_seen_side,
                blind_hold=self.search_blind_hold,
            )

        # -- approach
        self._blind_hold_ns = None            # evidence is back
        self._search_last_ns = None
        self._search_prev_rate = 0.0
        self._search_yaw_accum = 0.0
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
            # Entering the through-gate pipeline (align or commit) is an
            # aggressive act: it requires a RECENT view of the target.
            # Stale dead-reckoned estimates keep flying the gentler
            # approach until the detector refreshes (phase6c F3's
            # post-collision re-commits ran on 1.2s-old fiction).
            if state.gate_rel_age_s > self.entry_max_age_s \
                    and self._commit_until_ns is None:
                speed = ap.approach_speed(dist, self.speed_far,
                                          self.speed_near, self.near_distance)
                if self.vis.enable:
                    speed = visibility_speed(
                        speed, state.gate_rel_age_s, dist,
                        float(np.linalg.norm(state.v_world)), self.vis)
                v = direction * speed + crosstrack
                yaw_rate = 0.0
                if state.gate_center_px is not None and state.image_size is not None:
                    if (self.ibvs.enable and state.gate_center_age_s
                            <= self.ibvs_center_fresh_s):
                        # Stale-3D approach with a live pixel track: center
                        # on the pixel bearing (lateral + vertical + yaw)
                        # instead of the fossil pose — this is the keep-in-
                        # frame servo that prevents the R2C run-1 gate-2
                        # dropout (detection collapsed as the off-axis gate
                        # drifted out of the FOV).
                        vy, vz, yaw_rate = ibvs_centering(
                            state.gate_center_px, state.image_size,
                            self.cam_fov_deg, self.cam_mount_pitch, self.ibvs)
                        v = np.array([float(v[0]), vy, vz])
                        return Setpoint(phase="approach", v_body=v,
                                        yaw_rate=yaw_rate, ibvs=True)
                    yaw_rate = ap.yaw_rate_to_center(
                        state.gate_center_px, state.image_size,
                        self.yaw_center_gain)
                return Setpoint(phase="approach",
                                v_body=v,
                                yaw_rate=yaw_rate)
            # Vertical pre-alignment: close the TRUE height gap first,
            # creeping forward, then dash level (the in-commit hold's
            # 0.8 m/s cap can only trim small residuals in-window).
            world_dz = ap.true_world_dz(gate, state.q_att,
                                        state.level_roll, state.level_pitch)
            err_dz = abs(world_dz - au)
            misaligned = self.align_dz_max < err_dz <= self.align_sane_max
            if err_dz > self.align_sane_max:
                # Fiction guard (phase6c F2): "the gate is 4.9m above
                # me" is not a measurement on this track — never climb
                # on it. Commit proceeds under its own guards instead.
                misaligned = False
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
            self._commit_vz_prev = None           # fresh damper epoch
            self._commit_vz_prev_ns = None
            v[2] = self._damp_commit_vz(float(v[2]), world_dz - au, now_ns)
            self._commit_v_body = v
            self._commit_prev_z = float(gate.t[2])
            duration_s = max(self.commit_duration_s,
                             dist / max(self.commit_speed, 0.1) + 1.0)
            self._commit_until_ns = now_ns + int(duration_s * 1e9)
            return Setpoint(phase="commit", v_body=v, yaw_rate=0.0)

        speed = ap.approach_speed(dist, self.speed_far, self.speed_near, self.near_distance)
        if self.vis.enable:
            # Visibility-based speed (aigp_stack port): fresh fixes fly the
            # profile unchanged; an aging fix scales the approach down and a
            # short time-to-contact on weak evidence panic-brakes. Slow
            # blind meters cost seconds — fast blind meters cost the frame
            # (R2C run-4: forward into structure during approach).
            speed = visibility_speed(speed, state.gate_rel_age_s, dist,
                                     float(np.linalg.norm(state.v_world)),
                                     self.vis)
        yaw_rate = 0.0
        if state.gate_center_px is not None and state.image_size is not None:
            yaw_rate = ap.yaw_rate_to_center(
                state.gate_center_px, state.image_size, self.yaw_center_gain
            )
        return Setpoint(phase="approach", v_body=direction * speed + crosstrack,
                        yaw_rate=yaw_rate)
