# R26 Anchor Run on 3c4c5d9

Role: QA & MOCK-TUNER.
Scope: recorded-video replay plus synthetic oracle micro-replays only; no real simulator was launched.

Artifacts: `tuning/anchor-r26-3c4c5d9-3c4c5d9-20260720T102340Z/`
Source commit: `3c4c5d9263bbbde30c1332614b974d2fe6978b1e`
Repo HEAD: `3c4c5d9263bbbde30c1332614b974d2fe6978b1e`

## Verdicts

| Gate | Verdict | Key result |
|---|---|---|
| R26-1 liveness | PASS | Forced FULL loss at frame 304 produced `owner_term_side_rows=16`, `side_shadow_capture_rows=1`, max side admission `0.271 <= 0.30`, min side range `1.006m`, phase unchanged. |
| R26-2/3 sigma_a | FAIL | Measured `sigma_a_rms=1.956 m/s^2`, above the pre-registered live gate `~0.35 m/s^2`; floor row at measured sigma_a is `1.046m`, outside the `0.30m` corridor. |
| R26-4 side-offset isolation | PASS | SIDE offset did not move the FULL rate anchor; final `rate_source=FULL_RATE_ANCHOR`. |
| R26-5 contradiction invalidation | PASS | Contradictory SIDE sequence invalidated the anchor; final `rate_source=ANCHOR_INVALID`. |
| R26-6 FULL return upgrade | PASS | Three consistent FULL observations upgraded back to `FULL_QUAD`; anchor cleared. |

## Telemetry Note

`rate_source` and `rate_anchor_age_s` are present in every generated term row. However, the code-reported `rate_anchor_age_s` stayed frozen at `0.167s` while elapsed anchor age advanced from `0.167s` to `0.431s`. The harness therefore reports both `rate_anchor_age_s` and `rate_anchor_elapsed_s`; sigma_a scoring uses elapsed anchor age.

## Harness Note

The replay harness was updated under `tuning/run_l1_perception_replay.py` to match the current perception pipeline: side parallel production now uses the fallback-realistic prior, passes `z_m` into certificate anchoring, and preserves the side-armed latch through detector loss. Before that harness fix, the replay falsely reproduced the old `owner_term_side_rows=0` baseline.

## Verification

- `python -m py_compile tuning/run_anchor_r26.py` passed.
- `python -m py_compile tuning/run_l1_perception_replay.py` passed.
- Targeted `pytest tests/unit/test_vertical_owner.py` was attempted, but both available Python runtimes in this session reported `No module named pytest`; no dependency installation was performed.
