# Re-Baseline Mock Campaign - 2026-07-15-rebaseline-5ec57ee

Role: QA & MOCK-TUNER.

Commit: `5ec57ee2fc476a496639ea3b882e813c96a68919`.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.

Caveat: the pre-run guard was clear, but `FlightSim` was detected after the run
with PID `53212`, start time `2026-07-15 07:20:43 +03:00`, and no
`C:\Temp\eni_dcim_sim.lock`. That overlaps the tail of verification/flake
timing, so later measurements should be treated as possibly CPU-contended. No
additional reruns were launched after this detection.

## Bounds

```json
{
  "control.att_rate.vz_i": [
    0.2,
    0.7
  ],
  "control.att_rate.vz_p": [
    0.5,
    1.2
  ],
  "estimation.vision_vel_blend": [
    0.1,
    0.3
  ],
  "planner.approach.aim_up_m": [
    0.1,
    0.6
  ],
  "planner.commit.distance_m": [
    1.5,
    3.5
  ],
  "planner.commit.duration_s": [
    1.0,
    2.0
  ]
}
```

## 40-Flight CEM Campaign

- Flights: 40
- Total gates: 2
- Gates min/max: 0/1
- Gate-pass rate: 5.0%
- Finish rate: 0.0%
- Abort rate: 100.0%
- Best score: -121.91720000000205
- Avg score: -215.12398500000054

Best parameters:

```json
{
  "control.att_rate.vz_i": 0.539332995432149,
  "control.att_rate.vz_p": 0.8955208781183716,
  "estimation.vision_vel_blend": 0.23775495051989237,
  "planner.approach.aim_up_m": 0.4370225686600168,
  "planner.commit.distance_m": 2.985069787076817,
  "planner.commit.duration_s": 1.6935985469361712
}
```

Sakana patch starting point:

```powershell
--patch planner.approach.aim_up_m=0.4370225686600168 --patch planner.commit.distance_m=2.985069787076817 --patch planner.commit.duration_s=1.6935985469361712 --patch estimation.vision_vel_blend=0.23775495051989237 --patch control.att_rate.vz_p=0.8955208781183716 --patch control.att_rate.vz_i=0.539332995432149
```

## Verification: Default vs Best

Default params, 20 flights:
- Flights: 20
- Total gates: 0
- Gates min/max: 0/0
- Gate-pass rate: 0.0%
- Finish rate: 0.0%
- Abort rate: 100.0%
- Best score: -220.7890000000014
- Avg score: -225.0409300000002

Best params, 20 flights:
- Flights: 20
- Total gates: 0
- Gates min/max: 0/0
- Gate-pass rate: 0.0%
- Finish rate: 0.0%
- Abort rate: 100.0%
- Best score: -200.34380000000237
- Avg score: -220.8346099999998

## 30x Single-Gate Flake Hunt

- Flights: 30
- Total gates: 28
- Gates min/max: 0/1
- Gate-pass rate: 93.3%
- Finish rate: 93.3%
- Abort rate: 6.7%
- Best score: 92.5
- Avg score: 70.50512999999995

Failures: `2/30`.
Timeout-in-THROTTLE_DOWN signatures: `0`.

Failure signatures are in `flake-hunt-single-gate/single_gate_30.csv`.
