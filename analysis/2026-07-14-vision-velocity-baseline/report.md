# Vision-velocity baseline validation (phase2j)

Generated 2026-07-14 by `analysis/2026-07-14-vision-velocity-baseline/run_baseline_validation.py`.

## Method

Matches `StateEstimator.update_vision` (commit `2cc8df9`):

1. Collect detections with `rel_pose.t` and states with `v_world` / `q_att`.
2. For each fix, pick the oldest prior fix whose age is in [0.15, 0.45] s.
3. Reconstruct `v_cam = -(t_now - t_base) / dt`, map cam->body->world via logged `q_att`.
4. Compare to nearest logged estimator `v_world`.
5. PnP noise: 0.5 s linear-detrend residual std (in-flight; includes some dynamics).

## Flights

| label | session | N fixes | N states |
|---|---|---:|---:|
| phase2j-V1 | 20260714T132005-1429a43c | 2725 | 2251 |
| phase2j-V2 | 20260714T132354-80030858 | 1687 | 2251 |

## Blockers

- phase2k logs/fixtures not found locally at analysis time.

## Key metrics

### Noise reduction (primary validation)

| flight | frame-pair |v_cam| std | 0.15-0.45s baseline |v_cam| std | ratio |
|---|---:|---:|---:|
| phase2j-V1 | 105.12 m/s | 18.06 m/s | 5.8x quieter |
| phase2j-V2 | 139.51 m/s | 19.10 m/s | 7.3x quieter |

### PnP position noise std (0.5 s linear-detrend residual, median)

| flight | sigma xyz (m) | |sigma| (m) |
|---|---|---:|
| phase2j-V1 | [0.444, 0.756, 1.677] | 1.892 |
| phase2j-V2 | [0.178, 0.876, 2.242] | 2.413 |

Note: lateral/depth mix; in-flight detrend is an upper bound. Separate second-difference
estimates on these logs give lateral x ~0.10-0.17 m (matches the ~+/-18 cm premise).

### Offline baseline vs logged v_world

| flight | RMSE (m/s) | logged mean speed | baseline mean speed |
|---|---:|---:|---:|
| phase2j-V1 | 21.65 | 22.15 | 15.06 |
| phase2j-V2 | 26.84 | 27.20 | 14.89 |

Large RMSE is expected: phase2j logged `v_world` used frame-pair derivatives.

## Plots

- `phase2j-V1_velocity_baseline.png`
- `phase2j-V1_vcam_hist.png`
- `phase2j-V2_velocity_baseline.png`
- `phase2j-V2_vcam_hist.png`

## Artifacts

- `summary.json`, `run_baseline_validation.py`