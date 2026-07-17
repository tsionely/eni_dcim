import numpy as np

from aigp.core.messages import RelPose, StateEstimate
from aigp.core.params import ParamSet
from aigp.planning.race_planner import RacePlanner


def make_state(gate_t=None, center_px=None, age_s=0.0):
    rel = None
    if gate_t is not None:
        rel = RelPose(t=np.array(gate_t, dtype=float),
                      normal=np.array([0.0, 0.0, -1.0]))
    return StateEstimate(
        ts_ns=0, q_att=np.array([1.0, 0, 0, 0]), omega=np.zeros(3),
        v_world=np.zeros(3), gate_rel=rel, gate_rel_age_s=age_s,
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


def test_commit_yaws_camera_onto_offset_gate():
    """Phase 5 frames: commit strafes laterally with yaw pinned at 0 and the
    gate walks out the side of the fixed camera's FOV (edge_clip/no_red).
    While live-steering the commit, the nose must turn toward the gate."""
    p = planner()
    state = make_state(gate_t=[0.0, 0.0, 1.8], center_px=(320, 180))
    assert p.plan(0, "race", state, None).phase == "commit"
    # Next tick: gate drifted to the right in camera coords (+x cam = +y body).
    sp = p.plan(int(0.1e9), "race",
                make_state(gate_t=[0.6, 0.0, 1.5], center_px=(420, 180)), None)
    assert sp.phase == "commit"
    assert sp.yaw_rate > 0.1
    # And a centered gate needs ~no yaw.
    sp2 = p.plan(int(0.2e9), "race",
                 make_state(gate_t=[0.0, 0.0, 1.2], center_px=(320, 180)), None)
    assert abs(sp2.yaw_rate) < 0.05


def test_retreat_keeps_camera_on_gate():
    """Re-acquisition must happen on THIS gate: while retreating, keep
    turning toward the (dead-reckoned) gate bearing instead of drifting."""
    p = planner()
    p.plan(0, "race", make_state(gate_t=[0.0, 0.0, 1.5]), None)
    # Expire the commit window -> retreat begins.
    sp = p.plan(int(5e9), "race", make_state(gate_t=[0.8, 0.0, 2.0]), None)
    assert sp.phase == "retreat"
    assert sp.yaw_rate > 0.05      # gate right -> positive yaw toward it
    # Blind retreat (no gate estimate): no spurious yaw.
    p2 = planner()
    p2.plan(0, "race", make_state(gate_t=[0.0, 0.0, 1.5]), None)
    sp2 = p2.plan(int(5e9), "race", make_state(), None)
    assert sp2.phase == "retreat" and sp2.yaw_rate == 0.0


def test_no_arm_rule_vetoes_double_climb():
    """F1's +1m overfly: altitude hold already climbing from a believed
    LOW when vision drops out, then the sink insurance ARMED mid-coast
    on top of it. Under the no-arm rule the insurance decision is taken
    once at gap entry and the measured climb VETOES it."""
    p = planner()
    # Enter commit with the gate ABOVE us (cam +y is down): hold climbs.
    low = [0.0, -0.5, 1.8]
    assert p.plan(0, "race", make_state(gate_t=low, center_px=(320, 140)),
                  None).phase == "commit"
    sp_seen = p.plan(int(0.1e9), "race", make_state(gate_t=low, age_s=0.0), None)
    # Gap: dead-reckoned gate, growing age. Insurance must NOT stack.
    sp_blind = p.plan(int(0.2e9), "race", make_state(gate_t=low, age_s=0.5), None)
    assert sp_blind.phase == "commit"
    assert sp_blind.v_body[2] >= sp_seen.v_body[2] - 1e-6, \
        "blind coast ADDED climb on top of an already-climbing hold"


def test_no_arm_rule_arms_insurance_when_vertical_neutral():
    """When the hold is NOT climbing at gap entry, the sink insurance
    still arms (the phase3h sink class remains covered)."""
    p = planner()
    # Gate slightly below aim: hold is ~neutral/descending at entry.
    neutral = [0.0, 0.35, 1.8]
    assert p.plan(0, "race", make_state(gate_t=neutral, center_px=(320, 220)),
                  None).phase == "commit"
    sp_seen = p.plan(int(0.1e9), "race", make_state(gate_t=neutral, age_s=0.0), None)
    sp_blind = p.plan(int(0.2e9), "race", make_state(gate_t=neutral, age_s=0.5), None)
    assert sp_blind.v_body[2] < sp_seen.v_body[2] - 0.05, \
        "sink insurance failed to arm on a non-climbing gap entry"


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
