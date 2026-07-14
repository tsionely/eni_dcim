# Low-Load Default-Bounds Mock Campaigns - 2026-07-14

Role: QA & MOCK-TUNER.

Commit: `2cc8df981f2a804ed8893ad3d1ca3ab5d13e87f9`
Checkout: `C:\Users\tsion\Projects\eni_dcim_qa` (outside OneDrive).
All commands used `--sim mock --low-load`; the real simulator was not launched, reset, clicked, or commanded.

## CEM low-load default bounds - `camp-20260714T135502`

- Flights: 40
- Best score: -220.457800
- Worst score: -220.606200
- Gates passed: min 0, max 0, total 0
- Aborted: 40/40
- Finished: 0/40
- Gate clips: 0 total
- Environment hits: 40 total

Score progression by 10-flight window:
- 01-10: avg -220.507, best -220.459, worst -220.606
- 11-20: avg -220.476, best -220.458, worst -220.491
- 21-30: avg -220.495, best -220.472, worst -220.552
- 31-40: avg -220.487, best -220.464, worst -220.527

Best tuned parameters:

```json
{
  "control.att_rate.hover_thrust": 0.3952989514647001,
  "control.att_rate.tilt_max_rad": 0.4261863452763517,
  "control.att_rate.vel_p": 0.5291503261376398,
  "control.att_rate.vz_p": 1.4790403196429935,
  "planner.approach.near_distance_m": 7.40830735061412,
  "planner.approach.speed_far_mps": 2.8000749623027446,
  "planner.approach.speed_near_mps": 2.7191741878950824,
  "planner.commit.distance_m": 1.9529624179831586,
  "planner.commit.duration_s": 1.4125676010176669,
  "planner.commit.speed_mps": 3.0829079789002924
}
```

## RandomSearch low-load default bounds - `camp-20260714T140018`

- Flights: 40
- Best score: -220.471900
- Worst score: -220.639100
- Gates passed: min 0, max 0, total 0
- Aborted: 40/40
- Finished: 0/40
- Gate clips: 0 total
- Environment hits: 40 total

Score progression by 10-flight window:
- 01-10: avg -220.527, best -220.472, worst -220.591
- 11-20: avg -220.543, best -220.472, worst -220.639
- 21-30: avg -220.528, best -220.488, worst -220.616
- 31-40: avg -220.535, best -220.483, worst -220.633

Best tuned parameters:

```json
{
  "control.att_rate.hover_thrust": 0.4573385590127211,
  "control.att_rate.tilt_max_rad": 0.5736174063824999,
  "control.att_rate.vel_p": 0.36862591147430507,
  "control.att_rate.vz_p": 1.3784366177839003,
  "planner.approach.near_distance_m": 2.810579030134467,
  "planner.approach.speed_far_mps": 4.59801028756923,
  "planner.approach.speed_near_mps": 1.6556271327540284,
  "planner.commit.distance_m": 2.8037208504852043,
  "planner.commit.duration_s": 1.3354960514660161,
  "planner.commit.speed_mps": 2.585846564456345
}
```

## Overall Finding

Across 80 flights: total gates `0`, aborted `80/80`.
Best overall run: `camp-20260714T135502` score `-220.457800`.
