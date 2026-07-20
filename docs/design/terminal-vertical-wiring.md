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
8. d* calibration: absorb the measured pure offset into d_star via
   leave-one-flight-out fitting — never a downstream command bias.
   High-overfly and clean-pass recordings stay in the release
   regression set (a low-only set cannot kill an always-push-up
   defect).
   **QUARANTINE (round-5, both tanks):** the original "F2 +0.82
   signature" was measured while every vertical interpretation lived in
   the tilted rest frame (the phantom). It may contain the frame-tilt
   range term, lever-arm geometry, top-bar identity bias, banner
   substitution, and a smaller true constant — in unknown proportions.
   It is NOT carried into release. d* is re-fitted from scratch on
   corrected-frame replays only, after the frame-fix release gates
   (range-slope |b| < 0.03 m/m, pad-geometry agreement, F2
   counterfactual ~0) pass. Subtracting the phantom once through the
   frame transform and again through d* is the double-compensation
   class this note exists to prevent. The terminal sigmas (currently
   scalar 0.10/0.15) are likewise re-measured in the true frame at
   that point — a corrected mean with a tilted-frame sigma leaves the
   |mu|+k*sigma envelope internally inconsistent.

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

## Round-5 field disposition (tank-2) — adopted decisions

THE LAW (highest-impact policy of the round): a gate attempt must not
become irrevocable before the sensing mode needed to finish it has
been certified. The terminal controller is never asked to rescue an
attempt that began without terminal observability.

1. **Commit-permission gate** (plumbing next build, behind
   planner.commit.require_terminal_ready, default false until the V3
   counterfactual passes): new commit entry requires frame package
   accepted + same lock epoch + structure CERTIFIED before the
   late-capture boundary + latest unique feature age <= 0.10s + owner
   capture permitted + crossing tube inside the usable opening + no
   vertical-authority limitation. If unmet while holding/retreat is
   still safe: decelerate, hold acquisition distance, keep certifying.
   V3 release bar: F1 (healthy certificate) must NOT be blocked; F3
   must NOT enter its unobservable commit; no readiness chatter; no
   capture from rebroadcast copies; no late first capture.
2. **Frame-package acceptance replay**: rotated-basis, INTEGRATED —
   compares estimator outputs, discrete planner transitions,
   vertical-controller state incl. integrals/init, body commands, and
   abort decisions after re-expression to one physical frame. Bar:
   identical discrete transitions + command agreement within fp/test
   tolerance. (The gravity-only A/B is the failure this must catch.)
3. **Terminal sigmas**: scalar is adequate this release, but
   stratified by mode and age — FULL / ROW_ONLY / RATE_ONLY / LOST —
   never one sigma for all conditions. Fit in the corrected frame.
4. **Feature ladder** (one estimator, graceful degradation, never a
   second controller): STRUCTURE_METRIC (side-pair range + top-bar
   row, or full row/span) -> VERTICAL_PAIR (certified top bar +
   certified banner-bottom: Z = (d_T - d_B)/(y_T - y_B), closed form
   as replay oracle only; separate corrected-frame d_star_top and
   d_star_banner; coplanarity verified; zero identity swaps = release
   requirement) -> ROW_WITH_RANGE -> RATE_ONLY -> LOST (bounded
   prediction + no-return salvage). Border-clipped span is never
   metric scale.
5. **F3 autopsy decides the branch** (before any controller tuning):
   Case A (structure in image, software reports no fix) -> identity/
   tracker fixes, do NOT touch blind-coast limits. Case B (structure
   truly leaves the image) -> visibility-preserving braking (earlier,
   lower pitch demand; predicted top-bar/banner row constrained to a
   usable band; NO late pitch-up pulse) — slower speed at the same
   loss range only lengthens the blind interval. Case C (vertical
   survives, miss was lateral) -> vertical channel necessary but
   insufficient; a surviving side bar supplies a one-sided lateral
   constraint.
6. **Kill tests V1-V6** adopted verbatim: raw-vs-software visibility
   (>5% usable-structure-reported-LOST kills enable), axis-of-miss
   decomposition, commit-permission counterfactual, identity
   inheritance under artificial occlusion (any confident structural
   swap kills), counterfactual braking visibility (ship only if raw
   feature loss is materially delayed without worse passage error),
   post-miss atomic reset (rejecting a fiction measurement is
   insufficient if a command derived from it keeps executing).
7. **Ship order**: (1) integrated acceptance replay; (2) F3
   raw-visibility + axis-of-miss timeline; (3) projected identity
   stage + terminal-ready commit gate; (4) banner-bottom sibling
   measurement; (5) d*/sigma refit in corrected frame; (6) full-stack
   TERM shadow replay low/high/clean/F1-F3; (7) enable TERM at
   conservative speed after the suite passes; (8) if raw structure
   truly leaves the image, change braking geometry before adding dead
   reckoning.

## Ratified admission horizon + the honest-measurement gates (2026-07-20)

Both advisories ruled independently and identically on the sigma-horizon
ratification request: **approved in structure — and the MEAN must ride
the same uncorrected tail as the sigma** (a full-tau ballistic mean with
a benign 0.08 m/s measured rate consumes the whole 0.106m budget; the
third mock A/B proved it: engaged+ready 9/10 around 2.47m, owner=term
0/10). Corridor 0.30 stays (geometry vs epistemology — never trade the
two currencies); 0.42 rejected; position-only admission rejected as sole
criterion.

Implemented (this commit set):
- `h_tail = min(tau_eff, t_tail_s)` rides BOTH mean and sigma;
  `t_tail_s = max(0.45 damping+freeze, T_irrev)` with
  `T_irrev = abort_min_dist_m / commit_speed` — the no-return tail from
  the planner's own no-retreat band, so a loss after retreat stops being
  possible is never priced with the healthy-loop horizon.
- Liveness + safety unit fixtures per the pattern-book rule ("every
  guard ships with a liveness fixture as well as a safety fixture").

**The §3 coverage crux — answered from the real fixtures** (cert status
vs range, phase6i-R six + phase6h): certification does NOT die at 1.8m;
it THINS (50-65% per 0.2m bin below 2.25m) and holds to 0.6-0.9m on
every pass. Measured coverage tail on passes: 0.33-0.5s => T_u=0.45
stands on evidence (green branch). The cert=none finding was a
definitional split: per-bin presence vs per-tick continuity.

**Close-range measurement fiction (new, real-fixture evidence)**: three
1.8-cohort flights fed the oracle certified BAR_FULL quads whose span
implied ~5m while the believed gate stood <1.2m — the successor gate,
crisp behind the wash, wearing gate-1's certificate; e_meas pegged the
clamp and admission (rightly) refused two centered passes. Fix: the
honest-detection scale test (512 px.m, band 300-800) now guards the
oracle's front door — span and believed range must agree before a row
becomes metrology. Offline census after the gate: F4 still admits at
1.32m; the fiction rows (7/4/4 per flight) are refused at the door.
Remaining close-range coverage breadth is the e_z LADDER work item
(advisory-7 item 4) — robustness, not a live-treatment blocker.

**Mock-domain trim fiction (voids all mock owner=term verdicts)**: the
mock vehicle flies -20..-31 deg dynamic pitch at 1.8 m/s where the real
sim flies ~-1 deg; the trim compensation (calibrated on real graze data,
pitch_cal=-0.33) injects ~-2.2m into mock e_meas, pegging the clamp.
Mock A/B can therefore never exercise capture as-is. QA harness rule:
mock terminal arms must carry a MOCK-DOMAIN pitch_cal (calibrated from
mock commit logs) as a base patch in BOTH arms; it is a calibration
constant of the domain, never a treatment variable. Real-domain liveness
evidence stands on F4 (capture 1.32m, 28 owned ticks, pass).
