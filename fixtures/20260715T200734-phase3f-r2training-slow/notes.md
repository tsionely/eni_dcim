# Phase 3f — R2-TRAINING slow approach with cross-track nulling

- **Date (local):** 2026-07-15 ~22:43-23:07 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `9bad0d6...` (HEAD after pull; cross-track lateral nulling active)
- **SIM LOCK:** created at `C:\Temp\eni_dcim_sim.lock` before sim launch.
- **Task:** same slow patch set as Phase 3e, 3 flights. Optional center_gain flight only if misses remain lateral by constant margin.

## Slow patch set used
```powershell
--patch planner.approach.speed_far_mps=1.2
--patch planner.approach.speed_near_mps=0.8
--patch planner.commit.speed_mps=1.2
--patch planner.commit.duration_s=2.5
```

## Flight 1 — slow, cross-track code
ID: `20260715T195033-8edfeec4`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=4.2)"`
- duration 26.9s
- `gates_passed=0`, `env_hits=15`
- detections: 1818
- phases: `hover`, `takeoff`, `approach`, `commit`, `recover`
- recording ~312 MB; slice committed.

Closest / crossing side:
- direct closest detection: `u≈-0.015`, `v≈-0.410`, dist ~1.69m → centered-x but **HIGH in image**.
- closest state: `u≈-0.16`, `v≈+0.36`, dist ~1.53m → LEFT + LOW (dead-reckoned, stale-ish).

Interpretation:
- Not a constant lateral miss. Direct detector says vertical miss in the opposite direction from previous high/top trend — likely **low/bottom-side** or late vertical oscillation.
- Because state and direct detection disagree, this is more last-meter instability than a simple lateral offset.

## Flight 2 — slow, cross-track code
ID: `20260715T200011-8edfeec4`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=1.9)"`
- duration 26.7s
- `gates_passed=0`, `env_hits=4`
- detections: 2056
- phases: `hover`, `takeoff`, `approach`, `recover`
- recording ~294 MB; slice committed.

Closest / crossing side:
- direct closest detection: `u≈-0.04`, `v≈+0.92`, dist ~4.75m → centered-x, **LOW in image**.
- closest state: centered-x, `v≈-0.20..-0.50`, dist ~3.1m → **HIGH in image**.

Interpretation:
- Again not a constant lateral miss. Vertical evidence flips between detector and state, likely due recovery/impact and stale projection.
- Direct detection still shows **too high/top-side tendency** early.

## Flight 3 — slow, cross-track code
ID: `20260715T200142-8edfeec4`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=2.4)"`
- duration 26.1s
- `gates_passed=0`, `env_hits=1`
- detections: 1867
- phases: `hover`, `takeoff`, `approach`
- recording ~283 MB; slice committed.

Closest / crossing side:
- direct closest detection: `u≈-0.47`, `v≈-0.41`, dist ~2.57m → **LEFT + HIGH in image**.
- closest state: mostly centered-x, `v≈+0.18..0.25`, dist ~2.0m → center/LOW.

Interpretation:
- Mixed/unstable, but the direct detector indicates a lateral component (gate left → drone right of opening) plus low/bottom-side tendency at closest direct detection.
- Still no pass.

## Optional center_gain flight decision
I did **not** run the optional `--patch planner.approach.center_gain=1.0` because the misses in flights 1-3 did **not** stay lateral by a constant margin:
- Flight 1: direct centered-x/HIGH; state LEFT/LOW.
- Flight 2: direct centered-x/LOW; state centered-x/HIGH.
- Flight 3: direct LEFT/HIGH; state centered-x/LOW.

This is not a consistent lateral offset that stronger center_gain would obviously fix. The issue still looks like last-meter vertical/projection instability plus occasional lateral miss, not constant cross-track bias.

## Overall Phase 3f conclusion
- No gate pass yet.
- Cross-track nulling did not yield a clean pass in these 3 slow flights.
- Compared with Phase 3e, the failure signature is no longer simply persistent high/top; it alternates between high/low and sometimes left. This suggests the new lateral term may be active, but final commit remains unstable or stale in the last meters.
- Best next diagnostic may need a closer time-window around commit with direct detector vs dead-reckoned state, rather than another constant gain patch.

## Fixture contents
- `report.txt` — full console output.
- `phase3f_r2training_closest.txt` — closest detector/state analysis.
- logs/results/params for all 3 flights.
- 3 recording slices (`*_r2f_slice_start.aigprec`), each ~28.88 MB.
- `screens/` — downscaled screenshots from the attempts.
- Full recordings are too large for git and remain local / Drive candidates.
