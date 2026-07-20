"""Arbiter/adapter invariants from the round-4 override-arbitration spec."""
import numpy as np
import pytest

from aigp.estimation.attitude_filter import quat_multiply, quat_rotate
from aigp.planning.vertical_owner import (
    ALT_OWNER,
    TERM_OWNER,
    VerticalOwnerArbiter,
    body_z_for_world_up,
    decay_trim,
    init_transfer_trim,
    slew_up_velocity,
)

LEVEL = np.array([1.0, 0.0, 0.0, 0.0])


def quat_from_euler(roll: float, pitch: float, yaw: float) -> np.ndarray:
    qr = np.array([np.cos(roll / 2), np.sin(roll / 2), 0.0, 0.0])
    qp = np.array([np.cos(pitch / 2), 0.0, np.sin(pitch / 2), 0.0])
    qy = np.array([np.cos(yaw / 2), 0.0, 0.0, np.sin(yaw / 2)])
    return quat_multiply(qy, quat_multiply(qp, qr))


def test_level_flight_up_command_is_negative_body_z():
    v_bz, ok = body_z_for_world_up(0.5, LEVEL, v_bx=2.0, v_by=0.0)
    assert ok and v_bz == pytest.approx(-0.5)


def test_pitched_conversion_preserves_world_up():
    """The adapter invariant: |u_W . R v_B - vz_cmd| < 1e-3 across the
    braking-pitch envelope — a plain -vz fails exactly there."""
    for pitch in (-0.35, -0.15, 0.15, 0.35):
        q = quat_from_euler(0.05, pitch, 0.3)
        v_bx, v_by = 2.2, -0.4
        v_bz, ok = body_z_for_world_up(0.6, q, v_bx, v_by)
        assert ok
        v_world = quat_rotate(q, np.array([v_bx, v_by, v_bz]))
        achieved_up = -float(v_world[2])          # NED: up = -z
        assert achieved_up == pytest.approx(0.6, abs=1e-3)
        # And the naive adapter is measurably wrong when pitched:
        naive_world = quat_rotate(q, np.array([v_bx, v_by, -0.6]))
        assert abs(-float(naive_world[2]) - 0.6) > 0.01


def test_conditioning_guard_refuses_near_horizontal_body_z():
    q = quat_from_euler(0.0, 1.2, 0.0)            # ~69 deg pitch
    _, ok = body_z_for_world_up(0.5, q, 1.0, 0.0)
    assert not ok


def test_slew_is_asymmetric_and_bounded():
    assert slew_up_velocity(0.0, 1.0, 0.004, a_up=2.0, a_down=4.0) == \
        pytest.approx(0.008)
    assert slew_up_velocity(0.0, -1.0, 0.004, a_up=2.0, a_down=4.0) == \
        pytest.approx(-0.016)
    assert slew_up_velocity(0.5, 0.5001, 1.0, 2.0, 2.0) == pytest.approx(0.5001)


def test_bumpless_transfer_first_sample_continuous():
    trim = init_transfer_trim(prev_applied_up=0.42, new_raw_up=0.10)
    assert 0.10 + trim == pytest.approx(0.42)
    # Trim decays under budget, but NEVER behind saturation.
    t1 = decay_trim(trim, dt=0.004, rate=2.0, saturated=False)
    assert abs(t1) < abs(trim)
    assert decay_trim(trim, dt=0.004, rate=2.0, saturated=True) == trim
    assert decay_trim(0.005, dt=0.004, rate=2.0, saturated=False) == 0.0


def make_arbiter():
    a = VerticalOwnerArbiter()
    for _ in range(3):
        a.note_exposure(True)
    return a


def test_capture_requires_all_conditions():
    a = make_arbiter()
    assert a.tick(True, True, True, 0.05, "position") == TERM_OWNER
    # Missing any one condition -> no capture.
    for kwargs in (
        dict(commit_active=False, same_gate=True, certified=True,
             feature_age_s=0.05, phase="position"),
        dict(commit_active=True, same_gate=True, certified=False,
             feature_age_s=0.05, phase="position"),
        dict(commit_active=True, same_gate=True, certified=True,
             feature_age_s=0.5, phase="position"),
    ):
        b = make_arbiter()
        assert b.tick(**kwargs) == ALT_OWNER


def test_no_first_capture_in_damping_or_freeze():
    for phase in ("damping", "freeze"):
        a = make_arbiter()
        assert a.tick(True, True, True, 0.02, phase) == ALT_OWNER


def test_no_return_latch_holds_through_feature_loss():
    """Once the terminal schedule reached damping, losing the feature
    must NOT reactivate the stale altitude hold."""
    a = make_arbiter()
    assert a.tick(True, True, True, 0.05, "position") == TERM_OWNER
    assert a.tick(True, True, True, 0.05, "damping") == TERM_OWNER
    assert a.latched
    # Feature dies, identity gone — still terminal-owned.
    assert a.tick(True, False, False, 9.0, "freeze") == TERM_OWNER
    # Attempt ends (gate passed / retreat) -> handback.
    assert a.tick(False, False, False, 9.0, "freeze") == ALT_OWNER
    assert not a.latched


def test_identity_loss_in_position_hands_back():
    a = make_arbiter()
    assert a.tick(True, True, True, 0.05, "position") == TERM_OWNER
    assert a.tick(True, False, False, 0.3, "position") == ALT_OWNER


def test_shadow_check_is_consistent_and_never_captures():
    """Release-contract step 2: on every shadow tick the adapter must
    round-trip the legacy command exactly (delta ~ 0) and the owner must
    stay ALT while nothing is certified — across the attitude envelope."""
    from aigp.planning.vertical_owner import shadow_terminal_check
    a = VerticalOwnerArbiter()
    for _ in range(10):
        a.note_exposure(True)               # even with healthy exposures
    for pitch in (-0.35, 0.0, 0.3):
        q = quat_from_euler(0.1, pitch, -0.7)
        s = shadow_terminal_check(a, np.array([2.4, -0.5, -0.3]), q,
                                  gate_age_s=0.05, commit_active=True,
                                  ts_ns=1)
        assert s.owner == ALT_OWNER          # certified=False: no capture
        assert s.adapter_ok
        assert abs(s.adapter_delta_mps) < 1e-9


def test_terminal_override_directions_and_gating():
    """Enable-bit path: LOW commands climb, HIGH commands descend
    (symmetric +-0.10 command clamp, advisory-16 restoration); without
    certification the override yields None."""
    from aigp.core.messages import RelPose, StateEstimate
    from aigp.planning.vertical_owner import terminal_override

    def st(ty):
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, ty, 1.8]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True)

    a = make_arbiter()
    v_sp = np.array([2.4, 0.0, 0.0])
    owner, v_bz, vz = terminal_override(a, st(-0.4), v_sp, True, 0.9, 0.55,
                                        None, 0.016)
    assert owner == TERM_OWNER and v_bz is not None
    # LOW -> climb (advisory-16: the interim upward-allowance-zero
    # retired with the voided 0.744 evidence; symmetric clamp restored).
    assert v_bz < 0
    # HIGH case with a fresh arbiter:
    b = make_arbiter()
    owner, v_bz2, _ = terminal_override(b, st(+0.4), v_sp, True, 0.9, 0.55,
                                        None, 0.016)
    assert v_bz2 is not None and v_bz2 > 0    # HIGH -> descend
    # Uncertified: no capture, legacy keeps the tick.
    c = VerticalOwnerArbiter()
    owner, v_bz3, _ = terminal_override(c, st(-0.4), v_sp, False, 0.9, 0.55,
                                        None, 0.016)
    assert owner == ALT_OWNER and v_bz3 is None


def test_at_most_one_transition_per_tick():
    """Release contract: a handback tick must not also recapture — even
    with capture conditions instantly perfect again (no same-tick
    handback-and-recapture races)."""
    a = make_arbiter()
    assert a.tick(True, True, True, 0.05, "position") == TERM_OWNER
    # Attempt ends while conditions for a fresh capture are all true:
    # the tick performs ONE transition (handback) and returns.
    for _ in range(3):
        a.note_exposure(True)
    assert a.tick(False, True, True, 0.05, "position") == ALT_OWNER
    # Capture only happens on the NEXT tick.
    for _ in range(3):
        a.note_exposure(True)
    assert a.tick(True, True, True, 0.05, "position") == TERM_OWNER


def test_pixel_oracle_formula_pins_f2_graze():
    """The enable-build oracle formula against the REAL logged FEATURE
    records of the phase6e F2 graze (fixture 20260719T143556). Cursor's
    independent computation gave e_z = -0.554/-0.561/-0.591; the
    crossing's pixel-truth was ~+0.5 high — d*=0.8 validated to ~6cm
    by the label. e_z = W*(cy - y_top)/span - d*."""
    for y, s, expect in ((0.4, 1169.1, -0.554), (0.0, 1203.8, -0.561),
                         (-0.5, 1381.5, -0.591)):
        e = 1.6 * (180.0 - y) / s - 0.8
        assert e == pytest.approx(expect, abs=0.005)


def test_terminal_override_prefers_pixel_oracle():
    """Phase6e F2: believed said 'centered' while the pixel oracle read
    -0.56 (HIGH). With a fresh identity-held feature the override must
    command DESCEND from the oracle, ignoring the biased believed."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import terminal_override

    st = StateEstimate(
        ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
        gate_rel=RelPose(t=np.array([0.0, 0.0, 0.6]),      # believed: centered
                         normal=np.array([0.0, 0.0, -1.0])),
        gate_rel_age_s=0.05, gate_center_px=(320, 180),
        image_size=(640, 360), healthy=True)
    feat = TerminalFeature(ts_ns=0, y_top_px=0.0, span_px=1203.8,
                           center_x_px=320.0, cert_status="certified",
                           mode="BAR_FULL")
    a = make_arbiter()
    owner, v_bz, _ = terminal_override(a, st, np.array([2.0, 0.0, 0.0]),
                                       True, 0.5, 0.55, None, 0.016,
                                       feature=feat, feature_age_s=0.05)
    assert owner == TERM_OWNER and v_bz is not None
    assert v_bz > 0.05          # descend (NED body-z positive) — oracle wins
    # Same state WITHOUT the feature: believed-centered -> ~no descend.
    b = make_arbiter()
    owner2, v_bz2, _ = terminal_override(b, st, np.array([2.0, 0.0, 0.0]),
                                         True, 0.5, 0.55, None, 0.016)
    assert v_bz2 is None or abs(v_bz2) < 0.05
    # Stale feature -> falls back to believed.
    c = make_arbiter()
    owner3, v_bz3, _ = terminal_override(c, st, np.array([2.0, 0.0, 0.0]),
                                         True, 0.5, 0.55, None, 0.016,
                                         feature=feat, feature_age_s=0.5)
    assert v_bz3 is None or abs(v_bz3) < 0.05


def test_oracle_guard_jump_disarms_not_magnitude():
    """Advisory-7 §3: self-consistency disarms, cross-magnitude never.
    Three consecutive jump violations -> neutral-decay for the rest of
    the approach; a large but SMOOTH correction is untouched."""
    from aigp.planning.vertical_owner import TerminalOracle
    g = TerminalOracle()
    assert g.update(-0.56, 0.02, 0.6) == pytest.approx(-0.56)   # big is fine
    assert g.update(-0.55, 0.02, 0.6) == pytest.approx(-0.55)   # smooth
    for _ in range(3):                                          # wild jumps
        g.update(+0.80, 0.02, 0.6)
    assert g.disarmed
    # Post-disarm: held value decays toward zero, never a fresh command.
    vals = [g.update(-0.56, 0.02, 0.6) for _ in range(70)]
    assert abs(vals[-1]) < 0.05


def test_oracle_staleness_holds_then_decays_never_believed():
    """§3.3: hold-last <=0.3s, then decay to zero. The believed source
    stays cut — terminal_override with an oracle and no feature must
    command ~zero correction even when believed screams 'low'."""
    from aigp.core.messages import RelPose, StateEstimate
    from aigp.planning.vertical_owner import TerminalOracle, terminal_override

    g = TerminalOracle()
    assert g.update(0.30, 0.02, 0.6) == pytest.approx(0.30)
    for _ in range(10):                       # 0.2s: inside hold window
        v = g.update(None, 0.02, 0.6)
    assert v == pytest.approx(0.30)
    for _ in range(40):                       # decay
        v = g.update(None, 0.02, 0.6)
    assert abs(v) < 0.05

    st = StateEstimate(
        ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
        gate_rel=RelPose(t=np.array([0.0, -0.4, 1.8]),   # believed: LOW
                         normal=np.array([0.0, 0.0, -1.0])),
        gate_rel_age_s=0.05, gate_center_px=(320, 180),
        image_size=(640, 360), healthy=True)
    a = make_arbiter()
    fresh_oracle = TerminalOracle()
    owner, v_bz, _ = terminal_override(a, st, np.array([1.8, 0.0, 0.0]),
                                       True, 0.9, 0.55, None, 0.016,
                                       oracle=fresh_oracle)
    # First-enable predicate: an EMPTY oracle history blocks capture —
    # 'capture without sufficient unique history' is a stop condition.
    assert owner == ALT_OWNER and v_bz is None


def test_readiness_and_admission_gate_capture():
    """The advisory's enable predicate end-to-end: capture requires
    >=6 unique exposures over >=0.15s with no long gap AND the inner
    admission corridor |e_x| + 2 sigma + 0.06 <= 0.30. v_z comes from
    the oracle history's Theil-Sen slope, never the believed state."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_override

    def st():
        # level_pitch matches the REAL rig (-0.311): the trim
        # compensation is calibrated at pitch_cal=-0.33 and a zero-tilt
        # test rig would inject a +0.22 phantom into e_meas.
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3),
            v_world=np.array([0.0, 0.0, 5.0]),   # believed: absurd sink
            gate_rel=RelPose(t=np.array([0.0, 0.0, 1.8]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    # Feature at exact center-aim: y_top such that e_z ~ 0.
    # e_z = 1.6*(180 - y)/span - 0.8 = 0  =>  y = 180 - 0.5*span.
    # span is PHYSICAL for the 1.8m rig (512 px.m / 1.8m): the scale
    # gate at the oracle door rejects span/range fiction.
    def feat(ts_ns, span=284.0):
        return TerminalFeature(ts_ns=ts_ns, y_top_px=180.0 - 0.5 * span,
                               span_px=span, center_x_px=320.0,
                               cert_status="certified", mode="BAR_FULL")

    a = make_arbiter()
    g = TerminalOracle()
    owner = None
    # Six unique exposures, 40ms apart: history builds, then capture.
    for i in range(7):
        owner, v_bz, _ = terminal_override(
            a, st(), np.array([1.8, 0.0, 0.0]), True, 0.6, 0.55, None,
            0.04, feature=feat(int(i * 0.04e9)), feature_age_s=0.02,
            oracle=g)
    assert owner == TERM_OWNER and v_bz is not None
    # Centered arrival, flat history: near-zero correction — the
    # believed 5 m/s sink fiction must NOT leak into the command.
    assert abs(v_bz) < 0.15
    # Admission corridor blocks a genuinely-off arrival: e_z ~ -0.45.
    b = make_arbiter()
    g2 = TerminalOracle()
    span = 284.0
    y_off = 180.0 - (0.45 - 0.8 + 0.8) * span / 1.6 - 0.5 * span  # e~-0.45
    for i in range(7):
        f = TerminalFeature(ts_ns=int(i * 0.04e9),
                            y_top_px=180.0 - 0.5 * span + 0.45 * span / 1.6,
                            span_px=span, center_x_px=320.0,
                            cert_status="certified", mode="BAR_FULL")
        owner2, v_bz2, _ = terminal_override(
            b, st(), np.array([1.8, 0.0, 0.0]), True, 0.6, 0.55, None,
            0.04, feature=f, feature_age_s=0.02, oracle=g2)
    assert owner2 == ALT_OWNER and v_bz2 is None


def test_sign_pin_raw_frame_quads_f2_final_3m():
    """Advisory-7 §2.3 sign test, pinned with REAL logged quads from the
    F2 graze final 3m (drone HIGH throughout -> e_z must be negative).
    Corners are RAW image pixels; 'helpfully' derotating them flips the
    verdict to +0.8 wrong-sign — the phase6g-era lesson, frozen here."""
    for y_top, span in ((158.5, 178.1), (135.0, 218.6), (61.0, 311.1)):
        e = 1.6 * (180.0 - y_top) / span - 0.8
        assert e < 0.0, f"wrong sign at y_top={y_top}"


def test_rate_authority_scales_with_window_richness():
    """Advisory-7B: the minimal predicate window (6 samples / 0.15s)
    speaks at reduced authority (~0.3); a half-second, well-sampled
    window speaks at full volume."""
    from aigp.planning.vertical_owner import TerminalOracle
    g = TerminalOracle()
    for i in range(6):
        g.observe(i * 0.03, 0.0)
    assert g.rate_authority() == pytest.approx((0.15 / 0.3) * 0.6, abs=0.01)
    g2 = TerminalOracle()
    for i in range(13):
        g2.observe(i * 0.04, 0.0)
    assert g2.rate_authority() == 1.0


def test_observer_matures_before_ownership_no_maturity_delay():
    """The permanent rule as a regression: with TERM disabled (control
    arm), the observer still matures the history; on the first enabled
    eligible tick, capture happens immediately — no history reset, no
    maturity delay."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import (TerminalOracle,
                                              terminal_observe,
                                              terminal_override)

    def st():
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, 1.8]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    def feat(ts, span=284.0):
        return TerminalFeature(ts_ns=ts, y_top_px=180.0 - 0.5 * span,
                               span_px=span, center_x_px=320.0,
                               cert_status="certified", mode="BAR_FULL")

    g = TerminalOracle()
    # 'Control' phase: observer only, no override calls at all.
    for i in range(7):
        terminal_observe(g, st(), feat(int(i * 0.04e9)), 0.02)
    assert g.ready()
    # Enable flips: FIRST override tick captures — mature history kept.
    a = make_arbiter()
    owner, v_bz, _ = terminal_override(a, st(), np.array([1.8, 0.0, 0.0]),
                                       True, 0.6, 0.55, None, 0.04,
                                       feature=feat(int(7 * 0.04e9)),
                                       feature_age_s=0.02, oracle=g)
    assert owner == TERM_OWNER and v_bz is not None


def test_admission_passable_at_engagement_range():
    """The 0/10-capture arithmetic, frozen as a test: at the 2.5m
    engagement range (tau~1.37s at 1.8 m/s) the corridor must be
    PASSABLE for a centered, flat-history approach — the admission
    sigma runs over the uncorrected damping horizon, not the full
    time-to-plane (rate errors before damping are servo-corrected)."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_override

    def st():
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, 2.4]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    def feat(ts, span=213.0):
        return TerminalFeature(ts_ns=ts, y_top_px=180.0 - 0.5 * span,
                               span_px=span, center_x_px=320.0,
                               cert_status="certified", mode="BAR_FULL")

    a = make_arbiter()
    g = TerminalOracle()
    owner = None
    for i in range(7):
        owner, v_bz, _ = terminal_override(
            a, st(), np.array([1.8, 0.0, 0.0]), True, 1.37, 0.55, None,
            0.04, feature=feat(int(i * 0.04e9)), feature_age_s=0.02,
            oracle=g)
    assert owner == TERM_OWNER, \
        "admission corridor impassable at its own engagement range"


def _ramp_rig(e_start, e_step, t_tail_s=0.45, ticks=7, span=213.0):
    """Drive terminal_override with a linearly-drifting oracle history
    (constant span => the trim shift is constant and drops out of the
    slope). Returns the final (owner, v_bz)."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_override

    def st():
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, 2.4]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    a = make_arbiter()
    g = TerminalOracle()
    owner, v_bz = None, None
    for i in range(ticks):
        e_i = e_start + i * e_step
        y_top = 180.0 - (e_i + 0.8) * span / 1.6
        f = TerminalFeature(ts_ns=int(i * 0.04e9), y_top_px=y_top,
                            span_px=span, center_x_px=320.0,
                            cert_status="certified", mode="BAR_FULL")
        owner, v_bz, _ = terminal_override(
            a, st(), np.array([1.8, 0.0, 0.0]), True, 1.37, 0.55, None,
            0.04, feature=f, feature_age_s=0.02, oracle=g,
            t_tail_s=t_tail_s)
    return owner, v_bz


def test_admission_mean_rides_the_tail_horizon_liveness():
    """RATIFIED admission rule (both advisories + the third mock A/B's
    engaged+ready-9/10 / owner-0/10 deadlock): the MEAN forecast rides
    the same uncorrected tail as the sigma. A converging approach with
    a real measured closing rate — the servo's own action — must ADMIT;
    full-tau ballistics extrapolated that same rate through the aim
    into a phantom overshoot and blocked every capture. Liveness
    fixture per the pattern book: the guard must pass what it exists
    for, not only block what it must."""
    owner, v_bz = _ramp_rig(e_start=0.28, e_step=-0.026)
    assert owner == TERM_OWNER and v_bz is not None
    # The parameter is live: pricing the whole flight as open-loop
    # (t_tail = full tau) restores the deadlock on the same rig.
    owner_full, _ = _ramp_rig(e_start=0.28, e_step=-0.026, t_tail_s=1.37)
    assert owner_full == ALT_OWNER


def test_admission_tail_mean_still_blocks_divergence():
    """Safety companion: a genuinely diverging arrival (drone sinking
    away from the aim, miss growing every exposure) stays blocked
    under the tail horizon — the fix admits the correctable, not the
    unrecoverable."""
    owner, v_bz = _ramp_rig(e_start=0.10, e_step=0.026)
    assert owner == ALT_OWNER and v_bz is None


def test_scale_gate_rejects_successor_wearing_certificate():
    """Pinned with REAL logged numbers (1.8 cohort, flights 202445 /
    201630): certified BAR_FULL quads with span~103px arrived while
    the believed gate stood at 1.0m — span*range=103 px.m against the
    honest 512 px.m — the successor gate, crisp behind the wash,
    wearing gate-1's certificate. Rows like that pegged e_meas at the
    clamp and (rightly) blocked admission on two centered passes. The
    scale gate refuses them at the oracle's front door; the honest
    F4-capture geometry (span 388 at 1.32m => 512) passes."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_observe

    def st(r):
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, r]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    def feat(span):
        return TerminalFeature(ts_ns=1, y_top_px=360.0, span_px=span,
                               center_x_px=320.0, cert_status="certified",
                               mode="BAR_FULL")

    g = TerminalOracle()
    assert terminal_observe(g, st(1.0), feat(103.0), 0.02) is None
    assert len(g._hist) == 0                      # fiction never enters
    g2 = TerminalOracle()
    assert terminal_observe(g2, st(1.32), feat(388.0), 0.02) is not None
    assert len(g2._hist) == 1


def test_cmd_clamp_bounds_correction_measurement_stays_honest():
    """Advisory-10 geometry chain, decomposed: the servo's correction
    TARGET is bounded to cmd_clamp=0.10 (C_contact 0.18 minus oracle
    calibration 0.06 minus rail slack 0.02) — a wrong e_z may displace
    the commanded crossing by at most the no-touch band minus guards.
    The MEASUREMENT stays honest at +-0.45: admission must still SEE an
    off-corridor arrival to refuse it (the existing admission-block
    fixture is that safety pin; this one pins the command side)."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import (TERM_OWNER, TerminalOracle,
                                              VerticalOwnerArbiter,
                                              terminal_override)

    def st():
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, 1.8]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    span = 284.0
    # e_meas ~ -0.30: honest, off-aim (drone high), within the 0.45
    # measurement bound but 3x the command clamp.
    y_top = 180.0 - 0.5 * span + 0.30 * span / 1.6

    a = VerticalOwnerArbiter()
    a.owner = TERM_OWNER                    # already captured; command path
    g = TerminalOracle()
    v_bz = None
    for i in range(7):
        f = TerminalFeature(ts_ns=int(i * 0.04e9), y_top_px=y_top,
                            span_px=span, center_x_px=320.0,
                            cert_status="certified", mode="BAR_FULL")
        owner, v_bz, _ = terminal_override(
            a, st(), np.array([1.8, 0.0, 0.0]), True, 1.0, 0.55, None,
            0.04, feature=f, feature_age_s=0.02, oracle=g)
    assert owner == TERM_OWNER and v_bz is not None
    # Correction bounded by the clamped target: |e_cmd|<=0.10 =>
    # |vz| <= 0.10/tau_min(0.25) = 0.40 (+slew headroom), never the
    # 0.6 vz_max a 0.30 target would command.
    assert abs(v_bz) <= 0.45


def test_corridor_param_is_live():
    """CORRIDOR_INTERIM is a real config lever: shrinking it to 0.10
    must block the same liveness rig the 0.30 interim admits (its
    floor alone is 0.194). Guard-parameter liveness per the pattern
    book."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_override

    def st():
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, 2.4]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    span = 213.0
    a = make_arbiter()
    g = TerminalOracle()
    owner = None
    for i in range(7):
        f = TerminalFeature(ts_ns=int(i * 0.04e9),
                            y_top_px=180.0 - 0.5 * span, span_px=span,
                            center_x_px=320.0, cert_status="certified",
                            mode="BAR_FULL")
        owner, _, _ = terminal_override(
            a, st(), np.array([1.8, 0.0, 0.0]), True, 1.37, 0.55, None,
            0.04, feature=f, feature_age_s=0.02, oracle=g,
            corridor_m=0.10)
    assert owner == ALT_OWNER


def test_scale_gate_follows_image_geometry():
    """The honest product is geometry, not a constant: at the low-load
    mock's 320x180 the honest fx*W is 256 px.m — a literal 300 floor
    rejected every honest mock feature (10/10, calibrated QA rerun).
    An honest low-res feature (span*R ~ 256) must observe; the same
    fiction ratio (~0.2x honest) must still be refused."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_observe

    def st(r):
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, r]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(160, 90),
            image_size=(320, 180), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    def feat(span):
        return TerminalFeature(ts_ns=1, y_top_px=90.0, span_px=span,
                               center_x_px=160.0, cert_status="certified",
                               mode="BAR_FULL")

    g = TerminalOracle()
    # Honest at 320 wide: span 128 at R=2.0 => product 256 = fx*W.
    assert terminal_observe(g, st(2.0), feat(128.0), 0.02) is not None
    # Fiction at the same resolution: successor-scale span.
    g2 = TerminalOracle()
    assert terminal_observe(g2, st(1.0), feat(52.0), 0.02) is None
    assert len(g2._hist) == 0


def _obs_series(g, t0, n, e0, slope, dt=0.04, source="FULL_QUAD"):
    from aigp.planning.vertical_owner import TerminalOracle  # noqa: F401
    for i in range(n):
        g.observe(t0 + i * dt, e0 + slope * i * dt, source=source)
    return t0 + (n - 1) * dt


def test_s3_source_offset_never_becomes_velocity():
    """Ladder gate S3: FULL_QUAD and SIDE_PAIR carry a constant +0.08
    inter-source bias with the SAME true slope. A mixed history would
    convert the step at the transition into a fictitious vertical
    rate; per-source histories must keep v_z equal to the true slope
    on both sides of the switch."""
    from aigp.planning.vertical_owner import TerminalOracle
    g = TerminalOracle()
    true_slope = -0.10                       # e shrinking 0.10 m/s
    # Overlap region: both rungs observing (full active), then full dies.
    t = 0.0
    for i in range(8):
        ts = i * 0.04
        g.observe(ts, 0.30 + true_slope * ts, source="FULL_QUAD")
        g.observe(ts, 0.38 + true_slope * ts, source="SIDE_PAIR")
    assert g.active_source == "FULL_QUAD"
    v_before = g.v_z_visual()
    assert v_before == pytest.approx(0.10, abs=0.02)
    # Full-quad stream dies (below ~2m); side continues alone.
    for i in range(8, 14):
        ts = i * 0.04
        active = g.observe(ts, 0.38 + true_slope * ts, source="SIDE_PAIR")
    assert g.active_source == "SIDE_PAIR"    # consistency-gated switch
    assert active                            # side now acts
    v_after = g.v_z_visual()
    assert v_after == pytest.approx(0.10, abs=0.02), \
        "the +0.08 source bias leaked into vertical rate"


def test_s2_switch_requires_overlap_consistency_and_hysteresis():
    """Ladder gate S2 (unit form): a side rung whose overlap
    disagreement exceeds max(0.10, 3 sigma_side) may mature forever —
    it never becomes the active source. And after a legal downgrade,
    upgrading back requires 3 consecutive consistent full-quad
    observations (hysteresis), not one lucky frame."""
    from aigp.planning.vertical_owner import TerminalOracle
    g = TerminalOracle()
    # Inconsistent side rung: bias 0.40 >> bound.
    for i in range(10):
        ts = i * 0.04
        g.observe(ts, 0.10, source="FULL_QUAD")
        g.observe(ts, 0.50, source="SIDE_PAIR")
    for i in range(10, 16):
        g.observe(i * 0.04, 0.50, source="SIDE_PAIR")
    assert g.active_source == "FULL_QUAD"    # never switched
    # Legal switch on a consistent rung.
    g2 = TerminalOracle()
    for i in range(8):
        ts = i * 0.04
        g2.observe(ts, 0.10, source="FULL_QUAD")
        g2.observe(ts, 0.14, source="SIDE_PAIR")
    for i in range(8, 14):
        g2.observe(i * 0.04, 0.14, source="SIDE_PAIR")
    assert g2.active_source == "SIDE_PAIR"
    g2.update(0.14, 0.02, 0.6)               # e_z reference for streak
    # Upgrade needs 3 consecutive consistent full observations.
    g2.observe(14 * 0.04, 0.10, source="FULL_QUAD")
    g2.observe(15 * 0.04, 0.10, source="FULL_QUAD")
    assert g2.active_source == "SIDE_PAIR"   # streak of 2: not yet
    g2.observe(16 * 0.04, 0.10, source="FULL_QUAD")
    assert g2.active_source == "FULL_QUAD"   # third one flips it


def test_s6_source_histories_survive_enable_toggle_and_shadow_modes():
    """Ladder gate S6: histories are observer property — maturing with
    TERM disabled, untouched by enable toggles; shadow modes
    (SIDE_PAIR_ROW_ONLY) never enter metrology."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_observe

    def st():
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, 1.8]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    g = TerminalOracle()
    span = 284.0
    for i in range(7):
        f = TerminalFeature(ts_ns=int(i * 0.04e9),
                            y_top_px=180.0 - 0.5 * span, span_px=span,
                            center_x_px=320.0, cert_status="certified",
                            mode="SIDE_PAIR")
        terminal_observe(g, st(), f, 0.02)
    # Side history matured (inactive rung) without any enable bit.
    assert g._mature(g._hist_other)
    # Shadow mode: rejected at the door, no history growth anywhere.
    n_before = len(g._hist_other) + len(g._hist)
    sh = TerminalFeature(ts_ns=int(8 * 0.04e9), y_top_px=180.0 - 0.5 * span,
                         span_px=span, center_x_px=320.0,
                         cert_status="certified", mode="SIDE_PAIR_ROW_ONLY")
    assert terminal_observe(g, st(), sh, 0.02) is None
    assert len(g._hist_other) + len(g._hist) == n_before


def test_hard_step_limit_overrides_inflated_sigma():
    """RESPONSE19 disposition SS2.2: the old max(0.10, 3 sigma_side)
    rule permitted a 0.225m source step — approaching the whole
    corridor. A 0.15m inter-source bias (legal under the old rule)
    must now BLOCK the switch: |median de| <= 0.10 is HARD, and an
    inflated provisional sigma never relaxes it."""
    from aigp.planning.vertical_owner import TerminalOracle
    g = TerminalOracle()
    for i in range(10):
        ts = i * 0.04
        g.observe(ts, 0.10, source="FULL_QUAD")
        g.observe(ts, 0.25, source="SIDE_PAIR")   # de = 0.15
    for i in range(10, 16):
        g.observe(i * 0.04, 0.25, source="SIDE_PAIR")
    assert g.active_source == "FULL_QUAD"


def test_side_rung_maintains_but_never_first_captures():
    """RESPONSE19 disposition SS3 (conservative first-live): a mature,
    consistent SIDE_PAIR-active oracle must NOT open the control door —
    only FULL_QUAD may first-capture; the side rung maintains an owner
    it inherited."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_override

    def st():
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, 1.8]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    span = 284.0
    a = make_arbiter()
    g = TerminalOracle()
    g.active_source = "SIDE_PAIR"          # side-active by transition
    owner = None
    for i in range(7):
        f = TerminalFeature(ts_ns=int(i * 0.04e9),
                            y_top_px=180.0 - 0.5 * span, span_px=span,
                            center_x_px=320.0, cert_status="certified",
                            mode="SIDE_PAIR")
        owner, v_bz, _ = terminal_override(
            a, st(), np.array([1.8, 0.0, 0.0]), True, 0.6, 0.55, None,
            0.04, feature=f, feature_age_s=0.02, oracle=g)
    assert g.ready()                        # mature and honest...
    assert owner == ALT_OWNER               # ...but the door stays shut


def test_p1_held_latest_packet_is_consumed_once():
    """Kill test P1 (advisory-15B disposition): one SIDE packet held in
    a latest-value cell while the 250Hz loop polls it ~25 times must
    append to the side history EXACTLY once — repeated polling is
    re-observation, never new evidence. Exact-exposure pairing: the
    pair count increments at most once too."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_observe

    def st():
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, 1.8]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    span = 284.0
    g = TerminalOracle()
    full = TerminalFeature(ts_ns=1000, y_top_px=180.0 - 0.5 * span,
                           span_px=span, center_x_px=320.0,
                           cert_status="certified", mode="FULL_QUAD")
    side = TerminalFeature(ts_ns=1000, y_top_px=180.0 - 0.5 * span,
                           span_px=span, center_x_px=320.0,
                           cert_status="certified", mode="SIDE_PAIR")
    for _ in range(25):
        terminal_observe(g, st(), full, 0.02)
        terminal_observe(g, st(), side, 0.02)
    assert len(g._hist) == 1                  # FULL history: one row
    assert len(g._hist_other) == 1            # SIDE history: one row
    assert len(g._overlap_deltas) == 1        # exact-exposure pair: one


def test_full_rate_anchor_latches_and_survives_side_offset():
    """Advisory-16 (a): at the legal FULL->SIDE transition the FULL
    rate is LATCHED; a constant offset on all SIDE positions (R26-4)
    leaves the anchor unchanged and causes no rate spike — SIDE's
    slope never becomes active authority."""
    from aigp.planning.vertical_owner import TerminalOracle
    g = TerminalOracle()
    slope = -0.10                             # e shrinking: climb 0.10
    for i in range(8):
        ts = i * 0.04
        g.observe(ts, 0.30 + slope * ts, source="FULL_QUAD")
        g.observe(ts, 0.38 + slope * ts, source="SIDE_PAIR")
    for i in range(8, 14):
        g.observe(i * 0.04, 0.38 + slope * i * 0.04, source="SIDE_PAIR")
    assert g.active_source == "SIDE_PAIR"
    assert g.rate_anchor_valid
    assert g.rate_anchor_v == pytest.approx(0.10, abs=0.03)
    # Dual-read split (advisory-19): the honest measurement and the 7B
    # policy are stored separately; the actuating value is their
    # product (OLD path, unchanged until the harvest + re-stamp).
    assert g.rate_anchor_v_raw == pytest.approx(0.10, abs=0.005)
    assert g.rate_anchor_quality == pytest.approx((0.28 / 0.3) * 0.8,
                                                  abs=1e-6)
    assert g.rate_anchor_v == pytest.approx(
        g.rate_anchor_quality * g.rate_anchor_v_raw, abs=1e-9)
    # SIDE observations advance the clock but never reset the anchor.
    assert g.anchor_age_s() > 0.2


def test_anchor_falsified_by_contradictory_side_positions():
    """Advisory-16 SS6 / R26-5: a SIDE position sequence contradicting
    the held rate invalidates the anchor after two consecutive
    breaches — the monitor is a falsification gate, never a SIDE rate
    estimator; fallback (c) takes over via neutral rate."""
    from aigp.planning.vertical_owner import TerminalOracle
    g = TerminalOracle()
    for i in range(8):
        ts = i * 0.04
        g.observe(ts, 0.30 - 0.10 * ts, source="FULL_QUAD")   # climb 0.10
        g.observe(ts, 0.34 - 0.10 * ts, source="SIDE_PAIR")
    for i in range(8, 12):
        g.observe(i * 0.04, 0.34 - 0.10 * i * 0.04, source="SIDE_PAIR")
    assert g.active_source == "SIDE_PAIR" and g.rate_anchor_valid
    # Positions now move hard the OTHER way (true rate reversed).
    t0 = 12 * 0.04
    for k in range(3):
        ts = t0 + k * 0.04
        g.observe(ts, 0.34 - 0.10 * t0 + 0.6 * (ts - t0 + 0.5),
                  source="SIDE_PAIR")
    assert not g.rate_anchor_valid


def test_validated_max_age_caps_anchor_authority():
    """RESPONSE31 disposition (tank-2): runtime must enforce
    anchor_age <= min(A_validated_max, tau-dependent cap). Beyond the
    last held-out-validated age bin a PASSING maintenance score is an
    extrapolation, not authority — neutral-decay (c) takes the tick
    while TERM stays owned. tau=0.3 makes the legacy caps permissive
    to ~0.8s so the new ceiling is the only discriminator."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_override

    def st(ts_s):
        return StateEstimate(
            ts_ns=int(ts_s * 1e9), q_att=LEVEL, omega=np.zeros(3),
            v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, 1.8]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    def anchored_oracle():
        g = TerminalOracle()
        for i in range(8):
            ts = i * 0.04
            g.observe(ts, 0.30 - 0.10 * ts, source="FULL_QUAD")
            g.observe(ts, 0.34 - 0.10 * ts, source="SIDE_PAIR")
        for i in range(8, 14):
            g.observe(i * 0.04, 0.34 - 0.10 * i * 0.04, source="SIDE_PAIR")
        assert g.active_source == "SIDE_PAIR" and g.rate_anchor_valid
        assert g.anchor_applied_ref is None
        return g

    span = 284.0

    def run(g, age_s, **kw):
        a = make_arbiter()
        assert a.tick(True, True, True, 0.05, "position") == TERM_OWNER
        now = g.rate_anchor_ts + age_s
        f = TerminalFeature(ts_ns=int(now * 1e9),
                            y_top_px=180.0 - 0.5 * span, span_px=span,
                            center_x_px=320.0, cert_status="certified",
                            mode="SIDE_PAIR")
        return terminal_override(a, st(now), np.array([1.8, 0.0, 0.0]),
                                 True, 0.3, 0.55, 0.0, 0.04, feature=f,
                                 feature_age_s=0.02, oracle=g, **kw)

    # Inside the validated ceiling: the anchor branch runs (the
    # feed-forward reference latches on the first authority tick).
    g = anchored_oracle()
    owner, _, _ = run(g, 0.40)
    assert owner == TERM_OWNER and g.anchor_applied_ref is not None
    # Beyond the ceiling but inside tau+0.5 AND score-passing: no
    # authority — the branch must not run; ownership is unaffected.
    h = anchored_oracle()
    owner2, _, _ = run(h, 0.60)
    assert owner2 == TERM_OWNER and h.anchor_applied_ref is None
    # Same age with the ceiling widened: authority returns — proving
    # the new ceiling, not the legacy caps, was the discriminator.
    k = anchored_oracle()
    owner3, _, _ = run(k, 0.60, validated_max_age_s=0.70)
    assert owner3 == TERM_OWNER and k.anchor_applied_ref is not None


def _prenoreturn_fixture():
    """Shared SIDE-anchored fixture for the advisory-19 round tests:
    anchored oracle + TERM-owned arbiter + a runner that drives one
    terminal_override tick at a chosen anchor age and tau."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_override

    def st(ts_s):
        return StateEstimate(
            ts_ns=int(ts_s * 1e9), q_att=LEVEL, omega=np.zeros(3),
            v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, 1.8]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    def anchored_oracle():
        g = TerminalOracle()
        for i in range(8):
            ts = i * 0.04
            g.observe(ts, 0.30 - 0.10 * ts, source="FULL_QUAD")
            g.observe(ts, 0.34 - 0.10 * ts, source="SIDE_PAIR")
        for i in range(8, 14):
            g.observe(i * 0.04, 0.34 - 0.10 * i * 0.04, source="SIDE_PAIR")
        assert g.active_source == "SIDE_PAIR" and g.rate_anchor_valid
        return g

    span = 284.0

    def run(g, arb, age_s, tau_s=0.6, **kw):
        now = g.rate_anchor_ts + age_s
        f = TerminalFeature(ts_ns=int(now * 1e9),
                            y_top_px=180.0 - 0.5 * span, span_px=span,
                            center_x_px=320.0, cert_status="certified",
                            mode="SIDE_PAIR")
        return terminal_override(arb, st(now), np.array([1.8, 0.0, 0.0]),
                                 True, tau_s, 0.55, 0.0, 0.04, feature=f,
                                 feature_age_s=0.02, oracle=g, **kw)

    return anchored_oracle, run


def test_dual_read_shadow_anchor_removes_policy_scaling():
    """Advisory-19 §5 required shadow fixture: at a transition with
    unchanged command, the OLD forecast carries the policy-scaling
    offset -(1-auth)*v_raw and the SHADOW (repaired anchor: honest
    slope, authority kept as separate policy) removes exactly that
    offset WITHOUT altering the command feed-forward. Only the old
    path actuates while the HOLD lasts."""
    anchored_oracle, run = _prenoreturn_fixture()
    g = anchored_oracle()
    a = make_arbiter()
    assert a.tick(True, True, True, 0.05, "position") == TERM_OWNER
    owner, _, _ = run(g, a, 0.40)
    assert owner == TERM_OWNER
    auth = g.rate_anchor_quality
    assert auth is not None and auth < 1.0        # short-tail latch
    # Same feed-forward on both sides (prev_vz_up = applied ref = 0):
    ff = 0.0 - g.anchor_applied_ref
    old = g.rate_anchor_v + ff
    assert g.shadow_anchor_vz == pytest.approx(
        old + (1.0 - auth) * g.rate_anchor_v_raw, abs=1e-9)
    assert g.shadow_anchor_vz == pytest.approx(
        g.rate_anchor_v_raw + ff, abs=1e-9)
    # Complete forecast pair (§5 log list): old/new e_cross and
    # command recorded per tick; the e_cross split is EXACTLY the
    # crossing_error difference of the two rates — definition-proof.
    from aigp.planning.vertical_terminal import crossing_error
    fc = g.shadow_forecast
    assert fc is not None
    assert fc["e_cross_new"] - fc["e_cross_old"] == pytest.approx(
        crossing_error(0.0, g.shadow_anchor_vz, 0.6)
        - crossing_error(0.0, old, 0.6), abs=1e-9)
    assert fc["delta_latch"] == pytest.approx(
        -(1.0 - auth) * g.rate_anchor_v_raw, abs=1e-9)


def test_dual_read_purity_no_actuating_side_effects():
    """Advisory-20 binding purity invariant: enable vs disable of the
    dual-read instrument must leave everything actuating bit-for-bit
    unchanged. Two identical fixtures — one with the shadow channel
    live, one with the raw channel stripped (the pre-instrument
    build) — must return the identical (owner, v_bz, vz_up) triple
    and identical actuating oracle state; only the shadow fields may
    differ."""
    anchored_oracle, run = _prenoreturn_fixture()
    g1, g2 = anchored_oracle(), anchored_oracle()
    g2.rate_anchor_v_raw = None            # strip the instrument
    a1, a2 = make_arbiter(), make_arbiter()
    assert a1.tick(True, True, True, 0.05, "position") == TERM_OWNER
    assert a2.tick(True, True, True, 0.05, "position") == TERM_OWNER
    r1 = run(g1, a1, 0.40)
    r2 = run(g2, a2, 0.40)
    assert r1 == r2                        # owner, v_bz, vz_up: identical
    assert g1.rate_anchor_v == g2.rate_anchor_v
    assert g1.anchor_applied_ref == g2.anchor_applied_ref
    assert g1.e_z == g2.e_z
    assert a1.latched == a2.latched
    assert g1.shadow_anchor_vz is not None and g1.shadow_forecast is not None
    assert g2.shadow_anchor_vz is None and g2.shadow_forecast is None


def test_age_expiry_prenoreturn_flag_follows_reversibility():
    """RESPONSE32 disposition branch semantics: validated-age expiry
    BEFORE the no-return latch raises the hold/abort flag (the
    planner applies the braking-band feasibility test); AFTER the
    latch the flag must stay down — neutral-decay governs and TERM
    stays owned."""
    anchored_oracle, run = _prenoreturn_fixture()
    # Pre-no-return (tau 0.6 -> position phase, latch never set):
    g = anchored_oracle()
    a = make_arbiter()
    assert a.tick(True, True, True, 0.05, "position") == TERM_OWNER
    owner, _, _ = run(g, a, 0.60, tau_s=0.6)
    assert owner == TERM_OWNER and not a.latched
    assert g.rate_expired_prenoreturn          # hold/abort raised
    assert g.anchor_applied_ref is None        # and no authority
    # Post-no-return (tau 0.3 -> damping: the latch engages on the
    # SAME tick, before the rate branch reads it):
    h = anchored_oracle()
    b = make_arbiter()
    assert b.tick(True, True, True, 0.05, "position") == TERM_OWNER
    owner2, _, _ = run(h, b, 0.60, tau_s=0.3)
    assert owner2 == TERM_OWNER and b.latched
    assert not h.rate_expired_prenoreturn      # neutral-decay branch
    assert h.anchor_applied_ref is None


def test_no_first_capture_in_damping_via_production_wire():
    """The no-first-capture-in-damping rule previously lived only in
    unit tests: production passed a constant 'position' to the
    arbiter, so the schedule phase never reached it and the no-return
    latch never engaged in flight. The phase now derives from tau at
    the tick — a late feature at tau <= 0.45 must not open the door;
    the identical fixture at position-phase tau still captures."""
    from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
    from aigp.planning.vertical_owner import TerminalOracle, terminal_override

    def st():
        return StateEstimate(
            ts_ns=0, q_att=LEVEL, omega=np.zeros(3), v_world=np.zeros(3),
            gate_rel=RelPose(t=np.array([0.0, 0.0, 1.8]),
                             normal=np.array([0.0, 0.0, -1.0])),
            gate_rel_age_s=0.05, gate_center_px=(320, 180),
            image_size=(640, 360), healthy=True, level_roll=0.0,
            level_pitch=-0.311)

    span = 284.0

    def drive(tau_s):
        a = make_arbiter()
        g = TerminalOracle()
        owner = None
        for i in range(7):
            f = TerminalFeature(ts_ns=int(i * 0.04e9),
                                y_top_px=180.0 - 0.5 * span, span_px=span,
                                center_x_px=320.0, cert_status="certified",
                                mode="FULL_QUAD")
            owner, _, _ = terminal_override(
                a, st(), np.array([1.8, 0.0, 0.0]), True, tau_s, 0.55,
                None, 0.04, feature=f, feature_age_s=0.02, oracle=g)
        return owner

    assert drive(0.6) == TERM_OWNER            # position phase: door open
    assert drive(0.40) == ALT_OWNER            # damping: door stays shut


def test_anchor_age_grows_with_time_not_observations():
    """R26 telemetry finding: the anchor age must grow with CURRENT
    time even when observations pause — a frozen age kept a stale
    anchor 'young' during blindness, the unsafe direction."""
    from aigp.planning.vertical_owner import TerminalOracle
    g = TerminalOracle()
    for i in range(8):
        ts = i * 0.04
        g.observe(ts, 0.30 - 0.10 * ts, source="FULL_QUAD")
        g.observe(ts, 0.34 - 0.10 * ts, source="SIDE_PAIR")
    for i in range(8, 14):
        g.observe(i * 0.04, 0.34 - 0.10 * i * 0.04, source="SIDE_PAIR")
    assert g.active_source == "SIDE_PAIR" and g.rate_anchor_valid
    a1 = g.anchor_age_s(14 * 0.04)
    a2 = g.anchor_age_s(14 * 0.04 + 0.3)     # no new observations
    assert a2 == pytest.approx(a1 + 0.3, abs=1e-6)
