"""Blind-hold contract of the attitude-rate backend.

The R1h/R1i race-week measurements: with vel_leak 0.05 the blind hover
glides into structure on velocity the estimate forgot (commanded 0.00 in
the final 2s of 9/10 killing collisions); with 0.01 it fights velocity
the integrator hallucinated. The blind_hold flag severs actuation from
the horizontal velocity estimate entirely — level attitude, drag brakes
the vehicle. These tests pin that severance.
"""
import numpy as np

from aigp.core.messages import Setpoint, StateEstimate
from aigp.core.params import ParamSet
from aigp.control.attitude_rate_backend import AttitudeRateBackend


class CaptureIO:
    def __init__(self):
        self.calls = []

    def send_attitude_rates(self, roll_rate, pitch_rate, yaw_rate, thrust):
        self.calls.append((roll_rate, pitch_rate, yaw_rate, thrust))


def make_state(v_world, level_pitch=-0.31):
    return StateEstimate(
        ts_ns=0, q_att=np.array([1.0, 0.0, 0.0, 0.0]), omega=np.zeros(3),
        v_world=np.array(v_world, dtype=float), gate_rel=None,
        gate_rel_age_s=float("inf"), gate_center_px=None,
        image_size=(640, 360), healthy=True,
        level_roll=0.0, level_pitch=level_pitch,
    )


def backend(io):
    return AttitudeRateBackend(io, ParamSet.load("config/params_default.json"))


def blind_sp(yaw_rate=0.6):
    return Setpoint(phase="search", v_body=np.zeros(3), yaw_rate=yaw_rate,
                    blind_hold=True)


def tracking_sp():
    return Setpoint(phase="search", v_body=np.zeros(3), yaw_rate=0.6)


def test_blind_hold_ignores_fictional_velocity():
    # The commanded rates must be IDENTICAL whether the estimator believes
    # the vehicle is still or streaking at 3 m/s — fiction-independence.
    io_still, io_fast = CaptureIO(), CaptureIO()
    backend(io_still).update(blind_sp(), make_state([0.0, 0.0, 0.0]), 0.02)
    backend(io_fast).update(blind_sp(), make_state([3.0, -2.0, 0.0]), 0.02)
    r_still, r_fast = io_still.calls[0], io_fast.calls[0]
    assert r_still[0] == r_fast[0]          # roll rate
    assert r_still[1] == r_fast[1]          # pitch rate


def test_tracking_mode_still_chases_velocity():
    # Without the flag the same fictional velocity MUST change the command
    # (otherwise this test would pass vacuously on a broken backend).
    io_still, io_fast = CaptureIO(), CaptureIO()
    backend(io_still).update(tracking_sp(), make_state([0.0, 0.0, 0.0]), 0.02)
    backend(io_fast).update(tracking_sp(), make_state([3.0, -2.0, 0.0]), 0.02)
    r_still, r_fast = io_still.calls[0], io_fast.calls[0]
    assert (r_still[0] != r_fast[0]) or (r_still[1] != r_fast[1])


def test_blind_hold_targets_level_reference():
    # With zero current attitude and level reference level_pitch, the
    # pitch-rate command must drive toward the reference exactly (no
    # velocity term riding on top).
    io = CaptureIO()
    b = backend(io)
    state = make_state([1.5, 0.0, 0.0], level_pitch=-0.31)
    b.update(blind_sp(), state, 0.02)
    _, pitch_rate, _, _ = io.calls[0]
    expected = np.clip(b.rate_p * (state.level_pitch - 0.0),
                       -b.rate_max, b.rate_max)
    assert pitch_rate == b.sign_pitch * float(expected)


def test_blind_hold_keeps_yaw_and_vertical_authority():
    # The search spin must survive blind hold, and the vertical loop must
    # still respond to a vertical error (sinking blind hits the floor).
    io = CaptureIO()
    b = backend(io)
    b.update(blind_sp(yaw_rate=0.6), make_state([0.0, 0.0, 0.8]), 0.02)
    _, _, yaw_rate, thrust = io.calls[0]
    assert yaw_rate == b.sign_yaw * 0.6
    io2 = CaptureIO()
    b2 = backend(io2)
    b2.update(blind_sp(yaw_rate=0.6), make_state([0.0, 0.0, 0.0]), 0.02)
    thrust_no_err = io2.calls[0][3]
    # +0.8 m/s believed sink (NED +z) must raise thrust vs no vertical error.
    assert thrust > thrust_no_err


def test_blind_hold_resets_horizontal_integrators():
    # A long velocity-tracking stretch loads the PID integrators; blind
    # hold must clear them so the next active phase starts clean.
    io = CaptureIO()
    b = backend(io)
    chase = Setpoint(phase="approach", v_body=np.array([2.0, 0.0, 0.0]),
                     yaw_rate=0.0)
    for _ in range(50):
        b.update(chase, make_state([0.0, 0.0, 0.0]), 0.02)
    assert b.pid_vx._integral != 0.0
    b.update(blind_sp(), make_state([0.0, 0.0, 0.0]), 0.02)
    assert b.pid_vx._integral == 0.0 and b.pid_vy._integral == 0.0
