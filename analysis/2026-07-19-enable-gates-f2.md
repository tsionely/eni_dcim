# Enable-gate evidence — phase6e F2

Flight `20260719T143404-a76247fb` in fixture `20260719T143556-phase6e-aim-tfv1` (sibling checkout).
Timebase: **t_from_first** (log start); takeoff ≈ 4.22 s; gate clips at **t ≈ 7.97–7.98** (impulses 0.10 + 4.39).

These are **two of the three enable greens** (V3 disagreement evidence + FA=0). A6/`h_b` is a separate analyst task.

## Clip snapshot

- collisions: `[{"t": 7.9720387, "impulse": 0.10329741984605789, "threat_level": 1}, {"t": 7.9783977, "impulse": 4.394327163696289, "threat_level": 2}]`
- closest pre-clip detection: R=0.632 m at t=7.951, t_vec=[-0.08742407386249239, -0.17637278996970857, 0.6007237110373199], center=[243.28707316585331, 689.9838624574727]
- state @ clip: t=7.970, world_dz=0.05281037763114546, aim=0.04137972476115297, e_believed_up=-0.011430652869992494, age=0.039116816, t_cam=[-0.08082024209244716, -0.18003301023363819, 0.5152298761333018]

## 1. V3 overlap-band — oracle e_z vs believed alt-hold

From logged `feature` (pixel top-bar + span) and paired `state` in **t ∈ [7.0, 8.0)**:

- FEATURE samples: **3** (paired with state: 3)
- d*_bar = 0.8 (opening center under top bar); d*_banner = 0.15 (provisional R4)
- shadow owner hist: `{'term': 49}`

### Series

| t | y_top_px | span_px | e_z_bar | e_z_banner | e_believed_up | Δ(oracle−bel) | age | shadow |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 7.885 | 0.363 | 1169.056 | -0.554 | 0.096 | 0.007 | -0.561 | 0.016 | term |
| 7.922 | 0.018 | 1203.836 | -0.561 | 0.089 | 0.002 | -0.563 | 0.028 | term |
| 7.951 | -0.461 | 1381.466 | -0.591 | 0.059 | 0.014 | -0.605 | 0.042 | term |

### Stats

```json
{
  "e_z_bar": {
    "n": 3,
    "mean": -0.5686414028641836,
    "rms": 0.5688674507089625,
    "median": -0.5607880379485586,
    "min": -0.5909919999922626,
    "max": -0.5541441706517295
  },
  "e_believed_up": {
    "n": 3,
    "mean": 0.007783854494094564,
    "rms": 0.009097099701908317,
    "median": 0.006937488984201982,
    "min": 0.0024872472730378403,
    "max": 0.013926827225043868
  },
  "delta_oracle_minus_believed": {
    "n": 3,
    "mean": -0.5764252573582781,
    "rms": 0.5767779651487054,
    "median": -0.5632752852215964,
    "min": -0.6049188272173065,
    "max": -0.5610816596359315
  },
  "would_term_descend": true,
  "believed_near_centered": true,
  "high_bias_disagreement": true,
  "median_delta_m": -0.5632752852215964,
  "v3_rms_le_0p05": false
}
```

**Verdict:** YES — the pixel-row oracle is **HIGH** (median e_z_bar ≈ -0.56 m ⇒ TERM would command **descend**) while alt-hold believed near-centered (median e_believed_up ≈ 0.01 m). Median disagreement Δ ≈ -0.5632752852215964 m.

Note: all FEATURE `cert_status` values in this window are `none` — the side-pair certificate never armed, so live TERM ownership would NOT have captured even if enable were true. The oracle series is still the enable-gate *measurement* of what a healthy terminal feature would have said.

V3 release bar (RMS ≤ 0.05 m in the 1.5–3 m overlap band) is a tracker hygiene gate on healthy approaches; this graze’s sub-2 m FEATURE band documents the **actuation delta** alt-hold vs oracle, not a pass of that RMS bar (v3_rms_le_0p05=False).

## 2. Axis of contact — post-crossing detections

Window t ∈ [8.12, 8.52] (11 detections).

- votes: `{'TOP': 7, 'BOTTOM': 0, 'LEFT': 0, 'RIGHT': 3, 'UNCLEAR': 0}`
- winner: **TOP**
- P-B / top-bar hypothesis (predicts TOP): **CONFIRMED**

| t | R | t_vec | center_px | cert | label |
|---:|---:|---|---|---|---|
| 8.166 | 1.33 | `[0.42, -0.796, 0.985]` | `[439.3661441937761, 179.7450468684784]` | none | TOP |
| 8.194 | 1.57 | `[0.703, -0.62, 1.264]` | `[460.25, 179.5]` | certified | TOP |
| 8.223 | 1.65 | `[0.844, -0.657, 1.26]` | `[486.25, 179.5]` | certified | TOP |
| 8.255 | 1.71 | `[0.952, -0.683, 1.251]` | `[508.0, 179.5]` | certified | RIGHT |
| 8.289 | 1.77 | `[1.056, -0.696, 1.245]` | `[530.0, 179.5]` | certified | RIGHT |
| 8.328 | 1.82 | `[1.136, -0.709, 1.235]` | `[550.0, 179.5]` | certified | RIGHT |
| 8.386 | 1.60 | `[0.881, -0.798, 1.07]` | `[553.0646181161791, 186.8553632072892]` | none | TOP |
| 8.421 | 1.47 | `[0.744, -0.795, 0.983]` | `[531.6466675760184, 179.64866239170374]` | none | TOP |
| 8.458 | 1.42 | `[0.644, -0.797, 0.986]` | `[502.5962309947523, 179.47091304097276]` | none | TOP |
| 8.469 | 20.19 | `[5.337, -4.254, 19.0]` | `[411.25, 274.25]` | certified | FAR_FLICKER |
| 8.493 | 0.80 | `[-0.127, -0.472, 0.637]` | `[319.5, 71.25]` | certified | TOP |

## 3. FA=0 — certificate chain through the graze

Command window frame ids: `(295, 318)` (t_from_first 7.50–8.30, covers final approach + clip + immediate recover).

- exit code: `0`
- **FA=0: PASS**

```
window 295..318: 24 frames, certified=2 probation=0 -> FA=0 OK
overall: 460 frames, certified 110 (24%), probation 0 (0%)
terminal zone (<2.5m): 27 fix frames, certified 14 (52%), certified down to 0.80m
  certified-by-1.6m bar: MET
```

## Enable-green scorecard

| Gate | Status | Evidence |
|---|---|---|
| V3 oracle-vs-believed (this flight) | DOCUMENTED disagreement | Δ median=-0.5632752852215964 m; TERM descend=True |
| FA=0 suite (graze window) | **GREEN** | cert_suite window (295, 318) |
| A6 / h_b | OTHER TASK | feeds the third green |

## Deliverables

- `enable-gates-f2.md` (this file)
- `summary.json`, `v3_series.csv`, `contact_dets.csv`

