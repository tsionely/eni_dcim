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


def terminal_observe(oracle: "TerminalOracle", state, feature,
                     feature_age_s: float | None, d_star: float = 0.8,
                     gate_w: float = 1.6, pitch_cal_rad: float = -0.33,
                     e_z_clamp_m: float = 0.45) -> float | None:
    """OBSERVER step, independent of ownership/enable/phase (advisory
    permanent rule: measurement and readiness are observer
    responsibilities; ownership only decides whether an already MATURE
    estimate may actuate). Runs every commit tick — control arms and
    out-of-engagement-range ticks included — so the history exists
    before the authority it gates, by construction."""
    if (feature is None or feature_age_s is None or feature_age_s > 0.15
            or feature.span_px <= 1.0
            or feature.cert_status not in ("certified", "probation")
            or state.image_size is None):
        return None
    cy = state.image_size[1] / 2.0
    fx = state.image_size[0] / 2.0                # 90deg HFOV pinhole
    e_meas = gate_w * (cy - feature.y_top_px) / feature.span_px - d_star
    # Trim compensation (advisory-7 SS2.1): the row formula's zero moves
    # with pitch (~0.018*R/deg); compensate the DELTA from the graze
    # calibration trim so d*=0.8 carries across speed changes.
    q = np.asarray(state.q_att, dtype=np.float64)
    pitch_t = float(np.arcsin(np.clip(
        2.0 * (q[0] * q[2] - q[3] * q[1]), -1.0, 1.0))) \
        + float(state.level_pitch)
    e_meas += gate_w * fx * (np.tan(pitch_t) - np.tan(pitch_cal_rad)) \
        / feature.span_px
    # Authority clamp (SS1.4): bounded to the eroded opening (A8 inherits).
    e_meas = float(np.clip(e_meas, -e_z_clamp_m, e_z_clamp_m))
    oracle.observe(float(feature.ts_ns) / 1e9, e_meas)
    return e_meas


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
    q_lvl = level_quat(state.level_roll, state.level_pitch)
    # Observer step (idempotent per unique exposure: observe() dedupes
    # by timestamp, so a prior app-level terminal_observe call for the
    # same exposure is harmless). Without a persistent oracle the
    # measurement still runs (throwaway history) so a fresh identified
    # feature always outranks the believed channel.
    e_meas = terminal_observe(oracle if oracle is not None
                              else TerminalOracle(),
                              state, feature, feature_age_s,
                              d_star, gate_w, pitch_cal_rad, e_z_clamp_m)
    # Source-provenance + admission gate (advisory first-enable
    # predicate): a NEW capture additionally requires the oracle READY
    # (>=6 unique exposures, span >=0.15s, no gap >0.12s, finite robust
    # slope) and the ADMISSION corridor |e_x| + 2*sigma_x + 0.06 <=
    # 0.30m — the first-enable cycle validates a controller on an
    # already-plausible arrival, it does not rescue the opening's edge.
    # Once TERM owns, the latch/loss-grace semantics govern instead.
    capture_ok = certified
    if oracle is not None and arbiter.owner != TERM_OWNER:
        capture_ok = certified and oracle.ready()
        if capture_ok:
            from aigp.planning.vertical_terminal import (crossing_error,
                                                         crossing_sigma)
            vz_vis = oracle.v_z_visual() * oracle.rate_authority()
            e_now = e_meas if e_meas is not None else (
                oracle._hist[-1][1] if oracle._hist else 0.0)
            e_x = crossing_error(e_now, vz_vis, tau_s)
            # Admission sigma horizon (mock A/B rerun on the fixed wire
            # was STILL 0/10 captures — arithmetic, not wiring: at the
            # 2.5m engagement range tau~1.37s makes 2*sigma_x + 0.06 =
            # 0.35 > the 0.30 corridor even with a perfect forecast,
            # deferring capture below ~1.8m where certification dies.
            # The uncertainty that matters for admission is over the
            # UNCORRECTED interval (damping+freeze ~0.45s) — rate
            # errors before damping are corrected by the servo itself.
            # tau_cap awaits advisory ratification (pre-registered
            # corridor; constant parameterized, not hard-coded).
            tau_sig = min(tau_s, 0.45)
            # Oracle measurement sigmas, MEASURED not assumed: the F2
            # graze series scattered ~0.02 RMS sample-to-sample; 0.05 /
            # 0.10 carry a x2.5 margin on that. (The legacy 0.10/0.15
            # placeholders are the quarantined believed-channel numbers
            # — with them 2*sigma + 0.06 exceeds the 0.30 corridor at
            # any tau >= 0.45 and admission can never pass.)
            s_x = crossing_sigma(0.05, vz_vis, 0.10, tau_sig)
            capture_ok = abs(e_x) + 2.0 * s_x + 0.06 <= 0.30
    owner = arbiter.tick(commit_active=True, same_gate=True,
                         certified=capture_ok,
                         feature_age_s=state.gate_rel_age_s,
                         phase=phase_hint)
    if owner != TERM_OWNER or gr is None:
        return owner, None, prev_vz_up
    # e_z source ladder: the PIXEL-ROW oracle owns when a fresh,
    # identity-held feature exists (measured above); the believed
    # channel is the drift-biased fallback for the no-oracle path only.
    if oracle is not None:
        e_z = oracle.update(e_meas, dt, vz_max)
        if e_z is None:
            # Neutral: no certified history this approach — the servo
            # has nothing honest to act on. e_z NEVER reverts to the
            # believed source (§3.3: that wire stays cut); command zero
            # correction and let the base profile carry through.
            e_z = 0.0
        # Source provenance (the advisory's no-go condition): the
        # crossing-rate input comes from the ORACLE history's robust
        # slope, never solely from the believed state — that channel
        # drifts exactly in the final blind interval. No slope =>
        # neutral rate, never the believed fallback.
        vz_vis = oracle.v_z_visual()
        v_z_up = (vz_vis * oracle.rate_authority()
                  if vz_vis is not None else 0.0)
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
    # Body conversion, LEGACY-CONSISTENT: the geometrically-honest
    # adapter (q_true with the u·v cross-term) assumes the vehicle
    # flies its v_body literally along IMU axes — under the co-tuned
    # legacy cascade it does not (it flies near-horizontal with PID
    # trims bridging), and the cross-term injects ~+0.55 m/s of
    # fictitious climb at 1.8 m/s trim (caught by the admission unit
    # test). The empirically-validated vertical lever is the altitude
    # hold's own: v_bz ~ -vz_up, scaled by the mount-tilt cosine.
    # The honest adapter returns with the frame-unification package.
    cos_tilt = float(np.cos(state.level_pitch) * np.cos(state.level_roll))
    if cos_tilt < 0.7:
        # Outside the recorded tilt envelope: vertical_authority_limited
        # — never amplify the command without bound (advisory SS2).
        return owner, None, prev_vz_up
    v_bz = -vz_up / cos_tilt
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
                 hold_s: float = 0.3, decay_s: float = 0.3,
                 min_samples: int = 6, min_span_s: float = 0.15,
                 max_gap_s: float = 0.12) -> None:
        self.jump_floor = jump_floor_m
        self.jump_k = jump_k
        self.hold_s = hold_s
        self.decay_s = decay_s
        self.min_samples = int(min_samples)
        self.min_span_s = float(min_span_s)
        self.max_gap_s = float(max_gap_s)
        self.e_z: float | None = None
        self.stale_s = 0.0
        self._violations = 0
        self.disarmed = False
        # Unique-exposure oracle history (ts_s, e_z): source of the
        # VISUAL vertical rate. The advisory's no-go condition: the
        # crossing forecast must never take v_z solely from the
        # believed state — that channel drifts exactly when it matters.
        self._hist: list[tuple[float, float]] = []

    def reset(self) -> None:
        self.e_z = None
        self.stale_s = 0.0
        self._violations = 0
        self.disarmed = False
        self._hist = []

    def observe(self, ts_s: float, e_meas: float) -> None:
        """Record one UNIQUE exposure's accepted measurement (caller
        dedupes by feature timestamp — rebroadcasts overstate evidence
        ~8-9x)."""
        if self._hist and ts_s <= self._hist[-1][0]:
            return
        self._hist.append((ts_s, e_meas))
        if len(self._hist) > 40:
            self._hist = self._hist[-40:]

    def history_stats(self) -> tuple[int, float, float]:
        """(n_unique, span_s, max_gap_s) of the recent history."""
        n = len(self._hist)
        if n < 2:
            return n, 0.0, float("inf")
        ts = [t for t, _ in self._hist]
        gaps = [b - a for a, b in zip(ts, ts[1:])]
        return n, ts[-1] - ts[0], max(gaps)

    def v_z_visual(self) -> float | None:
        """Vertical rate from the ORACLE history (Theil-Sen), +up.

        e_z is the +up correction required; the drone climbing shrinks
        it, so v_z = -d(e_z)/dt."""
        from aigp.planning.vertical_terminal import robust_slope
        if len(self._hist) < 4:
            return None
        recent = self._hist[-12:]
        slope = robust_slope([t for t, _ in recent], [e for _, e in recent])
        if slope is None:
            return None
        return -float(slope)

    def ready(self) -> bool:
        """Advisory first-enable readiness: enough UNIQUE history, a
        real time span, no long gap, a finite robust slope."""
        n, span, gap = self.history_stats()
        return (n >= self.min_samples and span >= self.min_span_s
                and gap <= self.max_gap_s
                and self.v_z_visual() is not None
                and not self.disarmed)

    def rate_authority(self) -> float:
        """Advisory-7B §1: the barely-ready window's slope is ~4x
        noisier than a half-second one (sigma ~0.4 vs ~0.1 m/s at the
        margined per-sample 0.05). The predicate gates WHETHER v_z
        speaks; this schedule sets HOW LOUDLY — readiness onset must
        not inject rate jitter at exactly the wrong moment."""
        n, span, _ = self.history_stats()
        return float(min(1.0, (span / 0.3) * (n / 10.0)))

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
