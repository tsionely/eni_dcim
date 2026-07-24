"""Gate-clip debounce: one physical frame brush is one clip, not a burst.

T3 measured 11 gate contact events in 0.2s for a single impact, which
tripped the 10-clip budget and aborted a flight that was AT the gate.
"""
from aigp.core.messages import CollisionEvent
from aigp.core.params import ParamSet
from aigp.supervisor.safety import CollisionPolicy


def clip(ts_ns):
    return CollisionEvent(ts_ns=ts_ns, collision_id=CollisionEvent.GATE,
                          threat_level=1, impulse=1.0)


def base(debounce):
    p = ParamSet.load("config/params_default.json")
    if debounce:
        p = p.patch({"safety.gate_clip_debounce_s": debounce})
    return CollisionPolicy(p)


def test_burst_trips_budget_without_debounce():
    pol = base(0.0)
    verdicts = [pol.assess(clip(int(t * 1e9))) for t in
                [20.0 + i * 0.02 for i in range(11)]]  # 11 in 0.2s
    assert pol.gate_clips == 11
    assert any(v.abort for v in verdicts)


def test_burst_counts_as_one_clip_with_debounce():
    pol = base(0.3)
    verdicts = [pol.assess(clip(int(t * 1e9))) for t in
                [20.0 + i * 0.02 for i in range(11)]]  # one 0.2s impact
    assert pol.gate_clips == 1
    assert not any(v.abort for v in verdicts)


def test_separate_impacts_still_counted():
    pol = base(0.3)
    # Three impacts, each a 0.1s burst, spaced 2s apart -> three clips.
    for base_t in (10.0, 12.0, 14.0):
        for i in range(5):
            pol.assess(clip(int((base_t + i * 0.02) * 1e9)))
    assert pol.gate_clips == 3


def test_debounce_still_aborts_on_persistent_grinding():
    pol = base(0.3)
    # 15 distinct impacts spaced 0.5s apart (> debounce) -> real grinding.
    verdicts = [pol.assess(clip(int((10.0 + i * 0.5) * 1e9)))
                for i in range(15)]
    assert any(v.abort for v in verdicts)
