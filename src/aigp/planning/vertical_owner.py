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
            or feature.cert_status != "certified"
            or state.image_size is None):
        return None
    # Ladder first release: only the two METRIC rungs act (FULL_QUAD
    # from whole quads; SIDE_PAIR from observed certified side-pair
    # separation + top row). Sparse/row-only modes stay in shadow —
    # they may inform telemetry, never metrology.
    if getattr(feature, "mode", "FULL_QUAD") in ("BAR_ROW_ONLY",
                                                 "SIDE_PAIR_ROW_ONLY"):
        return None
    # Honest-detection scale gate at the oracle's front door: the span
    # and the BELIEVED range must tell the same story before a pixel
    # row becomes metrology. Three real 1.8-cohort flights fed the
    # oracle certified BAR_FULL quads whose span implied ~5m while the
    # believed gate stood <1.2m — the SUCCESSOR gate, crisp behind the
    # wash, wearing gate-1's certificate; e_meas pegged the clamp and
    # admission (rightly) refused two centered passes. Identity
    # machinery certifies continuity; only cross-channel consistency
    # certifies that the row measures THIS gate. The honest product is
    # GEOMETRY, not a constant: fx*W = (image_w/2)*1.6 — 512 px*m at
    # 640 wide (audited band 300-800) but 256 at the low-load mock's
    # 320x180, where a literal 300 floor rejected every honest feature
    # 10/10 (caught by the calibrated QA rerun). Ratios preserved.
    if state.gate_rel is not None:
        r_b = float(state.gate_rel.t[2])
        honest = 0.5 * float(state.image_size[0]) * gate_w
        if r_b >= 0.5 and not (0.59 * honest <= feature.span_px * r_b
                               <= 1.56 * honest):
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
    active = oracle.observe(float(feature.ts_ns) / 1e9, e_meas,
                            source=getattr(feature, "mode", "FULL_QUAD"))
    # Only the ACTIVE rung's measurement may act this tick; inactive-
    # rung observations were recorded (maturing toward a transition)
    # but must not steer — one estimate, one meaning per number.
    return e_meas if active else None


def terminal_override(arbiter: "VerticalOwnerArbiter", state, setpoint_v_body,
                      certified: bool, tau_s: float, margin_m: float,
                      prev_vz_up: float | None, dt: float,
                      vz_max: float = 0.6, az_max: float = 2.0,
                      feature=None, feature_age_s: float | None = None,
                      d_star: float = 0.8, gate_w: float = 1.6,
                      oracle: "TerminalOracle | None" = None,
                      pitch_cal_rad: float = -0.33,
                      e_z_clamp_m: float = 0.45,
                      t_tail_s: float = 0.45,
                      corridor_m: float = 0.30,
                      cmd_clamp_m: float = 0.10):
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
        # Conservative first-live authority policy (RESPONSE19
        # disposition SS3): only the highest-fidelity rung may open the
        # control door; the side rung MAINTAINS an already-captured
        # owner (its primary purpose — metrology after the full quad
        # disappears) but may not first-capture in its first cohort.
        capture_ok = (certified and oracle.ready()
                      and oracle.active_source == "FULL_QUAD")
        if capture_ok:
            from aigp.planning.vertical_terminal import (crossing_error,
                                                         crossing_sigma)
            vz_vis = oracle.v_z_visual() * oracle.rate_authority()
            e_now = e_meas if e_meas is not None else (
                oracle._hist[-1][1] if oracle._hist else 0.0)
            # RATIFIED admission horizon (both advisories, independently
            # identical): the mean forecast and the sigma must ride the
            # SAME uncorrected tail. The sigma-only cap left the mean
            # ballistic over full tau — a benign 0.08 m/s measured rate
            # at tau~1.37 consumed the whole 0.106m budget, and the
            # third mock A/B proved it: engaged+ready 9/10 around
            # 2.47m, owner=term 0/10. Admission prices the OPEN-LOOP
            # tail only; rate before damping is the servo's job.
            # t_tail_s = max(0.45 damping+freeze, dynamic no-return
            # tail) — supplied by the caller from the abort-band
            # geometry, so a loss after retreat stops being possible is
            # never priced with the shorter healthy-loop horizon.
            h_tail = min(tau_s, t_tail_s)
            e_x = crossing_error(e_now, vz_vis, h_tail)
            # Oracle measurement sigmas, MEASURED not assumed: the F2
            # graze series scattered ~0.02 RMS sample-to-sample; 0.05 /
            # 0.10 carry a x2.5 margin on that. (The legacy 0.10/0.15
            # placeholders are the quarantined believed-channel numbers
            # — with them 2*sigma + 0.06 exceeds the 0.30 corridor at
            # any tau >= 0.45 and admission can never pass.)
            sig_e, sig_v = oracle.sigmas()
            s_x = crossing_sigma(sig_e, vz_vis, sig_v, h_tail)
            # corridor_m is CORRIDOR_INTERIM (advisory-10 ruling): the
            # operational admission band 0.30, explicitly labeled and
            # time-boxed — expiry condition is the cohort-2 R5 sigma
            # library, after which corridor := C_contact = 0.18 with
            # evidence-based sigmas. Geometry vs epistemology stay
            # separate currencies; the interim operates against the
            # weaker geometric bound while the epistemology matures.
            capture_ok = abs(e_x) + 2.0 * s_x + 0.06 <= corridor_m
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
    # COMMAND clamp (advisory-10 geometry-chain ruling, decomposed from
    # the measurement bound): the correction target the servo may act
    # on is bounded to cmd_clamp = C_contact(0.18) - 0.06 oracle
    # calibration - 0.02 rail slack = 0.10 — a wrong e_z may displace
    # the commanded crossing by at most the no-touch band minus guards.
    # The MEASUREMENT stays honest at +-e_z_clamp_m (0.45): admission
    # and the continuous test must be able to SEE an off-corridor
    # arrival to refuse it; clamping the measurement to 0.10 would
    # blind the epistemology exactly where it must block (the safety
    # fixture pins this). Larger vehicle shrinks every allowance;
    # nothing grows.
    # Asymmetric command clamp (advisory-15 SS1.4 interim): the upward
    # allowance is ZERO while h_up is a contested/unknown envelope —
    # the downward arm (-0.10) is the program's one evidence-backed
    # clamp (0.10 <= measured C_bottom 0.162 - 0.06, by 2mm). Positive
    # e_z (climb wanted) is refused at the command site; admission
    # already restricts arrivals to near-centered, so nothing material
    # is lost. Reverts only via the freeze-exception channel with the
    # forensics attached.
    e_z_cmd = float(np.clip(e_z, -cmd_clamp_m, 0.0))
    g = compute_terminal_guidance(
        e_z=e_z_cmd, sigma_e=0.10, v_z=v_z_up, sigma_v=0.15, tau_s=tau_s,
        margin_m=margin_m, prev_phase=None, vz_max=vz_max, az_max=az_max)
    if g["vz_cmd"] is None:                     # freeze: hold applied target
        vz_goal = prev_vz_up if prev_vz_up is not None else 0.0
    else:
        vz_goal = g["vz_cmd"]
    # Upward allowance 0 (interim, see clamp above): arresting a sink
    # (raising vz toward zero) stays legal; commanding an actual climb
    # (vz_goal > 0) does not.
    vz_goal = min(vz_goal, 0.0)
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
        # LADDER (both rulings): _hist is the ACTIVE source's history;
        # the inactive rung accumulates in _hist_other. A slope is
        # NEVER fitted across a source boundary — a constant inter-
        # source bias stepping through one Theil-Sen history would
        # masquerade as vertical velocity (the S3 failure class).
        self._hist: list[tuple[float, float]] = []
        self._hist_other: list[tuple[float, float]] = []
        self.active_source = "FULL_QUAD"
        self._last_full: tuple[float, float] | None = None
        self._last_side: tuple[float, float] | None = None
        self._overlap_deltas: list[tuple[float, float]] = []  # (ts, de)
        self._overlap_ok = False
        self._upgrade_streak = 0
        self._transition_grace = False

    def reset(self) -> None:
        self.e_z = None
        self.stale_s = 0.0
        self._violations = 0
        self.disarmed = False
        self._hist = []
        self._hist_other = []
        self.active_source = "FULL_QUAD"
        self._last_full = None
        self._last_side = None
        self._overlap_deltas = []
        self._overlap_ok = False
        self._upgrade_streak = 0
        self._transition_grace = False

    SIGMAS = {"FULL_QUAD": (0.05, 0.10),
              # Side-pair rung: margined analogs (x1.5) until the R5
              # library matures per-rung residuals — sigmas are source
              # constants (advisory-13 SS2.2), never inherited.
              "SIDE_PAIR": (0.075, 0.15)}

    def sigmas(self) -> tuple[float, float]:
        """(sigma_e, sigma_v) of the ACTIVE source."""
        return self.SIGMAS[self.active_source]

    def _slope_of(self, hist: list):
        from aigp.planning.vertical_terminal import robust_slope
        tail = self._fresh_tail(hist)
        if len(tail) < 4:
            return None
        recent = tail[-12:]
        return robust_slope([t for t, _ in recent], [e for _, e in recent])

    @staticmethod
    def _push(hist: list, ts_s: float, e: float) -> None:
        if hist and ts_s <= hist[-1][0]:
            return
        hist.append((ts_s, e))
        if len(hist) > 40:
            del hist[:-40]

    def _fresh_tail(self, hist: list) -> list:
        """The contiguous evidence ending at the newest sample: walk
        back while consecutive gaps stay within max_gap_s. Readiness,
        maturity and the visual rate are properties of evidence that
        is actually contiguous — a single mid-approach outage must not
        permanently veto an approach whose recent stream is rich (the
        whole-history gap statistic was doing exactly that), and a
        slope must never be fitted across an outage."""
        if len(hist) < 2:
            return list(hist)
        i = len(hist) - 1
        while i > 0 and hist[i][0] - hist[i - 1][0] <= self.max_gap_s:
            i -= 1
        return hist[i:]

    def _mature(self, hist: list) -> bool:
        tail = self._fresh_tail(hist)
        if len(tail) < self.min_samples:
            return False
        return tail[-1][0] - tail[0][0] >= self.min_span_s

    def observe(self, ts_s: float, e_meas: float,
                source: str = "FULL_QUAD") -> bool:
        """Record one UNIQUE exposure's accepted measurement (caller
        dedupes by feature timestamp — rebroadcasts overstate evidence
        ~8-9x). Returns True when the observation belongs to the
        ACTIVE source (i.e. may act this tick), False when it was
        recorded to the inactive rung only.

        Source transitions (the ladder's fine print): downgrade
        FULL->SIDE only when the full history has gone stale, the side
        history is independently MATURE, and the most recent overlap
        passed |e_side - e_full| <= max(0.10, 3*sigma_side) — a
        measurement-model change, never a phase/ownership event.
        Upgrade back only after 3 consecutive consistent full-quad
        observations (hysteresis)."""
        if source in ("BAR_FULL",):
            source = "FULL_QUAD"
        if source not in ("FULL_QUAD", "SIDE_PAIR"):
            return False                      # shadow rungs: no metrology
        # Overlap bookkeeping (for the transition consistency gate).
        if source == "FULL_QUAD":
            self._last_full = (ts_s, e_meas)
        else:
            self._last_side = (ts_s, e_meas)
        # EXACT-EXPOSURE pairing (binding: nearest-timestamp joins are
        # prohibited — the latest FULL and latest SIDE can come from
        # adjacent images and a mismatched pair corrupts the 0.10 hard
        # step gate). Our exposure id IS the exposure timestamp; both
        # measurement models of one image carry the identical ts.
        if (self._last_full is not None and self._last_side is not None
                and self._last_full[0] == self._last_side[0]):
            de = self._last_side[1] - self._last_full[1]
            ts_pair = max(self._last_full[0], self._last_side[0])
            if (not self._overlap_deltas
                    or ts_pair > self._overlap_deltas[-1][0]):
                self._overlap_deltas.append((ts_pair, de))
                if len(self._overlap_deltas) > 12:
                    del self._overlap_deltas[:-12]
            # Switch legality (RESPONSE19 disposition SS2): >=3 paired
            # unique-exposure overlaps, newest pair fresh, and the
            # HARD absolute step limit |median(de)| <= 0.10 — an
            # inflated provisional sigma must never relax it (the old
            # max(0.10, 3*sigma_side) permitted a 0.225m source step
            # approaching the whole corridor). Rate compatibility:
            # opposing slope signs at the transition forbid it.
            # PAIRED TAIL (binding clarification): the maximal recent
            # suffix of pairs with adjacent pair-to-pair gap <= 0.12s,
            # newest pair fresh — ALL qualifying pairs are current, so
            # stale overlap evidence collected before range/obliquity/
            # identity changed cannot authorize a switch.
            i = len(self._overlap_deltas) - 1
            while (i > 0 and self._overlap_deltas[i][0]
                   - self._overlap_deltas[i - 1][0] <= 0.12):
                i -= 1
            tail_pairs = self._overlap_deltas[i:]
            self._overlap_ok = False
            if (len(tail_pairs) >= 3
                    and ts_pair - tail_pairs[-1][0] <= 0.12
                    and abs(float(np.median(
                        [d for _, d in tail_pairs]))) <= 0.10):
                v_act = self._slope_of(self._hist)
                v_oth = self._slope_of(self._hist_other)
                deadband = 0.05
                if (v_act is None or v_oth is None
                        or abs(v_act) <= deadband or abs(v_oth) <= deadband
                        or (v_act > 0) == (v_oth > 0)):
                    self._overlap_ok = True
        if source == self.active_source:
            self._push(self._hist, ts_s, e_meas)
            if self.active_source == "SIDE_PAIR":
                self._upgrade_streak = 0      # no full obs this tick
            return True
        # Inactive-rung observation.
        self._push(self._hist_other, ts_s, e_meas)
        if self.active_source == "FULL_QUAD":
            # Downgrade check: full gone stale + side mature + overlap.
            full_stale = (not self._hist
                          or ts_s - self._hist[-1][0] > self.max_gap_s)
            if (full_stale and self._mature(self._hist_other)
                    and self._overlap_ok):
                self._hist, self._hist_other = self._hist_other, self._hist
                self.active_source = "SIDE_PAIR"
                self._upgrade_streak = 0
                self._transition_grace = True
                return True
        else:
            # Full-quad seen while side is active: hysteresis count.
            # Upgrade on the ruling's bar — 3 consecutive CONSISTENT
            # full-quad observations; the fresh-tail readiness clock
            # then re-matures the returning rung honestly (no capture
            # authority until it does).
            ref = self.e_z if self.e_z is not None else e_meas
            if abs(e_meas - ref) <= 0.10:
                self._upgrade_streak += 1
            else:
                self._upgrade_streak = 0
            if self._upgrade_streak >= 3:
                self._hist, self._hist_other = self._hist_other, self._hist
                self.active_source = "FULL_QUAD"
                self._upgrade_streak = 0
                self._transition_grace = True
                return True
        return False

    def history_stats(self) -> tuple[int, float, float]:
        """(n_unique, span_s, max_gap_s) of the CONTIGUOUS fresh tail
        (see _fresh_tail — readiness is a property of contiguous
        evidence; ladder pre-registration in RESPONSE19)."""
        tail = self._fresh_tail(self._hist)
        n = len(tail)
        if n < 2:
            return n, 0.0, float("inf")
        ts = [t for t, _ in tail]
        gaps = [b - a for a, b in zip(ts, ts[1:])]
        return n, ts[-1] - ts[0], max(gaps)

    def v_z_visual(self) -> float | None:
        """Vertical rate from the ORACLE history (Theil-Sen), +up.

        e_z is the +up correction required; the drone climbing shrinks
        it, so v_z = -d(e_z)/dt."""
        from aigp.planning.vertical_terminal import robust_slope
        tail = self._fresh_tail(self._hist)
        if len(tail) < 4:
            return None
        recent = tail[-12:]
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

    def ready_legacy(self) -> bool:
        """The PRE-correction readiness (whole-attempt gap statistic),
        computed for cohort-4's dual-readiness log only — the semantic
        A/B measuring itself in situ (advisory-14 SS2.1). Never used
        for any decision."""
        n = len(self._hist)
        if n < self.min_samples:
            return False
        ts = [t for t, _ in self._hist]
        gaps = [b - a for a, b in zip(ts, ts[1:])]
        return (ts[-1] - ts[0] >= self.min_span_s
                and (not gaps or max(gaps) <= self.max_gap_s)
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
            if self._transition_grace:
                # One-shot, DIAGNOSTIC-ONLY (RESPONSE19 disposition
                # SS2.3): lifts the single temporal-innovation alarm a
                # certified <=0.10m source step legally causes; touches
                # no admission, envelope, maturity, age, phase or
                # ownership logic.
                self._transition_grace = False
                limit = max(limit, 0.10 + self.jump_floor)
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
