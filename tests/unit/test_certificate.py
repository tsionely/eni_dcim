"""Side-pair certificate: state machine + invariant executioners."""
from aigp.perception.certificate import (
    CERTIFIED,
    NONE,
    PROBATION,
    SidePairCertificate,
)

FXW = 512.0            # fx * 1.6
GOOD_W = [8.0, 9.0, 8.5, 9.5]


def good_update(c, ts_ns, z=2.0):
    sep = FXW / z
    return c.update(ts_ns, z, sep, sep, FXW, GOOD_W, GOOD_W, 0.8, 0.8)


def anchored(ts0=0):
    c = SidePairCertificate()
    c.on_full_quad(ts0)
    return c


def test_anchor_then_maintained_chain_stays_certified():
    c = anchored()
    ts = 0
    for i in range(10):
        ts = int((i + 1) * 0.05e9)          # 50ms steps, inside the gap
        assert good_update(c, ts) == CERTIFIED
    assert c.status_at(ts + int(0.05e9)) == CERTIFIED


def test_chain_break_demotes_to_probation_then_promotes_above_floor():
    c = anchored()
    good_update(c, int(0.05e9))
    # 0.5s gap: chain broken, pair still looks right -> PROBATION.
    ts = int(0.55e9)
    assert good_update(c, ts, z=2.0) == PROBATION
    for i in range(3):                       # clean streak promotes (z>1.4)
        ts += int(0.05e9)
        s = good_update(c, ts, z=2.0)
    assert s == CERTIFIED


def test_terminal_floor_blocks_fresh_certification():
    """Two naked vertical edges are never CERTIFIED in the terminal zone:
    below 1.4m a broken chain reaches at most PROBATION, forever."""
    c = anchored()
    good_update(c, int(0.05e9))
    ts = int(0.55e9)                         # chain broken
    for i in range(10):
        ts += int(0.05e9)
        s = good_update(c, ts, z=1.1)        # perfect frames, below floor
    assert s == PROBATION


def test_pillar_unbounded_width_fails_barness():
    """A floor-to-ceiling pillar / banner sheet has no bounded red run at
    bar width — the bar-ness invariant is its designated executioner
    (the separation ratio alone can PASS for the banner-edge pair)."""
    c = anchored()
    ts = int(0.05e9)
    sep = FXW / 2.0
    huge = [sep * 0.6] * 4                   # run far beyond bar width
    s = c.update(ts, 2.0, sep, sep, FXW, huge, huge, 0.8, 0.8)
    assert s != CERTIFIED


def test_width_disagreement_fails_barness():
    c = anchored()
    ts = int(0.05e9)
    sep = FXW / 2.0
    s = c.update(ts, 2.0, sep, sep, FXW, [8.0] * 4, [30.0] * 4, 0.8, 0.8)
    assert s != CERTIFIED


def test_wrong_scale_pair_not_certified():
    """The next gate's pair at ~4x range: separation ratio ~0.25 — far
    outside the band."""
    c = anchored()
    ts = int(0.05e9)
    sep_far = FXW / 8.0
    s = c.update(ts, 2.0, sep_far, sep_far, FXW, GOOD_W, GOOD_W, 0.8, 0.8)
    assert s != CERTIFIED


def test_status_decays_with_time():
    c = anchored()
    good_update(c, int(0.05e9))
    assert c.status_at(int(0.1e9)) == CERTIFIED
    assert c.status_at(int(0.3e9)) == PROBATION      # > chain gap
    assert c.status_at(int(2.0e9)) == NONE           # stale

def test_epoch_change_revokes():
    c = anchored()
    good_update(c, int(0.05e9))
    c.on_relock_or_collision()
    assert c.status_at(int(0.06e9)) == NONE


def test_p4d_honest_relock_refuses_wrong_gate_metrology():
    """P4(d) regression fixture (ruled: the honest-relock branch must
    be pinned once classified). F4 frames 308-315: CERTIFIED detector
    fixes at 17-20m arrived under a live sub-meter prior lock — the
    detector-only acceptance attributed far-gate metrology to the
    near-gate identity; the prediction-consistency gate relocks
    instead of anchoring, and the cleared identity cannot freshly
    re-certify below the promote floor, so the wrong-gate rows never
    become certified FULL metrology. Safety pair: a same-gate fix
    anchors; a first lock (no prior) always may."""
    from aigp.perception.pipeline import PerceptionAgent as P
    # The decision rule, on the recorded F4 numbers (p4d diff table):
    assert not P.anchor_consistent(0.579, 19.869)     # frame 308
    assert not P.anchor_consistent(0.502, 1.908)      # frame 309
    assert not P.anchor_consistent(0.077, 17.615)     # frame 315
    assert P.anchor_consistent(0.502, 0.55)           # honest same-gate fix
    assert P.anchor_consistent(None, 19.869)          # first lock: no prior
    # Consequence chain: the relock revokes the identity, and below
    # the promote floor the dead identity reaches at most PROBATION —
    # no certified metrology for the rest of the approach. This is
    # the certificate boundary's priced cost, accepted as ruled.
    c = anchored()
    good_update(c, int(0.05e9))
    c.on_relock_or_collision()
    assert c.status_at(int(0.06e9)) == NONE
    c.on_full_quad(int(0.1e9), z_m=0.6)               # sub-floor re-anchor
    ts = int(0.1e9)
    s = None
    for _ in range(6):
        ts += int(0.05e9)
        s = good_update(c, ts, z=0.6)
    assert s != CERTIFIED


def test_negative_controls_side_cannot_revoke_locked_identity():
    """Advisory-20 permanent regression invariant (the negative-control
    triplet beside the P4(d) fixture). Revocation
    (LOCKED_IDENTITY_REVOKED) is the DETECTOR wire's power alone —
    the SIDE producer may demote by evidence or decay by silence,
    never revoke:
    (a) ONE grossly inconsistent side-pair measurement demotes its
        own tick and the identity RECOVERS without a re-anchor;
    (c) ordinary SIDE tracking failure (silence) degrades by TIME
        decay and a detector re-anchor restores the held identity;
    (b) persistent gross target contradiction MAY revoke — pinned by
        test_p4d_honest_relock_refuses_wrong_gate_metrology (the
        certified-detector branch, the single revoke call site)."""
    # (a) single bad pair: demoted, not revoked; recovers in-chain.
    c = anchored()
    good_update(c, int(0.05e9))
    sep_far = FXW / 8.0                    # ~4x-range scale lie
    s = c.update(int(0.10e9), 2.0, sep_far, sep_far, FXW,
                 GOOD_W, GOOD_W, 0.8, 0.8)
    assert s == PROBATION                  # demotion, never NONE
    ts = int(0.10e9)
    for _ in range(3):
        ts += int(0.05e9)
        s = good_update(c, ts)             # clean streak, z=2.0 > floor
    assert s == CERTIFIED                  # same identity, no re-anchor
    # (c) silence: decay demotes; a detector re-anchor of the HELD
    # identity restores certification (contrast: after a revocation
    # the sub-floor re-anchor is refused — the P4(d) fixture).
    c2 = anchored()
    good_update(c2, int(0.05e9))
    assert c2.status_at(int(0.3e9)) == PROBATION   # decay, not revocation
    c2.on_full_quad(int(0.35e9), z_m=2.0)
    assert c2.status_at(int(0.36e9)) == CERTIFIED
