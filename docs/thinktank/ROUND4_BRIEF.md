# ROUND 4 BRIEF — after the terminal-ownership flights

Paste to BOTH think tanks, together with RESPONSE5 + RESPONSE6 (tank #1)
or RESPONSE6 alone (tank #2, which already has RESPONSE4). This is the
state update plus ONE focused question each.

## State (verified flight data, build 34d4f6b, three flights on verified R2-TRAINING)

Confirmed working in flight: terminal ownership (no more next-gate
steal — the drone stays on the near gate through the attempt), same-gate
reacquisition after clips (richest retry chain yet:
approach→commit→retreat→approach→commit), honest direct fixes to
0.90/1.46/1.83 m. Still zero passes. The remaining failure is purely
VERTICAL, with a clean two-part signature:

1. **Consistent LOW arrivals**: at closest approach the gate sits high
   in frame (y≈85-96 of 360, camera +11° up) ⇒ the drone is ~0.4-0.5 m
   BELOW the opening center, and drops short. Root cause traced: our
   no-arm veto (shipped after the HIGH-overfly round) killed the sink
   insurance whenever the altitude hold climbed at all. Fixed to TOP-UP
   semantics (insurance fills only the gap between the hold's climb at
   entry and the insured sink rate) — flying next cycle.
2. **Post-retreat ceiling chase**: far fixes carrying physically
   impossible heights (det ty −13.8 m in a hangar where gates stand
   ~3 m up) pulled 2.3 m/s climbs into the roof truss. Fixed with a
   height-plausibility gate (|ty| > 6 m ⇒ pose rejected).

Also now flight-confirmed from the H3 census: the SIDE BARS are the
last-surviving structure on a centered approach (left→right→bottom→top),
matching tank #1's prediction; and the banner appears mid-approach on
HIGH trajectories — the structure-identity-as-vertical-signal holds.

## The question — same core, per-tank angle

The last unwired piece is the terminal vertical channel. The building
blocks exist and are tested: GateCloseTracker (projected-edge fixes,
side-bar absolute range), vertical_terminal.py (scale-normalized
oracle, crossing forecast, velocity-closure command, phase schedule,
TTC from 1/span). What does NOT yet exist: the wiring — who computes
y_T/ℓ_T with verified structure identity, at what rate, and how its
output overrides/blends with the existing commit steering
(gate_direction + crosstrack + altitude_hold + top-up insurance).

**Tank #1** (t_c/plane-filter thread): given side-bars-last is now
flight-confirmed, spec the minimal identity test that certifies "these
two vertical edges are the near gate's side bars" (vs pillar edges,
truss verticals, next-gate bars) using only what the tracker knows
(projected model, covariance, edge support) — the certification is what
gates BOTH the absolute-range feed and the terminal vertical servo.
Plus your pending c_i anchoring answer (RESPONSE5 §7).

**Tank #2** (guidance-law thread): spec the override arbitration — when
the terminal vertical channel is healthy, does it REPLACE
altitude_hold+insurance outright inside commit, or blend? Your
compute_terminal_guidance returns an az correction while our control
stack takes body-frame VELOCITY setpoints at 250Hz — give the exact
adapter (vz* → v_body[2] with slew limits) and the fallback ladder when
the channel degrades mid-commit (BAR_ROW_ONLY → BAR_LOST) so the
handback to altitude_hold cannot step the command. Kill tests on the
committed phase5c slices for both.

Constraint reminder: offline-provable first (the phase5c fixtures are
committed, takeoff→end, >10s unique frames each), rank by
impact×simplicity, state the kill test for every proposal.
