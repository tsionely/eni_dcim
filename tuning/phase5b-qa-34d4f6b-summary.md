# Phase 5b QA Summary - `34d4f6b`

Generated: 2026-07-17.

Role: QA & MOCK-TUNER. Real simulator was not launched or controlled. Work paused whenever `C:\Temp\eni_dcim_sim.lock` appeared with a live operator/simulator cycle.

## Reflight Matrix

Harness: current HEAD `scripts/reflight.py` with frame dedupe, flight-log timing, estimator-prior pass-through, and close-tracker reporting. For `9fe3702`, the harness was copied into a temporary worktree with compatibility shims for the old detector API and missing close tracker.

Report: `tuning/phase5b-reflight-e9c1d97/fix-rate-head-vs-9fe3702.md`.

| Build | Runnable slices | Unique frames | Fixes | Fix rate | Accepted | Close-tracker fixes |
|---|---:|---:|---:|---:|---:|---:|
| `9fe3702` | 52 | 3233 | 2706 | 0.837 | 2407 | 0 |
| `34d4f6b` | 52 | 3233 | 2842 | 0.879 | 2676 | 11 |

New full-approach slices under `fixtures/20260717T092008-phase5b-confirm`:

| Slice | Frames | Old fixes / accepted / closest | HEAD fixes / accepted / closest | HEAD close-tracker |
|---|---:|---:|---:|---:|
| `20260717T090941...full.aigprec` | 344 | 254 / 185 / n/a | 261 / 212 / n/a | 0 |
| `20260717T091107...full.aigprec` | 367 | 270 / 196 / n/a | 269 / 233 / 2.14m | 7 |
| `20260717T091239...aigprec` | 321 | 131 / 75 / 1.06m | 123 / 72 / 1.03m | 3 |

## Windows CI

Command: `python -m pytest tests -q --basetemp=C:\Temp\pytest-eni`, using the bundled Codex Python runtime because the bare `python`/`py` launchers failed with the Windows logon-session error.

First sandboxed attempt reached `106 passed, 1 xfailed` but failed during `C:\Temp\pytest-eni` cleanup with `WinError 5`. Elevated rerun result:

`2 failed, 112 passed, 1 xfailed, 2 warnings in 50.42s`.

Failures:

| Test | Full-suite failure | Solo verdict |
|---|---|---|
| `test_single_gate_pass` | heartbeat timeout on `udpin:127.0.0.1:24550` | passed |
| `test_campaign_loop_against_mock` | heartbeat timeout on `udpin:127.0.0.1:24550` | passed |

The failures are load-sensitive heartbeat flakes, not deterministic solo failures.

## Closed-Loop Arbitration

Report: `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/closed-loop-arbitration.md`.

Each test node was run solo 3x per build. The `first_gate_with_second_visible` node is xfail-marked; the table below reports pytest-green return codes, with xfail/xpass details in per-run logs.

| Build | `single_gate` | `first_gate_with_second_visible` |
|---|---:|---:|
| `34d4f6b` | 1/3 | 3/3 pytest-green |
| `116b27e` | 1/3 | 3/3 pytest-green |

`single_gate` failures on both builds were environment-collision assertions, not heartbeat timeouts.

## Hover Overrun

Report: `tuning/phase5b-hover-34d4f6b/hover-overrun-telemetry.json`.

HEAD hover probe:

| Ticks | Overruns | `overrun_frac` | `max_late_us` | Abort reason |
|---:|---:|---:|---:|---|
| 1501 | 1116 | 0.7435043304463691 | 11000 | max duration |

Verdict: no material improvement from the prior ~0.74 Windows overrun baseline.
