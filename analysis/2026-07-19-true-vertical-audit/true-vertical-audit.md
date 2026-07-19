# True-vertical audit — tilted-frame discovery

Independent DATA ANALYST audit of ROUND5 / commit `2c5057a`.
Recorded data only. HEAD pulled before run; harness uses
`aigp.planning.approach.true_world_dz` (level composition).

## 0. Claim under audit

The attitude filter zeroes a **-17.8°** nose-down rest pose
(`level_pitch≈-0.311`). Naive `gate_world_dz` therefore mixes
`sin(17.8°)·R ≈ 0.31·R` of phantom "gate above" into every
vertical judgment. Claimed true gate-1 opening height above the
pad camera: **~1.3 m**.

## 1. TRUE opening height → GATE_GEOM

### Unit / pad pin (ROUND5 numbers)

```json
{
  "t_vec": [
    0.015,
    -3.217,
    5.525
  ],
  "phantom_dz": -3.217,
  "true_dz": -1.3719644233017538,
  "opening_height_above_cam_m": 1.3719644233017538,
  "claim_approx_1_3m": true
}
```

- **GATE_GEOM (gate-1 opening above pad cam):** **1.350 m**
- Pad rest-like cohort: {"label": "pad_rest_like", "n": 8867, "median_m": 1.349913517532631, "mean_m": 1.2263787737446408, "p10_m": 1.2334256618651263, "p90_m": 1.3724642766077109, "std_m": 0.4625074643772247}
- In-flight 1.5–12 m cohort: {"label": "inflight_1.5_12m", "n": 89313, "median_m": 1.4258111261288773, "mean_m": 1.0026432795182445, "p10_m": -1.623064097500902, "p90_m": 3.2174475801768256, "std_m": 1.9581143004623667}
- Pin flights (20260717T153903*): [
  {
    "fid": "20260717T153903-d946830d",
    "t_vec": [
      0.014897532500995014,
      -3.217097252580509,
      5.524948194341941
    ],
    "R": 6.393355083146716,
    "phantom_dz": -3.217097252580509,
    "true_dz": -1.3739999908830383,
    "opening_height_above_cam_m": 1.3739999908830383,
    "claim_1_3m": true,
    "unit_pin_target": -1.372
  }
]

### Gate 2+ opening heights

```json
{
  "n": 608,
  "summary": {
    "label": "gate2_plus_candidates",
    "n": 608,
    "median_m": -1.4788339720285362,
    "mean_m": -3.1706086901151607,
    "p10_m": -9.566547233517946,
    "p90_m": 0.06007128635236306,
    "std_m": 3.9472716544546236
  },
  "samples": [
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.2681509,
      "R": 19.69028448902565,
      "opening_height_above_cam_m": -3.6448325420807177,
      "true_dz": 3.6448325420807177,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.2786433,
      "R": 19.69028448902565,
      "opening_height_above_cam_m": -3.6348810142386965,
      "true_dz": 3.6348810142386965,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.2829884,
      "R": 19.69028448902565,
      "opening_height_above_cam_m": -3.6348810142386965,
      "true_dz": 3.6348810142386965,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.2945073,
      "R": 19.023503590418407,
      "opening_height_above_cam_m": -3.485939367229994,
      "true_dz": 3.485939367229994,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.3109815,
      "R": 19.023503590418407,
      "opening_height_above_cam_m": -3.458372490760865,
      "true_dz": 3.458372490760865,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.3223336,
      "R": 18.22224879492035,
      "opening_height_above_cam_m": -3.275766827791006,
      "true_dz": 3.275766827791006,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.3306139,
      "R": 18.22224879492035,
      "opening_height_above_cam_m": -3.275766827791006,
      "true_dz": 3.275766827791006,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.3388435,
      "R": 18.22224879492035,
      "opening_height_above_cam_m": -3.266148307409564,
      "true_dz": 3.266148307409564,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.351029,
      "R": 18.22224879492035,
      "opening_height_above_cam_m": -3.266148307409564,
      "true_dz": 3.266148307409564,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.3679886,
      "R": 17.655185869172033,
      "opening_height_above_cam_m": -3.1358412868937604,
      "true_dz": 3.1358412868937604,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.3799502,
      "R": 17.655185869172033,
      "opening_height_above_cam_m": -3.609170856572168,
      "true_dz": 3.609170856572168,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.3927244,
      "R": 17.92935046672763,
      "opening_height_above_cam_m": -3.673091985499762,
      "true_dz": 3.673091985499762,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.4034703,
      "R": 17.92935046672763,
      "opening_height_above_cam_m": -4.41560792482104,
      "true_dz": 4.41560792482104,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.4127241,
      "R": 17.92935046672763,
      "opening_height_above_cam_m": -4.41560792482104,
      "true_dz": 4.41560792482104,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.428244,
      "R": 18.929319317270657,
      "opening_height_above_cam_m": -4.498599219181668,
      "true_dz": 4.498599219181668,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.4402187,
      "R": 18.929319317270657,
      "opening_height_above_cam_m": -5.621481534569831,
      "true_dz": 5.621481534569831,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.4594927,
      "R": 18.929319317270657,
      "opening_height_above_cam_m": -6.088713933142193,
      "true_dz": 6.088713933142193,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.4879979,
      "R": 8.354024566759158,
      "opening_height_above_cam_m": -0.2275936858354637,
      "true_dz": 0.2275936858354637,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.4948356,
      "R": 8.354024566759158,
      "opening_height_above_cam_m": -0.2275936858354637,
      "true_dz": 0.2275936858354637,
      "note": "post-close far lock (possible next gate)"
    },
    {
      "fid": "20260716T131137-2ca531c3",
      "phase": "20260716T132549-phase3j-r2training-rerun",
      "t": 26.5053837,
      "R": 8.354024566759158,
      "opening_height_above_cam_m": -0.20649965943792736,
      "true_dz": 0.20649965943792736,
      "note": "post-close far lock (possible next gate)"
    }
  ]
}
```

**Verdict:** unit pin reproduces **~1.37 m** true height (phantom **~3.22 m**).
Pad cohort median is the recommended GATE_GEOM number above.

## 2. Miss map under TRUE vertical

- Attempts scored: **88**
- Re-attributed (OLD label ≠ TRUE label): **27** (30.7%)
- OLD LOW → not LOW (phantom lows): **11**
- TRUE HIGH count: **49** · TRUE LOW: **8** · TRUE CENTERED: **31**
- Median (phantom_dz − true_dz): **-0.11934794461906306** m
- Reattr breakdown: `{'LOW->HIGH': 7, 'CENTERED->HIGH': 15, 'LOW->CENTERED': 4, 'HIGH->LOW': 1}`
- Suspicion flags: `{'many_LOW_were_phantom': True, 'several_HIGH_were_real': True}`

Plot: `plots/miss_scatter_old_vs_true.png` · table: `miss_table_true_vertical.csv`

**Interpretation:** if many historical 'LOW arrivals' flip under
`true_world_dz`, they were chasing the tilted-frame phantom aim.
TRUE HIGH rows that stay HIGH are real overshoots.

## 3. F2 abort reconstruction (`20260719T075333`)

```json
{
  "flight_id": "20260719T075333-fab49fbf",
  "note_timebases": "t=0 is first log mono_ns; takeoff setpoint may be later. ROUND5 't~7.88' \u2248 retreat if measured from early hover; retreat_t_log=7.883s from first mono.",
  "retreat_t_s": 7.8834977,
  "retreat_state": {
    "dist": 1.3093740863828598,
    "t_vec": [
      -0.09498821139197787,
      -0.4599758541677471,
      1.2222356365980143
    ],
    "center_px": [
      295.13063215041075,
      59.571279934713814
    ],
    "age": 0.100108248,
    "phantom_dz": -0.2798791149786713,
    "true_dz": 0.12153000885040938,
    "phantom_minus_true": -0.40140912382908067,
    "corridor_error_vs_aim0_phantom": 0.2798791149786713,
    "corridor_error_vs_aim0_true": 0.12153000885040938
  },
  "closest_state": {
    "t": 8.2633924,
    "dist": 0.8217287598609395,
    "t_vec": [
      -0.008075141487040062,
      -0.5963220026841136,
      0.5653078948567497
    ],
    "center_px": [
      315.6317219044212,
      233.4789742344865
    ],
    "phantom_dz": -0.5661167573994595,
    "true_dz": -0.35718581029977964,
    "pixel_looks_centered": true
  },
  "last_commit_v_body": [
    2.151935529336169,
    -0.2192777759912385,
    -1.7041010252915585
  ],
  "counterfactual_coast": {
    "t_to_plane_s": 0.5450000000000004,
    "body_at_plane": [
      0.04943077310980398,
      0.02451817652324647,
      0.46875920461615306
    ],
    "lateral_m": 0.02451817652324647,
    "vertical_body_z_m": 0.46875920461615306,
    "vertical_true_dz_m": 0.4386756656099094,
    "vertical_phantom_dz_m": 0.46431491103075445,
    "inside_opening_lateral": true,
    "inside_opening_vertical_body": true,
    "inside_opening_vertical_true": true,
    "inside_opening": true
  },
  "verdict": "WOULD_HAVE_CLEARED",
  "claim_check": {
    "ROUND5_phantom_0_58": true,
    "phantom_delta_at_retreat": -0.40140912382908067,
    "abort_threshold_0_45": true,
    "phantom_would_trip_corridor": false,
    "true_would_trip_corridor": false
  }
}
```

**Verdict: `WOULD_HAVE_CLEARED`**

Method: at first `retreat`, freeze last `commit` `v_body` and
integrate body-frame gate vector `G ← G − v·dt` until body-x
reaches the gate plane; score lateral + `true_world_dz` vs ±0.8 m
opening half-size. (User's t≈7.88s maps to early-hover timebase;
log-relative retreat is ~3.74 s from first mono / ~3.74 s from takeoff
depending on t0 — see `note_timebases`.)

## 4. A6 banner-reference status

```json
{
  "status": "BLOCKED",
  "blocked_by": "far trusted dets exist in logs, but paired slices lack overlapping far-range frames (most takeoff\u2192end / pad slices), or red banner band not separable \u2014 20260714T210518-58cd98ad_r2_slice_start.aigprec: no frames in far window (slice may be takeoff-only); 20260714T210844-58cd98ad_r2_slice_start.aigprec: no frames in far window (slice may be takeoff-only); 20260714T211404-58cd98ad_r2_slice_start.aigprec: no frames in far window (slice may be takeoff-only); 20260715T045100-411f3135_r2c_slice_start.aigprec: no frames in far window (slice may be takeoff-only); 20260715T045458-411f3135_r2c_slice_start.aigprec: no frames in far window (slice may be takeoff-only)",
  "original_R4_m": 0.147,
  "attempted_visions": 69,
  "blockers": [
    "20260714T210518-58cd98ad_r2_slice_start.aigprec: no frames in far window (slice may be takeoff-only)",
    "20260714T210844-58cd98ad_r2_slice_start.aigprec: no frames in far window (slice may be takeoff-only)",
    "20260714T211404-58cd98ad_r2_slice_start.aigprec: no frames in far window (slice may be takeoff-only)",
    "20260715T045100-411f3135_r2c_slice_start.aigprec: no frames in far window (slice may be takeoff-only)",
    "20260715T045458-411f3135_r2c_slice_start.aigprec: no frames in far window (slice may be takeoff-only)",
    "20260715T051458-6092dbc0_r2c_slice_start.aigprec: no frames in far window (slice may be takeoff-only)",
    "20260715T121747-22978559_r2d_slice_start.aigprec: no frames in far window (slice may be takeoff-only)",
    "20260715T122040-22978559_r2d_slice_start.aigprec: no frames in far window (slice may be takeoff-only)",
    "20260715T122352-22978559_r2d_slice_start.aigprec: no frames in far window (slice may be takeoff-only)",
    "20260715T184758-8e6cf1f5_r2e_slice_start.aigprec: no frames in far window (slice may be takeoff-only)"
  ]
}
```

## 5. Bottom line

1. **GATE_GEOM gate-1 ≈ 1.3–1.4 m** above pad camera — pin holds.
2. Miss-map re-attribution quantifies how much of the old LOW/HIGH
   story was tilted-frame fiction vs real geometry.
3. F2 counterfactual says whether the phase6b abort killed a clear.
4. A6 is shipped if `status=DONE`, else blocked with an explicit reason.

## Deliverables

- `true-vertical-audit.md` (this file)
- `summary.json`, `gate_geom.json`
- `miss_table_true_vertical.csv`, `plots/miss_scatter_old_vs_true.png`
- `f2_abort_reconstruction.json`, `a6_banner_reference.json`

## M2 add-ons

### 1. Separating regression — phantom vs aperture share

Across the 88 scored arrivals:

\[ y = (\text{believed opening height} - \text{true opening height}) = a + b\, R_{\mathrm{lastfix}} \]

with heights = `−dz` (so `y = true_dz − phantom_dz`).

```json
{
  "fit_all_88": {
    "n": 88,
    "intercept": 0.08752649452349369,
    "slope": 0.22290181658462666,
    "r_squared": 0.3169410732280079,
    "residual_rmse": 0.39978446150660496,
    "x_mean": 3.33318524998179,
    "y_mean": 0.8304995417575175,
    "definition": "y = believed_opening_height \u2212 true_opening_height (= true_dz \u2212 phantom_dz) at LAST NEAR fix (R\u22645m); x = R_lastfix. Far-gate flickers excluded.",
    "expected_slope": 0.30601081732530144,
    "expected_intercept_aperture": 0.33,
    "slope_vs_sin_tilt": 0.08310900074067479,
    "R_lastfix_median": 3.350949090871958,
    "R_lastfix_mean": 3.33318524998179
  },
  "fit_fresh_age_lt_0_25": {
    "n": 6,
    "intercept": -0.05735513479817163,
    "slope": 0.16294536969615117,
    "r_squared": 0.0467532632307569,
    "residual_rmse": 0.28269244896955953,
    "x_mean": 1.4840915129979668,
    "y_mean": 0.18447070545020242
  },
  "fit_R_le_4m": {
    "n": 59,
    "intercept": -0.1462908487491755,
    "slope": 0.3090712273020497,
    "r_squared": 0.6643693830748545,
    "residual_rmse": 0.19396164611481637,
    "x_mean": 2.682087042645554,
    "y_mean": 0.6826650852522107
  },
  "n_arrivals": 88,
  "interpretation": {
    "slope_is_phantom_share": true,
    "intercept_is_aperture_share": true,
    "prior_bug": "v1 used any last det including 10-40m flickers (R_mean~15m) \u2192 slope collapsed; v2 restricts to near fixes R\u22645m"
  }
}
```

- **slope b** (phantom share): **0.22290181658462666** (expect ≈ sin(17.8°) = 0.306)
- **intercept a** (aperture share): **0.08752649452349369** (expect ≈ 0.33)
- **R²**: **0.3169410732280079**

Plot: `plots/m2_separating_regression.png` · points: `m2_separating_points.csv`

### 2. P4 — vertical holdout on TRUE-frame axes

Same F1 harness as RESPONSE5 (cold = `range3m_to_collision`; warm = `range5m_to_3m` + collision), `--blind-last-s 0.6`. Vertical now scored with `true_world_dz` (and the 0.95·ty+0.31·tz linearization as a cross-check). Legacy 0.76 m max was on tilted ty.

| condition | vision hist | range err end/max | ty err end/max (tilted) | TRUE dz err end/max | lin err end/max |
|---|---:|---:|---:|---:|---:|
| cold | 1.05s | -1.55 / 1.71 | +2.72 / 2.72 | **+2.64 / 2.64** | +2.18 / 2.18 |
| warm | 2.73s | +1.86 / 1.86 | -1.58 / 1.58 | **-1.27 / 1.27** | -1.11 / 1.11 |

```json
{
  "flight": "20260716T203450-2ca531c3",
  "blind_s": 0.6,
  "legacy_tilted_table": {
    "cold": {
      "range": "+1.77 / 1.77",
      "vertical_ty": "0.00 / 0.26"
    },
    "warm": {
      "range": "+0.97 / 0.97",
      "vertical_ty": "\u22120.69 / 0.76"
    },
    "source": "docs/thinktank/RESPONSE5.md"
  },
  "cold": {
    "slices": [
      "20260716T203450-2ca531c3_range3m_to_collision.aigprec"
    ],
    "n_frames": 33,
    "vision_history_s": 1.0532222,
    "blind_s": 0.6,
    "n_blind_refs": 2,
    "range_error_end_m": -1.5458507807436996,
    "range_error_max_abs_m": 1.7094764169949048,
    "vertical_ty_error_end_m": 2.720811376078208,
    "vertical_ty_error_max_abs_m": 2.720811376078208,
    "vertical_true_dz_error_end_m": 2.6389265179754915,
    "vertical_true_dz_error_max_abs_m": 2.6389265179754915,
    "vertical_lin_error_end_m": 2.1846023361812863,
    "vertical_lin_error_max_abs_m": 2.1846023361812863,
    "note": "true_dz via true_world_dz(level_pitch); lin = 0.95\u00b7ty+0.31\u00b7tz advisory linearization"
  },
  "warm": {
    "slices": [
      "20260716T203450-2ca531c3_range5m_to_3m.aigprec",
      "20260716T203450-2ca531c3_range3m_to_collision.aigprec"
    ],
    "n_frames": 69,
    "vision_history_s": 2.7263983,
    "blind_s": 0.6,
    "n_blind_refs": 4,
    "range_error_end_m": 1.8634383640491314,
    "range_error_max_abs_m": 1.8634383640491314,
    "vertical_ty_error_end_m": -1.5777717127503712,
    "vertical_ty_error_max_abs_m": 1.5777717127503712,
    "vertical_true_dz_error_end_m": -1.2733086487317298,
    "vertical_true_dz_error_max_abs_m": 1.2733086487317298,
    "vertical_lin_error_end_m": -1.1104439602587735,
    "vertical_lin_error_max_abs_m": 1.1104439602587735,
    "note": "true_dz via true_world_dz(level_pitch); lin = 0.95\u00b7ty+0.31\u00b7tz advisory linearization"
  }
}
```

Legacy tilted warm max |ty| error **0.76 m** → replace with TRUE-frame max |dz| from the warm row above for T1 budget work.
