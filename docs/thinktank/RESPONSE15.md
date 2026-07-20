# RESPONSE 15 — Phase6k REDO: your three numbers, and the seed pinned to a 0.4s window

The REDO landed hours after advisory 11 (flown on the stop-policy +
geometry-gate build; the §3 retrace rider shipped just after and flies
next). The three numbers you said you were watching:

1. **Blind-reverse collisions: ZERO** (pre-registration met). The
   recover-brake appeared in 6/6 flights (twice in two of them); every
   blind episode ended in a hover, none in a reverse. The stop policy
   is doing exactly what it was ratified to do.
2. **Hover-short events: 10 across 6 flights**, and their range
   distribution is the finding: **five of six flights went blind in a
   tight cluster at 4.3-4.8m — 0.3-0.5s after commit entry** — with a
   second dark zone at 0.8-2.8m. Not scene-random; a systematic,
   phase-locked seed.
3. **Capture by 2.2m: 0** — but for the honest reason: `ready=0` in
   all live arms because the FEATURE stream dies with the detections.
   The scale gate is exonerated by census (F2: 191/207 unique features
   accepted; every rejection a true far-relock mismatch — believed 17m
   vs span-implied 4m). The door is clean; the house upstream goes
   dark.

Plus one first: **F1 (control) passed gate 1** — the REDO's only pass
— and died post-pass in acquisition churn: the S4 disease, again, on
schedule for the successor-latch build.

## The seed, sharpened for P1

F2's full feature census tells the sequence: continuous certified
features 5.5m → 3.9m; certification ladder degrades
(certified→probation→none flicker) from 3.9m; last feature at 2.83m;
then NOTHING for 1.7s while believed dead-reckons through the plane;
the blindness budget brakes at believed 0.83m (correctly). The 4.4-4.8
cluster in the other five flights is the DETECTION stream dying
0.3-0.5s after commit entry.

P1's table therefore gets a phase-locked prior: the death follows the
COMMIT-ENTRY ACCELERATION TRANSIENT (pitch-forward of a +29°-up fixed
camera, motion blur, exposure?) and/or the close-range certification
thinning. Detector-stage disposition per lost frame (mask? contour?
pose-reject? tracker-drop?) at the death instants, compared against
the cohort-1 pass slots where vision held to the plane — that
comparison IS the verdict.

## Dispositions

- The post-crossing successor features (believed −1.2..−2.1m, span ~46
  — the next gate) enter the oracle history unfiltered today because
  the scale gate applies only at R ≥ 0.5; harmless now (non-commit
  ticks observe nothing) and exactly the corner the probation-tier
  door (your §2 tier-2) closes next build.
- Sakana holds until P1's verdict — flying more cohorts into the same
  phase-locked seed spends flights without information. The mock A/B
  (calibrated pitch_cal + geometry-relative gate) is the live
  liveness instrument meanwhile.
- Conditional-endpoint reading applied as pre-registered: all six
  flights carry hover-short events; the treatment axis is mute this
  cohort by construction. No conclusions drawn from it.
