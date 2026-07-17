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
- n_frames=18 dist_span=[0.030753529518360436, 1.491329368855941]
- presence_rates={'left': 0.8888888888888888, 'right': 0.3333333333333333, 'top': 0.05555555555555555, 'bottom': 0.9444444444444444, 'banner': 0.0}
- first_seen (as range decreases)={'left': {'dist': 1.491329368855941, 't': 7.2851817}, 'right': {'dist': 1.491329368855941, 't': 7.2851817}, 'bottom': {'dist': 1.491329368855941, 't': 7.2851817}, 'top': {'dist': 1.4759550720632861, 't': 8.3050928}}
- range_source=state_le_1.5
- transition_order_far_to_near=['left', 'right', 'bottom', 'top']
- V2={'last_structure': 'left', 'last_rates': {'left': 1.0, 'right': 0.0, 'top': 0.0, 'bottom': 0.6666666666666666, 'banner': 0.0}, 'mean_ty_closest': 0.01687836914526738, 'banner_last_implies_HIGH': False, 'state_says_HIGH': False, 'v2_consistent': True}

### `20260716T212408-2ca531c3`
- n_frames=7 dist_span=[2.101851633717449, 3.474403492539824]
- presence_rates={'left': 0.8571428571428571, 'right': 0.7142857142857143, 'top': 0.5714285714285714, 'bottom': 1.0, 'banner': 0.5714285714285714}
- first_seen (as range decreases)={'left': {'dist': 3.474403492539824, 't': 7.1231878}, 'bottom': {'dist': 3.474403492539824, 't': 7.1231878}, 'right': {'dist': 3.016355058341858, 't': 7.2429549}, 'banner': {'dist': 3.016355058341858, 't': 7.2429549}, 'top': {'dist': 2.782110095002108, 't': 7.3034683}}
- range_source=state_closest_span
- transition_order_far_to_near=['left', 'bottom', 'right', 'banner', 'top']
- V2={'last_structure': 'left', 'last_rates': {'left': 1.0, 'right': 1.0, 'top': 1.0, 'bottom': 1.0, 'banner': 0.0}, 'mean_ty_closest': 0.30017314422002367, 'banner_last_implies_HIGH': False, 'state_says_HIGH': True, 'v2_consistent': True}


## (i) F2 ROW-CONSISTENCY

{
  "t": 7.3028322,
  "dist_det": 1.672659584462913,
  "dist_state": 2.782110095002108,
  "age_state": 0.722866488,
  "ty_believed": 0.31383880041187073,
  "tz_believed_state": 2.75751263904207,
  "ty_det": -0.9446242102185011,
  "tz_det": 1.378104088023288,
  "row_believed_at_det_depth": 252.87433293652745,
  "row_believed_state_pose": 216.41992958069864,
  "row_if_det_ty": -39.34464159634089,
  "row_mask_mid": 182.5,
  "row_quad_center": 123.25,
  "row_ref_used": 123.25,
  "disagree_px_believed_at_1_67": 129.62433293652745,
  "disagree_px_believed_state": 93.16992958069864,
  "disagree_px_det": 162.5946415963409,
  "better_match": "believed_ty",
  "verdict": "BELIEVED_ROW_DISAGREES",
  "frame": "frames\\f2_row_consistency.jpg",
  "vision": "C:\\Users\\tsion\\Projects\\eni_dcim_phase1\\logs\\20260716T212408-2ca531c3\\vision.aigprec",
  "note": "STATE at conflict is ~2.78m DR while det R=1.67m; believed ty=+0.31 at det depth predicts an opening-center row the actual mask/quad violently disagrees with if the image matches det ty=-0.95 (pairs with D5 product\u226a512)."
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
