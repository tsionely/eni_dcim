"""Last-meter vertical channel: scale-normalized top-bar feature and
terminal crossing guidance (think-tank advisory #3, adopted design).

Below ~1.5m the opening exits the frame bottom and the TOP BAR is the
last structure the camera sees. The naive law — servo the bar's image
row onto the aim row — is geometrically wrong: the bar sits ~H/2 above
the opening center, so a fixed-row target steers the vehicle toward the
TOP EDGE, with an error of the same order as the ~1m overfly the last
real flight died on (demonstrated in tests). The correct feature is
scale-normalized:

    e_z = W * y_T / l_T - d*        (advisory #3 §1.2)

where y_T is the bar-center's vertical coordinate and l_T its apparent
full length in the DE-ROTATED, pass-aligned normalized image (+y up),
W the physical gate width and d* the desired vertical separation below
the bar at crossing. Range cancels: the desired bar row grows in
proportion to apparent bar length.

Pure functions only, wired into the planner together with the close
tracker's top-bar identity stage. All vertical quantities are +UP;
callers converting to NED body-z must negate.
"""
from __future__ import annotations

import numpy as np


def top_bar_vertical_error(y_top_norm: float, span_norm: float,
                           gate_w: float, d_star: float) -> float:
    """Required UPWARD displacement of the vehicle, from bar row + length.

    y_top_norm / span_norm: bar-center vertical coordinate (+up) and
    apparent full bar length, in the same normalized virtual-image
    units. Valid only when BOTH physical endpoints are visible
    (a border-clipped span is a lower bound, never metric scale).
    """
    if span_norm <= 1e-9:
        raise ValueError("span must be positive")
    return gate_w * y_top_norm / span_norm - d_star


def row_only_vertical_error(y_top_norm: float, range_m: float,
                            d_star: float) -> float:
    """BAR_ROW_ONLY fallback: endpoints clipped — convert row to meters
    with the PREDICTED range instead of apparent scale (low-gain use)."""
    return range_m * y_top_norm - d_star


def crossing_error(e_z: float, v_z: float, tau_eff: float) -> float:
    """Predicted vertical miss at the plane if v_z holds (all +up).

    The safety/abort decision must use THIS, not instantaneous e_z: a
    low vehicle already climbing fast enough is safe; a centered one
    descending is not.
    """
    return e_z - tau_eff * v_z


def terminal_vz_command(e_z: float, tau_eff: float, tau_min: float = 0.25,
                        vz_max: float = 1.0) -> float:
    """Bounded vertical velocity that closes e_z by the crossing time.

    Velocity-closure is preferred over the 2e/tau^2 acceleration form:
    less singular as tau -> 0 and directly clampable.
    """
    return float(np.clip(e_z / max(tau_eff, tau_min), -vz_max, vz_max))


def guidance_phase(tau_eff: float, position_until_s: float = 0.45,
                   damping_until_s: float = 0.25) -> str:
    """Terminal schedule: 'position' -> 'damping' -> 'freeze'.

    Near the plane image sensitivity and required acceleration explode
    while new commands have no time to act — the final frames must not
    produce a last-second thrust spike.
    """
    if tau_eff > position_until_s:
        return "position"
    if tau_eff > damping_until_s:
        return "damping"
    return "freeze"
