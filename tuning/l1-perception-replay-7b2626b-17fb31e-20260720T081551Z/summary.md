# L1 Perception Replay

Role: QA & MOCK-TUNER.
Scope: recorded video replay only; no real simulator was launched, reset, clicked, or commanded.
Commit: `17fb31e94f06c002b18f176250037c60ae016e64`.

## QA Notes

- Observer-only replay: this measures TerminalOracle observe/readiness/source history from fresh video-derived features, without running the terminal controller update or actuator ownership path.
- L1 liveness bar is positive for F2: fresh-tail readiness lights below 2m; `ready_legacy` stays dark, confirming the semantic difference on this video replay.
- The current replay does not produce metric features below 1.0m. The closest F2 metric row is at 1.006m with `e_z=-0.145m`, matching the contact-implied 0.1-0.2m magnitude; the sub-1m rows are row-only shadow and do not feed metrology.
- No baseline source transition to `SIDE_PAIR` occurred; S5 source-removal/dropout sweeps also failed to promote SIDE in these two videos.

## Inputs

- `F2` `20260720T071112-cd18c5fb`: 141 frames, detector fixes 125, tracker fixes 13, feature rows 90, level_pitch -0.310703 rad.
- `F4` `20260720T071333-cd18c5fb`: 120 frames, detector fixes 115, tracker fixes 2, feature rows 58, level_pitch -0.310658 rad.

## Ready Below 2m

| Flight | Range bin | Rows | Ready | Ready legacy | FULL | SIDE | Active SIDE |
|---|---:|---:|---:|---:|---:|---:|---:|
| `F2` | 1.5-2.0 | 5 | 5 | 0 | 5 | 0 | 0 |
| `F2` | 1.0-1.5 | 9 | 9 | 0 | 8 | 1 | 0 |
| `F2` | 0.5-1.0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `F2` | 0.0-0.5 | 0 | 0 | 0 | 0 | 0 | 0 |
| `F4` | 1.5-2.0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `F4` | 1.0-1.5 | 1 | 1 | 0 | 0 | 0 | 0 |
| `F4` | 0.5-1.0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `F4` | 0.0-0.5 | 0 | 0 | 0 | 0 | 0 | 0 |

## Final Meter Accuracy

| Flight | <1.0m rows | e_z median | <=1.1m rows | <=1.1m median | closest R | closest e_z | contact offset | closest abs-contact |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `F2` | 0 | n/a | 2 | -0.055 | 1.006 | -0.145 | 0.162 | -0.017 |
| `F4` | 0 | n/a | 0 | n/a | 2.779 | -0.450 | 0.162 | 0.288 |

## Earned Sigma Row

- Overlap rows: `2`.
- SIDE_PAIR minus FULL_QUAD bias_e: `-0.090` m.
- Measured sigma_e: `0.090` m.
- Measured sigma_v: `n/a` m/s.

## Source Transitions

No source transitions observed in baseline replay.

## S5 Dropout Sweeps

| Sweep | Flight | Fed rows | Ready below 2m | Legacy ready below 2m | Active SIDE below 2m | First ready range | Transitions |
|---|---|---:|---:|---:|---:|---:|---:|
| `baseline` | `F2` | 25 | 14 | 0 | 0 | 1.903 | 0 |
| `baseline` | `F4` | 26 | 1 | 0 | 0 | 1.028 | 0 |
| `drop_all_0p16s_after_first_below_2m` | `F2` | 20 | 4 | 0 | 0 | 1.194 | 0 |
| `drop_all_0p16s_after_first_below_2m` | `F4` | 26 | 1 | 0 | 0 | 1.028 | 0 |
| `drop_all_0p30s_after_first_below_2m` | `F2` | 15 | 0 | 0 | 0 | n/a | 0 |
| `drop_all_0p30s_after_first_below_2m` | `F4` | 26 | 1 | 0 | 0 | 1.028 | 0 |
| `drop_full_below_2p0m` | `F2` | 12 | 0 | 0 | 0 | n/a | 0 |
| `drop_full_below_2p0m` | `F4` | 26 | 1 | 0 | 0 | 1.028 | 0 |
| `drop_full_below_1p5m` | `F2` | 17 | 14 | 0 | 0 | 1.903 | 0 |
| `drop_full_below_1p5m` | `F4` | 26 | 1 | 0 | 0 | 1.028 | 0 |
| `drop_full_source_all` | `F2` | 6 | 0 | 0 | 0 | n/a | 0 |
| `drop_full_source_all` | `F4` | 2 | 0 | 0 | 0 | n/a | 0 |

Artifacts: `features.csv`, `timeline_baseline.csv`, `side_residuals.csv`, `source_transitions.csv`, `s5_dropout_sweeps.csv`, and `summary.json`.
