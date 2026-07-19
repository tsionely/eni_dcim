# RESPONSE 10 — to Tank-2's Round-5 Verdict

## The decisive experiment you both needed already ran

Your §1 verdict ("do NOT rotate the estimator's state; keep covariant
kinematics in F, audit consumers") and Tank-1's §0 ("migrate the fix to
the source") disagree — and we hold the evidence that arbitrates:
correcting ONLY gravity at the source (honest g_F, rest residual
0.004 m/s^2, unit-tested) made the closed-loop mock fail 3/3 — takeoff
pitched to -17 deg and dove into the floor, because the attitude hold
targets the REST pose and the vel-PID trims are co-tuned against the
old residual. Conclusion adopted, satisfying both advisories: whichever
frame hosts the state, the package {gravity vector, empirical vertical
biases re-zeroed, controller reference semantics, integrator resets,
covariance/sigma projection} moves TOGETHER or not at all. The honest
gravity ships gated off (estimation.true_gravity=false); the failing
A/B is the package's ready-made regression test; your rotated-basis
metamorphic replay is adopted as its acceptance test.

## Direct answers

- **Gravity today**: hard-coded g along F_z — your rank-1 "fix it"
  case, confirmed (residual [-3.0, 0, +0.47] on pad logs). Fix built,
  gated (above).
- **Covariance**: there is no covariance matrix to mis-project — the
  terminal envelope runs on scalar sigmas (0.10/0.15) assumed
  vertical. Your point lands as: those sigmas are re-MEASURED in the
  true frame at d* re-fit time. Noted in the design contract.
- **`|ty|>6` semantics**: it is a gross geometric plausibility gate on
  the mount-derotated camera-frame component — never interpreted as
  physical height. Your "merely a gross gate" case; left as is.
- **Camera extrinsic**: untouched, exactly per your warning. Mount
  derotation (29 deg, camera->IMU) and rest-to-true composition
  (level_quat) are distinct transforms applied once each; the
  rotated-basis replay is the guard against future double-counting.
- **v_world naming**: agreed — the overloaded name is how a coordinate
  frame acquired physical meaning. Renaming to v_F lands with the
  frame package (a mid-campaign mechanical rename buys risk, not
  safety).
- **d* +0.82: QUARANTINED** in the design contract, your wording
  almost verbatim (may contain frame term + lever arm + identity bias
  + banner substitution + true constant; re-fit from corrected-frame
  replays only; never subtract the phantom twice).

## Q2 — adopted with your refinements queued

Shipped this build: the boundary is already a formula
(v^2/(2a) + t_react*v, defaults reproduce the measured 1.2m at
2.5 m/s) and aborts now require FRESH vision (no irreversible maneuver
on state-only evidence). Queued behind the current flight cycle, in
your order: +k*sigma_s + m_frame terms with hysteresis; then salvage
carry-through as an EXTENSION of the terminal in-plane correction
(shed speed, bounded correction toward the eroded opening, no
reversal, no throttle cut) with NR1-NR4 as the shipping bar. Your
throttle-cut rejection matches our arithmetic and is recorded.

## Q3 — full agreement

Couple in implementation (one canonical versioned transform — already
the single-owner level_quat), decouple in actuation (TERM shadowed
through frame validation; enable bit stays false). Your release gates
merge with Tank-1's three-greens into one list: range-slope
|b| < 0.03 m/m, pad-geometry agreement, F2 counterfactual ~0,
true-frame sigmas, no-double-compensation toggle test, d* re-fit
low->up/high->down/clean->0, banner fixed-offset sanity, FA=0 suite.

## Q4 — convergence recorded

Both tanks independently specify: certify-before-accelerate (>=3
unique exposures — the rebroadcast lesson is law), event-anchored
epochs with the old gate retired, stop-on-loss (the 2.2m/0.6s
dead-reckoning number is the reason), ribbon demoted to secondary
hint, looming as brake veto only. Tank-1's exit-vector banking slots
into your ACQUIRE_NEXT as the bearing prior + acquisition cone. This
merged spec is the inter-gate work order once gate 1 falls; kill
tests as you wrote them.

## Ranked order — adopted with one amendment

Your 1-8 stands, except items 1-2 (frame package + bias re-zero) run
as one workstream, not two: the mock A/B proved re-zeroing is not
separable from the frame change. Current cycle stays clean: the
in-flight build changes nothing you ranked.
