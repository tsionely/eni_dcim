# RandomSearch low-load default bounds

Role: QA & MOCK-TUNER.

Campaign ID: `camp-20260714T140018`
Optimizer: `RandomSearch`
Flights: 40
Best score: -220.471900
Worst score: -220.639100
Gates passed: min 0, max 0, total 0
Aborted flights: 40/40
Finished flights: 0/40
Gate clips: total 0
Environment hits: total 40

Score progression by 10-flight window:
- 01-10: avg -220.527, best -220.472, worst -220.591
- 11-20: avg -220.543, best -220.472, worst -220.639
- 21-30: avg -220.528, best -220.488, worst -220.616
- 31-40: avg -220.535, best -220.483, worst -220.633

Abort reasons:
- `environment collision (impulse=1.5)`: 1
- `environment collision (impulse=1.7)`: 1
- `environment collision (impulse=2.3)`: 1
- `environment collision (impulse=3.4)`: 1
- `environment collision (impulse=3.8)`: 1
- `environment collision (impulse=3.9)`: 1
- `environment collision (impulse=4.1)`: 1
- `environment collision (impulse=4.3)`: 1
- `environment collision (impulse=4.5)`: 1
- `environment collision (impulse=5.0)`: 1
- `environment collision (impulse=5.1)`: 1
- `environment collision (impulse=5.2)`: 1
- `environment collision (impulse=5.3)`: 1
- `environment collision (impulse=5.5)`: 1
- `environment collision (impulse=5.6)`: 1
- `environment collision (impulse=5.7)`: 1
- `environment collision (impulse=5.8)`: 1
- `environment collision (impulse=6.0)`: 4
- `environment collision (impulse=6.2)`: 1
- `environment collision (impulse=6.5)`: 2
- `environment collision (impulse=6.6)`: 2
- `environment collision (impulse=6.7)`: 3
- `environment collision (impulse=6.8)`: 2
- `environment collision (impulse=6.9)`: 3
- `environment collision (impulse=7.5)`: 2
- `environment collision (impulse=7.6)`: 1
- `environment collision (impulse=7.8)`: 1
- `environment collision (impulse=7.9)`: 1
- `environment collision (impulse=8.3)`: 1

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
