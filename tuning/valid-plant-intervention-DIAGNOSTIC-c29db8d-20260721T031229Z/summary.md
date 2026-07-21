# Valid-Plant Intervention Rerun

Scope: DIAGNOSTIC, CSV/log replay only; no FlightSim/DCGame launch.
Repo HEAD: `c29db8d51b5f8eb4a3053f2f67d0dfd98c2e2ead`.
Criterion commit: `c29db8d51b5f8eb4a3053f2f67d0dfd98c2e2ead`.
Input manifest: `tuning/valid-plant-intervention-DIAGNOSTIC-c29db8d-20260721T031229Z/checkpoint_input_manifest.json`.
Input manifest sha256: `9ef2b4dbdf86f53fe9b5993fac16e1819759c3b52902c4a51dace99e5ef28f3f`.

## Plant Stream

The stream is read from archived `flight.jsonl` setpoint records and
converted with `v_up = -v_bz * cos(level_pitch) * cos(level_roll)`.
Max abs diff versus `features_archive.setpoint_vz_up_mps`: `4.440892098500626e-16`.

## Validity Pre-Check

Passed: `False`.
Invalid scopes: `phase6i/r-rate-ab=-0.6814289403069921, phase6k/cohort-2=-0.5548312683115861, phase6l/terminal_live=-0.8974190397044214, phase7m/metrology=-0.28867013304061073`.

## Judge

Judge status: `NOT_RUN_INVALID_INPUT_PRECHECK`.
Driver decomposition status: `NOT_RUN_INVALID_INPUT_PRECHECK`.

