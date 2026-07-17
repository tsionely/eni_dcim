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
