# Re-Baseline v3 Guard-Aborted Campaign

Role: QA & MOCK-TUNER.

Commit: `f5e88659a26056a7f692412004e30fac498dc276`.

Scope: mock only. No real simulator was launched, reset, clicked, or commanded.

## Status

This is not a valid clean baseline campaign.

The run started only after the machine was clear of `FlightSim`/`DCGame` and
`C:\Temp\eni_dcim_sim.lock`. During the campaign, a new SIM OPERATOR lock
appeared:

```text
SIM OPERATOR lock phase3h-r2training pid=59684 time=2026-07-16T00:31:14.9729652+03:00 repo=C:\Users\tsion\Projects\eni_dcim_phase1
```

The guard aborted immediately rather than continuing a contaminated
measurement.

## Evidence

- Hover probe after timer fix: `overrun_frac=0.7468099395567495`, `ticks=1489`.
- Campaign attempt 1 aborted by the contamination guard at 11/40 flights:
  `stale_imu_rate=18.2%`.
- Campaign attempt 2 reached 6/40 flights with `stale_imu_rate=0.0%`.
- Before attempt 2 flight 7, the guard detected the new SIM LOCK above and
  raised `RuntimeError: sim guard blocked run`.

## Verdict

- Valid 40-flight campaign: `False`.
- Sakana patch starting point: none.
- Next action: rerun the v3 campaign from a clean machine after the SIM LOCK
  and `FlightSim` process are gone.
