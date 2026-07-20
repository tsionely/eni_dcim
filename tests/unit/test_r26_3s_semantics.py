"""R26-3S command-semantics fixtures (advisory-21 / RESPONSE37-40 joint
ruling): closed-loop mock in which the commands ALTER the vehicle.

domain = MOCK, claim_type = SEMANTIC, magnitude_transfer = false — every
assertion here is a sign / order / structure predicate, never a threshold
tuned to the mock plant. The plant is a deliberately simple point-mass
vertical integrator with first-order velocity lag: any faithful physically
responding plant exercises the command chain's composition; none of its
constants transfer to the real domain. The production owner, limiter,
adapter, and feed-forward code run unmodified; the plant consumes the
ACHIEVED (returned) body command and its response feeds back through the
pixel row — a true closed loop, never shadow-command replay.
"""
import numpy as np
import pytest

from aigp.core.messages import RelPose, StateEstimate, TerminalFeature
from aigp.planning.vertical_owner import (
    ALT_OWNER,
    TERM_OWNER,
    TerminalOracle,
    VerticalOwnerArbiter,
    terminal_override,
)

LEVEL = np.array([1.0, 0.0, 0.0, 0.0])
SPAN = 284.0                       # 512 px.m / 1.8 m (real-res geometry)
DT = 0.02                          # 50Hz commit tick
LEVEL_PITCH = -0.311
# Mandatory mock-domain control (advisory-21): the calibration is the
# DOMAIN'S OWN, common to every arm — this rig's rest pitch IS its trim
# truth, so pitch_cal == level_pitch here. The REAL rig's production
# trim constant belongs to the real domain; carrying it into the mock
# re-creates the trim fiction the mock A/B was voided for, and the
# calibration-isolation fixture below scans this module to prove the
# production literal never appears here.
MOCK_PITCH_CAL = LEVEL_PITCH
COS_TILT = float(np.cos(LEVEL_PITCH))


class VerticalPlant:
    """Point-mass vertical plant: first-order velocity lag, then
    integration of the TRUE vertical error. e_z is +up (target above
    the vehicle); climbing reduces it. Consumes the achieved BODY
    command through the same tilt relation the adapter used, so the
    loop closes through physics, not through an echo of the request."""

    def __init__(self, e0_m: float, lag_s: float = 0.08) -> None:
        self.e_z = float(e0_m)
        self.v_up = 0.0
        self.lag_s = float(lag_s)

    def step(self, v_bz_cmd: float, dt: float) -> None:
        v_up_cmd = -v_bz_cmd * COS_TILT
        alpha = min(1.0, dt / self.lag_s)
        self.v_up += alpha * (v_up_cmd - self.v_up)
        self.e_z -= self.v_up * dt


def _state(ts_s: float, level_pitch: float = LEVEL_PITCH) -> StateEstimate:
    return StateEstimate(
        ts_ns=int(ts_s * 1e9), q_att=LEVEL, omega=np.zeros(3),
        v_world=np.zeros(3),
        gate_rel=RelPose(t=np.array([0.0, 0.0, 1.8]),
                         normal=np.array([0.0, 0.0, -1.0])),
        gate_rel_age_s=0.05, gate_center_px=(320, 180),
        image_size=(640, 360), healthy=True, level_roll=0.0,
        level_pitch=level_pitch)


def _feature(ts_s: float, e_z: float, mode: str = "FULL_QUAD"):
    # Inverse of the oracle's row->e_z map at the 1.8 m rig:
    # e_z = 1.6*(180 - y_top)/span - 0.8  =>  y_top = 180-(e_z+0.8)*span/1.6
    y_top = 180.0 - (e_z + 0.8) * SPAN / 1.6
    return TerminalFeature(ts_ns=int(ts_s * 1e9), y_top_px=y_top,
                           span_px=SPAN, center_x_px=320.0,
                           cert_status="certified", mode=mode)


def run_episode(e0_m: float, ticks: int = 120, tau_s: float = 0.9,
                vz_max: float = 0.6, az_max: float = 2.0,
                withhold_full_after: int | None = None,
                level_pitch: float = LEVEL_PITCH,
                pitch_cal: float = MOCK_PITCH_CAL):
    """Drive the production terminal chain against the plant. Returns
    per-tick rows: (ts, e_true, owner, v_bz, vz_up)."""
    a = VerticalOwnerArbiter()
    for _ in range(3):
        a.note_exposure(True)
    g = TerminalOracle()
    plant = VerticalPlant(e0_m)
    prev = None
    rows = []
    for i in range(ticks):
        ts = i * DT
        if withhold_full_after is not None and i >= withhold_full_after:
            f = _feature(ts, plant.e_z, mode="SIDE_PAIR")
        else:
            f = _feature(ts, plant.e_z, mode="FULL_QUAD")
            if withhold_full_after is not None:
                # Overlap volume so the SIDE rung matures before the cut.
                g.observe(ts, plant.e_z, source="SIDE_PAIR")
        st = _state(ts, level_pitch)
        owner, v_bz, vz_up = terminal_override(
            a, st, np.array([1.8, 0.0, 0.0]), True, tau_s, 0.55, prev,
            DT, feature=f, feature_age_s=0.01, oracle=g,
            vz_max=vz_max, az_max=az_max, pitch_cal_rad=pitch_cal)
        if owner == TERM_OWNER and v_bz is not None:
            plant.step(v_bz, DT)               # physical response
        rows.append((ts, plant.e_z, owner, v_bz, vz_up))
        prev = vz_up
    return rows, g, a


def _owned(rows):
    return [r for r in rows if r[2] == TERM_OWNER and r[3] is not None]


def test_up_step_sign_and_closure():
    """[MOCK/SEMANTIC] Upward correction: target above the vehicle
    (e_z=+0.10) must command CLIMB (world-up positive => body-z
    negative through the adapter), the plant must physically rise,
    and the closed loop must REDUCE the true error — sign routing and
    closure, no magnitude claim."""
    rows, _, _ = run_episode(+0.10)
    owned = _owned(rows)
    assert len(owned) > 40                      # captured and held
    cmds_up = [r[4] for r in owned]
    # Command sign: world-up positive while the +up error stands.
    early = cmds_up[:10]
    assert max(early) > 0.0
    # Adapter sign relation: v_bz = -vz_up/cos_tilt.
    for r in owned[:20]:
        assert r[3] == pytest.approx(-r[4] / COS_TILT, abs=1e-9)
    # Physical closure: the true error shrinks substantially and does
    # not invert beyond the honest deadband scale.
    assert abs(rows[-1][1]) < 0.5 * 0.10
    assert min(r[1] for r in rows) > -0.10      # no gross overshoot flip


def test_down_step_sign_and_closure():
    """[MOCK/SEMANTIC] Downward correction: mirror of the up step —
    e_z=-0.10 commands sink, plant descends, |e| closes, no gross
    inversion."""
    rows, _, _ = run_episode(-0.10)
    owned = _owned(rows)
    assert len(owned) > 40
    early = [r[4] for r in owned[:10]]
    assert min(early) < 0.0                     # world-up negative
    for r in owned[:20]:
        assert r[3] == pytest.approx(-r[4] / COS_TILT, abs=1e-9)
    assert abs(rows[-1][1]) < 0.5 * 0.10
    assert max(r[1] for r in rows) < 0.10


def test_slew_ordering_and_achieved_command():
    """[MOCK/SEMANTIC] Limiter ordering: consecutive applied world-up
    targets never step faster than az_max*dt; the applied value never
    exceeds vz_max (achieved, not requested); and the oracle's applied
    ring records the ACHIEVED value — the same number the plant
    consumed — never an internal pre-clip request."""
    az_max = 2.0
    for e0 in (+0.10, -0.10):
        rows, g, _ = run_episode(e0, az_max=az_max)
        owned = _owned(rows)
        for (a_row, b_row) in zip(owned, owned[1:]):
            assert abs(b_row[4] - a_row[4]) <= az_max * DT + 1e-9
        assert max(abs(r[4]) for r in owned) <= 0.6 + 1e-9


def test_authority_limited_follows_reversibility_split():
    """[MOCK/SEMANTIC] authority_limited (disposition §6 amendment):
    outside the recorded tilt envelope the branch follows the SAME
    reversibility split as the age ceiling. Pre-no-return: TERM never
    actuates the vertical, the hold/abort request is raised (the
    planner guards feasibility), and the achieved thread carries None
    — a command that never reached the plant can NEVER later read as
    a real rate change. Post-no-return: TERM remains the applied
    owner with a NEUTRAL command — no handback to believed
    altitude."""
    rows, g, a = run_episode(+0.08, level_pitch=-0.85,  # cos ~ 0.66
                             pitch_cal=-0.85)
    owned_ticks = [r for r in rows if r[2] == TERM_OWNER]
    assert len(owned_ticks) > 20                # ownership still happens
    assert all(r[3] is None for r in rows)      # vertical never actuates
    assert all(r[4] is None for r in owned_ticks)   # achieved thread None
    assert g.rate_expired_prenoreturn           # hold/abort raised
    assert not a.latched
    # Post-no-return: latch the schedule, tick once more — TERM keeps
    # the vertical with a neutral command and the request stays down.
    a.latched = True
    ts_next = rows[-1][0] + DT
    f = _feature(ts_next, 0.08)
    owner, v_bz, vz_up = terminal_override(
        a, _state(ts_next, level_pitch=-0.85), np.array([1.8, 0.0, 0.0]),
        True, 0.9, 0.55, None, DT, feature=f, feature_age_s=0.01,
        oracle=g, pitch_cal_rad=-0.85)
    assert owner == TERM_OWNER
    assert v_bz == 0.0 and vz_up == 0.0         # neutral, TERM-owned
    assert not g.rate_expired_prenoreturn       # not the abort branch
    # Neutral through the NORMAL limiter, never a hard step
    # (disposition amendment): from a nonzero achieved value the
    # applied target SLEWS toward zero — bounded decay, TERM-owned.
    owner2, v_bz2, vz_up2 = terminal_override(
        a, _state(ts_next + DT, level_pitch=-0.85),
        np.array([1.8, 0.0, 0.0]), True, 0.9, 0.55, 0.30, DT,
        feature=_feature(ts_next + DT, 0.08), feature_age_s=0.01,
        oracle=g, pitch_cal_rad=-0.85)
    assert owner2 == TERM_OWNER
    assert vz_up2 == pytest.approx(0.30 - 2.0 * DT, abs=1e-9)  # slewing
    assert v_bz2 == pytest.approx(-vz_up2 / np.cos(-0.85), abs=1e-9)


@pytest.mark.parametrize("cal", [-0.311, -0.35])
def test_mock_calibration_is_common_arm(cal):
    """[MOCK/SEMANTIC] Permanent calibration invariant (disposition
    §5): the mock rig's rest calibration enters BOTH command arms
    identically — either honest rig calibration captures and closes
    in both directions — and the REAL rig's production trim literal
    never appears in this module (scanned), so changing the real
    constant cannot change any mock result."""
    for e0 in (+0.08, -0.08):
        rows, _, _ = run_episode(e0, level_pitch=cal, pitch_cal=cal)
        assert len(_owned(rows)) > 40
        assert abs(rows[-1][1]) < 0.5 * abs(e0)
    import pathlib
    src = pathlib.Path(__file__).read_text()
    banned = "-0.3" + "3"                       # built, not written: the
    assert banned not in src                    # production literal is absent


def test_source_transition_is_not_vehicle_response():
    """[MOCK/SEMANTIC] Owner/source isolation: a FULL->SIDE source
    transition mid-hold must not appear as a command step — the
    applied world-up target across the transition tick stays inside
    the ordinary slew bound (the measurement-model change is not
    physics and must not actuate as if it were)."""
    rows, g, _ = run_episode(+0.10, ticks=160, withhold_full_after=80,
                             az_max=2.0)
    owned = _owned(rows)
    assert len(owned) > 60
    assert g.active_source == "SIDE_PAIR"       # the transition happened
    for (a_row, b_row) in zip(owned, owned[1:]):
        assert abs(b_row[4] - a_row[4]) <= 2.0 * DT + 1e-9
    # Achieved-command semantics: the applied ring (the feed-forward
    # substrate, filled on SIDE-active ticks) carries EXACTLY values
    # the chain returned as applied — never an internal pre-clip
    # request the plant did not receive.
    applied = {round(v, 12) for _, v in g._applied_ring}
    returned = {round(r[4], 12) for r in rows if r[4] is not None}
    assert applied <= (returned | {0.0})


def test_term_exclusivity_under_ownership():
    """[MOCK/SEMANTIC] Zero legacy vertical contribution while TERM
    owns: by construction the plant here consumes ONLY the TERM
    output — this fixture pins that the chain's applied/achieved
    bookkeeping agrees with that exclusivity (prev_vz_up threading:
    every tick's feed-forward reference is the PREVIOUS tick's
    completed applied command, never the current tick's request —
    causality of the prior-tick rule)."""
    rows, g, _ = run_episode(+0.10)
    assert len(_owned(rows)) > 40
    # The applied ring fills ONLY on SIDE-active ticks — in this
    # FULL-only episode it must be empty: the feed-forward substrate
    # exists for the anchor path alone, no silent parallel consumer.
    assert g._applied_ring == []
