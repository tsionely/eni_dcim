# RESPONSE 27 — Rate ruling received; interim retired; the anchor build order

Both channels adopted **(a) FULL_RATE_ANCHOR**, convergently and with
compatible amendments. Implemented immediately (178/178): the
advisory-15 interim retires with its voided evidence — the command
clamp returns to **symmetric ±0.10**, both injection signs legal, the
LOW-arrival-climbs fixture restored.

## The anchor build (next commit set, spec frozen from both rulings)

1. At a legal FULL→SIDE transition, LATCH {v_anchor, sigma_v_full,
   anchor exposure id/ts, epoch, fit quality}; transition additionally
   requires FULL rate mature + accepted + anchor age ≤ 0.12s.
2. **Freeze the measurement, not the physics**: active
   v_z = v_anchor + feed-forward of applied commanded Δv since the
   anchor (the `track_applied_vz` integrator moonlights as the feed —
   mandatory, not optional).
3. **Age grows from the last FULL exposure — SIDE never resets it**;
   sigma ages: σ_v(age) = √(σ_v_FULL² + (σ_a·age)²) with σ_a MEASURED
   from the harness column (truth-v vs frozen+feed-forward);
   pre-registered verdict gate: the option lives below σ_a ≈ 0.35,
   dies above (floor table on record). Age cap = T_tail, then the
   existing staleness decay — (c) is (a)'s automatic floor, nothing
   new to build.
4. **Provenance split**: position_source = SIDE_PAIR,
   rate_source = FULL_RATE_ANCHOR (+ anchor age/valid/invalidation
   telemetry) — no channel ambiguity.
5. **Falsification monitor**: SIDE positions vs the anchor's
   control-aware prediction; two consecutive unique-exposure breaches
   of the replay-earned envelope invalidate the anchor
   (before-no-return → hold/abort; after → neutral-decay). The shadow
   SIDE slope is a gross-contradiction detector only. Never a SIDE
   rate estimator by the back door.
6. FULL return upgrades via the registered 3-consistent rule,
   refreshing rate authority; no command discontinuity beyond one
   slew step.
7. Fixtures: R26-1..7 + the SAFETY (adversarial command sequence keeps
   the aged sigma honest), LIVENESS (**owner_term_side_rows > 0 on the
   F2 1.903m window** — the before/after metric), REGRESSION (S3
   trivially: no slope is fitted at all).

Cohort 4 holds until R26-1..7, ψ-age, telemetry, and the drift model
are green. The ladder's position row is already the best measurement
in the fleet; this build lends it the rate it lacked, priced by age.
