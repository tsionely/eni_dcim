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


def row_only_vertical_error(y_top_norm: float, depth_z_m: float,
                            d_star: float) -> float:
    """BAR_ROW_ONLY fallback: endpoints clipped — convert row to meters
    with the PREDICTED depth instead of apparent scale (low-gain use).

    depth_z_m is the PROJECTIVE depth along the pass axis (t[2] in the
    aligned frame), NOT the slant range |t|: e_z = Z·y − d*, and feeding
    the euclidean norm biases the result on off-axis approaches
    (think-tank review of this module, 2026-07-17).
    """
    return depth_z_m * y_top_norm - d_star


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


_PHASE_ORDER = {"position": 0, "damping": 1, "freeze": 2}


def guidance_phase(tau_eff: float, prev_phase: str | None = None,
                   position_until_s: float = 0.45,
                   damping_until_s: float = 0.25) -> str:
    """Terminal schedule: 'position' -> 'damping' -> 'freeze', MONOTONIC.

    Near the plane image sensitivity and required acceleration explode
    while new commands have no time to act — the final frames must not
    produce a last-second thrust spike. Passing prev_phase makes the
    progression one-way: once in damping/freeze, TTC noise cannot
    re-arm the position controller (think-tank review hysteresis).
    """
    if tau_eff > position_until_s:
        phase = "position"
    elif tau_eff > damping_until_s:
        phase = "damping"
    else:
        phase = "freeze"
    if prev_phase in _PHASE_ORDER and _PHASE_ORDER[phase] < _PHASE_ORDER[prev_phase]:
        return prev_phase
    return phase


def robust_slope(times_s: list[float], values: list[float]) -> float | None:
    """Theil-Sen slope over UNIQUE-timestamp samples.

    Duplicate timestamps are rejected outright (the sim rebroadcasts each
    exposure ~8-9x; a duplicate is not new information and must not
    tighten anything). Needs >= 4 unique points.
    """
    seen: dict[float, float] = {}
    for t, v in zip(times_s, values):
        if t not in seen:
            seen[t] = v
    pts = sorted(seen.items())
    if len(pts) < 4:
        return None
    slopes = [(v2 - v1) / (t2 - t1)
              for i, (t1, v1) in enumerate(pts)
              for (t2, v2) in pts[i + 1:] if t2 > t1]
    if not slopes:
        return None
    return float(np.median(slopes))


def tau_from_span(times_s: list[float], spans: list[float]) -> float | None:
    """Time-to-plane from apparent-scale expansion, via the 1/span line.

    For any rigid gate-plane feature, span = k/Z so 1/span ∝ Z: under
    constant closing speed 1/span is LINEAR in t and its zero crossing
    is the crossing instant — fitting 1/span avoids the bias of fitting
    a line to the accelerating span itself (think-tank identity).
    Returns None unless genuinely closing (negative 1/span slope).
    """
    if any(s <= 1e-9 for s in spans):
        return None
    inv = [1.0 / s for s in spans]
    b = robust_slope(times_s, inv)
    if b is None or b >= -1e-9:
        return None
    now = max(times_s)
    seen: dict[float, float] = {}
    for t, v in zip(times_s, inv):
        seen.setdefault(t, v)
    pts = sorted(seen.items())
    a = float(np.median([v - b * t for t, v in pts]))   # robust intercept
    value_now = a + b * now
    if value_now <= 0:
        return 0.0
    return float(-value_now / b)


def crossing_sigma(sigma_e: float, v_z: float, sigma_v: float,
                   tau_eff: float, sigma_tau: float = 0.0) -> float:
    """First-order uncertainty of the crossing-error forecast."""
    return float(np.sqrt(sigma_e ** 2 + (tau_eff * sigma_v) ** 2
                         + (v_z * sigma_tau) ** 2))


def safe_to_continue(e_cross: float, sigma_cross: float, margin_m: float,
                     k: float = 2.0) -> bool:
    """|mu| + k*sigma inside the usable half-opening — else retreat/delay."""
    return abs(e_cross) + k * sigma_cross < margin_m


def compute_terminal_guidance(e_z: float, sigma_e: float, v_z: float,
                              sigma_v: float, tau_s: float,
                              margin_m: float,
                              prev_phase: str | None = None,
                              camera_latency_s: float = 0.0,
                              actuator_delay_s: float = 0.0,
                              vz_max: float = 1.0, az_max: float = 3.0,
                              kv: float = 2.0) -> dict:
    """One integrated terminal-guidance step (all vertical quantities +UP).

    Returns phase, effective TTC, crossing forecast with uncertainty,
    the envelope decision, and a bounded vertical VELOCITY target and
    ACCELERATION CORRECTION — a correction for the existing thrust
    controller (which keeps supplying gravity/tilt compensation), never
    an absolute thrust. In freeze the correction is exactly zero.
    """
    tau_eff = tau_s - camera_latency_s - actuator_delay_s
    phase = guidance_phase(tau_eff, prev_phase)
    e_cross = crossing_error(e_z, v_z, tau_eff)
    sig = crossing_sigma(sigma_e, v_z, sigma_v, tau_eff)
    safe = safe_to_continue(e_cross, sig, margin_m)
    if phase == "position":
        vz_cmd = terminal_vz_command(e_z, tau_eff, vz_max=vz_max)
        az = float(np.clip(kv * (vz_cmd - v_z), -az_max, az_max))
    elif phase == "damping":
        vz_cmd = 0.0
        az = float(np.clip(kv * (0.0 - v_z), -az_max, az_max))
    else:
        vz_cmd = 0.0
        az = 0.0
    return {"phase": phase, "tau_eff": tau_eff, "e_cross": e_cross,
            "sigma_cross": sig, "safe": safe, "vz_cmd": vz_cmd,
            "az_correction": az}
