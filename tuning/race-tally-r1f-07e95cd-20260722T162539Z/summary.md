# RACE TALLY R1f - true-world dz

- Generated UTC: `2026-07-22T16:25:39.830623+00:00`
- Repo HEAD: `07e95cd17b1d264ed3a7da75ad92a3ee6c5ae2d6`
- Scope: replay/CSV only; no FlightSim/DCGame launched.
- Vertical metric: `aigp.planning.approach.true_world_dz`, detection paired with latest preceding state `q_att/level_roll/level_pitch`.
- Retired metrics not regenerated: camera-frame `ty` and align/commit bias columns.

## Per-config summary
| config | runs | pass_rate | median_true_world_dz_m | min_true_world_dz_m | max_true_world_dz_m | spread_true_world_dz_m | collision_aborts | clip_budget_aborts | timeout_aborts | owner_term_tick_total | term_command_applied_total | admission_score_min_over_runs | admission_score_median_over_runs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 5 | 0.0000 | 0.1015 | -0.3582 | 0.5376 | 0.8958 | 3 | 2 | 0 | 18 | 18 | 0.2623 | 0.6514 |
| B | 5 | 0.0000 | 0.4369 | -0.3095 | 1.8376 | 2.1472 | 4 | 0 | 1 | 0 | 0 |  |  |

## Per-run closest approach
| config | run | gates | abort | closest_range_m | true_world_dz_m | owner_term_ticks | term_cmd_applied | adm_min | adm_med |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 1 | 0 | collision | 0.8324 | 0.5376 | 0 | 0 | 0.6289 | 0.6514 |
| A | 3 | 0 | collision | 1.1365 | -0.3582 | 0 | 0 | 0.6247 | 0.6357 |
| A | 5 | 0 | clip_budget | 1.0368 | 0.1606 | 0 | 0 | 0.6514 | 0.6514 |
| A | 7 | 0 | collision | 1.5154 | -0.1277 | 0 | 0 | 0.3382 | 1.5926 |
| A | 9 | 0 | clip_budget | 0.9025 | 0.1015 | 18 | 18 | 0.2623 | 0.2623 |
| B | 2 | 0 | collision | 4.3234 | 1.8376 |  |  |  |  |
| B | 4 | 0 | collision | 1.3366 | -0.2921 |  |  |  |  |
| B | 6 | 0 | collision | 0.9486 | -0.3095 |  |  |  |  |
| B | 8 | 0 | timeout | 4.0415 | 1.5204 |  |  |  |  |
| B | 10 | 0 | collision | 2.0173 | 0.4369 |  |  |  |  |

## A vs B scatter read
| comparison | a_spread_true_world_dz_m | b_spread_true_world_dz_m | a_median_true_world_dz_m | b_median_true_world_dz_m | verdict |
| --- | --- | --- | --- | --- | --- |
| R1f A vs B true-world dz spread | 0.8958 | 2.1472 | 0.1015 | 0.4369 | A_TIGHTER |

## R1g harm column
| status | config | r1g_runs | r1g_clip_budget_aborts | r1f_A_clip_budget_aborts | harm_delta_clip_budget_aborts_vs_r1f_A | harm_verdict |
| --- | --- | --- | --- | --- | --- | --- |
| MISSING_AT_HEAD | R1g | 0 |  | 2 |  | UNJUDGED_NO_R1G_FIXTURES |

## Files
- `r1f_runs.csv`
- `r1f_detection_true_world_dz.csv`
- `r1f_config_summary.csv`
- `r1f_A_terminal_status_rollup.csv`
- `scatter_comparison.csv`
- `r1g_harm_vs_r1f_A.csv`
- `generation_info.json`
