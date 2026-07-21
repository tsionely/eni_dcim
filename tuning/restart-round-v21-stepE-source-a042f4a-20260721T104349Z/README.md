# Restart Round v2.1 Step E + REG-1v2.1 Source Generator

- DIAGNOSTIC token throughout.
- Replay/CSV/synthetic only; FlightSim/DCGame not launched.
- REG-2(v2) is PENDING/VOID and startup refusal is expected/correct.
- RESPONSE69 applied: fixture (m) now drives the real `TerminalOracle` path and separately reconstructs `rate_anchor_v_raw` with fresh-tail, last-12, imported `robust_slope`.
- Step-E matrix: 18 passed, 0 failed.
- REG-1v2.1 source fixtures: 8 passed, 0 failed.
- No A091 execution, no 23-approach checkpoint read, no 4/23 artifact, no Contract-B residuals.
- Step F remains NO-GO because no REG-2 exists.
- Supersedes `tuning/restart-round-stepE-source-8e76b6e-20260721T072816Z/` for adjudicative purposes; its fixture (m) is VOID per RESPONSE69.
