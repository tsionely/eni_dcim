# Phase 3d — R2-TRAINING with camera mount modeled

- **Date (local):** 2026-07-15 ~15:06-15:56 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `d65cd41...` (HEAD after pull; required commit or newer)
- **Task:** R2-TRAINING, 3 default flights, optional flight 4 with `--patch estimation.gyro_scale_roll=0.75`.
- **SIM LOCK:** created at `C:\Temp\eni_dcim_sim.lock` before launching the sim.
- **Simulator lifecycle:** fresh sim launched for the cycle; will be closed after push.

## Summary table

| Flight | Params | Result | Gates | Evidence on crossing / clip side |
|---|---|---|---:|---|
| F1 `20260715T121747-22978559` | default | env collision impulse 28.5 | 0 | gate low in image near direct detection; closest state far LEFT+LOW -> mostly high/top, with lateral component |
| F2 `20260715T122040-22978559` | default | env collision impulse 1.2, many env hits | 0 | direct closest gate far LEFT but vertically centered; state LEFT+HIGH -> lateral miss dominates, likely right-of-opening / side clip |
| F3 `20260715T122352-22978559` | default | env collision impulse 3.7 | 0 | mixed: direct closest RIGHT/center-y and earlier RIGHT+LOW; closest state near center/left-high -> lateral/vertical correction oscillates; no clean pass |
| F4 `20260715T051458-6092dbc0` | `gyro_scale_roll=0.75` | env collision impulse 17.5 | 0 | gate LEFT+LOW in image -> high/top plus likely right-of-opening; patch worse |

## Flight 1 — default
ID: `20260715T121747-22978559`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=28.5)"`
- duration 31.9s
- `gates_passed=0`, `env_hits=2`
- detections: 2974
- phases: `hover`, `takeoff`, `approach`, `commit`, `search`
- full recording ~465 MB; slice committed.

Crossing-side evidence:
- Direct closest detections around t+2.38s: center `[333, 282.75]` in 640x360 image -> `u≈+0.04`, `v≈+0.57` (gate LOW in image), dist ~3.24m.
- Closest dead-reckoned states around t+3.4s project gate center far **LEFT + LOW** (`center≈[-15, 3435]`), very close dist ~0.36m.

Interpretation:
- The dominant vertical miss remains **high/top-bar side** (gate low/below image). The closest state also suggests a lateral component: the gate is left of view, so the drone is likely right of the opening at the final miss.
- Not a pass; no active gate index advance.

## Flight 2 — default
ID: `20260715T122040-22978559`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=1.2)"`
- duration 30.7s
- `gates_passed=0`, `env_hits=32`
- detections: 2465
- phases: `hover`, `takeoff`, `recover`, `commit`, `approach`, `search`
- full recording ~423 MB; slice committed.

Crossing-side evidence:
- Direct closest detections around t+2.8s: center `[60, 180.75]`, `u≈-0.81`, `v≈0.00`, dist ~1.87m — gate far LEFT, vertically centered.
- Closest state estimates around t+3.6s project gate far **LEFT + HIGH** (`center≈[-1796, -237]`), dist ~0.25m.

Interpretation:
- This is mainly a **lateral miss**. Gate left in image means the drone/nose is to the right of the opening and needs left correction.
- The closest state says LEFT+HIGH, but direct detections say LEFT/center-y; I trust the direct detection more for side. Flight 2 likely clips/misses the **right side of the opening** (from aircraft perspective), not primarily top/bottom.
- Many env hits imply scraping/interaction rather than clean ring pass.

## Flight 3 — default
ID: `20260715T122352-22978559`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=3.7)"`
- duration 28.7s
- `gates_passed=0`, `env_hits=1`
- detections: 2638
- phases: `hover`, `takeoff`, `approach`, `commit`, `search`
- full recording ~371 MB; slice committed.

Crossing-side evidence:
- Direct closest detections around t+10.23s: center `[473.25, 166.5]`, `u≈+0.48`, `v≈-0.08`, dist ~2.1m — gate RIGHT, near vertical center.
- Earlier close direct detections around t+8.95s: `u≈+0.32`, `v≈+0.87` — RIGHT + LOW in image.
- Closest state around t+10.21s: gate center `[250.5,147.8]`, `u≈-0.22`, `v≈-0.18`, dist ~0.13m — LEFT + HIGH, but this is dead-reckoned/very close.

Interpretation:
- This flight is mixed: direct detector sees gate on the RIGHT approaching center; dead-reckoning at very close range swings LEFT+HIGH.
- It likely gets close to the opening but does not hold a clean centered line. Side may change through commit; no pass.
- This is the most ambiguous of the default runs and may show last-meter steering instability rather than a single fixed bar miss.

## Flight 4 — optional `--patch estimation.gyro_scale_roll=0.75`
ID: `20260715T051458-6092dbc0`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=17.5)"`
- duration 23.8s
- `gates_passed=0`, `env_hits=1`
- detections: 1366
- phases: `hover`, `takeoff`, `approach`, `search`
- full recording ~258 MB; slice committed.

Crossing-side evidence:
- Direct closest detections: gate **LEFT + LOW** in image (`u≈-0.29`, `v≈+0.56`, dist ~4.0m).
- This means high/top tendency remains (gate low in image), and the drone is likely right of the opening.

Interpretation:
- `gyro_scale_roll=0.75` did **not** help; it made lateral alignment worse and collision impulse worse.
- Reject this patch for now.

## Overall Phase 3d conclusion
- No gate pass yet (`gates_passed=0` in all four flights).
- The camera mount model changed the failure signature: not every default run is simply "too high/top" anymore.
- F1 still shows high/top-bar tendency; F2 is mostly lateral (gate left); F3 is mixed/unstable at the last meters; F4 roll-scale is worse.
- The key next issue appears to be **last-meter commit alignment / lateral steering stability**, not only altitude.

## Fixture contents
- `report.txt` — console output and appended analysis.
- `phase3d_r2training_closest.txt` — closest detection/state table used for high/low/left/right analysis.
- logs/results/params for all four flights.
- four recording slices (`*_r2d_slice_start.aigprec`), all <50 MB.
- downscaled screenshots for each flight.
- Full recordings are too large for git and remain local / Drive candidates.
