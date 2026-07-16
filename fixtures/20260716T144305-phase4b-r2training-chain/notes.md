# Phase 4b — R2-TRAINING chain: relock sanity + retry altitude

- **Date (local):** 2026-07-16 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385** (`AI GP 1.0.3385` in HUD)
- **Flight code commit:** `e742cf1` — `Relock distance sanity: stop chasing far gates after a near miss`
- **Also included:** `fd9d419` retreat climb-bias/altitude fix and `43ef2b0` scheduler RX fix.
- **SIM LOCK:** created at `C:\Temp\eni_dcim_sim.lock` before sim launch.
- **Track:** R2-TRAINING.
- **Command:** default speeds, `--max-duration 300 --patch safety.flight_timeout_s=300`.

## Summary verdict
- Three valid Phase 4b R2-TRAINING default-speed chain flights were run.
- **No gates passed** in this sample (`gates_passed=0` for all three).
- Because there were no passes, the RIGHT-next-gate relock-after-pass path was **not exercised**, and there were no pass+20s windows to slice.
- I committed no-pass start/attempt slices instead, named `*_r2b_nopass_start_slice.aigprec`.

## Flight results

### F1 default chain
ID: `20260716T143604-927a4c97`
- Result: `environment collision (impulse=3.7)`
- Duration: `31.4s`
- `gates_passed=0`, `gate_clips=0`, `env_hits=1`
- Phase sequence: `hover -> takeoff -> approach -> commit -> retreat -> approach -> commit -> retreat`
- Attempts: approach=2, commit=2, retreat=2
- Closest direct: `4.39m`, center-x / LOW
- Closest state: `0.14m`, LEFT / LOW, age `0.87s`
- Hard hit: one threat-2 collision at `t+32.4s`, impulse `3.69`.
- Retry altitude note: despite two retreats, only one env hit; this is much cleaner than Phase 4a’s many ground scrapes, suggesting retreat altitude is improved, but it still ends in collision before pass.

### F2 default chain
ID: `20260716T143739-927a4c97`
- Result: `environment collision (impulse=4.0)`
- Duration: `31.1s`
- `gates_passed=0`, `gate_clips=0`, `env_hits=1`
- Phase sequence: `hover -> takeoff -> approach -> commit -> retreat -> approach -> search`
- Attempts: approach=2, commit=1, retreat=1, search=1
- Closest direct: `1.85m`, LEFT / HIGH
- Closest state: `0.09m`, LEFT / LOW, age `1.09s`
- Hard hit: one threat-2 collision at `t+32.0s`, impulse `3.97`.
- Retry altitude note: one retreat, one env hit; again no repeated ground-scrape cascade, but no gate pass.

### F3 default chain
ID: `20260716T143915-927a4c97`
- Result: `environment collision (impulse=13.4)`
- Duration: `26.6s`
- `gates_passed=0`, `gate_clips=0`, `env_hits=2`
- Phase sequence: `hover -> takeoff -> approach -> commit -> recover`
- Attempts: approach=1, commit=1, retreat=0, recover=1
- Closest direct: `4.82m`, RIGHT / LOW
- Closest state: `0.57m`, LEFT / LOW, age `1.46s`
- Hard hit: threat-2 collision at `t+27.6s`, impulse `13.42`.
- This was the hardest hit in this set and occurred before any pass/relock.

## Pass / relock observations
- No flight passed Gate 1, so there is no post-pass segment and no RIGHT next-gate lock to evaluate.
- Relock distance sanity after a **near miss** may have affected F1/F2 retry behavior, but there was no gate index advancement and no far-gate chase observed.
- The main failure in this sample remains getting through Gate 1 consistently, not chaining after a pass.

## Slices
No pass+20s slices exist because there were no passes. Included instead:
- `20260716T143604-927a4c97_r2b_nopass_start_slice.aigprec`
- `20260716T143739-927a4c97_r2b_nopass_start_slice.aigprec`
- `20260716T143915-927a4c97_r2b_nopass_start_slice.aigprec`

## Fixture contents
- `report.txt` — full console output.
- `phase4b_r2training_chain_analysis.txt` — gates/phase/collision/closest-fix analysis.
- logs/results/params for all 3 selected Phase 4b flights.
- 3 no-pass start/attempt recording slices (~28.88 MB each).
- `screens/` — downscaled screenshots for F1/F2/F3.
- Full recordings (231-329 MB) exceed the git fixture size limit and remain local / Drive candidates.
