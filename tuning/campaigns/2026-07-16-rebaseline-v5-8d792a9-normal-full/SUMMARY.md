# Re-Baseline v5 Mock Campaign - 2026-07-16-rebaseline-v5-8d792a9-normal-full

Role: QA & MOCK-TUNER.

Scope: mock only. No real simulator was launched, reset, clicked, killed, or commanded by this run.

Pre-run guard: clear. `FlightSim`/`DCGame` were not running and `C:\Temp\eni_dcim_sim.lock` was absent.

Mode: normal. `AIGP_NOSLEEP=1`.

## Windows Timer Fix Quantification

- Before v5: v4 standalone hover probe `overrun_frac=0.7471341874578556`.
- After v5: standalone hover probe `overrun_frac=0.7435043304463691` over 1501 ticks.
- Interpretation: the never-sleep/sub-tick change is slightly lower on this machine, but the Windows overrun telemetry remains high.

## Campaign Guard

- Campaign attempt: 40/40 flights completed.
- stale-IMU: 0/40 (`0.0%`).
- Guard result: valid. No `--low-load` fallback was needed.
- CPU samples: 12.4%, 13.2%, 16.3%, 12.2%, 9.7%, 6.7%.

## Campaign Result

- Finishes: 2/40.
- Total gates: 10.
- Max gates in one flight: 2.
- Best score: `188.67200000000003`.
- Best flight: `20260716T141808-fa6abf10`.
- Best flight details: 2 gates, finished true, lap time `11.327999999999975`, no abort, no gate clips, no env hits.

## Best Parameters

```json
{
  "control.att_rate.vz_i": 0.4282407486549845,
  "control.att_rate.vz_p": 0.5997127390752905,
  "estimation.vision_vel_blend": 0.1752711783794073,
  "planner.approach.aim_up_m": 0.5155244016963784,
  "planner.commit.distance_m": 1.5729619093978944,
  "planner.commit.duration_s": 1.1792217758917576
}
```

## Guard Interruption After Campaign

The helper script completed the requested 40-flight campaign, then began its extra default verification pass. After 10/20 verification flights, the guard stopped the script because the SIM OPERATOR lock appeared:

`SIM OPERATOR lock phase4b-r2training-chain pid=61100 time=2026-07-16T17:35:35.5839937+03:00 repo=C:\Users\tsion\Projects\eni_dcim_phase1`

No further CI or campaign work was run under that lock.
