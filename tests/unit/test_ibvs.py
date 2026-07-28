"""IBVS pixel-bearing servo + visibility speed (aigp_stack port).

The geometry invariant under test: with the camera mounted UP-TILTED by
mount_pitch_deg, "centered" for the servo means the gate rides at the
BODY-FORWARD bearing — which projects BELOW the image center by
fx*tan(pitch) — not at the image center. Centering at the image center
(the source stack's forward-camera assumption) would fly under gates.
"""
import math

import numpy as np
import pytest

from aigp.core.messages import RelPose, StateEstimate
from aigp.core.params import ParamSet
from aigp.planning.ibvs import (IbvsConfig, VisibilityConfig, gate_dir_body,
                                ibvs_centering, visibility_speed)
from aigp.planning.race_planner import RacePlanner

W, H = 640, 360
FOV = 90.0
PITCH = 29.0
FX = (W / 2.0) / math.tan(math.radians(FOV) / 2.0)
# Pixel row where body-level-forward projects with the up-tilted camera.
V_FWD = H / 2.0 + FX * math.tan(math.radians(PITCH))


def cfg(**kw):
    return IbvsConfig(enable=True, **kw)


def test_body_forward_pixel_maps_to_forward():
    d = gate_dir_body((W / 2.0, V_FWD), (W, H), FOV, PITCH)
    assert d[0] == pytest.approx(1.0, abs=1e-6)
    assert d[1] == pytest.approx(0.0, abs=1e-6)
    assert d[2] == pytest.approx(0.0, abs=1e-6)


def test_image_center_is_above_body_level_with_up_tilt():
    # A gate at the IMAGE center sits 29 deg ABOVE body-forward.
    d = gate_dir_body((W / 2.0, H / 2.0), (W, H), FOV, PITCH)
    assert d[2] < -0.4          # NED down-negative = above us


def test_centering_zero_at_body_forward():
    vy, vz, yaw = ibvs_centering((W / 2.0, V_FWD), (W, H), FOV, PITCH, cfg())
    assert vy == pytest.approx(0.0, abs=1e-6)
    assert vz == pytest.approx(0.0, abs=1e-6)
    assert yaw == pytest.approx(0.0, abs=1e-6)


def test_gate_right_of_center_strafes_and_yaws_right():
    vy, vz, yaw = ibvs_centering((W / 2.0 + 120, V_FWD), (W, H), FOV, PITCH,
                                 cfg())
    assert vy > 0.05            # body-right
    assert yaw > 0.05           # positive yaw = turn right


def test_gate_high_in_image_commands_climb():
    # Gate at the image center = 29 deg above body-level -> climb (NED: vz<0).
    vy, vz, yaw = ibvs_centering((W / 2.0, H / 2.0), (W, H), FOV, PITCH,
                                 cfg())
    assert vz < -0.2


def test_caps_respected():
    c = cfg(max_lat_mps=0.4, max_vert_mps=0.3, yaw_cap_rps=0.2)
    vy, vz, yaw = ibvs_centering((W - 1.0, 0.0), (W, H), FOV, PITCH, c)
    assert abs(vy) <= 0.4 + 1e-9
    assert abs(vz) <= 0.3 + 1e-9
    assert abs(yaw) <= 0.2 + 1e-9


def test_no_mount_pitch_matches_image_center():
    # With a level camera the two conventions coincide.
    vy, vz, yaw = ibvs_centering((W / 2.0, H / 2.0), (W, H), FOV, 0.0, cfg())
    assert vy == pytest.approx(0.0, abs=1e-6)
    assert vz == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------- visibility

def vcfg(**kw):
    return VisibilityConfig(enable=True, **kw)


def test_visibility_fresh_full_speed():
    assert visibility_speed(3.0, 0.05, 10.0, 1.0, vcfg()) == pytest.approx(3.0)


def test_visibility_stale_scales_down():
    s = visibility_speed(3.0, 0.5, 10.0, 1.0, vcfg())
    assert s == pytest.approx(3.0 * 0.35)


def test_visibility_floor():
    s = visibility_speed(1.0, 2.0, 10.0, 1.0, vcfg(min_speed_mps=0.8))
    assert s == pytest.approx(0.8)


def test_visibility_ttc_panic_brake():
    # 1m out at 3 m/s = 0.33s TTC with a stale fix -> panic halving stacks.
    slow = visibility_speed(3.0, 0.3, 1.0, 3.0, vcfg())
    no_panic = visibility_speed(3.0, 0.3, 10.0, 3.0, vcfg())
    assert slow < no_panic


def test_visibility_never_exceeds_base():
    assert visibility_speed(2.0, 0.0, 100.0, 0.1, vcfg()) <= 2.0


# ---------------------------------------------------------------- planner

def make_state(gate_t=None, center_px=None, age_s=0.0, center_age_s=0.0):
    rel = None
    if gate_t is not None:
        rel = RelPose(t=np.array(gate_t, dtype=float),
                      normal=np.array([0.0, 0.0, -1.0]))
    return StateEstimate(
        ts_ns=0, q_att=np.array([1.0, 0, 0, 0]), omega=np.zeros(3),
        v_world=np.zeros(3), gate_rel=rel, gate_rel_age_s=age_s,
        gate_center_px=center_px, image_size=(W, H), healthy=True,
        level_roll=0.0, level_pitch=0.0, gate_center_age_s=center_age_s,
    )


def planner(**over):
    p = ParamSet.load("config/params_default.json")
    if over:
        p = p.patch(over)
    return RacePlanner(p)


def test_default_config_never_calls_ibvs():
    # Defaults preserve behavior: stale commit still dead-reckons.
    pl = planner()
    st = make_state(gate_t=[0.0, 0.0, 3.0], center_px=(320, 300))
    sp = pl.plan(0, "race", st, None)
    assert sp.phase == "commit"
    blind = make_state(gate_t=[0.0, 0.0, 1.5], center_px=(320, 300),
                       age_s=0.5, center_age_s=0.05)
    sp2 = pl.plan(int(0.3e9), "race", blind, None)
    assert sp2.phase == "commit"
    # Locked commit vector (dead-reckoned live-steer), not the pure IBVS
    # [commit_speed, vy, vz] shape with yaw from pixels while blind at 1.5m
    # fwd -- the fossil branch computes direction from gate geometry.


def test_ibvs_steers_blind_commit_on_fresh_pixels():
    pl = planner(**{"planner.ibvs.enable": True})
    st = make_state(gate_t=[0.0, 0.0, 3.0], center_px=(320, 300))
    sp = pl.plan(0, "race", st, None)
    assert sp.phase == "commit"
    # 3D fossil (age 0.5 > blind_age 0.3), pixel fresh, gate right of fwd.
    blind = make_state(gate_t=[0.0, 0.0, 1.5], center_px=(W / 2.0 + 150, V_FWD),
                       age_s=0.5, center_age_s=0.05)
    sp2 = pl.plan(int(0.3e9), "race", blind, None)
    assert sp2.phase == "commit"
    assert sp2.v_body[0] == pytest.approx(pl.commit_speed)
    assert sp2.v_body[1] > 0.05          # strafe toward the pixel bearing
    assert sp2.yaw_rate > 0.05           # yaw toward the pixel bearing


def test_ibvs_requires_fresh_pixels():
    pl = planner(**{"planner.ibvs.enable": True})
    st = make_state(gate_t=[0.0, 0.0, 3.0], center_px=(320, 300))
    pl.plan(0, "race", st, None)
    # Pixel as stale as the 3D fix: IBVS must NOT engage.
    blind = make_state(gate_t=[0.0, 0.0, 1.5], center_px=(W / 2.0 + 150, V_FWD),
                       age_s=0.5, center_age_s=0.5)
    sp2 = pl.plan(int(0.3e9), "race", blind, None)
    assert sp2.phase == "commit"
    # Fossil live-steer keeps the locked-vector shape; the pure-IBVS
    # signature (v_body[0] == commit_speed exactly AND yaw from pixels)
    # must not appear.
    assert not (sp2.v_body[0] == pytest.approx(pl.commit_speed, abs=1e-9)
                and sp2.v_body[1] > 0.05 and sp2.yaw_rate > 0.05)


def test_no_retreat_geometric_behind_brakes_not_crashes():
    # retreat disabled: the geometric_behind exit must brake to recover —
    # before the fix it fell through to Setpoint(v_body=None) (TypeError
    # downstream). Enter commit, then present a fresh behind-plane gate.
    pl = planner(**{"planner.retreat.enabled": False})
    st = make_state(gate_t=[0.0, 0.0, 3.0], center_px=(320, 300))
    sp = pl.plan(0, "race", st, None)
    assert sp.phase == "commit"
    behind = make_state(gate_t=[0.0, 0.0, -0.6], center_px=None, age_s=0.1)
    sp2 = pl.plan(int(0.2e9), "race", behind, None)
    assert sp2.phase == "recover"
    assert sp2.v_body is not None
    assert float(np.linalg.norm(sp2.v_body)) == 0.0
    assert pl.commit_exit_reason == "geometric_behind"


def test_visibility_scales_stale_approach():
    pl = planner(**{"planner.visibility.enable": True})
    fresh = make_state(gate_t=[0.0, 0.0, 10.0], age_s=0.0)
    stale = make_state(gate_t=[0.0, 0.0, 10.0], age_s=0.45)
    v_fresh = pl.plan(0, "race", fresh, None)
    pl2 = planner(**{"planner.visibility.enable": True})
    v_stale = pl2.plan(0, "race", stale, None)
    assert v_fresh.phase == "approach" and v_stale.phase == "approach"
    assert float(np.linalg.norm(v_stale.v_body)) < \
        float(np.linalg.norm(v_fresh.v_body))


def test_visibility_disabled_is_inert():
    pl = planner()
    stale = make_state(gate_t=[0.0, 0.0, 10.0], age_s=0.45)
    pl2 = planner(**{"planner.visibility.enable": True})
    sp_off = pl.plan(0, "race", stale, None)
    sp_on = pl2.plan(0, "race", stale, None)
    assert float(np.linalg.norm(sp_on.v_body)) < \
        float(np.linalg.norm(sp_off.v_body))
