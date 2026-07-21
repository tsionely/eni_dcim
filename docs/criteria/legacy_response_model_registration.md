# MODEL REGISTRATION — Contract B closed-loop response model (the DYNAMIC TRANSFORM)

Registered BEFORE the post-criterion generator exists (channel-2 on
R60-63 §5: the counterfactual transform cannot first appear inside
the result-producing artifact). This document is REG-1: the model
FORM and calibration PROCEDURE. It is numerically INCOMPLETE until
REG-2 — a follow-up commit that fills the NUMERIC BLOCK below from
the A091 calibration artifact and binds that artifact's path and
SHA-256. The generator commit must carry REG-2 as an ancestor; a
generator descending from REG-1 alone fails ancestry.

**AMENDED PRE-CALIBRATION (channel-2 on R64 §4 — this amendment
precedes any calibration artifact, so no methodological choice
moves from criterion into evidence): the first edition claimed
"every declared choice" while leaving grid increments, tie-break,
interval selection, the measured-response field, the corrected-
residual equation, and TERM-to-legacy transport open. Those are
frozen below. REG-2 fills NUMERICS ONLY, never methodology.**

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
  CALIBRATION interval is selected by the DETERMINISTIC DETECTOR
  below (never by the artifact generator's judgment) and is
  DISJOINT from the A091 SENTINEL interval (criterion, row-level
  proof clause): no rows wear two hats.
- **DOWN-STEP DETECTOR (deterministic, fit-blind — it never reads
  fit quality; channel-2 on R64 §4.2):** operating on the world-up
  reference stream at the dt = 0.02 s tick grid:
  1. STEP EVENT at tick k if v_ref[k] - v_ref[k-1] <= -0.30 m/s
     (minimum step magnitude = the registered admission-corridor
     constant). Consecutive qualifying ticks merge into ONE event
     anchored at the first qualifying tick.
  2. PRE-WINDOW: the 10 ticks before k must exist with
     |v_ref[i] - v_ref[k-1]| < 0.05 m/s (the registered near-zero
     constant) — the reference is stable before the step.
  3. POST-WINDOW: 25 ticks after k (0.5 s, the registered interim
     validated-age ceiling), truncated at the next step event
     minus one tick (gap/overlap rule).
  4. EXCLUSIONS (typed, listed, never silent): any window row with
     absent reference or absent measured response -> the window is
     excluded ABSENT_INPUT; window overlapping the sentinel
     interval -> SENTINEL_DISJOINT; window with fewer than 8 valid
     rows -> INSUFFICIENT_ROWS.
  5. NO QUALIFYING WINDOW -> the calibration returns UNCALIBRATABLE
     (typed) and the criterion's Contract B item-5 fallback applies
     (registered prior-tick semantics with a published zero-lag
     sensitivity band, both shown). UNCALIBRATABLE is a result,
     not a license to loosen the detector.
- **MEASURED RESPONSE (exact field, frozen here):** the
  oracle-measured world-up vertical velocity — checkpoint column
  `v_full_raw_mps` (the raw, unattenuated FULL-quad measurement;
  runtime twin `rate_anchor_v_raw`), at `feature_ts_ns`
  timestamps. Frame/sign: already world-up positive-up by the
  adapter's derivation, restated in writing in the artifact.
  Timestamp alignment: reference exposure-aligned per the
  registered prior-tick semantics; response mapped to the tick
  grid by nearest tick with maximum mismatch one tick, mismatches
  listed. Duplicate broadcasts of one frame (same flight_id +
  frame_id) deduplicate to the FIRST by feature_ts_ns. Missing
  response rows are excluded and listed (ABSENT_INPUT), never
  zero-filled; measured 0.0 is a value and enters the objective.
- **OBJECTIVE AND WEIGHTING (frozen):** sum of squared
  (v_meas[k] - v_hat[k]) over all valid rows of all qualifying
  windows, EQUAL WEIGHT PER ROW (windows are not reweighted;
  window count and per-window row counts are published).
- **GRID (exact ordered candidate lists — the optimum is a
  lookup, not a choice):**
      g   : 0.50, 0.55, ..., 1.50   (step 0.05, 21 values, ascending)
      tau : 0.02, 0.04, ..., 0.60 s (step 0.02, 30 values, ascending)
      L   : 0, 1, ..., 25 ticks     (26 values, ascending)
  ITERATION ORDER: L outer, tau middle, g inner (lexicographic,
  all ascending). COMPARISON: IEEE-754 float64, strict less-than,
  no epsilon. TIE-BREAK: the FIRST candidate in iteration order
  attaining the minimum wins (a later equal objective never
  replaces it). All candidate scores are published, not only the
  winner.
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
  applicability row in the era/funnel ledger. An era that cannot
  affirm applicability has its rows typed OFF_SUPPORT for the
  intervention — reducing coverage honestly, never silently.
  **TERM-TO-LEGACY TRANSPORT PROOF (channel-2 on R64 §4.5 — the
  calibration source is a TERM episode; the mechanism concerns
  legacy-commanded approaches; "same backend" must be TYPED, not
  affirmed):** before REG-2 transports the A091 triplet anywhere,
  the era/applicability ledger must fill, per era:
      TERM reference producer and consumer (module/field);
      legacy reference producer and consumer (module/field);
      the shared downstream velocity-tracking controller path;
      configuration/gain equivalence (same values or named deltas);
      limiter/saturation equivalence (same caps or named deltas);
      known era-specific differences, each named;
      the era's vertical command cap VALUE with its config source
      file and commit.
  A material difference in any row bars transport by labeling: the
  era is OFF_SUPPORT until the difference is either priced into
  the sensitivity band or resolved by its own calibration.
- **Sign/frame**: the frame transform is the adapter's own
  equation, derived in writing in the artifact; the sign/frame
  inversion fixture (criterion, negative controls) must fail
  loudly when either factor is flipped.

## 3b. Corrected-residual equation (channel-2 on R64 §4.4 — the sign is registered, never inferred from whichever direction reduces slopes)

The archive evaluation's registered residual convention
(checkpoint column `residual_sign_convention`):

    r_v[k] = v_ref_oracle[k] - (v_latch_true[k] + feed_forward[k])

The mechanism-2 counterfactual ADDS the model-predicted legacy
contribution to the MODELED side, on legacy-owned support only:

    r_v_corrected[k] = v_ref_oracle[k]
                       - (v_latch_true[k] + feed_forward[k]
                          + v_hat[k])

    correction_term[k] = v_hat[k]   on legacy-owned support
    correction_term[k] = 0.0        on TERM-owned support
                                    (the structural no-op —
                                     EXACTLY zero, not small)

SIGN: v_hat carries the world-up positive-up sign of the
transformed reference — a legacy down-command (negative world-up)
makes v_hat negative and moves the corrected residual UP relative
to r_v. TIMESTAMP: v_hat enters at the same exposure-aligned
prior-tick timestamp the feed-forward term uses — no future
leakage. Mixed-owner intervals are split BEFORE this equation is
applied (criterion, ownership gating). No generator may flip this
sign, and a generator observing that the opposite sign "works
better" has found evidence AGAINST the mechanism, not a knob.

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
change to Section 1-3b after REG-2 voids the registration and
restarts it.

## 5. GENERATOR STARTUP CONTRACT (channel-2 on R64 §5 — executable, in this order)

    1. Resolve the exact required REG-2 commit.
    2. Prove REG-2 is an ancestor of the generator commit.
    3. Parse the NUMERIC BLOCK.
    4. FAIL if any field is pending.
    5. Verify the calibration artifact digest and row-key binding.
    6. Only then read or transform the 23-approach checkpoint.
    7. Only then create result directories or residual fields.

A fail-fast NO-GO packet may be generated before step 6. A
partially run intervention, driver decomposition, or result-shaped
directory may NOT exist pre-REG-2 — pre-REG-2 numeric output is
VOID / diagnostic history only (the fb1584f-round lesson: the
sequencing rule must be enforced at PROCESS ENTRY, not by later
cleanup).
