# Detector evaluation with classified misses

Generated 2026-07-14 by `analysis/2026-07-14-detector-eval/run_classified_eval.py`.
Reuses `HsvGateDetector` + `ChunkAssembler` over local `.aigprec` recordings
from `eni_dcim_phase1` (not committed).

## Classification method

Every assembled frame is run through the repo HSV gate detector. Misses are then
split with a **relaxed red-pixel / contour proxy** (no human labels):

1. Build a relaxed HSV red mask (hue bands 0–14 and 166–180, sat≥55, val≥45) —
   looser than the detector's sat≥90 / val≥70 so motion-blurred rings still count.
2. Morphological close; measure `red_frac` and largest external contour area.
3. Label **visible gate** if largest blob ≥120 px and blob_frac ≥0.0006, or
   red_frac ≥0.0012 with a non-trivial blob. Otherwise **no gate in view**.
4. Report rates as % of all frames:
   - (a) `no_gate_in_view_%` — expected misses (facing away / tumble / blank).
   - (b) `visible_gate_missed_%` — real detector failures.

PnP-solve % is over all frames (same as prior eval's PnP/frm).

## Per-recording summary

| recording | phase | frames | det% | PnP% | dist mean±std (m) | no-gate-in-view% | visible-gate-missed% |
|---|---|---:|---:|---:|---|---:|---:|
| `phase1-20260713T200814` | phase1d | 20156 | 95.6 | 95.5 | 16.38±5.48 | 0.1 | 4.3 |
| `20260713T202513-ea4b5f0c` | phase1e | 11133 | 97.0 | 97.0 | 16.44±5.55 | 0.1 | 2.9 |
| `20260714T045635-b9a568ab` | phase2a | 12512 | 5.9 | 5.9 | 17.66±6.60 | 91.4 | 2.7 |
| `20260714T041536-88e6e576` | phase1f | 8535 | 96.0 | 96.0 | 16.00±5.08 | 0.2 | 3.8 |
| `20260714T072732-8ff375f3` | phase2b | 9920 | 12.8 | 12.2 | 20.75±11.83 | 81.8 | 5.4 |
| `20260714T081945-bb5494d6` | phase2c | 7499 | 17.8 | 17.7 | 18.43±8.22 | 76.3 | 5.8 |
| `fixtures_slice` | phase1e-slice | 658 | 100.0 | 100.0 | 13.77±0.18 | 0.0 | 0.0 |

## Interpretation (per recording)

### `phase1-20260713T200814` (phase1d)

High raw detection (95.6%) — gate usually in view and HSV detector locks on. Classified visible-gate misses are only 4.3% of frames; remaining non-detections are mostly no-gate / off-axis (0.1%). Gate distance when detected: mean 16.4 m (std 5.5 m).

### `20260713T202513-ea4b5f0c` (phase1e)

High raw detection (97.0%) — gate usually in view and HSV detector locks on. Classified visible-gate misses are only 2.9% of frames; remaining non-detections are mostly no-gate / off-axis (0.1%). Gate distance when detected: mean 16.4 m (std 5.5 m).

### `20260714T045635-b9a568ab` (phase2a)

Raw detection collapses to 5.9%, but that number is dominated by no-gate-in-view frames (91.4%) — tumbling / facing away. True visible-gate misses are 2.7% of frames (341/12512). Gate distance when detected: mean 17.7 m (std 6.6 m).

### `20260714T041536-88e6e576` (phase1f)

High raw detection (96.0%) — gate usually in view and HSV detector locks on. Classified visible-gate misses are only 3.8% of frames; remaining non-detections are mostly no-gate / off-axis (0.2%). Gate distance when detected: mean 16.0 m (std 5.1 m).

### `20260714T072732-8ff375f3` (phase2b)

Raw detection collapses to 12.8%, but that number is dominated by no-gate-in-view frames (81.8%) — tumbling / facing away. True visible-gate misses are 5.4% of frames (533/9920). Gate distance when detected: mean 20.7 m (std 11.8 m).

### `20260714T081945-bb5494d6` (phase2c)

Raw detection collapses to 17.8%, but that number is dominated by no-gate-in-view frames (76.3%) — tumbling / facing away. True visible-gate misses are 5.8% of frames (437/7499). Gate distance when detected: mean 18.4 m (std 8.2 m).

### `fixtures_slice` (phase1e-slice)

Perfect 100% detection on this 658-frame Phase-1e slice — every frame has a clear gate and PnP solves.
No classified misses of either type. Distance is nearly constant (13.8±0.2 m), consistent with a parked /
slow approach view used as the original perception fixture.

## Aggregate

- Frames: **70413**; detections: **42260** (60.0%)
- (a) no-gate-in-view: **25330** (36.0%)
- (b) visible-gate-missed: **2823** (4.0%)

## Artifacts

- `stats.csv` — per-second timeline (`recording,time_s,frames,detections,...`)
- `hard_frames/` — 40 downscaled JPEGs (~800px) where a gate looks visible but the detector missed (`<recording>_<frame_id>.jpg`)
- `no_gate/` — 10 example frames with no gate evidence

## Notes for cloud agent

- Phase-2 raw det% of 5.9–17.8% is **not** a detector collapse by itself: most of
  those frames are classified as no-gate-in-view. Focus tuning on `visible_gate_missed`.
- Hard frames are the actionable failure set for HSV / contour thresholds.
- Large `.aigprec` sources remain only on the operator machine.
