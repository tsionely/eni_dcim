# Think-tank ROUND-3 UPDATE pack

AGENTS.md DATA ANALYST item 5 (HEAD ≥ `84a9cdf`).
Order: **(f) Test A RERUN** → **(g) H3** → **(i) row-consistency** → **(h) T3**.

## Notes carried forward

1. REAL_GATE_CONSISTENT band (product 272–308) still carried the ty conflict; HEAD `scale_min=0.65` (floor ≈333) rejects it — analyst agrees; no counterexample frame with product<333 and verified-true pose found.
2. Prior Test A failure was d*=0.8 vs banner geometry; R4 d*_banner=0.15.

## (f) Test A RERUN — bar vs banner, R4-calibrated d*

- d*_bar = 0.8 m · d*_banner = 0.15 m (R4)
- Band: **1.5–2.4 m**. Identity: HEAD scale-gate kill ⇒ `banner_strip`.

### `20260716T203450-2ca531c3`
- n_bar=15 n_banner_strip=7

| bucket | n | median bias | P90 | sign acc | bars |
|---|---:|---:|---:|---:|---|
| overall | 22 | -1.440211682695421 | 1.5217893794253994 | 0.0 | med=False p90=False sign=False |
| top_bar | 15 | -1.5018244808081904 | 1.5217893794253994 | 0.0 | med=False p90=False sign=False |
| banner_strip | 7 | -1.301650838364998 | 1.405081617318377 | 0.0 | med=False p90=False sign=False |

### `20260716T212408-2ca531c3`
- n_bar=12 n_banner_strip=12

| bucket | n | median bias | P90 | sign acc | bars |
|---|---:|---:|---:|---:|---|
| overall | 24 | -0.4835700499005918 | 1.7548889509997574 | 0.5 | med=False p90=False sign=False |
| top_bar | 12 | 0.8191821081449959 | 0.8421482784849421 | 1.0 | med=False p90=False sign=True |
| banner_strip | 12 | -1.7274771163943017 | 1.7635636053702148 | 0.0 | med=False p90=False sign=False |


## (g) H3 — visible-edge census (last 1.5 m)

### `20260716T203450-2ca531c3`
- n_frames=6 dist_span=[0.3787644264371387, 1.491329368855941]
- presence_rates={'left': 0.0, 'right': 0.0, 'top': 0.0, 'bottom': 0.3333333333333333, 'banner': 0.0}
- first_seen (as range decreases)={'bottom': {'dist': 1.491329368855941, 't': 7.2851817}}
- transition_order=['bottom']
- V2={'last_structure': 'left', 'last_rates': {'left': 0.0, 'right': 0.0, 'top': 0.0, 'bottom': 0.0, 'banner': 0.0}, 'mean_ty_closest': -0.026010502385653438, 'banner_last_implies_HIGH': False, 'state_says_HIGH': False, 'v2_consistent': True}

### `20260716T212408-2ca531c3`
- ERROR: no states in last 1.5m

## (i) F2 ROW-CONSISTENCY

{
  "error": "no focus state near 1.67m"
}


## (h) T3 — F1 no-arm replay

{
  "fid": "20260716T203450-2ca531c3",
  "gap_entries": 1,
  "vetoes_at_entry": 1,
  "arms_at_entry": 0,
  "double_climb_violations": 0,
  "structurally_unreachable": true,
  "blind_age_s": 0.3,
  "blind_climb_bias": 0.1,
  "events_sample": [
    {
      "t": 7.5849864,
      "age": 0.306838432,
      "dist": 0.5913668934896334,
      "ty": -0.11611788821759761,
      "vz_cmd": -0.7233439640190078,
      "gap_bias": 0.0,
      "event": "gap_entry"
    }
  ],
  "verdict": "PASS \u2014 double climb structurally unreachable under no-arm rule"
}


## Deliverables

- `report.md`, `summary.json`
- `test_a_samples.csv`, `h3_f1.csv`, `h3_f2.csv`
- `frames/f2_row_consistency.jpg`
