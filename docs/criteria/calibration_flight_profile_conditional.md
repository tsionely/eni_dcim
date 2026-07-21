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
        ADEQUATE iff the reason set is EMPTY;
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
        NOT_IDENTIFIED / UNCALIBRATABLE(reason)

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
    3. model UNCALIBRATABLE with reason OUTSIDE the
       support-starvation allowlist
           -> NO_ARM_NONCOLLECTION_FAILURE (a flight never cures
              an instrument)
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
        P5 recovery       = altitude re-trim to BAND CENTER
                          = 4.25 m from gate face (the numeric
                          center of 3.5-5.0), commanded through
                          the same shipped interface at
                          reference magnitude <= 0.35 m/s;
                          SUCCESS PREDICATE: |range - 4.25| <=
                          0.25 m for 10 consecutive ticks;
                          TIMEOUT = 150 ticks
      FAILED PRIMITIVE (one rule, one timeout — the v2 100/200
      inconsistency is dead): a primitive that has not reached
      its P5 success predicate within 300 ticks TOTAL from its
      P1 start is FAILED_PRIMITIVE — logged, counted, the script
      advances to the next primitive's P1; NO in-flight retry
      beyond the fixed 10 primitives
      max total duration  = 120 s wall clock, hard abort after
      max vertical excursion = +/- 1.5 m about band center ->
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
  target, never an adjudicative threshold. UP-transitions (the
  P1 ramps) are DETECTED and listed per 2d — never fitted unless
  a separate up-direction validation is later registered.
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
  PROFILE-CONFIG DIGEST (sha256 of the exact script table); any
  drift from the registered table is a Gate-3 refusal.**
- **Implementation**: the scripted profile is an ISOLATED planner
  mode — off by default, config-gated, zero changes to the race
  path, TERM disabled. It is flight-adjacent code and therefore
  requires its own two-channel review before the flight; its
  existence changes nothing about the blocked shipping path.

## 4. DATA CONTRACT (the flight inherits every v2.5 law)

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

Registered pre-outcome. Arms only by Section 2. Authorizes
nothing by itself. Sakana STANDBY; cohort-4 HOLD; the blocked
shipping path stays blocked; no mechanism verdict, no admissible
residual, no HOLD-lift signature exists.
