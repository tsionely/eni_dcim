# Crossing autopsy: one terminal STALL vs four gate-1 PASSES

## Scope and method

This compares `20260723T203357-raceprep-t2r1-B-run2` (STALL, zero gates)
with four fixtures that incremented `active_gate_index` to one.  The
analysis uses 100 ms bins over `[closest - 3.0 s, closest + 0.5 s]`.

`closest` is the smallest positive `t[2]` before the first gate-pass counter
increment.  It therefore remains anchored to gate 1 when a successful flight
has already started acquiring gate 2.  It uses a certified detection where
one is available; otherwise it uses the locked state, because the ring
normally leaves the camera before the plane. `true_world_dz` is reconstructed
from the locked `gate_rel`, `q_att`, and recorded rest-level roll/pitch.
Positive dz means the gate is below the drone in the physical level frame.

The supplied risk brief describes the stall as roughly 0.77 m centered. The
state log continues through the terminal clip and reaches `t[2]=0.486 m`
(`||t||=0.548 m`) at the impact sample; the last certified direct PnP fix was
0.50 s earlier at `t[2]=1.152 m`. This report deliberately shows both: the
first is the controller's terminal state and the second establishes when
direct visual evidence ended.

## Per-flight final-window summary

| Case | min `t[2]` / norm (m) | true dz (m) | lateral (m) | phase at min | vx / vz at min (m/s) | detection bins, last 0.5 s | pass counter relative to min |
|---|---:|---:|---:|---|---:|---:|---:|
| STALL t2r1 B2 | 0.486 / 0.548 | +0.469 | +0.086 | commit | +1.553 / -1.022 | 1/6 (17%) | none |
| PASS r1k-off R3 | 0.247 / 0.553 | +0.120 | +0.168 | retreat | -1.200 / -0.200 | 5/6 (83%) | +0.007 s |
| PASS alt-B R2 | 0.059 / 0.252 | +0.053 | +0.007 | commit | +1.915 / +0.000 | 3/6 (50%) | +0.082 s |
| PASS alt-A R5 | 0.003 / 0.329 | +0.015 | +0.001 | commit | +1.521 / -0.350 | 6/6 (100%) | +0.181 s |
| PASS alt-B R10 | 0.040 / 0.488 | +0.105 | -0.159 | commit | +1.197 / -0.180 | 5/6 (83%) | +0.173 s |

## The discriminating signature

1. **Terminal height, not lateral centering, separates this stall.** At its
   closest state the STALL was **+0.469 m** in true-world dz; the four PASSes
   were **+0.015 to +0.120 m** (mean **+0.073 m**, maximum +0.120 m).
   In contrast, STALL lateral error was **+0.086 m**, within the PASS range
   (−0.159 to +0.168 m; mean +0.004 m).
2. The STALL's direct vision evaporated before the decision: certified
   detections occupy **17% (1/6)** of the final 0.5 s and **55%** of the
   final 1.0 s. PASSes retained **50–100%** in the final 0.5 s (mean
   **79%**) and **64–100%** in the final second.
3. The STALL remained in **commit** for **2.46 s** from entry at −2.44 s
   through the closest sample. It did **not** retreat or recover before the
   minimum. `recover` began **+0.020 s** after it, coincident with a
   `collision_id=1001`, impulse **1.77** event. This is an impact-driven
   recovery, not a protective early abort.
4. Commit expiry does not explain this instance: the STALL's only
   commit exit is the collision recovery at +0.020 s. The four PASS counters
   arrive **+0.007, +0.082, +0.181, and +0.173 s** after their closest
   samples, so the recorded pass acknowledgement is also post-closest.
5. The STALL was still advancing at the terminal state
   (**vx=+1.553 m/s**, 1 s mean **+1.445 m/s**) and had a strong upward NED
   command (**vz=−1.022 m/s**). The successful committed crossings carried
   **+1.20 to +1.92 m/s** at the minimum (the r1k fixture is an acknowledged
   pass after an early retreat/recommit, so it is not a clean velocity
   template). Forward speed alone is therefore not discriminating.
6. The terminal no-return condition was reached in both outcomes:
   `state_range < 0.8 m` while in commit is true for the STALL and for
   three of four PASSes. The abort corridor must consequently key on a
   geometry/evidence signature, not on range alone.
7. Recommended instrumentation: emit at every terminal tick
   `true_world_dz`, direct-fix age, detection-certification state, and an
   explicit `commit_exit_reason`. The candidate reject condition to test is
   **freshness loss plus |true_world_dz| > 0.12 m** before the braking band;
   it targets the measured STALL signature without rejecting the four
   successful terminal states.

## Artifacts

- `comparison.csv` — requested per-flight metrics.
- `summary.json` — transitions and race-counter pass timing.
- `per_flight_timeline_*.csv` — 100 ms final-3-second timelines.
- `run_crossing_autopsy.py` — reproducible parser and metric extraction.
