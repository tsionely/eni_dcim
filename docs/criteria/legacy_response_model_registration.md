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
strict less-than for the RAW ARGMIN COMPUTATION ONLY — the
argmin is a numeric scan; STATUS and minimizer-set membership are
decided by the registered loss_equal relation, and FIRST-wins
selects nothing but the DISPLAY representative, chosen only after
the full equivalence class is published (v2.6.2); all candidate
scores published. Candidates are ELIGIBILITY-GATED per Section 2c —
UNIDENTIFIABLE candidates never enter the argmin.

## 2. Calibration source and detector (v2)

- **Source**: the A091 physical episode (20260719T201851),
  command-step intervals selected by the deterministic detector.
  Calibration intervals DISJOINT from the A091 sentinel interval.
  **SOURCE-LOG BINDING (v2.6.3, channel-2 order A6): the packet
  binds source_log_paths + source_log_sha256 per file as STARTUP
  inputs (like the sentinel binding); the registered selector is
  DETERMINISTIC and PRE-RESULT: ALL control and feature records
  of flight_id 20260719T201851-50f9dcc8 in the committed
  recording — no sub-selection, no file chosen after seeing
  contents.**
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

      SCORING KEY (fixed types, one per objective row;
      CONTROL IDENTITY v2.6.2 — assigned_control_tick was an
      undefined post-bridge field; support identity uses the
      REGISTERED control identity):
          (window_id: str, flight_id: str, feature_ts_ns: int,
           assigned_control_segment_id: int,
           assigned_control_mono_ns: int)
      A logged tick number may be PUBLISHED as a descriptor but
      never carries support identity.
      CANONICAL window_id (v2.6; SEGMENT-QUALIFIED v2.6.1 — the
      v2.6 form collided across clock resets reusing the same
      mono_ns):
          window_id = "W|" + flight_id + "|" +
                      decimal(control_segment_id) + "|" +
                      decimal(event_control_mono_ns) + "|" +
                      direction("DOWN"/"UP")
          — derived from immutable event data only; the segment
          id comes from the committed-record-order rule (2f.1),
          so reordered input can move neither resets nor IDs.
      No scoring key may repeat after canonical normalization:
      a duplicate is a HARD STOP, never a silent set conversion
      (duplicate_scoring_key_count published, must equal 0).
      SERIALIZATION (v2.6; BYTE-UNIQUE v2.6.1; ALPHABET AND
      TUPLE FIXED v2.6.2 — the v2.6.1 sentence confused slash
      with pipe, a nonsense clause inside a byte contract; ledger
      entry R83): the actual field VALUES as a JSON array
      [window_id, flight_id, feature_ts_ns,
      assigned_control_segment_id, assigned_control_mono_ns].
      STRING ALPHABET, the clean rule: permitted characters are
      EXACTLY A-Z, a-z, 0-9, underscore, hyphen, pipe (0x7C),
      period, colon, plus — nothing else: no quote, no
      backslash, no slash, no space; any other character ->
      ledger-construction refusal. NO escape sequences exist by
      construction; a serializer emitting any backslash fails.
      Integers decimal only — no floats, no null, no NaN, no
      string coercion; UTF-8 (pure ASCII by the alphabet rule);
      separators ("," and ":") with no optional whitespace;
      records sorted by the TYPED tuple (string, string, int,
      int, int) with string order = ASCII BYTE order; exactly
      one LF after EVERY record including the final.
      scoring_support_sha256 = SHA-256 of that byte stream.
      key_encoder_id = REG1_KEY_ENCODER_V1, carried in the
      packet. **THIS BLOCK is the
      registered KEY-SERIALIZATION CONTRACT — the sentinel
      keyset uses THIS encoder verbatim on [flight_id,
      feature_ts_ns] (the earlier "2f.9 value rules"
      cross-reference pointed at the fixture roster and is
      corrected here); sentinel_keyset_sha256 and
      calibration_keyset_sha256 are computed with it and
      published.**

  The support ledger is constructed ONCE, before candidate
  iteration; candidate rows REFERENCE its count and digest and
  never independently reconstruct the support. Identical across
  all candidates; runtime-asserted alongside the count; mismatch
  in EITHER field is a hard STOP. The artifact publishes:
  support_ledger_path, support_ledger_sha256, rows_scored_common,
  scoring_support_sha256, duplicate_scoring_key_count = 0 — and
  ONE support ledger (v2.6.3 — the stale assigned_control_tick
  field is dead; the ledger carries the REGISTERED control
  identity): window_id, event key, feature_ts_ns,
  assigned_control_segment_id, assigned_control_mono_ns,
  relative_tick, response-validity state, trace-validity state,
  included_in_objective, exclusion reason. A logged tick number,
  if published anywhere, is a descriptor tied to no identity.
  [VOID_SUPERSEDED_BY_V2_5 (v2.6, channel-2 on R77-78 §3): the
  sentence that stood here — "nearest tick, dedup to first" —
  contradicted the causal-floor and whole-conflict-class rules
  and is VOID. The ONLY normative alignment/dedup text is 2f.1
  (causal floor) and 2f.3 (canonical identity). Never nearest
  future tick; never first-wins on contradictory payloads.]
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
  coordinate — membership decided by the ONE registered
  loss_equal relation (v2.6.2; the earlier relative-only "within
  NULL_TIE_REL_TOL" wording is dead) — and a
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
  **EXACT COMPARISON SEMANTICS (v2.6 TRI-STATE — the v2.5 binary
  rule was NOT A PARTITION: with gap = best_positive_sse -
  null_sse, "TIE iff gap <= epsilon" swallowed every case where
  the POSITIVE model is strictly better (gap = -5 is not a tie);
  and the 1e-18 sat inside the product where its contribution was
  1e-27 — a misnamed floor. Ledger entry R80. The registered
  relation:**

      losses: float64 SSE on the common support
      gap     = best_positive_sse - null_sse
      epsilon = max(NULL_TIE_REL_TOL
                      * max(|null_sse|, |best_positive_sse|),
                    SSE_ABS_TOL)
      NULL_TIE_REL_TOL = 1e-9
      SSE_ABS_TOL      = 1e-18   (a TRUE absolute tolerance,
                                  outside the product)

      gap >  epsilon  -> NULL_STRICTLY_BETTER
      gap < -epsilon  -> POSITIVE_STRICTLY_BETTER
      else            -> TIE

      NULL_STRICTLY_BETTER
        AND eligible_positive_candidate_count > 0
        AND identical support for every comparator
        AND no positive-g global minimizer -> NULL_CALIBRATED
      TIE -> NOT_IDENTIFIED (both-exactly-zero lands here: a
        dataset on which every model is perfect identifies
        nothing)
      POSITIVE_STRICTLY_BETTER -> the positive-g winner's own
        minimizer-set and local-face path

  **NON-VACUITY (v2.6; UNIQUE STATUS v2.6.1 — a branch cannot be
  both a typed disposition and an implementation choice):**
  eligible_positive_candidate_count == 0 -> EXACTLY
  UNCALIBRATABLE_NO_POSITIVE_COMPARATOR (NOT_IDENTIFIED may
  remain a reporting parent class, never the serialized primary
  status), REG-2 effect NONE, never NULL_CALIBRATED — "better
  than every member of an empty family" is vacuous truth, not
  identification. The packet publishes null_loss,
  best_positive_loss, gap, epsilon, the tri-state verdict, and
  the eligible-positive count.
  **ONE LOSS-EQUIVALENCE FUNCTION (v2.6.1, channel-2 §5 — the
  same pair may not be "tied" in one section and ordered in
  another):**

      loss_equal(a, b) := |a - b| <=
          max(LOSS_REL_TOL * max(|a|, |b|), LOSS_ABS_TOL)
      LOSS_REL_TOL = 1e-9;  LOSS_ABS_TOL = 1e-18

  This ONE relation governs: null-vs-best-positive; positive
  global-minimizer membership and global_minimizer_count; local
  neighbor comparison; first-wins display-row selection (chosen
  only AFTER the full equivalence class is published); and
  prediction-equivalence testing. The tri-state epsilon above IS
  this function's bound applied to the gap.
  [VOID_SUPERSEDED_BY_V2_6_2: the sentence that stood here sent
  a null/positive TIE to the positive winner's closed-face path
  — contradicting the tri-state table, under which TIE is
  TERMINAL NOT_IDENTIFIED for this calibration. The exclusive
  decision: no eligible positive comparator ->
  UNCALIBRATABLE_NO_POSITIVE_COMPARATOR; NULL_STRICTLY_BETTER ->
  evaluate NULL_CALIBRATED requirements;
  TIE -> NOT_IDENTIFIED, terminal; POSITIVE_STRICTLY_BETTER ->
  construct the complete positive loss_equal equivalence class;
  more than one non-equivalent positive minimizer ->
  NOT_IDENTIFIED; exactly one prediction-equivalence class ->
  the local positive-g face rule. A POSITIVE-BETTER outcome never
  rescues a tie; walking order never decides anything.]
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
   or tick index.
   [VOID_SUPERSEDED_BY_V2_6_1 (v2.6.2, channel-2 on R81 §2): the
   formula that stood here compared feature_ts_ns (EPOCH) to the
   control timeline — the exact cross-domain inequality the
   clock bridge below outlaws. The ONLY executable join is the
   CONTROL TIMELINE block below: entirely monotonic,
   feature_record_mono_ns against control mono_ns, within flight
   and segment. A correct amendment does not supersede an
   incompatible sentence merely by appearing later in the file —
   the incompatible sentence is dead, by name, here.]
   The causal-floor PRINCIPLE stands: no future control value
   ever leaks into an exposure-aligned row; no equidistant case
   exists; the fitted row is labeled by the assigned control row;
   the exposure identity time is preserved in the ledger; the
   signed-mismatch LEDGER is mandatory.
   **CONTROL TIMELINE (v2.6; CLOCK BRIDGE v2.6.1 — the v2.6 join
   compared EPOCH feature_ts_ns against MONOTONIC setpoint
   mono_ns, two different clocks ~1.78e9 seconds apart on the
   A091 hostile instance; ledger entry R81):**

   TWO CLOCKS, TWO ROLES: feature_ts_ns (epoch) is the IDENTITY
   clock — exposure identity, dedup, sentinel keys. The JOIN
   clock is MONOTONIC: every feature record LOGS ITS OWN mono_ns
   beside feature_ts_ns (verified on the committed A091 key
   files) — the bridge is the logged PAIR on each record, never
   an arithmetic transform, never a synthesized value. A feature
   record missing mono_ns -> ABSENT_CONTROL_TIME (typed), row
   OFF support.

   THE JOIN, entirely in the monotonic domain: control timestamp
   field = the replay-attached setpoint record's mono_ns;
   WITHIN-FLIGHT (partition flight_id), within SEGMENT.
   **CONTROL_SEGMENT_ID (v2.6.1; RESET-VS-DISORDER v2.6.2 — a
   mono_ns decrease alone does not distinguish a process-clock
   reset from one out-of-order record; automatic-decrease
   segmentation could invent a false segment at a late-written
   row):** segmentation operates ONLY on the canonical CONTROL
   stream (the replay-attached setpoint records), read from the
   COMMITTED source-log bytes in record order, with the packet
   binding: exact source-log path, source-log sha256, the
   control-record class used, and source_record_index (the
   committed ordinal, carried on every derived row so a
   reordered downstream copy reconstructs identical segments —
   fixture s37). Rules (v2.6.3, channel-2 H3 — "an explicit marker" was an
   unnamed concept; NO reset-marker field is registered in the
   logger contract): EVERY mono_ns decrease in the control
   stream -> CONTROL_ORDER_CONFLICT, fail closed — a segment is
   NEVER auto-created; one flight is one segment unless and
   until a marker field is registered from the logger's
   documented contract and walked by both channels (that future
   registration must freeze field name, accepted value set,
   strict parser, marker position relative to the decrease, and
   marker-without-decrease behavior); feature-row ordering NEVER
   participates in reset detection.
   assigned control row = argmax(control_mono_ns) subject to same
   flight AND same segment AND control_mono_ns <=
   feature_record_mono_ns; accept only 0 <= mismatch <= one
   registered control period. Row-level published: feature_ts_ns,
   feature mono_ns, assigned control mono_ns, signed mismatch.
   Fail-closed types: OFF_WINDOW_NO_CAUSAL_CONTROL;
   OFF_WINDOW_CONTROL_GAP; CONTROL_IDENTITY_CONFLICT (below);
   ABSENT_CONTROL_TIME.

   **CONTROL PRIMARY ID AND PAYLOAD (v2.6.1, channel-2 §7):**
   control primary ID = (flight_id, control_segment_id,
   control_mono_ns). CONTROL RELEVANT PAYLOAD, frozen ordered
   list (EXPANDED v2.6.3, channel-2 H2 — any field that changes
   owner, source, frame, clipping, or correction semantics
   participates in conflict adjudication; identical setpoints
   with contradictory physical stories may never be selected by
   order): (setpoint.v_body[2], planner_phase,
   vertical_owner_state, arbiter_selected_source, adapter_input,
   post_limit_command, clip_status, and every frame/sign field
   on the record — floats under the one float law: finite-only,
   NaN/Inf -> parse refusal, -0.0 normalized to +0.0; strings
   under strict closed-set parsing; missing -> typed ABSENT, and
   mixed presence within a class is an inconsistency). Duplicate control primary ID with
   inconsistent payload -> CONTROL_IDENTITY_CONFLICT, the ENTIRE
   control-identity class excluded and listed.
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
   (EXPOSURE_PAYLOAD_CONFLICT); any missing ID component ->
   ABSENT_EXPOSURE_KEY, excluded and listed.
   **RELEVANT PAYLOAD, FROZEN (v2.6; v2.6.2 — the v2.6 list
   omitted the feature record's OWN mono_ns, the entire clock
   bridge: two "exact duplicates" could join different control
   commands by file order without a conflict; ledger entry R83):**
       feature_record_mono_ns : int, exact equality — same
                         primary ID with different mono_ns ->
                         EXPOSURE_CLOCK_CONFLICT, entire class
                         excluded
       e_meas_m        : float64
       certified_full  : the parsed tri-state (2f.2)
       range_z_m       : float64, when present on the record
       level_pitch_rad : float64 (body-to-world transform input)
       level_roll_rad  : float64 (body-to-world transform input)
   ONE FLOAT LAW for every payload field, exposure and control
   alike (v2.6.2; BYTE ORDER v2.6.3, channel-2 H5): finite-only
   parse; NaN/Inf -> refusal; -0.0 normalized to +0.0 before
   comparison; equality on the canonical float64 bytes after
   normalization, where canonical = BIG-ENDIAN (network-order)
   IEEE-754, rendered as 16 lowercase hex characters wherever a
   textual form is needed; any other encoding is refused.
   A relevant field missing on SOME records of a class while
   present on others is a payload INCONSISTENCY (the class
   excludes); missing on ALL records is typed absence, not
   conflict.
   **FRAME_ID AUTHORITY (v2.6):** frame_id is DISCLOSED and
   COUNTED (collisions typed FRAME_ID_COLLISION in the ledger)
   but has NO independent censoring authority over
   primary-identity evidence until a runtime-equivalence fixture
   settles whether frame reuse is corruption or legal metadata —
   it may flag, never exclude, on its own. ONE normalization step applies this
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
   **THE COMMON KEY SCHEMA, FROZEN (v2.6; REFERENCE FIXED
   v2.6.2):** the primary exposure identity (flight_id,
   feature_ts_ns), serialized by THE KEY-SERIALIZATION CONTRACT
   named in the SCORING_SUPPORT_SHA256 block — the same encoder,
   verbatim, carried in the packet as key_encoder_id =
   REG1_KEY_ENCODER_V1 beside both keyset digests; no
   section-number indirection (the "2f.9 value rules" pointer
   that stood here was the fixture roster — stale, dead) — never
   row_key, frame_id, or any implementation label. sentinel_artifact_path is
   REPOSITORY-RELATIVE and must be the same path at all three
   checked commits. Duplicate keys within EITHER set are a
   failure. Missing fields, an unresolvable commit, or a schema
   mismatch are STARTUP/PRE-FIT failures.
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
   WHOLE-GROUP disposition, never first-row trust;
   **(v2.6 additions, channel-2 on R77-78 §12:)** (s24) positive
   model strictly better (gap < -epsilon) ->
   POSITIVE_STRICTLY_BETTER, never TIE, never NULL_CALIBRATED;
   (s25) zero eligible positive comparators ->
   UNCALIBRATABLE_NO_POSITIVE_COMPARATOR, never vacuous NULL;
   (s26) same physical windows in different input order -> same
   canonical window_ids, same support digest; (s27) equal
   cardinality with a substituted event -> different digest,
   hard STOP; (s28) future tick temporally NEARER than the prior
   tick -> the causal floor still selects the prior tick; (s29)
   flight boundary / clock reset / duplicate control tick -> no
   cross-segment join, typed refusals; (s30) same
   (flight_id, feature_ts_ns) with different registered payload
   -> entire class excluded; (s31) frame_id disagreement ->
   disclosed and counted, no undeclared censoring authority;
   (s32) sentinel and calibration key encodings differ ->
   refusal before fitting; (s33) source bytes committed earlier
   than execution tip -> distinct full hashes reported, byte
   equality proved.

   **FIXTURE DEFINITIONS s34-s48 (v2.6.3 — REGISTERED AS
   EXECUTABLE DEFINITIONS, each with input and expected
   disposition; the R83 claim that these existed was false — the
   editing script's replace missed its anchor and printed success
   unconditionally; ledger entry R85):**
   (s34) input: a join attempt comparing epoch feature_ts_ns
   against control mono_ns -> expected: hard failure, no join
   result field exists in the output at all.
   (s35) input: two rows, same (flight_id, feature_ts_ns),
   feature mono_ns 100 vs 120, all else equal -> expected:
   EXPOSURE_CLOCK_CONFLICT, entire class excluded, zero rows
   enter support.
   (s36) input: control stream mono order 100,120,110,130, no
   reset marker -> expected: CONTROL_ORDER_CONFLICT fail-closed;
   no segment invented; the packet's instrument_validity = FAIL.
   (s37) input: a downstream copy of identical rows in shuffled
   order, each carrying source_record_index -> expected:
   identical segment IDs, window IDs, and scoring_support_sha256.
   (s38) input: null loss and one positive loss with
   loss_equal(a,b) true -> expected: terminal NOT_IDENTIFIED;
   asserting the positive face path was NEVER entered.
   (s39) input: one qualifying window, 13 objective rows ->
   expected: STARVED with BOTH INSUFFICIENT_PRIMARY_WINDOWS and
   INSUFFICIENT_COMMON_SUPPORT_ROWS present.
   (s40) input: support reasons empty + model reason
   INSUFFICIENT_PRIMARY_WINDOWS -> expected:
   NO_ARM_MALFORMED_PACKET.
   (s41) input: support reasons nonempty + model
   UNCALIBRATABLE(PROVENANCE_FAILURE) -> expected:
   NO_ARM_NONCOLLECTION_FAILURE, never armed.
   (s42) input: profile config bytes differing from the
   registered table in one tick value -> expected:
   profile-digest mismatch, Gate-3 refusal.
   (s43) input: arming packet lacking the profile symmetry row
   (or carrying one with an unanswered counterfactual) ->
   expected: arming-packet refusal.
   (s44) input: support-predicate evaluator raising on predicate
   2 of 3, emitting an empty reason set with
   predicates_evaluated_n = 2 != 3 -> expected:
   NO_ARM_MALFORMED_PACKET, never ADEQUATE.
   (s45) input: two control rows, same
   (flight, segment, mono_ns), same setpoint, owner LEGACY vs
   TERM -> expected: CONTROL_IDENTITY_CONFLICT, whole class
   excluded (owner is payload, never order-selected).
   (s46) input: same, but clip_status false vs true -> expected:
   CONTROL_IDENTITY_CONFLICT, whole class excluded.
   (s47) input: a mono_ns decrease adjacent to a blank / "False"
   / misplaced marker-like field -> expected:
   CONTROL_ORDER_CONFLICT in every case (no marker field is
   registered; no decrease is ever a lawful reset).
   (s48) input: the float 1.0 serialized under both endian
   conventions -> expected: exactly one accepted canonical form
   (big-endian IEEE-754 hex), the other refused.
   **RERUN RULE (v2.6): the prior 21/21 + 18/18 greens are valid
   HISTORY of the cases they executed under their v2.3-bound
   source — never summed into final-contract coverage. One
   complete run of every still-relevant fixture, under ONE source
   commit descending from the final criterion, at ONE pushed tip,
   is the only coverage that counts.**

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

**MACHINE-BOUND DISCLOSURE FIELDS (v2.5; EXACT VALUES FROZEN IN
THE CRITERION v2.6, channel-2 order 11 — the packet checker FAILS
a real calibration candidate lacking this block):**

    prior_viewed_artifact_path =
        tuning/a091-response-model-calibration-reg1v22-aaa1c17-20260721T113736Z/summary.json
    prior_viewed_artifact_sha256 =
        b7e7f66bc307a0f0b68f6938b78ae55719ee43f648164019dbaada46ad3553f1
        (committed bytes at the evidence commit)
    prior_viewed_evidence_commit_full =
        b42103962f2ee8445f3d2cd51897006b1da97714
    prior_viewed_attestation_commit_full =
        044153b55cb543b5141b910e8893c65ce92fa36b
    prior_viewed_removal_commit_full =
        2fa8e9d8059f5031b211e7cf28742b0bfe535d4b
    prior_calibration_status = NULL_CALIBRATED
    prior_g = 0.0; prior_tau = 0.02; prior_L = 0; prior_rms = 0.0
    prior_scoring_rows = 51
    prior_fit_directions = [DOWN, UP]
    prior_disposition = VOID_PRE_V2.3
    prior_board_effect = NONE

**OUTCOME-SYMMETRY MACHINE LEDGER (v2.6, channel-2 on R77-78 §1
— the walk's question becomes a typed record; one row per
post-observational amendment in every real packet):**

    amendment_id; amendment_commit;
    prior_result_seen;
    status_independent_defect_statement;
    evidence_establishing_the_defect;
    opposite_result_counterfactual;
    same_amendment_under_opposite_result (YES/NO);
    effect_on_evidentiary_burden (RAISES/LOWERS/NEUTRAL);
    channel1_disposition; channel2_disposition.

A NO answer does not prohibit the amendment; it forces the typed
classification OUTCOME_RESPONSIVE and bars describing it as an
ordinary instrument correction.
**TYPED CONSEQUENCE (v2.6.1, channel-1 on ADVISORY-30 — "a
classification without a disposition is a label, and labels
without dispositions are where drift lives"):** every
OUTCOME_RESPONSIVE row carries a mandatory consequence field,
closed enum: VOID_AND_RESTART_UNDER_INDEPENDENT_RATIONALE (the
amendment re-lands only with a justification that never
references the seen status) or QUARANTINE_PENDING_REREGISTRATION
(the amendment is inoperative until both channels ratify it
knowingly as outcome-responsive). A row classified
OUTCOME_RESPONSIVE with no consequence, or with an unknown
consequence string, is a packet-checker FAILURE.

**WALK DISCLOSURE (channel-1 on R81, standing rule of the
program): every channel walk PUBLISHES the hostile-instance list
it ran — the all-candidate-scores discipline applied to the
walker itself. A nod without a published instance list is a
presence-audit, not a contract-audit; and the book is the
instance GENERATOR (ledger-driven hostility): before every nod,
each relevant book line — clock domains, zero/None, units,
placement, identity/cardinality, vacuity, partition — runs
against the clause as a computed number, not a read sentence.**

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
                         NULL_CALIBRATED; UNCALIBRATABLE,
                         UNCALIBRATABLE_NO_POSITIVE_COMPARATOR,
                         and NOT_IDENTIFIED cannot fill this
                         block — the no-comparator status is a
                         first-class member of every closed enum
                         and startup parser, never a child label
                         of generic UNCALIBRATABLE)
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
