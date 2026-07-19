# Phase 6b ALIGNED DASH — clean verified-R2 cycle

- **Date (local):** 2026-07-19 11:03:21 +03:00
- **Operator role:** SIM OPERATOR (Sakana)
- **Sim version:** AI-GP Simulator v1.0.3385
- **Branch HEAD flown:** `93fba45830fb5fb991a6fbe8f91e417aab29b36b` (`93fba45` Align-then-dash).
- **Command:** `python scripts/fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300` (no strategy patches).
- **Counting rule:** verified R2-TRAINING + TAKEOFF->end slice with >300 unique frames (>10s @30fps). Stopped immediately at exactly three counted flights.

## Step 0 git verification output

```text
===== git status =====
On branch main
Your branch is up to date with 'origin/main'.

Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070410-fab49fbf-flight.jsonl
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070410-fab49fbf-params.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070410-fab49fbf-result.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070410-fab49fbf_takeoff_to_end.aigprec
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070844-fab49fbf-flight.jsonl
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070844-fab49fbf-params.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070844-fab49fbf-result.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070844-fab49fbf_takeoff_to_end.aigprec
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070959-fab49fbf-flight.jsonl
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070959-fab49fbf-params.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070959-fab49fbf-result.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/20260719T070959-fab49fbf_takeoff_to_end.aigprec
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/manifest.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/notes.md
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/report.txt
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/summary.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_000.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_002.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_eventlist.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_race.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_race_dialog.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_row_highlight.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_select.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_verify_after_race.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_000.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_002.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_006.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_eventlist.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_race.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_race_dialog.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_row_highlight.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_select.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_verify_after_race.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_000.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_002.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_006.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_eventlist.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_race.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_race_dialog.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_row_highlight.jpg
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_select.json
	new file:   fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_verify_after_race.jpg

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	phase6b_aligned_dash_report.txt
	scripts/launch_sim.ps1
	tests/unit/test_attitude_rate_backend.py


===== git checkout main =====
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070410-fab49fbf-flight.jsonl
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070410-fab49fbf-params.json
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070410-fab49fbf-result.json
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070410-fab49fbf_takeoff_to_end.aigprec
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070844-fab49fbf-flight.jsonl
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070844-fab49fbf-params.json
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070844-fab49fbf-result.json
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070844-fab49fbf_takeoff_to_end.aigprec
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070959-fab49fbf-flight.jsonl
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070959-fab49fbf-params.json
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070959-fab49fbf-result.json
A	fixtures/20260719T072447-phase6b-aligned-dash/20260719T070959-fab49fbf_takeoff_to_end.aigprec
A	fixtures/20260719T072447-phase6b-aligned-dash/manifest.json
A	fixtures/20260719T072447-phase6b-aligned-dash/notes.md
A	fixtures/20260719T072447-phase6b-aligned-dash/report.txt
A	fixtures/20260719T072447-phase6b-aligned-dash/summary.json
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_000.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_002.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_eventlist.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_race.json
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_race_dialog.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_row_highlight.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_select.json
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try3_verify_after_race.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_000.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_002.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_006.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_eventlist.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_race.json
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_race_dialog.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_row_highlight.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_select.json
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F1_try7_verify_after_race.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_000.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_002.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_006.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_eventlist.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_race.json
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_race_dialog.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_row_highlight.jpg
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_select.json
git : Already on 'main'
At line:8 char:10
+ $out += (git checkout main 2>&1 | Out-String)
+          ~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (Already on 'main':String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
A	fixtures/20260719T072447-phase6b-aligned-dash/track_verification/phase6b_aligned_dash_F2_try8_verify_after_race.jpg
Your branch is up to date with 'origin/main'.

===== git pull =====
Already up to date.

===== git log -1 --oneline =====
93fba45 Align-then-dash: the 1.6m height deficit is measured — close it BEFORE the commit
```

## Counted flights

| Count | Attempt | Log ID | Gates | Clips | Env hits | Result | Dur s | Closest direct fix + center px | Phase sequence | Visual observation |
|---:|---:|---|---:|---:|---:|---|---:|---|---|---|
| 1 | 1 | `20260719T074950-fab49fbf` | 0 | 0 | 3 | environment collision (impulse=1.5) | 21.30 | 4.12m @ t+2.84s, center [232.2, 392.2] | hover -> takeoff -> align -> commit -> retreat -> approach -> hover | ALIGN before COMMIT t+2.50-2.84s; then dash t+2.84-4.80s. |
| 2 | 4 | `20260719T075333-fab49fbf` | 0 | 1 | 1 | environment collision (impulse=15.9) | 14.04 | 0.82m @ t+4.12s, center [315.6, 233.5] | hover -> takeoff -> commit -> retreat -> recover -> approach -> search -> approach | No sustained ALIGN before first commit; drone dashes soon after takeoff. Screen samples/telemetry show early env collision, not a clean rise-then-level surge. |
| 3 | 12 | `20260719T080255-fab49fbf` | 0 | 0 | 1 | environment collision (impulse=9.1) | 14.10 | 1.03m @ t+10.84s, center [294.5, 87.3] | hover -> takeoff -> commit -> retreat -> search -> approach -> commit -> hover | No sustained ALIGN before first commit; drone dashes soon after takeoff. Screen samples/telemetry show early env collision, not a clean rise-then-level surge. |

## Rejected attempts

- Attempt 2: 20260719T075113-fab49fbf r2ok=True unique=296 (need >300)
- Attempt 3: 20260719T075227-fab49fbf r2ok=True unique=118 (need >300)
- Attempt 5: 20260719T075448-fab49fbf r2ok=True unique=277 (need >300)
- Attempt 6: 20260719T075600-fab49fbf r2ok=True unique=282 (need >300)
- Attempt 7: 20260719T075713-fab49fbf r2ok=True unique=143 (need >300)
- Attempt 8: 20260719T075820-fab49fbf r2ok=True unique=138 (need >300)
- Attempt 9: 20260719T075928-fab49fbf r2ok=True unique=121 (need >300)
- Attempt 10: 20260719T080035-fab49fbf r2ok=True unique=269 (need >300)
- Attempt 11: 20260719T080147-fab49fbf r2ok=True unique=140 (need >300)

## Cycle answer

No pass in this clean cycle. All three counted verified-R2 flights failed with 0 gates passed and 0 clips. The intended first-approach `takeoff -> align -> commit` behavior was not observed as a sustained pre-commit climb; the log sequences are dominated by `takeoff -> commit` first, with any `align` occurring later on retry/miss paths. The drone did not visibly execute the requested rise ~0.6-1m almost in place before the dash; it surged/committed early and collided with the environment.

## Slice verification

| Count | Slice file | Unique frames | ~sec @30fps | Span s | Size MB |
|---:|---|---:|---:|---:|---:|
| 1 | `20260719T074950-fab49fbf_takeoff_to_end.aigprec` | 540 | 18.0 | 18.0 | 23.5 |
| 2 | `20260719T075333-fab49fbf_takeoff_to_end.aigprec` | 328 | 10.9 | 10.9 | 14.3 |
| 3 | `20260719T080255-fab49fbf_takeoff_to_end.aigprec` | 326 | 10.9 | 10.8 | 16.8 |
