# Detector evaluation v2 (relaxed HSV thresholds)

Generated 2026-07-14 by `analysis/2026-07-14-detector-eval-v2/run_classified_eval.py`.
Uses **current** repo `HsvGateDetector` defaults from `config/params_default.json`
(sat≥60 / val≥50; previously sat≥90 / val≥70 in the v1 eval).
Same miss classification as `analysis/2026-07-14-detector-eval/report.md`.

## Classification method

Every assembled frame is run through the repo HSV gate detector. Misses are then
split with a **relaxed red-pixel / contour proxy** (no human labels):

1. Build a relaxed HSV red mask (hue bands 0–14 and 166–180, sat≥55, val≥45) —
   looser than the detector's sat≥60 / val≥50 so motion-blurred rings still count.
2. Morphological close; measure `red_frac` and largest external contour area.
3. Label **visible gate** if largest blob ≥120 px and blob_frac ≥0.0006, or
   red_frac ≥0.0012 with a non-trivial blob. Otherwise **no gate in view**.
4. Report rates as % of all frames:
   - (a) `no_gate_in_view_%` — expected misses (facing away / tumble / blank).
   - (b) `visible_gate_missed_%` — real detector failures.

PnP-solve % is over all frames (same as prior eval's PnP/frm).

## Before vs after (visible-gate-missed%)

Comparison against `analysis/2026-07-14-detector-eval/report.md` (sat90/val70 era).

| recording | phase | v1 vis-miss% | v2 vis-miss% | delta (pp) |
|---|---|---:|---:|---:|
| `phase1-20260713T200814` | phase1d | 4.3 | 1.6 | -2.7 |
| `20260713T202513-ea4b5f0c` | phase1e | 2.9 | 1.2 | -1.7 |
| `20260714T045635-b9a568ab` | phase2a | 2.7 | 2.0 | -0.8 |
| `20260714T041536-88e6e576` | phase1f | 3.8 | 1.6 | -2.2 |
| `20260714T072732-8ff375f3` | phase2b | 5.4 | 4.8 | -0.6 |
| `20260714T081945-bb5494d6` | phase2c | 5.8 | 5.0 | -0.8 |
| `fixtures_slice` | phase1e-slice | 0.0 | 0.0 | +0.0 |

**Same-set aggregate** (v1 recording keys only): v1 visible-gate-missed **4.0%** (2823/70413) → v2 **2.4%** (1685/70413) (Δ -1.6 pp).

## Per-recording summary (all local recordings)

| recording | phase | frames | det% | PnP% | dist mean±std (m) | no-gate-in-view% | visible-gate-missed% |
|---|---|---:|---:|---:|---|---:|---:|
| `phase1-20260713T200814` | phase1d | 20156 | 98.3 | 98.3 | 15.76±5.37 | 0.1 | 1.6 |
| `20260713T202513-ea4b5f0c` | phase1e | 11133 | 98.7 | 98.7 | 15.61±5.24 | 0.1 | 1.2 |
| `20260714T045635-b9a568ab` | phase2a | 12512 | 6.6 | 6.6 | 17.39±6.90 | 91.4 | 2.0 |
| `20260714T041536-88e6e576` | phase1f | 8535 | 98.2 | 98.2 | 15.28±4.80 | 0.2 | 1.6 |
| `20260714T072732-8ff375f3` | phase2b | 9920 | 13.4 | 13.0 | 19.43±10.56 | 81.8 | 4.8 |
| `20260714T081945-bb5494d6` | phase2c | 7499 | 18.6 | 18.3 | 16.75±6.80 | 76.3 | 5.0 |
| `fixtures_slice` | phase1e-slice | 658 | 100.0 | 100.0 | 13.63±2.13 | 0.0 | 0.0 |
| `20260714T122243-73ed53b1` | phase2h | 10148 | 25.8 | 23.8 | 19.03±7.09 | 58.9 | 15.2 |
| `20260714T110643-02cf6940` | phase2f-B | 8982 | 30.8 | 30.8 | 19.53±7.08 | 54.6 | 14.7 |
| `20260714T132005-1429a43c` | phase2j-V1 | 9958 | 28.7 | 28.6 | 22.86±10.86 | 56.6 | 14.7 |
| `20260714T132354-80030858` | phase2j-V2 | 10203 | 17.3 | 17.3 | 18.42±7.01 | 70.9 | 11.8 |
| `20260714T125600-73ed53b1` | phase2i | 7141 | 25.2 | 22.6 | 17.33±7.98 | 56.0 | 18.8 |
| `20260714T120153-73ed53b1` | phase2g | 6235 | 37.3 | 37.3 | 19.93±8.68 | 47.1 | 15.7 |
| `20260714T110032-62997d9b` | phase2f-A | 5143 | 98.6 | 98.6 | 17.41±6.49 | 0.0 | 1.4 |
| `20260714T113457-36aa6178` | phase2f-C | 3994 | 60.5 | 56.7 | 17.80±6.91 | 23.5 | 15.9 |
| `phase1e-inflight` | unknown | 515 | 100.0 | 100.0 | 15.39±4.80 | 0.0 | 0.0 |
| `phase1e_countdown_and_gate` | unknown | 463 | 100.0 | 100.0 | 13.36±0.64 | 0.0 | 0.0 |

## Interpretation (per recording)

### `phase1-20260713T200814` (phase1d)

High raw detection (98.3%) — gate usually in view and HSV detector locks on. Classified visible-gate misses are only 1.6% of frames; remaining non-detections are mostly no-gate / off-axis (0.1%). Gate distance when detected: mean 15.8 m (std 5.4 m).

### `20260713T202513-ea4b5f0c` (phase1e)

High raw detection (98.7%) — gate usually in view and HSV detector locks on. Classified visible-gate misses are only 1.2% of frames; remaining non-detections are mostly no-gate / off-axis (0.1%). Gate distance when detected: mean 15.6 m (std 5.2 m).

### `20260714T045635-b9a568ab` (phase2a)

Raw detection collapses to 6.6%, but that number is dominated by no-gate-in-view frames (91.4%) — tumbling / facing away. True visible-gate misses are 2.0% of frames (244/12512). Gate distance when detected: mean 17.4 m (std 6.9 m).

### `20260714T041536-88e6e576` (phase1f)

High raw detection (98.2%) — gate usually in view and HSV detector locks on. Classified visible-gate misses are only 1.6% of frames; remaining non-detections are mostly no-gate / off-axis (0.2%). Gate distance when detected: mean 15.3 m (std 4.8 m).

### `20260714T072732-8ff375f3` (phase2b)

Raw detection collapses to 13.4%, but that number is dominated by no-gate-in-view frames (81.8%) — tumbling / facing away. True visible-gate misses are 4.8% of frames (474/9920). Gate distance when detected: mean 19.4 m (std 10.6 m).

### `20260714T081945-bb5494d6` (phase2c)

Raw detection collapses to 18.6%, but that number is dominated by no-gate-in-view frames (76.3%) — tumbling / facing away. True visible-gate misses are 5.0% of frames (376/7499). Gate distance when detected: mean 16.8 m (std 6.8 m).

### `fixtures_slice` (phase1e-slice)

High raw detection (100.0%) — gate usually in view and HSV detector locks on. Classified visible-gate misses are only 0.0% of frames; remaining non-detections are mostly no-gate / off-axis (0.0%). Gate distance when detected: mean 13.6 m (std 2.1 m).

### `20260714T122243-73ed53b1` (phase2h)

Moderate detection (25.8%). No-gate frames 58.9%; visible-gate misses 15.2% — these are the actionable detector failures. Gate distance when detected: mean 19.0 m (std 7.1 m).

### `20260714T110643-02cf6940` (phase2f-B)

Moderate detection (30.8%). No-gate frames 54.6%; visible-gate misses 14.7% — these are the actionable detector failures. Gate distance when detected: mean 19.5 m (std 7.1 m).

### `20260714T132005-1429a43c` (phase2j-V1)

Moderate detection (28.7%). No-gate frames 56.6%; visible-gate misses 14.7% — these are the actionable detector failures. Gate distance when detected: mean 22.9 m (std 10.9 m).

### `20260714T132354-80030858` (phase2j-V2)

Raw detection collapses to 17.3%, but that number is dominated by no-gate-in-view frames (70.9%) — tumbling / facing away. True visible-gate misses are 11.8% of frames (1202/10203). Gate distance when detected: mean 18.4 m (std 7.0 m).

### `20260714T125600-73ed53b1` (phase2i)

Moderate detection (25.2%). No-gate frames 56.0%; visible-gate misses 18.8% — these are the actionable detector failures. Gate distance when detected: mean 17.3 m (std 8.0 m).

### `20260714T120153-73ed53b1` (phase2g)

Moderate detection (37.3%). No-gate frames 47.1%; visible-gate misses 15.7% — these are the actionable detector failures. Gate distance when detected: mean 19.9 m (std 8.7 m).

### `20260714T110032-62997d9b` (phase2f-A)

High raw detection (98.6%) — gate usually in view and HSV detector locks on. Classified visible-gate misses are only 1.4% of frames; remaining non-detections are mostly no-gate / off-axis (0.0%). Gate distance when detected: mean 17.4 m (std 6.5 m).

### `20260714T113457-36aa6178` (phase2f-C)

Moderate detection (60.5%). No-gate frames 23.5%; visible-gate misses 15.9% — these are the actionable detector failures. Gate distance when detected: mean 17.8 m (std 6.9 m).

### `phase1e-inflight` (unknown)

High raw detection (100.0%) — gate usually in view and HSV detector locks on. Classified visible-gate misses are only 0.0% of frames; remaining non-detections are mostly no-gate / off-axis (0.0%). Gate distance when detected: mean 15.4 m (std 4.8 m).

### `phase1e_countdown_and_gate` (unknown)

High raw detection (100.0%) — gate usually in view and HSV detector locks on. Classified visible-gate misses are only 0.0% of frames; remaining non-detections are mostly no-gate / off-axis (0.0%). Gate distance when detected: mean 13.4 m (std 0.6 m).

## Aggregate (all recordings this run)

- Frames: **133195**; detections: **65994** (49.5%)
- (a) no-gate-in-view: **56954** (42.8%)
- (b) visible-gate-missed: **10247** (7.7%)

## Artifacts

- `stats.csv` — per-second timeline (`recording,time_s,frames,detections,...`)
- `hard_frames/` — 9 downscaled JPEGs (~800px) where a gate looks visible but the detector missed (`<recording>_<frame_id>.jpg`)
- `no_gate/` — 4 example frames with no gate evidence

## Notes

- Detector thresholds for this run: sat≥60, val≥50 (`params_default.json`).
- Evidence proxy unchanged (sat≥55 / val≥45) so miss classification stays comparable.
- Large `.aigprec` sources remain only on the operator machine.
