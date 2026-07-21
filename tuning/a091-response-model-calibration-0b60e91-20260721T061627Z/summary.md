# A091 response-model calibration (REG-1)

DIAGNOSTIC token throughout. Replay/CSV only; no FlightSim/DCGame launch.

- generator commit: `0b60e9104fb04dac81be4e9bb297c2b8668e9f23`
- required ancestor cited: `9a85c73`
- REG-1 methodology commit observed: `fe69759b7a03b341b118410a536b8310e97f7aaf`
- source: `20260719T201851-50f9dcc8` DOWN-STEP intervals only
- calibration status: `CALIBRATED`
- best fit: `g=0.50, tau=0.60s, L=0 ticks, RMS=0.0102753797 m/s, n=13`
- qualifying windows: `1` of `12` merged down-step events
- calibration rows: `13`
- calibration/sentinel row-key overlap: `0`

## Signal Chain

`setpoint.v_body[2]` is body-z positive-down. The Contract-B world-up commanded reference is:

```text
v_ref_up = -v_body_z * cos(level_pitch) * cos(level_roll)
```

For A091, `level_pitch=-0.3106987661062333` and `level_roll=0.00025650874109527094`, so `cos_tilt=0.952120141444416`.

## Measured Response

The measured response column published by this artifact is `v_full_raw_mps`, reconstructed for every A091 certified FULL exposure as `-Theil-Sen(d e_meas/dt)` over the prior 0.50 s FULL history. This is the checkpoint/runtime-twin semantic of `rate_anchor_v_raw`; the artifact includes `v_full_raw_reconstruction_check.csv` against the previous forced-withhold packet for disclosure only. The fit uses only detector-selected A091 rows.

## REG-2 Boundary

This artifact does not write REG-2 and does not create the post-REG-2 intervention generator. It only supplies the calibration numerics and row-key binding for the next criterion commit.
