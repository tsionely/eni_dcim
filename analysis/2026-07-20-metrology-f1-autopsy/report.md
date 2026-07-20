# Metrology-f1 cluster failure autopsy

RESPONSE35 §3 — flight `20260720T133443-9aa0ef5c` vs twin `20260720T071220-5b501b4c`.

## WHERE_USABILITY_DIED: **SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP**

**RESCUABLE: False** — does not add a 7th harvest cluster.

All 11 FULL<=3.5 certified rows die at e_reject=scale_gate. Span is ~1/3 of fx*W/Z at the reported range_z (same visual structure later reappears at ~10 m with e_reject=ok). center_x~510–513 (right edge), |x|~3.5–4.5 m, gate_age~1.2–1.5 s, phase=recover after a FULL gap filled only by SIDE_PAIR_ROW_ONLY/none. Certification was earned above the 1.6 m promote floor; usability died at the scale gate on flipped/far-gate quads — not harness over-reject of honest e_z. Twin 071220 shows the same kill (1 FULL<=3.5, scale_gate, then ~9 m). Not rescuable as a 7th cluster.

## Stage-by-stage (11 FULL certified ≤3.5 m)

| # | frame | t_rel | range_z | span | span/E[span] | center_x | |x| | age_s | e_reject | kill |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 1 | 274 | 5.729 | 3.483 | 49.0 | 0.33 | 512 | 3.76 | 1.17 | scale_gate | scale_gate |
| 2 | 275 | 5.764 | 3.417 | 54.5 | 0.36 | 512 | 3.84 | 1.20 | scale_gate | scale_gate |
| 3 | 276 | 5.789 | 3.382 | 50.2 | 0.33 | 513 | 3.88 | 1.22 | scale_gate | scale_gate |
| 4 | 277 | 5.826 | 3.314 | 55.1 | 0.36 | 512 | 3.97 | 1.26 | scale_gate | scale_gate |
| 5 | 278 | 5.864 | 3.249 | 54.1 | 0.34 | 512 | 4.05 | 1.29 | scale_gate | scale_gate |
| 6 | 279 | 5.897 | 3.166 | 51.0 | 0.32 | 514 | 4.16 | 1.34 | scale_gate | scale_gate |
| 7 | 280 | 5.930 | 3.125 | 55.1 | 0.34 | 512 | 4.22 | 1.36 | scale_gate | scale_gate |
| 8 | 281 | 5.960 | 3.077 | 59.2 | 0.36 | 510 | 4.29 | 1.39 | scale_gate | scale_gate |
| 9 | 282 | 5.992 | 3.020 | 56.2 | 0.33 | 511 | 4.38 | 1.42 | scale_gate | scale_gate |
| 10 | 283 | 6.028 | 2.965 | 54.1 | 0.31 | 511 | 4.47 | 1.46 | scale_gate | scale_gate |
| 11 | 284 | 6.062 | 2.911 | 54.2 | 0.31 | 510 | 4.55 | 1.49 | scale_gate | scale_gate |

### Stage pass counts

- FULL_QUAD + certified + range≤3.5: **11**
- e_reject==ok (e_z-usable): **0**
- kill_stage: `{"scale_gate": 11}`

## Twin 071220

- FULL certified ≤3.5: **1**, e_z-usable: **0**, kill: `{"scale_gate": 1}`
- Same mechanism: **True**

## Ruled-out hypotheses

- Promote-floor (1.6 m) never-certify: **no** — all 11 certified with range_z ≥ 2.91 m.
- Bloom washing red so cert never fires: **no** — det_cert/cert stay certified; span is simply too small for the *reported* near range (far-gate geometry).
- Harness over-reject of honest e_z: **no** — scale_gate is the correct refusal of flipped-range quads (later frames of the same blob settle at ~10 m with ok).
- Mid-approach relock clearing identity: **partial context** — recover after FULL gap + SIDE_ROW_ONLY/none + stale gate_age; identity that *does* return is a lateral far gate, not a rescued near opening.

## Deliverables

- `rejection_table_f1.csv`
- `rejection_table_twin_071220.csv`
- `summary.json`

