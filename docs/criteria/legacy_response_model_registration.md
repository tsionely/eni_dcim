# MODEL REGISTRATION v2 — Contract B closed-loop response model (RESTARTED under channel-2 on RESPONSE-66)

This registration RESTARTED: REG-2(v1) is
**VOID_INVALID_CALIBRATION_INPUT** (see VOID HISTORY below). The
restart is the lawful route both channels named — channel-1's
pre-committed contingency and channel-2's explicit order converge
on it. The restart rationale is independent of the 23 archive
approaches: it arises entirely from the v1 calibration's own
support and objective (all-zero response target, excluded null
model, double open boundary, contaminated window, erased
transient). REG-2(v2) may fill numerics only from a calibration
that is IDENTIFIED under the rules below.

## 1. Model equation (form, unchanged — accepted by both channels)

    v_hat[k+1] = v_hat[k] + (dt / tau) * (g * v_ref[k - L] - v_hat[k])

dt = 0.02 s. Parameters g (gain), tau (s), L (integer ticks). No
additional terms; inadequacy is published as calibration residual,
never absorbed by post-hoc structure.

**PARAMETER DOMAIN v2 (restart-registered; rationale = the v1
non-identification, cited, not the 23):**

    g   : 0.00, 0.05, ..., 1.50   (step 0.05, 31 values — the NULL
                                   RESPONSE g = 0 is now INSIDE the
                                   domain; its score is published in
                                   every calibration)
    tau : 0.02, 0.04, ..., 1.20 s (step 0.02, 60 values — extension
                                   past v1's 0.60 cap cites v1's
                                   tau-at-boundary symptom)
    L   : 0, 1, ..., 25 ticks

Iteration order L-outer/tau/g-inner ascending; IEEE-754 float64
strict less-than; FIRST-wins tie-break; all candidate scores
published. Candidates are ELIGIBILITY-GATED per Section 2c —
UNIDENTIFIABLE candidates never enter the argmin.

## 2. Calibration source and detector (v2)

- **Source**: the A091 physical episode (20260719T201851),
  command-step intervals selected by the deterministic detector.
  Calibration intervals DISJOINT from the A091 sentinel interval.
- **MEASURED RESPONSE (v2.1 — registered from the CODE, not from
  the v1 artifact's description; amended pre-calibration, REG-2(v2)
  still empty):** the registered source is the EXACT runtime
  algorithm of rate_anchor_v_raw
  (src/aigp/planning/vertical_owner.py, _slope_of), which is NOT
  a fixed-window fit: for each certified-FULL exposure at
  feature_ts_ns,
  1. FRESH TAIL: walk back from the newest sample while
     consecutive gaps stay within the oracle's max_gap_s (0.12 s
     default) — a slope is never fitted across an outage;
  2. LAST-12 CAP: at most the final 12 fresh-tail samples enter;
  3. robust_slope (vertical_terminal.py): Theil-Sen over
     UNIQUE-timestamp samples, duplicates rejected, >= 4 unique
     points required;
  4. v_full_raw = -slope.
  **EXACT-_slope_of CONTRACT (v2.2, channel-2 Blocker 3 —
  resolving the span-gate mismatch by choosing exactness): the
  reconstruction contains NO condition _slope_of does not. The
  0.15 s span gate some implementations added is REMOVED from the
  reconstructed quantity — _slope_of has no span condition; the
  only absence rule is robust_slope's own >= 4 unique timestamps
  (plus fresh-tail truncation). The oracle's min_span_s maturity
  predicate is a SEPARATE readiness concept, not part of the rate
  value, and may not be smuggled into it. Battery member (v),
  required: a series with 4 unique timestamps spanning LESS than
  0.15 s — BOTH legs produce equal VALUES (not ABSENT), asserting
  by execution that no extra gate exists. It cannot be called the
  exact _slope_of algorithm and silently contain a condition
  _slope_of does not.**
  Rows failing the minimums are ABSENT_RESPONSE (typed), never
  zero-filled. **The v1 description ("prior 0.50 s window") was
  NOT the runtime computation — the registration author copied the
  artifact's summary instead of the code; entered in the ledger
  (RESPONSE-69). The reconstruction implementation must import
  robust_slope from the flight code and replicate
  _fresh_tail/_slope_of exactly — never re-derive them.**
  VALIDATION, both legs mandatory: (a) fixture (m) — leg 1 drives
  the REAL oracle class from src/aigp (feed the synthetic
  certified-FULL series through observe(), force the
  FULL->SIDE downgrade latch, read oracle.rate_anchor_v_raw); leg
  2 is the reconstruction; EXACT equality asserted by execution
  over a FOUR-member battery: (i) a DENSE series (> 12 samples in
  0.5 s — exposes any fixed-window impostor), (ii) a GAPPED
  series (exposes fresh-tail violations), (iii) duplicate
  timestamps including a poisoned rebroadcast, and (iv)
  BELOW-MINIMUM SUPPORT (channel-1 on R69, registered before the
  v2.1 calibration run: a series with only 3 unique timestamps —
  BOTH legs must emit ABSENT/None or a typed absence error, NEVER
  0.0, asserted by execution; this welds the fixture to the
  zero/None law at exactly the edge where sparse support could
  mint false zeros — the R68 §3 candidate explanation). A fixture
  whose two legs share an implementation is VOID — equality of a
  function with itself proves nothing; the comparison spec
  declares the INDEPENDENCE BOUNDARY of its legs (channel-1's
  checklist item, adopted): leg 1 imports only from src/aigp's
  shipped classes, leg 2 may share nothing with leg 1 above
  robust_slope itself. (b) SAME-ROW validation on every row where
  the checkpoint column and the reconstruction both exist
  anywhere in the archive — equality within 1e-9 published;
  disagreement is a STOP, not a footnote.
- **STEP DETECTOR v2** (deterministic, fit-blind; the v1 floor's
  units error is corrected):
  1. STEP EVENT at tick k if |v_ref[k] - v_ref[k-1]| >= 0.35 m/s —
     the registered COMMAND-DOMAIN constant
     planner.commit.vz_cap_mps (config, m/s — correct units; the
     v1 floor borrowed the 0.30 m admission corridor, a LENGTH).
     Down-steps and up-steps are both DETECTED; calibration FIT
     uses the registered direction(s) per Section 2d. Consecutive
     qualifying ticks merge to the first.
  2. PRE-WINDOW: 10 ticks before k with |v_ref[i] - v_ref[k-1]| <
     0.05 m/s (the registered near-zero RATE constant — correct
     units).
  3. POST-WINDOW: from k to the FIRST material reference
     transition IN ANY DIRECTION (|v_ref[i] - v_ref_post_level| >=
     0.05 m/s), capped at 50 ticks (1.0 s; horizon extension cites
     v1's horizon-shorter-than-candidates defect). The v1 defect —
     truncating only at the next DOWN-step, letting an up-command
     contaminate the window — is closed by the any-direction rule.
  4. EXCLUSIONS (typed, listed): ABSENT_INPUT, SENTINEL_DISJOINT,
     INSUFFICIENT_ROWS (< 8 valid rows).
  5. PRE-EVENT INITIAL STATE (v1 defect closed — the v1 rule
     initialized at the post-step zero and ERASED the transient):
     v_hat at event entry = g * (mean v_ref over the 10-tick
     pre-window), propagated through the event across the window.
     No burn-in inside calibration windows — the transient IS the
     signal. (The intervention's burn-in rule, Section 3, is
     unchanged.)
- **OBJECTIVE — ONE COMMON ROW SET (v2.2, channel-2 on R67-68
  Blocker 1: raw SSE across candidate-dependent row sets is
  INADMISSIBLE — a larger L could win merely by summing fewer
  residuals):** every candidate is scored on the SAME support —
  all valid rows of every qualifying window. Pre-lag rows are
  PREDICTED, never discarded: for relative_tick < L the model
  prediction uses the registered pre-event reference (as the
  predict path already defines). Loss = sum of squared
  (v_meas[k] - v_hat[k]) over that common set, equal weight per
  row; window count and per-window rows published.
  **ROWS_SCORED_COMMON COLUMN (channel-1 on R73, binding): every
  candidate-score row publishes rows_scored_common, and the value
  is IDENTICAL across all candidates in one artifact — the
  common-support invariant made eyeball-visible, a second
  tripwire above fixture s2. The generator ASSERTS the equality
  at run time; a mismatch is a STOP, and an artifact whose
  candidate rows disagree on it is malformed on its face.**
  Alignment/dedup rules unchanged from v1 (accepted):
  feature_ts_ns to tick grid, nearest tick, max one-tick mismatch
  listed; duplicate frame broadcasts dedup to first.
- **NULL-MODEL SCORE**: the g = 0 row is in the domain; every
  calibration publishes it explicitly beside the winner.

## 2c. Identifiability gating (v2 — a lookup minimum is not an identified model)

Per candidate, per qualifying-window set (v2.2 — the horizon is
measured AFTER the lag, channel-2 Blocker 1.2):

- L is ELIGIBLE only if valid rows with relative_tick >= L number
  >= 8 (identifiability is post-lag support; scoring support is
  the common set above — the two are DIFFERENT sets and never
  conflated).
- tau is ELIGIBLE only if the POST-LAG excited horizon
  max((relative_tick - L) * dt) >= tau — time observed after the
  candidate's own lag, never from the event (a 50-tick window
  with L = 25 observes 0.48 s, not 0.98 s).
- Ineligible candidates are typed UNIDENTIFIABLE, listed with the
  failing rule, and EXCLUDED from the argmin — a tie-break may
  never select them.
- If the argmin over eligible candidates lies on an OPEN face of
  the eligible domain (any face whose beyond-side is excluded by
  eligibility or by the domain edge), calibration_status =
  NOT_IDENTIFIED.
- **NULL_CALIBRATED (v2.2 — never from one first-winning cell,
  channel-2 Blocker 2; at g = 0 tau and L are nuisance parameters
  and the prediction is identically zero, so on the common
  support all g = 0 cells share ONE loss, the null loss):**
  NULL_CALIBRATED requires ALL of:
  1. every compared candidate scored on the registered common
     support;
  2. null loss strictly better than EVERY g > 0 eligible
     candidate's loss beyond the registered tolerance
     NULL_TIE_REL_TOL = 1e-9 (relative to the larger loss);
  3. no g > 0 candidate attains the global minimum.
  A g > 0 candidate tying the null within tolerance, or beating
  it, removes NULL_CALIBRATED: the status is then decided by the
  positive-gain winner's own closed-face check (CALIBRATED or
  NOT_IDENTIFIED). g = 0 receives NO exemption from this
  comparison — the gain direction toward positive contribution
  must be genuinely closed by the loss ordering, not by walking
  order.
- calibration_status in {UNCALIBRATABLE, NOT_IDENTIFIED} =>
  NO ADJUDICATIVE REG-2. The prior-tick/zero-lag fallback remains
  DIAGNOSTIC ONLY and can never fill REG-2 or support the judge.
- **REQUIRED SOURCE FIXTURES for this section (executed before
  the A091 run):** (s1) a large-lag candidate with >= 8 post-lag
  rows but post-lag horizon < tau -> UNIDENTIFIABLE with
  HORIZON_LT_TAU on the corrected measure; (s2) a synthetic case
  where candidate-specific row censoring would select the WRONG
  lag while common-support scoring selects the right one —
  asserting the objective contract bites; (s3) a null tie: a
  g > 0 candidate equal to the null within tolerance ->
  NOT_IDENTIFIED, never NULL_CALIBRATED.

## 2d. Command-direction applicability (v2)

Calibration fitted on one direction registers the model for THAT
direction. Intervention rows whose reference dynamics are
dominated by the unvalidated direction are typed
OFF_SUPPORT_DIRECTION unless a same-procedure validation window in
that direction passes. Both directions' windows are always
DETECTED and listed, whether or not fitted.

## 2e. Provenance bindings (v2 — the generator-identity gap closed)

The calibration generator SOURCE FILE is committed AFTER this
registration and BEFORE the evidence it creates. The packet binds:
source_generator_path, source_generator_commit, execution_tip,
artifact_commit, REG-1 commit, input paths + digests, exact
command line. The packet's own artifact_manifest digests are
computed on COMMITTED bytes at the pushed tip (publish-then-attest
child), closing the v1 stale-self-manifest defect. Row-level
owner/actuation trace REQUIRED per fitted row: planner phase, TERM
owner state, arbiter-selected vertical source, adapter input,
post-limit command, clip status — transport is proven per ROW,
never by one event-tick label.

## 3. Declared handling rules (unchanged from v1 — accepted)

Initial state for the INTERVENTION stream (not calibration
windows): steady-state start with burn-in max(3 * tau, L * dt)
excluded as BURN_IN. Saturation clipped to the era cap, events
listed, majority-clipped cuts flagged and excluded from counts.
None/absent -> OFF_SUPPORT typed rows; 0.0 is a value. Era
transport per the ledger with typed per-era rows; eras without
rows OFF_SUPPORT. Sign/frame fixture must fail loudly on either
factor flipped.

## 3b. Corrected-residual equation (unchanged from v1 — accepted)

    r_v[k]           = v_ref_oracle[k] - (v_latch_true[k] + feed_forward[k])
    r_v_corrected[k] = v_ref_oracle[k] - (v_latch_true[k] + feed_forward[k] + v_hat[k])

    correction_term[k] = v_hat[k] on legacy-owned support
    correction_term[k] = 0.0     on TERM-owned support (EXACTLY)

Sign registered (world-up positive-up); v_hat enters at the
exposure-aligned prior tick; mixed-owner intervals split first; a
generator finding the opposite sign "works better" has found
evidence AGAINST the mechanism, not a knob.

## 4. NUMERIC BLOCK (REG-2 v2 — EMPTY by construction)

    g    = PENDING_CALIBRATION
    tau  = PENDING_CALIBRATION
    L    = PENDING_CALIBRATION
    calibration_status          = PENDING (must be CALIBRATED or
                                  NULL_CALIBRATED; UNCALIBRATABLE /
                                  NOT_IDENTIFIED cannot fill this
                                  block)
    calibration_artifact_path   = PENDING
    calibration_artifact_sha256 = PENDING (committed bytes)
    calibration_interval_keys   = PENDING (disjoint from sentinel)
    residual_rms_at_optimum     = PENDING
    null_model_rms              = PENDING (always published)
    profile_box                 = PENDING (closed on every face, or
                                  the status is NOT_IDENTIFIED)
    row_level_owner_trace       = PENDING (per fitted row)
    source_generator_commit     = PENDING

Any change to Sections 1-3b after REG-2(v2) voids and restarts
again.

## 5. GENERATOR STARTUP CONTRACT (v2 — step 3a added)

    1.  Resolve the exact required REG-2 commit.
    2.  Prove REG-2 is an ancestor of the generator commit.
    3.  Parse the NUMERIC BLOCK.
    3a. Parse calibration_status: refuse VOID / UNCALIBRATABLE /
        NOT_IDENTIFIED / PENDING — fail closed.
    4.  FAIL if any field is pending.
    5.  Verify the calibration artifact digest and row-key binding.
    6.  Only then read or transform the 23-approach checkpoint.
    7.  Only then create result directories or residual fields.

Fail-fast NO-GO packets only before step 6; pre-REG-2 numeric
output is VOID / diagnostic history (the fb1584f lesson stands).

## VOID HISTORY — REG-2(v1), superseded IN TYPE

    status  = VOID_INVALID_CALIBRATION_INPUT (channel-2 on R66)
    reasons = REGISTERED_RESPONSE_FIELD_ABSENT;
              POST_HOC_RESPONSE_RECONSTRUCTION;
              ZERO_RESPONSE_UNIDENTIFIED_MODEL (13/13 fitted
              response rows exactly 0.0; SSE == sum(v_hat^2); the
              excluded null model scores 0);
              DOUBLE_OPEN_BOUNDARY (g-min/tau-max corner: nearest
              allowed point to the excluded null model);
              CONTAMINATED_SINGLE_EVENT_WINDOW (up-commands +0.746
              / +0.868 inside the down-step window; pre-step state
              erased by the v1 initialization).
    v1 numerics (g=0.50, tau=0.60, L=0, RMS 0.0102753797,
    artifact 0b60e91/edff619 round) are HISTORY, non-adjudicative
    forever; the files remain immutable in git history; the
    packet's stale self-manifest is superseded by this record and
    the artifact round that replaces it.
    mechanism verdict from v1: NONE. admissible residual: NONE.

## ANNEX A — channel dispositions (annotations in place)

**Channel-1 on RESPONSE-66:** proceed-under-labels with a
pre-committed one-time restart contingency for non-CONFIRM
verdicts; provenance RATIFIED conditional on the runtime-twin
fixture and annotation form; transport inversion approved.

**Channel-2 on RESPONSE-66:** provenance ratification REFUSED
(the registered field was a storage-bound source; its absence on
support makes the substitution post-hoc); BOUNDARY_OPTIMUM
DISQUALIFYING (the open direction contains the null-contribution
model); calibration UNIDENTIFIED on an all-zero response target;
transport inversion event-local only, row-level proof owed;
REG-2 VOID; ordered restart A-G.

**CONFLICT RESOLUTION (standing law — the conservative option
governs):** the refusal governs over the ratification; the
immediate void supersedes the proceed-with-contingency route. The
two rulings CONVERGE on the restart itself: channel-1
pre-authorized exactly the lawful restart that channel-2 orders,
and channel-1's a-fortiori-CONFIRM logic is preserved in spirit by
2c: only an IDENTIFIED (closed-box) or NULL_CALIBRATED model can
ever reach the judge, so no verdict of any kind can ride an open
boundary again — the contingency's trigger condition is now
unreachable by construction. Channel-1's two ratification
conditions (fixture (m), annotation form) are RETAINED in v2 as
mandatory validation legs — stricter, not looser, than either
ruling alone.
