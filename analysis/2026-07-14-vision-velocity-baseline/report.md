# Vision-velocity baseline validation (phase2j)

Generated 2026-07-14. Offline reconstruction of vision velocity using a
**0.15–0.45 s fix-history baseline** (as in commit `2cc8df9`), compared to
the estimator's logged `v_world` from phase2j flights (which still used
frame-pair derivatives under `da38639`).

## Method

1. Load `detection` records with PnP `rel_pose.t` and `state` with `v_world` / `q_att`.
2. For each fix, take the oldest prior fix whose age is in [0.15, 0.45] s.
3. `v_cam = -(t_now - t_base) / dt`, then `v_body = cam_to_body(v_cam)`,
   `v_world = R(q_att) * v_body` using nearest logged attitude.
4. PnP position noise: median residual std after linear detrend in 0.5 s windows.

## Logs used

- `phase2j-V1`: `20260714T132005-1429a43c` (2725 PnP fixes, 2251 states)
- `phase2j-V2`: `20260714T132354-80030858` (1687 PnP fixes, 2251 states)

## Blockers

- phase2k logs/fixtures not found locally — validation uses phase2j only.

## Key metrics

### phase2j-V1 (`20260714T132005-1429a43c`)

- **PnP position noise std** (0.5 s linear-detrend residual, median over 29 windows): xyz = [0.444, 0.756, 1.677] m; |std| = 1.892 m
- Vision |v_cam| std: frame-pair **105.12 m/s** vs 0.2s baseline **18.06 m/s**
- Offline baseline vs logged `v_world` RMSE: **21.65 m/s** (xyz [34.51, 5.59, 13.56])
- Mean speed: logged 22.15 m/s, baseline 15.06 m/s
- Plots: `analysis/2026-07-14-vision-velocity-baseline/phase2j-V1_velocity_baseline.png`, `analysis/2026-07-14-vision-velocity-baseline/phase2j-V1_vcam_hist.png`

### phase2j-V2 (`20260714T132354-80030858`)

- **PnP position noise std** (0.5 s linear-detrend residual, median over 16 windows): xyz = [0.178, 0.876, 2.242] m; |std| = 2.413 m
- Vision |v_cam| std: frame-pair **139.51 m/s** vs 0.2s baseline **19.10 m/s**
- Offline baseline vs logged `v_world` RMSE: **26.84 m/s** (xyz [41.24, 4.48, 21.0])
- Mean speed: logged 27.20 m/s, baseline 14.89 m/s
- Plots: `analysis/2026-07-14-vision-velocity-baseline/phase2j-V2_velocity_baseline.png`, `analysis/2026-07-14-vision-velocity-baseline/phase2j-V2_vcam_hist.png`

## Interpretation

- Phase2j logged `v_world` was fed by **frame-pair** vision derivatives; those
  magnitudes are dominated by PnP jitter (commit message cites ~±18 cm).
- The 0.15–0.45 s baseline reduces derivative noise; residual RMSE vs logged
  `v_world` is expected to be large because the online estimate was the noisy one.
- PnP noise std validates the premise for the new baseline.

## Phase2k

No phase2k flight logs/fixtures found on this machine at analysis time.
