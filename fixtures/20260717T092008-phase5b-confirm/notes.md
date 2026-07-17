# Phase 5b confirm — VERIFIED R2-TRAINING cycle

- **Date (local):** 2026-07-17 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Operator workspace:** `C:\Users\tsion\Projects\eni_dcim_phase1` (Option A real team clone)
- **Code flown:** `b66e8ed318f2635d1e598524ccd56edccef178b9` (`b66e8ed`)
- **Command:** `scripts\fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300`
- **SIM LOCK:** `C:\Temp\eni_dcim_sim.lock` held during the cycle.
- **Launch procedure:** pre-open race dialog with no pilot; start `fly_once`; click RACE immediately after `Connected. Starting IO agents...`.

## Track-ID correction and permanent reference

The earlier visual protocol was ambiguous because **R1 also has a dark scene,
red square gates, and a cyan racing line**. Before flying this cycle I captured
an explicit R1-vs-R2 reference in `fixtures/track-id-reference/`.

For every counted flight here, selection used the deterministic text-template
helper on the ACTIVE EVENTS list:

- verified rows visible: `R1`, `R2 - SUBMISSION`, and `R2 - TRAINING`, all
  template-matched at ~1.000;
- selected row: **`AI-GP VIRTUAL QUALIFIER R2 - TRAINING`** (bottom row);
- click point: **[415,394]** (matched R2-TRAINING row center);
- race dialog is generic and not trusted for event identity;
- after RACE, the scene was checked against the R2 discriminators: hangar floor,
  station-number pillars, traffic-light posts, parked jets, first gate close to
  the pad. Verification screenshots/status JSONs are under
  `track_verification/`.

Telemetry note: `RaceStatus` exposes `active_gate_index` only; there is no total
track gate count field in the log. All three counted flights remained on
`active_gate_index=0`.

## Flights

| Flight | Log ID | Verified selected row | Scene discriminators | Result | Gates / active_gate | Clips / env hits | Closest direct fix | Closest believed state | Post-miss behavior | Calibration / anomaly |
|---|---|---|---|---|---:|---:|---|---|---|---|
| F1 | `20260717T090941-debf3ec1` | R2-TRAINING, click `[415,394]`, row scores R1/R2sub/R2train = 0.99965/0.99974/0.99966 | R2 hangar: station pillars + traffic posts + parked jets; cyan px 34,766 | `environment collision (impulse=2.6)`, 10.50s | 0 passed, active_gate_index 0..0 | 0 clips / 3 env | 3.75 m (image center low/bottom: center y 328.5) | 0.04 m, age 1.28s (believed essentially through gate) | **Retreat and retry same gate:** `approach -> commit -> retreat -> search -> approach`, active gate stayed 0 | `live calibration (180 samples): bias=[0. 0. 0.] level roll=+0.000 pitch=-0.311`; loop overrun 0.15% |
| F2 | `20260717T091107-debf3ec1` | R2-TRAINING, click `[415,394]`, row scores 0.99956/0.99974/0.99966 | R2 hangar verified; cyan px 49,151 | `environment collision (impulse=13.6)`, 11.19s | 0 passed, active_gate_index 0..0 | 0 clips / 2 env | 2.14 m, center y 271.5 | 0.31 m, age 1.18s | **Retreat and retry same gate:** `approach -> commit -> retreat -> approach`, active gate stayed 0 | same live calibration values; loop overrun 1.43% |
| F3 | `20260717T091239-debf3ec1` | R2-TRAINING, click `[415,394]`, row scores 0.99990/0.99996/0.99997 | R2 hangar verified; cyan px 27,521 | `environment collision (impulse=30.5)`, 14.40s | 0 passed, active_gate_index 0..0 | **4 clips** / 1 env | **0.88 m** (closest direct), center y 255.0 | 0.69 m, age 0.09s | Collision/gate clips, then recover and re-approach/search same active gate | same live calibration values; loop overrun 0.17% |

## Operator observations

- **Gate-in-view / yaw tracking:** The verified R2 spectator frames show the
  drone does not immediately slide the first gate out the side as in earlier
  phase5 material; it closes fast with the R2 scene still identifiable. However,
  F1/F2 direct fixes stop at 3.75 m / 2.14 m while the believed state runs much
  closer, so the final approach is still partly dead-reckoned. F3 got real close
  fixes down to 0.88 m and then clipped/impacted.
- **Actual proximity:** no official pass. F3 is the closest and most useful:
  direct fix 0.88 m, believed 0.69 m, 4 gate clips, then a hard env collision.
- **Vertical / high-low:** F1's closest direct detection is low in the image
  (center y 328.5) while the state believes it is already through the gate;
  spectator frame F3_002 shows the drone pitched/climbed toward the ceiling
  grid shortly before the clip/impact sequence. This is consistent with the
  vertical channel remaining the open front.
- **Post-miss behavior:** relock/retry stayed local. All attempts kept
  `active_gate_index=0`; no far-gate chase was observed.
- **Event metadata:** no event name appears in the generic dialog or window
  title. Track ID is therefore backed by verified row selection plus vision
  scene features, not by window title.

## Slice verification

The old `slice_start` mistake was avoided. For each flight I located the FSM
`dst="TAKEOFF"` line and cut a slice that covers from TAKEOFF to the flight end.
Because F1/F2 takeoff-to-end lasted only ~7-8 seconds of unique video, those
slices were widened to include the pre-takeoff part of the same flight so the
committed slice contains >10 seconds of unique frames. F3 is exact
TAKEOFF->end.

| Flight | TAKEOFF `mono_ns` | Slice file | Window committed | Unique frames in slice | Approx seconds (@30fps) | Unique frames after TAKEOFF | Size |
|---|---:|---|---|---:|---:|---:|---:|
| F1 | `689334080451100` | `20260717T090941-debf3ec1_takeoff_to_end_full.aigprec` | full flight, covers TAKEOFF->end | 344 | 11.5s | 217 | 16.7 MB |
| F2 | `689420792003800` | `20260717T091107-debf3ec1_takeoff_to_end_full.aigprec` | full flight, covers TAKEOFF->end | 367 | 12.2s | 233 | 18.4 MB |
| F3 | `689513381942600` | `20260717T091239-debf3ec1_takeoff_to_end.aigprec` | exact TAKEOFF->end | 321 | 10.7s | 320 | 14.0 MB |

Verification method: decoded the slices using `ChunkAssembler`, deduped by
`frame_id`, and cross-checked with `scripts/reflight.py`, which reported unique
frames 344 / 367 / 321 respectively.

Reflight quick stats on these slices:
- F1: 344 unique frames, closest replay fix in 3-5 m bin only.
- F2: 367 unique frames, closest replay fix 2.14 m.
- F3: 321 unique frames, replay fixes down to 0.73-0.88 m range, confirming the
  useful close-range gate-clip material.

## Full recordings

The embedded full recordings are too large for git and were not committed:
- F1 `logs/20260717T090941-debf3ec1/vision.aigprec` (~505 MB)
- F2 `logs/20260717T091107-debf3ec1/vision.aigprec` (~517 MB)
- F3 `logs/20260717T091239-debf3ec1/vision.aigprec` (~661 MB)

The committed deduped slices are the intended analysis artifacts.
