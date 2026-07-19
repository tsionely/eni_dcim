# Terminal CEM Mock Campaign

Role: QA & MOCK-TUNER.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.
Commit: `23813aaa9d6aa32cb5e4464ce995a6eb782d526b`.
Seed: `20260719`.
Flights: `40`.

## Base Patch

```json
{
  "planner.commit.speed_mps": 1.8,
  "planner.terminal.enable": true,
  "safety.imu_stale_s": 0.25
}
```

## Bounds

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
  "planner.terminal.engage_range_m": [
    2.0,
    3.5
  ],
  "planner.terminal.margin_m": [
    0.4,
    0.7
  ]
}
```

## Result

- Flights: `40`
- Gate >=1 pass rate: `14/40` (`35.0%`)
- Total gates: `16`
- Max gates: `2`
- Finished: `2/40` (`5.0%`)
- Aborted: `38/40`
- Best score: `189.7969999999999`
- Average score: `-182.68406250000007`
- Flights with terminal applied while not ready: `0`
- Terminal authority note: `term_status` was present, but `owner=term` and
  `v_bz_applied` stayed at zero across the campaign. The best patch should be
  treated as a mock flight-tuning starting point, not proof that the terminal
  vertical channel actively owned the last meter.

## Best Parameters

Best score: `189.7969999999999`.

```json
{
  "control.att_rate.hover_thrust": 0.513245487740746,
  "control.att_rate.tilt_max_rad": 0.5489551774887438,
  "control.att_rate.vel_i": 0.1355089905524141,
  "control.att_rate.vel_p": 0.5860590512868975,
  "control.att_rate.vz_i": 0.8,
  "control.att_rate.vz_p": 0.7029585629358039,
  "planner.align.max_dz_m": 0.4855650970120281,
  "planner.terminal.engage_range_m": 2.45141347066278,
  "planner.terminal.margin_m": 0.467747228306376
}
```

Sakana patch starting point:

```powershell
--patch safety.imu_stale_s=0.25 --patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=true --patch planner.terminal.margin_m=0.467747228306376 --patch planner.terminal.engage_range_m=2.45141347066278 --patch planner.align.max_dz_m=0.4855650970120281 --patch control.att_rate.vel_p=0.5860590512868975 --patch control.att_rate.vel_i=0.1355089905524141 --patch control.att_rate.vz_p=0.7029585629358039 --patch control.att_rate.vz_i=0.8 --patch control.att_rate.tilt_max_rad=0.5489551774887438 --patch control.att_rate.hover_thrust=0.513245487740746
```

Artifacts: `all-flights.csv`, `score_progression.csv`, `results.sqlite`, and per-flight logs under `tuning/runtime-logs/`.
