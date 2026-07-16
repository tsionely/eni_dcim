# Phase 4b v2 — R2-TRAINING chain: time-based relock escape hatch

- **Date (local):** 2026-07-16 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385** (`AI GP 1.0.3385` in HUD)
- **Flight code commit:** `54a75a1` — `Time-based relock escape hatch (0.11s was an accident at 224Hz)`
- **SIM LOCK:** created at `C:\Temp\eni_dcim_sim.lock` before sim launch.
- **Track:** R2-TRAINING.
- **Command:** default speeds, `--max-duration 300 --patch safety.flight_timeout_s=300`.

## Summary verdict
- Three required flights plus one replacement were attempted.
- Valid race attempts: F1 and F3. F2 and replacement F2b were no-race telemetry timeouts (`frames=0`, `detections=0`, `race_start=-1`).
- **No gates passed** in this sample, so the post-pass RIGHT-next-gate relock path was not exercised.
- F3 does show the important post-miss behavior: after commit/retreat it kept working the near/same Gate 1 region (gate clips and close direct fix) rather than obviously chasing a far 27m gate. It still did not pass.

## Flight results

### F1 default chain v2
ID: `20260716T153120-927a4c97`
- Result: `environment collision (impulse=4.0)`
- Duration: `24.3s`
- `gates_passed=0`, `gate_clips=0`, `env_hits=1`
- Phase sequence: `hover -> takeoff -> approach`
- Attempts: approach=1, commit=0, retreat=0
- Closest direct: `dist=1.29m`, center-x / HIGH
- Closest state: `dist=2.72m`, center-x / center-y, age `1.28s`
- Hard hit: `t+25.2s`, impulse `3.95`, threat 2
- Observation: fast approach toward Gate 1, but hit before commit/retry could exercise relock.

### F2 default chain v2
ID: `20260716T153248-927a4c97`
- Result: `max duration`
- Duration: `300s`
- `gates_passed=0`
- Invalid/no-race telemetry: `frames=0`, `detections=0`, `imu=0`, `race_start=-1`
- Phase sequence: `hover -> takeoff -> search`
- Observation: helper clicked R2/RACE, but telemetry never became a valid FPV/race stream.

### F2b default chain v2 replacement
ID: `20260716T154201-927a4c97`
- Result: `max duration`
- Duration: `300s`
- `gates_passed=0`
- Invalid/no-race telemetry: `frames=0`, `detections=0`, `imu=0`, `race_start=-1`
- Phase sequence: `hover -> takeoff -> search`
- Observation: replacement repeated the no-race telemetry failure; included for diagnosis.

### F3 default chain v2
ID: `20260716T153853-927a4c97`
- Result: `environment collision (impulse=5.0)`
- Duration: `31.5s`
- `gates_passed=0`, `gate_clips=2`, `env_hits=1`
- Phase sequence: `hover -> takeoff -> approach -> commit -> retreat -> approach -> commit -> retreat -> recover -> approach -> search`
- Attempts: approach=3, commit=2, retreat=2, recover=1, search=1
- Closest direct: `dist=1.31m`, RIGHT / center-y
- Closest state: `dist=0.06m`, LEFT / LOW, age `0.89s`
- Collisions: `t+29.1s` impulses `0.45` and `5.63`; `t+32.5s` impulse `5.05`
- Observation: after retreat, the pilot continued to work the close Gate 1/miss region (2 gate clips, close direct fix) rather than immediately chasing a far side gate. Altitude during retry looked better than earlier ground-scrape cascades, but the run still hit before pass.

## Relock / retry observations
- No gate pass, so no RIGHT next-gate lock after a pass could be evaluated.
- F3 is the useful relock-sanity evidence: post-miss behavior stayed local/near Gate 1 and did not show the old immediate far-gate chase signature.
- The approach is close but still not stamping Gate 1 reliably; F3 had two gate clips and no official pass.

## Slices
No pass+20s slices exist because there were no passes. Included no-pass start/attempt slices for valid race attempts:
- `20260716T153120-927a4c97_r2b_v2_nopass_start_slice.aigprec`
- `20260716T153853-927a4c97_r2b_v2_nopass_start_slice.aigprec`

## Fixture contents
- `report.txt` — full console output.
- `phase4b_v2_r2training_chain_analysis.txt` — gates/phase/collision/closest-fix analysis.
- logs/results/params for F1, F2, F2b, F3.
- 2 no-pass recording slices for the valid race attempts.
- `screens/` — downscaled screenshots for all attempts.
- Full recordings for valid attempts exceed the git fixture size limit and remain local / Drive candidates.
