# Plant Stream Derivation

Source: archived `flight.jsonl` records, topic `setpoint`.

Per-era field naming is disclosed in `harness_stream_disclosure.csv`.

For each forced-withhold row, the generator locates the last setpoint
sample at or before the replay feature `mono_ns`. The vertical body
component is read from `setpoint.v_body[2]` when present, otherwise
`setpoint.vel_body[2]` or `setpoint.velocity_body[2]`.

The world-up conversion follows the adapter equation registered in
the criterion:

`v_up = -v_bz * cos(level_pitch) * cos(level_roll)`

Here `v_bz` is the logged body-z plant input; negative body-z means
climb in the NED/body convention used by the planner tests, so the
leading minus maps climb to positive world-up.

