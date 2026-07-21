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
- **MEASURED RESPONSE (v2 — registered IN ADVANCE, replacing the
  v1 checkpoint-column reference that was ABSENT on calibration
  support):** the registered source is the EXACT reconstruction
  procedure, identical to the runtime FULL_RATE_ANCHOR
  computation: for each certified-FULL exposure at feature_ts_ns,
  v_full_raw = -Theil-Sen slope of e_meas over the certified-FULL
  samples in the prior 0.50 s, subject to the runtime minimums
  (>= 4 samples, >= 0.15 s span); rows failing the minimums are
  ABSENT_RESPONSE (typed), never zero-filled. VALIDATION, both
  legs mandatory: (a) fixture (m) — one synthetic series through
  the runtime code path and the reconstruction, exact equality
  asserted by execution; (b) SAME-ROW validation on every row
  where the checkpoint column and the reconstruction both exist
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
- **OBJECTIVE**: sum of squared (v_meas[k] - v_hat[k]) over valid
  rows of qualifying windows, equal weight per row; window count
  and per-window rows published. Alignment/dedup rules unchanged
  from v1 (accepted): feature_ts_ns to tick grid, nearest tick,
  max one-tick mismatch listed; duplicate frame broadcasts dedup
  to first.
- **NULL-MODEL SCORE**: the g = 0 row is in the domain; every
  calibration publishes it explicitly beside the winner.

## 2c. Identifiability gating (v2 — a lookup minimum is not an identified model)

Per candidate, per qualifying-window set:

- L is ELIGIBLE only if valid rows beyond L * dt number >= 8.
- tau is ELIGIBLE only if the observed excited post-step horizon
  >= tau (at least one time constant observed).
- Ineligible candidates are typed UNIDENTIFIABLE, listed, and
  EXCLUDED from the argmin — a tie-break may never select them.
- If the argmin over eligible candidates lies on an OPEN face of
  the eligible domain (any face whose beyond-side is excluded by
  eligibility or by the domain edge, except g = 0 which is now
  interior-includable), calibration_status = NOT_IDENTIFIED.
- An argmin AT g = 0 exactly is a RESULT: NULL_CALIBRATED — the
  identified legacy contribution is zero; it feeds the mechanism
  table honestly (a mechanism whose modeled contribution is null
  predicts no resolution — the table's R = 0 branch will say so).
- calibration_status in {UNCALIBRATABLE, NOT_IDENTIFIED} =>
  NO ADJUDICATIVE REG-2. The prior-tick/zero-lag fallback remains
  DIAGNOSTIC ONLY and can never fill REG-2 or support the judge.

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
