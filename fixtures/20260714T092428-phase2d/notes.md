# Phase 2d — Decisive sign experiment (Mode E)

- **Date (local):** 2026-07-14 ~12:07-12:24 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit:** `b51571c...` (branch `main`, clean pull; see manifest.json)
- **Ground rules honored:** no edits to `src/`, `config`, `simtools`, `tests`, or `docs`.
- **No fly_once this cycle**, per runbook.

## Single-instance verification
Exactly one simulator instance:
- `FlightSim.exe` PID 56276
- `DCGame-Win64-Shipping.exe` PID 49312
- engine owns `udp:14560` and `udp:5601`
- no stray python processes at preflight.

## Run 1 — control_probe --modes E
Race was started while the probe waited for GO; probe printed `GO!`.

Open-loop verdict block, verbatim:

```text
  === open-loop verdict ===
  commanded: RAW pitch rate +0.30 for 0.5s (expected +0.15 rad nose-up)
  gyro-integrated pitch: -0.399 rad
  accel f_x after settle: -1.35 m/s^2 -> physical pitch NOSE-DOWN
  interpretation:
    physical NOSE-UP  + gyro negative -> COMMANDS standard, GYRO inverted
    physical NOSE-DOWN + gyro negative -> COMMANDS inverted, gyro fine
    |gyro_pitch|/0.15 = scale factor 2.66
```

## Run 2 — control_probe --modes E
Independent second race window; probe again printed `GO!`.

Open-loop verdict block, verbatim:

```text
  === open-loop verdict ===
  commanded: RAW pitch rate +0.30 for 0.5s (expected +0.15 rad nose-up)
  gyro-integrated pitch: -0.182 rad
  accel f_x after settle: -0.92 m/s^2 -> physical pitch NOSE-DOWN
  interpretation:
    physical NOSE-UP  + gyro negative -> COMMANDS standard, GYRO inverted
    physical NOSE-DOWN + gyro negative -> COMMANDS inverted, gyro fine
    |gyro_pitch|/0.15 = scale factor 1.21
```

## Operator conclusion
Both independent Mode E runs agree:
- RAW +pitch-rate command produces **negative gyro-integrated pitch**.
- Accelerometer after settle indicates **physical NOSE-DOWN**.
- The probe's own interpretation says this corresponds to:
  **COMMANDS inverted, gyro fine**.

So the evidence supports flipping the command side (at least pitch command sign), not gyro parsing. Run 1 and Run 2 differ in scale factor (2.66 vs 1.21), but the physical direction/verdict is consistent.

## Fixture notes
- `report.txt` contains the full console output including both runs and race-starter timestamps.
- `20260714T081945-bb5494d6-*` flight log files are **stale from Phase 2c**; no fly_once was run in Phase 2d. `collect_artifacts.py` copied the newest existing flight log.
- `vision.aigprec` was skipped as oversized (~519 MB), as expected.
