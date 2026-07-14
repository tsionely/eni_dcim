# Cross-checks — DATA ANALYST

Date: 2026-07-14. Sources: operator checkout
`C:\Users\tsion\Projects\eni_dcim_phase1` recordings/logs + GitHub clone code.

## Findings (evidence-backed)

### 1. Detection collapses on Phase-2 moving flights

| recording | frames | det% | notes |
|---|---:|---:|---|
| phase1-20260713T200814 (race vision) | 20156 | 95.6 | parked/stable view of track |
| 20260713T202513-ea4b5f0c (phase1e) | 11133 | 97.0 | near-zero gyro std (parked) |
| 20260714T041536-88e6e576 (phase1f) | 8535 | 96.0 | near-zero gyro std |
| 20260714T045635-b9a568ab (phase2a) | 12512 | **5.9** | gyro std large — MOVING/tumble |
| 20260714T072732-8ff375f3 (phase2b) | 9920 | **12.8** | MOVING; center jump p95 19 px |
| 20260714T081945-bb5494d6 (phase2c) | 7499 | **17.8** | MOVING; 1 gap >50 ms |

**Flag for cloud agent:** red-HSV detector that scored 100% on the parked phase1e
slice is **not robust under Phase-2 flight dynamics**. PnP is fine when a quad is
found (~95–100% of detections). Failure mode is contour/HSV miss, not solvePnP.

### 2. IMU motion vs detection rate (kinematics cross-link)

From `analysis/20260714-flight-kinematics.md`:

- Phase-1e/1f: gyro std ≈ 0 → PARKED → high vision det% in matching recordings.
- Phase-2a/2b/2c: gyro std ≫ 0.05 → MOVING → low vision det%.

This is consistent with motion blur / large roll-pitch taking the red ring out of
the assumed frontal appearance / HSV thresholds.

### 3. Decode / clock health

- JPEG decode failures: **0** across evaluated recordings.
- Frame gaps >50 ms: rare (one 52.2 ms gap on phase2c). No systematic dropouts.
- Distance step instability: elevated on phase2b (p95 abs Δd high) when detections
  are sparse — expected when the active gate switches or false quads appear.

### 4. Do not treat early-frame misses as primary hard cases

Initial mining overweighted frame_id 0–13 menu/boot misses from the large phase1d
recording. Re-mined with mid-race preference + parent-folder diversity (see
`analysis/hard_frames/`).

## Not fixed (out of DATA ANALYST scope)

- Detector confidence still hard-coded to `1.0` in `gate_detector_hsv.py`.
- No code/config changes made; cloud agent owns robustness work.

## Artifacts

- `analysis/20260714-detector-eval-at-scale.md`
- `analysis/detector_eval_metrics.json`
- `analysis/hard_frames/`
- `analysis/20260714-flight-kinematics.md`
- `analysis/plots/`
- `fixtures/20260714T111500-analysis-slices/`
