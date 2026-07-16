# Phase 3j — R2-TRAINING: blind-commit climb bias / aim taper restored

- **Date (local):** 2026-07-16 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385** (`AI GP 1.0.3385` in HUD)
- **Flight code commit:** `bbe3aee` — `Blind-commit climb bias; aim floor reverted (visibility beats altitude)`
- **SIM LOCK:** created at `C:\Temp\eni_dcim_sim.lock` before sim launch.
- **Track:** R2-TRAINING.
- **Task:** 3 slow flights using speed patches only, **dropping** the old `planner.commit.duration_s` patch; optional no-patch flight.

## Patch set used for slow attempts
```powershell
--patch planner.approach.speed_far_mps=1.2
--patch planner.approach.speed_near_mps=0.8
--patch planner.commit.speed_mps=1.2
```
No `planner.commit.duration_s` patch was used. I also did **not** add any non-task safety/watchdog patches, even though `safety.frame_stale_s` would likely mask the operational failure.

## Summary verdict
- **No valid Phase 3j flight was obtained.**
- No pass/crossing/miss-size data are available for this cycle.
- The simulator GUI could reach R2-TRAINING and even show countdown / race view, but the controller did not receive a sustained live frame stream. Runs either timed out with `race_start=-1` and zero frames, or aborted as `stale channels: frame` after only one/short bursts of frames.
- This is an operational/sensor-stream issue in the local sim cycle, not a tuning verdict on the blind-climb-bias build.

## Attempted runs

### Initial 3 slow + optional default attempts
- `20260716T121026-8edfeec4` — slow: `flight timeout`, 120s, zero frames/detections, `race_start=-1`.
- `20260716T121331-8edfeec4` — slow: `flight timeout`, 120s, zero frames/detections, `race_start=-1`.
- `20260716T121635-8edfeec4` — slow: `flight timeout`, 120s, zero frames/detections, `race_start=-1`.
- `20260716T121939-2ca531c3` — optional default: `flight timeout`, 120s, zero frames/detections, `race_start=-1`.

Root cause for these first attempts: the pre-filled login modal was still blocking the event UI. `screens/login_modal_blocked_initial.jpg` documents this.

### Hardened login / race-visible attempts
- `20260716T122609-8edfeec4` — slow: `stale channels: frame`, 14.23s. The race/countdown was visibly live (`screens/race_countdown_but_frame_stale.jpg`), but the log contains only **1 frame** and **1 detection** before frame staleness.
- `20260716T122932-8edfeec4` — slow, pre-open race dialog: `stale channels: frame`, 0.60s. It had 526 frames in recording/log pre-start but `race_start=-1`; controller died before launch.
- `20260716T123132-8edfeec4` — slow, RACE pre-click before controller: `stale channels: frame`, 0.63s. It had a visible race and `race_start` briefly positive, but still only 72 frames and immediate stale abort.
- `20260716T123403-8edfeec4` — slow, delayed controller start after RACE click: `stale channels: frame`, 0.62s. `race_start=40336` and 589 frames are present in the log/recording, but the watchdog still judged the frame channel stale immediately at controller startup.

## What this means
- The corrected Phase 3i login/row helper is not sufficient by itself for Phase 3j because the frame channel is not continuously healthy after race launch.
- I tried three launch orderings while preserving the task's flight patch constraints:
  1. controller first, then login / R2 row / RACE;
  2. pre-open race dialog, controller first, then RACE;
  3. RACE first, then controller startup during countdown.
- All three failed on the same frame-channel health failure. I did not apply a `safety.frame_stale_s` patch because the task explicitly requested slow **speed patches only**.

## Suggested next action
- Before the next real flight attempt, run a focused `frame_probe.py` / vision liveness check during R2 countdown/race to understand why the GUI shows a live race but `fly_once` sees stale or discontinuous frames.
- If the cloud agent wants an emergency workaround, it can explicitly authorize a runtime stale-frame watchdog relaxation, but that would no longer be a pure Phase 3j speed-only flight.

## Fixture contents
- `report.txt` — full console output for all Phase 3j attempts and launch-order experiments.
- `phase3j_r2training_analysis.txt` — per-attempt topic counts, race_start ranges, frame/detection counts, and recording sizes.
- logs/results/params for all attempted flights listed above.
- `recording.zip` from the newest short stale-frame attempt when collected, plus screenshots documenting login modal, race dialog, and countdown/race-visible stale-frame states.
- No valid crossing recording slice was produced because no run reached a usable approach/commit sequence.
