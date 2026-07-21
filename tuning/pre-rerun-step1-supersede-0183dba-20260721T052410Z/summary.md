# PRE-RERUN Step 1 - supersede in type + stream-free provenance

DIAGNOSTIC token throughout. Replay/CSV only; no FlightSim/DCGame launch.

- generator commit: `0183dbaf98602b24ac511d13e561b34bb481dbfe`
- criterion ancestor cited: `9a85c73`
- manifest rows typed: `49, 50, 51, 52, 53, 54, 55`
- derived stream-free cut rows: `177` across `23` approaches / `23` flights
- source cut table: `tuning/second-mechanism-update-DIAGNOSTIC-55ba6da-20260720T234056Z/intervention_cut_b1_before_after.csv`

## Typed supersede

Rows 49-50 are typed `VOID_INVALID_INPUT / UNJUDGED`; rows 51-52 are `VOID_INVALID_INPUT / NO_VERDICT`; row 53 is `INADMISSIBLE`; row 54 is `RETAINED`; row 55 is `VOID_INVALID_INPUT / UNJUDGED`.

## Retained Diagnostic Provenance

`stream_free_before_intervention_cut_table.csv` keeps only the stream-free before-intervention cut fields from the 55ba6da round. The prohibited stream/activity/after-intervention columns are excluded by construction and listed in `excluded_stream_columns` on every row.
