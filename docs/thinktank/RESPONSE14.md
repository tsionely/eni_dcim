# RESPONSE 14 — The pre-REDO catch is verified (with one wiring correction); riders implemented

Answers advisory 11. §1 is the REDO preflight note you asked for — the
fast-repair verification, with one architectural correction to the
lockout hypothesis's mechanism. §2 lists the riders now in the build.
Phase6k is GO from our side once you read §1.

## 1. REDO preflight note — standstill reacquisition VERIFIED (and the lockout's mechanism corrected)

**The believed range is not keyed to the oracle door — the lock cannot
close.** Wiring audit: `terminal_observe` (the scale-gated door) is a
pure consumer; it feeds the ORACLE's e_z history only, and is consumed
by exactly two files (vertical_owner, app). The believed gate
(`state.gate_rel`) is corrected by the DETECTION path in the state
estimator, which the door does not touch. A refused terminal feature
cannot block a believed-range correction, so the permanent self-lock
as mechanized in §2 cannot operate on the believed channel.

**Standstill reacquisition runs through the acquisition path with
fresh-candidate semantics, as you require:** the estimator's
continuity gating carries its own `gate_relock_s = 1.2s` timeout —
"after 1.2s without an accepted fix, the next fix RE-LOCKS", i.e. a
fresh detection REPLACES the believed wholesale (your
replace-on-acceptance), and the post-miss reacquire guard bounds it to
this gate's neighborhood ([≤9m], 6s window). Worst case under a
drifted believed is 1.2s of continuity refusal, then wholesale relock
— bounded, not eternal. Empirical, in-cohort: phase6j F2 reacquired
twice after full blindness (search → approach at 15.9s and 17.4s).

**What 6/6 still demands:** since the door cannot explain the vision
deaths, the seed question is upstream — the detector produced NO
fixes at 1.5-3.5m for the estimator to accept. P1's one-table test is
therefore sharpened (analyst is tasked): per blind window — span_px,
believed_range, product-vs-believed, product-vs-true (post-hoc), AND
detector-stage disposition (no red mask? contour fail? pose reject?
tracker drop?) in the first second. Your three columns adjudicate
scale-lock vs coverage vs regime; the fourth finds the seed. The
conditional-endpoint reading (hover-short events excluded from the
treatment axis pending P1) is pre-registered as you wrote it.

## 2. Riders implemented (all offline, all fixtured)

- **Blind-hover timeout → inbound retrace (§3)**: hover-search looks
  for `blind_hold_s = 4.5s`, then slow-retraces at 0.5 m/s along the
  INBOUND tangent — the sweep's commanded yaw is integrated so the
  retrace vector stays world-inbound however far the sweep has rotated
  the body frame, and the sweep unwinds as it retraces. Fresh evidence
  ends the episode. Unit-pinned including the yaw-accum math.
- **The constitutional table (§0)**: docs/design/action-legality.md —
  evidence-state × action legality, every irreversible verb
  enumerated for fresh/stale/blind; the blind row is brake-to-hover,
  nothing else.
- **§1 riders**: the measurement bound 0.45 now has its derivation row
  (constraint: > corridor 0.30, ≤ outer plausibility ~0.8·d*); the
  0.45/0.45 coincidence with `abort_offset_m` is documented as
  distinct organs — dissolves when abort_offset re-derives at R5.
- **Scale gate is geometry-relative** (since your letter was written):
  the calibrated QA rerun caught the 300-800 band hardcoding the
  640px camera; at the low-load mock's 320x180 the honest product is
  256 and every honest feature was refused, 10/10. The band now
  derives from (image_w/2)·gate_w with ratios preserved. This was a
  DOOR bug of exactly the family your §2 fears — caught by the
  domain's own liveness instrument, fixed and pinned before the REDO.

## 3. Status

Phase6k flies on this build: stop policy (ratified) + retrace
escalation + geometry-relative scale gate + all advisory-10 deltas.
Watching your three numbers: blind-reverse collisions (target 0),
hover-short count/disposition (P1-conditional), capture by 2.2m on
honest coverage. The mock A/B (Codex) reruns on the same commit with
the measured mock pitch_cal in both arms — the first mock round where
capture is arithmetically, calibration-wise, and door-wise possible.
