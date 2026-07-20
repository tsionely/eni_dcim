# L1 Full Addendum + Sigma Harvest

Date: 2026-07-20

Role: QA & MOCK-TUNER. Scope stayed recorded-video replay only; no
FlightSim/DCGame was launched, reset, clicked, or commanded.

Source under test: `2aa8b9c385982be5f82d18e9d0bec11abe82f09c`.

Primary artifact:
`tuning/l1-full-addendum-2aa8b9c-2aa8b9c-20260720T092333Z/summary.md`

Harness note: the replay now reads/emits both terminal feature topics:
`feature` for FULL/tracker-primary rows and `feature_side` for the parallel
SIDE_PAIR rung. The shadow replay observes both topics but only `feature`
contributes arbiter healthy-exposure streaks, matching the app wire.

## Result

Partial pass / addendum NO-PASS.

What is fixed:
- Parallel side production is visible in replay.
- Primary F2/F4 produced `30` `feature_side` rows.
- The 29-recording sweep produced `244` `feature_side` rows.
- Earned sigma overlap volume is now real: `202` sweep overlap pairs.
- S5 dropout now produces legal full->side transitions.

What is still not passing:
- F4 did not produce a legal full->side transition.
- No run held `shadow_owner == term` through active `SIDE_PAIR`.
- The full shadow-capture conjunction therefore remains NO-PASS.

## Transition Findings

Primary F2/F4:
- F2 `drop_full_below_2p0m`: FULL_QUAD -> SIDE_PAIR at `R=1.649m`,
  `paired_overlap_count=8`, `overlap_delta_median=-0.043m`,
  `jump_grace_consumed=False`, `sigma_induced_abort_after=True`.
- F4: no legal transition observed.

29-recording sweep:
- Total transition rows: `13`.
- `drop_full_below_2p0m`: `6` FULL_QUAD -> SIDE_PAIR and `3` SIDE_PAIR -> FULL_QUAD.
- `drop_full_below_1p5m`: `2` FULL_QUAD -> SIDE_PAIR and `2` SIDE_PAIR -> FULL_QUAD.

S5 readiness did survive side-rung transitions. Examples:
- F2 `drop_full_below_2p0m`: `18` ready rows and 1 legal transition.
- `20260719T160537-f170ead6` `drop_full_below_2p0m`: `62` ready rows and 1 legal transition.
- `20260719T163649-f170ead6` `drop_full_below_2p0m`: `119` ready rows and 2 transitions.
- `20260719T201851-50f9dcc8` `drop_full_below_2p0m`: `92` ready rows and 2 transitions.

## Earned Sigma

Primary F2/F4:
- all ranges: `n=22`, `sigma_e=0.058m`, `sigma_v=0.515m/s`.
- 2.0-2.5m: `n=5`, `sigma_e=0.020m`, `sigma_v=0.795m/s`.
- 1.5-2.0m: `n=3`, `sigma_e=0.027m`, `sigma_v=0.451m/s`.
- 1.0-1.5m: `n=2`, `sigma_e=0.008m`, `sigma_v=n/a`.

29-recording sweep:
- all ranges: `n=202`, `sigma_e=0.038m`, `sigma_v=0.294m/s`.
- 2.0-2.5m: `n=39`, `sigma_e=0.012m`, `sigma_v=0.311m/s`.
- 1.5-2.0m: `n=29`, `sigma_e=0.057m`, `sigma_v=0.412m/s`.
- 1.0-1.5m: `n=17`, `sigma_e=0.050m`, `sigma_v=0.671m/s`.
- 0.5-1.0m: `n=5`, `sigma_e=0.039m`, `sigma_v=0.895m/s`.

## Shadow Capture

Valid shadow-capture rows still occur:
- F2 baseline: `2` rows, first at `R=1.903m`, min score `0.221`.
- `20260719T201851-50f9dcc8` baseline: `6` rows, first at `R=1.268m`.
- `20260720T062804-c38fd469` baseline: `11` rows, first at `R=1.317m`.

But these captures occur while the active source remains FULL_QUAD. The legal
SIDE_PAIR transitions appear in dropout sweeps, where first-capture admission
is no longer satisfied or sigma-induced abort is flagged. That is the remaining
gap between "side rung is alive" and the full addendum conjunction.
