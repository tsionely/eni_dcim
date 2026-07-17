# Phase 5f — terminal vertical enable-bit A/B (VERIFIED R2-TRAINING)

- **Date (local):** 2026-07-17 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Operator workspace:** `C:\Users\tsion\Projects\eni_dcim_phase1`
- **Code flown:** `1fc11fcad058a96c1ed3754cfc7d37d397cf1d01` (`1fc11fc` — "HOTFIX: enable-bit init crashed every launch")
- **Label:** `phase5f-terminal`
- **SIM LOCK:** `C:\Temp\eni_dcim_sim.lock` held during the cycle.
- **Track:** verified `AI-GP VIRTUAL QUALIFIER R2 - TRAINING` row, click `[415,394]`, scene checked against `fixtures/track-id-reference/`.

## Launch sanity

Before F1 I ran a quick verified-R2 sanity launch on the hotfix. It reached the FSM `TAKEOFF` transition and completed a real flight (`20260717T150812-74644518`, 9.43s, env collision, 2 gate clips), so the tick-one `NameError` crash from `e26c13d` was fixed. The sanity flight is not counted in the A/B table.

## A/B slots

- **F1, F2 baseline:** `python scripts/fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300`
- **F3, F4 terminal LIVE:** same command plus `--patch planner.terminal.enable=true`

A first terminal-live F4 attempt (`20260717T151421-e179e097`) was valid but too short for the >10s unique-slice guard, so it was replaced by the counted F4 below (`20260717T151717-e179e097`).

## Track verification

| Flight | Slot | Enable bit | Row scores R1 / R2sub / R2train | Post-RACE cyan px | Track |
|---|---|---:|---|---:|---|
| F1 | baseline | false | 0.99995 / 0.99996 / 0.99992 | 48,443 | R2-TRAINING ✓ |
| F2 | baseline | false | 0.99960 / 0.99961 / 0.99977 | 27,160 | R2-TRAINING ✓ |
| F3 | terminal LIVE | true | 0.99966 / 0.99987 / 0.99987 | 27,600 | R2-TRAINING ✓ |
| F4 | terminal LIVE | true | 0.99974 / 0.99978 / 0.99984 | 28,355 | R2-TRAINING ✓ |

All counted flights stayed at `active_gate_index=0`.

## Per-flight results

| Flight | Log ID | Enable bit | Result | Gates | Clips / env | Closest direct fix | Closest believed state | Vertical read at closest direct | Post-miss behavior |
|---|---|---:|---|---:|---:|---|---|---|---|
| F1 | `20260717T151002-a9753343` | false | env collision 6.6, 13.42s | 0 | 0 / 1 | 2.72 m @ t+2.53s, center `[329.8,339.3]` | 0.04 m @ t+3.45s, age 0.93s | gate near bottom (y≈339) ⇒ drone HIGH | approach→commit→retreat→search→approach→hover; same gate |
| F2 | `20260717T151126-a9753343` | false | env collision 7.9, 17.35s | 0 | 0 / 1 | 3.17 m @ t+2.58s, center `[372.0,331.6]` | 0.09 m @ t+3.64s, age 1.06s | gate near bottom (y≈332) ⇒ drone HIGH | approach→commit→retreat→search→approach→search; same gate |
| F3 | `20260717T151254-e179e097` | true | env collision 1.1, 10.75s | 0 | 0 / 1 | 2.93 m @ t+2.52s, center `[286.5,279.25]` | 0.08 m @ t+3.58s, age 1.01s | gate low in frame (y≈279) ⇒ drone HIGH | approach→commit→retreat→approach→commit; same gate |
| F4 | `20260717T151717-e179e097` | true | env collision 1.6, 12.93s | 0 | 0 / 1 | **1.36 m** @ t+2.92s, center `[338.6,362.7]` | 0.02 m @ t+3.38s, age 0.48s | gate bottom/out of frame (y≈363) ⇒ drone HIGH / over | approach→commit→retreat→search→approach→search→approach→hover; same gate |

No counted A/B flight passed a gate or clipped a gate. The only counted clip-like event was the environment collision abort; the pre-F1 sanity flight (not counted) had 2 gate clips.

## Terminal LIVE behavior (F3/F4)

The new live channel was enabled in F3/F4 only.

| Flight | Shadow owners | Feature/cert states | Final vertical command stats (last 4s before collision/end) | Oscillation / spike observation |
|---|---|---|---|---|
| F3 | `alt` 45, **`term` 63** | 5 features: probation 2, none 2, certified 1; BAR_FULL 5 | v_body[2] range -1.96..+0.61, mean -0.16, max adjacent jump 0.83 | Terminal owner was active. No obvious sustained oscillation; final commands transition smoothly enough, no violent sawtooth. |
| F4 | `alt` 39, `term` 0 | 6 certified BAR_FULL features | v_body[2] range -3.11..0.00, mean -0.51, max adjacent jump **2.72** | Enable bit was true, but terminal owner did not take over. There is a late abrupt vertical command ramp/spike to -3.11 in the final approach window; because owner stayed `alt`, this appears to be legacy/altitude path behavior rather than terminal-owner action. |

So: the terminal channel can own ticks (F3) without a clear oscillatory instability; F4 shows an abrupt vertical spike but **not** under terminal ownership.

## Calibration line

Exact-zero gyro bias persists on all four counted flights:

- F1: `gyro bias calibrated over 116 samples: [0. 0. 0.]; ... live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311`
- F2: same exact-zero bias (115 samples)
- F3: same exact-zero bias (116 samples)
- F4: same exact-zero bias (116 samples)

## Slice verification

Slices cover TAKEOFF→end; when exact TAKEOFF→end had <10s unique video, the slice was widened slightly before TAKEOFF while preserving the end. All committed slices have >10s unique frames and are <50 MB.

| Flight | TAKEOFF mono_ns | Slice file | Window | Unique frames | ~sec @30fps | Unique after TAKEOFF | Size |
|---|---:|---|---|---:|---:|---:|---:|
| F1 | `710956833249300` | `20260717T151002-a9753343_takeoff_to_end_wide0p5.aigprec` | TAKEOFF−0.5s → end | 315 | 10.5s | 299 | 16.1 MB |
| F2 | `711040876536500` | `20260717T151126-a9753343_takeoff_to_end.aigprec` | exact TAKEOFF→end | 413 | 13.8s | 412 | 20.7 MB |
| F3 | `711128585587200` | `20260717T151254-e179e097_takeoff_to_end_wide3p0.aigprec` | TAKEOFF−3.0s → end | 311 | 10.4s | 222 | 17.2 MB |
| F4 | `711392062761400` | `20260717T151717-e179e097_takeoff_to_end_wide1p5.aigprec` | TAKEOFF−1.5s → end | 308 | 10.3s | 262 | 16.3 MB |

Verification: decoded slices with `ChunkAssembler`, deduped by `frame_id`, and cross-checked with `scripts/reflight.py` (315 / 413 / 311 / 308 unique frames).

## Full recordings

Full embedded recordings are too large for git and are not committed. The committed slices plus full `flight.jsonl` logs are the intended artifacts.
