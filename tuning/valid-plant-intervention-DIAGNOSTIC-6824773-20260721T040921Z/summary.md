# Contract-B Plant-Stream Intervention Rerun

Scope: DIAGNOSTIC, CSV/log replay only; no FlightSim/DCGame launch.
Repo HEAD: `68247733f97d385e3f5f34803cc20623bcd0998b`.
Criterion commit: `4d4827c4cb63029535e9f15124b9f084662f5137`.
Input manifest: `tuning/valid-plant-intervention-DIAGNOSTIC-6824773-20260721T040921Z/checkpoint_input_manifest.json`.
Input manifest sha256: `9ef2b4dbdf86f53fe9b5993fac16e1819759c3b52902c4a51dace99e5ef28f3f`.

## Plant Stream

The stream is read from archived `flight.jsonl` setpoint records and
converted with `v_up = -v_bz * cos(level_pitch) * cos(level_roll)`.
It is typed as Contract B commanded velocity reference, with pure-delay
response before entering the counterfactual residual.
A091 selected response lag: `0.15` seconds.
Max abs diff versus `features_archive.setpoint_vz_up_mps`: `4.440892098500626e-16`.

## Diagnostic Correlation

The old zero-lag positive-correlation gate is withdrawn; these rows are diagnostic only.
Non-positive zero-lag scopes: `phase6i/r-rate-ab=-0.6814289403069921, phase6k/cohort-2=-0.5548312683115861, phase6l/terminal_live=-0.8974190397044214, phase7m/metrology=-0.28867013304061073`.

## Judge

Judge status: `RUN_CONTRACT_B_RESPONSE_MODEL`.
Intervention verdict: `REFUTED_AS_REGISTERED_REMAINDER_EXPLANATION`.
Residual admissibility: `INADMISSIBLE_as_corrected_mechanism_drift_measurement`.
B before-large approaches: `4`.
A same-approach large-after: `4`.
D collapsed approaches: `0`.
Q quiet-after-large approaches: `0`.
Large cluster count after total: `22`.
Clusters dropped by intervention: `[]`.
Prediction refutation branch met: `False`.
Driver decomposition status: `RUN`.

## A/B/C/D

- `A_raw_shadow_residual`: point `0.0`, profile U95 `3.1533874493631515`, bootstrap U95 `0.30436364096952645`, conservative `3.1533874493631515`
- `B_cut_intercept_adjusted`: point `0.0`, profile U95 `5.148418549437215`, bootstrap U95 `0.24828988249935896`, conservative `5.148418549437215`
- `C_response_adjusted`: point `0.0`, profile U95 `15.547127976351447`, bootstrap U95 `0.0`, conservative `15.547127976351447`
- `D_both_adjusted`: point `0.0`, profile U95 `6.534834486359184`, bootstrap U95 `0.6242528939607876`, conservative `6.534834486359184`

