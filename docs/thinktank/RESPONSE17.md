# RESPONSE 17 — Reconciliation brief: the two rulings conflict on one constant and one convention; flying disposition held conservative

Addressed to BOTH advisory channels. Tank-1 = the Advisory 9/10/11
chain; Tank-2 = the RESPONSE-12 disposition + signed A8 amendment just
received. Tank-2's ruling predates several events the other chain has
already ruled on (advisory-10 geometry deltas, advisory-11
ratifications, the cohort-2 wipeout + stop policy, the A8 contact-
validity collapse, the commit vertical damper). This brief puts every
open constant in one place, names the two collisions, and states what
flies meanwhile.

## 1. THE CONVENTION CLASH — the same 0.62 read two ways

- Tank-1 (advisory 10) read h=0.62 as the vertical HALF-extent against
  the half-opening d*=0.8: C_contact = 0.8 − 0.62 = **0.18**, and
  derived cmd_clamp = 0.18 − 0.06 − 0.02 = **0.10**.
- Tank-2 read 0.62 as the FULL top-to-bottom envelope against the full
  opening 1.60: M_contact = (1.60 − 0.62)/2 = **0.49**, and approved a
  controller clamp of **0.60** as controller-protection (explicitly
  NOT a collision boundary).

This is the exact d*-class confusion advisory-11 §1 warned about — now
BETWEEN the two channels. And beneath both readings: the analyst's
contact-validity audit (P2) found 3/11 of the graze samples used
far-state belief; the contact-valid extraction currently supports NO
value of h at all. Both derivations rest on a number in collapse.

**Resolution path (registered):** the A8 re-extraction (already
tasked) now absorbs Tank-2's spec — contact-instant states only,
r_top and r_bottom SEPARATELY (not their sum), the opening dimension
and extraction uncertainty published in ONE stated convention, minimum
n, both tails. When it lands, clamp/margins re-derive once, under both
signatures, with Tank-2's asymmetric M_top/M_bottom test replacing the
symmetric margin, and the A8-1..A8-5 fixture suite ships with that
build.

## 2. The clamp split — flying disposition

- **Measurement path — the tanks now CONVERGE and we adopt the
  stronger form at the next build boundary:** Tank-1 ratified an
  honest bound (0.45, must exceed the corridor); Tank-2 rules NO
  measurement clamp after the validity gates (identity + span×range),
  because clipping corrupts residual fitting and can dress an unsafe
  0.80 as a plausible 0.45/0.60. Adopted: the measurement clamp is
  REMOVED in the next build (post-cohort-3) — validity gates own
  plausibility, admission/safety see raw accepted values, R5 fits
  unclipped residuals. This is a flight-behavior change and does not
  enter the frozen cohort.
- **Controller clamp — CONFLICT, held at 0.10 while h is
  unsupported:** Tank-1 derived 0.10 from contact geometry; Tank-2
  approves 0.60 as controller protection. We hold **0.10** for the
  flying build, for three reasons: (i) it is coherent with the
  admission tube — an admitted arrival carries a mean ≤ 0.106 by
  construction, so the servo never legitimately needs more than
  ~0.1 m of correction authority inside the corridor's own contract;
  (ii) with h unsupported, 0.10 is conservative in the only direction
  that cannot license contact; (iii) swinging a safety constant 6×
  between two open rulings mid-campaign is exactly how d*-class
  errors propagate. Tank-2's replay/calibration concern (the
  0.45–0.60 region being truncated) is a MEASUREMENT-path concern and
  is fully answered by the clamp removal above, not by widening the
  command clamp. The 0.10-vs-0.60 question re-opens WITH the A8
  re-derivation, under the unified convention, where both channels
  sign one number.

## 3. Convergences — no action required

- **Corridor 0.30**: both channels keep it; the expiry collision
  (RESPONSE16 §3) stands — no execution while its target constant is
  in collapse and the sigma library is control-arm only.
- **T_tail**: both keep 0.45s base; T_tail = max(0.45, T_irrev,
  coverage-p95 0.50) already flying; A8 metre results explicitly do
  not touch the time constants (unit-collision pin queued per A8-4).
- **margin_m 0.55**: both channels retire it (already QUARANTINED in
  the derivation table); recomputes from the A8 re-extraction as
  M_top/M_bottom.
- **Freshness/timeout invariant**: Tank-2's required invariant is the
  already-ratified stop policy, verbatim — stale crossings cannot
  terminate or release authority; timeouts enter a bounded stop
  (brake-to-hover, stationary search, bounded inbound retrace); no
  global reacquisition opens while moving. The blind-travel bound
  Tank-2 asks for is stricter in the flying build than in the ruling:
  blind commit travel is capped at 0.6s of evidence age, not the
  full timer.
- **Constant renames with units** (T_TAIL_BASE_S vs metre clamps):
  adopted, next build boundary (a config-key rename mid-cohort would
  break the arms' param-hash comparability for no behavioral gain).

## 4. Riders queued into the metrology build (post-cohort-3)

Measurement-clamp removal; renames with units + A8-4 unit-collision
pin + A8-5 no-inheritance fixture; R5 dual recording (e_z_raw,
e_z_control, M_top/M_bottom, admission score, crossing residual,
contact/pass); the probation-tier door (advisory-11 §2 tier-2);
term_source_mode.

## 5. What flies

Cohort-3 (phase6l) on the damper build, unchanged — Tank-2's own
cohort rule legitimizes common-arm safety/identity corrections with
planner.terminal.enable as the sole treatment variable, and the
damper is exactly such a correction (P1-adjudicated, fixtured,
pre-registered). Single-owner architecture unchanged. R5 will record
the dual clamp values from the next build onward.
