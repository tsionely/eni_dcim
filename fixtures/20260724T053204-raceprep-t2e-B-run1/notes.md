# T2e HUD observed flight

- Exact HEAD flown: `f4431ca9b9620692bb3fd1190e14c0475a10b3c3`
- Simulator: `C:\Users\tsion\Downloads\AI-GP Simulator v1.0.3390\FlightSim.exe`
  (`1.0.3390`)
- Event: R1
- Flight ID: `20260724T052750-01330cb1`
- Screenshots: 10, approximately every 5 seconds
- Post-runner capture: 10 seconds

## Flight result

- Gates: 0
- Duration: 19.776 s
- Abort: `gate clip budget exceeded (11)`
- Gate clips: 11
- Environment hits: 0

This observed flight did **not** end on a stale-channel/stream-stop event, so
it does not directly answer what the HUD shows at the terminal stream cutoff.
Per instruction, no retry was flown.

## What the HUD showed at and after the pilot abort

- `shot_006_t0030.1s.png`: vehicle still moving at 16 km/h near a gate.
- `shot_007_t0035.1s.png`: near the abort window, the same track view remains;
  speed is 0 km/h and the HUD timer reads `00:11.165`.
- The runner exited at approximately `t=38.071s`.
- `shot_008_t0040.1s.png`: about 2 seconds after runner exit, the track view
  remains at 0 km/h and the timer has advanced to `00:16.084`.
- `shot_009_t0045.1s.png`: about 7 seconds after runner exit, the track view
  still remains at 0 km/h and the timer has advanced to `00:21.154`.

No attempt-over banner, results screen, off-course warning, disqualification
message, or crash text appeared in the captured post-abort window. The sim
continued rendering the live course HUD and advancing its timer after the
pilot had stopped.
