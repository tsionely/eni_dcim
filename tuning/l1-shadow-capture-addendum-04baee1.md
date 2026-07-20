# L1 Shadow Capture Addendum Verdict

Date: 2026-07-20

Role: QA & MOCK-TUNER. Scope stayed mock/replay only; no FlightSim/DCGame was
launched, reset, clicked, or commanded.

Source under test: `04baee11e3d42d1519e718ce3c11d17e2577ee31`.
Repo HEAD while running: `4732d84fe79c834bf75666c8d72b02769a654b3c`.
Non-tuning delta from `04baee1`: none.

Primary artifact:
`tuning/l1-shadow-capture-04baee1-4732d84-20260720T085525Z/summary.md`

## Result

NO-PASS for the addendum gate.

The liveness bar was measured as shadow capture, not readiness:
`observer_ready && admission_score <= 0.30 && shadow_owner == term &&
shadow_phase == position && valid source provenance`.

F2 did produce a valid first shadow capture:
- sweep `baseline`: first capture at range `1.903m`, source `FULL_QUAD`,
  min admission score `0.221`, `1` capture row by `2.2m`.
- sweep `drop_all_0p16s_after_first_below_2m`: first capture at range
  `1.064m`, source `FULL_QUAD`, min admission score `0.266`, `2` capture
  rows by `2.2m`.

The addendum still fails because no replay produced a legal full->side source
transition. Therefore there are no per-switch transition fields to report:
`paired_overlap_count`, `overlap_delta_median`, and `jump_grace_consumed` have
no rows in `shadow_source_transitions.csv`.

## Blocker

The current video-derived feature stream does not provide enough legal
SIDE_PAIR evidence to mature the side rung after FULL goes stale.

F2/F4/F6 default replay:
- F2: `7` SIDE_PAIR rows, only `1` certified metric row; `0` transitions.
- F4: `1` SIDE_PAIR row, `0` certified metric rows; `0` transitions.
- F6: `1` SIDE_PAIR row, `0` certified metric rows; `0` transitions.

I also scanned 29 recent phase6h-phase6l recordings as candidates. The closest
one was `20260719T201851-50f9dcc8`: current perception produced `24` SIDE_PAIR
rows, `3` certified SIDE_PAIR rows, and `5` shadow-capture rows, but still
`0` full->side transitions. That confirms the blocker is the ladder transition
evidence requirement, not just the F2/F4 fixture choice.

## Notes

An exploratory runtime close-tracker sensitivity run made F2 produce three
certified SIDE_PAIR rows, but still did not reach the oracle's legal switch
bar: six contiguous side samples over at least `0.15s` plus valid overlap gate.
I did not ship that patched artifact as the primary result because the
addendum requested commit `04baee1` behavior.
