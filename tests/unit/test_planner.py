import numpy as np

from aigp.core.messages import RelPose, StateEstimate
from aigp.core.params import ParamSet
from aigp.planning.race_planner import RacePlanner


def make_state(gate_t=None, center_px=None):
    rel = None
    if gate_t is not None:
        rel = RelPose(t=np.array(gate_t, dtype=float),
                      normal=np.array([0.0, 0.0, -1.0]))
    return StateEstimate(
        ts_ns=0, q_att=np.array([1.0, 0, 0, 0]), omega=np.zeros(3),
        v_world=np.zeros(3), gate_rel=rel, gate_rel_age_s=0.0,
        gate_center_px=center_px, image_size=(640, 360), healthy=True,
    )


def planner():
    return RacePlanner(ParamSet.load("config/params_default.json"))


def test_takeoff_mode_climbs():
    sp = planner().plan(0, "takeoff", make_state(), None)
    assert sp.phase == "takeoff"
    assert sp.v_body[2] < 0        # NED: climb is negative z


def test_search_when_no_gate():
    sp = planner().plan(0, "race", make_state(), None)
    assert sp.phase == "search"
    assert sp.yaw_rate > 0
    assert np.linalg.norm(sp.v_body[:2]) == 0


def test_approach_flies_toward_gate():
    # Gate 8m straight ahead (camera z = body x).
    sp = planner().plan(0, "race", make_state(gate_t=[0.0, 0.0, 8.0],
                                              center_px=(320, 180)), None)
    assert sp.phase == "approach"
    assert sp.v_body[0] > 1.0                    # forward
    assert abs(sp.v_body[1]) < 0.2               # centered -> no lateral
    assert abs(sp.yaw_rate) < 0.1


def test_approach_yaws_toward_offset_gate():
    sp = planner().plan(0, "race", make_state(gate_t=[2.0, 0.0, 8.0],
                                              center_px=(480, 180)), None)
    assert sp.yaw_rate > 0.1       # gate right of center -> positive yaw


def test_commit_locks_vector():
    p = planner()
    state = make_state(gate_t=[0.0, 0.0, 1.5], center_px=(320, 180))   # inside commit distance
    sp = p.plan(0, "race", state, None)
    assert sp.phase == "commit"
    v_locked = sp.v_body.copy()

    # Gate detection changes/disappears during the blind window: vector holds.
    sp2 = p.plan(int(0.5e9), "race", make_state(), None)
    assert sp2.phase == "commit"
    assert np.allclose(sp2.v_body, v_locked)

    # Window expires without a pass -> RETREAT (back off for another
    # attempt), and only after the retreat window -> search.
    sp3 = p.plan(int(5e9), "race", make_state(), None)
    assert sp3.phase == "retreat"
    assert sp3.v_body[0] < 0.0                    # flying backward
    sp4 = p.plan(int(5e9 + 3e9), "race", make_state(), None)
    assert sp4.phase == "search"


def test_gate_passed_clears_commit():
    p = planner()
    p.plan(0, "race", make_state(gate_t=[0.0, 0.0, 1.5]), None)
    p.on_gate_passed()
    sp = p.plan(int(0.1e9), "race", make_state(), None)
    assert sp.phase == "search"


def test_collision_triggers_recover_brake():
    p = planner()
    p.on_collision(now_ns=0)
    sp = p.plan(int(0.1e9), "race", make_state(gate_t=[0.0, 0.0, 8.0]), None)
    assert sp.phase == "recover"
    assert np.allclose(sp.v_body, 0.0)
    # After the brake window, resume approach.
    sp2 = p.plan(int(2e9), "race", make_state(gate_t=[0.0, 0.0, 8.0],
                                              center_px=(320, 180)), None)
    assert sp2.phase == "approach"
