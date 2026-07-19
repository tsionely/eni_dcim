# Phase 6i RATE A/B (PARTIAL - live-arm no-go per protocol)

- **Date:** 2026-07-19 20:38:11 +0300
- **Operator role:** SIM OPERATOR (Sakana)
- **HEAD flown:** `fd6c3efca69a23b6c0c49308313e1516a2daebf6` (`fd6c3ef N0 autopsy: prediction refuted — the chase deaths are REAL-gate acquisition churn; N2 promoted to critical path`); `20395de` ancestor verified OK.
- **Wrapper bug FIXED:** prior unique=0 misread was a PowerShell function that both wrote to the pipeline (Add-Report/Tee) and returned values, polluting the return array. Phase 6i captures analyzer/slicer JSON inline; self-tested a known log at unique=301, gates=1. No F1 retry loop recurred.
- **Counting rule:** verified R2 + TAKEOFF->end slice >300 unique frames. Alternating F1/F3/F5 control, F2/F4/F6 live.

## PROTOCOL STOP

**Stopped after F2 (first live arm) on a protocol no-go.** Reason: first term ownership at 4.1m (>2.5m); env contact with term-dominant ownership (term=292 alt=5). Per amended protocol, live-arm stop-conditions halt the cycle and we push what we have. Only F1 (control) and F2 (live) counted; F3-F6 not flown.

## Counted flights
| Slot | Arm | Log ID | Gates | Clips | Env | Result | Closest fix + px | age@closest | First term range (live) | Owner hist | agi_max | Death | Phase sequence |
|---:|---|---|---:|---:|---:|---|---|---|---|---|---:|---|---|
| 1 | control | `20260719T173050-f170ead6` | 0 | 0 | 1 | environment collision (impulse=17.0) | 1.39m @ t+3.82s, [515.0, 211.7] | 0.010s | n/a (control) | {"alt": 2, "term": 111} | 0 | t+11.456 environment collision (impulse=17.0) | hover -> takeoff -> commit -> retreat -> search -> approach -> search -> align |
| 2 | live | `20260719T173427-50f9dcc8` | 0 | 0 | 4 | environment collision (impulse=1.8) | 1.61m @ t+12.14s, [381.8, 341.8] | 1.201s | 4.1m up=-0.8155507191128664 | {"alt": 5, "term": 292} | 0 | t+13.364 environment collision (impulse=1.8) | hover -> takeoff -> align -> commit -> retreat -> align -> commit -> retreat -> align -> commit -> retreat -> recover |

## Rejected attempts

- Attempt 1 slot 1 arm control: r2ok=True unique=145
- Attempt 3 slot 2 arm live: r2ok=True unique=255
- Attempt 4 slot 2 arm live: r2ok=True unique=243

## Questions this cycle can / cannot answer

- **Control pass rate / TERM effect / gate-2 killer:** NOT answerable from this partial (1 control + 1 live counted, both 0 gates, agi_max=0 - neither reached gate 2). The cycle halted on the live no-go before a statistic could form.
- **Key live finding (the stop trigger):** with terminal enabled, `term` took vertical ownership starting at ~4.1 m (beyond the <=2.5 m admission corridor) and stayed terminal-dominant (term=292 vs alt=5) through an environment contact; first-term up_legacy_mps ~ -0.82 m/s at 4.1 m = an early large downward terminal command far from the gate. Implicates premature/over-far TERM authority admission on this build - exactly what the stop-condition catches. The control arm logs owner telemetry too (term appears in shadow ~5.2 m) but does not act on it; its abort was an unrelated env collision (impulse 17.0).

## Slice verification
| Slot | Slice | Unique frames | Span s | MB |
|---:|---|---:|---:|---:|
| 1 | `20260719T173050-f170ead6_takeoff_to_end.aigprec` | 345 | 11.5 | 15.4 |
| 2 | `20260719T173427-50f9dcc8_takeoff_to_end.aigprec` | 402 | 13.4 | 24.2 |