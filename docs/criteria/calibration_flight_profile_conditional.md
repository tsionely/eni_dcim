# CONDITIONAL PRE-REGISTRATION — Dedicated calibration-metrology flight (SAKANA), armed only by a typed data-starvation finding

THIS DOCUMENT AUTHORIZES NO FLIGHT. It is a pre-registration —
PRE-ADJUDICATIVE, NOT PRE-OBSERVATION (v3, channel-2 on R81 §12:
the VOID_PRE_V2.3 NULL_CALIBRATED packet had already been
generated and viewed when this document and its rewrites landed;
the earlier "while the outcome is unknown" opening was a false
historical tense — ledger entry R83). It is registered before any
LAWFUL final-generation A091 read exists, and both the trigger
and the exact profile carry their own outcome-symmetry ledger
rows rather than a pre-outcome claim.
It becomes operative only through the full gate chain in Section
5 — including explicit BOTH-CHANNEL reopening of the ratified
collection stop and the standard two-channel-signed release to
Sakana. Until then Sakana remains STANDBY and zero flights are
spent.

## 1. Why this pre-registration exists

The archive census is CLOSED at 23 physical approaches (ratified;
zero flights spent) — archive evidence cannot be minted. A091 is
the ONE physical TERM episode, and the entire response-model
calibration currently rests on ONE qualifying down-step window
with 13 rows, whose v1 (void) read showed an all-zero response
target — with sparse certified-FULL coverage standing as a named
candidate explanation (RESPONSE-68 §3). If the lawful FINAL-GENERATION
instrument reads A091 and declares data starvation, a dedicated
metrology flight is the ONLY lawful route to more calibration
evidence. This document exists so that route is days, not weeks,
from that finding.

## 2. ARMING CONDITION (v2 — SUPPORT-FIRST, channel-2 on R79-80 §10-§11: the v1 trigger armed on a starved NULL and disarmed on a CALIBRATED at IDENTICAL support — it failed the outcome-symmetry check this program had just registered; ledger entry R81. Support adequacy is now a separate, PRIMARY axis, blind to the model answer)

The arming read is three typed axes, all computed by the
generator and read off a FINAL-GENERATION A091 packet (the
final REG-1 commit's contract — never the superseded v2.5),
walked by both channels:

    instrument_validity: PASS / FAIL
        FAIL (any INVALID_INPUT, PROVENANCE_FAILURE,
        CLOCK_ALIGNMENT_FAILURE, SENTINEL_BINDING_FAILURE,
        SCHEMA_FAILURE, MODEL_CONTRACT_FAILURE,
        UNSUPPORTED_DIRECTION) -> repair the instrument;
        a flight NEVER cures an instrument; NEVER arms.

    calibration_support_status (v3 — a PARTITION, channel-2 §8:
    the v2 singular statuses overlapped on the known
    one-window/13-row pattern):
        calibration_support_reasons : closed SET, possibly
        multiple, of:
            INSUFFICIENT_PRIMARY_WINDOWS
                (qualifying_windows_primary < 2)
            INSUFFICIENT_COMMON_SUPPORT_ROWS
                (common OBJECTIVE rows — post-alignment,
                 post-certification, post-dedup, post-trace-
                 validity, the rows_scored_common count — < 16;
                 the count basis is the objective set, nothing
                 earlier)
            NO_ELIGIBLE_POSITIVE_COMPARATOR_DUE_TO_SUPPORT_HORIZON
                (eligible_positive_candidate_count == 0 AND the
                 ineligibility reasons are all HORIZON_LT_TAU /
                 INSUFFICIENT_ROWS — the mechanical
                 identifiability-starvation definition)
        ADEQUATE iff the reason set is EMPTY **UNDER THE
        COMPUTED-COMPLETENESS ATTESTATION (v3.1, channel-1 on
        ADVISORY-31 — empty-by-failure must never read as
        empty-by-adequacy): the packet asserts
        predicates_evaluated_n == registered_predicates_n, where
        registered_predicates_n = 3 is DERIVED from the frozen
        registry registered_predicate_ids =
        {INSUFFICIENT_PRIMARY_WINDOWS,
        INSUFFICIENT_COMMON_SUPPORT_ROWS,
        NO_ELIGIBLE_POSITIVE_COMPARATOR_DUE_TO_SUPPORT_HORIZON}
        — never accepted from the result producer (v3.2,
        channel-2 §5; fixture s49) — with one evaluated flag and
        result PER exact ID; an empty set
        WITHOUT that attestation is NO_ARM_MALFORMED_PACKET at
        arming branch 2, never adequacy. An empty set is never
        adequacy evidence unless its emptiness is attested — the
        zero-minting law at the set level.**
        STARVED iff it is NONEMPTY (all reasons published).
        ADEQUATE is captioned MINIMALLY ADEQUATE FOR
        WITHIN-FLIGHT MODEL IDENTIFICATION — it never implies
        transport validation, cross-flight replication,
        mechanism confirmation, or shipping-build validation.
        Typed counts published: window_n, flight_n,
        dependence_block_n (for this flight: flight_n = 1,
        dependence_block_n = 1, regardless of window_n)
        (constants cite their sources, channel-1 rider 1:
         16 = 2 x the 2c post-lag row minimum of 8 — two
         windows' worth of it; 2 = the minimum on which
         leave-one-window-out validation is DEFINED at all — a
         calibration-domain derivation, NOT the mechanism K = 2,
         whose approach-level transfer is withdrawn; ledger
         entry R81)

    calibration_model_status: CALIBRATED / NULL_CALIBRATED /
        NOT_IDENTIFIED / UNCALIBRATABLE_NO_POSITIVE_COMPARATOR /
        UNCALIBRATABLE(reason) — the model-reason enum is CLOSED:
        {INSUFFICIENT_PRIMARY_WINDOWS,
         INSUFFICIENT_VALID_RESPONSE_ROWS} are the only
        support-class reasons; every other string is non-support.

    **CROSS-AXIS COMPATIBILITY MATRIX (v3.1, channel-2 H12 —
    every permitted pair named; every unnamed pair is
    NO_ARM_MALFORMED_PACKET):**
        INSUFFICIENT_PRIMARY_WINDOWS pairs with: CALIBRATED,
            NULL_CALIBRATED, NOT_IDENTIFIED,
            UNCALIBRATABLE(INSUFFICIENT_PRIMARY_WINDOWS);
        INSUFFICIENT_COMMON_SUPPORT_ROWS pairs with: CALIBRATED,
            NULL_CALIBRATED, NOT_IDENTIFIED,
            UNCALIBRATABLE(INSUFFICIENT_VALID_RESPONSE_ROWS);
        NO_ELIGIBLE_POSITIVE_COMPARATOR_DUE_TO_SUPPORT_HORIZON
            pairs with: UNCALIBRATABLE_NO_POSITIVE_COMPARATOR —
            **AND (v3.3, channel-2 on R86 H2: the matrix failed a
            lawful multi-reason hostile) that primary status is
            EXPLICITLY COMPATIBLE with any ADDITIONAL
            support-starvation reasons simultaneously true:
            a packet may carry {INSUFFICIENT_PRIMARY_WINDOWS,
            NO_ELIGIBLE_POSITIVE_COMPARATOR_DUE_TO_SUPPORT_HORIZON}
            (or rows, or all three) beside primary
            UNCALIBRATABLE_NO_POSITIVE_COMPARATOR with the
            matching reason_set — a valid STARVED packet, never
            MALFORMED.**
    **ADEQUATE ROW (v3.2, channel-2 §6.1):** support reasons
    empty (attested) pairs with: CALIBRATED, NULL_CALIBRATED,
    NOT_IDENTIFIED — and NOTHING else; a support-class
    UNCALIBRATABLE reason beside an empty support set, or any
    UNCALIBRATABLE beside attested-adequate support, is
    NO_ARM_MALFORMED_PACKET.
    **MULTI-REASON COMPOSITION (§6.2):** the model reason field
    is SET-VALUED (reason_set); compatibility requires EVERY
    support reason to have its matrix counterpart present and
    EVERY model reason to have its support counterpart —
    intersection semantics, both directions; the 1-window/13-row
    hostile carries both pairs.
    **CLOSED ENUMS (§6.3):** support-class model reasons =
    {INSUFFICIENT_PRIMARY_WINDOWS,
    INSUFFICIENT_VALID_RESPONSE_ROWS,
    NO_POSITIVE_COMPARATOR_SUPPORT_HORIZON}; non-support model
    reasons = exactly the instrument-axis enum (which executes at
    branch 1, never branch 3); ANY other string ->
    NO_ARM_MALFORMED_PACKET, always (v3.3 — the "or branch-3"
    alternative is dead with branch 3 itself); "every other
    string is non-support" is dead; unknown is MALFORMED, never
    reclassified.
    A model support-class reason maps by THIS matrix alone — an
    implementation never decides membership by string
    resemblance.

ARMING RULE (v3 — TOP-DOWN, first match wins, channel-2 §9:
the v2 general rule and the UNCALIBRATABLE allowlist conflicted
on a starved-support packet with a non-support UNCALIBRATABLE
reason):

    1. instrument FAIL
           -> NO_ARM_INSTRUMENT_REPAIR
    2. cross-axis inconsistency (e.g. support ADEQUATE beside an
       insufficient-windows model reason; or a support reason
       without its matching model evidence)
           -> NO_ARM_MALFORMED_PACKET
    3. [DELETED v3.3, channel-2 on R86 H1: branch 3 had no
       lawful registered member — known non-support reasons are
       instrument-axis (branch 1), unknown strings are MALFORMED
       (branch 2). An unknown reason cannot be both MALFORMED and
       a lawful branch input. Unknown model reason -> ALWAYS
       NO_ARM_MALFORMED_PACKET at branch 2.]
    4. calibration_support_reasons nonempty
           -> ARM_PENDING_FIVE_GATES
    5. calibration_support_reasons empty
           -> DISARM_SUPPORT_ADEQUATE

    Permitted cross-axis pair, registered explicitly:
    support reason
    NO_ELIGIBLE_POSITIVE_COMPARATOR_DUE_TO_SUPPORT_HORIZON pairs
    with model primary status
    UNCALIBRATABLE_NO_POSITIVE_COMPARATOR. Unknown reason codes
    FAIL CLOSED at branch 3 and never arm.

**SUPPORT ADEQUACY PRECEDES REG-2 ELIGIBILITY: a support-starved
result NEVER fills REG-2 — not even a starved CALIBRATED. The
contradiction "established enough to bind, starved enough to
fly" cannot arise.**

**SYMMETRY-LEDGER ROW for this filing (mandatory in the arming
packet):** this criterion was filed after the VOID_PRE_V2.3 null
packet was viewed. Under the v1 trigger the honest answer to
"same amendment under the opposite result?" was NO; under THIS
support-first rewrite it is YES — the trigger reads support,
never the model answer. The row is carried with
classification ORDINARY_INSTRUMENT_CORRECTION and the rewrite
history disclosed.

## 3. FLIGHT PROFILE (v3 — exact deterministic experiment; post-observational instrument design, audited by its own symmetry row)

- **Class**: METROLOGY FLIGHT — not a race flight, not a release,
  not the repaired-build re-earn, and not evidence for any
  mechanism verdict by itself.
- **LEGACY PATH ONLY — TERM NEVER ENGAGES**: the terminal
  vertical channel is DISABLED BY CONFIG for this flight (owner
  arbiter never takes vertical; the known signed defect lives in
  TERM actuation and therefore never actuates). The calibration
  measures the legacy actuating path — exactly the path the
  Contract-B model describes (the R66 transport inversion).
- **Geometry**: hover-hold facing a gate at range 3.5-5.0 m from
  the gate face — at or above the 3.5 m bound below which
  certified FULL was observed to drop
  (NO_CERTIFIED_FULL_BELOW_3P5, flight-4 record) — camera on the
  gate, dense certified FULL-quad coverage throughout.
- **Command script (v2 — EXACT, channel-2 §13: the v1
  inequalities admitted materially different profiles chosen
  after the outcome; this is a frozen experiment, not a
  template):**

      primitives          = 10, identical, executed in order
      starting reference  = 0.0 m/s world-up (hover trim)
      per primitive (v3 — per-tick determinism, channel-2 §11):
        INTERFACE: every reference is written to
                          Setpoint.v_body[2] through the shipped
                          planner interface (rider 2), with the
                          registered sign transform v_body_z =
                          -v_up / (cos(level_pitch) *
                          cos(level_roll)); the EXPECTED world-up
                          reference stream below is the per-tick
                          truth the log must show
        P1 ramp           = EXACTLY 25 ticks, linear per-tick
                          sequence v_up[i] = 0.50 * i / 25,
                          i = 1..25 (deterministic table, no
                          shape freedom); a limiter clip on any
                          P1 tick is LISTED and the primitive is
                          classified CLIPPED (still executed,
                          never fitted)
        P2 stable hold    = 60 ticks at exactly +0.50; ENTRY
                          PREDICATE (machine): the logged
                          reference equals 0.50 within 1e-9 for
                          10 consecutive ticks; the 60-tick
                          counter starts at the first tick of
                          that run
        P3 down-step      = one tick, +0.50 -> 0.0 exactly
        P4 post-step hold = 75 ticks at exactly 0.0; counter
                          starts the tick after P3
        P5 recovery       = ALTITUDE re-trim, deterministic
                          per-tick LAW (v3.1, channel-2 H10; the
                          v3 range-conflation is corrected —
                          forward range [3.0,5.5] is a GUARD,
                          altitude is what P5 re-trims):
                          e_alt[i] = alt[i] - alt_ref (alt_ref
                          latched once at script P0);
                          v_up_cmd[i] = clamp(-0.30 * e_alt[i],
                          -0.30, +0.30), deadband |e_alt| <=
                          0.10 -> 0.0; per-tick update; missing
                          altitude sample -> hold previous
                          command, count it; 5 consecutive
                          missing -> SCRIPT TERMINATES. **SLEW LIMIT (v3.2) AND
                          EXACT RECURRENCE (v3.3, channel-2 on
                          R86 §4 — a bound excludes the 0.60
                          jump but selects no single command;
                          the experiment is ONE sequence):
                          target[i] = deadbanded
                          clamp(-0.30 * e_alt[i], -0.30, +0.30);
                          delta[i] = clamp(target[i] -
                          v_cmd[i-1], -0.15, +0.15);
                          v_cmd[i] = v_cmd[i-1] + delta[i].
                          v_cmd at P5 entry = 0.0 (P4 ends
                          there). On a missing altitude sample:
                          target[i] = target[i-1] (held), the
                          recurrence still applies. The success
                          predicate reads the POST-SLEW command
                          (reference at 0.0 means v_cmd == 0.0
                          exactly).**
                          With magnitude <= 0.30 AND per-tick
                          change <= 0.15 < 0.35, no P5
                          transition can qualify as a detector
                          event — now BY THE REGISTERED LAW, not
                          by inference (fixture s50).
                          SUCCESS: |e_alt| <= 0.15 for 10
                          consecutive ticks AND reference at
                          0.0. Altitude source: the shipped
                          estimator's anchored world-altitude
                          output; the exact field name, clock,
                          sign, and validity rule are bound in
                          the machine-readable profile config
                          (below) and walked at Gate 3.
      ONE DEADLINE (v3.1, channel-2 H9 — the v3 150/300 pair
      summed to 311 > 300; the 150-tick phase timeout is dead):
      the TOTAL primitive budget is 350 ticks from that
      primitive's P1 tick 0 (25+60+1+75 = 161 scripted + up to
      189 for P5); the ONLY deadline is the total.
      FAILED PRIMITIVE = P5 success not reached at tick 349 ->
      **THE SCRIPT TERMINATES (v3.1, channel-2 H11 — a failed
      reset can never be followed by an "identical" next
      primitive): standard recovery/landing; partial data
      ingests under Section 4 like any data; the primitive
      count records how far the script got.** NO in-flight
      retry, ever.
      P0A — ALTITUDE-REFERENCE ACQUISITION (v3.2, channel-2 §8
      — the v3.1 P0 was circular: e_alt needed alt_ref, and P0
      created it): executed ONCE, before primitive 1: collect 25
      consecutive VALID altitude samples (validity per the
      binding artifact) whose spread (max - min) <= 0.10 m;
      alt_ref = their median, IMMUTABLE for the whole script
      (never re-latched between primitives); acquisition not
      achieved within 300 ticks -> SCRIPT NEVER STARTS.
      P0B — START-STATE VERIFICATION (every primitive, including
      the first): reference at 0.0 AND |alt - alt_ref| <= 0.15
      for 10 consecutive ticks AND forward range in [4.0, 4.5]
      m; not achieved within 200 ticks -> SCRIPT TERMINATES
      (never a primitive from an unverified state).
      max total duration  = 120 s wall clock, hard abort after
      max vertical excursion (v3.2 — typed against ALTITUDE,
      channel-2 §9; "band center" is a forward-range number and
      never an altitude reference): |alt - alt_ref| > 1.5 m ->
                          hard abort (script terminates, standard
                          recovery/landing; partial data ingests
                          under Section 4 like any data)
      range guard         = abort outside [3.0, 5.5] m from gate
      clip/saturation     = shipped limiter behavior; every clip
                          event listed
      fewer than 8 qualifying windows post-flight -> NO reflight
                          under this arming (channel-1 rider 4:
                          one flight per arming event; re-arming
                          requires a fresh walked packet and
                          fresh gates)

  Design target >= 8 qualifying windows: 10 primitives at the
  detector's by-construction acceptance (each primitive is built
  to satisfy pre-window, floor, and horizon exactly) minus
  headroom for two failures. The adequacy MINIMUM remains 2
  windows / 16 rows (Section 2 derivations); 8 is a design
  target, never an adjudicative threshold. **P1 CORRECTION
  (v3.1, channel-2 H7 — the v3 sentence was FALSE under the
  registered detector): the P1 ramp moves 0.02 m/s per tick,
  BELOW the 0.35 per-tick step floor — it creates ZERO detector
  step events; it is listed as SCRIPT PROVENANCE only. The ONLY
  detector events this script can create are the P3 down-steps:
  P5 commands are bounded to 0.30 m/s with every single-tick
  change < 0.35 by the registered law below, so no P5 transition
  can ever qualify (channel-2 H8, closed BY CONSTRUCTION).**
  **INGESTION SYMMETRY (channel-1 rider 3): the flight's windows
  meet the same detector and eligibility rules as A091's, with
  zero flight-specific allowances.** **METROLOGY PROVENANCE
  (channel-1 rider 5): outside every cohort, Advisory-19
  condition 3 verbatim.**
  **PROFILE SYMMETRY-LEDGER ROW (v3, channel-2 §12 — the trigger
  may be symmetric while the excitation profile is
  result-responsive; separate amendments, separate rows):** the
  arming packet carries amendment_id
  conditional_flight_exact_profile_v3; prior result seen: YES
  (the VOID_PRE_V2.3 null packet and its sparse-support
  history); counterfactual question: would the same ten
  primitives, +0.50 amplitude, exact durations, abort envelope,
  and one-flight rule have been registered after an opposite
  model result on the same support? Honest answer: YES for the
  structure (the amplitude and durations derive from registered
  constants and detector margins, not from the null result); the
  row is carried with that answer and its derivation, and any
  future profile change re-answers it or takes an
  OUTCOME_RESPONSIVE consequence. The profile carries a
  PROFILE-CONFIG DIGEST with a BYTE CONTRACT (v3.1, channel-2
  H13): the machine-readable table is the committed file
  docs/criteria/calibration_flight_profile_config.json — UTF-8,
  LF newlines, two-space indent, sorted keys, decimal numbers —
  and the digest is the SHA-256 of its COMMITTED BYTES (git
  show at the governing commit). Gate 3 compares THAT digest;
  any drift is a refusal. **FIELD-BINDING ARCHITECTURE = OPTION B (v3.2, channel-2 §10):
  the profile-law JSON stays IMMUTABLE; the exact
  altitude/range source fields land in a SEPARATE Gate-3
  binding artifact with its own schema, ancestry, digest, and
  both-channel walk; the flight-ingestion generator must descend
  from that binding before reading flight data. GATE-3
  COMPLETENESS (channel-1 on R84-85, beside identity): at
  arming, the EFFECTIVE config (profile-law JSON + binding
  artifact) contains ZERO PENDING markers — any pending marker
  is a typed Gate-3 refusal; identity (digest match) and
  completeness (no pending) are TWO checks, both mandatory.**
- **Implementation**: the scripted profile is an ISOLATED planner
  mode — off by default, config-gated, zero changes to the race
  path, TERM disabled. It is flight-adjacent code and therefore
  requires its own two-channel review before the flight; its
  existence changes nothing about the blocked shipping path.

## 4. DATA CONTRACT (the flight inherits the FINAL GOVERNING REG-1 generation — the v2.5 heading was stale, dead by name; v3.1)

The flight's recordings are ingested by the SAME FINAL-GENERATION
source generator (the final REG-1 commit's contract — the v2.5
binding of the first edition is corrected; ledger entry R81)
under the SAME contracts: clock-bridged causal-floor alignment,
runtime-aligned exposure identity, strict certification parsing,
canonical dedup, support-digest identity, staged sentinel schema,
branch-typed output, prior-viewing disclosure (2g — including
this document and the A091 starvation packet as viewed context).
New-flight calibration windows are calibration-only: the A091
sentinel interval remains the sentinel; no row wears two hats;
mechanism-2 adjudication consumes nothing from this flight
without its own criterion. Any bridge use of the flight's TERM-
free episodes requires its own registration.

## 5. GATE CHAIN (all five, in order — none skippable)

    1. The arming packet exists, is walked by BOTH channels, and
       its starvation markers are confirmed in both walks.
    2. BOTH channels explicitly REOPEN the ratified collection
       stop for exactly ONE metrology flight (scope-limited
       reopening, not a standing reopening).
    3. BOTH channels review and sign the profile config + the
       isolated scripted mode (Section 3), including the
       TERM-disabled config proof.
    4. The standard two-channel-signed release instruction issues
       to Sakana (SIM LOCK protocol, ancestor rule, unpushed
       flights do not exist).
    5. Post-flight: data ingested under Section 4; the criterion
       chain for anything read from it starts at THIS document's
       commit.

## 6. Standing

[VOID_SUPERSEDED_BY_V3 (v3.1, channel-2 H6): "Registered
pre-outcome" stood here — the same false tense the opening
already corrected; dead by name.] Registered PRE-ADJUDICATIVE,
POST-OBSERVATION. Arms only by Section 2. Authorizes
nothing by itself. Sakana STANDBY; cohort-4 HOLD; the blocked
shipping path stays blocked; no mechanism verdict, no admissible
residual, no HOLD-lift signature exists.
