# R1j 3390 validation run 1

- Simulator: `C:\Users\tsion\Downloads\AI-GP Simulator v1.0.3390\FlightSim.exe`
- Simulator version: `1.0.3390`
- Exact HEAD flown: `c49028809c0899cf0256a48a7c8e8d00e65c2dcf`
- Event selection: R2-TRAINING; all three event-row template scores were `1.000`.
- Config B patches: commit speed `1.8`, commit vertical cap `1.2`, terminal disabled.

## Result

- Gates passed: 0
- Duration: 24.452 s
- Abort: `stale channels: imu`
- Gate clips: 0
- Environment hits: 0
- Loop overruns: 0 / 6113
- IMU records before the stale abort: 2754

FSM sequence:

1. `IDLE -> ARMING` (`flight start`)
2. `ARMING -> THROTTLE_DOWN` (`armed`)
3. `THROTTLE_DOWN -> ABORTED` (`stale channels: imu`)
4. `ABORTED -> DONE` (`flight over`)

The sim race-start value remained `-1`; the FSM never reached TAKEOFF or
RACING. There were no search ticks, blind-hold ticks, or collision records.

Under the registered R1j definition this is harm-clean (known stale-channel
abort class, no blind-hold collision, and no ground contact in search) but
non-mechanism-exercising.
