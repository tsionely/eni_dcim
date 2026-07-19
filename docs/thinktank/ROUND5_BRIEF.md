# Round 5 Brief — The Tilted-Frame Phantom (advisory teams 1 & 2)

Status: sent to both advisory teams. Advisory-only: every suggestion is
validated against recorded data before any code changes.

## The discovery (phase6b forensics, build 93fba45 -> fix 2c5057a)

The attitude filter zeroes the drone's TILTED rest pose: on the pad the
state quaternion reads identity while the IMU physically sits -17.8 deg
nose-down (stored separately as level_pitch=-0.311). Every "world"
rotation downstream therefore lands in a frame pitched 17.8 deg from
true level. Consequence: every vertical judgment in the planner mixed
in sin(17.8 deg) * range ~ 0.31*R of phantom "gate above me":

- At R=6m (pad): the gate read 3.2m "above" when the true height is
  ~1.3m. An entire phase (6b) chased this artifact with a taller
  takeoff, overshooting the real opening.
- At R=1-1.5m: the phantom is 0.31-0.46m — straddling the 0.45m abort
  threshold. Flight F2 (20260719T075333) arrived at R=0.82m centered
  on BOTH axes (gate center pixel [316, 233]; opening center projects
  to y~243 at that range) and the abort corridor, reading the phantom
  as +0.58m of vertical error, commanded a retreat 0.8m before the
  plane. The drone's 2.5 m/s momentum carried it INTO the gate: the
  gate clip at impulse 4.3 is the fossil of an aborted perfect pass.

## The fix (2c5057a, flying next cycle as phase6c)

- true_world_dz(): composes the measured rest attitude (level_roll,
  level_pitch) back into the world rotation. Consumers: altitude hold,
  align gate, abort corridor, terminal channel (e_z, v_z, adapter).
- Abort corridor: no retreat inside 1.2m (braking distance — the
  retreat IS the collision there); corridor band is now 1.2-1.5m.
- Post-miss reacquisition guard: 6s window after a failed attempt in
  which approach refuses targets beyond 9m (F1 chased a believed-40m
  relock across the obstacle field into three env hits).
- takeoff.duration_s back to 1.5s (true opening ~1.3m above the pad).

## Questions for the advisory teams

1. **Residual tilted-frame consumers.** We de-tilted the planner's
   vertical judgments and the terminal channel. Audit request: what
   else implicitly assumes the filter world == true world? Candidates
   we see: (a) v_world's gravity handling in the estimator (it was
   built self-consistently in the rest frame — phantom-velocity bugs
   were solved there long ago, so we did NOT touch it); (b) retreat
   climb biases and search climb (open-loop, tuned historically ON TOP
   of the phantom — should they be re-zeroed?); (c) the commit
   velocity direction vector itself (frame-covariant, so unaffected —
   agree?). Rank by risk.
2. **The no-retreat band.** Inside 1.2m we now always carry through.
   Failure mode to weigh: a genuinely off-corridor arrival (true
   lateral 0.5m+) now strikes the frame instead of retreating. Data
   says retreat there strikes ANYWAY (F2). Is there a third option
   worth designing (e.g., lateral dodge within the plane, or throttle
   cut)? Keep in mind pass events are external (sim adjudicates).
3. **Terminal-channel enablement.** The vertical terminal channel
   (certificate-gated, single-owner arbiter, now frame-honest) is
   still enable=false. Proposal: enable it the cycle AFTER phase6c
   validates the true frame, so attribution stays clean. Any reason to
   couple them instead?
4. **Gates 2+ pre-planning.** If phase6c passes gate 1: the next
   frontier is inter-gate navigation (5.7m+ spacing, obstacles, the
   cyan ribbon as a corridor hint). The reacquire guard (9m) already
   constrains relocking. What minimal navigation discipline between
   gates would you design FIRST, given one fixed forward camera and
   no GPS?

## Data anchors (for skeptical review)

- fixtures/20260719T080320-phase6b-aligned-dash/ — the three counted
  flights, notes.md, slices.
- Pad geometry pin: first detection of 20260717T153903, rel_pose
  t=[0.015, -3.217, 5.525] with q=identity, level_pitch=-0.311:
  naive dz=-3.22 (phantom), true dz=-1.37. Pixel cross-check: gate
  center at image center on the pad = camera axis elevation (29-17.8
  = 11.2 deg) at 6.13m slant = 1.19m true height.
- Unit pin: tests/unit/test_planner.py::test_true_world_dz_untilts_rest_frame.
