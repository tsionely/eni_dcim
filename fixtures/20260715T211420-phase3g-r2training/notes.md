# Phase 3g — R2-TRAINING slow set with ABSOLUTE altitude hold

- **Date (local):** 2026-07-15 ~23:33-00:01 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385** (HUD reads `AI GP 1.0.3385`)
- **Code commit:** `2c3b765` — "Absolute altitude hold from the gate reference (approach + commit)"
- **SIM LOCK:** created at `C:\Temp\eni_dcim_sim.lock` before launching a fresh sim.
- **Track:** R2-TRAINING (indoor data-center arena: white grid ceiling, "Station" pillars, cyan racing line, red AI-GP gates, green marker lights).
- **Task:** same slow patch set as Phase 3e, 3 flights; optional flight 4 at default speeds if altitude hold looked good.
- **Result headline:** still **no gate pass** (max gates_passed = 0 on all 4). Every flight ended in an environment collision.

## Slow patch set used (flights 1-3)
```powershell
--patch planner.approach.speed_far_mps=1.2
--patch planner.approach.speed_near_mps=0.8
--patch planner.commit.speed_mps=1.2
--patch planner.commit.duration_s=2.5
```
Flight 4 used **no patches** (default speeds).

Every flight logged the same live calibration: `bias=[0,0,0] level roll=+0.000 pitch=-0.311` (the -0.311 rad resting pitch is applied as expected).

## Flight 1 — slow
ID: `20260715T203300-8edfeec4`
- `aborted=True`, `abort_reason="environment collision (impulse=10.1)"`
- duration 36.8s, `gates_passed=0`, `gate_clips=0`, `env_hits=19`
- detections 3173, states 1143; phases: hover, takeoff, approach, commit, recover, search
- recording 628.7 MB (full local only); 28.88 MB start-slice committed.
- Crossing side:
  - direct closest detection: `u≈-0.71 / v≈+0.01` (dist ~1.78m) → **LEFT**, center-y; a near-simultaneous fix at `u≈-0.33 / v≈-0.16` → LEFT/HIGH.
  - closest state: `u≈+5 (off-frame), v≈-1.2`, dist ~0.45m, age ~1.2s → **stale dead-reckoned RIGHT/HIGH** (u is way outside the image; not a trustworthy steer).
- Visual: forward view with a red gate centered-low and the cyan line leading in, i.e. a plausible approach framing that still ended in repeated wall/structure contact (19 env hits).

## Flight 2 — slow
ID: `20260715T204925-8edfeec4`
- `aborted=True`, `abort_reason="environment collision (impulse=5.1)"`
- duration 34.4s, `gates_passed=0`, `env_hits=1`
- detections 2681, states 1038; phases: hover, takeoff, approach, commit, search
- recording ~494.6 MB (full local only); 28.88 MB start-slice committed.
- Crossing side:
  - direct closest detection: `u≈+0.22 / v≈+0.85`, dist ~4.12m → **RIGHT / LOW-in-image**.
  - closest state: `u≈-0.06 / v≈+0.17`, dist ~1.98m → center-x / **LOW-in-image**.

## Flight 3 — slow
ID: `20260715T205124-8edfeec4`
- `aborted=True`, `abort_reason="environment collision (impulse=1.2)"`
- duration 22.8s, `gates_passed=0`, `env_hits=1`
- detections 1450, states 504; phases: hover, takeoff, approach, commit
- recording ~236.7 MB (full local only); 28.88 MB start-slice committed.
- Crossing side:
  - direct closest detection: `u≈+0.25 / v≈+0.43`, dist ~4.11m → **RIGHT / LOW-in-image**.
  - closest state: `u≈-0.04 / v≈+0.28`, dist ~1.84m → center-x / **LOW-in-image**.
- Visual: late frames show the camera pitched UP toward the ceiling grid and rolled — an attitude excursion (nose-up/roll) that lost the gate before commit.

## Flight 4 — DEFAULT speeds (no patches)
ID: `20260715T205845-fc86a160`
- `aborted=True`, `abort_reason="environment collision (impulse=9.3)"`
- duration 27.2s, `gates_passed=0`, `env_hits=1`
- detections **only 269**, states 629; phases: hover, takeoff, approach, commit
- **loop timing anomaly:** `loop_overrun_frac=0.02767` (188 overruns, `max_late_us=17570`) — the only flight this cycle with loop overruns.
- recording ~146.7 MB (full local only); 28.88 MB start-slice committed.
- Crossing side:
  - direct closest detection: `u≈-0.44 / v≈-0.45`, dist ~1.72m → **LEFT / HIGH-in-image**.
  - closest state: `u≈-0.75 / v≈-0.03`, dist **~0.05m**, age ~1.1s → **LEFT / center-y**, the closest miss of the cycle but well off-center laterally (u≈-0.75).
- Visual: late frames show the drone nose-down looking at the floor with a warning indicator on-screen — the default-speed approach pitched hard and drove into the ground.

## Interpretation
- **Altitude hold did not produce a pass**, but the vertical signature is now **mixed, not uniformly high/top** as in earlier phases:
  - F1: direct LEFT/HIGH; stale state RIGHT/HIGH.
  - F2 & F3: direct RIGHT/LOW; state center-x/LOW.
  - F4 (default): direct LEFT/HIGH; state LEFT/center-y very close.
- The dominant remaining error in the slow flights (F2/F3) is now **lateral + low**, not the old persistent "too high" — the absolute-height reference appears to have removed the constant-high bias, but the last-meter fixes come in **LOW and off to one side**.
- F1's "closest state" (dist 0.45m) is a **stale dead-reckoned projection** with u≈+5 (far outside the image); it should not be read as a real centered approach — the trustworthy signal is the direct detector, which says LEFT.
- **Default speeds did not help**: F4 saw very few detections (269), overran its loop 188 times, and dove nose-first into the floor. The slow set remains the safer regime.

## Suggested next steps (for the cloud agent — not code changes I make)
- The slow-flight misses are now **lateral/low** rather than high; consider whether cross-track nulling gain and the low-side vertical (mount/reference) need a small re-trim toward LOW-side compensation.
- Investigate F1's 19 env hits vs the single hit in F2/F3 — F1 kept flying (recover/search phases) and grinding into structure; a hard-abort-on-first-impact policy would give cleaner per-flight signals.
- The F4 loop overruns (max_late 17.6ms) coincide with a near-empty detection stream (269) — flag whether default-speed load is starving the perception/loop budget on this machine.

## Fixture contents
- `report.txt` — full console output (preflight, lock, launch, all 4 flights).
- `phase3g_r2training_closest.txt` — closest detector/state analysis per flight.
- logs/results/params for all 4 flights (`<id>-flight.jsonl` / `-result.json` / `-params.json`).
- 4 recording start-slices (`*_r2g_slice_start.aigprec`), each 28.88 MB (wire-format intact).
- `screens/` — downscaled screenshots (start + approach) for each flight.
- Full recordings (147-629 MB) exceed the git limit and remain local / Drive candidates.
