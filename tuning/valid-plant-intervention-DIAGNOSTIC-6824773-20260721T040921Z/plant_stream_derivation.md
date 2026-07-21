# Plant Stream Derivation

Source: archived `flight.jsonl` records, topic `setpoint`.

Per-era field naming is disclosed in `harness_stream_disclosure.csv`.

For each forced-withhold row, the generator locates the last setpoint
sample at or before the replay feature `mono_ns`. The vertical body
component is read from `setpoint.v_body[2]` when present, otherwise
`setpoint.vel_body[2]` or `setpoint.velocity_body[2]`.

Stream contract: Contract B, commanded velocity reference. The logged
setpoint is the innermost commanded reference delivered to the velocity
backend, not achieved motion. The counterfactual therefore enters through
the declared response model rather than raw zero-lag subtraction.

The world-up conversion follows the adapter equation registered in
the criterion:

`v_up = -v_bz * cos(level_pitch) * cos(level_roll)`

Here `v_bz` is the logged body-z plant input; negative body-z means
climb in the NED/body convention used by the planner tests, so the
leading minus maps climb to positive world-up.

Response model: pure-delay command reference, lag calibrated from A091 only at `0.150` s.
Ownership gate: rows whose prior `term_status.owner` is `term` get
`contract_b_correction_vz_up_mps = 0.0` as the RESPONSE63 structural no-op.
All other rows use the delayed logged setpoint world-up value.
For each feature row:

`delayed_logged_setpoint_vz_up_mps = setpoint_world_up_at_or_before(feature_mono_ns - lag)`

The intervention residual is:

`r_after = v_ref_oracle_mps - (v_latch_true_mps + contract_b_correction_vz_up_mps)`

The old zero-lag correlation gate is withdrawn by RESPONSE61 and is
published only as diagnostic disclosure.

