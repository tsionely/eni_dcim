# Phase 5c Loop Profile / Windows CI - `2afcfc4`

Generated: 2026-07-17.

Role: QA & MOCK-TUNER. Real simulator was not launched or controlled. SIM lock was clear before mock/CI runs.

## Hover Loop Profile

Report: `tuning/hover-loop-profile-2afcfc4/hover-loop-profile.md`.

Setup: mock-only 60s stationary hover, detection disabled with `perception.detector.red_sat_min=256`, search yaw set to `0.0`, and `safety.imu_stale_s=0.25`. Timing was captured by wrapping `RateLoop.wait_next_tick`; `wait` is time inside scheduler pacing, `work` is everything from scheduler return to the next scheduler entry.

| Case | Target Hz | Achieved Hz | Ticks | Overrun frac | Wait mean / p95 ms | Work mean / p95 ms | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| default env | 250 | 249.84 | 14994 | 0.7451 | 2.722 / 13.207 | 1.281 / 3.874 | max duration, no hits/clips |
| `AIGP_NOSLEEP=1` | 250 | 249.76 | 14989 | 0.7447 | 2.732 / 13.068 | 1.272 / 3.781 | max duration, no hits/clips |
| `control_hz=125` | 125 | 124.99 | 7501 | 0.4883 | 6.406 / 15.067 | 1.596 / 4.034 | max duration, no hits/clips |

Interpretation:

- Achieved loop rate is on target in all three cases, but overrun remains high because many ticks begin late after Windows scheduler waits.
- Work time is not the dominant budget consumer: 250Hz work mean is about `1.27-1.28ms`, while scheduler wait p95 remains about `13ms`.
- `AIGP_NOSLEEP=1` does not materially change overrun (`0.7451` -> `0.7447`).
- `control_hz=125` improves overrun but only to `0.4883`, not near zero. It is stable in this stationary-hover probe but is not a recommended-config candidate from these data.

## Windows CI

Command: `python -m pytest tests -q --basetemp=C:\Temp\pytest-eni`, using the bundled Codex Python runtime.

Full output: `tuning/pytest-windows-2afcfc4-basetemp-full.txt`.

Result: `2 failed, 123 passed, 1 xfailed, 2 warnings in 42.59s`.

Full-suite failures:

| Test | Failure |
|---|---|
| `test_single_gate_pass` | heartbeat timeout on `udpin:127.0.0.1:24550` |
| `test_campaign_loop_against_mock` | heartbeat timeout on `udpin:127.0.0.1:24550` |

Solo reruns:

| Test | Solo verdict |
|---|---|
| `test_campaign_loop_against_mock` | passed in `55.34s` |
| `test_single_gate_pass` run 1 | failed with pymavlink UDP client-set race: `RuntimeError: Set changed size during iteration` |
| `test_single_gate_pass` run 2 | failed as closed-loop miss after built-in retry: `environment collision (impulse=4.3)`, `gates_passed=0`, `overrun_frac=0.7439` |

Verdict: the full-suite failures are the known heartbeat environmental class. The single-gate solo remains unreliable on this Windows host and failed twice with two different signatures.
