# Inter-gate segment — N0 verdict + pre-registered A/B endpoints

Gate 1 is declared closed (advisory 8 §0; two sim-counted passes,
crossing |true_dz| <= 0.09 vs the 0.2 bar). This file opens the next
front per the advisory-8 implementation brief.

## N0 autopsy verdict (run 2026-07-19 on both chase-death fixtures)

**The registered prediction ("at least one death is a wash-seeded
fiction chase") is REFUTED.** Post-hoc 512-scale test on every
post-pass detection with pose:

- try15 (pass 7.93s, death 14.16s impulse 5.2): products 550-776 —
  HONEST throughout. The believed target hops R=7.4 -> 17.1 -> 4.8 ->
  5.5 -> 6.1 -> 11.8 with bearing swinging +41 -> -20 -> +7 -> +14 ->
  +21 -> -3 deg. Death mechanism: **acquisition churn among multiple
  REAL gates** — path weaves following the hops, strikes structure
  during the post-retreat recover.
- try39 (pass 8.59s, death 18.21s impulse 2.4): same signature —
  honest products, bearings swinging +/-30 deg; its first post-pass
  commit reached believed R=0.42 (geometric termination — a near-pass
  of gate 2!) before the churn resumed and killed it.
- First-0.5s window: 13 detections during the wash in each, mostly
  honest at +24..+41 deg (structure at extreme angle during crossing).
  The quiet window (N1) remains justified as relock hygiene, but it is
  NOT the killer.

**Re-ranking per the advisory's own rule** (real-gate chase =>
corridor/acquisition critical): **N2 (exit-vector banking + acquisition
gate: range in [banked +/- margin] ∩ [3,9]m, bearing cone +/-12 deg,
scale consistency, no chase on unconfirmed acquisition) is load-bearing
and first to build.** N1 (0.5s quiet window) ships with it (trivial).
N3 ribbon-follow stays gated on extended R1. The three rules stand: no
chase on unconfirmed acquisition; never outrun your ribbon; retrace
beats explore.

Open N-asks routed to analysis: N-R2 (extended R1 + A7), N-R3 (D7 +
banked-bearing error distribution — sets the cone), N-R4 (corridor
clearance statistic), N-R5 (gate-2 truth labels at crossing), A8
(fourth request — the 0.45 clamp still borrows 0.15m on faith).

## Pre-registered A/B endpoints (advisory 8 §1, before Block A flight 1)

- **Block A (phase6i, alternating six at 1.8)**: PRIMARY =
  non-inferiority of the |true_dz| crossing-dispersion distribution
  (live vs control) + zero TERM-attributable anomalies (sign-disarms,
  correction jitter, readiness-onset transients). SECONDARY = pass
  rate (n=3+3 cannot speak except at the maximal split; recorded, not
  concluded from).
- **Block B (correction capability, 2-4 flights, only after Block A)**:
  inject a +/-0.12m aim offset into the LEGACY aim only
  (--patch planner.approach.aim_up_m shifted by +/-0.12, alternating
  sign, pre-registered per flight). TERM-live must null to <=0.1m;
  control must express ~0.12m. The injected offset is one knob with
  known truth — it replaces restoring 2.5 m/s, which would move trim
  and re-open the oracle verification. AMENDED 0.20 -> 0.12 by the
  advisory-10 geometry ruling: +-0.20 exceeds C_contact = 0.18 (a
  commanded clip); 0.12 keeps ~2.4 sigma against the ~0.05 delivery
  noise, so the designed power survives.
- **The frame-package canary (pre-registered)**: when the honest
  adapter + source-frame migration lands and 2.5 m/s is restored, the
  retired ~0.25m residual must either be explained by the package or
  reappear on cue; its silent absence is itself a finding.

## S4 exit-maneuver design — ADOPTED (tank-2 answer to B2/B3)

Failure class re-named: successor-target ARBITRATION failure among
multiple valid gates. The fix is a one-way authority chain, not
detector scoring:

    pass event -> physically clear gate 1 -> choose ONE successor in a
    FROZEN exit frame -> latch -> acquire only inside its predicted
    tube -> hand THAT tracklet to the proven approach pipeline -> stop
    rather than switch while moving.

State machine: PASS_LATCH -> EXIT_CLEAR -> BANK_SELECT ->
BANK_BRIDGE -> TRANSIT_LOCKED (existing machinery), with BRAKE_SEARCH
on ambiguity/loss and retrace-not-explore escalation. The retired gate
never regains authority within the epoch.

Key decisions, verbatim-adopted:
1. **Clearance is DISTANCE-based** (s_lb integral of max(0, v_par -
   m_v) >= d_clear; 0.9m provisional until N-R4), time only a watchdog
   (0.8s -> brake/hold, never assume clearance). Frozen TRAVEL
   DIRECTION during EXIT_CLEAR (not frozen attitude). Suppress
   candidate AUTHORITY, not perception — tracklets accumulate in
   shadow through the wash.
2. **Bank selection: angularly nearest eligible tracklet to the
   FROZEN gate-1 exit vector** — never current heading (positive-
   feedback churn: slight turn toward A makes A nearest). Exit frame
   frozen at pass: x_E = exit vector (median of final ~0.15s travel),
   z_E = true up. Eligibility: robust range 3-12m, forward half-space,
   >=3 unique exposures over >=0.10s, bearing+scale continuity, not
   the retired track. Winner margin required; D7-band ties resolved by
   ribbon vote or BRAKE. Range is a plausibility gate, never sequence
   truth.
3. **Latch**: banked_candidate_id + epoch; while moving no re-ranking,
   no runner-up switch, no score-based steal. Released only by pass /
   termination / persistent-contradiction-then-full-stop / explicit
   retrace.
4. **Acquisition = predicted TUBE, not static cone**: bearing cone
   Q99(D7 bank-bearing error)+2deg, hard max +/-12 (if D7 needs more,
   kill the bank predictor, not the cap); range tube propagated
   R_pred(t) = R_B - s_par(t) ∩ [3,9]m; apparent-scale consistency
   l_pred ~ l_B * R_B/R_pred. NO widening while moving (uncertainty
   while moving reduces speed, never expands the candidate set);
   widening only during the stationary BRAKE_SEARCH sweep, sector
   centered on the banked exit-frame vector. No fresh promotion below
   3m.
5. **Bridge budget exists only after a candidate is banked** (no
   banked candidate at clear -> budget 0, brake). STOP-BY the cap
   (0.8s/0.8m, whichever first): brake when remaining budget equals
   pessimistic stopping distance. Bridge speed ~1.0 m/s, not the 1.8
   crossing speed. Candidate loss starts deceleration next cycle.
6. **Handoff to the EXACT banked tracklet only** (ID + epoch +
   continuity + tube + certificate + entry range); seed the approach
   controller, common slew limiter, retire the selector, no re-ranking
   until gate-2 pass/miss/reset. Post-handoff loss: existing approach
   rules; persistent loss -> hover, keep identity epoch, one bounded
   sweep, reacquire-or-retrace. Never the runner-up while moving.
7. **Ribbon: bounded tie-breaker only** in build 1 (chooses among
   D7-band ties; cannot bypass range/scale/persistence; zero-hijack
   doctrine). Promote to bounded score term only if D7 shows the true
   successor is ever not the angularly-nearest eligible tracklet.

Kill tests C1 (clearance), B1 (successor selection incl.
frozen-vs-current-heading A/B and adversarial ribbon), A1 (tube: the
-20deg/17m hop rejected by construction), L1 (bounded bridge), H1
(authority/handoff; try39 must replay as select-retain-handoff with
zero hops). Implementation order 1-8 as ranked (latch first, ribbon
seventh, adaptive search last).

THE RULE: uncertainty while moving reduces speed and eventually forces
a stop; it never expands the set of gates allowed to take control.

## Advisory-8B riders (acknowledged, pre-data)

- **Pattern book**: "any token that feeds a pre-registered endpoint
  must carry exactly one meaning — instrument ambiguity is conclusion
  ambiguity" (joins GATE_GEOM and frame ownership).
- **Cohort hygiene**: flights flown under the ambiguous instrument
  (phase6i F1/F2) are QUARANTINED from Block A's endpoint; the restart
  is a fresh cohort. The quarantined flights stay usable for anything
  not reading TermStatus.
- **A8 convention**: report max AND scatter of (0.8 - true_dz at
  contact) across the graze samples; the clamp recomputes from the
  MAX — clearance is a worst-case quantity, props flex.
- **Drop formats (so each lands one-pass analyzable)**: alternating
  six => per-flight TermStatus timeline + crossing vs post-hoc pixel
  truth + oracle residual binned by range (sigma library) + anomaly
  ledger. Successor-latch vs B1/H1 => per-trigger disposition table
  (accepted/rejected, clause fired, post-hoc 512 verdict) + formal
  closure of N0 (a)-(d) — the wash-seeded-fiction prediction stays
  open on the advisory board until (b) and (d) are answered, our 512
  refutation notwithstanding.

## Status-vocabulary pin + pre-registered D7/N-R4 interpretation (8C)

**Vocabulary mapping** (one meaning per token; current fields ->
pinned names): observer_ready = TermStatus.ready;
shadow_selected_owner = ShadowTerminal.owner (never adjudicates
treatment); applied_owner = TermStatus.owner; term_enable = the
explicit patch; term_command_applied = TermStatus.v_bz_applied is not
None. MISSING and queued for the next telemetry rider:
term_source_mode (oracle | hold | decay | neutral) on TermStatus.

**D7 pre-registered output** (P1 spec): error measured vs the FROZEN
exit vector; report per cone half-width {correct-gate recall,
wrong-real-gate admissions, MAX contiguous correct-target outage,
first-certification latency}; select the narrowest width with ZERO
wrong-gate admissions on the churn fixtures (recall loss acceptable —
uncertainty brakes, never switches); >12deg required => kill the
moving-bridge assumption, not the cap.

**N-R4 pre-registered output** (P2 spec): TWO quantities sized
independently — d_clear = rear envelope + turn sweep + structure
margin; d_bridge_max = min(0.8m, corridor_lower - d_clear -
d_stop_pess). Kill conditions => stationary post-clear acquisition:
d_bridge_max <= 0, or correct candidate cannot certify before stop-by
onset, or the pessimistic stop leaves the corridor. Either way the
authority chain is unchanged — the decision is mechanical, not
architectural.

**A8 expanded** (P4 spec): full envelope extraction — rearward extent,
rotor/body lateral sweep at bank onset, upper/lower/side contact
envelope, contact-timing uncertainty, minimum true clearance on the
SUCCESSFUL passes; combine graze labels with near-clearance
trajectories, never a single graze point. Sets the erosion margin and
the turn-sweep term of d_clear; clamp from the MAX.

**Alternating-six outcome set** (final): sim-declared pass rate,
vertical + lateral crossing dispersion, TERM active-ownership count,
readiness-WITHOUT-ownership count, source/provenance violations,
loss/handback anomalies. A TERM anomaly never triggers an
opportunistic S4 change; a post-pass chase belongs to exit-authority
analysis, not the gate-1 treatment outcome.

**B1 acceptance is SEQUENCE IDENTITY**: a build that picks a different
plausible gate and flies smoothly still FAILS. try39's counterfactual
is narrow: same real gate-2 track retained -> certificate handoff ->
existing approach continues.
