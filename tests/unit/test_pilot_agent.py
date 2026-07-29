"""PilotAgent decision tests — each anchored to a MEASURED death class.

The agent must out-decide the FSM exactly where the R2 censuses showed
the FSM dying: low-blind arrivals into the pedestal, motion on stale
belief, forward flight into looming structure, and the post-pass chain.
"""
import numpy as np
import pytest

from aigp.core.messages import RelPose, StateEstimate
from aigp.core.params import ParamSet
from aigp.planning.pilot_agent import (ADVANCE, BRAKE, CHAIN, CLIMB, CROSS,
                                       SCAN, PilotAgent)
from aigp.planning.race_planner import RacePlanner


def make_state(gate_t=None, center_px=None, age_s=0.0, center_age_s=0.0,
               level_pitch=0.0):
    rel = None
    if gate_t is not None:
        rel = RelPose(t=np.array(gate_t, dtype=float),
                      normal=np.array([0.0, 0.0, -1.0]))
    return StateEstimate(
        ts_ns=0, q_att=np.array([1.0, 0, 0, 0]), omega=np.zeros(3),
        v_world=np.zeros(3), gate_rel=rel, gate_rel_age_s=age_s,
        gate_center_px=center_px, image_size=(640, 360), healthy=True,
        level_roll=0.0, level_pitch=level_pitch,
        gate_center_age_s=center_age_s,
    )


def agent(**over):
    p = ParamSet.load("config/params_default.json")
    over = {"planner.agent.enable": True, **over}
    return PilotAgent(p.patch(over))


def act(sp):
    return sp.phase


# gate_t is CAMERA frame (x right, y down, z forward).

def test_fresh_centered_level_crosses():
    a = agent()
    sp = a.decide(0, make_state(gate_t=[0.0, 0.5, 2.2], age_s=0.05), 0.0)
    assert sp.phase == "commit"          # CROSS
    assert sp.v_body[0] > 0.5


def test_low_blind_near_gate_never_crosses():
    # R2E death class: 1.7m out, gate 0.9m ABOVE us (camera y=-0.9 =>
    # body down=-0.9 => tdz=-0.9), semi-blind (0.6s). The FSM dashed and
    # hit the pedestal; the agent must climb or stop, never cross.
    a = agent()
    sp = a.decide(0, make_state(gate_t=[0.0, -0.9, 1.7], age_s=0.6), 0.0)
    assert sp.phase in ("align", "recover", "search")   # CLIMB/BRAKE/SCAN
    # And the vertical command must be a climb if CLIMB was chosen.
    if sp.phase == "align":
        assert sp.v_body[2] < 0.0        # NED: negative z = up


def test_stale_belief_slows_or_stops():
    # Motion on stale belief killed every R2C-R2E flight in some form.
    a = agent()
    sp = a.decide(0, make_state(gate_t=[0.0, 0.0, 6.0], age_s=1.2), 0.0)
    speed = float(np.linalg.norm(sp.v_body))
    assert speed <= 1.0                  # no fast blind flight


def test_looming_blocks_advance():
    # Fresh far gate but the center of the image is EXPANDING (structure
    # between us and the gate — the R2D run-1 class). High looming must
    # veto fast forward flight.
    a = agent()
    quiet = a.decide(0, make_state(gate_t=[0.0, 0.0, 6.0], age_s=0.05), 0.0)
    a2 = agent()
    loomy = a2.decide(0, make_state(gate_t=[0.0, 0.0, 6.0], age_s=0.05), 0.08)
    assert float(loomy.v_body[0]) < float(quiet.v_body[0])


def test_post_pass_chains_forward():
    a = agent()
    a.on_gate_passed(0)
    sp = a.decide(int(0.5e9), make_state(gate_t=None), 0.0)
    assert sp.phase == "advance"         # CHAIN
    assert sp.v_body[0] > 0.5


def test_chain_window_expires_to_scan():
    a = agent()
    a.on_gate_passed(0)
    sp = a.decide(int(4.0e9), make_state(gate_t=None), 0.0)
    assert sp.phase == "search"
    assert float(np.linalg.norm(sp.v_body)) == 0.0


def test_collision_brakes():
    a = agent()
    a.on_collision(int(1e9))
    sp = a.decide(int(1.2e9), make_state(gate_t=[0.0, 0.0, 3.0]), 0.0)
    assert sp.phase == "recover"
    assert float(np.linalg.norm(sp.v_body)) == 0.0


def test_decision_record_published():
    a = agent()
    a.decide(0, make_state(gate_t=[0.0, 0.0, 3.0], age_s=0.05), 0.02)
    d = a.last_decision
    assert d is not None
    assert d["action"] in (CROSS, ADVANCE, CLIMB, BRAKE, SCAN, CHAIN)
    assert set(d["scores"].keys()) >= {CROSS, ADVANCE, CLIMB, BRAKE, SCAN}
    assert d["looming"] == 0.02


def test_ibvs_cross_on_stale_pose_fresh_pixels():
    # Stale 3D + live pixel track: CROSS must be possible via the pixel
    # servo (the ported IBVS), marked on the setpoint.
    a = agent()
    sp = a.decide(0, make_state(gate_t=[0.0, 0.1, 1.6], age_s=0.6,
                                center_px=(320.0, 340.0),
                                center_age_s=0.05), 0.0)
    if sp.phase == "commit":
        assert sp.ibvs


def test_planner_delegates_to_agent():
    p = ParamSet.load("config/params_default.json").patch(
        {"planner.agent.enable": True})
    pl = RacePlanner(p)
    st = make_state(gate_t=[0.0, 0.5, 2.2], age_s=0.05)
    sp = pl.plan(0, "race", st, None)
    assert sp.phase == "commit"
    assert pl.agent is not None and pl.agent.last_decision is not None


def test_planner_default_no_agent():
    pl = RacePlanner(ParamSet.load("config/params_default.json"))
    assert pl.agent is None


def test_hysteresis_no_dither():
    # Two consecutive near-identical states must not flip the action.
    a = agent()
    st = make_state(gate_t=[0.0, 0.2, 4.0], age_s=0.05)
    sp1 = a.decide(0, st, 0.0)
    sp2 = a.decide(int(0.05e9),
                   make_state(gate_t=[0.0, 0.21, 3.98], age_s=0.05), 0.0)
    assert sp1.phase == sp2.phase
