# Phase 3c — R2-TRAINING with live-steered commit

- **Date (local):** 2026-07-15 ~07:14-08:22 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `e8098e2...` (HEAD after pull; newer than required `8da7453`)
- **Task:** 3 default R2-TRAINING flights + optional flight 4 with `--patch estimation.gyro_scale_roll=0.75`.
- **Ground rules honored:** no code/config/docs edits; all run-time experiments via CLI patch only.
- **Simulator lifecycle:** launched fresh sim, will close after push.

## Quick summary table

| Flight | Params | Result | Gates | Frames | Detections | Closest / crossing-side evidence |
|---|---|---|---:|---:|---:|---|
| F1 `20260715T044545-411f3135` | default | flight timeout, 120s | 0 | 0 | 0 | no vision/detections — no crossing evidence |
| F2 `20260715T045100-411f3135` | default | env collision impulse 1.2 | 0 | many | 1379 | gate low in image / top-bar side; later state estimate far below frame |
| F3 `20260715T045458-411f3135` | default | env collision impulse 5.2 | 0 | many | 2163 | gate low in image / top-bar side; closest state center far below frame |
| F4 `20260715T051458-6092dbc0` | `gyro_scale_roll=0.75` | env collision impulse 17.5 | 0 | many | 1366 | gate left+low in image -> likely high and right-of-opening |

## Flight 1 — default
ID: `20260715T044545-411f3135`

Result:
- `aborted=True`, `abort_reason="flight timeout"`
- duration 120.0s
- `gates_passed=0`, `gate_clips=0`, `env_hits=0`
- No `frame` messages, no `detection` messages, no vision recording data.
- FSM phases: `hover`, `takeoff`, `search` only.

Crossing/clip side:
- None. No vision stream/detections, no crossing attempt evidence.
- This repeats the known intermittent R2 issue where the stream sometimes stays dead.

## Flight 2 — default
ID: `20260715T045100-411f3135`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=1.2)"`
- duration 22.6s
- `gates_passed=0`, `env_hits=3`
- Detections: 1379
- Phases: `hover`, `takeoff`, `approach`, `commit`, `recover`

Closest / crossing side evidence:
- Direct detections near approach show gate center **LOW in image**:
  - t+2.18s: center `[322.75, 261.5]`, `u≈+0.01`, `v≈+0.45`, dist ~5.2m
  - t+2.22s: center `[323, 287.75]`, `u≈+0.01`, `v≈+0.60`, dist ~5.2m
- Closest dead-reckoned states put gate center extremely below frame:
  - closest dist ~1.12m, center `[296, 668]`, image height 360, `v≈+2.7`.

Interpretation:
- Gate is below camera center / even below frame at closest approach, so the aircraft is **too high relative to the opening** and is likely clipping/colliding on the **top-bar side**.
- Lateral error near direct detections is small (mostly center-x), so main miss is vertical, high/top.

## Flight 3 — default
ID: `20260715T045458-411f3135`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=5.2)"`
- duration 26.8s
- `gates_passed=0`, `env_hits=2`
- Detections: 2163
- Phases: `hover`, `takeoff`, `approach`, `commit`, `recover`

Closest / crossing side evidence:
- Direct detections close to the gate show gate LOW in image:
  - t+2.72s: dist ~3.27m, center `[336.5, 346]`, `u≈+0.05`, `v≈+0.92`
  - t+2.70s: dist ~3.31m, center `[328.75, 345]`, `u≈+0.03`, `v≈+0.92`
- Closest dead-reckoned states show gate center way below frame near closest approach:
  - dist ~0.17–0.24m with projected center around `[245, 1305]`, far below image height 360.

Interpretation:
- Again this is primarily **too high / top-bar side**. The horizontal error is small-to-moderate but vertical error dominates.
- This looks like the live-steered commit still keeps the target below frame at the last meters rather than pulling down enough.

## Flight 4 — optional `--patch estimation.gyro_scale_roll=0.75`
ID: `20260715T051458-6092dbc0`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=17.5)"`
- duration 23.8s
- `gates_passed=0`, `env_hits=1`
- Detections: 1366
- Phases: `hover`, `takeoff`, `approach`, `search`

Closest / crossing side evidence:
- Direct detections closest to approach show gate **LEFT + LOW in image**:
  - t+2.49s: dist ~4.00m, center `[225.75, 280]`, `u≈-0.29`, `v≈+0.56`
  - t+2.46s: dist ~4.06m, center `[232.5, 276.75]`, `u≈-0.27`, `v≈+0.54`
- State/dead-reckoning later has inconsistent projected centers, but still mostly very low in frame.

Interpretation:
- LOW in image again means **too high / top-bar side**.
- LEFT in image means the gate is left of the nose; the aircraft is likely **right of the opening** (needs left correction). So the optional roll-scale run worsened lateral alignment: high + right-of-opening.
- The optional `gyro_scale_roll=0.75` did not help; collision impulse was the worst of the cycle.

## Overall Phase 3c findings
1. **No gate pass yet** (`gates_passed=0` in all four flights).
2. The current default controller now sees/detects R2 gates and enters approach/commit in successful vision runs.
3. The dominant miss in default flights is vertical: **too high / top-bar side** — gate appears low or below the frame during close approach/commit.
4. Optional roll-scale patch `gyro_scale_roll=0.75` appears worse: adds a lateral miss component (right-of-opening) and stronger collision.
5. Flight 1 had no vision stream; R2 stream startup remains intermittently flaky.

## Recording deliverables
Full recordings are too large for git:
- F2 full: ~213 MB
- F3 full: ~318 MB
- F4 full: ~258 MB

Committed slices:
- `20260715T045100-411f3135_r2c_slice_start.aigprec` — 33.69 MB
- `20260715T045458-411f3135_r2c_slice_start.aigprec` — 33.69 MB
- `20260715T051458-6092dbc0_r2c_slice_start.aigprec` — 33.69 MB

## Fixture contents
- `report.txt` — full console and summary analysis.
- Logs/results/params for all four flights.
- 3 R2 recording slices around the approach attempts.
- `screens/` — downscaled screenshots from each flight.
- `phase3c_r2training_closest.txt` was not added separately; its key findings are summarized above.
