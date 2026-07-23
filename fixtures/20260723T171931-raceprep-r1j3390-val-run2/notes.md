# R1j 3390 validation run 2

- Simulator: `C:\Users\tsion\Downloads\AI-GP Simulator v1.0.3390\FlightSim.exe`
- Simulator version: `1.0.3390`
- Exact HEAD flown: `07695a78a8c55f1a5bfbeed746e3721d68945918`
- Event selection: R2-TRAINING; template scores were R1 `0.977`,
  R2-SUBMISSION `1.000`, and R2-TRAINING `1.000`.
- Config B patches: commit speed `1.8`, commit vertical cap `1.2`,
  terminal disabled.
- Runner printed `[STEP 3] RACE clicked`.

## Launch-success criteria

All three criteria were met:

- `race_start_boot_time_ms` changed from `-1` to `5575560`.
- Live IMU continued (2269 IMU records).
- FSM fired `THROTTLE_DOWN -> TAKEOFF` and then
  `TAKEOFF -> RACING`.

## Result

- Gates passed: 0
- Duration: 20.248 s
- Abort: `environment collision (impulse=1.8)`
- Environment hits: 3
- Gate clips: 0
- Loop overruns: 50 / 5062
- Search ticks: 125
- Search ticks with `blind_hold=true`: 125

FSM sequence:

1. `IDLE -> ARMING`
2. `ARMING -> THROTTLE_DOWN`
3. `THROTTLE_DOWN -> TAKEOFF` (`race GO`)
4. `TAKEOFF -> RACING`
5. `RACING -> ABORTED` (`environment collision (impulse=1.8)`)
6. `ABORTED -> DONE`

The first environment collision occurred immediately after a
`phase=search, blind_hold=true` setpoint. This run is
mechanism-exercising but **not harm-clean** under the registered R1j
definition.

## Validation decision

**HARD STOP.** A collision occurred during a blind-hold search stretch.
Do not fly validation run 3 or start the 10-run block without a new
authorization.
