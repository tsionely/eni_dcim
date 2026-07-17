# Terminal vertical channel — merged design (think-tank round 4)

The two round-4 answers compose into one work item. This doc pins the
decisions so the multi-stage build has a stable reference. Sources:
tank #1's side-pair certificate (advisory 4) and tank #2's override
arbitration spec; both validated against our flight data.

## Architecture rule (verbatim, adopted)

    one terminal estimate -> one terminal vertical controller ->
    one world-up velocity target -> one common limiter ->
    one attitude-aware body-frame conversion

No legacy vertical term (aim_up / altitude hold / sink insurance) runs
in parallel while the terminal channel owns. The open-loop patch line
(insurance -> veto -> top-up) is formally closed.

## Components and status

| Component | Source | Status |
|---|---|---|
| Scale-normalized oracle, crossing forecast, velocity-closure, phase schedule, robust 1/span TTC | vertical_terminal.py | DONE, tested (121-suite) |
| Robust current-time TTC intercept | ours; tank #2 adopted it back | DONE |
| Single-owner arbiter (capture conditions, no-return latch), asymmetric slew, bumpless trim, attitude-correct body-z adapter with conditioning guard | vertical_owner.py | DONE (pure functions + state machine, tested) |
| Side-pair certificate: inheritance from last fully-gated quad, 5 invariants (chain / pair scale / bar-ness+width / support+polarity / expansion probe), CERTIFIED-PROBATION-NONE, terminal no-fresh-certification below ~1.4m | tank #1 §2 | NEXT: implement inside GateCloseTracker |
| y_T/l_T extraction with verified identity + exposure-time de-rotation to the pass frame | tracker identity stage | NEXT (same work item) |
| Planner wiring: commit vertical terms switched by the arbiter; TERM path = compute_terminal_guidance -> vz goal -> common limiter -> body_z_for_world_up | race_planner + app | AFTER certificate |
| c_i-as-state (trust = variance of per-source scale), model-speed anchor | tank #1 §4, T1 plane filter | LATER (with T1) |
| Ribbon vertical reference (V1) | gated on R1 measurement (analyst, top priority) | PENDING DATA |

## Key rules pinned

1. Capture ALT->TERM: commit active + same locked gate + CERTIFIED
   structure + 3 consecutive healthy UNIQUE exposures + feature age
   <=0.10s + phase still "position". Never a first capture in
   damping/freeze.
2. While TERM owns: aim_up = altitude hold = sink insurance = 0.
   Insurance must never veto a terminal-requested descent.
3. No-return latch: after damping under TERM, no handback until gate
   passed / retreat complete / attempt terminated.
4. BAR_FULL -> BAR_ROW_ONLY is a measurement-model change, not an
   ownership change (same filter state; row-only uses PROJECTIVE depth,
   never slant range; reduced authority factor 0.5 initial).
5. Loss grace: min(0.12s, 0.25*tau_eff at loss); after grace in
   position -> abort+handback; in damping/freeze -> stay latched.
6. Adapter: velocity interface (never integrate az); FREEZE holds the
   WORLD-UP target and recomputes body-z through attitude every tick;
   |u_B[2]| >= 0.5 conditioning guard; saturation reduces horizontal
   first and preserves world-up; infeasible => vertical_authority_
   limited, never "safe" from an unattainable command.
7. Bumpless transfer: trim b0 = prev_applied - new_raw, decayed under
   slew budget, NEVER decayed while saturated; inactive controller in
   tracking/anti-windup mode.
8. d* calibration: absorb the measured pure offset (F2 +0.82 signature)
   into d_star via leave-one-flight-out fitting — never a downstream
   command bias. High-overfly and clean-pass recordings stay in the
   release regression set (a low-only set cannot kill an always-push-up
   defect).

## Kill-test suite (offline, before any flight with TERM active)

Tank #1 suite: FA=0 on the three adversarial segments (A1 manifest),
availability >=95% of last-2m in-frame frames, promotion latency
<=0.2s with CERTIFIED by >=1.6m, leave-one-out ablation matrix.
Tank #2 suite: A (exclusive-vs-blend shadow replay), B (adapter
invariant |u.Rv - vz| < 1e-3 over the braking envelope), C (full-span
to row-only degradation), D (dropout/handback sweep, no owner chatter,
no phase regression), E (bumpless assertions incl. hidden-trim), F
(authority/saturation with a pessimistic fitted response model), G
(TTC final-sample corruption), H (leave-one-flight-out calibration +
low/high/clean directional regression).
