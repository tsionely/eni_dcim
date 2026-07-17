# Phase 5e — shadow terminal-channel logging cycle (VERIFIED R2-TRAINING)

- **Date (local):** 2026-07-17 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Operator workspace:** `C:\Users\tsion\Projects\eni_dcim_phase1`
- **Code flown:** `698903b5ef99d1b6b57201671b882ec7b5220fe3` (`698903b` — "Terminal density: tracker co-runs on center-only detections + range-scaled support")
- **Command:** `scripts\fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300`
- **Label:** `phase5e-shadow`
- **SIM LOCK:** `C:\Temp\eni_dcim_sim.lock` held during the cycle.
- **Launch protocol:** verified R2-TRAINING row → pre-open race dialog → start `fly_once` → click RACE immediately after `Connected. Starting IO agents...`.

This build is intentionally non-actuating for the new terminal channel. The key deliverable is the flight logs: they now include per-tick `shadow` owner decisions plus `feature` terminal/certificate observations.

## Counted flights and excluded attempts

Five verified R2 launches were made. Attempts 1 and 2 were real R2 flights, but were not counted because their flight durations were <10s and would have failed the >10s unique-slice guard. Counted flights are attempts 3/4/5 below. The console report still records all attempts.

## Track verification

All counted flights selected the bottom row `AI-GP VIRTUAL QUALIFIER R2 - TRAINING` at click `[415,394]`. The generic race dialog was not used for event identity; R2 scene verification used the permanent `fixtures/track-id-reference/` discriminators. Evidence is under `track_verification/`.

| Counted flight | Attempt label | Row scores R1 / R2sub / R2train | Post-RACE cyan px | Track |
|---|---|---|---:|---|
| F1 | `phase5e_shadow_f_3` | 0.99977 / 0.99989 / 0.99970 | 33,677 | R2-TRAINING ✓ |
| F2 | `phase5e_shadow_f_4` | 0.99998 / 0.99999 / 0.99996 | 200,197 | R2-TRAINING ✓ |
| F3 | `phase5e_shadow_f_5` | 0.99969 / 0.99986 / 0.99990 | 28,640 | R2-TRAINING ✓ |

`RaceStatus` exposes only `active_gate_index`; all three stayed at active gate 0.

## Flight summary (build 698903b)

| Flight | Log ID | Result | Gates / active_gate | Clips / env hits | Closest direct fix | Closest believed state | Vertical read at closest direct |
|---|---|---|---:|---:|---|---|---|
| F1 | `20260717T142306-7223cc0c` | `environment collision (impulse=4.1)`, 10.21s | 0 / 0..0 | **1 clip** / 1 env | **1.19 m** @ t+5.17s, t=[+0.31,-0.20,+1.13], center px `[424.9,390.6]` | 0.07 m @ t+3.73s, age 1.10s | gate below frame/bottom (y≈391 > 360) ⇒ drone HIGH / over gate |
| F2 | `20260717T142426-7223cc0c` | `environment collision (impulse=5.6)`, 10.15s | 0 / 0..0 | 0 clips / 3 env | 2.92 m @ t+1.84s, t=[+0.76,-1.66,+2.28], center px `[408.4,151.1]` | 0.04 m @ t+2.86s, age 1.01s | gate slightly HIGH in frame (y≈151) ⇒ drone LOW |
| F3 | `20260717T142546-7223cc0c` | `environment collision (impulse=3.4)`, 11.75s | 0 / 0..0 | 0 clips / 2 env | 3.27 m @ t+8.08s, t=[-1.59,-2.21,+1.80], center px `[114.1,60.2]` | 0.05 m @ t+3.46s, age 1.37s | gate very HIGH in frame (y≈60) ⇒ drone LOW |

## Shadow / certificate / terminal-feature logging

The new log channels are present and populated in all counted flights:

| Flight | `feature` count | cert_status counts | feature modes | `shadow` count | shadow owners | adapter_ok | max |adapter_delta_mps| |
|---|---:|---|---|---:|---|---|---:|
| F1 | 29 | certified 15, probation 5, none 9 | BAR_FULL 26, BAR_ROW_ONLY 3 | 43 | alt 43 | 43/43 true | 2.0e-16 |
| F2 | 1 | none 1 | BAR_ROW_ONLY 1 | 37 | alt 37 | 37/37 true | 2.2e-16 |
| F3 | 7 | certified 6, probation 1 | BAR_FULL 7 | 125 | alt 117, **term 8** | 125/125 true | 3.3e-16 |

Sample log records:
- `feature`: `y_top_px`, `span_px`, `center_x_px`, `cert_status`, `mode` (e.g. F1 starts certified/BAR_FULL; F1 ends none/BAR_ROW_ONLY; F3 has certified/probation BAR_FULL features).
- `shadow`: `owner`, `up_legacy_mps`, `adapter_delta_mps`, `adapter_ok`.

Because `adapter_delta_mps` is effectively zero and `adapter_ok=True` throughout, the new channel behaved as a shadow/non-actuating path as expected. F3 is the only counted flight where the shadow owner selected `term` (8 ticks); the actuator path remained legacy-equivalent.

## Calibration line

The exact-zero bias persists again on 698903b:

- F1: `gyro bias calibrated over 116 samples: [0. 0. 0.]; ... live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311`
- F2: same exact-zero bias (116 samples)
- F3: same exact-zero bias (115 samples)

So the suspicious `bias=[0. 0. 0.]` remains unchanged from phase5b/5c/5d.

## Slice verification

Exact TAKEOFF→end windows were under 10s unique video for all three counted flights, so the slices were widened to full-flight while still covering TAKEOFF→end, per the now-standard guard. Each committed slice has >10s unique frames and is <50 MB.

| Flight | TAKEOFF mono_ns | Slice file | Window committed | Unique frames | ~sec @30fps | Unique after TAKEOFF | Size |
|---|---:|---|---|---:|---:|---:|---:|
| F1 | `708140737810300` | `20260717T142306-7223cc0c_takeoff_to_end_full.aigprec` | full flight, covers TAKEOFF→end | 334 | 11.1s | 209 | 16.9 MB |
| F2 | `708220693422100` | `20260717T142426-7223cc0c_takeoff_to_end_full.aigprec` | full flight, covers TAKEOFF→end | 334 | 11.1s | 204 | 18.1 MB |
| F3 | `708300881546800` | `20260717T142546-7223cc0c_takeoff_to_end_full.aigprec` | full flight, covers TAKEOFF→end | 383 | 12.8s | 254 | 20.5 MB |

Verification method: decoded with `ChunkAssembler`, deduped by `frame_id`, and cross-checked with `scripts/reflight.py` (unique frames 334 / 334 / 383).

## Full recordings (not committed)

Full embedded recordings are too large for git. The committed deduped full-flight slices are the intended analysis artifacts; full recordings remain under `logs/<flight_id>/vision.aigprec` locally.
