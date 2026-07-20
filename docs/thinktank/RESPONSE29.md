# RESPONSE 29 — The sigma_a estimator is reference-noise-dominated at maintenance ages; deconvolution proposed (interim — the deconvolved number is pending)

This is the HOLD-lift package's frame, filed before its final number
so the measurement-design finding reaches both channels without
delay. Items 6-9 of the ruling's twelve are green and pinned in the
build; this note carries the sigma_a story.

## 1. Reference provenance — measured, as ordered

The harness's truth-v_z was `state.v_world` (de-tilted believed).
Re-referenced to the ruling's own §7B standard (the WITHHELD FULL
oracle, Theil-Sen on e_z):

    reference            p95 |r|/a     RMS
    believed v_world      4.455        1.956
    withheld FULL oracle  2.340        1.614

The believed reference inflated the measurement (the caged-gravity
sawtooth, as predicted) — but the oracle-referenced number still sits
~7x above the 0.35 gate. R26-2/3 currently FAIL.

## 2. The finding: the ratio estimator cannot measure 0.35 at these ages

The §5 estimator sigma_a >= Q_p(|r_v(a)|/a) contains the REFERENCE'S
own rate noise divided by age:

    Var(|r_v|/a) = sigma_a^2 + sigma_ref^2 / a^2

With the measured oracle-slope noise sigma_ref ~ 0.15-0.3 m/s and
maintenance ages 0.1-0.5s, the sigma_ref/a term ALONE spans 0.3-3.0
m/s^2 — above the gate at ZERO true drift, across the rung's entire
lifetime. The estimator is noise-dominated everywhere it can be
applied; a FAIL from it is uninformative about the physics.

## 3. The proposed replacement — same model, separable estimate

The ruling's own drift model is Var(r_v(a)) = sigma_ref^2 +
(sigma_a * a)^2. Regressing r_v^2 on a^2 separates intercept
(reference noise) from slope (true drift):

    slope     -> sigma_a^2   (bootstrap CI)
    intercept -> sigma_ref^2 (sanity: must land near the measured
                              0.15-0.3 oracle-slope noise)

The 0.35 gate DOES NOT MOVE; only the estimator becomes measurable.
Requested: ratification of the estimator change. The deconvolution
runs on the already-pushed residuals (reference_comparison.csv,
caa2398) — no new replay.

## 4. Board state while the number is pending

GREEN and pinned in the build: causal feed-forward ordering,
exposure-aligned applied_at_anchor (command ring), current-time
anchor aging through observation loss, the runtime age-indexed
maintenance score gate (sigma_a ceiling 0.35 until measured), R26-1
re-stamped PASS with advancing age columns, R26-4/5/6 PASS.
PENDING: the deconvolved sigma_a (+ held-out coverage per age bin),
R26-2/3 formal close under the ratified estimator, P4 wall-clock.
Cohort 4 remains HOLD; if the deconvolved number passes and the
envelope covers, the lift request follows with the full twelve-row
board.
