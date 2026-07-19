# Frame-Fix Mock CEM Campaign

Role: QA & MOCK-TUNER.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.
Commit: `78c84617815541c73e1b84ebf81b6f5f6c7a7808`.
Seeds: `20260719, 20260720`.
Flights per seed: `40`.
Total flights: `80`.
Mode: normal 250Hz mock, no `--low-load`.

## Campaign Bounds

Bounds were supplied by this campaign runner under `tuning/`; no project config file was edited.

```json
{
  "control.att_rate.hover_thrust": [
    0.35,
    0.65
  ],
  "control.att_rate.tilt_max_rad": [
    0.2,
    0.6
  ],
  "control.att_rate.vel_i": [
    0.02,
    0.3
  ],
  "control.att_rate.vel_p": [
    0.15,
    0.6
  ],
  "control.att_rate.vz_i": [
    0.1,
    0.8
  ],
  "control.att_rate.vz_p": [
    0.4,
    1.5
  ],
  "planner.align.max_dz_m": [
    0.3,
    0.8
  ],
  "planner.approach.reacquire_max_m": [
    6.0,
    12.0
  ],
  "planner.commit.abort_min_dist_m": [
    0.8,
    1.5
  ]
}
```

## Overall Result

- Flights: `80`
- Gate >=1 pass rate: `9/80` (`11.2%`)
- Total gates: `13`
- Max gates in one flight: `2`
- Finished: `4/80` (`5.0%`)
- Aborted: `76/80`
- Stale-IMU aborts: `0`
- Best score: `189.781`
- Average score: `-199.14264624999993`

## Per-Seed Summary

| Seed | Flights | >=1 gate | Pass rate | Max gates | Finished | Best score |
|---:|---:|---:|---:|---:|---:|---:|
| 20260719 | 40 | 2 | 5.0% | 2 | 1 | 189.484 |
| 20260720 | 40 | 7 | 17.5% | 2 | 3 | 189.781 |

## Best Parameters

Best score: `189.781`.

```json
{
  "control.att_rate.hover_thrust": 0.4872553517555112,
  "control.att_rate.tilt_max_rad": 0.4919919446274588,
  "control.att_rate.vel_i": 0.1971306369154902,
  "control.att_rate.vel_p": 0.31122594064937564,
  "control.att_rate.vz_i": 0.41338897812125247,
  "control.att_rate.vz_p": 1.2184746417650334,
  "planner.align.max_dz_m": 0.46834367747348,
  "planner.approach.reacquire_max_m": 9.885819024819634,
  "planner.commit.abort_min_dist_m": 1.1618975201387252
}
```

Sakana patch starting point:

```powershell
--patch planner.align.max_dz_m=0.46834367747348 --patch planner.commit.abort_min_dist_m=1.1618975201387252 --patch planner.approach.reacquire_max_m=9.885819024819634 --patch control.att_rate.vel_p=0.31122594064937564 --patch control.att_rate.vel_i=0.1971306369154902 --patch control.att_rate.vz_p=1.2184746417650334 --patch control.att_rate.vz_i=0.41338897812125247 --patch control.att_rate.tilt_max_rad=0.4919919446274588 --patch control.att_rate.hover_thrust=0.4872553517555112
```

## Artifacts

- `all-flights.csv`: every flight, score, gate count, abort reason, and params.
- `seed-*/score_progression.csv`: per-seed score progression.
- `campaign-config.json`: seed list, flight count, and bounds used.
