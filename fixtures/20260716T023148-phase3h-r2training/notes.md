# Phase 3h — R2-TRAINING: age-aware lock + retreat-and-retry (endgame build)

- **Date (local):** 2026-07-16 ~00:31-05:25 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385** (HUD `AI GP 1.0.3385`)
- **Code commit:** `f5e8865` — "Age-aware gate-lock tolerance: end the last-meter vision blackout" (also carries retreat-and-retry `970e539` + absolute altitude hold `2c3b765`).
- **SIM LOCK:** created at `C:\Temp\eni_dcim_sim.lock` before launch.
- **Track:** R2-TRAINING.
- **Task:** 3 slow flights + optional default flight; watch for **retreat (brief backward flight) + re-attempt** after a blown commit, count attempts, any pass = milestone.

## Slow patch set (flights 1-3)
```powershell
--patch planner.approach.speed_far_mps=1.2
--patch planner.approach.speed_near_mps=0.8
--patch planner.commit.speed_mps=1.2
--patch planner.commit.duration_s=2.5
```
Flight 4 = default speeds, no patches.

## HEADLINE
- **No gate pass yet** (gates_passed = 0 on all flights), BUT the **retreat-and-retry behavior is CONFIRMED live**: in 3 of 4 valid flights the FSM ran `approach -> commit -> retreat -> approach` (a genuine second attempt after backing off), instead of the old clip-and-flail.
- **F1 is the closest the pilot has ever come:** its direct detector was **dead-centered horizontally (u≈0.00) at 0.90 m**, and it **clipped the gate 11 times** (aborted on the gate-clip budget, `env_hits=0`) — i.e. it was in the gate plane but a touch **too LOW** (v≈+0.45), catching the lower bar instead of flying clean through.

## Valid flights
| Flight | ID | Result | Attempts (approach runs) | Retreats | Closest |
|---|---|---|---|---|---|
| F1 slow | 20260715T213138-8edfeec4 | gate clip budget exceeded (11), 20.2s | 1 | 1 | direct 0.90 m, **center-x / LOW** (11 clips) |
| F2 slow | 20260715T213225-8edfeec4 | env collision impulse 2.5, 27.9s | **2** | 1 | state 0.72 m, LEFT / center-y |
| F3c slow (fresh sim) | 20260716T022502-8edfeec4 | env collision impulse 7.6, 27.6s | **2** | 1 | direct 1.11 m, RIGHT / HIGH |
| F4 default | 20260715T213406-fc86a160 | env collision impulse 25.5, 33.6s | **2** | 1 | state 0.21 m, center-x / LOW |

Phase sequences (collapsed):
- F1: `hover -> takeoff -> approach -> commit -> retreat -> recover -> hover`
- F2: `hover -> takeoff -> approach -> commit -> retreat -> approach -> hover`  (retry)
- F3c: `hover -> takeoff -> approach -> commit -> retreat -> recover -> approach`  (retry)
- F4: `hover -> takeoff -> approach -> commit -> retreat -> approach`  (retry)

## Interpretation
- **Age-aware lock works:** F1 accepted true fixes right down to 0.90 m dead-center — previously the fixed lock tolerance rejected last-meter fixes as "another gate." The self-inflicted blackout is gone; F1 clipping (not colliding blind) is the visible proof.
- **Retreat-and-retry works:** every valid flight backed off after the first commit and (F2/F3c/F4) started a fresh approach. Visually the retreat shows as a brief 0 km/h nose-up hold before re-approaching.
- **Why still no pass:** the second approach never reached a second *commit* before running out of room / colliding. The residual last-meter error is **low + slightly lateral**: F1 centered-x but LOW (clipped low bar); F4 center-x but LOW; F3c RIGHT/HIGH; F2 LEFT. The steering state is still ~1.0-1.2 s stale at closest range, so the final correction lags.
- **Default speed (F4)** again the hardest hit (impulse 25.5) — the slow set remains safer and gets closer to clean geometry.

## Anomaly (documented, not a pilot failure)
- Two slow attempts — `20260715T213319-8edfeec4` and `20260716T022234-8edfeec4` — **never started a real race**: `abort_reason="stale channels: frame"`, thousands of phantom `env_hits`, and the screenshots show the **main event menu** (see `screens/f3_noRace_menu.jpg`), i.e. no race GO / no vision frames.
- This happened on the long-lived (~5 h) sim instance; a **fresh sim restart immediately fixed it** (that produced the valid F3c). Root cause looks like sim/GUI degradation on a stale instance, consistent with the "close FlightSim every cycle" operational note.
- Suggestion for the cloud agent: `fly_once` could detect "no race GO / no frames within N s" and abort fast instead of accumulating thousands of phantom collisions.

## Suggested next steps (for the cloud agent)
- Small **vertical low-bias** remains at the gate plane (F1 centered but clipped LOW; F4 center/LOW). A minor upward nudge of the gate-relative target height (or mount-pitch re-trim) may convert F1's clip into a pass.
- Make the **re-approach tighter** so the 2nd attempt can reach a 2nd commit rather than dying in `approach`/`recover`.
- Consider shrinking the ~1 s steering-state lag at close range (predict-forward or faster fix acceptance) to fix the last-meter low/lateral drift.

## Fixture contents
- `report.txt` — full console output (preflight, lock, launch, all runs incl. the two no-race anomalies and the fresh-restart F3c).
- `phase3h_r2training_closest.txt` — per-flight phase timeline, attempt/retreat counts, closest direct/state fixes.
- logs/results/params for the 4 valid flights (`<id>-flight.jsonl` / `-result.json` / `-params.json`).
- 4 recording start-slices (`*_r2h_slice_start.aigprec`), 28.88 MB each.
- `screens/` — downscaled screenshots incl. F1 gate-centered, F2/F4 retreat (nose-up 0 km/h), F3c, and the `f3_noRace_menu.jpg` anomaly.
- Full recordings (234-500 MB) exceed the git limit; local / Drive candidates.
