# Final-meter blindness — phase6c F3 vs F1

Fixture: `fixtures/20260719T121704-phase6c-true-vertical/`.
F3 `20260719T121637` crossed the gate plane on attempt 1 with
`gate_rel` age **1.25 s** (zero accepted fixes in the final ~1.25 s).
This report reconstructs **t = 6.4–8.4 s** (log mono timebase) and
contrasts F1 attempt 1 where vision held through retreat.

## Requirement question

What must close the last meter: **close-tracker tuning** (support,
solo timeout, ROI) or a **terminal feature** that does not need a
full certified pose (top-bar / banner row once identity is held)?

## F3 — terminal dash (blind)

- frames=60 pose=40 lock_ok=31 trk_ok=31 age_end=0.968126408 age_max=0.968126408
- note: geometric termination ~8.38s, age 1.25s, crossed believed z=-0.42
- phase transitions near window: `[{'t': 5.4034291, 'phase': 'takeoff'}, {'t': 5.6436644, 'phase': 'align'}, {'t': 6.4036387, 'phase': 'commit'}, {'t': 8.3835106, 'phase': 'retreat'}]`
- log detections in window: **43**
- plane-cross (log): `{'t': 8.2635904, 't_vec': [0.0602538888447124, 0.22740011009017577, -0.06120245662665799], 'age': 1.135474528, 'believed_z_cam': -0.06120245662665799}`
- closest state sample: `{'t': 8.2434279, 't_vec': [0.0627298742130038, 0.2089401575018326, 0.004035212054883254], 'age': 1.114086528, 'dist': 0.21819099310465995}`

### Detector reject histogram

```json
{
  "OK_pose": 40,
  "grazing_normal(|nz|=0.33)": 2,
  "grazing_normal(|nz|=0.30)": 1,
  "grazing_normal(|nz|=0.25)": 2,
  "scale_high(1.56>1.5)": 1,
  "scale_high(1.62>1.5)": 1,
  "grazing_normal(|nz|=0.22)": 1,
  "scale_high(1.86>1.5)": 1,
  "grazing_normal(|nz|=0.18)": 1,
  "scale_high(1.64>1.5)+grazing_normal(|nz|=0.21)": 1,
  "scale_high(1.57>1.5)+grazing_normal(|nz|=0.17)": 1,
  "no_quad_or_box": 6,
  "grazing_normal(|nz|=0.20)": 1,
  "grazing_normal(|nz|=0.24)": 1
}
```

### Close-tracker reject histogram

```json
{
  "OK": 31,
  "track_failed_solve_or_step": 2,
  "low_support(2<10,edges=1)": 1,
  "low_support(0<10,edges=0)": 13,
  "solo_timeout(1.00>1.0)": 1,
  "solo_timeout(1.04>1.0)": 1,
  "solo_timeout(1.07>1.0)": 1,
  "solo_timeout(1.10>1.0)": 1,
  "solo_timeout(1.13>1.0)": 1,
  "solo_timeout(1.17>1.0)": 1,
  "solo_timeout(1.20>1.0)": 1,
  "solo_timeout(1.24>1.0)": 1,
  "solo_timeout(1.26>1.0)": 1,
  "solo_timeout(1.30>1.0)": 1,
  "solo_timeout(1.34>1.0)": 1,
  "solo_timeout(1.37>1.0)": 1,
  "solo_timeout(1.40>1.0)": 1
}
```

### FOV / bloom tags

```json
{
  "in_fov": 27,
  "edge_clip:bottom": 11,
  "edge_clip:right": 22
}
```

### Hardest frames

- `t=7.98` hard=9 det=`grazing_normal(|nz|=0.24)` trk=`solo_timeout(1.00>1.0)` fov=`edge_clip:right` age=0.565509408 R̂=6.508020367041188 → `frames/F3/F3_t7.98_h9.jpg`
- `t=7.45` hard=8 det=`scale_high(1.64>1.5)+grazing_normal(|nz|=0.21)` trk=`track_failed_solve_or_step` fov=`edge_clip:right` age=0.040889408 R̂=4.714584890174382 → `frames/F3/F3_t7.45_h8.jpg`
- `t=7.48` hard=8 det=`scale_high(1.57>1.5)+grazing_normal(|nz|=0.17)` trk=`track_failed_solve_or_step` fov=`edge_clip:right` age=0.065555408 R̂=4.777747905738977 → `frames/F3/F3_t7.48_h8.jpg`
- `t=7.52` hard=7 det=`no_quad_or_box` trk=`low_support(2<10,edges=1)` fov=`edge_clip:bottom` age=0.100344408 R̂=4.877578153155782 → `frames/F3/F3_t7.52_h7.jpg`
- `t=7.55` hard=7 det=`no_quad_or_box` trk=`low_support(0<10,edges=0)` fov=`edge_clip:bottom` age=0.134893408 R̂=4.979613978925322 → `frames/F3/F3_t7.55_h7.jpg`
- `t=7.58` hard=7 det=`no_quad_or_box` trk=`low_support(0<10,edges=0)` fov=`edge_clip:bottom` age=0.162845408 R̂=5.057480642871646 → `frames/F3/F3_t7.58_h7.jpg`
- `t=7.62` hard=7 det=`no_quad_or_box` trk=`low_support(0<10,edges=0)` fov=`edge_clip:bottom` age=0.197476408 R̂=5.157671968993872 → `frames/F3/F3_t7.62_h7.jpg`
- `t=7.65` hard=7 det=`no_quad_or_box` trk=`low_support(0<10,edges=0)` fov=`edge_clip:bottom` age=0.243739408 R̂=5.304178498933104 → `frames/F3/F3_t7.65_h7.jpg`

## F1 — contrast (vision held)

- frames=60 pose=52 lock_ok=60 trk_ok=58 age_end=0.003369184 age_max=0.022829128
- note: retreat ~8.20s with age 0.00 — vision held; contrast case
- phase transitions near window: `[{'t': 5.4043547, 'phase': 'takeoff'}, {'t': 5.7045383, 'phase': 'align'}, {'t': 6.4451946, 'phase': 'commit'}, {'t': 8.2048416, 'phase': 'retreat'}]`
- log detections in window: **60**
- closest state sample: `{'t': 8.3043827, 't_vec': [-0.7224937654700258, -0.1877611845404424, 1.0219454163281694], 'age': 0.029839832, 'dist': 1.2655528189361525}`

### Detector reject histogram

```json
{
  "OK_pose": 52,
  "grazing_normal(|nz|=0.18)+ty_max(|ty|=-6.51>6.0)": 1,
  "grazing_normal(|nz|=0.20)+ty_max(|ty|=-8.21>6.0)": 1,
  "ty_max(|ty|=-6.21>6.0)": 1,
  "grazing_normal(|nz|=0.27)": 1,
  "grazing_normal(|nz|=0.19)": 1,
  "grazing_normal(|nz|=0.29)": 1,
  "grazing_normal(|nz|=0.24)": 1,
  "scale_high(1.54>1.5)": 1
}
```

### Close-tracker reject histogram

```json
{
  "OK": 58,
  "low_support(5<5,edges=1)": 2
}
```

### FOV / bloom tags

```json
{
  "edge_clip:bottom": 13,
  "in_fov": 34,
  "edge_clip:top": 1,
  "edge_clip:right": 4,
  "edge_clip:top,bottom": 2,
  "edge_clip:left,top,bottom": 4,
  "edge_clip:left,bottom": 2
}
```

### Hardest frames

- `t=7.72` hard=7 det=`scale_high(1.54>1.5)` trk=`OK` fov=`edge_clip:right` age=0.003202152 R̂=2.2661200820373817 → `frames/F1/F1_t7.72_h7.jpg`
- `t=6.52` hard=4 det=`grazing_normal(|nz|=0.18)+ty_max(|ty|=-6.51>6.0)` trk=`OK` fov=`in_fov` age=0.002975936 R̂=4.261826429902077 → `frames/F1/F1_t6.52_h4.jpg`
- `t=6.59` hard=4 det=`grazing_normal(|nz|=0.20)+ty_max(|ty|=-8.21>6.0)` trk=`OK` fov=`in_fov` age=0.000604752 R̂=3.997377734125885 → `frames/F1/F1_t6.59_h4.jpg`
- `t=6.67` hard=4 det=`ty_max(|ty|=-6.21>6.0)` trk=`OK` fov=`in_fov` age=0.013929136 R̂=3.761526819589309 → `frames/F1/F1_t6.67_h4.jpg`
- `t=8.35` hard=4 det=`OK_pose` trk=`low_support(5<5,edges=1)` fov=`edge_clip:left,bottom` age=0.003502472 R̂=1.7079054535011682 → `frames/F1/F1_t8.35_h4.jpg`
- `t=8.39` hard=4 det=`OK_pose` trk=`low_support(5<5,edges=1)` fov=`edge_clip:top,bottom` age=0.003369184 R̂=1.7368487217773774 → `frames/F1/F1_t8.39_h4.jpg`
- `t=7.79` hard=3 det=`OK_pose` trk=`OK` fov=`edge_clip:right` age=0.003635464 R̂=2.1308338819441626 → `frames/F1/F1_t7.79_h3.jpg`
- `t=7.82` hard=3 det=`OK_pose` trk=`OK` fov=`edge_clip:right` age=0.00204 R̂=2.0911400517415215 → `frames/F1/F1_t7.82_h3.jpg`

## What differed (F3 vs F1)

| | F3 | F1 |
|---|---:|---:|
| frames in window | 60 | 60 |
| detector poses | 40 | 52 |
| lock accepts | 31 | 60 |
| tracker OK | 31 | 58 |
| age at window end | 0.968126408 | 0.003369184 |
| log dets in window | 43 | 60 |

## Spec implication (next build)

Read the histograms + hard frames before choosing:

1. **If** rejects are dominated by `scale_low` / `ty_max` / `grazing_normal` while the ring is still visually present → the **full-pose detector is the wrong sensor** in the last meter; keep identity from an earlier certified fix and close with **tracker + terminal feature** (top-bar/banner row).
2. **If** rejects are `low_support` / `solo_timeout` with edges still in FOV → **tracker tuning** (min_support, max_solo_s, search_px) can recover fixes without a new feature.
3. **If** FOV is `edge_clip` / ring gone → neither detector nor edge tracker can invent geometry; need **border-exit / structure-identity** terminal channel or an earlier commit slowdown.
4. F1 holding age≈0 through the same clock window means the pipeline *can* keep fixes at that geometry — F3's blindness is situational (approach geometry / bloom / clip), not a universal last-meter blackout.

## Deliverables

- `final-meter-blindness.md` (this file)
- `summary.json`, `f3_timeline.csv`, `f1_timeline.csv`
- `frames/F3/*.jpg`, `frames/F1/*.jpg` (hardest 6–8 each)
