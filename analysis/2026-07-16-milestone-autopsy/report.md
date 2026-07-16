# Milestone autopsy + inter-gate frontier

AGENTS.md DATA ANALYST CURRENT TASK (HEAD ≥ `3d37d99`).
Milestone flight: `20260716T131137-2ca531c3` in `fixtures/20260716T132549-phase3j-r2training-rerun`.

## 1. Crossing-miss map extension (phase3i + phase3j-rerun + PASS)

See `miss_map_extension.md`, `miss_table.csv`, `plots/miss_scatter_with_pass.png`.

### PASS crossing vector (first ground-truth success)

| field | value |
|---|---|
| closest dist | **0.103 m** |
| lateral | **+0.006 m** ( + = aircraft LEFT ) |
| vertical | **+0.100 m** ( + = aircraft HIGH ) |
| gate_rel_age | 1.08 s |
| cycle | `approach+commit+approach+commit+retreat` |

### New phases at a glance (ok, dist≤5m)

| phase | n | mean lat | mean vert | rms |
|---|---:|---:|---:|---:|
| phase3i | 3 | -0.03 | +0.14 | 0.16 |
| phase3j_rerun | 5 | -0.03 | +0.06 | 0.25 |

## 2. Inter-gate segment study (pass → collision)

![intergate](plots/intergate_kinematics.png)

### Timeline corrections vs AGENTS.md wording

| AGENTS.md | Measured on log |
|---|---|
| pass t≈25.4 | **agi 0→1 at t=26.371s**; closest STATE at t=26.2251324s |
| commit→retreat t≈31.6 | **[(32.4854292, 'commit'), (32.6850963, 'retreat'), (34.7055027, 'approach'), (35.3454404, 'search'), (35.4255074, 'approach')]** |
| collision t≈38.9 | **t=39.787s** impulse=15.537909507751465 |

### Gate-2 lock quality

- Inter-gate STATE samples: **636**
- Mean `gate_rel_age_s`: **0.4103572022515723**
- Max age: **1.488557856**
- After the pass the pipeline re-arms on a far gate (~18 m). Approach closes range to ~2–4 m by t≈32, then a **0.20 s commit** flips to **retreat** (age≈1.0 s — stale lock / corridor breach), backs off, re-approaches, then wanders with lock jumps (dist 14→40 m) before the hard env hit.

### Brief commit→retreat

Measured cycle (not 31.6):

- t=32.485s → `commit`
- t=32.685s → `retreat`
- t=34.706s → `approach`
- t=35.345s → `search`
- t=35.426s → `approach`

Interpretation: gate-2 attempt aborted almost immediately — age-aware lock was already stale (~0.8–1.0 s) at commit entry; retreat fired, then the second approach never re-acquired a clean close lock before the obstacle strike.

### What did it hit?

Frames: `collision_frames/` (operator `f4_*` + any extracted vision frames).

- `f4_end.jpg`: edge vert_peak=39.7 horiz_peak=255.0 (high vert_peak suggests pillar/column structure).
- `f4_late.jpg`: edge vert_peak=54.4 horiz_peak=152.0 (high vert_peak suggests pillar/column structure).
- `f4_mid.jpg`: edge vert_peak=26.1 horiz_peak=96.6 (high vert_peak suggests pillar/column structure).
- Kinematics: in the last 1s before collision, STATE `gate_rel` dist jumped ~14m→40m (lock switch / far gate), while flying straight toward the stale/next lock — consistent with an intervening obstacle not in the gate model.

- Vision coverage: `{"path": "C:\\Users\\tsion\\Projects\\eni_dcim_phase1\\logs\\20260716T131137-2ca531c3\\vision.aigprec", "n_assembled_frames": 4512, "rec_duration_s": 22.2347633, "flight_t_first": 17.7544988, "flight_t_last": 39.9892621, "covers_pass": true, "covers_collision": true}`

## 3. Cyan line as obstacle-free corridor (phase4b input)

HSV bands (from R2 deep-dive): H∈[90,98], S≥120, V≥120.

### Recording windows

| label | frames | cyan-present% | mean frac | max absent gap (s) |
|---|---:|---:|---:|---:|
| `pass_full_local` | 4512 | 53.8 | 0.0074 | 8.02 |
| `pass_intergate` | 2559 | 26.0 | 0.0022 | 7.81 |
| `pass_pre_pass` | 1687 | 95.5 | 0.0149 | 0.21 |
| `slice_203252-phase3a-r2tr_2_f2_slice_start` | 111 | 100.0 | 0.0334 | 0.00 |
| `slice_115732-phase3i-r2tr__r2i_slice_start` | 198 | 100.0 | 0.0292 | 0.00 |
| `slice_132549-phase3j-r2tr_erun_slice_start` | 290 | 100.0 | 0.0343 | 0.00 |

### Operator screens (collision context)

- `f4_mid.jpg`: cyan_frac=0.0000 (absent/weak)
- `f4_late.jpg`: cyan_frac=0.0013 (absent/weak)
- `f4_end.jpg`: cyan_frac=0.0003 (absent/weak)

### Verdict (phase4b navigation design)

**NO — not continuously segmentable in this window** (present 26%). Do not bet phase4b on cyan-only corridor follow without better inter-gate recordings.

Would following the line have avoided the hit?

- **Cannot prove from pixels yet** (inter-gate frames missing/short). Kinematically the hit is a straight-line chase after a failed gate-2 commit; any corridor prior (cyan or map) that keeps the path off pillars/aircraft would address the failure mode. **Collect inter-gate slice next.**

## Deliverables

- `report.md` (this file)
- `miss_map_extension.md`, `miss_table.csv`, `plots/miss_scatter_with_pass.png`
- `intergate_summary.json`, `plots/intergate_kinematics.png`, `collision_frames/`
- `cyan_corridor_summary.json`, `cyan_frames/`, `plots/cyan_timeline_*.png`
- Shared miss-map refresh: `analysis/2026-07-15-crossing-miss-map/miss_table.csv` + scatter
