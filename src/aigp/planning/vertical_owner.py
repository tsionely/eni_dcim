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
