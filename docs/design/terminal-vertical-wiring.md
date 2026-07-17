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

## Advisory-5 amendments (aperture question)

- **Branch question OPEN, leaning B**: if banner-bottom is truly +0.15
  above the OPENING CENTER (branch A), the flyable aperture is
  [-0.8, +0.15] (center z_ap=-0.325, margin ±0.33) and aim_up=+0.25
  aims INTO the banner. M1 re-scoring (all six phase5c/5d terminal
  arrivals, honest last fixes): ty(center) -0.66..-1.29, ty(aperture)
  -0.34..-0.96 — ALL still low-of-aperture, the branch-A prediction
  (">=half inside") FAILS => evidence for branch B (reference slip in
  the R4 measurement; suspected cause: opening_cy_px taken from the
  banner-merged quad center, displaced upward). A6(i) re-measurement
  decides; NO aim re-base until it does. Robust-to-branch facts: the
  LOW arrivals are real, and closed-loop is arithmetically mandatory
  (blind drift 0.76 vs margin <=0.4 either way).
- **Certificate invariant 6 (edge identity routing), folded into C1
  BEFORE implementation**: (6a) a horizontal top-region edge whose
  support extends laterally beyond the certified side-bar lines is the
  BANNER BOTTOM (constants: banner width / h_b); one terminating at
  them is the top inner edge. (6b) a vertical edge supported entirely
  above the banner-bottom row is a banner side edge — rejected from
  the pair. New impostor class this kills: the banner's own vertical
  edges (separation ratio 2.0/1.6=1.25 — INSIDE the [0.65,1.5] scale
  gate; the separation check cannot catch it; 6b + bar-ness (A4) are
  the executioners).
- **GATE_GEOM single source of truth**: all gate geometry constants
  (opening size, bar width, banner h_b + width, aperture bounds, drone
  vertical half-extent, ribbon height when measured) live in ONE
  config block (perception.gate.*) consumed by tracker, certificate,
  V2 tables and planner aim — the d*-routing bug class dies there.
  Populated as measurements land (A4/A6/A7/A8); branch-conditional
  entries marked.

## Release-contract tightenings (tank-2 review, adopted)

Verdict accepted: approved for SHADOW integration only; TERM actuation
stays blocked until the identity certificate passes FA=0 and the full
replay suite is green.

1. **Provenance** (per their audit requirement):
   - src/aigp/planning/vertical_terminal.py — oracle/guidance; test:
     `python -m pytest tests/unit/test_vertical_terminal.py` (20 tests).
   - src/aigp/planning/vertical_owner.py — arbiter/limiter/adapter;
     test: `python -m pytest tests/unit/test_vertical_owner.py` (9).
   - Hashes = the repo commit history on origin/main (each commit
     message documents the change; current tip recorded per push).
2. **FREEZE semantics fixed in code**: compute_terminal_guidance now
   returns vz_cmd=None in freeze — the ADAPTER holds the previously
   APPLIED world-up target and recomputes body-z through attitude each
   tick. 0.0 invited misuse.
3. **Epoch-bound identity**: every terminal observation will carry
   exposure id/ts, gate-lock epoch, certificate epoch, mode,
   covariance, de-rotation timestamp. A relock revokes the
   certificate; below the ~1.4m floor a revoked certificate can only
   continue via inheritance/probation, never fresh promotion.
4. **Row-only 0.5 factor scoped**: scales terminal speed/slew limits
   ONLY — never e_z, tau, covariance, crossing error, or the envelope.
5. **Grace clamp**: clamp(0.25·max(tau_eff_at_loss,0), 0, 0.12s);
   after persistent loss in position the planner FIRST leaves forward
   commit into retreat, only then bumpless ALT handback (atomic order).
6. **Saturation priority refined**: preserve feasible vertical AND
   lateral corridor corrections; reduce pass-axis forward speed first;
   safety/telemetry always uses the ACHIEVED world-up component.
7. **Calibration sign pinned**: bias = median(e_oracle − e_reference);
   d_star_release = d_star_nominal + bias (the measured +0.82 raises
   d_star by ~0.82). Sign unit test ships with the calibration.
8. **One ownership transition per tick**, fixed priority: pass/
   termination > hard failure > persistent-loss retreat > new capture
   (the arbiter satisfies this by construction — handback returns
   before any capture check; pinned by test).
9. **Ship order updated — SHADOW WIRING MOVES UP**: wire owner +
   limiter + adapter into the planner in non-actuating shadow mode
   next (TERM decision and final body command computed and logged on
   every replay; applied command asserted bit-for-bit identical to
   legacy). Only the enable bit waits for the certificate.

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
