"""Geometric oracle tests for the last-meter vertical feature.

Synthetic pinhole geometry (+y up, normalized coordinates): a gate of
width W with its top bar h_bar meters above the camera reference, at
range Z, projects to y_top = h_bar/Z and span = W/Z.
"""
import numpy as np
import pytest

from aigp.planning.vertical_terminal import (
    blend_tau,
    compute_terminal_guidance,
    crossing_error,
    crossing_sigma,
    guidance_phase,
    robust_slope,
    row_only_vertical_error,
    safe_to_continue,
    tau_from_span,
    terminal_vz_command,
    top_bar_vertical_error,
    top_bar_vertical_sigma,
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


def test_guidance_phase_is_monotonic():
    """TTC noise must never re-arm the position controller after
    damping/freeze has begun."""
    assert guidance_phase(0.8, prev_phase="damping") == "damping"
    assert guidance_phase(0.8, prev_phase="freeze") == "freeze"
    assert guidance_phase(0.3, prev_phase="freeze") == "freeze"
    assert guidance_phase(0.1, prev_phase="damping") == "freeze"   # forward ok


def test_row_only_uses_axial_depth_semantics():
    """The parameter is projective depth Z, not slant range: for an
    off-axis gate the two differ and only Z gives e_z = Z·y − d*."""
    y = 0.3 / 1.5
    z = 1.5
    slant = np.sqrt(1.5**2 + 1.0**2)      # 1m lateral offset
    assert row_only_vertical_error(y, z, D_STAR) == pytest.approx(-0.5)
    assert row_only_vertical_error(y, slant, D_STAR) != pytest.approx(-0.5)


def test_robust_slope_rejects_duplicate_timestamps():
    ts = [0.0, 0.0, 0.0, 0.1, 0.1, 0.2]   # only 3 unique -> None
    assert robust_slope(ts, [1, 1, 1, 2, 2, 3]) is None
    ts = [0.0, 0.1, 0.2, 0.3]
    assert robust_slope(ts, [0.0, 0.1, 0.2, 0.3]) == pytest.approx(1.0)


def test_tau_from_span_constant_closing_speed():
    """Z(t) = 3 - 1.5t, span = k/Z: 1/span is linear, the fit must recover
    time-to-plane exactly. At t=0.4, Z=2.4 -> tau = 1.6s."""
    k = 512.0
    times = [0.0, 0.1, 0.2, 0.3, 0.4]
    spans = [k / (3.0 - 1.5 * t) for t in times]
    assert tau_from_span(times, spans) == pytest.approx(1.6, abs=0.02)


def test_tau_from_span_requires_closing():
    times = [0.0, 0.1, 0.2, 0.3]
    opening = [100.0, 95.0, 90.0, 85.0]   # shrinking span = receding
    assert tau_from_span(times, opening) is None


def test_safety_envelope_uses_moments():
    assert safe_to_continue(0.2, 0.1, margin_m=0.5)          # 0.4 < 0.5
    assert not safe_to_continue(0.2, 0.2, margin_m=0.5)      # 0.6 >= 0.5
    assert crossing_sigma(0.1, 0.5, 0.2, 0.5) == pytest.approx(
        np.sqrt(0.1**2 + 0.1**2))


def test_integrated_guidance_freeze_is_zero_correction():
    g = compute_terminal_guidance(e_z=0.4, sigma_e=0.05, v_z=0.0,
                                  sigma_v=0.1, tau_s=0.2, margin_m=0.55)
    assert g["phase"] == "freeze"
    assert g["az_correction"] == 0.0      # correction, NOT zero thrust
    # Release-contract FREEZE semantics: the target is None — the adapter
    # holds the previously APPLIED world-up target; 0.0 here would read
    # as "command zero vertical velocity", which FREEZE is not.
    assert g["vz_cmd"] is None


def test_tau_from_span_rejects_nonmonotonic_history():
    """Identity swap / border clipping shows as non-monotonic scale: the
    fit must refuse rather than average it in."""
    times = [0.0, 0.1, 0.2, 0.3, 0.4]
    spans = [100.0, 130.0, 90.0, 140.0, 95.0]      # thrashing
    assert tau_from_span(times, spans) is None


def test_top_bar_sigma_grows_with_row_noise_and_range():
    # Same pixel noise hurts more when the bar is small (far / short span).
    near = top_bar_vertical_sigma(0.4, 0.8, W, sigma_y=0.01, sigma_span=0.01)
    far = top_bar_vertical_sigma(0.1, 0.2, W, sigma_y=0.01, sigma_span=0.01)
    assert far > near > 0


def test_blend_tau_fallbacks():
    assert blend_tau(None, 0.8) == 0.8
    assert blend_tau(0.6, None) == 0.6
    assert blend_tau(0.6, 0.8, scale_weight=0.5) == pytest.approx(0.7)
    assert blend_tau(None, None) is None


def test_integrated_guidance_f1_signature_descends():
    """High and drifting higher: guidance must command DOWN and flag
    unsafe when the forecast leaves the envelope."""
    g = compute_terminal_guidance(e_z=-0.5, sigma_e=0.05, v_z=+0.3,
                                  sigma_v=0.05, tau_s=0.8, margin_m=0.55,
                                  prev_phase="position")
    assert g["phase"] == "position"
    assert g["vz_cmd"] < 0                # descend
    assert g["az_correction"] < 0
    assert g["e_cross"] == pytest.approx(-0.74)
    assert not g["safe"]                  # forecast outside the envelope
