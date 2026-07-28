# RESPONSE 93 — Channel-2 ADVISORY-2 on gate chaining: NO-GO accepted; but chaining is DOWNSTREAM of the R2 gate-1 wall found today, so the hardening is filed and gated behind reaching gate 1 on R2

Race-risk register. ADVISORY-2 is a full code walk with a No-Go on
flying the current 1.5m/s x 2s ADVANCE as a validation until a guarded
successor architecture + hostile fixtures land. It is correct
engineering, and honored.

## 1. The No-Go is ACCEPTED — and costs nothing right now

The channel's ruling: the current ADVANCE (fresh + fwd>1 = "acquired";
full-speed forward + one-sided yaw = a blind arc) identifies "a
gate-shaped pose ahead", not "the NEXT gate", and its motion is a large
blind excursion near structure. Accepted. But TODAY's A1 result
reframes the priority: on the real R2 course the frozen baseline passes
**0 gates** (commits toward a gate, collides with environment structure
at 17-33s). ADVANCE fires only AFTER a pass; with zero passes on R2 it
never runs (the C1 runs confirm: advance_seen=false). So the No-Go is
free — we were not going to fly ADVANCE-validation on R2 regardless.
The active wall is upstream: gate 1 on R2, not chaining.

## 2. Adopted already (RESPONSE92, pre-ADVISORY-2, convergent)

The channel's guard 1 (distance not time) and guard 2 (blind-speed cap)
were adopted before this advisory: ADVANCE now terminates on integrated
forward displacement (distance_m 1.2) with a blind-speed cap 1.2 and an
outer time watchdog. The headline PASS-source risk (its guard 7 / A-36
V5) was checked: our PASSED is the sim's active_gate_index increment
(ground truth), not our integral — verified in source. These converge
with the advisory.

## 3. Filed, GATED behind R2 gate-1 (the chaining iteration)

The full proposal is recorded as the chaining architecture, to build
WHEN chaining becomes reachable (a gate-1 pass exists on R2):
  - the CROSSING_HOLD/PASS_PENDING pre-score state (suppress retreat
    while geometrically behind-plane and the score edge is pending —
    the real pre-fix bug: retreat starts ~0.5s before the pass);
  - EXIT_CLEAR (yaw~0, frozen exit vector, short distance+time caps) ->
    SUCCESSOR_SEARCH (decelerate, bounded symmetric sweep) ->
    SUCCESSOR_VERIFY (>=k unique exposures, old-gate exclusion,
    forward-plane ordering, candidate competition) -> APPROACH;
  - detector publishes a top-K candidate set with per-track features
    (the architectural fix: identity cannot be solved from one retained
    pose after the estimator reset);
  - old-gate snapshot (plane/normal/track) carried across the estimator
    reset;
  - the 10 hostile fixtures (delayed pass, old-gate-turns-forward,
    far-gate ambiguity, through-opening successor, no-post-pass-gate,
    run-2 geometry, single-frame phantom, search reversal, sensor-stale
    exit, reset) as the pre-flight gate;
  - reset() clears _advance_pending / _advance_start_ns (state hygiene,
    adopted now — small, cheap).

## 4. Why gated, not built now

Building the top-K tracker + 10 fixtures is the correct architecture
but is the SAME mistake I just made — optimizing gate chaining while
the drone cannot pass gate 1 on the course that counts. The owner has
directed a cautious R2 probe (R2C) to find whether gate 1 is threadable
on R2 at all. Chaining hardening resumes the moment a gate-1 pass on R2
exists to chain from. Standing: race-risk mode; parked campaign
untouched; no HOLD-lift; sigma_a_cfg 0.35.
