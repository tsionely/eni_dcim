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
    """Enable-bit path: LOW state commands climb (negative body-z), HIGH
    commands descend; without certification the override yields None."""
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
    assert v_bz < 0                     # LOW -> climb (NED body-z negative)
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
    def feat(ts_ns, span=800.0):
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
    span = 800.0
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
