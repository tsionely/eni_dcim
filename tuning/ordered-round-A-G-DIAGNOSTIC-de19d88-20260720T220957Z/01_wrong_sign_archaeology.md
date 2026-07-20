# WRONG-SIGN ARCHAEOLOGY

Scope: DIAGNOSTIC, CSV-only, archaeology before re-score.

## Ancestor Harness

- First harness-lineage hit: `5c69823ee41fed7f9c24013029686e34b7ec4950`.
- The historical restamp count came from `tuning/run_archive_retro_census_and_diagnostics.py`.
- Formula reconstructed from the ancestor harness:

```python
term_rows = [r for r in all_rows if r.get('shadow_owner') == TERM_OWNER]
cmd = fnum(row.get('terminal_vz_up_mps'))
ez = fnum(row.get('e_meas'))
if cmd is not None and ez is not None and abs(ez) > 0.03 and cmd * ez < -1e-6:
    wrong_sign += 1
```

This did not encode command-vs-velocity directly. It is still marked `INVALID_TEST_WRONG_SUPPORT_AND_MASK` because it used trace rows as units, raw `e_meas`, the old 0.03 e deadband, and no old/new paired event support.

## Count Reconstruction

- Legacy term rows: `108`.
- Legacy formula positives: `28`.
- Traceability term/SIDE rows with new command populated: `16`.
- Unique command events after `(flight_id, trial, mono_ns)` dedupe and `fed=True` selection: `9`.
- Sign-evaluable events after 0.02 command deadband: `7`.
- Zero/neutral command events on support: `2`.

The apparent `16 -> 13` contraction is a trace-row to sign-evaluable-row contraction, not a support loss: three trace rows carry numeric zero/neutral commands. After event dedupe, they are two zero-command events that remain on support and score as nonviolations.

## Corrected Criterion

- Criterion file: `docs\criteria\wrong_sign_rescore_equivalence.md`.
- Criterion commit: `d0a73f028c265c428c1ceabbcb30b51cb2e66849`.
- Corrected wrong-sign clause result on paired common support: `PASS`.
- Historical zero-wrong-sign artifacts re-scored: `5`.
