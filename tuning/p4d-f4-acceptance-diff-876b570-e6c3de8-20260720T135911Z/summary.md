# P4(d) F4 Acceptance Diff

Scope: recorded F4 replay/CSV only; no simulator launched.
Repo HEAD: `e6c3de8a906ab7aa75af5a71cb1f6da4c2439011`.
Source P4 artifact: `tuning\hold-lift-p4-3b554f3-3942837-20260720T115546Z`.
Source ref: `876b570` -> `876b5707738fa294b073045c5470b206fed4a50c`.

## Reproduction

| Arm | raw FULL fixes | accepted FULL | side rows | relock events |
|---|---:|---:|---:|---:|
| `detector_only` | 115 | 64 | 0 | 0 |
| `parallel_tracker` | 115 | 56 | 15 | 56 |

Existing P4 lost frame ids: `[308, 309, 310, 311, 312, 313, 314, 315]`.

## Lost Rows

| frame | ts_ns | range | stage | relock at/before | mismatch | prior z | relock det range | contrad before | contrad at/before |
|---:|---:|---:|---|---|---:|---:|---:|---:|---:|
| 308 | 1784531621032630700 | 19.869 | `other_prediction_inconsistent_relock` | `True` | 19.289 | 0.579 | 19.869 | 47 | 48 |
| 309 | 1784531621067313800 | 1.908 | `other_prediction_inconsistent_relock` | `True` | 1.406 | 0.502 | 1.908 | 48 | 49 |
| 310 | 1784531621095166900 | 19.243 | `other_prediction_inconsistent_relock` | `True` | 18.803 | 0.441 | 19.243 | 49 | 50 |
| 311 | 1784531621129823900 | 18.529 | `other_prediction_inconsistent_relock` | `True` | 18.164 | 0.365 | 18.529 | 50 | 51 |
| 312 | 1784531621164422500 | 17.548 | `other_prediction_inconsistent_relock` | `True` | 17.258 | 0.290 | 17.548 | 51 | 52 |
| 313 | 1784531621199178000 | 18.010 | `other_prediction_inconsistent_relock` | `True` | 17.796 | 0.213 | 18.010 | 52 | 53 |
| 314 | 1784531621233908300 | 17.239 | `other_prediction_inconsistent_relock` | `True` | 17.102 | 0.137 | 17.239 | 53 | 54 |
| 315 | 1784531621261671700 | 17.615 | `other_prediction_inconsistent_relock` | `True` | 17.538 | 0.077 | 17.615 | 54 | 55 |

## Verdict

`HONEST RELOCK`: All lost rows are relock-rejected after many prior contradictory exposures, and the rejected detector ranges jump far outside the live primary lock. This prices the certificate boundary rather than showing a primary-channel liveness regression.

F4 cluster quarantine: `CLEARED`.

Artifacts: `p4d_lost_full_diff.csv`, `p4d_parallel_trace.csv`, `p4d_detector_trace.csv`, `p4d_relock_events.csv`, `p4d_arm_meta.csv`, `summary.json`, and `summary.md`.
