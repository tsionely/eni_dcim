# Phase 6c TRUE VERTICAL — clean verified-R2 cycle

- **Date (local):** 2026-07-19 15:17:05 +03:00
- **Operator role:** SIM OPERATOR (Sakana)
- **Sim version:** AI-GP Simulator v1.0.3385
- **Branch HEAD flown:** `7113b1a093c2a468576004ecfc6d413261257413` (`7113b1a Advisory-6 lands: braking-band formula, fresh-vision-only aborts, honest gravity behind a gate`). Named code commit `2c5057a` verified as ancestor (OK).
- **Command:** `python scripts/fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300` (no strategy patches).
- **Counting rule:** verified R2-TRAINING + TAKEOFF->end slice with >300 unique frames. Stopped immediately at exactly three counted flights.

## Step 0 git verification output

```text
===== git status =====
On branch main
Your branch is up to date with 'origin/main'.

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	scripts/launch_sim.ps1
	tests/unit/test_attitude_rate_backend.py

nothing added to commit but untracked files present (use "git add" to track)

===== git checkout main =====
git : Already on 'main'
At line:148 char:52
+ ... "`n===== git checkout main =====`n" + (git checkout main 2>&1 | Out-S ...
+                                            ~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (Already on 'main':String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
Your branch is up to date with 'origin/main'.

===== git pull =====
git : From https://github.com/tsionely/eni_dcim
At line:149 char:43
+   $step0 += "`n===== git pull =====`n" + (git pull 2>&1 | Out-String)
+                                           ~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (From https://gi...ionely/eni_dcim:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
   78c8461..7113b1a  main       -> origin/main
Updating 78c8461..7113b1a
Fast-forward
 analysis/2026-07-19-true-vertical-audit.md         | 389 +++++++++
 .../a6_banner_reference.json                       |  18 +
 .../f2_abort_reconstruction.json                   |  68 ++
 .../2026-07-19-true-vertical-audit/gate_geom.json  | 243 ++++++
 .../miss_summary.json                              |  21 +
 .../miss_table_true_vertical.csv                   |  89 ++
 .../plots/miss_scatter_old_vs_true.png             | Bin 0 -> 119243 bytes
 .../run_true_vertical_audit.py                     | 968 +++++++++++++++++++++
 .../2026-07-19-true-vertical-audit/summary.json    |  92 ++
 .../true-vertical-audit.md                         | 389 +++++++++
 config/params_default.json                         |   4 +-
 docs/thinktank/RESPONSE9.md                        |  81 ++
 src/aigp/estimation/attitude_filter.py             |  16 +
 src/aigp/estimation/state_estimator.py             |  34 +-
 src/aigp/planning/approach.py                      |  12 +-
 src/aigp/planning/race_planner.py                  |  24 +-
 tests/unit/test_planner.py                         |  26 +
 tests/unit/test_state_estimator.py                 |  31 +
 18 files changed, 2487 insertions(+), 18 deletions(-)
 create mode 100644 analysis/2026-07-19-true-vertical-audit.md
 create mode 100644 analysis/2026-07-19-true-vertical-audit/a6_banner_reference.json
 create mode 100644 analysis/2026-07-19-true-vertical-audit/f2_abort_reconstruction.json
 create mode 100644 analysis/2026-07-19-true-vertical-audit/gate_geom.json
 create mode 100644 analysis/2026-07-19-true-vertical-audit/miss_summary.json
 create mode 100644 analysis/2026-07-19-true-vertical-audit/miss_table_true_vertical.csv
 create mode 100644 analysis/2026-07-19-true-vertical-audit/plots/miss_scatter_old_vs_true.png
 create mode 100644 analysis/2026-07-19-true-vertical-audit/run_true_vertical_audit.py
 create mode 100644 analysis/2026-07-19-true-vertical-audit/summary.json
 create mode 100644 analysis/2026-07-19-true-vertical-audit/true-vertical-audit.md
 create mode 100644 docs/thinktank/RESPONSE9.md

===== git log -1 --oneline =====
7113b1a Advisory-6 lands: braking-band formula, fresh-vision-only aborts, honest gravity behind a gate

===== git merge-base --is-ancestor 2c5057a HEAD && echo OK =====
OK
```

## Counted flights

| Count | Attempt | Log ID | Gates | Clips | Env hits | Result | Dur s | Closest direct fix + center px | Phase sequence | Visual observation |
|---:|---:|---|---:|---:|---:|---|---:|---|---|---|
| 1 | 1 | `20260719T121141-f186c83e` | 0 | 0 | 27 | environment collision (impulse=1.3) | 15.88 | 0.85m @ t+9.54s, center [319.5, 125.5] | hover -> takeoff -> align -> commit -> retreat -> recover -> commit -> retreat -> commit -> retreat -> search -> hover | ALIGN before COMMIT t+1.52-2.26s; then dash t+2.26-4.02s. |
| 2 | 2 | `20260719T121258-f186c83e` | 0 | 0 | 1 | environment collision (impulse=6.1) | 17.55 | 3.95m @ t+2.29s, center [312.0, 318.0] | hover -> takeoff -> align -> commit -> retreat -> search -> align -> hover | ALIGN before COMMIT t+1.50-2.28s; then dash t+2.28-3.74s. |
| 3 | 5 | `20260719T121637-f186c83e` | 0 | 0 | 12 | environment collision (impulse=1.5) | 15.08 | 1.76m @ t+11.03s, center [276.4, 111.2] | hover -> takeoff -> align -> commit -> retreat -> commit -> retreat -> search -> align -> commit -> recover | ALIGN before COMMIT t+1.51-2.27s; then dash t+2.27-4.25s. |

## Rejected attempts

- Attempt 3: 20260719T121416-f186c83e r2ok=True unique=260 (need >300)
- Attempt 4: 20260719T121528-f186c83e r2ok=True unique=197 (need >300)

## Cycle answer

No counted pass in this cycle: all three counted verified-R2 flights reported 0 gates passed. The phantom fix did not convert the approach into a counted pass in these three runs.

## Slice verification

| Count | Slice file | Unique frames | ~sec @30fps | Span s | Size MB |
|---:|---|---:|---:|---:|---:|
| 1 | `20260719T121141-f186c83e_takeoff_to_end.aigprec` | 382 | 12.7 | 12.7 | 17.4 |
| 2 | `20260719T121258-f186c83e_takeoff_to_end.aigprec` | 431 | 14.4 | 14.4 | 16.7 |
| 3 | `20260719T121637-f186c83e_takeoff_to_end.aigprec` | 360 | 12.0 | 12.0 | 14.6 |
