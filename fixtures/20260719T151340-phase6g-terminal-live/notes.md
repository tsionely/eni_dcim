# Phase 6g TERMINAL LIVE — two arms + control

- **Date (local):** 2026-07-19 18:13:41 +0300
- **Operator role:** SIM OPERATOR (Sakana)
- **Sim version:** AI-GP Simulator v1.0.3385
- **Branch HEAD flown:** `d2bb9ec860b1501950cd31a9126d6a40b3f8370f` (`d2bb9ec The enable build: pixel-row oracle owns terminal e_z, graze-calibrated d*=0.8`). `d2bb9ec` verified as ancestor (`OK`).
- **F1/F2 terminal-live command:** `python scripts/fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300 --patch planner.terminal.enable=true --patch planner.commit.speed_mps=1.8`.
- **F3 control command:** `python scripts/fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300`.
- **Counting rule:** verified R2-TRAINING + TAKEOFF->end slice with >300 unique frames. Stopped at exactly three counted flights (two terminal-live arms + one control).

## Step 0 git verification output

```text
﻿===== git status =====
On branch main
Your branch is up to date with 'origin/main'.

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	scripts/launch_sim.ps1
	tests/unit/test_attitude_rate_backend.py

nothing added to commit but untracked files present (use "git add" to track)

===== git checkout main =====
git : Already on 'main'
At line:174 char:52
+ ... "`n===== git checkout main =====`n" + (git checkout main 2>&1 | Out-S ...
+                                            ~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (Already on 'main':String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
Your branch is up to date with 'origin/main'.

===== git pull =====
git : From https://github.com/tsionely/eni_dcim
At line:175 char:43
+   $step0 += "`n===== git pull =====`n" + (git pull 2>&1 | Out-String)
+                                           ~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (From https://gi...ionely/eni_dcim:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
   6ed8e93..d2bb9ec  main       -> origin/main
Updating 6ed8e93..d2bb9ec
Fast-forward
 config/params_default.json          |  3 ++-
 src/aigp/app.py                     | 19 ++++++++++++++-
 src/aigp/perception/pipeline.py     | 21 ++++++++++++++++-
 src/aigp/planning/vertical_owner.py | 22 ++++++++++++++---
 tests/unit/test_vertical_owner.py   | 47 +++++++++++++++++++++++++++++++++++++
 5 files changed, 106 insertions(+), 6 deletions(-)

===== git log -1 --oneline =====
d2bb9ec The enable build: pixel-row oracle owns terminal e_z, graze-calibrated d*=0.8

===== git merge-base --is-ancestor d2bb9ec HEAD && echo OK =====
OK
```

## Counted flights

| Slot | Arm | Attempt | Log ID | Gates | Clips | Env hits | Result | Dur s | Closest direct fix + center px | gate_rel age @ closest | Phase sequence | Terminal ownership from shadow/owner |
|---:|---|---:|---|---:|---:|---:|---|---:|---|---|---|---|
| 1 | terminal_live | 2 | `20260719T150627-486b0765` | 0 | 0 | 44 | environment collision (impulse=3.0) | 14.68 | 1.04m @ t+3.99s, center [425.4, 537.5] | 0.014s (state range 1.02m) | hover -> takeoff -> align -> commit -> retreat -> recover -> commit -> retreat -> hover | shadow_count=281, term_event_count=281, owner_values={'alt': 2, 'term': 279} |
| 2 | terminal_live | 5 | `20260719T151000-486b0765` | 0 | 0 | 3 | environment collision (impulse=25.6) | 17.09 | 1.75m @ t+11.38s, center [244.0, 111.8] | 0.088s (state range 4.57m) | hover -> takeoff -> align -> commit -> retreat -> search -> recover -> search -> commit | shadow_count=279, term_event_count=279, owner_values={'alt': 6, 'term': 273} |
| 3 | control | 7 | `20260719T151227-49448448` | 0 | 0 | 1 | environment collision (impulse=2.9) | 14.52 | 3.78m @ t+11.25s, center [293.0, 75.0] | 0.143s (state range 3.87m) | hover -> takeoff -> align -> commit -> retreat -> approach -> commit -> retreat | control arm (terminal patches off) |

## Rejected attempts

- Attempt 1 slot 1 arm terminal_live: `20260719T150516-486b0765` — r2ok=True unique=147 (need >300)
- Attempt 3 slot 2 arm terminal_live: `` — see report.txt (rejected before counted F2)
- Attempt 4 slot 2 arm terminal_live: `` — see report.txt (rejected before counted F2)
- Attempt 6 slot 3 arm control: `20260719T151118-49448448` — r2ok=True unique=179 (need >300)

## Cycle answer

Counted gate passes: 0/3. No counted pass in these three flights.

## Slice verification

| Slot | Slice file | Unique frames | ~sec @30fps | Span s | Size MB |
|---:|---|---:|---:|---:|---:|
| 1 | `20260719T150627-486b0765_takeoff_to_end.aigprec` | 343 | 11.4 | 11.4 | 16.5 |
| 2 | `20260719T151000-486b0765_takeoff_to_end.aigprec` | 417 | 13.9 | 13.9 | 19.2 |
| 3 | `20260719T151227-49448448_takeoff_to_end.aigprec` | 339 | 11.3 | 11.3 | 17.4 |