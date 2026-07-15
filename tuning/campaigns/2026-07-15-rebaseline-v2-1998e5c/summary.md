# Re-Baseline v2 Mock Campaign - 2026-07-15-rebaseline-v2-1998e5c

Role: QA & MOCK-TUNER.

Commit: `1998e5cc047a25bf1cdf64976ffb9d13b4daf4e2`.
Pre-run requirement: clean machine, no `FlightSim`/`DCGame`, no sim lock.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.

## Guard

- Campaign attempt used: `3`.
- Campaign valid under stale-IMU <=10% rule: `False`.
- Default 0% finish P0 finding: `False`.

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

- Flights: 10
- Total gates: 1
- Max gates: 1
- Gate-pass rate: 10.0%
- Finish rate: 0.0%
- Abort rate: 100.0%
- Stale-IMU: 2 (20.0%)
- Best score: -121.76410000000615
- Avg score: -209.63842000000062

Best parameters from rejected contaminated attempt:

```json
{
  "control.att_rate.vz_i": 0.6378822816307717,
  "control.att_rate.vz_p": 0.7314218914467759,
  "estimation.vision_vel_blend": 0.1943822816447598,
  "planner.approach.aim_up_m": 0.33826145699758137,
  "planner.commit.distance_m": 3.5,
  "planner.commit.duration_s": 1.5740820869310885
}
```

Sakana patch starting point:

```powershell
# NO VALID SAKANA PATCH: all campaign attempts exceeded the stale-IMU contamination guard.
```

## Verification: Default vs Best

Default params, 20 flights:
- Flights: 20
- Total gates: 4
- Max gates: 2
- Gate-pass rate: 15.0%
- Finish rate: 5.0%
- Abort rate: 95.0%
- Stale-IMU: 6 (30.0%)
- Best score: 189.609
- Avg score: -189.76893000000024

Best params, 20 flights:
- Flights: 20
- Total gates: 0
- Max gates: 0
- Gate-pass rate: 0.0%
- Finish rate: 0.0%
- Abort rate: 100.0%
- Stale-IMU: 2 (10.0%)
- Best score: -200.3140999999945
- Avg score: -224.2534999999986

## CPU Samples

CPU samples are recorded in `cpu.csv` and per-verification CPU CSVs.
