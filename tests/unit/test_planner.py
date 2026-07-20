import numpy as np
import pytest

from aigp.core.messages import RelPose, StateEstimate
from aigp.core.params import ParamSet
from aigp.planning.race_planner import RacePlanner


def make_state(gate_t=None, center_px=None, age_s=0.0, level_pitch=0.0):
    rel = None
    if gate_t is not None:
        rel = RelPose(t=np.array(gate_t, dtype=float),
                      normal=np.array([0.0, 0.0, -1.0]))
    return StateEstimate(
        ts_ns=0, q_att=np.array([1.0, 0, 0, 0]), omega=np.zeros(3),
        v_world=np.zeros(3), gate_rel=rel, gate_rel_age_s=age_s,
        gate_center_px=center_px, image_size=(640, 360), healthy=True,
        level_roll=0.0, level_pitch=level_pitch,
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
    # (0.2m: big enough to drive a strong climb, small enough that the
    # phase6b vertical pre-alignment gate still allows commit entry.)
    low = [0.0, -0.2, 1.8]
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


def test_no_arm_rule_tops_up_weak_climb():
    """phase5c: the binary veto killed insurance for ANY climb and all
    three flights arrived LOW. Insurance now TOPS UP a weak climb to the
    insured sink rate — a hold climbing 0.03 gets ~0.07 more, while F1's
    strong climb (0.7) still gets zero."""
    p = planner()
    # Gate a hair above the aim point: hold climbs weakly (~0.05) at entry.
    weak = [0.0, 0.19, 1.8]
    assert p.plan(0, "race", make_state(gate_t=weak, center_px=(320, 150)),
                  None).phase == "commit"
    sp_seen = p.plan(int(0.1e9), "race", make_state(gate_t=weak, age_s=0.0), None)
    sp_blind = p.plan(int(0.2e9), "race", make_state(gate_t=weak, age_s=0.5), None)
    seen_climb = -sp_seen.v_body[2]
    blind_climb = -sp_blind.v_body[2]
    assert blind_climb > seen_climb + 0.01, "no top-up on a weak climb"
    assert blind_climb - seen_climb <= 0.11, "top-up exceeded the insured rate"


def test_align_gates_commit_on_vertical_deficit():
    """Phase6a keystone: the opening center is 3.11m above the pad camera
    while takeoff tops out ~1.6m lower — committing with that deficit is
    how every dash arrived LOW. Commit entry must first close the height
    gap in an ALIGN phase (climb replaces the 0.8-capped hold), then dash."""
    p = planner()
    # Gate 5m ahead and 1.6m ABOVE (cam +y down): inside commit range,
    # badly misaligned vertically.
    low = make_state(gate_t=[0.0, -1.6, 5.0], center_px=(320, 80))
    sp = p.plan(0, "race", low, None)
    assert sp.phase == "align"
    assert sp.v_body[2] < -0.8              # climbing faster than the hold cap
    assert 0.0 < sp.v_body[0] < 1.0         # creeping forward, not dashing
    # Height gap closed -> the same planner enters commit.
    ok = make_state(gate_t=[0.0, 0.1, 4.5], center_px=(320, 190))
    sp2 = p.plan(int(1.5e9), "race", ok, None)
    assert sp2.phase == "commit"


def test_align_budget_expires_into_commit():
    """A capped attempt beats hovering out the flight clock: if the gap
    will not close within align.max_s, commit anyway."""
    p = planner()
    low = make_state(gate_t=[0.0, -1.6, 5.0], center_px=(320, 80))
    assert p.plan(0, "race", low, None).phase == "align"
    assert p.plan(int(2e9), "race", low, None).phase == "align"
    sp = p.plan(int(4.5e9), "race", low, None)
    assert sp.phase == "commit"


def test_commit_window_scales_with_entry_distance():
    """Phase6a dash-F1: the fixed 2.5s window expired at believed
    z=+1.09m — BEFORE the plane — and retreat yanked a centered dash
    back. The window must outlive the crossing at commit speed."""
    p = planner()
    state = make_state(gate_t=[0.0, 0.0, 6.4], center_px=(320, 180))
    assert p.plan(0, "race", state, None).phase == "commit"
    # 6.4m at 2.5 m/s = 2.56s > the 2.5s base; with the +1s margin the
    # window must still be open at 3.4s...
    sp = p.plan(int(3.4e9), "race", make_state(), None)
    assert sp.phase == "commit"
    # ...and expired by 3.7s.
    sp2 = p.plan(int(3.7e9), "race", make_state(), None)
    assert sp2.phase == "retreat"


def test_midcommit_relock_jump_terminates_attempt():
    """Phase6a dash-F2: after slipping past gate 1 the estimator
    relocked the NEXT gate at 7m while commit kept flying on the old
    timer. A believed-z jump UP of >2m mid-commit ends the attempt."""
    p = planner()
    assert p.plan(0, "race", make_state(gate_t=[0.0, 0.0, 2.0],
                                        center_px=(320, 180)),
                  None).phase == "commit"
    sp = p.plan(int(0.3e9), "race",
                make_state(gate_t=[0.5, 0.0, 7.0], center_px=(400, 180)), None)
    assert sp.phase == "retreat"
    # Normal in-commit range progress must NOT trip the guard.
    p2 = planner()
    assert p2.plan(0, "race", make_state(gate_t=[0.0, 0.0, 2.0],
                                         center_px=(320, 180)),
                   None).phase == "commit"
    sp2 = p2.plan(int(0.3e9), "race",
                  make_state(gate_t=[0.0, 0.0, 1.4], center_px=(320, 180)),
                  None)
    assert sp2.phase == "commit"


def test_true_world_dz_untilts_rest_frame():
    """The phase6b keystone: the attitude filter zeroes the TILTED rest
    pose (level_pitch=-0.311 on this airframe), so naive world rotation
    reads the pad-visible gate 3.2m 'above' when the true height is
    ~1.37m. This pins the level composition forever (real pad numbers
    from fixture 20260717T153903, first detection)."""
    from aigp.planning.approach import gate_world_dz, true_world_dz
    rel = RelPose(t=np.array([0.015, -3.217, 5.525]),
                  normal=np.array([0.0, 0.0, -1.0]))
    q = np.array([1.0, 0.0, 0.0, 0.0])          # rest: filter reads identity
    assert gate_world_dz(rel, q) == pytest.approx(-3.217, abs=0.01)
    assert true_world_dz(rel, q, 0.0, -0.311) == pytest.approx(-1.372,
                                                               abs=0.01)


def test_abort_corridor_ignores_rest_tilt_phantom():
    """Phase6b F2: a vertically-centered arrival at R~0.9 read +0.58
    'low' through the tilted rest frame and the corridor aborted a
    perfect pass. With the same body-frame numbers, the corridor must
    hold when the tilt explains the offset — and still abort when it
    does not (level_pitch=0)."""
    tilt = -0.311
    p = planner()
    entry = make_state(gate_t=[0.0, 0.0, 2.0], center_px=(320, 180),
                       level_pitch=tilt)
    assert p.plan(0, "race", entry, None).phase == "commit"
    # True vertical: ~at aim (off 0.20 < 0.45). Tilted frame: off 0.65.
    corridor = make_state(gate_t=[0.0, -0.397, 1.4], center_px=(320, 120),
                          level_pitch=tilt)
    for i in range(6):
        sp = p.plan(int((0.1 + 0.05 * i) * 1e9), "race", corridor, None)
    assert sp.phase == "commit", "phantom vertical aborted a centered pass"
    # Same body numbers with NO rest tilt: genuinely off -> abort fires.
    p2 = planner()
    assert p2.plan(0, "race", make_state(gate_t=[0.0, 0.0, 2.0],
                                         center_px=(320, 180)),
                   None).phase == "commit"
    flat = make_state(gate_t=[0.0, -0.397, 1.4], center_px=(320, 120))
    for i in range(6):
        sp2 = p2.plan(int((0.1 + 0.05 * i) * 1e9), "race", flat, None)
    assert sp2.phase == "retreat"


def test_no_retreat_inside_braking_band():
    """Phase6b F2's strike mechanism: retreat commanded at 1.31m with
    2.5 m/s of forward momentum coasted INTO the gate. Inside
    abort_min_dist_m the attempt is committed — no corridor abort."""
    p = planner()
    assert p.plan(0, "race", make_state(gate_t=[0.0, 0.0, 2.0],
                                        center_px=(320, 180)),
                  None).phase == "commit"
    inside = make_state(gate_t=[0.0, -0.7, 0.9], center_px=(320, 60))
    for i in range(6):
        sp = p.plan(int((0.1 + 0.05 * i) * 1e9), "race", inside, None)
    assert sp.phase == "commit"


def test_abort_requires_fresh_vision():
    """Advisory-6, T3's twin: no irreversible maneuver on state-only
    evidence in the terminal zone. Off-corridor breaches on a
    dead-reckoned estimate (age > blind_age_s) must never fire the
    abort — F2's fossil abort ran on age 0.32s."""
    p = planner()
    assert p.plan(0, "race", make_state(gate_t=[0.0, 0.0, 2.0],
                                        center_px=(320, 180)),
                  None).phase == "commit"
    stale = make_state(gate_t=[0.0, -0.397, 1.4], center_px=(320, 120),
                       age_s=0.5)
    for i in range(6):
        sp = p.plan(int((0.1 + 0.05 * i) * 1e9), "race", stale, None)
    assert sp.phase == "commit", "dead-reckoned evidence fired the abort"


def test_no_abort_radius_scales_with_commit_speed():
    """Advisory-6: the braking band is a formula, not a number. Slower
    commit speed shrinks the no-abort radius (down to the floor)."""
    fast = planner()
    slow = RacePlanner(ParamSet.load("config/params_default.json").patch(
        {"planner.commit.speed_mps": 1.5}))
    assert fast.abort_min_dist_m == pytest.approx(1.202, abs=0.01)
    assert slow.abort_min_dist_m == pytest.approx(0.8, abs=0.01)  # floor


def test_postmiss_far_target_guard():
    """Phase6b F1: after the blown attempt the estimator relocked a
    believed 40m target and the planner chased it into three env hits.
    Right after a miss, approach refuses far targets and keeps
    searching; sane-range targets and post-window reacquisition pass."""
    p = planner()
    assert p.plan(0, "race", make_state(gate_t=[0.0, 0.0, 1.5],
                                        center_px=(320, 180)),
                  None).phase == "commit"
    assert p.plan(int(5e9), "race", make_state(), None).phase == "retreat"
    # Retreat window over; a 20m 'gate' appears -> refused, keep searching.
    far = make_state(gate_t=[0.0, 0.0, 20.0], center_px=(320, 180))
    assert p.plan(int(7.5e9), "race", far, None).phase == "search"
    # A sane-range target is accepted immediately.
    near = make_state(gate_t=[0.0, 0.0, 8.0], center_px=(320, 180))
    assert p.plan(int(7.6e9), "race", near, None).phase == "approach"
    # After the reacquire window (5s fail + 6s), even far targets fly.
    assert p.plan(int(11.5e9), "race", far, None).phase == "approach"


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


def test_align_refuses_fiction_vertical():
    """Phase6c F2: post-miss believed read 'gate 4.9m above me' and
    ALIGN climbed into the ceiling (impulse 6.1). No R2 gate needs >2m
    of height closure — bigger readings are fiction; never climb on
    them. Commit proceeds under its own guards instead."""
    p = planner()
    fiction = make_state(gate_t=[0.0, -4.0, 3.0], center_px=(320, 40))
    sp = p.plan(0, "race", fiction, None)
    assert sp.phase == "commit"          # not align — and no 1.2 m/s climb


def test_commit_entry_requires_fresh_fix():
    """Phase6c F3: post-collision re-commits entered on 1.2s-old
    dead-reckoned fiction and floor-scraped. Entering align/commit
    requires a recent view; stale estimates keep flying approach."""
    p = planner()
    stale = make_state(gate_t=[0.0, 0.0, 2.0], center_px=(320, 180),
                       age_s=1.0)
    assert p.plan(0, "race", stale, None).phase == "approach"
    fresh = make_state(gate_t=[0.0, 0.0, 2.0], center_px=(320, 180))
    assert p.plan(int(0.1e9), "race", fresh, None).phase == "commit"


def test_blind_commit_stops_instead_of_phantom_or_flail():
    """THE first-attempt fork (1.8 cohort) + the cohort-2 wipeout: a
    phantom crossing on a 1.45s-blind believed must not RETREAT (the
    0/4 churn deaths), and the commit must not keep dashing blind
    either (cohort-2 F1: 3.7m blind continuation, then a blind reverse
    into the structure, impulse 7.2). Stale evidence mid-commit =>
    BRAKE to hover, then reacquire from standstill. A fresh crossing
    still retreats — that maneuver has evidence behind it."""
    p = planner()
    sp = p.plan(0, "race", make_state(gate_t=[0.0, 0.0, 1.4],
                                      center_px=(320, 180)), None)
    assert sp.phase == "commit"
    # Phantom: believed crossed the plane, but vision is 1.45s old.
    phantom = make_state(gate_t=[0.0, 0.0, -0.5], age_s=1.45)
    sp2 = p.plan(int(0.5e9), "race", phantom, None)
    assert sp2.phase == "recover"
    assert np.allclose(sp2.v_body, 0.0)           # full stop, no reverse
    # After the brake window: stationary search (yaw in place), never a
    # blind retreat.
    sp3 = p.plan(int(2.0e9), "race", make_state(age_s=2.0), None)
    assert sp3.phase == "search"
    assert np.linalg.norm(sp3.v_body[:2]) == 0
    # Fresh crossing on a separate attempt: evidence-backed retreat.
    p2 = planner()
    assert p2.plan(0, "race", make_state(gate_t=[0.0, 0.0, 1.4],
                                         center_px=(320, 180)),
                   None).phase == "commit"
    honest = make_state(gate_t=[0.0, 0.0, -0.5], age_s=0.1)
    assert p2.plan(int(0.5e9), "race", honest, None).phase == "retreat"


def test_timer_expiry_blind_brakes_instead_of_reverse():
    """Cohort-2 F1's exact death: window expires with believed long
    expired (age inf) after a blind overfly — backing up at -1.2 m/s
    reverses into the structure just passed. Stale at timer => brake;
    fresh at timer keeps the historical retreat."""
    p = planner()
    p.plan(0, "race", make_state(gate_t=[0.0, 0.0, 1.4],
                                 center_px=(320, 180)), None)
    stale = make_state(gate_t=[0.0, 0.0, 1.0], age_s=3.0)
    sp = p.plan(int(5e9), "race", stale, None)
    assert sp.phase == "recover"
    assert np.allclose(sp.v_body, 0.0)
