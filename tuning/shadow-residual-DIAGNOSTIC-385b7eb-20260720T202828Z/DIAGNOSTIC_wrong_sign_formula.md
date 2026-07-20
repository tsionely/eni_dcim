# DIAGNOSTIC Wrong-Sign Formula Disclosure

Scope: CSV-only restamp disclosure. This file does not change the channel verdict.

## Legacy Formula That Produced `wrong_sign_command_rows=28`

Rows considered: `DIAGNOSTIC_r26_1_anchor_trial_rows.csv` rows where `shadow_owner == 'term'`.

Columns:
- `cmd = terminal_vz_up_mps`
- `raw_e = e_meas`

Predicate:

```python
cmd is not None and raw_e is not None and abs(raw_e) > 0.03 and cmd * raw_e < -1e-6
```

Recomputed count: `28`.

## Re-score Requested By RESPONSE47

Needed-correction score uses `applied_e_z` as the correction actually fed to the terminal owner, with `abs(cmd)>0.02`, `abs(applied_e_z)>0.02`, and `cmd*applied_e_z < 0` as opposition.

See `DIAGNOSTIC_wrong_sign_scorecard.csv` for old actual, old forecast, and new shadow forecast rows.
