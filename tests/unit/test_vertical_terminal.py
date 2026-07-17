"""Geometric oracle tests for the last-meter vertical feature.

Synthetic pinhole geometry (+y up, normalized coordinates): a gate of
width W with its top bar h_bar meters above the camera reference, at
range Z, projects to y_top = h_bar/Z and span = W/Z.
"""
import numpy as np
import pytest

from aigp.planning.vertical_terminal import (
    crossing_error,
    guidance_phase,
    row_only_vertical_error,
    terminal_vz_command,
    top_bar_vertical_error,
)

W = 1.6
D_STAR = 0.8            # cross at opening center, bar H/2 above


def project(h_bar, z):
    return h_bar / z, W / z          # y_top_norm, span_norm


def test_feature_is_range_invariant():
    """The whole point: same true vertical offset -> same e_z at any
    range. (The bar's DESIRED row scales with apparent length.)"""
    h_bar = 0.8                       # vehicle exactly at opening center
    for z in (3.0, 2.0, 1.2, 0.7):
        y, s = project(h_bar, z)
        assert top_bar_vertical_error(y, s, W, D_STAR) == pytest.approx(0.0, abs=1e-9)


def test_sign_high_overfly_commands_descent():
    """F1 signature: vehicle ~0.5m ABOVE center -> bar only 0.3 above the
    camera -> e_z must say DESCEND by 0.5 (negative, +up convention)."""
    y, s = project(0.3, 1.5)
    assert top_bar_vertical_error(y, s, W, D_STAR) == pytest.approx(-0.5)


def test_sign_low_crossing_commands_climb():
    y, s = project(1.3, 1.5)          # vehicle 0.5m BELOW center
    assert top_bar_vertical_error(y, s, W, D_STAR) == pytest.approx(+0.5)


def test_fixed_row_servo_is_geometrically_wrong():
    """Advisory #3 rank-5 rejection, demonstrated: hold the bar on a FIXED
    image row (the naive law) and the implied vertical position drifts
    toward the TOP EDGE as range shrinks — meter-class error."""
    y_fixed = 0.8 / 3.0               # row that was 'centered' at 3m
    implied_offset = []
    for z in (3.0, 2.0, 1.0):
        h_bar = y_fixed * z           # bar height that keeps the fixed row
        implied_offset.append(D_STAR - h_bar)   # vehicle above center by this
    assert implied_offset[0] == pytest.approx(0.0, abs=1e-9)
    assert implied_offset[-1] > 0.5   # ~centered at 3m -> near top edge at 1m


def test_span_must_be_positive():
    with pytest.raises(ValueError):
        top_bar_vertical_error(0.1, 0.0, W, D_STAR)


def test_row_only_uses_predicted_range():
    # Same geometry as the high-overfly case, range from the estimator.
    y, _ = project(0.3, 1.5)
    assert row_only_vertical_error(y, 1.5, D_STAR) == pytest.approx(-0.5)


def test_crossing_error_beats_instantaneous():
    """Low but climbing fast = safe; centered but sinking = not."""
    assert crossing_error(e_z=0.4, v_z=+0.8, tau_eff=0.5) == pytest.approx(0.0)
    assert crossing_error(e_z=0.0, v_z=-0.8, tau_eff=0.5) == pytest.approx(+0.4)


def test_terminal_vz_bounded_and_nonsingular():
    assert terminal_vz_command(0.3, tau_eff=0.5) == pytest.approx(0.6)
    # tau below tau_min must not blow up the command.
    assert terminal_vz_command(0.5, tau_eff=0.01) == pytest.approx(1.0)
    assert terminal_vz_command(-5.0, tau_eff=0.5) == -1.0


def test_guidance_phase_schedule():
    assert guidance_phase(0.8) == "position"
    assert guidance_phase(0.35) == "damping"
    assert guidance_phase(0.1) == "freeze"
