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
  **SCORING_SUPPORT_SHA256 (v2.4; EXACT BYTE CONTRACT v2.5 — a
  digest whose input bytes are unregistered is not reproducible):**
  every candidate row also publishes scoring_support_sha256.

      SCORING KEY (fixed types, one per objective row):
          (window_id: str, flight_id: str, feature_ts_ns: int,
           assigned_control_tick: int)
      No scoring key may repeat after canonical normalization
      (duplicate_scoring_key_count == 0, published).
      SERIALIZATION: one canonical JSON array per key, exactly
      ["window_id","flight_id",feature_ts_ns,assigned_control_tick]
      in that fixed order; UTF-8; no optional whitespace; decimal
      integers only; records sorted lexicographically by the
      typed tuple; one LF after EVERY record including the final.
      scoring_support_sha256 = SHA-256 of that byte stream.

  The support ledger is constructed ONCE, before candidate
  iteration; candidate rows REFERENCE its count and digest and
  never independently reconstruct the support. Identical across
  all candidates; runtime-asserted alongside the count; mismatch
  in EITHER field is a hard STOP. The artifact publishes:
  support_ledger_path, support_ledger_sha256, rows_scored_common,
  scoring_support_sha256, duplicate_scoring_key_count = 0 — and
  ONE support ledger: window_id, event key, feature_ts_ns,
  assigned_control_tick, relative_tick, response-validity state,
  trace-validity state, included_in_objective, exclusion reason.
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
  NOT_IDENTIFIED. **LOCAL-FACE RULE (v2.3, channel-2 on R69-73
  §7.9; SCOPE FIXED v2.4, channel-2 on R74-75 §4): openness is
  decided at the WINNING CELL by inspecting its six outward
  neighbors with the other coordinates held fixed —
  (g +/- step, tau, L), (g, tau +/- step, L), (g, tau, L +/- 1)
  — a face is OPEN when that specific neighbor is outside the
  domain or ineligible. Global eligibility sets may not stand in.
  THE LOCAL-FACE CHECK APPLIES TO POSITIVE-g WINNERS ONLY.**
- **NULL MANIFOLD, COLLAPSED (v2.4 — resolving the g = 0
  contradiction: a literal face check would call every null
  winner open at the physically excluded negative-g boundary and
  expose nuisance tau/L edges):** all g = 0 cells are ONE typed
  prediction-equivalent candidate class — tau and L are
  non-operative nuisance coordinates there, with no effect on the
  predicted contribution. The null class's status is decided ONLY
  by the common-support loss ordering against every eligible
  g > 0 candidate (tolerance rule below, no positive-g global
  minimizer). The negative-g direction is not an empirical open
  face; nuisance-coordinate boundaries never control status; a
  null representative row is a display convention, not a cell
  with faces. PRECEDENCE: a result is never simultaneously
  NULL_CALIBRATED and NOT_IDENTIFIED — the null class takes the
  loss-ordering path, positive-g winners take the local-face
  path, exclusively.
- **POSITIVE-G MULTIPLE-MINIMIZER RULE (v2.3, §7.10 — first-wins
  is reproducibility, never identification):** the artifact
  publishes global_minimizer_count, every global-minimizer
  coordinate (ties within NULL_TIE_REL_TOL), and a
  prediction-equivalence status. Distinct positive-g minimizers
  => NOT_IDENTIFIED, unless a PRE-REGISTERED equivalence-class
  rule proves their intervention contribution identical on every
  applicable support. (The positive-g counterpart of the null-tie
  rule.)
- **NULL_CALIBRATED (v2.2 — never from one first-winning cell,
  channel-2 Blocker 2; at g = 0 tau and L are nuisance parameters
  and the prediction is identically zero, so on the common
  support all g = 0 cells share ONE loss, the null loss):**
  NULL_CALIBRATED requires ALL of:
  1. every compared candidate scored on the registered common
     support;
  2. null loss strictly better than EVERY g > 0 eligible
     candidate's loss beyond the registered tolerance;
  3. no g > 0 candidate attains the global minimum.
  **EXACT COMPARISON SEMANTICS (v2.5, channel-2 order F — never
  left to source code):** losses are float64 SSE on the common
  support. gap = best_positive_sse - null_sse. TIE iff
  gap <= NULL_TIE_REL_TOL * max(best_positive_sse, null_sse,
  SSE_ABS_FLOOR), with NULL_TIE_REL_TOL = 1e-9 and
  SSE_ABS_FLOOR = 1e-18 (the floor decides the both-exactly-zero
  case: 0.0 vs 0.0 is a TIE, hence NOT_IDENTIFIED — a dataset on
  which every model is perfect identifies nothing). NULL wins iff
  gap > that bound. The packet publishes null_loss,
  best_positive_loss, the gap, and the tie-rule verdict.
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

## 2d. Command-direction applicability (v2.3 — primary direction FROZEN)

**PRIMARY FIT DIRECTION = DOWN** (v2.3, channel-2 on R69-73 §7.8:
an evidence-sensitive CLI default is not a registration). Frozen
here, pre-evidence, with pre-existing provenance: the calibration
source has been registered as "the A091 DOWN-STEP episode" since
the first Contract B registration. The real-run generator REFUSES
to run without an explicit direction argument equal to the
registered primary; a permissive default is a startup-contract
violation. Calibration fitted on one direction registers the
model for THAT direction. Intervention rows whose reference
dynamics are dominated by the unvalidated direction are typed
OFF_SUPPORT_DIRECTION unless a same-procedure validation window
in that direction passes. Both directions' windows are always
DETECTED and listed, whether or not fitted.

## 2f. Real-run input and identity contracts (v2.3 — channel-2 on R69-73 §7, registered so the source repairs are ancestry-enforceable)

1. **CANONICAL FEATURE-TIME ALIGNMENT (§7.4; CAUSAL-FLOOR
   ALGORITHM v2.5 — the v2.4 text was internally contradictory:
   nearest-tick can assign a FUTURE control tick whenever the
   exposure falls past the midpoint, while the same sentence
   promised never-later; ledger entry R78):** feature_ts_ns is
   canonical for certified exposures; a missing exposure time is
   ABSENT (typed) and may NEVER be synthesized from control time
   or tick index. THE RULE IS THE CAUSAL FLOOR:

       assigned_control_tick = the LATEST registered control tick
                               whose timestamp <= feature_ts_ns
       signed_mismatch_ns    = feature_ts_ns
                               - assigned_control_tick_time_ns
       required: 0 <= signed_mismatch_ns <= one control period
       no prior control tick          -> OFF_WINDOW (typed)
       mismatch > one control period  -> OFF_WINDOW (typed)

   No future control value can leak into an exposure-aligned row,
   and no equidistant special case exists. The fitted row is
   labeled by the assigned CONTROL tick; the exposure time is
   preserved in the ledger; signed mismatch published per row.
   The mismatch LEDGER is mandatory.
2. **STRICT CERTIFICATION PARSING (§7.3):** CSV values are text.
   Accepted TRUE set: {"True", "true", "1"}; accepted FALSE set:
   {"False", "false", "0"}; missing/blank/unknown ->
   ABSENT_CERTIFICATION, fail closed, never default-True.
   Truthiness on a nonempty string is the outlawed pattern.
3. **CANONICAL FIRST-EXPOSURE DEDUP (§7.5; RUNTIME-ALIGNED
   IDENTITY v2.5 — the v2.4 three-component key was registered as
   "exact" without checking the runtime, whose exposure identity
   IS the feature timestamp (the oracle dedups by ts; robust_slope
   rejects duplicate timestamps); ledger entry R78):**

       PRIMARY EXPOSURE ID:  (flight_id, feature_ts_ns)
       CONSISTENCY METADATA: frame_id (never part of identity
                             until a runtime-equivalence fixture
                             proves rebroadcasts preserve it and
                             no runtime path splits on it)

   Collision policy, WHOLE-CLASS semantics (an identity
   contradiction is never cured by trusting whichever row came
   first): exact duplicate (same primary ID, identical relevant
   payload) -> FIRST canonical file-order occurrence retained,
   discards listed; same primary ID with INCONSISTENT payload ->
   the ENTIRE conflict class excluded and listed
   (EXPOSURE_PAYLOAD_CONFLICT); same frame_id across different
   feature timestamps -> typed FRAME_ID_COLLISION, entire class
   excluded unless runtime semantics prove frame reuse
   legitimate; any missing ID component -> ABSENT_EXPOSURE_KEY,
   excluded and listed. ONE normalization step applies this
   BEFORE the detector and the response reconstruction; first
   wins in EVERY path only for byte-identical duplicates; every
   discard listed. A dict keyed by tick that keeps the last row
   is the outlawed pattern.
4. **SENTINEL-KEY BINDING (§7.2; STAGED SCHEMA v2.5 — the v2.4
   schema demanded calibration-derived counts as CLI inputs
   before detection, inviting the caller to supply the answer
   the generator must compute; ledger entry R78):**

   STARTUP-BOUND INPUTS (CLI-required, verified before any
   window detection):
       sentinel_artifact_path, sentinel_artifact_sha256,
       sentinel_criterion_commit, sentinel_evidence_commit,
       sentinel_reviewed_tip, sentinel_key_schema.
   The generator then READS the committed sentinel artifact and
   derives sentinel_key_count and sentinel_keys.

   POST-DETECTION DERIVED OUTPUTS (computed, never accepted):
       calibration_key_schema, calibration_key_count,
       calibration_keys, intersection_count, intersection_keys.

   PRE-FIT EQUATIONS, all mandatory:
       sentinel_criterion_commit <= sentinel_evidence_commit
           <= sentinel_reviewed_tip <= execution_tip  (ancestry);
       digest(sentinel_evidence_commit:path) ==
       digest(sentinel_reviewed_tip:path) ==
       digest(execution_tip:path) == sentinel_artifact_sha256
           (the artifact survives unchanged at all three);
       sentinel_key_schema == calibration_key_schema ==
       the registered canonical key schema (two incomparable
       encodings can produce a trivially empty intersection);
       intersection_count == 0.
   Missing fields, an unresolvable commit, or a schema mismatch
   are STARTUP/PRE-FIT failures.
5. **TYPED TRACE VALIDATION (§7.6):** transport completeness is
   about VALUES, not keys — every trace field non-empty and from
   its registered value set; a present key with a blank or
   untyped value is an INCOMPLETE row.
6. **ZERO/NONE IN METADATA (§7.7):** absent references serialize
   as None/empty plus a typed reason, NEVER as 0.0 — including in
   EXCLUDED-window metadata; false provenance is still falsity.
7. **PACKET SCOPE ENUM (§7.11):** the ambiguous diagnostic_only
   boolean is replaced by a typed scope: SYNTHETIC_DIAGNOSTIC /
   REG2_CALIBRATION_CANDIDATE / VOID. A calibration candidate
   moves no board by itself, but it is not a synthetic dry run.
8. **IDENTITY CHAIN (§7.1; EXACT HASH v2.4; SELF-REFERENCE
   RESOLVED v2.5, channel-2 §8):** a criterion cannot contain its
   own not-yet-created hash; the lawful meaning is that the NEXT
   SOURCE COMMIT hard-binds the full 40-hex hash of its COMPLETE
   governing criterion ancestor — the final amendment commit,
   whichever it is when the source lands (after this v2.5 round:
   the commit introducing this text, superseding 3fe25ea as
   governing). The packet proves GOVERNING_REG1_COMMIT <=
   source_generator_commit <= execution_tip <= artifact_commit,
   where source_generator_commit is the ACTUAL last commit
   supplying the executed source bytes (discovered from git
   history of the source path) — never HEAD copied into both
   fields — and additionally publishes
   source_generator_sha256_at_source_commit ==
   source_generator_sha256_at_execution_tip (the executed bytes
   are the registered bytes).
9. **REQUIRED SOURCE FIXTURES (consolidated roster; the prior
   green suites remain valid history and do NOT satisfy this):**
   (iv) 3 unique timestamps -> both legs ABSENT, never 0.0;
   (v) 4 unique timestamps spanning < 0.15 s -> equal VALUES;
   (s1) post-lag horizon < tau -> UNIDENTIFIABLE/HORIZON_LT_TAU;
   (s2) candidate-censoring picks wrong lag, common support picks
   right; (s3) positive-g null tie -> NOT_IDENTIFIED;
   (s4) certified_full = "False"/"0"/blank/invalid -> none enters
   history; (s5) poisoned duplicate -> first wins in every path;
   (s6) exposure/control tick separation -> registered alignment
   + mismatch ledger; (s7) trace keys present, one value blank ->
   incomplete; (s8) sentinel overlap through the ACTUAL CLI ->
   window rejected; (s9) missing/mismatched direction argument ->
   startup refusal; (s10) locally-open face hidden by global
   eligibility -> NOT_IDENTIFIED; (s11) multiple distinct
   positive-g global minimizers -> NOT_IDENTIFIED; (s12)
   source_generator_commit != execution_tip -> both identities
   reported correctly; **(v2.4 additions, channel-2 on R74-75:)**
   (s13) same rows_scored_common but different support digest ->
   STOP; (s14) g = 0 null winner at a domain boundary -> status
   decided by loss ordering, never killed by negative-g or
   nuisance faces; (s15) missing feature_ts_ns -> typed absence,
   never synthesized; (s16) SUPERSEDED by the v2.5 causal floor
   (no equidistant case exists under it; retained as history);
   (s17) sentinel bytes altered at execution tip -> startup
   refusal; **(v2.5 additions, channel-2 on R76:)** (s18)
   exposure at 0.75 periods after the earlier tick -> the CAUSAL
   FLOOR selects the earlier tick, never the nearer future one;
   (s19) sentinel and calibration key schemas differ -> hard
   refusal; (s20) NULL_CALIBRATED serialization ->
   tau/L/profile NOT_APPLICABLE with the five null fields
   present; (s21) same support in different input order ->
   identical canonical digest; (s22) one substituted key at
   equal cardinality -> different digest and STOP; (s23)
   conflicting exposure-identity group -> the registered
   WHOLE-GROUP disposition, never first-row trust.

## 2g. PRIOR-VIEWING DISCLOSURE (v2.4 — this round is PRE-ADJUDICATIVE, not PRE-OBSERVATION)

A calibration-shaped A091 packet was generated and committed
BEFORE v2.3 landed (b421039, attested 044153b, removed from the
tree at 2fa8e9d). Its committed summary — read from history, not
from its removal label — reports calibration_status
NULL_CALIBRATED, g = 0.0, tau = 0.02, L = 0, RMS = 0.0, 51
scoring rows, fit directions DOWN AND UP, diagnostic_only, no
REG-2 written. Disposition: **VOID_PRE_V2.3, non-adjudicative
history, no REG-2 effect, no mechanism effect, no admissible
residual — AND THE RESULT WAS VIEWED.** Every subsequent
calibration packet MUST disclose: prior_viewed_output = the
044153b diagnostic NULL_CALIBRATED packet with the numbers above;
why it is void (generator predates v2.3; UP direction included;
real-run contracts incomplete; provenance rules incomplete); and
that its effect on current status is none. The next A091 read is
a repaired-instrument read, never an untouched confirmation, and
no description may claim otherwise.

**MACHINE-BOUND DISCLOSURE FIELDS (v2.5, channel-2 order G — the
packet checker FAILS a real calibration candidate lacking this
block):** prior_viewed_artifact_path, prior_viewed_artifact_sha256,
prior_viewed_evidence_commit_full (b421039...),
prior_viewed_attestation_commit_full (044153b...),
prior_viewed_removal_commit_full (2fa8e9d...),
prior_calibration_status = NULL_CALIBRATED, prior_g = 0.0,
prior_tau = 0.02, prior_L = 0, prior_rms = 0.0,
prior_scoring_rows = 51, prior_fit_directions = [DOWN, UP],
prior_disposition = VOID_PRE_V2.3, prior_board_effect = NONE.
Full 40-hex hashes in the packet, never abbreviated labels.

**OUTCOME-SYMMETRY CHECK (channel-1 on R76, standing rule of the
program):** every POST-OBSERVATIONAL amendment must be justified
WITHOUT reference to the status it benefits, and both-channel
walks include this check explicitly. This 2g disclosure is what
makes the check auditable: the walker knows what was seen, so the
walker can ask whether each repair would have been equally
ordered had the opposite status been seen. The honest-repair
signature, recorded: post-viewing repairs should tend to RAISE
the bar for exactly the observed status — as this round's do
(the observed NULL must now beat every positive gain beyond
tolerance on identical support; the direction freeze restores a
registered intent whose breach produced the UP rows).

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

## 4. NUMERIC BLOCK (REG-2 v2 — EMPTY by construction; BRANCH-TYPED v2.5, channel-2 order A: a NULL result has no identified tau/L and no three-dimensional profile box — serializing a first-listed nuisance coordinate would revive exactly what the collapsed null class prohibits)

    calibration_status = PENDING (must be CALIBRATED or
                         NULL_CALIBRATED; UNCALIBRATABLE /
                         NOT_IDENTIFIED cannot fill this block)
    model_class        = PENDING (POSITIVE_GAIN | NULL_CONTRIBUTION)

    IF model_class = POSITIVE_GAIN (calibration_status CALIBRATED):
        g           = required, > 0
        tau         = required
        L           = required
        profile_box = required, locally closed on every face
        residual_rms_at_optimum = required
        null_model_rms          = required (always published)

    IF model_class = NULL_CONTRIBUTION (status NULL_CALIBRATED):
        g           = 0.0
        tau         = NOT_APPLICABLE (never a number)
        L           = NOT_APPLICABLE (never a number)
        profile_box = NOT_APPLICABLE_NULL_CLASS
        required instead:
            null_loss
            best_positive_loss
            null_to_positive_loss_gap
            positive_global_minimizer_count
            null_tie_rule_result
        (a representative null grid row may appear in the
         candidate TABLE; it is never serialized here as
         calibrated physical tau/L numerics)

    COMMON to both branches:
    calibration_artifact_path   = PENDING
    calibration_artifact_sha256 = PENDING (committed bytes)
    calibration_interval_keys   = PENDING (disjoint from sentinel)
    row_level_owner_trace       = PENDING (per fitted row)
    source_generator_commit     = PENDING (actual source-bytes
                                  commit, with
                                  source_generator_sha256 at both
                                  the source commit and the
                                  execution tip)
    prior_viewing_block         = PENDING (2g machine fields)

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
