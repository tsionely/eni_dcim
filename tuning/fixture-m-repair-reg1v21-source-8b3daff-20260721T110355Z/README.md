# Fixture (m) Repair + REG-1v2.1 Source Generator

- DIAGNOSTIC token throughout.
- Replay/CSV/synthetic only; FlightSim/DCGame not launched.
- Required ancestor `62c9648` verified.
- Fixture (m) repair: leg 1 drives the real `TerminalOracle` through `observe()` and forces FULL->SIDE downgrade; leg 2 reconstructs with REG-1v2.1 fresh-tail, last-12 cap, and imported `robust_slope`.
- Battery covered: dense >12 samples, gapped mid-history outage, duplicate timestamps.
- Negative control covered: old fixed-0.50s reconstruction is asserted unequal on the dense series.
- Calibration source generator is committed only; no A091 calibration run was performed.
- Step-E fixture suite: 18 passed, 0 failed.
- REG-1v2.1 source fixture suite: 8 passed, 0 failed.
- Step F remains NO-GO because no REG-2 exists.
