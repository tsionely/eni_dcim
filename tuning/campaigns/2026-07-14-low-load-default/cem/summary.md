# CEM low-load default bounds

Role: QA & MOCK-TUNER.

Campaign ID: `camp-20260714T135502`
Optimizer: `CEM`
Flights: 40
Best score: -220.457800
Worst score: -220.606200
Gates passed: min 0, max 0, total 0
Aborted flights: 40/40
Finished flights: 0/40
Gate clips: total 0
Environment hits: total 40

Score progression by 10-flight window:
- 01-10: avg -220.507, best -220.459, worst -220.606
- 11-20: avg -220.476, best -220.458, worst -220.491
- 21-30: avg -220.495, best -220.472, worst -220.552
- 31-40: avg -220.487, best -220.464, worst -220.527

Abort reasons:
- `environment collision (impulse=1.6)`: 1
- `environment collision (impulse=3.2)`: 1
- `environment collision (impulse=3.3)`: 1
- `environment collision (impulse=3.9)`: 1
- `environment collision (impulse=4.2)`: 1
- `environment collision (impulse=4.3)`: 2
- `environment collision (impulse=4.6)`: 2
- `environment collision (impulse=4.7)`: 1
- `environment collision (impulse=4.8)`: 1
- `environment collision (impulse=5.0)`: 2
- `environment collision (impulse=5.2)`: 1
- `environment collision (impulse=5.3)`: 1
- `environment collision (impulse=5.4)`: 1
- `environment collision (impulse=5.5)`: 3
- `environment collision (impulse=5.9)`: 2
- `environment collision (impulse=6.0)`: 2
- `environment collision (impulse=6.1)`: 2
- `environment collision (impulse=6.2)`: 2
- `environment collision (impulse=6.3)`: 1
- `environment collision (impulse=6.5)`: 1
- `environment collision (impulse=6.6)`: 1
- `environment collision (impulse=6.8)`: 2
- `environment collision (impulse=7.0)`: 2
- `environment collision (impulse=7.2)`: 1
- `environment collision (impulse=7.3)`: 1
- `environment collision (impulse=7.5)`: 1
- `environment collision (impulse=7.8)`: 2
- `environment collision (impulse=8.2)`: 1

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
