# ADJUDICATIVE REGENERATION ROUND

Scope: DIAGNOSTIC verdict-layer regeneration, CSV-only, no simulator launch.
Report generator commit: `4d4b0ef13b8e8cbee7263964eba0259087ea72d8`.
Computation checkpoint commit: `de19d881ce8fa0ddc27dd71d7306d0d366c43e90`.
Checkpoint evidence commit: `c19602f384bc30b0a53d649238b429f9085b6b8f`.
Source checkpoints: `tuning/ordered-round-A-G-DIAGNOSTIC-de19d88-20260720T220957Z`.
Input manifest: `tuning/adjudicative-regeneration-DIAGNOSTIC-4d4b0ef-20260720T231905Z/checkpoint_input_manifest.json`.
Input manifest sha256: `6e352d4b0ea87650c7904e6096d490a0d62125467c8e13453d1e0180fe739821`.

## Shadow Closure Read

Generated 3/20/23 tables from the registered split. The 20-confirmatory distribution is the closure read; overlap-3 and pooled-23 are context.

## Wrong-Sign Re-Score

Event support: 16 trace rows -> 9 command events -> 7 sign-evaluable + 2 zero-on-support.
Legacy formula: `reconstructed: cmd=terminal_vz_up_mps, e=e_meas, abs(e)>0.03, cmd*e<-1e-6; zero command has no deadband in the historical mask; reconstructs 28/68 scored trace rows`.
Verdict language: PASS at 1/1 is a FIXTURE-LEVEL pass (one physical approach, four correlated variants), not population evidence.

## RESPONSE55 Prediction Table

Produced per-cluster and cut-level |b1| vs legacy vertical activity tables using `rate_feed_forward_mps` as the archived applied vertical stream.

The artifact manifest lists output paths and SHA-256 digests.
