# RACE RISK BRIEF 2 — the gate-chaining problem (for both advisory channels)

Race-risk advisory mode (R89 §4). Engineering triage, no criterion
machinery; the parked calibration campaign is untouched.

## The reframing (owner-driven, honest)

For a week the program optimized the gate-1 CROSSING and plateaued at
~30-40% gate-1 on the R1 event. The owner correctly redirected: that
is a local optimization; WINNING needs a completed multi-gate track,
and the drone has NEVER passed gate 2. The flight must be fully
AUTONOMOUS — vision + IMU only, no GPS, no map, no hard-coded layout.

## What the logs prove about gate 2

Traced a gate-1-passing run (fixtures/*b1-B-run2) second by second:
- 19.9s commit v=[+1.5,..] flying forward through gate 1
- 20.3s the commit exits to RETREAT v=[-1.2,..] — flying BACKWARD
- 20.8s the gate-1 pass event fires (drone already retreating)
- 20.8s search (blind yaw spin), 22.2s align, 24.3s commit,
  25.8s COLLISION x13 — crash. Gate 2 never reached.
Post-pass detections exist SOMETIMES (run2: a gate at fwd +3.0m,
right -2.6m, high-conf) and sometimes not (run3: zero after the pass).
So the failure is BOTH: (a) the planner retreats/spins after a pass
instead of advancing; (b) even when a next gate is visible it is not
cleanly acquired before a collision.

## What was just shipped (c07fe45) — for you to critique

A new ADVANCE state: on a pass, fly FORWARD at 1.5 m/s for 2s while
scanning (last-seen-side yaw), hand off to approach the instant a
fresh gate is seen AHEAD (fwd > 1.0m, age fresh), ignore the
just-passed gate (fwd <= 0), a collision ends it. First cut, config-
gated (planner.advance.{duration_s,speed_mps,min_fwd_m}), 247 tests
green, unflown.

## The questions for the channels (advisory only)

1. Is forward-advance-and-scan the right autonomous primitive between
   gates, or is there a better vision-only next-gate search (e.g.
   yaw-sweep-in-place vs forward-progress; how to bias the scan
   direction without a map)?
2. The just-passed gate re-detection hazard: after passing gate 1 the
   estimator may relock gate 1 (now behind) or a far gate. fwd<=0
   rejection is the current guard — is it sufficient, and how should
   "which blob is the NEXT gate" be decided from vision alone?
3. Momentum/geometry: the drone exits gate 1 at speed on some heading;
   the next gate can be off-axis (run2: 2.6m lateral). What is the
   right decel/turn/re-acquire sequence that does not collide with
   gate-1's frame or nearby structure on the way out?
4. Failure-mode risk of the ADVANCE change: flying forward blind for
   2s could drive into structure if no gate appears. What bounds/guards
   would you require (distance cap, obstacle-aware abort, shrink the
   window)?

Evidence: fixtures/*b1-B-run2 (pass-then-crash trace),
fixtures/*b1-B-run3 (blind after pass), src/aigp/planning/race_planner.py
(the ADVANCE block + on_gate_passed). Conservative-on-conflict; nothing
here lifts any HOLD or touches the parked campaign.
