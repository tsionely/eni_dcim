# Hover Loop Profile - 2afcfc4

Mock-only 60s stationary-hover runs: detection disabled and search yaw set to zero. Per-tick budget uses runtime wrapping around `RateLoop.wait_next_tick`: wait is time inside the scheduler call; work is time from scheduler return to the next scheduler entry.

| Case | Target Hz | Achieved Hz | Ticks | Overrun frac | Max late us | Wait mean / p95 ms | Work mean / p95 ms | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `default-250hz` | 250 | 249.84 | 14994 | 0.7451 | 27000 | 2.722 / 13.207 | 1.281 / 3.874 | max duration, env_hits=0, clips=0 |
| `nosleep-250hz` | 250 | 249.76 | 14989 | 0.7447 | 24000 | 2.732 / 13.068 | 1.272 / 3.781 | max duration, env_hits=0, clips=0 |
| `default-125hz` | 125 | 124.99 | 7501 | 0.4883 | 17000 | 6.406 / 15.067 | 1.596 / 4.034 | max duration, env_hits=0, clips=0 |

## Candidate Note

`control_hz=125` is not yet a clean recommended-config candidate from this probe.
