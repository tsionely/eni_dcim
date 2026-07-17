# Phase 5d — vertical plausibility / sink-insurance cycle (VERIFIED R2-TRAINING)

- **Date (local):** 2026-07-17 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Operator workspace:** `C:\Users\tsion\Projects\eni_dcim_phase1`
- **Code flown:** `9e640307003ed8bef55d44ac58f21cc850bd733b` (`9e64030` — "height-plausibility gate + top-up sink insurance")
- **Command:** `scripts\fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300`
- **Label:** `phase5d-vertical`
- **SIM LOCK:** `C:\Temp\eni_dcim_sim.lock` held during the cycle.
- **Launch protocol:** verified R2-TRAINING row → pre-open race dialog → start `fly_once` → click RACE immediately after `Connected. Starting IO agents...`.

## Track verification

All counted flights used the deterministic ACTIVE EVENTS template selector and selected the bottom row `AI-GP VIRTUAL QUALIFIER R2 - TRAINING` at click `[415,394]`. The generic race dialog is not trusted for identity; R2 scene verification uses the permanent `fixtures/track-id-reference/` discriminators (hangar floor, station pillars, traffic posts, parked jets, cyan ribbon). Evidence is under `track_verification/`.

| Flight | Row scores R1 / R2sub / R2train | Click | Post-RACE cyan px | Track |
|---|---|---|---:|---|
| F1 | 0.99968 / 0.99968 / 0.99939 | [415,394] | 30,361 | R2-TRAINING ✓ |
| F2 | 0.99954 / 0.99962 / 0.99957 | [415,394] | 201,786 | R2-TRAINING ✓ |
| F3 | 0.99958 / 0.99967 / 0.99959 | [415,394] | 26,954 | R2-TRAINING ✓ |

`RaceStatus` exposes only `active_gate_index`; all three stayed at active gate 0.

## Flights (build 9e64030)

| Flight | Log ID | Result | Gates / active_gate | Clips / env hits | Closest direct fix | Closest believed state | Vertical read at closest direct | Gate passed / clip details |
|---|---|---|---:|---:|---|---|---|---|
| F1 | `20260717T101837-7223cc0c` | `environment collision (impulse=4.7)`, 14.46s | 0 / 0..0 | 0 / 10 | 2.92 m @ t+3.55s, t=[-1.05,-0.76,2.62], center px `[201.75,259.75]` | 0.14 m @ t+4.73s, age 1.04s | gate LOW in frame (y≈260/360) ⇒ drone HIGH relative to opening | no gate-pass, no gate clips; many low-impulse env contacts during/after retreat, final env hit at t+11.21s |
| F2 | `20260717T102007-7223cc0c` | `environment collision (impulse=3.9)`, 15.24s | 0 / 0..0 | 0 / 36 | 1.89 m @ t+7.75s, t=[+0.64,-1.24,1.27], center px `[445.18,118.49]` | 0.07 m @ t+3.40s, age 1.23s | gate HIGH in frame (y≈118/360) ⇒ drone LOW | no gate-pass, no gate clips; many low-impulse env contacts after first retreat, final env hit at t+11.98s |
| F3 | `20260717T102132-7223cc0c` | `environment collision (impulse=4.8)`, 18.42s | 0 / 0..0 | 0 / 2 | **0.88 m** @ t+6.81s, t=[-0.04,-0.70,0.52], center px `[318.5,74.5]` | 0.88 m @ t+13.08s, age 0.85s | gate very HIGH in frame (y≈75/360) ⇒ drone LOW | no gate-pass, no gate clips; two final env impacts at t+15.16s (4.77 / 9.49) |

## Watch-item answers

1. **Post-retreat ceiling climbs:** improved but **not eliminated**. The far-fiction chase appears gated (all flights stayed on active_gate_index 0; no far-gate steal), but F2 spectator frame `phase5d_vertical_f_2_002` still shows a ceiling/upper-truss view around the retreat/collision window (Station 21, 15 km/h). So: no evidence of a next-gate/far-fiction chase, but there are still upper-truss/ceiling excursions after retreat/collision.
2. **Terminal arrivals high/low/centered:** mixed, but mostly still LOW at the useful terminal fixes:
   - F1 closest direct gate center y≈260 ⇒ gate below image center ⇒ drone HIGH.
   - F2 y≈118 ⇒ gate high in image ⇒ drone LOW.
   - F3 y≈75 ⇒ gate very high in image ⇒ drone LOW.
   Previous phase5c read LOW ~0.4-0.5m; phase5d still has LOW terminal arrivals on F2/F3, with F3 closest direct 0.88m.
3. **Gate passed / clips:** no official gate passes and **no gate clips** this cycle. All aborts are environment collisions. This differs from phase5c F1 (1 clip) and phase5b F3 (4 clips).
4. **Calibration line:** still exact-zero bias on all three flights:
   - `gyro bias calibrated over 117-118 samples: [0. 0. 0.]; level ref roll=+0.000 pitch=-0.311`
   - `live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311`
   The suspicious `bias=[0. 0. 0.]` persists on 9e64030.

## Phase/retry behavior

- F1: `hover -> takeoff -> approach -> commit -> retreat -> recover -> search -> approach`
- F2: `hover -> takeoff -> approach -> commit -> retreat -> recover -> search -> approach -> commit -> retreat -> search -> hover`
- F3: `hover -> takeoff -> approach -> commit -> retreat -> approach -> search -> approach -> commit -> retreat -> search -> hover`

All retries/reacquisitions remained on the same active gate (0). No far-gate chase observed in telemetry.

## Slice verification (exact TAKEOFF->end)

All three exact TAKEOFF→end slices exceed 10 seconds of unique frames, so no widened/full-flight fallback was needed.

| Flight | TAKEOFF mono_ns | Slice file | Unique frames | ~sec @30fps | Size |
|---|---:|---|---:|---:|---:|
| F1 | `693470811231300` | `20260717T101837-7223cc0c_takeoff_to_end.aigprec` | 338 | 11.3s | 17.1 MB |
| F2 | `693560636270700` | `20260717T102007-7223cc0c_takeoff_to_end.aigprec` | 360 | 12.0s | 14.4 MB |
| F3 | `693645237695100` | `20260717T102132-7223cc0c_takeoff_to_end.aigprec` | 456 | 15.2s | 20.5 MB |

Verification method: decoded slices with `ChunkAssembler`, deduped by `frame_id`, and cross-checked with `scripts/reflight.py` (unique frames 338 / 360 / 456). Reflight closest fix ranges: F1 2.92m, F2 2.92m in replay (live log closest direct 1.89m), F3 0.88m.

## Full recordings (not committed)

Full embedded recordings are too large for git:
- F1 `logs/20260717T101837-7223cc0c/vision.aigprec`
- F2 `logs/20260717T102007-7223cc0c/vision.aigprec`
- F3 `logs/20260717T102132-7223cc0c/vision.aigprec`

Committed deduped TAKEOFF→end slices are the analysis artifacts.
