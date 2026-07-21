# Race Tally R1b Request - No Valid R1b Logs Present

Scope: replay/CSV only. No FlightSim/DCGame process was launched. The local branch was rebased over `4ef7712` before this report commit. The raw tally was generated from the 10-run packet that ended at `bcd4aa3`.

Source package: no fixture directory currently matches `*raceprep-r1b*`. The 10 available post-R1 alternating runs are `fixtures/*raceprep-r1-alt-*`. Per `docs/racing/COMPETITION_PLAN.md` at `4ef7712`, these are R1-ALT, not the registered R1b block. They are counted below only as the available 10-run packet, and all 10 are flagged because they did not include the required R1b speed patch.

Expected parameter profile: `config/params_default.json` plus `planner.commit.speed_mps=1.8` and the config-specific `planner.terminal.enable` value. Closest gate approach is the minimum Euclidean norm of `detection.data.rel_pose.t`; the phase is the latest logged setpoint phase at that detection row.

## Source Fixtures

- `20260721T193344-raceprep-r1-alt-A-run1`
- `20260721T193502-raceprep-r1-alt-B-run2`
- `20260721T193624-raceprep-r1-alt-A-run3`
- `20260721T193741-raceprep-r1-alt-B-run4`
- `20260721T193902-raceprep-r1-alt-A-run5`
- `20260721T194024-raceprep-r1-alt-B-run6`
- `20260721T194140-raceprep-r1-alt-A-run7`
- `20260721T194254-raceprep-r1-alt-B-run8`
- `20260721T194415-raceprep-r1-alt-A-run9`
- `20260721T194532-raceprep-r1-alt-B-run10`

## Verdict

- Config A: 0/5 full completions, 1/5 runs passed at least one gate, 5/5 collision aborts, 0/5 clip-budget-only aborts.
- Config B: 0/5 full completions, 2/5 runs passed at least one gate, 5/5 collision aborts, 0/5 clip-budget-only aborts.
- Parameter integrity: 10/10 runs deviate from the R1b protocol: actual `planner.commit.speed_mps=2.5`, expected `1.8`; terminal enable matches A=True and B=False. Therefore this packet is not a valid R1b result.

## Config Summary

| config | runs | gates/run | complete | >=1 gate | collision aborts | clip-budget aborts | median wall s | best wall s | min closest m | param deviations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 5 | 0/0/1/0/0 | 0/5 | 1/5 | 5 | 0 | 14.828 | 7.996 | 0.962 | 5 |
| B | 5 | 1/0/0/0/1 | 0/5 | 2/5 | 5 | 0 | 13.840 | 10.116 | 0.646 | 5 |

## Per-Run Tables

### Config A

| run | gates | abort_class | phase | failed_gate | wall_s | closest_m | closest_phase | clips | env_hits | param_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | collision | search | 1 | 7.996 | 4.332 | align | 0 | 2 | DEVIATES |
| 3 | 0 | collision | recover | 1 | 14.828 | 3.587 | commit | 0 | 12 | DEVIATES |
| 5 | 1 | collision | search | 2 | 15.748 | 0.962 | commit | 0 | 32 | DEVIATES |
| 7 | 0 | collision | recover | 1 | 12.128 | 2.461 | commit | 0 | 2 | DEVIATES |
| 9 | 0 | collision | approach | 1 | 17.092 | 2.403 | approach | 0 | 1 | DEVIATES |

### Config B

| run | gates | abort_class | phase | failed_gate | wall_s | closest_m | closest_phase | clips | env_hits | param_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 1 | collision | hover | 2 | 13.900 | 0.646 | commit | 0 | 1 | DEVIATES |
| 4 | 0 | collision | hover | 1 | 13.840 | 1.737 | commit | 0 | 15 | DEVIATES |
| 6 | 0 | collision | recover | 1 | 18.372 | 1.072 | commit | 0 | 53 | DEVIATES |
| 8 | 0 | collision | search | 1 | 10.116 | 2.010 | commit | 0 | 2 | DEVIATES |
| 10 | 1 | collision | recover | 2 | 13.456 | 0.825 | commit | 3 | 81 | DEVIATES |

## Failure Modes

| config | failed_gate | phase | abort_class | count | runs |
| --- | --- | --- | --- | --- | --- |
| A | 1 | approach | collision | 1 | 9 |
| A | 1 | recover | collision | 2 | 3,7 |
| A | 1 | search | collision | 1 | 1 |
| A | 2 | search | collision | 1 | 5 |
| B | 1 | hover | collision | 1 | 4 |
| B | 1 | recover | collision | 1 | 6 |
| B | 1 | search | collision | 1 | 8 |
| B | 2 | hover | collision | 1 | 2 |
| B | 2 | recover | collision | 1 | 10 |

## Parameter Deviations

| run | config | speed_actual | terminal_actual | deviation |
| --- | --- | --- | --- | --- |
| 1 | A | 2.5 | True | planner.commit.speed_mps=2.5 expected 1.8; command_missing_commit_speed_patch |
| 2 | B | 2.5 | False | planner.commit.speed_mps=2.5 expected 1.8; command_missing_commit_speed_patch |
| 3 | A | 2.5 | True | planner.commit.speed_mps=2.5 expected 1.8; command_missing_commit_speed_patch |
| 4 | B | 2.5 | False | planner.commit.speed_mps=2.5 expected 1.8; command_missing_commit_speed_patch |
| 5 | A | 2.5 | True | planner.commit.speed_mps=2.5 expected 1.8; command_missing_commit_speed_patch |
| 6 | B | 2.5 | False | planner.commit.speed_mps=2.5 expected 1.8; command_missing_commit_speed_patch |
| 7 | A | 2.5 | True | planner.commit.speed_mps=2.5 expected 1.8; command_missing_commit_speed_patch |
| 8 | B | 2.5 | False | planner.commit.speed_mps=2.5 expected 1.8; command_missing_commit_speed_patch |
| 9 | A | 2.5 | True | planner.commit.speed_mps=2.5 expected 1.8; command_missing_commit_speed_patch |
| 10 | B | 2.5 | False | planner.commit.speed_mps=2.5 expected 1.8; command_missing_commit_speed_patch |

## Artifacts

- `runs.csv`: per-run row-level tally.
- `config_summary.csv`: per-config summary counts and timing.
- `failure_modes.csv`: grouped failure modes by config, failed gate, phase, and abort class.
