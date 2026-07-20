# Metrology-f4 cluster failure autopsy

RESPONSE36 §3 — flight `20260720T142917-9aa0ef5c` (fixtures/20260720T142941-phase7m-metrology-f4).
Census label: **NO_CERTIFIED_FULL_BELOW_3P5** (distinct from f1's scale-gate kill).

## WHERE_USABILITY_DIED: **FULL_DROPOUT_THEN_UNCERTIFIED_CLOSE_DETS**

**SYSTEMATIC profile coverage lottery** (same label as archive F1/F5) — not an idiosyncratic one-off. **Not rescuable** as a 7th cluster without a tanks-visible profile selection change.

Approach DID get close (live min det 2.30 m, 2 dets ≤3.5 m) but both close dets are cert=none conf=0.5 and emit no harvest FULL feature. Continuous certified FULL ends ~5.31 m; the 4–5 m band is SIDE probation/row-only only; one recover FULL at 3.75 m sits ABOVE the 3.5 m census cut (e_reject=ok — not a scale_gate kill). Archive F1/F5 share NO_CERTIFIED_FULL_BELOW_3P5 with closest harvest FULL ≥4.3 m. Successful sibling 134522 delivers 33 certified FULL ≤3.5 on the same metrology profile family — so this is a systematic coverage lottery of the standard approach, not an idiosyncratic one-off and not f1's funnel.

## Stage-by-stage rejection table

| Stage | Pass? | Kill? | n | Detail |
|---|---|---|---:|---|
| `A_pad_to_mid_FULL_certified` | True | False | 31 | 31 certified FULL with range_z>5; continuous lock from pad |
| `B_FULL_dropout_to_SIDE_4to5m` | True | False | 6 | 6 SIDE rows ≤5m (probation=5, row_only=3); last continuous FULL before band ends ~5.31m |
| `C_harvest_certified_FULL_le_3p5` | False | True | 0 | census gate FAIL — 0 certified FULL ≤3.5m; closest certified FULL harvest range=3.748470846892272 (frame 284, phase=recover) |
| `D_live_detector_fixes_le_3p5` | True | False | 2 | YES approach got close — min_det={'mono_ns': 234436648706300, 'ts_ns': 1784557765501837500, 'range_z_m': 2.302953553473273, 'cert_status': 'none', 'confidence': 0.5, 'center_px': [259.23188202356476, 253.6251868953678]}; cert breakdown ≤3.5: {'none': 2} |
| `E_close_dets_certified` | False | True | 0 | close dets are cert=none conf=0.5 — identity never re-certified below promote floor path; promote_floor=1.6m is moot because these are not fresh FULL anchors in harvest |
| `F_SIDE_certified_for_cluster` | False | True | 0 | SIDE stays probation/row-only/none — census needs certified SIDE≥2 AND certified FULL≤3.5 |

## Did the approach get close enough?

- Live min detection: **{'mono_ns': 234436648706300, 'ts_ns': 1784557765501837500, 'range_z_m': 2.302953553473273, 'cert_status': 'none', 'confidence': 0.5, 'center_px': [259.23188202356476, 253.6251868953678]}**
- Live dets ≤3.5 m: **2** (cert breakdown `{'none': 2}`)
- Harvest closest certified FULL: **3.748 m** (recover frame 284) — above the 3.5 m cut
- Abort: environment collision (impulse=2.6), gates_passed=0

## Comparator board (same census label vs OK sibling)

| Flight | certified FULL≤3.5 | closest FULL | SIDE probation | census |
|---|---:|---:|---:|---|
| f4 `20260720T142917-9aa0ef5c` | 0 | 3.748470846892272 | 5 | NO_CERTIFIED_FULL_BELOW_3P5 |
| archive F1 | 0 | 4.314456083022236 | 1 | NO_CERTIFIED_FULL_BELOW_3P5 |
| archive F5 | 0 | 4.5730690923464765 | 0 | NO_CERTIFIED_FULL_BELOW_3P5 |
| ok sibling f2 | 33 | -0.8334916678566519 | 1 | OK |

## Ruled-out / distinguished

- f1-style scale_gate on flipped far gate: **no** — closest harvest FULL at 3.75 m has e_reject=ok; zero FULL≤3.5 to kill.
- Never approached: **no** — live to 2.30 m.
- Promote-floor blocking fresh cert below 1.6 m: **not the primary kill** — coverage already failed above 3.5 m; close dets are none/0.5 before that floor matters.
- Harness over-reject of honest certified FULL≤3.5: **no** — none exist in harvest.

## Profile selection change (tanks-visible)

**Decision: `CHANGE_METROLOGY_PROFILE_SELECTION`** — tanks-visible (RESPONSE36 §3 / advisory §6).
Do **not**: quiet retune of detector/cert thresholds to rescue these flights.

### P1_accept_gate: Collection accept-gate on certified coverage

A metrology flight counts toward the shortfall ONLY if harvest shows ≥4 certified FULL with range_z≤3.5 and e_reject=ok (cluster entry bar). Flights labeled NO_CERTIFIED_FULL_BELOW_3P5 are logged as coverage failures and do not consume the remaining shortfall slot — retry under P2.

### P2_hold_certified_through_band: Hold certified FULL through the 5→3 m band

Profile selection change: when FULL drops to SIDE before 4.5 m, align/hold (or slow to ≤1.2 m/s) until ≥3 consecutive certified FULL re-anchors, then continue. Goal = enrich older-age SIDE bins AND hold certified FULL coverage through ≤3.5 m (advisory §6 both clauses).

### P3_no_more_identical_blind_collection: Stop identical blind collection

Per RESPONSE36 escalation: do not fly another identical standard-profile metrology attempt until P1/P2 are adopted. f1 (scale_gate) and f4 (no certified FULL≤3.5) are two different honest funnels; repeating the profile reproduces known censoring.

## Deliverables

- `rejection_table_f4.csv`
- `timeline_le5p5_f4.csv`
- `comparator_summary.csv`
- `summary.json`
- `run_f4_autopsy.py`

