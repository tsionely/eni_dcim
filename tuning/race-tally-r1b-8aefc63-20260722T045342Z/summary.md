# Race Tally R1b

Scope: replay/CSV only. No FlightSim/DCGame process was launched. Analysis ran at repo HEAD `8aefc63` after `git pull --rebase origin main`.

Source packages:
- R1b: `fixtures/*raceprep-r1b-*` (10 runs, speed 1.8, anchor `e8f46a9`).
- R1-ALT comparison: `fixtures/*raceprep-r1-alt-*` (10 runs, speed 2.5 by params/defaults, anchor `935e973`).

Closest gate approach is the minimum Euclidean norm of `detection.data.rel_pose.t`; `closest_xyz` preserves the logged vector components at that row. `approach_phase_duration_s` is accumulated from setpoint phase intervals labeled `approach`, including the last setpoint interval through the final logged row.

## Verdict

- Config A: 0/5 full completions, 0/5 runs passed at least one gate, 4/5 collision aborts, 1/5 clip-budget abort.
- Config B: 0/5 full completions, 0/5 runs passed at least one gate, 5/5 collision aborts, 0/5 clip-budget aborts.
- Parameter integrity: 10/10 R1b runs match `config/params_default.json` plus `planner.commit.speed_mps=1.8` and the config-specific terminal enable patch.
- Geometry compared with R1-ALT is confounded by both speed and build: R1-ALT flew 2.5 on anchor `935e973`; R1b flew 1.8 on anchor `e8f46a9`. The comparison shows observed packet-to-packet changes, not isolated causality.
- Observed miss geometry: Config A got much closer at R1b median closest range (2.461m -> 1.123m) but lost the one gate pass; Config B was roughly unchanged/slightly farther (1.072m -> 1.212m) and also lost both prior gate passes.
- Approach-phase duration changed sharply: overall median approach phase fell from 1.091s in R1-ALT to 0.170s in R1b; Config A collapsed from 2.280s to 0.100s, while Config B moved from 0.820s to 0.642s median with one long tail run.

## R1b Config Summary

| config | runs | gates_per_run | full_completion_rate | any_gate_rate | collision_aborts | clip_budget_aborts | median_wall_time_s | best_wall_time_s | median_closest_m | min_closest_m | median_approach_phase_duration_s | param_ok_runs | anchor_or_build_anchor |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 5 | 0/0/0/0/0 | 0/5 | 0/5 | 4 | 1 | 9.235 | 7.664 | 1.123 | 0.679 | 0.100 | 5 | e8f46a9 |
| B | 5 | 0/0/0/0/0 | 0/5 | 0/5 | 5 | 0 | 14.344 | 11.604 | 1.212 | 0.650 | 0.642 | 5 | e8f46a9 |

## R1b Per-Run Tables

### Config A

| run | gates | abort_class | phase | failed_gate | wall_s | closest_m | closest_phase | closest_xyz | approach_s | approach_entries | clips | env_hits | param_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | collision | recover | 1 | 10.568 | 2.056 | commit | (-0.135,-0.365,2.019) | 0.100 | 1 | 0 | 6 | OK |
| 3 | 0 | collision | align | 1 | 7.704 | 0.883 | align | (-0.041,-0.738,0.483) | 0.480 | 1 | 0 | 1 | OK |
| 5 | 0 | clip_budget | recover | 1 | 7.664 | 1.123 | retreat | (-0.012,-0.797,0.792) | 0.000 | 0 | 11 | 0 | OK |
| 7 | 0 | collision | commit | 1 | 9.372 | 2.168 | commit | (0.012,-0.073,2.167) | 0.100 | 1 | 0 | 1 | OK |
| 9 | 0 | collision | retreat | 1 | 9.235 | 0.679 | commit | (0.019,-0.234,0.637) | 0.000 | 0 | 0 | 1 | OK |

### Config B

| run | gates | abort_class | phase | failed_gate | wall_s | closest_m | closest_phase | closest_xyz | approach_s | approach_entries | clips | env_hits | param_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 0 | collision | recover | 1 | 14.344 | 1.212 | align | (0.025,-0.928,0.779) | 0.240 | 2 | 0 | 2 | OK |
| 4 | 0 | collision | approach | 1 | 15.996 | 1.487 | align | (-0.647,-1.090,0.777) | 0.642 | 3 | 0 | 17 | OK |
| 6 | 0 | collision | recover | 1 | 12.276 | 0.999 | retreat | (0.293,-0.508,0.809) | 0.900 | 1 | 6 | 19 | OK |
| 8 | 0 | collision | search | 1 | 11.604 | 2.070 | commit | (-0.836,-0.532,1.818) | 0.000 | 0 | 0 | 1 | OK |
| 10 | 0 | collision | approach | 1 | 27.956 | 0.650 | retreat | (0.056,-0.200,0.615) | 4.118 | 4 | 0 | 3 | OK |

## R1b Failure Modes

| packet | config | failed_gate | abort_phase | abort_class | count | runs |
| --- | --- | --- | --- | --- | --- | --- |
| R1b | A | 1 | align | collision | 1 | 3 |
| R1b | A | 1 | commit | collision | 1 | 7 |
| R1b | A | 1 | recover | clip_budget | 1 | 5 |
| R1b | A | 1 | recover | collision | 1 | 1 |
| R1b | A | 1 | retreat | collision | 1 | 9 |
| R1b | B | 1 | approach | collision | 2 | 4,10 |
| R1b | B | 1 | recover | collision | 2 | 2,6 |
| R1b | B | 1 | search | collision | 1 | 8 |

## Closest Approach vs R1-ALT

| config | r1_alt_speed_mps | r1b_speed_mps | r1_alt_anchor | r1b_anchor | r1_alt_gates | r1b_gates | r1_alt_median_closest_m | r1b_median_closest_m | delta_median_closest_r1b_minus_alt_m | r1_alt_median_approach_s | r1b_median_approach_s | delta_median_approach_r1b_minus_alt_s | r1_alt_closest_phase_counts | r1b_closest_phase_counts | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 2.500 | 1.800 | 935e973 | e8f46a9 | 1 | 0 | 2.461 | 1.123 | -1.338 | 2.280 | 0.100 | -2.180 | align:1; approach:1; commit:3 | align:1; commit:3; retreat:1 | closer median approach but fewer gates |
| B | 2.500 | 1.800 | 935e973 | e8f46a9 | 2 | 0 | 1.072 | 1.212 | 0.139 | 0.820 | 0.642 | -0.178 | commit:5 | align:2; commit:1; retreat:2 | similar/farther median approach and fewer gates |
| ALL | 2.500 | 1.800 | 935e973 | e8f46a9 | 3 | 0 | 1.874 | 1.167 | -0.707 | 1.091 | 0.170 | -0.921 | align:1; approach:1; commit:8 | align:3; commit:4; retreat:3 | overall closer median approach but fewer gates; phase distribution shifted away from mostly commit |

## R1b Parameter Integrity

| run | config | speed_actual | terminal_actual | param_integrity |
| --- | --- | --- | --- | --- |
| 1 | A | 1.8 | True | OK |
| 2 | B | 1.8 | False | OK |
| 3 | A | 1.8 | True | OK |
| 4 | B | 1.8 | False | OK |
| 5 | A | 1.8 | True | OK |
| 6 | B | 1.8 | False | OK |
| 7 | A | 1.8 | True | OK |
| 8 | B | 1.8 | False | OK |
| 9 | A | 1.8 | True | OK |
| 10 | B | 1.8 | False | OK |

## Artifacts

- `r1b_runs.csv`: R1b per-run tally.
- `r1b_config_summary.csv`: R1b per-config summary.
- `r1b_failure_modes.csv`: failed-gate attribution grouped by gate, phase, and abort class.
- `r1_alt_comparison_runs.csv`: R1-ALT recomputed with the same parser for apples-to-apples closest/phase metrics.
- `closest_approach_vs_r1_alt.csv`: side-by-side geometry and approach-duration comparison.
- `all_runs_for_comparison.csv`: combined row set.
