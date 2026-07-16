# Re-Baseline v4 Guard-Aborted Campaign

Role: QA & MOCK-TUNER.

Commit: `44f5f741878e3cf51461c4706e40b7aaaee5b523`.

Scope: mock only. No real simulator was launched, reset, clicked, or commanded.

## Status

This is not a valid clean baseline campaign.

The run started only after the machine was clear of `FlightSim`/`DCGame` and
`C:\Temp\eni_dcim_sim.lock`. During campaign attempt 1, a new SIM OPERATOR
lock appeared:

```text
SIM OPERATOR lock phase3i-r2training pid=48124 time=2026-07-16T06:08:24.4301036+03:00 repo=C:\Users\tsion\Projects\eni_dcim_phase1
```

The guard aborted immediately rather than continuing a contaminated
measurement.

## Evidence

- Mode: normal.
- Hover probe after v4 timer/power fix: `overrun_frac=0.7471341874578556`, `ticks=1483`.
- Campaign attempt 1 reached 4/40 flights.
- Stale-IMU at the time of guard abort: 0/4 flights (`0.0%`).
- The abort was caused by SIM LOCK, not by the stale-IMU contamination guard.

## Verdict

- Valid 40-flight campaign: `False`.
- Low-load fallback: not started yet; blocked by active SIM LOCK.
- Sakana patch starting point: none.
- Next action: rerun the v4 campaign from a clean machine after the SIM LOCK
  and `FlightSim` process are gone; if stale-IMU then exceeds 10%, rerun with
  `--low-load`.
