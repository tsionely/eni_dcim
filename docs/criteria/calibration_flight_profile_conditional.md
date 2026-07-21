# CONDITIONAL PRE-REGISTRATION — Dedicated calibration-metrology flight (SAKANA), armed only by a typed data-starvation finding

THIS DOCUMENT AUTHORIZES NO FLIGHT. It is a pre-registration,
committed BEFORE the v2.5 A091 calibration read exists, so that
neither the arming decision nor the flight profile can be shaped
after seeing which calibration status appears
(outcome-symmetry: registered now, while the outcome is unknown).
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
candidate explanation (RESPONSE-68 §3). If the lawful v2.5
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

    calibration_support_status (typed reasons, closed):
        ADEQUATE iff qualifying_windows_primary >= 2
                 AND total_valid_response_rows >= 16
                 AND no identifiability starvation
        else STARVED_WINDOWS / STARVED_ROWS /
             STARVED_IDENTIFIABILITY
        (constants cite their sources, channel-1 rider 1:
         16 = 2 x the 2c post-lag row minimum of 8 — two
         windows' worth of it; 2 = the minimum on which
         leave-one-window-out validation is DEFINED at all — a
         calibration-domain derivation, NOT the mechanism K = 2,
         whose approach-level transfer is withdrawn; ledger
         entry R81)

    calibration_model_status: CALIBRATED / NULL_CALIBRATED /
        NOT_IDENTIFIED / UNCALIBRATABLE(reason)

ARMING RULE, symmetric by construction:

    instrument PASS and support_status != ADEQUATE -> ARM,
        regardless of the model answer — a starved CALIBRATED
        arms exactly as a starved NULL does.
    instrument PASS and support ADEQUATE -> DISARM,
        regardless of the model answer.
    instrument FAIL -> no arming; instrument repair.

    UNCALIBRATABLE arms ONLY through the closed reason
    allowlist: INSUFFICIENT_PRIMARY_WINDOWS,
    INSUFFICIENT_VALID_RESPONSE_ROWS,
    NO_ELIGIBLE_POSITIVE_COMPARATOR_DUE_TO_SUPPORT_HORIZON.
    Unknown or non-support reason codes FAIL CLOSED and never
    arm.

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

## 3. FLIGHT PROFILE (frozen here, pre-outcome)

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
      per primitive:
        P1 ramp           <= 25 ticks to reference +0.50 m/s
                          world-up (within every legacy cap;
                          shipped command interface ONLY —
                          channel-1 rider 2, no bespoke
                          actuation path)
        P2 stable hold    = 60 ticks at +0.50 (covers the
                          10-tick / 0.05 m/s pre-window rule
                          with 6x margin)
        P3 down-step      = one tick, +0.50 -> 0.0
                          (magnitude 0.50 >= the 0.35 floor)
        P4 post-step hold = 75 ticks at 0.0 (covers the 50-tick
                          horizon with 1.5x margin; no
                          intervening transition)
        P5 recovery       = <= 100 ticks altitude re-trim to
                          band center
      failed primitive (stability not reached within 200 ticks)
                          -> skip to P5, count it, continue; NO
                          in-flight retry logic beyond the fixed
                          10 primitives
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
