# Phase 6f REPEAT — verified-R2 statistics cycle

- **Date (local):** 2026-07-19 17:52:43 +0300
- **Operator role:** SIM OPERATOR (Sakana)
- **Sim version:** AI-GP Simulator v1.0.3385
- **Branch HEAD flown:** `adddf6a96a4ee82d7302fbdae8998f9ef1f852be` (`adddf6a [sim-run] phase6e aim center + terminal feature r2`). `564e98d` verified as ancestor (`OK`).
- **Command:** `python scripts/fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300` (no strategy patches).
- **Counting rule:** verified R2-TRAINING + TAKEOFF->end slice with >300 unique frames. Stopped at exactly three counted flights.

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
At line:152 char:52
+ ... "`n===== git checkout main =====`n" + (git checkout main 2>&1 | Out-S ...
+                                            ~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (Already on 'main':String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
Your branch is up to date with 'origin/main'.

===== git pull =====
Already up to date.

===== git log -1 --oneline =====
adddf6a [sim-run] phase6e aim center + terminal feature r2

===== git merge-base --is-ancestor 564e98d HEAD && echo OK =====
OK
```

## Counted flights

| Count | Attempt | Log ID | Gates | Clips | Env hits | Result | Dur s | Closest direct fix + center px | gate_rel age @ closest direct | Phase sequence |
|---:|---:|---|---:|---:|---:|---|---:|---|---|---|
| 1 | 1 | `20260719T144540-a76247fb` | 0 | 0 | 0 | stale channels: frame | 32.62 | 3.12m @ t+7.43s, center [299.0, 312.5] | 0.005s (state range 3.49m) | hover -> takeoff -> approach -> align -> commit -> retreat -> commit -> retreat -> search -> hover |
| 2 | 4 | `20260719T144941-a76247fb` | 0 | 0 | 303 | environment collision (impulse=5.6) | 24.11 | 0.66m @ t+19.07s, center [295.6, 596.9] | 0.025s (state range 0.70m) | hover -> takeoff -> align -> commit -> retreat -> search -> approach -> commit -> retreat -> recover -> search -> commit -> retreat -> recover |
| 3 | 5 | `20260719T145122-a76247fb` | 0 | 0 | 142 | environment collision (impulse=4.1) | 18.90 | 0.80m @ t+6.35s, center [320.2, 106.5] | 0.000s (state range 14.19m) | hover -> takeoff -> align -> commit -> retreat -> search -> recover -> search -> recover -> search -> approach -> recover |

## Rejected attempts

- Attempt 2: `20260719T144715-a76247fb` — r2ok=True unique=274 (need >300)
- Attempt 3: `20260719T144828-a76247fb` — r2ok=True unique=269 (need >300)

## Repeat-statistics note

Every graze-class crossing adds shadow evidence toward terminal-feature enable gates. Raw shadow/feature/collision data is in each `flight.jsonl` and `summary.json`.

## Cycle answer

Counted gate passes: 0/3. No counted pass in these three repeat flights.

## Slice verification

| Count | Slice file | Unique frames | ~sec @30fps | Span s | Size MB |
|---:|---|---:|---:|---:|---:|
| 1 | `20260719T144540-a76247fb_takeoff_to_end.aigprec` | 867 | 28.9 | 28.9 | 27.5 |
| 2 | `20260719T144941-a76247fb_takeoff_to_end.aigprec` | 628 | 20.9 | 20.9 | 23.3 |
| 3 | `20260719T145122-a76247fb_takeoff_to_end.aigprec` | 470 | 15.7 | 15.6 | 19.2 |