# ROUND-4 / advisory-4 measurement pack

AGENTS.md DATA ANALYST item 6 (HEAD ≥ `0cbb682`).
Priority: **(A2/R1)** → (A1) → (A4) → (A5).

## (A2/R1) Cyan-ribbon availability in last 2 m

Horizon row = `180 + 320·tan(11°+pitch)`. Offset = cyan_mean_row − horizon (negative ⇒ cyan ABOVE horizon in the image). LOW-geometry prediction: ≈ −30 px.

| phase | flight | n | cyan% | above% | med offset px | ~+30 above? | V1≥60% |
|---|---|---:|---:|---:|---:|---|---|
| phase5c | F1 | 73 | 56.2 | 7.317073170731708 | 54.069835647185414 | False | False |
| phase5c | F2 | 21 | 71.4 | 0.0 | 113.97298272870799 | False | True |
| phase5c | F3 | 37 | 89.2 | 0.0 | 106.3402212397751 | False | True |
| phase5d | F1 | 35 | 60.0 | 71.42857142857143 | -62.3090463356495 | False | True |
| phase5d | F2 | 70 | 41.4 | 0.0 | 120.07982214135396 | False | False |
| phase5d | F3 | 52 | 23.1 | 0.0 | 111.58123065267883 | False | False |

**Aggregate cyan presence (per-flight mean):** 56.9% over 6 flights.
**Flights clearing V1 ≥60% bar:** 3/6.

## (A1) Standing FA=0 adversarial suite

### A1-banner-fiction-F2
- F2 banner-fiction / scale-inconsistent lock (D5 garbage)
- flight: `20260716T212408-2ca531c3`
- t_range_s: [7.0, 7.5]
- source: `C:\Users\tsion\Projects\eni_dcim_phase1\logs\20260716T212408-2ca531c3\vision.aigprec`
- frame_id range: 221 … 235 (n=15)
- FA=0 expectation: certificate / scale-gate must REJECT all poses in this window

### A1-phase5d-F2-post-retreat-ceiling
- phase5d F2 post-retreat ceiling / upper-truss view
- flight: `20260717T102007-7223cc0c`
- t_range_s: [7.8042713, 11.3042713]
- source: `C:\Users\tsion\Projects\eni_dcim_github\fixtures\20260717T102447-phase5d-vertical\20260717T102007-7223cc0c_takeoff_to_end.aigprec`
- frame_id range: 313 … 417 (n=105)
- FA=0 expectation: no CERTIFIED gate pose while looking at ceiling

### A1-phase5b-F3-next-gate-steal
- phase5b F3 next-gate-steal through near opening
- flight: `20260717T091239-debf3ec1`
- t_range_s: [6.9, 7.3]
- source: `C:\Users\tsion\Projects\eni_dcim_github\fixtures\20260717T092008-phase5b-confirm\20260717T091239-debf3ec1_takeoff_to_end.aigprec`
- frame_id range: 290 … 301 (n=12)
- FA=0 expectation: near-gate ownership / prediction-consistent boost must win; far-gate pose must not be CERTIFIED as the active target

## (A4) Physical bar width `w_bar`

```json
{
  "fid": "20260717T100017-a560c093",
  "phase": "phase5c",
  "flight": "F3",
  "t": 12.4667432,
  "R": 19.881523445406145,
  "ty": -8.082692489903557,
  "quad_width_px": 29.154759474226502,
  "quad_height_px": 23.53720459187964,
  "scale_ratio": 1.1321113945937717,
  "bar_thickness_px": 13.0,
  "w_bar_m": 0.8076868899696248,
  "method": "red_mask_top_edge_thickness",
  "frame_id": 451,
  "frame": "frames\\a4_bar_width.jpg"
}
```

## (A5) Minimum inter-gate spacing

```json
{
  "n_pairs": 153,
  "min_spacing_m": 5.706561036223846,
  "p10_spacing_m": 8.267517441552185,
  "median_spacing_m": 10.328132589762355,
  "best": {
    "fid": "20260717T102132-7223cc0c",
    "phase": "phase5d",
    "flight": "F3",
    "t": 9.3964029,
    "frame_id": 344,
    "spacing_m": 5.706561036223846,
    "R1": 13.918716050173254,
    "R2": 16.735243531791703,
    "du_px": 118.0353889465332,
    "frame": "frames\\a5_intergate_spacing.jpg"
  },
  "top5_smallest": [
    {
      "fid": "20260717T102132-7223cc0c",
      "phase": "phase5d",
      "flight": "F3",
      "t": 9.3964029,
      "frame_id": 344,
      "spacing_m": 5.706561036223846,
      "R1": 13.918716050173254,
      "R2": 16.735243531791703,
      "du_px": 118.0353889465332,
      "frame": "frames\\a5_intergate_spacing.jpg"
    },
    {
      "fid": "20260717T102132-7223cc0c",
      "phase": "phase5d",
      "flight": "F3",
      "t": 9.2298051,
      "frame_id": 339,
      "spacing_m": 5.945256277782282,
      "R1": 15.045290358605087,
      "R2": 17.561455118592907,
      "du_px": 114.25675964355469,
      "frame": "frames\\a5_intergate_spacing.jpg"
    },
    {
      "fid": "20260717T101837-7223cc0c",
      "phase": "phase5d",
      "flight": "F1",
      "t": 7.2819409,
      "frame_id": 310,
      "spacing_m": 6.032533061520435,
      "R1": 9.481481481481481,
      "R2": 15.058823529411764,
      "du_px": 125.0,
      "frame": "frames\\a5_intergate_spacing.jpg"
    },
    {
      "fid": "20260717T102132-7223cc0c",
      "phase": "phase5d",
      "flight": "F3",
      "t": 9.9004688,
      "frame_id": 359,
      "spacing_m": 6.068708120890462,
      "R1": 7.829043427045678,
      "R2": 13.055448418956201,
      "du_px": 119.48563385009766
    },
    {
      "fid": "20260717T102132-7223cc0c",
      "phase": "phase5d",
      "flight": "F3",
      "t": 9.9004688,
      "frame_id": 359,
      "spacing_m": 7.023923918890199,
      "R1": 6.6403967982607455,
      "R2": 7.829043427045678,
      "du_px": 295.73563385009766
    }
  ]
}
```


## Deliverables

- `report.md`, `summary.json`, `a1_fa0_manifest.json`
- `a2_r1.csv`, `frames/a4_bar_width.jpg`, `frames/a5_intergate_spacing.jpg`
