# RESPONSE 9 — Answers to Advisory 6

Build: this response ships with the advisory-6 items that survived data
contact. Sakana is concurrently flying phase6c (78c8461) — nothing here
changes that build's flight behavior.

## P1 — CONFIRMED real, fixed, and then the fix taught us something bigger

The check you specified was decisive. Line-of-code answer: gravity was
added as `g*z-hat` in the filter frame. Pad-log verification:

    residual today:  [-2.999, -0.002, +0.466] m/s^2   (spec: <0.1 all axes)
    g' from level:   [+3.001,  0.000, +9.336]         (your predicted x ~ +3.0)
    residual fixed:  [+0.002, -0.002, -0.004]

The honest vector is implemented (`g' = R_level^-1 (0,0,g)`, derived from
the stored level reference) with a 5s-rest regression test. **But the
closed-loop A/B on the faithful mock failed 3/3 with the fix enabled**:
takeoff pitched to -17 deg and the ship dove into the floor. Diagnosis:
the whole cascade is co-tuned against the residual — the attitude filter
is rest-zeroed, the attitude hold targets the REST pose
(`pitch_des = level_pitch - PID`), and the vel-PID trims absorb the
difference. Correcting gravity ALONE removes one leg of a mutually
compensating web (your "four compensation generations", now measured in
one experiment). The honest vector therefore sits behind
`estimation.true_gravity` (default false), and your §0 architecture note
is upgraded from recommendation to REQUIREMENT: the frame migration must
happen at the source as ONE designed change — attitude anchor
(initialize q at the level reference), gravity vector, controller
reference semantics (`use_level_ref`), and PID/hover trims — validated
by the mock closed loop, the gt harness, and M2. The failing mock A/B is
that migration's ready-made regression test.

## P2 — isotropic, closed

`v_world *= (1 - leak*dt)` — scalar. `vision_blend` and
`vision_vel_blend` — scalar blends on full vectors. All covariant; rank-3
concern is clean.

## P3 — captured

Rest roll is measured and stored alongside pitch (measured +0.000 on
every pad calibration; the mount tilt is pure pitch, as you inferred
from the lateral/vertical asymmetry). `level_quat` composes both. Full
rest-quaternion storage is adopted as part of the migration project.

## Q2 — implemented this build

- The no-abort radius is now the formula `v^2/(2 a_brake) + t_react*v`
  (defaults reproduce the measured ~1.2m at 2.5 m/s; `a_brake` awaits
  direct measurement from retreat-segment kinematics — assigned).
- Your twin-of-T3 commandment is law: corridor breaches only count on
  FRESH vision (age <= 0.3s). F2's fossil abort ran on age 0.32s — it is
  now the unit test.
- Sign-only bounded nudge: accepted as designed, deferred until the V2
  sign-certain signals exist; its zero-wrong-sign kill test is noted as
  the shipping bar. Carry-through's decision-theoretic dominance
  (external adjudication, survivable clips) is recorded in the planner
  comments.

## Q3 — adopted verbatim

Shadow-during-validation is already live (SHADOW + FEATURE topics stream
on every commit tick since phase5e). The three-green enable gate — M2
slope collapse, V3 RMS <= 0.05m in the 1.5-3m band, FA=0 suite including
the banner impostor — replaces the calendar.

## Q4 — adopted with your ranking

Exit-vector banking (over already-computed, currently-discarded
detections) -> FOLLOW/BRIDGE/HOVER-SCAN state machine -> ribbon pursuit
gated on extended-R1. Queued behind gate 1; D7 and extended-R1 are
assigned to the analyst/operator queues. The F1 believed-40m chase is
the acquisition gate's replay kill test, as specified.

## M2 — running

Assigned to the analyst with your regression spec verbatim: slope ~0.31
= phantom share, constant ~0.33 = aperture share; predictions to check:
LOW cluster collapses, F2 re-classifies pass-worthy, holdout harness
axes reissued. A6/A4/A8 remain the open geometry keystones.
