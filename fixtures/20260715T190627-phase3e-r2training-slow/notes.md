# Phase 3e — R2-TRAINING slow approach

- **Date (local):** 2026-07-15 ~21:31-22:06 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `f6efeb0...` (HEAD after pull)
- **SIM LOCK:** created at `C:\Temp\eni_dcim_sim.lock` before sim launch.
- **Task:** 3 slow R2 flights with exact slow patch set, then optional mount-pitch A/B. Because flights 1-3 still mostly showed gate LOW in image (high/top tendency), optional flight 4 used `perception.camera.mount_pitch_deg=34`.

## Slow patch set used for flights 1-3
```powershell
--patch planner.approach.speed_far_mps=1.2
--patch planner.approach.speed_near_mps=0.8
--patch planner.commit.speed_mps=1.2
--patch planner.commit.duration_s=2.5
```

## Flight 1 — slow default
ID: `20260715T183716-8e6cf1f5`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=2.5)"`
- duration 24.5s
- `gates_passed=0`, `env_hits=1`
- detections: 1776
- phases: `hover`, `takeoff`, `approach`
- recording ~305 MB; slice committed.

Crossing side:
- closest direct detections: gate RIGHT + LOW in image (`u≈+0.70`, `v≈+0.35`, dist ~4.36m)
- closest state: gate LEFT/center-x + LOW (`v≈+0.72..0.76`, dist ~2.5m)
- interpretation: still mainly **HIGH / top-bar side**, with lateral inconsistency. No pass.

## Flight 2 — slow default
ID: `20260715T184758-8e6cf1f5`

Result:
- `aborted=True`, `abort_reason="stale channels: frame"`
- duration 45.7s
- `gates_passed=0`, `env_hits=4380`
- detections: 2703
- phases: `hover`, `takeoff`, `approach`, `recover`
- recording ~824 MB; slice committed.

Crossing side:
- closest direct detections: gate RIGHT + LOW (`u≈+0.36`, `v≈+0.69`, dist ~4.77m)
- closest state after recovery: center-x + HIGH, but this appears stale/post-impact while in recover.
- interpretation: early approach still shows **HIGH / top-bar side**. The run degraded into repeated impacts/recoveries, so later state projection is less trustworthy.

## Flight 3 — slow default
ID: `20260715T185046-8e6cf1f5`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=1.3)"`
- duration 33.5s
- `gates_passed=0`, `env_hits=2`
- detections: 2148
- phases: `hover`, `takeoff`, `approach`, `commit`, `recover`
- recording ~392 MB; slice committed.

Crossing side:
- direct detections: gate LEFT + LOW (`u≈-0.17`, `v≈+0.84`, dist ~3.59m)
- closest state: near center, center-y (`u≈-0.04`, `v≈-0.03`, dist ~1.45m)
- interpretation: this is the best slow run. It gets a near-centered dead-reckoned closest state around 1.4–1.7m, but the direct detector before that still sees the gate low in image. It likely improved but still did not thread the opening.

## Optional Flight 4 — slow + mount pitch 34
Patch added:
```powershell
--patch perception.camera.mount_pitch_deg=34
```
ID: `20260715T185843-7f28e2fb`

Result:
- `aborted=True`, `abort_reason="environment collision (impulse=3.0)"`
- duration 22.5s
- `gates_passed=0`, `env_hits=1`
- detections: 1621
- phases: `hover`, `takeoff`, `approach`
- recording ~222 MB; slice committed.

Crossing side:
- closest direct detection: gate RIGHT + HIGH (`u≈+0.42`, `v≈-0.49`, dist ~2.29m)
- earlier direct detections show center/LOW; closest state shows center/LOW (`v≈+0.2`)
- interpretation: mount 34 changes the sign of the vertical miss in direct detection (now high in image at closest direct), so 34 may over-correct the camera mount. It did not pass and had a stronger collision than flight 3.

## Overall Phase 3e findings
- No gate pass in any flight.
- Slow approach reduced some violent behavior, and Flight 3 showed the closest near-centered state, but all runs still miss/collide.
- The pre-optional flights still mostly look HIGH/top-side from direct detections, hence choosing mount 34 was justified by the task rule.
- Mount 34 appears to over-correct vertically at closest direct detection (gate becomes HIGH in image) and does not improve pass outcome.
- The best candidate from this cycle is Flight 3 slow default: near-centered closest state; next tuning likely should refine final commit, not simply push mount pitch further.

## Fixture contents
- `report.txt` — full console and summaries.
- `phase3e_r2training_closest.txt` — closest detection/state analysis for high/low/left/right.
- Logs/results/params for all four flights.
- Four recording slices (`*_r2e_slice_start.aigprec`), all <50 MB.
- Downscaled screenshots for each flight.
- Full recordings are too large for git and remain local / Drive candidates.
