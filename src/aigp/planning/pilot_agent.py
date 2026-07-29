"""PilotAgent: an embedded autonomous AI pilot (owner directive 2026-07-29).

Replaces the scripted phase FSM with an AGENT: every decision tick it
enumerates candidate maneuvers, rolls each forward through a short-horizon
motion model against the current world belief (gate pose, staleness,
altitude-vs-gate-line, looming), scores the predicted outcomes with a
utility function, and flies the argmax. Decisions are data, not script —
every tick publishes the full score table so flight censuses read WHY the
pilot did what it did.

The utility terms are the R2 death census, made machine-readable:
  - low-arrival penalty      (R2E/R2F class: centered but below the gate
                              line into the pedestal structure)
  - blind-motion penalty     (every R2C-R2E death involved motion on stale
                              belief; uncertainty must slow and stop)
  - looming penalty          (forward-into-structure with fresh gate lock:
                              the camera sees the obstacle even though the
                              gate detector does not — the looming sensor
                              turns that into a scalar)
  - corridor / crossing terms (the physics of actually threading the ring)

Design constraints honored:
  - vision + IMU only, no map, no layout priors (fully autonomous);
  - pure function of the tick's inputs -> deterministic, unit-testable;
  - no external calls of any kind — this is the flight code itself;
  - config-gated (planner.agent.enable, default OFF): unpatched flights
    keep the FSM.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from aigp.core.messages import Setpoint, StateEstimate
from aigp.core.params import ParamSet
from aigp.estimation.attitude_filter import (level_quat, quat_multiply,
                                             quat_rotate)
from aigp.planning import approach as ap
from aigp.planning.ibvs import IbvsConfig, ibvs_centering

# Maneuver vocabulary. Phases map onto the existing telemetry vocabulary
# so downstream consumers (shadow wiring, censuses, replay tools) keep
# working: CROSS->commit, ADVANCE->approach, CLIMB->align, BRAKE->recover,
# SCAN->search, CHAIN->advance.
CROSS = "CROSS"
ADVANCE = "ADVANCE"
CLIMB = "CLIMB"
BRAKE = "BRAKE"
SCAN = "SCAN"
CHAIN = "CHAIN"

_PHASE = {CROSS: "commit", ADVANCE: "approach", CLIMB: "align",
          BRAKE: "recover", SCAN: "search", CHAIN: "advance"}


@dataclass
class _Candidate:
    action: str
    v_body: np.ndarray          # commanded body velocity [fwd, right, down]
    yaw_rate: float
    score: float = 0.0
    terms: dict | None = None


class PilotAgent:
    def __init__(self, params: ParamSet) -> None:
        p = params
        g = lambda k, d: p.get("planner.agent." + k, default=d)  # noqa: E731
        self.cross_speed = float(g("cross_speed_mps", 1.2))
        self.advance_speed = float(g("advance_speed_mps", 2.0))
        self.climb_fwd = float(g("climb_fwd_mps", 0.4))
        self.aim_up_m = float(g("aim_up_m", 0.35))
        self.corridor_m = float(g("corridor_m", 0.55))
        # Asymmetric vertical crossing corridor (R2E census): crossing
        # BELOW center is a pedestal strike (allow almost none); crossing
        # high risks only a top-bar clip (allow more).
        self.cross_low_m = float(g("cross_low_m", 0.15))
        self.cross_high_m = float(g("cross_high_m", 0.65))
        self.cross_max_age_s = float(g("cross_max_age_s", 0.35))
        self.horizon_s = float(g("horizon_s", 3.0))
        self.dt_s = float(g("dt_s", 0.25))
        self.tau_s = float(g("tau_s", 0.4))
        self.low_margin_m = float(g("low_margin_m", 0.15))
        self.w_progress = float(g("w_progress", 1.0))
        # Predicted progress is a CLAIM about a belief: discount it by
        # evidence age (exp decay). Fresh belief -> full credit; a
        # second-old fossil earns almost none, so blind speed loses to
        # stopping on utility, not on a scripted threshold.
        self.conf_tau_s = float(g("conf_tau_s", 0.5))
        self.w_cross = float(g("w_cross", 6.0))
        self.w_low = float(g("w_low", 4.0))
        self.w_loom = float(g("w_loom", 30.0))
        self.w_blind = float(g("w_blind", 1.2))
        self.w_lat = float(g("w_lat", 1.5))
        self.w_switch = float(g("w_switch", 0.8))
        self.chain_s = float(g("chain_s", 3.0))
        # Crossing latch: once CROSS is chosen close-in on fresh evidence,
        # COMMIT through the blind final stretch (the FSM's proven
        # insight, imported as a latched maneuver). Re-arbitration is
        # suspended until plane-cross/pass/breach/timer.
        self.latch_range_m = float(g("latch_range_m", 2.5))
        self.latch_margin_s = float(g("latch_margin_s", 0.8))
        # Latch overrun: fly THROUGH the believed plane by this much (the
        # believed plane runs ahead of the physical one — T2f ledger).
        self.latch_overrun_m = float(g("latch_overrun_m", 0.8))
        # Safe-default floor (R2G run-4: post-collision attitude fiction
        # made EVERY candidate score -24 and the argmax still flew at
        # 2 m/s toward a 31m phantom). When the best prediction is this
        # bad, the right maneuver is to stop, not "least bad".
        self.score_floor = float(g("score_floor", -1.5))
        # Fiction guards (imported from the FSM's hard-won rules): a gate
        # reading >2m above us is attitude/estimator fiction on this
        # course (R2G run-1 climbed 2m into overhead structure chasing
        # one); a target beyond this range is a far-gate relock, not a
        # target to fly at.
        self.fiction_high_m = float(g("fiction_high_m", 2.0))
        self.fiction_far_m = float(g("fiction_far_m", 12.0))
        self.scan_yaw = float(g("scan_yaw_rps", 0.6))
        self.brake_s = float(g("brake_s", 0.8))
        self.vz_cap = float(g("vz_cap_mps", 1.0))
        self.blind_hold = bool(p.get("planner.search.blind_hold_enable",
                                     default=False))
        self.ibvs_cfg = IbvsConfig(
            enable=True,
            lat_gain=float(p.get("planner.ibvs.lat_gain", default=1.6)),
            vert_gain=float(p.get("planner.ibvs.vert_gain", default=1.2)),
            yaw_gain=float(p.get("planner.ibvs.yaw_gain", default=1.5)),
            max_lat_mps=float(p.get("planner.ibvs.max_lat_mps", default=1.5)),
            max_vert_mps=float(p.get("planner.ibvs.max_vert_mps", default=1.0)),
            yaw_cap_rps=float(p.get("planner.ibvs.yaw_cap_rps", default=0.8)))
        self.center_fresh_s = float(p.get("planner.ibvs.center_fresh_s",
                                          default=0.3))
        self.cam_fov = float(p.get("perception.camera.fov_deg"))
        self.cam_pitch = float(p.get("perception.camera.mount_pitch_deg",
                                     default=0.0))
        # Mutable agent state (the minimum a pilot carries between ticks).
        self._action = SCAN
        self._brake_until_ns: int | None = None
        self._chain_until_ns: int | None = None
        self._latch_until_ns: int | None = None
        self._latch_v: np.ndarray | None = None
        self._latch_yaw = 0.0
        self._latch_breach = 0
        self._last_seen_side = 1.0
        self.last_decision: dict | None = None

    # -- events ---------------------------------------------------------------

    def on_gate_passed(self, now_ns: int) -> None:
        """A pass opens the chaining window: fly forward and scan for the
        successor instead of treating the empty belief as 'lost'."""
        self._chain_until_ns = now_ns + int(self.chain_s * 1e9)
        self._clear_latch()

    def on_collision(self, now_ns: int) -> None:
        self._brake_until_ns = now_ns + int(self.brake_s * 1e9)
        self._chain_until_ns = None
        self._clear_latch()
        self._action = BRAKE

    def _clear_latch(self) -> None:
        self._latch_until_ns = None
        self._latch_v = None
        self._latch_yaw = 0.0
        self._latch_breach = 0

    def reset(self) -> None:
        self._action = SCAN
        self._brake_until_ns = None
        self._chain_until_ns = None
        self._clear_latch()
        self._last_seen_side = 1.0
        self.last_decision = None

    # -- rollout --------------------------------------------------------------

    def _rollout(self, d_true: np.ndarray, age0: float,
                 v_cmd: np.ndarray, v_true: np.ndarray,
                 looming: float) -> dict:
        """Predict the outcome of flying v_cmd for the horizon.

        World belief: the gate is static; our commanded velocity is
        achieved through a first-order lag (tau_s). Returns the utility
        terms; the caller weighs them. All frames are body-at-decision
        (yaw ignored over a 1.5s horizon at these speeds — the error is
        second-order next to the belief noise this guards against).
        """
        steps = max(1, int(round(self.horizon_s / self.dt_s)))
        rel = d_true.astype(float).copy()   # gate in TRUE frame [fwd,rt,dn]
        dist0 = float(np.linalg.norm(rel))
        crossed = False
        cross_lat = None
        cross_dz = None
        low_pen = 0.0
        for k in range(1, steps + 1):
            t = k * self.dt_s
            achieved = 1.0 - math.exp(-t / self.tau_s)
            step_v = v_true * achieved
            prev_fwd = rel[0]
            rel = rel - step_v * self.dt_s
            if not crossed and prev_fwd > 0.0 >= rel[0]:
                crossed = True
                cross_lat = float(abs(rel[1]))
                cross_dz = float(rel[2])    # + = gate below = crossing HIGH
            if not crossed and rel[0] < 1.8 \
                    and rel[2] < -self.low_margin_m:
                # ADVANCING below the gate line inside the terminal zone:
                # the pedestal-strike precondition. Proportional to the
                # meters flown forward while low — standing still low is
                # safe, flying forward low is how R2E/R2F died.
                low_pen += ((-float(rel[2]) - self.low_margin_m)
                            * max(float(step_v[0]), 0.0) * self.dt_s)
        dist1 = float(np.linalg.norm(rel))
        # Blind motion: horizontal flight on stale belief is the killer;
        # vertical correction is the escape maneuver — half weight.
        blind_speed = (abs(float(v_cmd[0])) + abs(float(v_cmd[1]))
                       + 0.5 * abs(float(v_cmd[2])))
        return {
            "progress": dist0 - dist1,
            "crossed": crossed,
            "cross_lat": cross_lat,
            "cross_dz": cross_dz,
            "low_pen": low_pen,
            "blind_pen": age0 * blind_speed,
            "loom_pen": looming * max(float(v_cmd[0]), 0.0),
            "lat_pen": abs(float(rel[1])) if rel[0] < 2.0 else 0.0,
        }

    def _score(self, c: _Candidate, d_true, age0, looming,
               can_cross: bool, v_true) -> None:
        r = self._rollout(d_true, age0, c.v_body, v_true, looming)
        conf = math.exp(-age0 / max(self.conf_tau_s, 1e-3))
        s = self.w_progress * r["progress"] * conf
        if r["crossed"]:
            in_corridor = (r["cross_lat"] is not None
                           and r["cross_lat"] <= self.corridor_m
                           and -self.cross_low_m <= r["cross_dz"]
                           <= self.cross_high_m)
            if can_cross and in_corridor:
                s += self.w_cross
            else:
                # Predicted to reach the plane outside the corridor or on
                # stale belief: that is a frame/pedestal strike, not a pass.
                s -= self.w_cross
        s -= self.w_low * r["low_pen"]
        s -= self.w_blind * r["blind_pen"]
        s -= self.w_loom * r["loom_pen"]
        s -= self.w_lat * r["lat_pen"]
        if c.action == self._action:
            s += self.w_switch          # hysteresis: stay the course on ties
        c.score = s
        c.terms = {k: (round(v, 3) if isinstance(v, float) else v)
                   for k, v in r.items()}

    # -- decision -------------------------------------------------------------

    def decide(self, now_ns: int, state: StateEstimate,
               looming: float) -> Setpoint:
        # Collision reflex outranks deliberation (safety envelope).
        if self._brake_until_ns is not None:
            if now_ns < self._brake_until_ns:
                self._emit(now_ns, BRAKE, [], looming, reflex="collision")
                return Setpoint(phase="recover", v_body=np.zeros(3),
                                yaw_rate=0.0)
            self._brake_until_ns = None

        gate = state.gate_rel
        if gate is not None and abs(float(gate.t[0])) > 0.05:
            self._last_seen_side = 1.0 if gate.t[0] > 0 else -1.0

        # Active crossing latch: fly the committed vector through the
        # blind final stretch. Exits: pass/collision (events), fresh
        # corridor breach, or the physics-sized timer.
        if self._latch_until_ns is not None:
            if now_ns >= self._latch_until_ns:
                self._clear_latch()
                self._brake_until_ns = now_ns + int(self.brake_s * 1e9)
                self._emit(now_ns, BRAKE, [], looming, reflex="latch_timeout")
                return Setpoint(phase="recover", v_body=np.zeros(3),
                                yaw_rate=0.0)
            if gate is not None and state.gate_rel_age_s <= self.cross_max_age_s:
                q_true = quat_multiply(
                    level_quat(state.level_roll, state.level_pitch),
                    state.q_att)
                d_true = quat_rotate(q_true, ap.cam_to_body(gate.t))
                # Breach only in the OUTER latch: inside ~0.85m nothing
                # can change (momentum carries to the plane regardless) and
                # a brake there coasts INTO the frame — the FSM's no-abort
                # braking band, relearned on the mock (2026-07-29: a
                # tightened low bound breached at 1.2m and the brake slid
                # into the gate).
                breach = (0.85 < d_true[0] < 1.5
                          and (abs(float(d_true[1])) > self.corridor_m
                               # Asymmetric: LOW (gate above, d2<0) is the
                               # pedestal side — tight; HIGH is a bar
                               # graze at worst — loose.
                               or float(d_true[2]) < -(self.cross_low_m + 0.3)
                               or float(d_true[2]) > self.cross_high_m + 0.2))
                self._latch_breach = self._latch_breach + 1 if breach else 0
                if self._latch_breach >= 4:
                    self._clear_latch()
                    self._brake_until_ns = now_ns + int(self.brake_s * 1e9)
                    self._emit(now_ns, BRAKE, [], looming,
                               reflex="latch_breach")
                    self.last_decision["breach_geom"] = {
                        "fwd": round(float(d_true[0]), 2),
                        "lat": round(float(d_true[1]), 2),
                        "dz": round(float(d_true[2]), 2)}
                    return Setpoint(phase="recover", v_body=np.zeros(3),
                                    yaw_rate=0.0)
                # Live-steer while fresh: refresh the latched vector.
                aim_l = ap.cam_to_body(gate.t) - np.array(
                    [0.0, 0.0, self.aim_up_m])
                n = float(np.linalg.norm(aim_l))
                if n > 1e-6:
                    self._latch_v = aim_l / n * self.cross_speed
                self._latch_yaw = ap.yaw_rate_to_bearing(gate, 1.2)
            elif (state.gate_center_px is not None
                  and state.image_size is not None
                  and state.gate_center_age_s <= self.center_fresh_s):
                # 3D stale but the blob is live (run-8: the ring left the
                # detector at 1.3m while far gates kept firing; the pixel
                # track is the only honest steering left) — IBVS-refine
                # the latched vector through the blind crossing.
                vy, vz, yw = ibvs_centering(
                    state.gate_center_px, state.image_size,
                    self.cam_fov, self.cam_pitch, self.ibvs_cfg)
                self._latch_v = np.array([self.cross_speed, vy, vz])
                self._latch_yaw = yw
            self._emit(now_ns, CROSS, [], looming, reflex="latch")
            return Setpoint(phase="commit", v_body=self._latch_v,
                            yaw_rate=self._latch_yaw, ibvs=True)

        # No gate belief: chain after a pass, otherwise scan from a stand.
        if gate is None:
            if self._chain_until_ns is not None and now_ns < self._chain_until_ns:
                sp = Setpoint(phase=_PHASE[CHAIN],
                              v_body=np.array([self.advance_speed * 0.6,
                                               0.0, 0.0]),
                              yaw_rate=self.scan_yaw * self._last_seen_side)
                self._set_action(CHAIN)
                self._emit(now_ns, CHAIN, [], looming)
                return sp
            self._set_action(SCAN)
            self._emit(now_ns, SCAN, [], looming)
            return Setpoint(phase=_PHASE[SCAN], v_body=np.zeros(3),
                            yaw_rate=self.scan_yaw * self._last_seen_side,
                            blind_hold=self.blind_hold)
        self._chain_until_ns = None

        # Fiction guards BEFORE deliberation: never fly at fiction.
        d_body_pre = ap.cam_to_body(gate.t)
        q_true_pre = quat_multiply(level_quat(state.level_roll,
                                              state.level_pitch), state.q_att)
        d_true_pre = quat_rotate(q_true_pre, d_body_pre)
        dist_pre = float(np.linalg.norm(d_body_pre))
        if (float(d_true_pre[2]) < -self.fiction_high_m
                or dist_pre > self.fiction_far_m):
            self._set_action(SCAN)
            self._emit(now_ns, SCAN, [], looming, reflex="fiction")
            return Setpoint(phase=_PHASE[SCAN], v_body=np.zeros(3),
                            yaw_rate=self.scan_yaw * self._last_seen_side,
                            blind_hold=self.blind_hold)

        # World belief for the rollout — in the TRUE (gravity-referenced)
        # frame. The body frame rides the airframe's 17.8deg rest tilt;
        # rolling out true-vertical positions with body-frame velocities
        # manufactured a +3m phantom climb in the first mock autopsy.
        # Rotate ONCE here; candidates are constructed in body axes (what
        # the backend flies) and their rollouts use the rotated copy.
        d_body = ap.cam_to_body(gate.t)
        q_true = quat_multiply(level_quat(state.level_roll,
                                          state.level_pitch), state.q_att)
        d_true = quat_rotate(q_true, d_body)
        tdz = float(d_true[2])
        age0 = float(state.gate_rel_age_s)
        dist = float(np.linalg.norm(d_body))
        aim = d_body - np.array([0.0, 0.0, self.aim_up_m])  # body LOS aim
        aim_n = aim / max(float(np.linalg.norm(aim)), 1e-6)
        lat_null = float(np.clip(1.2 * d_body[1], -0.8, 0.8))
        vz_align = float(np.clip(1.0 * (tdz - 0.0), -self.vz_cap, self.vz_cap))
        yaw_gate = ap.yaw_rate_to_bearing(gate, 1.2)

        # IBVS pixel refinement for the terminal maneuver when the 3D pose
        # is stale but the blob is live (the ported servo, agent-side).
        ibvs_terms = None
        if (state.gate_center_px is not None and state.image_size is not None
                and state.gate_center_age_s <= self.center_fresh_s
                and age0 > self.cross_max_age_s):
            ibvs_terms = ibvs_centering(state.gate_center_px,
                                        state.image_size, self.cam_fov,
                                        self.cam_pitch, self.ibvs_cfg)

        can_cross = age0 <= self.cross_max_age_s or ibvs_terms is not None

        cands: list[_Candidate] = [
            _Candidate(CROSS, aim_n * self.cross_speed, yaw_gate),
            _Candidate(ADVANCE,
                       aim_n * min(self.advance_speed,
                                   max(0.8, dist * 0.6))
                       + np.array([0.0, lat_null, 0.0]) * 0.3,
                       yaw_gate),
            _Candidate(CLIMB, np.array([self.climb_fwd, lat_null * 0.5,
                                        vz_align]), yaw_gate),
            _Candidate(BRAKE, np.zeros(3), 0.0),
            _Candidate(SCAN, np.zeros(3), self.scan_yaw * self._last_seen_side),
        ]
        if ibvs_terms is not None:
            vy, vz, yw = ibvs_terms
            cands[0] = _Candidate(CROSS, np.array([self.cross_speed, vy, vz]),
                                  yw)
        for c in cands:
            v_true = quat_rotate(q_true, c.v_body)
            self._score(c, d_true, age0, looming, can_cross, v_true)
        best = max(cands, key=lambda c: c.score)
        if best.score < self.score_floor:
            # Every prediction is bad: uncertainty stops (never argmax of
            # garbage — the R2G run-4 death).
            self._set_action(BRAKE)
            self._emit(now_ns, BRAKE, cands, looming, reflex="floor")
            return Setpoint(phase=_PHASE[BRAKE], v_body=np.zeros(3),
                            yaw_rate=0.0)
        self._set_action(best.action)
        self._emit(now_ns, best.action, cands, looming)
        if (best.action == CROSS and dist <= self.latch_range_m
                and age0 <= self.cross_max_age_s):
            # Commit through the final stretch: physics-sized window.
            self._latch_v = best.v_body
            self._latch_yaw = best.yaw_rate
            self._latch_breach = 0
            self._latch_until_ns = now_ns + int(
                ((dist + self.latch_overrun_m) / max(self.cross_speed, 0.1)
                 + self.latch_margin_s) * 1e9)
        return Setpoint(phase=_PHASE[best.action], v_body=best.v_body,
                        yaw_rate=best.yaw_rate,
                        ibvs=(best.action == CROSS and ibvs_terms is not None))

    # -- bookkeeping ----------------------------------------------------------

    def _set_action(self, action: str) -> None:
        self._action = action

    def _emit(self, now_ns: int, chosen: str, cands: list[_Candidate],
              looming: float, reflex: str | None = None) -> None:
        self.last_decision = {
            "ts_ns": now_ns,
            "action": chosen,
            "reflex": reflex,
            "looming": round(float(looming), 4),
            "scores": {c.action: round(c.score, 3) for c in cands},
            "terms": {c.action: c.terms for c in cands},
        }
