# Phase 6d FICTION GUARDS — clean verified-R2 cycle

- **Date (local):** 2026-07-19 16:48:36 +03:00
- **Operator role:** SIM OPERATOR (Sakana)
- **Sim version:** AI-GP Simulator v1.0.3385
- **Branch HEAD flown:** `31f7da5cfa75061221de24d078f3ddd4ab7d3e20` (`31f7da5 [tuning] frame-fix windows ci and mock campaign`). Named code commit `524104f` verified as ancestor (OK).
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
At line:189 char:52
+ ... "`n===== git checkout main =====`n" + (git checkout main 2>&1 | Out-S ...
+                                            ~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (Already on 'main':String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
Your branch is up to date with 'origin/main'.

===== git pull =====
git : From https://github.com/tsionely/eni_dcim
At line:190 char:43
+   $step0 += "`n===== git pull =====`n" + (git pull 2>&1 | Out-String)
+                                           ~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (From https://gi...ionely/eni_dcim:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
   76091b1..31f7da5  main       -> origin/main
Updating 76091b1..31f7da5
Fast-forward
 config/params_default.json                         |   6 +-
 docs/design/terminal-vertical-wiring.md            |  22 +-
 docs/thinktank/RESPONSE10.md                       |  83 +++++
 src/aigp/planning/race_planner.py                  |  48 ++-
 tests/unit/test_planner.py                         |  23 ++
 .../all-flights.csv                                |  81 ++++
 .../campaign-config.json                           |  50 +++
 .../sakana-next-patch.txt                          |   1 +
 .../seed-20260719/best-params.json                 |  15 +
 .../seed-20260719/flights.csv                      |  41 +++
 .../seed-20260719/score_progression.csv            |  41 +++
 .../seed-20260720/best-params.json                 |  15 +
 .../seed-20260720/flights.csv                      |  41 +++
 .../seed-20260720/score_progression.csv            |  41 +++
 .../summary.json                                   | 102 ++++++
 .../summary.md                                     | 103 ++++++
 tuning/framefix-campaign-runner-output.txt         | Bin 0 -> 58186 bytes
 .../head-78c8461-run01.txt                         |   2 +
 .../head-78c8461-run02.txt                         |  47 +++
 .../head-78c8461-run03.txt                         |   2 +
 .../head-78c8461-run04.txt                         |  47 +++
 .../head-78c8461-run05.txt                         |   2 +
 .../head-78c8461-run06.txt                         |  47 +++
 .../head-78c8461-run07.txt                         |   2 +
 .../head-78c8461-run08.txt                         |   2 +
 .../head-78c8461-run09.txt                         |   2 +
 .../head-78c8461-run10.txt                         |   2 +
 .../pre-fix-79d9f76-run01.txt                      |   2 +
 .../pre-fix-79d9f76-run02.txt                      |  47 +++
 .../pre-fix-79d9f76-run03.txt                      |   2 +
 .../pre-fix-79d9f76-run04.txt                      |  47 +++
 .../pre-fix-79d9f76-run05.txt                      |  47 +++
 .../pre-fix-79d9f76-run06.txt                      |   2 +
 .../pre-fix-79d9f76-run07.txt                      |  47 +++
 .../pre-fix-79d9f76-run08.txt                      |   2 +
 .../pre-fix-79d9f76-run09.txt                      |   2 +
 .../pre-fix-79d9f76-run10.txt                      |   2 +
 .../single-gate-runs.csv                           |  21 ++
 .../single-gate-runs.json                          | 223 +++++++++++
 .../summary.md                                     |  39 ++
 tuning/framefix-single-gate-runner-output-r2.txt   | Bin 0 -> 2014 bytes
 tuning/pytest-windows-78c8461-basetemp-full.txt    | Bin 0 -> 19036 bytes
 tuning/run_framefix_mock_campaign.py               | 406 +++++++++++++++++++++
 tuning/run_framefix_single_gate_reliability.py     | 232 ++++++++++++
 tuning/windows-ci.md                               |  38 ++
 45 files changed, 2014 insertions(+), 13 deletions(-)
 create mode 100644 docs/thinktank/RESPONSE10.md
 create mode 100644 tuning/campaigns/2026-07-19-framefix-78c8461-20260719T115958Z/all-flights.csv
 create mode 100644 tuning/campaigns/2026-07-19-framefix-78c8461-20260719T115958Z/campaign-config.json
 create mode 100644 tuning/campaigns/2026-07-19-framefix-78c8461-20260719T115958Z/sakana-next-patch.txt
 create mode 100644 tuning/campaigns/2026-07-19-framefix-78c8461-20260719T115958Z/seed-20260719/best-params.json
 create mode 100644 tuning/campaigns/2026-07-19-framefix-78c8461-20260719T115958Z/seed-20260719/flights.csv
 create mode 100644 tuning/campaigns/2026-07-19-framefix-78c8461-20260719T115958Z/seed-20260719/score_progression.csv
 create mode 100644 tuning/campaigns/2026-07-19-framefix-78c8461-20260719T115958Z/seed-20260720/best-params.json
 create mode 100644 tuning/campaigns/2026-07-19-framefix-78c8461-20260719T115958Z/seed-20260720/flights.csv
 create mode 100644 tuning/campaigns/2026-07-19-framefix-78c8461-20260719T115958Z/seed-20260720/score_progression.csv
 create mode 100644 tuning/campaigns/2026-07-19-framefix-78c8461-20260719T115958Z/summary.json
 create mode 100644 tuning/campaigns/2026-07-19-framefix-78c8461-20260719T115958Z/summary.md
 create mode 100644 tuning/framefix-campaign-runner-output.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/head-78c8461-run01.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/head-78c8461-run02.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/head-78c8461-run03.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/head-78c8461-run04.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/head-78c8461-run05.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/head-78c8461-run06.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/head-78c8461-run07.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/head-78c8461-run08.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/head-78c8461-run09.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/head-78c8461-run10.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/pre-fix-79d9f76-run01.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/pre-fix-79d9f76-run02.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/pre-fix-79d9f76-run03.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/pre-fix-79d9f76-run04.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/pre-fix-79d9f76-run05.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/pre-fix-79d9f76-run06.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/pre-fix-79d9f76-run07.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/pre-fix-79d9f76-run08.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/pre-fix-79d9f76-run09.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/pre-fix-79d9f76-run10.txt
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/single-gate-runs.csv
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/single-gate-runs.json
 create mode 100644 tuning/framefix-single-gate-20260719T114643Z/summary.md
 create mode 100644 tuning/framefix-single-gate-runner-output-r2.txt
 create mode 100644 tuning/pytest-windows-78c8461-basetemp-full.txt
 create mode 100644 tuning/run_framefix_mock_campaign.py
 create mode 100644 tuning/run_framefix_single_gate_reliability.py

===== git log -1 --oneline =====
31f7da5 [tuning] frame-fix windows ci and mock campaign

===== git merge-base --is-ancestor 524104f HEAD && echo OK =====
OK
```

## Counted flights

| Count | Attempt | Log ID | Gates | Clips | Env hits | Result | Dur s | Closest direct fix + center px | Phase sequence |
|---:|---:|---|---:|---:|---:|---|---:|---|---|
| 1 | 1 | `20260719T134326-2477345e` | 0 | 9 | 1 | environment collision (impulse=4.8) | 18.50 | 0.74m @ t+7.77s, center [320.4, 522.7] | hover -> takeoff -> align -> commit -> retreat -> align -> commit -> recover -> commit -> retreat -> search |
| 2 | 2 | `20260719T134446-2477345e` | 0 | 0 | 2 | environment collision (impulse=6.5) | 17.90 | 1.16m @ t+14.65s, center [246.0, 112.5] | hover -> takeoff -> align -> commit -> retreat -> search -> commit |
| 3 | 4 | `20260719T134714-2477345e` | 0 | 0 | 0 | stale channels: frame | 62.06 | 3.75m @ t+4.62s, center [311.0, 266.7] | hover -> takeoff -> approach -> commit -> retreat -> approach -> search -> commit -> retreat -> search |

## Fiction-guard expectations vs observed

- **Env hits per counted flight:** 1, 2, 0 (phase6c counted were 27 / 1 / 12). Watch for reduction from removing fiction climbs / stale re-commits.
- **Retries pausing in approach until vision refreshes:** phase sequences above show the approach/commit/retreat structure; look for approach dwell rather than immediate stale re-commit.
- Visual observation this pass is telemetry + periodic screen samples (verification JPGs), not continuous human viewing.

## A6 far rider (8-20m far-approach reference)

- Slice `20260719T134446-2477345e_a6_far_reference.aigprec` from flight `20260719T134446-2477345e`: 108 unique frames, span 3.6s, far range 9.57-19.61 m (62 far detections), 6.0 MB.

## Cycle answer

No counted pass this cycle: all three counted verified-R2 flights reported 0 gates passed. See env-hit comparison above for the fiction-guard effect.

## Slice verification

| Count | Slice file | Unique frames | ~sec @30fps | Span s | Size MB |
|---:|---|---:|---:|---:|---:|
| 1 | `20260719T134326-2477345e_takeoff_to_end.aigprec` | 458 | 15.3 | 15.2 | 22.7 |
| 2 | `20260719T134446-2477345e_takeoff_to_end.aigprec` | 443 | 14.8 | 14.7 | 16.1 |
| 3 | `20260719T134714-2477345e_takeoff_to_end.aigprec` | 1751 | 58.4 | 58.3 | 58.5 |
