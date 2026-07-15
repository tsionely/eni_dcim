# R2 deep-dive (phase3a-r2training)

Generated 2026-07-14 by `analysis/2026-07-14-r2-deepdive/run_r2_deepdive.py`.
Sources: `fixtures/20260714T203252-phase3a-r2training/` (committed slices + flight.jsonl).
Implements AGENTS.md DATA ANALYST CURRENT TASK: cyan line / FP audit / sensor model.

## 1. Cyan racing-line study

### Recommended HSV bands (OpenCV H 0–180)

- **Recommended:** H∈[90, 98], S≥120, V≥120 (seed used in analysis: H∈[88,102], S≥100, V≥90).
- Sweep best mean_frac=0.0172, score=0.942.

| slice | frames | cyan-present% | H mean±std | S mean | V mean | gate frames | line-through-next-gate% |
|---|---:|---:|---|---:|---:|---:|---:|
| `r2_f2` | 111 | 100.0 | 98.5±1.2 | 197 | 139 | 93 | 100.0 |
| `r2_f3` | 416 | 100.0 | 98.6±0.8 | 195 | 134 | 407 | 100.0 |

### Does the line always pass through the next gate?

Proxy: nearest red convex quad (largest area) = next/active gate; cyan mask within 32 px of its center.

- `r2_f2`: **100.0%** of gate-visible frames have cyan through the opening (93/93).
- `r2_f3`: **100.0%** of gate-visible frames have cyan through the opening (407/407).

Interpretation: the glowing cyan ribbon is highly saturated (H≈90–100) and segmentable with a cheap
HSV mask at high reliability when the line is in view. When a gate is visible, the line usually
threads the opening — usable as an active-gate / path prior for planning (see detector TODO).

Annotated frames: `cyan_frames/<slice>/`.

## 2. Detector false-positive audit

Repo `HsvGateDetector` (params_default) on both slices. Orbs = circular red blobs;
signs = non-quad red blobs; multi-quad = ≥2 red 4-gons (other gates).

| slice | frames | det% | PnP% | orb-like frames | sign-like frames | multi-quad det frames | det locked on orb |
|---|---:|---:|---:|---:|---:|---:|---:|
| `r2_f2` | 111 | 83.8 | 83.8 | 90 | 111 | 0 | 0 (0.0% of dets) |
| `r2_f3` | 416 | 97.8 | 97.8 | 349 | 416 | 0 | 0 (0.0% of dets) |

### Ring / 4-gon test vs E-signs and pink orbs

- **Orbs / start lights:** mostly rejected — circular blobs fail the convex 4-gon + rectangularity path.
  `detector_locked_on_orb` counts near-zero if the ring test holds.
- **Red E / station signs:** filled non-quad red regions are rejected the same way; they inflate
  `sign-like` frame counts but rarely become the chosen detection.
- **Real risk:** multiple AI-GP gates in view — largest-area wins (known); cyan line should
  disambiguate which opening is next (task 1).

Example frames: `fp_frames/<slice>/`.

## 3. Sensor-model audit (docs/07 correlations)

Pixel motion of detection `center_px` vs integrated raw gyro over the same mono-time gap.
Expected if gyro truthful + body-fixed cam: pitch→Δv slope ≈ +fx (~320 px/rad).
docs/07 found negative slopes ⇒ `gyro_sign=-1`. Per-axis scale ≈ |slope|/fx.
Pair window: dt ∈ [5, 350] ms (widened vs first pass so dense phase3a detections pair).

| flight | status | N pairs | corr(Δpitch,Δv) | slope pitch→v | corr(Δroll,Δu) | slope roll→u | gyro_scale pitch | gyro_scale roll |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `f1_novision` | insufficient_detections | — | — | — | — | — | — | — |
| `f2` | ok | 225 | -0.60 | -274 | 0.22 | 235 | 0.86 | 0.73 |
| `f3` | ok | 668 | -0.37 | -324 | 0.16 | 239 | 1.01 | 0.75 |

Plots: `plots/*_pixel_vs_gyro.png`.

### Verdict vs docs/07

- Pitch: corr(Δpitch,Δv)=-0.60, slope=-274 px/rad → **gyro_sign=-1** holds; gyro_scale_pitch≈0.86.
- Confirmed on `f3`: corr=-0.37, scale_pitch≈1.01, scale_roll≈0.75.
- Per-axis gyro_scale (mean over ok flights): pitch **0.94**, roll **0.74** (docs/07 cited ~1.0–1.1).

## Deliverables

- `report.md` (this file)
- `summary.json`
- `cyan_frames/`, `fp_frames/`, `plots/`
- `cyan_timeline.csv`
