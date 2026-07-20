# Phantom-crossing reclassification — phase6h 47-flight rescue set

Context: commit `8596c24` — geometric termination now requires `gate_rel_age_s <= entry_max_age_s` (~0.6s). This report sizes how many of the 44 env-collision deaths began with the stale phantom-crossing abort the fix refuses.

## Verdict

- Env-collision deaths: **44** / 47
- Phantom first-commit abort (tz < -0.4 ∧ age > 0.6s): **10**
- Fraction of env deaths: **22.7%**
- Missing logs: 0

## Per-flight table (phantom cases)

| fid | abort R | age@term | tz | commit dur | closest R | end→ | death |
|---|---:|---:|---:|---:|---:|---|---|
| `20260719T155227-f170ead6` | 0.43 | 0.91 | -0.40 | 2.68 | 0.04 | retreat | env_collision |
| `20260719T155652-f170ead6` | 0.42 | 0.91 | -0.42 | 2.27 | 0.05 | retreat | env_collision |
| `20260719T160039-f170ead6` | 0.40 | 1.16 | -0.40 | 2.24 | 0.03 | retreat | env_collision |
| `20260719T161136-f170ead6` | 0.43 | 1.40 | -0.43 | 2.78 | 0.05 | retreat | env_collision |
| `20260719T161414-f170ead6` | 0.44 | 1.16 | -0.44 | 1.58 | 0.03 | retreat | env_collision |
| `20260719T161749-f170ead6` | 0.43 | 0.99 | -0.42 | 2.36 | 0.02 | retreat | env_collision |
| `20260719T162358-f170ead6` | 0.46 | 0.80 | -0.45 | 2.70 | 0.01 | retreat | env_collision |
| `20260719T163525-f170ead6` | 0.47 | 0.62 | -0.46 | 1.52 | 0.03 | retreat | env_collision |
| `20260719T164321-f170ead6` | 0.42 | 1.20 | -0.42 | 2.02 | 0.02 | retreat | env_collision |
| `20260719T164548-f170ead6` | 0.42 | 0.80 | -0.41 | 2.40 | 0.05 | retreat | env_collision |

## All env deaths (compact)

| fid | phantom? | abort R | age | closest R | death_mode |
|---|---|---:|---:|---:|---|
| `20260719T154704-f170ead6` | False | 0.68 |  | 0.68 | env_collision |
| `20260719T154832-f170ead6` | False | 0.49 |  | 0.49 | env_collision |
| `20260719T154952-f170ead6` | False | 0.53 |  | 0.53 | env_collision |
| `20260719T155107-f170ead6` | False | 1.13 |  | 1.13 | env_collision |
| `20260719T155227-f170ead6` | True | 0.43 | 0.91 | 0.04 | env_collision |
| `20260719T155339-f170ead6` | False | 1.20 |  | 1.20 | env_collision |
| `20260719T155446-f170ead6` | False | 1.29 |  | 1.29 | env_collision |
| `20260719T155652-f170ead6` | True | 0.42 | 0.91 | 0.05 | env_collision |
| `20260719T155813-f170ead6` | False | 0.58 |  | 0.58 | env_collision |
| `20260719T155926-f170ead6` | False | 1.56 |  | 1.56 | env_collision |
| `20260719T160039-f170ead6` | True | 0.40 | 1.16 | 0.03 | env_collision |
| `20260719T160258-f170ead6` | False | 1.37 |  | 1.37 | env_collision |
| `20260719T160421-f170ead6` | False | 0.06 |  | 0.06 | env_collision |
| `20260719T160537-f170ead6` | False | 0.03 |  | 0.03 | pass_then_env_collision |
| `20260719T160650-f170ead6` | False | 0.04 |  | 0.04 | env_collision |
| `20260719T160815-f170ead6` | False | 1.83 |  | 1.83 | env_collision |
| `20260719T160921-f170ead6` | False | 1.76 |  | 1.76 | env_collision |
| `20260719T161028-f170ead6` | False | 2.88 |  | 2.88 | env_collision |
| `20260719T161136-f170ead6` | True | 0.43 | 1.40 | 0.05 | env_collision |
| `20260719T161259-f170ead6` | False | 1.45 |  | 1.45 | env_collision |
| `20260719T161414-f170ead6` | True | 0.44 | 1.16 | 0.03 | env_collision |
| `20260719T161523-f170ead6` | False | 0.58 |  | 0.58 | env_collision |
| `20260719T161634-f170ead6` | False | 1.80 |  | 1.80 | env_collision |
| `20260719T161749-f170ead6` | True | 0.43 | 0.99 | 0.02 | env_collision |
| `20260719T161859-f170ead6` | False | 2.11 |  | 2.11 | env_collision |
| `20260719T162020-f170ead6` | False | 0.75 |  | 0.75 | env_collision |
| `20260719T162245-f170ead6` | False | 0.15 |  | 0.15 | env_collision |
| `20260719T162358-f170ead6` | True | 0.46 | 0.80 | 0.01 | env_collision |
| `20260719T162511-f170ead6` | False | 2.05 |  | 2.05 | env_collision |
| `20260719T162631-f170ead6` | False | 0.46 |  | 0.46 | env_collision |
| `20260719T162747-f170ead6` | False | 2.19 |  | 2.19 | env_collision |
| `20260719T162853-f170ead6` | False | 1.24 |  | 1.24 | env_collision |
| `20260719T163035-f170ead6` | False | 0.08 |  | 0.08 | env_collision |
| `20260719T163151-f170ead6` | False | 1.15 |  | 1.15 | env_collision |
| `20260719T163304-f170ead6` | False | 0.05 |  | 0.05 | env_collision |
| `20260719T163525-f170ead6` | True | 0.47 | 0.62 | 0.03 | env_collision |
| `20260719T163649-f170ead6` | False | 0.28 |  | 0.28 | pass_then_env_collision |
| `20260719T163807-f170ead6` | False | 0.06 |  | 0.06 | env_collision |
| `20260719T163920-f170ead6` | False | 0.45 |  | 0.45 | env_collision |
| `20260719T164032-f170ead6` | False | 1.18 |  | 1.18 | env_collision |
| `20260719T164153-f170ead6` | False | 1.32 |  | 1.32 | env_collision |
| `20260719T164321-f170ead6` | True | 0.42 | 1.20 | 0.02 | env_collision |
| `20260719T164433-f170ead6` | False | 0.12 |  | 0.12 | env_collision |
| `20260719T164548-f170ead6` | True | 0.42 | 0.80 | 0.05 | env_collision |

## Implication

The shipped freshness gate on geometric termination (age ≤ 0.6s) would have blocked **10** first-commit phantom aborts in this rescue set. Those flights then entered the post-abort churn that ends in env collision — the fix sizes to that count.

## Deliverables

- `phantom-crossing.md`, `summary.json`, `per_flight.csv`
