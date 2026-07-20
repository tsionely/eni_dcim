# R26-3 physical command-regime inventory (2e37585fee1e)

Scope: real recorded `flight.jsonl` files under `fixtures/`; shadow-only TERM rows are listed but excluded from closure because R26-3 requires physically realized commands.

## Method

- Physical TERM row: `term_status.owner == term`, `engaged=true`, `ready=true`, and numeric `vz_up` + `v_bz_applied`.
- Episode split: gap > 0.35s.
- R26-3 up/down coverage uses the physical command sign: `vz_up` >= +/- 0.03 m/s.
- Diagnostic slope steps are also recorded: `delta(vz_up)` >= +/- 0.03 m/s inside an episode.
- Saturation: `abs(vz_up or v_bz_applied)` >= 0.95 * terminal `vz_max_mps` (0.600).
- Authority-limited: `rate_anchor_quality` present and < 0.999; absent authority fields are not counted as evidence.

## Result

- Flight logs scanned: 156
- Recordings with physical TERM rows: 1
- Physical TERM rows: 28 across 1 episodes
- Shadow-only TERM recordings excluded: 45
- Covered regimes: down_steps, saturation
- R26-3 gaps: up_steps, up_down_triangular, down_up_triangular, authority_limited

## Regime Totals

| Regime | Count |
| --- | ---: |
| up_steps | 0 |
| down_steps | 28 |
| diagnostic_up_slope_steps | 11 |
| diagnostic_down_slope_steps | 2 |
| up_command_rows | 0 |
| down_command_rows | 28 |
| up_down_triangular | 0 |
| down_up_triangular | 0 |
| diagnostic_up_down_slope_triangular | 0 |
| diagnostic_down_up_slope_triangular | 1 |
| saturation | 3 |
| authority_limited | 0 |

## Gap List

| Regime | Covered | Physical evidence count | Route if gap |
| --- | --- | ---: | --- |
| up_steps | False | 0 | closed-loop simulator fixture required |
| down_steps | True | 28 |  |
| up_down_triangular | False | 0 | closed-loop simulator fixture required |
| down_up_triangular | False | 0 | closed-loop simulator fixture required |
| saturation | True | 3 |  |
| authority_limited | False | 0 | closed-loop simulator fixture required |

## Artifacts

- `recording_manifest.csv`
- `physical_term_rows.csv`
- `episode_regime_inventory.csv`
- `flight_regime_inventory.csv`
- `r26_3_gap_list.csv`
- `shadow_only_excluded.csv`
- `summary.json`
