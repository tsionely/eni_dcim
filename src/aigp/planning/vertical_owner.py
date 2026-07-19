"""Single-owner vertical arbitration + body-frame adapter (advisory-4 #2).

The decisive architecture rule, verbatim from the round-4 spec:

    one terminal estimate -> one terminal vertical controller ->
    one world-up velocity target -> one common limiter ->
    one attitude-aware body-frame conversion

At every control tick there is exactly ONE vertical owner (ALT_OWNER or
TERM_OWNER). The non-owner runs in shadow and contributes exactly zero:
blending two vertical controllers at the actuator boundary makes the
safety envelope meaningless and reintroduces the open-loop patch war
this design ends. Legacy terms (aim_up / altitude hold / sink
insurance) are all suppressed while the terminal channel owns.

Conventions: vz here is WORLD-UP positive (module boundary); our stack
is NED (world z DOWN, body FRD), so world-up in NED is (0,0,-1) and a
level-flight upward command maps to negative body-z. All conversion to
body-z happens in exactly one place: body_z_for_world_up().
"""
from __future__ import annotations

import numpy as np

from aigp.estimation.attitude_filter import quat_rotate_inv

ALT_OWNER = "alt"
TERM_OWNER = "term"


def slew_up_velocity(previous: float, goal: float, dt: float,
                     a_up: float, a_down: float) -> float:
    """Asymmetric slew toward goal (all +up, rates in m/s^2)."""
    delta = goal - previous
    if delta >= 0.0:
        delta = min(delta, a_up * dt)
    else:
        delta = max(delta, -a_down * dt)
    return previous + delta


def world_up_in_body(q_att: np.ndarray) -> np.ndarray:
    """World-up unit vector expressed in the (FRD, NED-world) body frame."""
    return quat_rotate_inv(q_att, np.array([0.0, 0.0, -1.0]))


def body_z_for_world_up(vz_cmd_up: float, q_att: np.ndarray,
                        v_bx: float, v_by: float) -> tuple[float, bool]:
    """Body-z setpoint achieving the commanded WORLD-UP velocity.

    Solves u_B . v_B = vz_cmd_up given the already-chosen horizontal
    body components — a plain v_bz = -vz misallocates exactly during
    pitch-up braking, which is the failing regime. Returns (v_bz, ok);
    ok=False when |u_B[2]| < 0.5 (body-z nearly horizontal — do NOT
    divide through a small number; caller must reduce tilt demand or
    declare vertical authority unavailable).
    """
    u = world_up_in_body(q_att)
    if abs(float(u[2])) < 0.5:
        return 0.0, False
    v_bz = (vz_cmd_up - float(u[0]) * v_bx - float(u[1]) * v_by) / float(u[2])
    return v_bz, True


def init_transfer_trim(prev_applied_up: float, new_raw_up: float) -> float:
    """Bumpless transfer: trim making the first post-switch output exactly
    continuous (new_raw + trim == prev_applied)."""
    return prev_applied_up - new_raw_up


def decay_trim(trim: float, dt: float, rate: float, saturated: bool) -> float:
    """Drive the transfer trim to zero under a slew budget — but NEVER
    while the final command is saturated (a hidden trim decaying behind
    saturation reappears as a jump when saturation clears)."""
    if saturated:
        return trim
    step = rate * dt
    if trim > step:
        return trim - step
    if trim < -step:
        return trim + step
    return 0.0


def shadow_terminal_check(arbiter: "VerticalOwnerArbiter", setpoint_v_body,
                          q_att: np.ndarray, gate_age_s: float,
                          commit_active: bool, ts_ns: int,
                          certified: bool = False):
    """One non-actuating shadow tick (release-contract step 2).

    Runs the arbiter on real inputs (certificate state included, once
    the perception side supplies it) and round-trips the LEGACY
    command's world-up component through the adapter: the reconstruction
    must reproduce the legacy body-z to numerical precision. Returns a
    ShadowTerminal record for the flight log; touches nothing else —
    even a TERM owner decision here actuates nothing (there is no
    enable bit yet), it only tells us what WOULD have happened.
    """
    from aigp.core.messages import ShadowTerminal
    from aigp.estimation.attitude_filter import quat_rotate

    v = np.asarray(setpoint_v_body, dtype=np.float64)
    up_legacy = -float(quat_rotate(q_att, v)[2])       # NED: up = -z
    v_bz, ok = body_z_for_world_up(up_legacy, q_att, float(v[0]), float(v[1]))
    delta = float(v[2]) - v_bz if ok else 0.0
    owner = arbiter.tick(commit_active=commit_active, same_gate=True,
                         certified=certified, feature_age_s=gate_age_s,
                         phase="position")
    return ShadowTerminal(ts_ns=ts_ns, owner=owner, up_legacy_mps=up_legacy,
                          adapter_delta_mps=delta, adapter_ok=ok)


def terminal_override(arbiter: "VerticalOwnerArbiter", state, setpoint_v_body,
                      certified: bool, tau_s: float, margin_m: float,
                      prev_vz_up: float | None, dt: float,
                      vz_max: float = 0.6, az_max: float = 2.0,
                      feature=None, feature_age_s: float | None = None,
                      d_star: float = 0.8, gate_w: float = 1.6,
                      oracle: "TerminalOracle | None" = None,
                      pitch_cal_rad: float = -0.33,
                      e_z_clamp_m: float = 0.45):
    """The ONE final-boundary override (enable-bit path).

    Computes the terminal vertical command from the CERTIFIED gate state
    and, when the arbiter grants TERM ownership, returns the body-z that
    replaces the legacy vertical — via exactly one limiter and one
    attitude-aware conversion. Returns (owner, v_bz_or_None, vz_up):
    v_bz None => legacy keeps the tick (ALT owner, adapter
    ill-conditioned, or guidance freeze with no held target).

    v1 sources (documented in the design contract): e_z = TRUE-vertical
    offset of the continuously-corrected gate estimate (aim = opening
    center per the M1 verdict, d* recalibration rides the accumulating
    certified features); v_z from the world state, de-tilted the same
    way; tau supplied by the caller. All verticals compose the measured
    rest attitude (state.level_*) — the raw filter frame is pitched
    ~17.8 deg from true level (the phase6b phantom).
    """
    from aigp.estimation.attitude_filter import quat_multiply, quat_rotate
    from aigp.planning.approach import level_quat, true_world_dz
    from aigp.planning.vertical_terminal import compute_terminal_guidance

    gr = state.gate_rel
    phase_hint = "position"
    owner = arbiter.tick(commit_active=True, same_gate=True,
                         certified=certified,
                         feature_age_s=state.gate_rel_age_s,
                         phase=phase_hint)
    if owner != TERM_OWNER or gr is None:
        return owner, None, prev_vz_up
    q_lvl = level_quat(state.level_roll, state.level_pitch)
    # e_z source ladder (enable build): the PIXEL-ROW oracle owns when a
    # fresh, identity-held feature exists — phase6e F2 proved the
    # believed channel carries a +0.3-0.5m bias at the plane (attitude
    # drift) while the oracle read the graze exactly (e_z -0.56 at a
    # crossing pixel-truth ~+0.5 high; d*=0.8 validated to ~6cm by that
    # label). Fallback: the believed TRUE-vertical (still de-tilted).
    e_meas = None
    if (feature is not None and feature_age_s is not None
            and feature_age_s <= 0.15 and feature.span_px > 1.0
            and feature.cert_status in ("certified", "probation")
            and state.image_size is not None):
        cy = state.image_size[1] / 2.0
        fx = state.image_size[0] / 2.0            # 90deg HFOV pinhole
        e_meas = gate_w * (cy - feature.y_top_px) / feature.span_px - d_star
        # Advisory-7 §2.1: the row formula's zero moves with trim pitch
        # (~0.018·R per degree). d*=0.8 was graze-calibrated at
        # pitch_cal; compensate the DELTA from that trim per tick so the
        # calibration carries across the 1.8 m/s speed change.
        q = np.asarray(state.q_att, dtype=np.float64)
        pitch_t = float(np.arcsin(np.clip(
            2.0 * (q[0] * q[2] - q[3] * q[1]), -1.0, 1.0))) \
            + float(state.level_pitch)
        e_meas += gate_w * fx * (np.tan(pitch_t) - np.tan(pitch_cal_rad)) \
            / feature.span_px
        # Authority clamp (§1.4): commanded crossing target bounded to
        # the eroded opening (0.8 - half-extent - buffer; A8 inherits).
        e_meas = float(np.clip(e_meas, -e_z_clamp_m, e_z_clamp_m))
    if oracle is not None:
        e_z = oracle.update(e_meas, dt, vz_max)
        if e_z is None:
            # Neutral: no certified history this approach — the servo
            # has nothing honest to act on. e_z NEVER reverts to the
            # believed source (§3.3: that wire stays cut); command zero
            # correction and let the base profile carry through.
            e_z = 0.0
    else:
        e_z = e_meas if e_meas is not None else -true_world_dz(
            gr, state.q_att, state.level_roll, state.level_pitch)
    v_z_up = -float(quat_rotate(q_lvl, np.asarray(state.v_world,
                                                  dtype=np.float64))[2])
    g = compute_terminal_guidance(
        e_z=e_z, sigma_e=0.10, v_z=v_z_up, sigma_v=0.15, tau_s=tau_s,
        margin_m=margin_m, prev_phase=None, vz_max=vz_max, az_max=az_max)
    if g["vz_cmd"] is None:                     # freeze: hold applied target
        vz_goal = prev_vz_up if prev_vz_up is not None else 0.0
    else:
        vz_goal = g["vz_cmd"]
    vz_up = slew_up_velocity(prev_vz_up if prev_vz_up is not None else vz_goal,
                             vz_goal, dt, az_max, az_max)
    v = np.asarray(setpoint_v_body, dtype=np.float64)
    q_true = quat_multiply(q_lvl, np.asarray(state.q_att, dtype=np.float64))
    v_bz, ok = body_z_for_world_up(vz_up, q_true, float(v[0]), float(v[1]))
    if not ok:
        return owner, None, prev_vz_up
    return owner, float(v_bz), float(vz_up)


class TerminalOracle:
    """Advisory-7 §3 guard state: asymmetric by design.

    - Self-consistency disarms; cross-magnitude (oracle vs believed)
      only logs — large disagreement with the believed state is the
      EXPECTED condition, it is the bias this channel corrects.
    - Jump limit per certified tick: |Δe_z| <= vz_max·Δt + floor;
      k=3 consecutive violations => disarm to neutral-decay for the
      rest of the approach.
    - Staleness: hold-last <= 0.3s, then decay to zero. e_z NEVER
      reverts to the believed source — that wire stays cut.
    - Disarm != retreat: neutral means carry-through on the base
      profile with the correction decaying, nothing irreversible.
    """

    def __init__(self, jump_floor_m: float = 0.05, jump_k: int = 3,
                 hold_s: float = 0.3, decay_s: float = 0.3) -> None:
        self.jump_floor = jump_floor_m
        self.jump_k = jump_k
        self.hold_s = hold_s
        self.decay_s = decay_s
        self.e_z: float | None = None
        self.stale_s = 0.0
        self._violations = 0
        self.disarmed = False

    def reset(self) -> None:
        self.e_z = None
        self.stale_s = 0.0
        self._violations = 0
        self.disarmed = False

    def update(self, e_meas: float | None, dt: float,
               vz_max: float) -> float | None:
        """Feed one tick; returns the effective e_z or None (neutral)."""
        if self.disarmed:
            e_meas = None                     # neutral-decay to the end
        if e_meas is not None:
            limit = vz_max * max(dt, 1e-3) + self.jump_floor
            if self.e_z is not None and abs(e_meas - self.e_z) > limit:
                self._violations += 1
                if self._violations >= self.jump_k:
                    self.disarmed = True      # flagged; neutral-decay
                    e_meas = None
                else:
                    e_meas = self.e_z         # reject the jump, hold
            else:
                self._violations = 0
        if e_meas is not None:
            self.e_z = float(e_meas)
            self.stale_s = 0.0
            return self.e_z
        # No fresh certified measurement: hold-last, then decay to zero.
        if self.e_z is None:
            return None
        self.stale_s += dt
        if self.stale_s <= self.hold_s:
            return self.e_z
        self.e_z *= max(0.0, 1.0 - dt / self.decay_s)
        if abs(self.e_z) < 0.02:
            self.e_z = 0.0
        return self.e_z


class VerticalOwnerArbiter:
    """Owner state machine: capture conditions, no-return latch, grace.

    Capture ALT->TERM requires ALL of: commit active, same locked gate,
    certified structure identity, >=3 consecutive healthy UNIQUE
    exposures, feature age <= 0.10s, guidance phase still 'position'
    (never a first capture in damping/freeze — a late feature may
    inform telemetry/abort but must not cause a last-second ownership
    switch). Handback TERM->ALT happens only on gate-passed, retreat
    complete, or attempt termination; once the terminal schedule has
    reached damping, loss of the feature does NOT hand back (the
    no-return latch: reactivating a stale position controller exactly
    where the schedule removed position correction is the crash class
    this exists to prevent).
    """

    def __init__(self, min_healthy_exposures: int = 3,
                 max_feature_age_s: float = 0.10) -> None:
        self.owner = ALT_OWNER
        self.latched = False           # no-return: reached damping under TERM
        self._healthy_streak = 0
        self.min_healthy = int(min_healthy_exposures)
        self.max_age = float(max_feature_age_s)

    def note_exposure(self, healthy: bool) -> None:
        """Feed once per UNIQUE exposure (never per message — the sim
        rebroadcasts each exposure ~8-9x)."""
        self._healthy_streak = self._healthy_streak + 1 if healthy else 0

    def tick(self, commit_active: bool, same_gate: bool, certified: bool,
             feature_age_s: float, phase: str) -> str:
        if self.owner == TERM_OWNER:
            if phase in ("damping", "freeze"):
                self.latched = True
            if not commit_active:
                # gate passed / retreat complete / attempt terminated
                self.owner = ALT_OWNER
                self.latched = False
                self._healthy_streak = 0
            elif not self.latched and not certified and not same_gate:
                # identity lost while still in position phase: abort path
                self.owner = ALT_OWNER
                self._healthy_streak = 0
            return self.owner
        # ALT_OWNER: capture check.
        if (commit_active and same_gate and certified
                and self._healthy_streak >= self.min_healthy
                and feature_age_s <= self.max_age
                and phase == "position"):
            self.owner = TERM_OWNER
        return self.owner
