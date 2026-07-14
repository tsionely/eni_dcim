# CEM low-load hover/velocity-trim bounds

Role: QA & MOCK-TUNER.

Campaign ID: `trim-camp-20260714T140605`
Optimizer: `CEM`
Flights: 40
Best score: -220.471900
Worst score: -240.764000
Gates passed: min 0, max 0, total 0
Aborted flights: 40/40
Finished flights: 0/40
Gate clips: total 0
Environment hits: total 41

Score progression by 10-flight window:
- 01-10: avg -222.592, best -220.503, worst -240.764
- 11-20: avg -220.545, best -220.480, worst -220.611
- 21-30: avg -220.537, best -220.472, worst -220.641
- 31-40: avg -220.548, best -220.472, worst -220.672

Abort reasons:
- `environment collision (impulse=2.5)`: 2
- `environment collision (impulse=2.7)`: 1
- `environment collision (impulse=3.3)`: 1
- `environment collision (impulse=3.4)`: 1
- `environment collision (impulse=3.7)`: 2
- `environment collision (impulse=3.9)`: 2
- `environment collision (impulse=4.2)`: 1
- `environment collision (impulse=5.0)`: 1
- `environment collision (impulse=5.2)`: 1
- `environment collision (impulse=5.3)`: 1
- `environment collision (impulse=5.5)`: 3
- `environment collision (impulse=5.7)`: 2
- `environment collision (impulse=5.8)`: 1
- `environment collision (impulse=5.9)`: 3
- `environment collision (impulse=6.1)`: 2
- `environment collision (impulse=6.2)`: 1
- `environment collision (impulse=6.3)`: 1
- `environment collision (impulse=6.4)`: 2
- `environment collision (impulse=6.6)`: 2
- `environment collision (impulse=6.7)`: 1
- `environment collision (impulse=6.9)`: 1
- `environment collision (impulse=7.0)`: 1
- `environment collision (impulse=7.3)`: 1
- `environment collision (impulse=7.5)`: 1
- `environment collision (impulse=7.7)`: 2
- `environment collision (impulse=7.8)`: 1
- `environment collision (impulse=8.4)`: 1
- `environment collision (impulse=8.7)`: 1

Best tuned parameters:

```json
{
  "control.att_rate.vel_i": 0.16282943078713075,
  "control.att_rate.vz_i": 0.7381184156532321,
  "estimation.vel_leak": 0.09511782342063133,
  "estimation.vision_vel_blend": 0.32977692042316653
}
```
