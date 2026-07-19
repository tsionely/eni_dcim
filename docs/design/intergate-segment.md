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
  inject a +/-0.20m aim offset into the LEGACY aim only
  (--patch planner.approach.aim_up_m shifted by +/-0.2, alternating
  sign, pre-registered per flight). TERM-live must null to <=0.1m;
  control must express ~0.2m. The injected offset is one knob with
  known truth — it replaces restoring 2.5 m/s, which would move trim
  and re-open the oracle verification.
- **The frame-package canary (pre-registered)**: when the honest
  adapter + source-frame migration lands and 2.5 m/s is restored, the
  retired ~0.25m residual must either be explained by the package or
  reappear on cue; its silent absence is itself a finding.
