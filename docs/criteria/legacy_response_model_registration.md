# MODEL REGISTRATION — Contract B closed-loop response model (the DYNAMIC TRANSFORM)

Registered BEFORE the post-criterion generator exists (channel-2 on
R60-63 §5: the counterfactual transform cannot first appear inside
the result-producing artifact). This document is REG-1: the
complete model FORM, calibration PROCEDURE, and every declared
choice. It is numerically INCOMPLETE until REG-2 — a follow-up
commit that fills the NUMERIC BLOCK below from the A091 calibration
artifact and binds that artifact's path and SHA-256. The generator
commit must carry REG-2 as an ancestor; a generator descending from
REG-1 alone fails ancestry.

## 1. Model equation (form, fixed here)

Discrete first-order lag tracking of the commanded velocity
reference, in world-up after the Contract B frame transform,
tick dt = 0.02 s:

    v_hat[k+1] = v_hat[k] + (dt / tau) * (g * v_ref[k - L] - v_hat[k])

    v_ref  = world-up commanded velocity reference
             (setpoint.v_body[2] through
              v_up = -v_bz * cos(level_pitch) * cos(level_roll))
    v_hat  = model-predicted causal legacy contribution
             (the INTERVENTION QUANTITY of the Contract B chain)
    g      = steady-state tracking gain          [NUMERIC BLOCK]
    tau    = closed-loop time constant, seconds  [NUMERIC BLOCK]
    L      = transport lag, integer ticks        [NUMERIC BLOCK]

No additional terms (no feed-through, no derivative branch, no
deadband) — the form is the simplest declared model; inadequacy is
published as calibration residual, never absorbed by post-hoc
structure.

## 2. Calibration source and method (fixed here)

- **Source**: the A091 physical TERM episode (20260719T201851)
  DOWN-STEP intervals ONLY — the one episode with both a logged
  command and a densely measured physical response. The
  CALIBRATION interval is identified by row keys in the
  calibration artifact and is DISJOINT from the A091 SENTINEL
  interval (criterion, row-level proof clause): no rows wear two
  hats.
- **Fit method**: least squares of the model's step response
  against the measured response over the calibration interval, on
  a declared (g, tau, L) grid — L over integer ticks 0..25 (0 to
  0.5 s), tau over 0.02..0.60 s, g over 0.5..1.5; grid declared
  here so the optimum is a lookup, not a choice.
- **Uncertainty**: the calibration artifact publishes the residual
  RMS at the optimum and the parameter box in which fit RMS is
  within 10% of optimum (profile box). The intervention republishes
  its headline quantities at the box corners as a SENSITIVITY BAND
  — published always, adjudicative never.
- **Prohibition (channel-2, binding)**: the 23 archive approaches
  may not select g, tau, L, clipping, or sign — not directly, not
  by "which parameters make the table land on a favorable branch".
  Only A091's calibration interval selects numerics.

## 3. Declared handling rules (fixed here)

- **Initial state**: v_hat starts at the first valid reference
  sample under a steady-state assumption, v_hat[0] = g * v_ref[-L];
  a burn-in of max(3 * tau, L * dt) is excluded from intervention
  support (typed BURN_IN, listed, never zero-filled).
- **Saturation**: v_hat is clipped to the era's registered vertical
  command cap; every clipping event is listed in the artifact. A
  cut whose support is majority-clipped is FLAGGED and excluded
  from threshold counting (listed, like the estimability
  exclusions).
- **Missing input**: None/absent reference rows produce OFF_SUPPORT
  rows — typed, counted, listed; NEVER zero-filled; 0.0 is an
  observed reference value and propagates through the model
  normally (zero/None law).
- **Era transport**: parameters are calibrated on A091's era.
  Transport to any other era requires a published per-era
  applicability row in the era/funnel ledger (same-backend
  affirmation or a named difference). An era that cannot affirm
  applicability has its rows typed OFF_SUPPORT for the
  intervention — reducing coverage honestly, never silently.
- **Sign/frame**: the frame transform is the adapter's own
  equation, derived in writing in the artifact; the sign/frame
  inversion fixture (criterion, negative controls) must fail
  loudly when either factor is flipped.

## 4. NUMERIC BLOCK (REG-2 — empty in REG-1 by construction)

    g    = PENDING_CALIBRATION
    tau  = PENDING_CALIBRATION
    L    = PENDING_CALIBRATION
    calibration_artifact_path   = PENDING
    calibration_artifact_sha256 = PENDING
    calibration_interval_keys   = PENDING (disjoint from sentinel)
    residual_rms_at_optimum     = PENDING
    profile_box                 = PENDING

REG-2 fills every field above, citing the pushed calibration
artifact; the generator's ancestry check names REG-2's commit. Any
change to Section 1-3 after REG-2 voids the registration and
restarts it.
